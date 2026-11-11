#!/bin/bash
# Nächtliche Kopie der Beta-Ablage (Gespräche, Feedback, Nutzerlog) als root, ausgelöst vom Timer
# dwh-frontend-v3-ablage-sicherung. Ziel /var/backups/dwh-frontend-v3 (0700 root), je Tag ein Archiv, 14 Tage.
# Schützt vor versehentlichem Löschen und fehlerhaftem Überschreiben, nicht vor dem Verlust des Servers: Die Kopie
# liegt auf derselben Platte.
set -euo pipefail
umask 077
ziel=/var/backups/dwh-frontend-v3
install -d -m 0700 -o root -g root "$ziel"
neu="$ziel/.ablage-neu.tar.gz"
# Der Dienst schreibt währenddessen weiter: Status 1 (Datei änderte sich beim Lesen) ist kein Fehler
tar -C /var/lib/dwh-frontend-v3 -czf "$neu" ablage || [[ $? -eq 1 ]]
tar -tzf "$neu" >/dev/null  # nur ein lesbares Archiv ersetzt das von heute
mv "$neu" "$ziel/ablage-$(date +%F).tar.gz"
find "$ziel" -maxdepth 1 -name 'ablage-*.tar.gz' -mtime +14 -delete
