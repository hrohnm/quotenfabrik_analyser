"use client";

import { useRouter } from "next/navigation";
import { startTransition } from "react";
import { Card } from "@/components/ui";

export default function Error({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  const router = useRouter();
  // Server component errors need a refresh, reset() alone only re-renders the client boundary
  const retry = () => startTransition(() => { router.refresh(); reset(); });
  const offline = /nicht erreichbar|fetch failed/i.test(error.message);
  return (
    <Card title={offline ? "Backend nicht erreichbar" : "Fehler beim Laden"}>
      <div className="space-y-3 text-sm text-slate-600">
        <p>{offline ? "Das Frontend bekommt keine Antwort von der API (Port 8000)." : error.message}</p>
        <p>{offline ? "Dienste" : "Falls das Backend nicht läuft: Dienste"} neu starten (im Terminal des Codespace) und danach erneut versuchen:</p>
        <pre className="rounded-md bg-slate-900 px-3 py-2 text-xs text-slate-100">bash .devcontainer/restart.sh</pre>
        <p className="text-xs text-slate-400">Logs: /tmp/api.log und /tmp/qf-services.log</p>
        <button type="button" onClick={retry} className="rounded-md bg-slate-900 px-3 py-1.5 text-sm text-white">Erneut versuchen</button>
      </div>
    </Card>
  );
}
