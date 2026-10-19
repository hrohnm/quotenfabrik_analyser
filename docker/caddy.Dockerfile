# Public entry: HTTPS (Let's Encrypt for QF_DOMAIN) and password protection in front of the frontend.
FROM caddy:2.10
COPY docker/Caddyfile /etc/caddy/Caddyfile
COPY docker/caddy-start.sh /usr/local/bin/caddy-start.sh
CMD ["sh", "/usr/local/bin/caddy-start.sh"]
