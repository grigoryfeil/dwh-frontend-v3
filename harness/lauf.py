"""Führt Gespräche aus einer Fragendatei durch den Harness und legt die vollständigen Ausgaben ab.

Aufruf auf dem VPS als root: `python3 -I lauf.py fragen.json [--parallel 3]`. Ergebnis unter
`/var/lib/dwh-frontend-v3/laeufe/<zeitstempel>/`: `ergebnis.json` (alles) und `bericht.md` (zum Lesen).
"""

import argparse
import configparser
import datetime
import json
import os
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kontext  # noqa: E402
from sitzung import Gespraech, Sitzungsfehler  # noqa: E402

APP = Path("/opt/dwh-frontend-v3/app")
DATEN = Path("/var/lib/dwh-frontend-v3")
OPTIONSDATEI = "/etc/dwh-frontend-v3/dwh-leser.cnf"


def datenstand():
    optionen = configparser.ConfigParser(interpolation=None)
    optionen.read(OPTIONSDATEI)
    schema = optionen["client"]["database"]  # b_YYYYMMDDtHHMMSSz_xxxx
    return datetime.datetime.strptime(schema[2:10], "%Y%m%d").strftime("%d.%m.%Y"), schema


def schritt(item):
    art = item.get("type")
    if art == "mcpToolCall":
        argumente = item.get("arguments") or {}
        return {"art": "sql", "abfrage": argumente.get("abfrage", argumente)}
    if art == "commandExecution":
        return {"art": "befehl", "befehl": str(item.get("command"))[:400]}
    if art == "reasoning":
        return {"art": "denken", "text": " ".join(item.get("summary") or [])[:400]}
    return None


def gespraech_fuehren(nummer, fragen, anweisung, lauf):
    arbeit = DATEN / "gespraeche" / f"{lauf}-{nummer:02d}"
    arbeit.mkdir(parents=True)
    shutil.chown(arbeit, "dwhv3", "dwhv3")
    ergebnis = {"nummer": nummer, "runden": []}
    try:
        with Gespraech(arbeit, anweisung) as g:
            ergebnis["codex"] = g.codex_version
            for frage in fragen:
                try:
                    r = g.frage(frage)
                except Sitzungsfehler as fehler:
                    ergebnis["runden"].append({"frage": frage, "fehler": str(fehler)})
                    break
                ergebnis["runden"].append({
                    "frage": frage, "antwort": r.text, "sekunden": r.sekunden, "token": r.token,
                    "modellanfragen": r.modellanfragen,
                    "schritte": [s for s in map(schritt, r.items) if s],
                })
                print(f"[{nummer}] {r.sekunden:>6}s  {frage[:70]}", flush=True)
    except Sitzungsfehler as fehler:
        ergebnis["fehler"] = str(fehler)
        print(f"[{nummer}] FEHLER {fehler}", flush=True)
    return ergebnis


def bericht(lauf, stand, ergebnisse):
    teile = [f"# Lauf {lauf}\n\nDatenstand {stand}\n"]
    for e in ergebnisse:
        teile.append(f"\n---\n\n## Gespräch {e['nummer']}\n")
        if e.get("fehler"):
            teile.append(f"**Fehler:** {e['fehler']}\n")
        for r in e["runden"]:
            teile.append(f"\n### Frage: {r['frage']}\n")
            if r.get("fehler"):
                teile.append(f"**Fehler:** {r['fehler']}\n")
                continue
            sql = sum(1 for s in r["schritte"] if s["art"] == "sql")
            befehle = sum(1 for s in r["schritte"] if s["art"] == "befehl")
            teile.append(f"*{r['sekunden']} s, {sql} SQL-Abfragen, {befehle} Shell-Befehle, "
                         f"{r['token'].get('inputTokens', '?')} Eingabe-Token*\n\n{r['antwort']}\n")
    return "\n".join(teile)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("fragen")
    parser.add_argument("--parallel", type=int, default=3)
    args = parser.parse_args()
    gespraeche = json.loads(Path(args.fragen).read_text(encoding="utf-8"))
    stand, schema = datenstand()
    anweisung = kontext.anweisung(APP / "katalog", APP / "wissen", stand)
    lauf = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    ablage = DATEN / "laeufe" / lauf
    ablage.mkdir(parents=True)
    with ThreadPoolExecutor(args.parallel) as pool:
        ergebnisse = list(pool.map(lambda nf: gespraech_fuehren(nf[0], nf[1], anweisung, lauf),
                                   enumerate(gespraeche, 1)))
    version = (APP / "VERSION").read_text().strip() if (APP / "VERSION").exists() else "?"
    (ablage / "ergebnis.json").write_text(json.dumps(
        {"lauf": lauf, "version": version, "schema": schema, "anweisung": anweisung, "gespraeche": ergebnisse},
        ensure_ascii=False, indent=1), encoding="utf-8")
    (ablage / "bericht.md").write_text(bericht(lauf, stand, ergebnisse), encoding="utf-8")
    print(ablage)


if __name__ == "__main__":
    main()
