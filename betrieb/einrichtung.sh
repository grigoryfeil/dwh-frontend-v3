#!/bin/bash
# Einrichtung von DWH Frontend V3 auf dem VPS, als root, wiederholbar.
# Aufruf: betrieb/einrichtung.sh <Pfad zum entpackten Repo-Stand auf dem VPS>
set -euo pipefail
quelle="${1:?Repo-Stand fehlt}"

# Wartungsfenster (betrieb/wartung.sh): nicht, solange Gespräche laufen oder ruhen
source "$quelle/betrieb/wartung.sh"
wartung_pruefen
V2=/opt/dwh-frontend-v2
APP=/opt/dwh-frontend-v3/app
H=/var/lib/dwh-frontend-v3/codex-home

# V2 einfrieren: nichts mehr starten, der Login geht an V3 über (zwei Kopien entwerten sich gegenseitig).
systemctl disable --now dwh-frontend-v2-web.service dwh-frontend-v2-codex.socket \
  dwh-frontend-v2-codex-aktualisieren.timer dwh-frontend-v2-lesekonto.timer 2>/dev/null || true

id dwhv3 &>/dev/null || useradd --system --home-dir /var/lib/dwh-frontend-v3 --shell /usr/sbin/nologin --user-group dwhv3
install -d -m 0755 -o root -g root /opt/dwh-frontend-v3 /opt/dwh-frontend-v3/codex
install -d -m 0750 -o dwhv3 -g dwhv3 /var/lib/dwh-frontend-v3 "$H" /var/lib/dwh-frontend-v3/gespraeche /var/lib/dwh-frontend-v3/runden
install -d -m 0700 -o root -g root /var/lib/dwh-frontend-v3/laeufe
install -d -m 0750 -o root -g dwhv3 /etc/dwh-frontend-v3

# Codex und Node: dieselben geprüften Versionen wie in V2, als eigene Kopie.
ver=$(readlink "$V2/codex/aktuell")
[[ -d /opt/dwh-frontend-v3/codex/$ver ]] || cp -a "$V2/codex/$ver" /opt/dwh-frontend-v3/codex/
ln -sfn "$ver" /opt/dwh-frontend-v3/codex/aktuell
node=$(readlink -f "$V2/node")
[[ -d /opt/dwh-frontend-v3/$(basename "$node") ]] || cp -a "$node" /opt/dwh-frontend-v3/
ln -sfn "$(basename "$node")" /opt/dwh-frontend-v3/node
chown -R root:root /opt/dwh-frontend-v3/codex "/opt/dwh-frontend-v3/$(basename "$node")"

# Umgebung der Modell-Shell: Vorlade-Datei für Node, python als Name für python3.
install -d -m 0755 -o root -g root /opt/dwh-frontend-v3/umgebung /opt/dwh-frontend-v3/umgebung/bin
install -m 0644 -o root -g root "$quelle/betrieb/umgebung/spawn-ohne-eingabe-pipe.cjs" /opt/dwh-frontend-v3/umgebung/
ln -sfn /usr/bin/python3 /opt/dwh-frontend-v3/umgebung/bin/python
install -m 0644 -o root -g root "$quelle/betrieb/umgebung/profile" /var/lib/dwh-frontend-v3/.profile

# Login und Plugin-Cache einmalig aus V2 übernehmen.
if [[ ! -e $H/auth.json ]]; then
  cp -a /var/lib/dwh-frontend-v2-codex/codex-home/{auth.json,installation_id,plugins,cache} "$H/"
  chown -R dwhv3:dwhv3 "$H"
fi
install -m 0640 -o root -g dwhv3 "$quelle/betrieb/codex-config.toml" "$H/config.toml"

# Lesekonto (nur SELECT auf den eingefrorenen Bestand).
[[ -e /etc/dwh-frontend-v3/dwh-leser.cnf ]] || \
  install -m 0640 -o root -g dwhv3 /etc/dwh-frontend-v2-codex/dwh-leser.cnf /etc/dwh-frontend-v3/dwh-leser.cnf

# Python für das Datenwerkzeug.
[[ -x /opt/dwh-frontend-v3/venv/bin/python ]] || python3 -m venv /opt/dwh-frontend-v3/venv
/opt/dwh-frontend-v3/venv/bin/pip install -q "mcp==2.3.0" "PyMySQL==1.2.3" "argon2-cffi==25.1.0"

# Anwendung: Harness, Katalog, SAE-Wissen, Version.
rm -rf "$APP.neu"
install -d -m 0755 "$APP.neu"
cp -r "$quelle/harness" "$quelle/katalog" "$quelle/VERSION" "$APP.neu/"
[[ -d $quelle/wissen ]] && cp -r "$quelle/wissen" "$APP.neu/"
[[ -d $quelle/web ]] && cp -r "$quelle/web" "$APP.neu/"
# Themenansichten aus Katalog und SAE-Wissen erzeugen (die Anweisung verweist darauf)
python3 -I "$APP.neu/harness/kontext.py" --themen "$APP.neu/katalog" "$APP.neu/wissen" "$APP.neu/kontext" >/dev/null
chown -R root:root "$APP.neu" && chmod -R a+rX "$APP.neu"
rm -rf "$APP" && mv "$APP.neu" "$APP"

/opt/dwh-frontend-v3/codex/aktuell/bin/codex --version
echo "einrichtung: ok"

# Weboberfläche (Unit, vHost, Zertifikat, Testkonto)
[[ -x $quelle/betrieb/web-einrichtung.sh ]] && "$quelle/betrieb/web-einrichtung.sh" "$quelle"
