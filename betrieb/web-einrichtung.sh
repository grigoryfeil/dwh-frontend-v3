#!/bin/bash
# Weboberfläche von DWH Frontend V3 auf dem VPS, als root, wiederholbar. Läuft am Ende von einrichtung.sh, die
# Anwendung samt web/ liegt dann unter /opt/dwh-frontend-v3/app. Berührt nur Eigenes: Unit dwh-frontend-v3-web,
# vHost dwhv3, Zertifikat der Subdomain, Kontendatei, Zugangsdatei des Testkontos.
# Aufruf: betrieb/web-einrichtung.sh <Pfad zum entpackten Repo-Stand auf dem VPS>
set -euo pipefail
quelle="${1:?Repo-Stand fehlt}"
APP=/opt/dwh-frontend-v3/app
domain=dwhv3.152-53-125-222.sslip.io
konten=/etc/dwh-frontend-v3/konten.json
zugang=/etc/dwh-frontend-v3/zugang  # Testkonto für Grigory: Benutzer und Passwort, nur root (0600)

/opt/dwh-frontend-v3/venv/bin/pip install -q "starlette==1.10.0" "uvicorn==0.54.0"

# Beta-Ablage der Gespräche: nur Dienst und root
install -d -m 0700 -o dwhv3 -g dwhv3 /var/lib/dwh-frontend-v3/ablage

# Konten und Testkonto: Passwort einmalig erzeugen, nie ausgeben
[[ -e $konten ]] || install -m 0640 -o root -g dwhv3 /dev/null "$konten"
chown root:dwhv3 "$konten" && chmod 0640 "$konten"
if [[ ! -e $zugang ]]; then
  umask 077
  printf 'benutzer: grigory\npasswort: %s\n' "$(openssl rand -base64 18 | tr -d '/+=' | cut -c1-20)" > "$zugang"
fi
chown root:root "$zugang" && chmod 0600 "$zugang"
sed -n 's/^passwort: //p' "$zugang" \
  | DWH_V3_KONTEN=$konten /opt/dwh-frontend-v3/venv/bin/python -I "$APP/web/konten.py" setzen grigory >/dev/null

# Beta-Konto: der Tester aus V2 mit unverändertem Hash (argon2), also gleichem Passwort, einmalig übernommen
python3 -I - "$konten" <<'PY'
import json, os, sys
pfad = sys.argv[1]
try:
    alt = json.load(open("/etc/dwh-frontend-v2/konten.json"))["konten"]["tester"]
except (OSError, KeyError, ValueError):
    sys.exit(0)
konten = json.load(open(pfad))
if "tester" not in konten:
    konten["tester"] = {"hash": alt["hash"], "aktiv": True}
    neu = pfad + ".neu"
    open(neu, "w").write(json.dumps(konten, ensure_ascii=False, indent=1) + "\n")
    st = os.stat(pfad); os.chown(neu, st.st_uid, st.st_gid); os.chmod(neu, 0o640); os.replace(neu, pfad)
PY

# Täglicher Selbsttest (06:30) über die öffentliche Adresse
install -D -m 0644 -o root -g root "$quelle/betrieb/selbsttest.py" "$APP/betrieb/selbsttest.py"
install -m 0644 -o root -g root "$quelle/betrieb/dwh-frontend-v3-selbsttest.service" \
  "$quelle/betrieb/dwh-frontend-v3-selbsttest.timer" /etc/systemd/system/

install -m 0644 -o root -g root "$quelle/betrieb/dwh-frontend-v3-web.service" /etc/systemd/system/
systemd-analyze verify /etc/systemd/system/dwh-frontend-v3-web.service
systemctl daemon-reload
systemctl enable dwh-frontend-v3-web.service >/dev/null
systemctl enable --now dwh-frontend-v3-selbsttest.timer >/dev/null
systemctl restart dwh-frontend-v3-web.service

# Zertifikat im webroot-Verfahren über den bestehenden Port-80-Server (acme-only), dann der vHost
if [[ ! -e /etc/letsencrypt/live/$domain/fullchain.pem ]]; then
  certbot certonly --webroot -w /var/www/html -d "$domain" --non-interactive --agree-tos \
    --key-type ecdsa --no-eff-email --register-unsafely-without-email --quiet
fi
# nginx bedient auch V1 und V2: eine fehlerhafte Fassung nie aktiv lassen, sondern die alte zurückspielen
[[ -e /etc/nginx/sites-available/dwhv3 ]] && cp -a /etc/nginx/sites-available/dwhv3 /etc/nginx/sites-available/.dwhv3.alt
install -m 0644 -o root -g root "$quelle/betrieb/nginx-dwhv3" /etc/nginx/sites-available/dwhv3
ln -sfn /etc/nginx/sites-available/dwhv3 /etc/nginx/sites-enabled/dwhv3
if ! nginx -t -q; then
  [[ -e /etc/nginx/sites-available/.dwhv3.alt ]] && mv /etc/nginx/sites-available/.dwhv3.alt /etc/nginx/sites-available/dwhv3
  echo "nginx-Konfiguration fehlerhaft, alte Fassung zurückgespielt" >&2
  exit 1
fi
rm -f /etc/nginx/sites-available/.dwhv3.alt
systemctl reload nginx
/usr/local/sbin/surveylens-port-preflight --all >/dev/null

sleep 2
systemctl is-active dwh-frontend-v3-web.service
curl -fsS -o /dev/null --resolve "$domain:443:127.0.0.1" "https://$domain/api/stand"
echo "web-einrichtung: ok"
