# 13 – Installation auf einem VPS (Hostinger)

Zwei Wege, beide mit demselben Ergebnis: Frontend unter `https://<hostname>` mit Passwortschutz, API und Datenbank
nicht öffentlich erreichbar, Cron-Jobs für Quoten-Archiv, Ergebnisse und Prognosen, nächtliche Backups.

| | A: Docker (empfohlen) | B: manuell |
|---|---|---|
| Einrichtung | Repo-Link im Hostinger **Docker Manager** (oder `docker compose up -d --build`) | Pakete, systemd, nginx, Cron von Hand |
| Updates | neu deployen | `bash deploy/update.sh` |
| Dateien | `docker-compose.yml`, `docker/` | `deploy/` |

> **Wichtig:** Die App hat (noch) kein eigenes Login. Auf der Einstellungsseite kann jeder mit Zugriff Ligen hinzufügen
> und damit API-Quota verbrauchen. Deshalb **nie** ohne Passwortschutz öffentlich betreiben (A: `QF_LOGIN_PASSWORD`,
> B: nginx-Passwort in Schritt 9).

## Variante A: Docker (Hostinger Docker Manager)

```text
Browser ──HTTPS + Passwort──▶ caddy :443 ──▶ frontend (Next.js) ──/api──▶ api (FastAPI) ──▶ db (PostgreSQL 16)
                                                                          cron (qf …) ──────▶ db
```

| Container | Aufgabe |
|---|---|
| `db` | PostgreSQL 16; beim **ersten** Start wird der Seed aus dem Repository eingespielt (1–2 Minuten) |
| `api` | REST-API; führt beim Start die Migrationen aus; Hintergrund-Jobs der Einstellungsseite laufen hier |
| `cron` | Zeitplan aus `docker/crontab`: Quoten-Snapshots, Betano-Verläufe, Saison nachladen, Prognosen, nächtliches Backup |
| `frontend` | privates Frontend (Next.js) |
| `caddy` | einziger öffentlicher Zugang (Port 80/443): HTTPS-Zertifikat von Let's Encrypt, Passwortschutz |

Daten liegen in Docker-Volumes (`qf_pgdata` Datenbank, `qf_backups` Backups) und bleiben bei Updates erhalten.

### A1. Daten aus dem Codespace ins Repository

Das Datenbank-Image enthält `seed/quotenfabrik_seed.dump` aus dem Repository – vorher den aktuellen Stand committen,
damit keine API-Requests für bereits geladene Daten verbraucht werden:

1. Im Codespace **Einstellungen → Backups → „Backup jetzt“** (bei „Seed aktualisieren = 1“ wird der Seed ersetzt).
2. Im Codespace-Terminal `ls -lh seed/` – unter **100 MB** (Limit von GitHub):
   `git add seed && git commit -m "Update seed" && git push`. Größer: siehe „Backup einspielen“ unten.

Ab dann ist der **Server die führende Installation**: neue Ligen nur noch dort hinzufügen.

### A2. VPS vorbereiten

- VPS mit **Ubuntu 24.04 und Docker** (in hPanel: Betriebssystem → Vorlage mit Docker bzw. „Docker Manager“),
  mindestens **4 GB RAM** (Modellläufe, Frontend-Build), ≥ 30 GB Platz.
- Hostname notieren: hPanel → VPS → Übersicht, z. B. `srv123456.hstgr.cloud` (zeigt bereits auf die IP des Servers).
- Firewall (hPanel → VPS → Firewall, falls aktiv): eingehend **22, 80, 443** erlauben – sonst bekommt Caddy kein
  Zertifikat.

### A3. Projekt im Docker Manager anlegen

hPanel → VPS → **Docker Manager** → neues Projekt (Compose) **aus einer URL / einem Git-Repository**
(die Bezeichnungen in hPanel können leicht abweichen):

- URL: `https://github.com/hrohnm/quotenfabrik_analyser` – die `docker-compose.yml` im Hauptverzeichnis wird verwendet.
  Ist das Repository privat, braucht Hostinger Lesezugriff (Zugangstoken bzw. Deploy-Key, je nach Angebot im Formular);
  gibt es die Möglichkeit nicht, Weg A5 nehmen.
- **Umgebungsvariablen** eintragen:

| Variable | Wert |
|---|---|
| `QF_DOMAIN` | Hostname, z. B. `srv123456.hstgr.cloud` |
| `QF_LOGIN_USER` | Benutzername für den Zugang (ohne Angabe: `admin`) |
| `QF_LOGIN_PASSWORD` | langes Passwort für den Zugang (**Pflicht**, ohne startet `caddy` nicht) |
| `POSTGRES_PASSWORD` | Datenbank-Passwort, nur Buchstaben und Ziffern (z. B. aus `openssl rand -hex 16`); wird bei jedem Start übernommen |
| `API_FOOTBALL_KEY` | API-Football-Key |
| `ODDSPAPI_API_KEY` | OddsPapi-Key |

- Deployen. Der erste Start dauert einige Minuten (Images bauen, Seed einspielen, Zertifikat holen).

**Erst deployen, dann Variablen eintragen** (Ablauf im Docker Manager) ist kein Problem: Der erste Start läuft mit
Standardwerten – `caddy` startet ohne `QF_LOGIN_PASSWORD` nicht (gewollt, die Seite ist bis dahin nicht erreichbar),
die Datenbank wird mit dem Passwort `qf` angelegt. Nach dem Eintragen der Variablen **neu deployen**: Der Container
`db` übernimmt bei jedem Start `POSTGRES_PASSWORD` als Passwort (Log: „Passwort von qf aus POSTGRES_PASSWORD
übernommen“), `api` und `cron` verbinden sich damit. Ein späterer Passwortwechsel funktioniert genauso.

Danach `https://<hostname>` öffnen → Benutzername/Passwort → Spieltage. Unter **Einstellungen** prüfen, ob beide
API-Keys erkannt werden. „Seed aktualisieren“ hat im Docker-Betrieb keine Wirkung (Backups landen im Volume).

### A4. Updates

Nach einem `git push` auf `main`: im Docker Manager das Projekt **neu deployen** (mit Neubau der Images). Vorher in den
Einstellungen nachsehen, dass kein Hintergrund-Job läuft – ein Neustart bricht ihn ab (er kann danach erneut gestartet
werden und lädt nur Fehlendes nach). Migrationen laufen beim Start der API automatisch.

### A5. Ohne Docker Manager (per SSH, gleicher Stack)

```bash
ssh root@<IP>
git clone https://github.com/hrohnm/quotenfabrik_analyser.git && cd quotenfabrik_analyser
cat > .env <<'ENV'
QF_DOMAIN=srv123456.hstgr.cloud
QF_LOGIN_USER=admin
QF_LOGIN_PASSWORD=<langes Passwort>
POSTGRES_PASSWORD=<openssl rand -hex 16>
API_FOOTBALL_KEY=<key>
ODDSPAPI_API_KEY=<key>
ENV
chmod 600 .env
docker compose up -d --build
docker compose logs -f api            # bis "Uvicorn running" erscheint, dann Strg+C
```

Update: `git pull && docker compose up -d --build`.

### Betrieb (Variante A)

| Aufgabe | Befehl (per SSH im Projektordner; im Docker Manager über Logs/Terminal des Containers) |
|---|---|
| Status | `docker compose ps` |
| Logs | `docker compose logs -f api` (ebenso `cron`, `caddy`, `db`) |
| Backup sofort | Einstellungsseite „Backup jetzt“ oder `docker compose exec api qf backup` |
| Backup herunterladen | Einstellungsseite → Backups → *Download* (regelmäßig außerhalb des Servers sichern!) |
| Backup einspielen | `docker compose cp <name>.dump api:/app/backups/` und `<name>.revision` ebenso, dann `docker compose exec api qf seed import --force --file /app/backups/<name>.dump` |
| CLI | `docker compose exec api qf …` (z. B. `qf quality`) |

Zusätzlich in hPanel automatische Snapshots/Backups des VPS aktivieren.

Typische Fehler beim Deploy:

| Meldung | Ursache und Lösung |
|---|---|
| `failed to bind host port 0.0.0.0:80 … address already in use` | Ein anderer Reverse-Proxy belegt Port 80/443 – oft **Traefik** (Hostinger-Vorlage) oder nginx. Wenn er sonst nichts bedient: stoppen (`docker stop <traefik> && docker update --restart=no <traefik>` bzw. `systemctl disable --now nginx`), dann neu deployen. |
| `pull access denied for quotenfabrik-…` / `No such image` | Images werden aus dem Repository gebaut, nicht heruntergeladen (`pull_policy: build`); tritt mit aktuellem Stand nicht mehr auf – neu deployen. |
| `api` unhealthy, im Log `Warte auf die Datenbank: … password authentication failed` | `db` neu starten lassen (Redeploy): übernimmt `POSTGRES_PASSWORD`; Passwort nur aus Buchstaben und Ziffern. |

## Variante B: manuelle Installation

```text
Browser ──HTTPS + Passwort──▶ nginx :443 ──▶ Next.js 127.0.0.1:3000 ──/api──▶ FastAPI 127.0.0.1:8000
                                                                                   │
                                     cron (qf …) ─────────────────────────────▶ PostgreSQL 16 (Docker, 127.0.0.1:5432)
```

Alle Dateien für den Server liegen unter `deploy/`. Pfade darin gelten für den Benutzer **`qf`** mit dem Repository
unter **`/home/qf/quotenfabrik_analyser`** – wer andere Namen nimmt, passt sie in den Dateien an. Die Datenbank läuft
hier nur als Container `db` (`docker compose up -d db`), alles andere direkt auf dem Server.

### 0. VPS wählen

- Betriebssystem: **Ubuntu 24.04** (bringt Python 3.12 und den PostgreSQL-Client 16 direkt mit).
- Mindestens **4 GB RAM** (Modellläufe und `next build`); mit 8 GB läuft alles entspannt. Platz: ≥ 30 GB
  (Datenbank ≈ 1 GB, Backups je ≈ 70 MB).
- Optional eine Domain/Subdomain, deren A-Record auf die IP des VPS zeigt (für HTTPS). Ohne eigene Domain geht auch der
  Hostname des VPS aus hPanel (z. B. `srv123456.hstgr.cloud`).

### 1. Grundeinrichtung (als root)

```bash
ssh root@<IP>
apt update && apt -y upgrade
adduser qf                    # Passwort vergeben (wird für sudo gebraucht)
usermod -aG sudo qf
# eigenen SSH-Key übernehmen, damit Login als qf ohne Passwort klappt
rsync --archive --chown=qf:qf ~/.ssh /home/qf
timedatectl                   # Zeitzone des Servers (Cron-Zeiten); Hostinger: UTC
```

Swap anlegen (schützt Modellläufe und den Frontend-Build vor Speichermangel):

```bash
fallocate -l 4G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

### 2. Pakete

```bash
apt -y install git curl python3-venv postgresql-client-16 nginx apache2-utils certbot python3-certbot-nginx
# Docker (für PostgreSQL)
curl -fsSL https://get.docker.com | sh
usermod -aG docker qf
# Node.js 22 LTS (Frontend)
curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
apt -y install nodejs
```

Danach als `qf` neu einloggen (damit die Docker-Gruppe greift): `exit`, dann `ssh qf@<IP>`.

### 3. Daten aus dem Codespace mitnehmen

Damit auf dem Server keine API-Requests für bereits geladene Daten verbraucht werden, kommt die Datenbank aus dem Seed:

1. Im Codespace unter **Einstellungen → Backups → „Backup jetzt“** (bei „Seed aktualisieren = 1“ wird dabei
   `seed/quotenfabrik_seed.dump` ersetzt).
2. Im Codespace-Terminal: `ls -lh seed/` – ist der Dump **unter 100 MB** (Limit von GitHub):
   ```bash
   git add seed && git commit -m "Update seed" && git push
   ```
   Ist er größer, stattdessen direkt kopieren (beide Dateien!) und in Schritt 6 mit `--file` einspielen:
   ```bash
   scp backups/<name>.dump backups/<name>.revision qf@<IP>:~/
   ```

Ab dann ist der **Server die führende Installation**: neue Ligen nur noch dort hinzufügen, sonst laufen die Daten
auseinander und Requests werden doppelt verbraucht.

### 4. Repository holen (als qf)

Öffentliches Repository: `git clone https://github.com/hrohnm/quotenfabrik_analyser.git`.
Privates Repository: Deploy-Key (nur Lesezugriff) anlegen:

```bash
ssh-keygen -t ed25519 -C "quotenfabrik-vps" -f ~/.ssh/id_ed25519 -N ""
cat ~/.ssh/id_ed25519.pub   # GitHub → Repository → Settings → Deploy keys → Add deploy key (ohne Schreibrecht)
git clone git@github.com:hrohnm/quotenfabrik_analyser.git
```

### 5. Konfiguration `.env`

```bash
cd ~/quotenfabrik_analyser
cp .env.example .env && chmod 600 .env
openssl rand -hex 16          # → sicheres Datenbank-Passwort
nano .env
```

In `.env` setzen (das Passwort an beiden Stellen gleich):

```dotenv
API_FOOTBALL_KEY=<dein Key>
ODDSPAPI_API_KEY=<dein Key>
POSTGRES_PASSWORD=<passwort>
DATABASE_URL=postgresql+psycopg://qf:<passwort>@localhost:5432/quotenfabrik
```

`POSTGRES_PASSWORD` übernimmt der Container `db` bei jedem Start. `.env` wird nie committet.

### 6. Datenbank starten (Seed wird automatisch eingespielt)

```bash
docker compose up -d db
docker compose logs -f db     # warten auf "Quotenfabrik: Seed eingespielt." (1–2 Minuten), dann Strg+C
```

Die Datenbank ist nur auf `127.0.0.1` erreichbar (`docker-compose.yml`) und startet nach einem Reboot automatisch.

### 7. Backend

```bash
cd ~/quotenfabrik_analyser/backend
python3 -m venv .venv
.venv/bin/pip install -e .
bash ../scripts/ensure_schema.sh        # Seed-Stand übernehmen + Migrationen
# nur falls der Dump per scp kam (Schritt 3):
# .venv/bin/qf seed import --force --file ~/<name>.dump
.venv/bin/qf quality | head            # Datenbestand prüfen
```

### 8. Frontend bauen, Dienste einrichten

```bash
cd ~/quotenfabrik_analyser/frontend-private
npm ci && npm run build
mkdir -p ~/logs
sudo cp ~/quotenfabrik_analyser/deploy/qf-api.service ~/quotenfabrik_analyser/deploy/qf-frontend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now qf-api qf-frontend
curl -s localhost:8000/api/meta | head -c 200; echo     # API antwortet?
curl -sI localhost:3000/spieltage | head -1             # Frontend antwortet? (HTTP/1.1 200)
```

### 9. nginx mit Passwort und HTTPS

```bash
sudo htpasswd -c /etc/nginx/quotenfabrik.htpasswd <benutzer>  # Benutzername frei wählbar, Passwort eingeben
sudo cp ~/quotenfabrik_analyser/deploy/nginx-quotenfabrik.conf /etc/nginx/sites-available/quotenfabrik
sudo nano /etc/nginx/sites-available/quotenfabrik              # server_name = deine Domain
sudo ln -s /etc/nginx/sites-available/quotenfabrik /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d <deine-domain>                         # HTTPS + Weiterleitung von http
```

Das Zertifikat verlängert certbot automatisch.

### 10. Firewall

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
sudo ufw status
```

Zusätzlich kann in hPanel (VPS → Firewall) dasselbe freigegeben werden (22, 80, 443). Port 5432, 8000 und 3000 bleiben zu.

### 11. Cron-Jobs

```bash
crontab -l                                      # sollte leer sein – sonst Einträge in deploy/crontab übernehmen
crontab ~/quotenfabrik_analyser/deploy/crontab
```

Enthält: Quoten-Snapshots (alle 3 h), Betano-Verläufe (alle 3 h), tägliches Nachladen der Saison, Prognosen +
Tipps (6/12/18 Uhr), Spielernamen an Spieltagen, nächtliches Backup. Logs unter `~/logs/`.
Die Saison (`--seasons aktuell`) wechselt im Juli automatisch.

### 12. Einstellungen auf der Seite

`https://<deine-domain>/einstellungen`:

- **Backup → „Seed aktualisieren“ auf 0** setzen. Auf dem Server soll ein Backup nicht die Seed-Datei im Repository
  verändern (sonst blockiert sie `git pull` bei Updates).
- „Backups behalten“ z. B. auf 7 (eine Woche nächtliche Backups).
- API-Kontingent oben prüfen: beide Keys erkannt?

### Updates einspielen

```bash
cd ~/quotenfabrik_analyser && bash deploy/update.sh
```

Holt den neuen Stand, installiert Abhängigkeiten, führt Migrationen aus, baut das Frontend und startet beide Dienste
neu. Bricht ab, solange ein Hintergrund-Job (z. B. Liga-Import) läuft.

### Backups

- Automatisch: nach jedem Liga-Import und nächtlich unter `~/quotenfabrik_analyser/backups/`.
- **Außerhalb des Servers sichern**, sonst sind sie bei einem Serverausfall mit weg: regelmäßig über
  Einstellungen → Backups → *Download* oder vom eigenen Rechner `scp qf@<IP>:quotenfabrik_analyser/backups/*.dump .`
  (die `.revision`-Datei gleichen Namens mitnehmen). Zusätzlich Snapshots/Backups in hPanel aktivieren.
- Wiederherstellen: `cd backend && .venv/bin/qf seed import --force --file ../backups/<name>.dump`

### Fehlersuche

| Problem | Prüfen |
|---|---|
| Seite lädt nicht / 502 | `systemctl status qf-frontend qf-api`, `journalctl -u qf-api -n 100` |
| API meldet DB-Fehler | `docker compose ps`, `docker compose logs db`, `DATABASE_URL` in `.env` |
| Hintergrund-Job hängt | Log: `/tmp/qf-job-<id>.log`; nach Absturz wird der Job beim nächsten Seitenaufruf als fehlgeschlagen markiert |
| Cron läuft nicht | `grep CRON /var/log/syslog`, Logs unter `~/logs/` |
| Zertifikat | `sudo certbot renew --dry-run` |
