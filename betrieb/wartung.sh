# Wartungsfenster für das Einspielen, eingebunden von einrichtung.sh und web-einrichtung.sh.
# Einspielen tauscht Dateien unter laufenden Prozessen und startet die Web-Unit neu: laufende Runden brechen ab, und
# alle Gespräche, auch ruhende ohne Modellprozess, verlieren ihren Verlauf. Deshalb nur, wenn weder ein Modellprozess
# läuft noch ein Gespräch offen ist, oder ausdrücklich mit ERZWINGEN=1. Prüfung einmal je Einspielen.
wartung_pruefen() {
  [[ ${DWH_WARTUNG_GEPRUEFT:-0} == 1 ]] && return 0
  local prozesse gespraeche
  prozesse=$(pgrep -u dwhv3 -fc "app-server" || true)
  gespraeche=$(find /var/lib/dwh-frontend-v3/gespraeche -maxdepth 1 -name 'web-*' -type d 2>/dev/null | wc -l)
  if [[ $(( ${prozesse:-0} + gespraeche )) -gt 0 && ${ERZWINGEN:-0} != 1 ]]; then
    echo "Einspielen abgebrochen: ${prozesse:-0} Modellprozess(e), $gespraeche offene(s) Gespräch(e) in der Oberfläche." >&2
    echo "Sie verlören ihren Verlauf. Später erneut oder mit ERZWINGEN=1." >&2
    exit 1
  fi
  export DWH_WARTUNG_GEPRUEFT=1
}
