"""Führt Gespräche aus einer Fragendatei durch den Harness und legt die vollständigen Ausgaben ab.

Aufruf auf dem VPS als root: `python3 -I lauf.py fragen.json [--parallel 3] [--pruefen]`. Mit `--pruefen` läuft
jede Antwort durch die Prüfrunde wie mit dem Schalter Verify (Feld `pruefung` je Runde). Ergebnis unter
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
import pruefung  # noqa: E402
from sitzung import Gespraech, Sitzungsfehler  # noqa: E402

APP = Path("/opt/dwh-frontend-v3/app")
DATEN = Path("/var/lib/dwh-frontend-v3")
OPTIONSDATEI = "/etc/dwh-frontend-v3/dwh-leser.cnf"


def datenstand():
    optionen = configparser.ConfigParser(interpolation=None)
    optionen.read(OPTIONSDATEI)
    schema = optionen["client"]["database"]  # b_YYYYMMDDtHHMMSSz_xxxx
    return datetime.datetime.strptime(schema[2:10], "%Y%m%d").strftime("%d.%m.%Y"), schema


GRENZE = 200_000  # Zeichen je Werkzeugergebnis, schützt nur vor Ausreißern


def _ergebnis_text(ergebnis):
    """Text eines MCP-Ergebnisses: der Inhalt des Werkzeugs `sql` ist JSON mit spalten, zeilen, gekuerzt."""
    if not isinstance(ergebnis, dict):
        return ergebnis
    teile = [c.get("text", "") for c in ergebnis.get("content") or [] if isinstance(c, dict)]
    text = "\n".join(teile) if teile else json.dumps(ergebnis, ensure_ascii=False)
    try:
        return json.loads(text)
    except (ValueError, TypeError):
        return text[:GRENZE]


def schritt(item):
    """Ein Schritt der Runde, vollständig genug, um Antwort, Tabelle und Diagramm nachzuvollziehen."""
    s = _schritt(item)
    if s is not None:
        s["sekunde"] = item.get("_sekunde")
    return s


def _schritt(item):
    art = item.get("type")
    if art == "mcpToolCall":
        argumente = item.get("arguments") or {}
        return {"art": "sql", "abfrage": argumente.get("abfrage", argumente),
                "ergebnis": _ergebnis_text(item.get("result")), "fehler": item.get("error")}
    if art == "commandExecution":
        return {"art": "befehl", "befehl": str(item.get("command")),
                "ausgabe": str(item.get("aggregatedOutput") or "")[:GRENZE], "exitcode": item.get("exitCode")}
    if art == "reasoning":
        return {"art": "denken", "text": " ".join(item.get("summary") or [])}
    if art == "fileChange":
        return {"art": "datei", "aenderungen": [c.get("path") for c in item.get("changes") or []]}
    return None


def pruefrunde(arbeit, anweisung, runden, frage, text):
    """Prüfrunde wie in der Oberfläche (web/app.py, pruefe), in `arbeit/pruefung`. Liefert das Feld `pruefung`."""
    ort = arbeit / "pruefung"
    ort.mkdir(exist_ok=True)
    shutil.chown(ort, "dwhv3", "dwhv3")
    verlauf = [(r["frage"], r["antwort"]) for r in runden if r.get("antwort")]
    try:
        e = pruefung.pruefen(ort, anweisung, verlauf, frage, text)
        r = e.pop("runde")
        return {**e, "sekunden": r.sekunden, "token": r.token, "schritte": [s for s in map(schritt, r.items) if s]}
    except Sitzungsfehler as fehler:
        return {"urteil": "gescheitert", "antwort": None, "grund": str(fehler)[:300]}


def gespraech_fuehren(nummer, fragen, anweisung, lauf, pruefen=False):
    arbeit = DATEN / "gespraeche" / f"{lauf}-{nummer:02d}"
    arbeit.mkdir(parents=True)
    shutil.chown(arbeit, "dwhv3", "dwhv3")
    ergebnis = {"nummer": nummer, "runden": []}
    korrektur = None
    try:
        with Gespraech(arbeit, anweisung) as g:
            ergebnis["codex"] = g.codex_version
            for frage in fragen:
                # {"falls_rueckfrage": "Ja."}: die vorbereitete Antwort eines Nutzers, der nur antwortet, wenn gefragt
                if isinstance(frage, dict):
                    letzte = ergebnis["runden"][-1].get("antwort", "") if ergebnis["runden"] else ""
                    if not letzte.lstrip().startswith("[Rückfrage]"):
                        continue
                    frage = frage["falls_rueckfrage"]
                try:
                    r = g.frage(pruefung.mit_korrektur(korrektur, frage) if korrektur else frage)
                    korrektur = None
                except Sitzungsfehler as fehler:
                    ergebnis["runden"].append({"frage": frage, "fehler": str(fehler)})
                    break
                runde = {
                    "frage": frage, "antwort": r.text, "sekunden": r.sekunden, "token": r.token,
                    "modellanfragen": r.modellanfragen,
                    "schritte": [s for s in map(schritt, r.items) if s],
                }
                # --pruefen: wie der Schalter Verify, die korrigierte Fassung ersetzt die Antwort und geht weiter
                if pruefen and not r.text.lstrip().startswith("[Rückfrage]"):
                    p = pruefrunde(arbeit, anweisung, ergebnis["runden"], frage, r.text)
                    runde["pruefung"] = p
                    if p["urteil"] == "korrigiert" and p.get("antwort"):
                        runde["antwort_vor_pruefung"], runde["antwort"] = r.text, p["antwort"]
                        korrektur = p["antwort"]
                ergebnis["runden"].append(runde)
                print(f"[{nummer}] {r.sekunden:>6}s  {frage[:70]}", flush=True)
    except Sitzungsfehler as fehler:
        ergebnis["fehler"] = str(fehler)
        print(f"[{nummer}] FEHLER {fehler}", flush=True)
    # Erzeugte Dateien (Diagramme, Tabellen) mit dem Lauf sichern, das Gesprächsverzeichnis ist nur Arbeitsfläche
    ziel = DATEN / "laeufe" / lauf / f"dateien-{nummer:02d}"
    dateien = [p for p in arbeit.rglob("*") if p.is_file() and not p.is_symlink()
               and not any(t.startswith(".") for t in p.relative_to(arbeit).parts)]
    for pfad in dateien:
        (ziel / pfad.relative_to(arbeit)).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(pfad, ziel / pfad.relative_to(arbeit))
    ergebnis["dateien"] = [str(p.relative_to(arbeit)) for p in dateien]
    shutil.rmtree(arbeit, ignore_errors=True)  # Daten bleiben nur im Lauf (root), nicht im Bereich der Modell-Shell
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
    parser.add_argument("--pruefen", action="store_true", help="jede Antwort durch die Prüfrunde (Schalter Verify)")
    args = parser.parse_args()
    gespraeche = json.loads(Path(args.fragen).read_text(encoding="utf-8"))
    stand, schema = datenstand()
    anweisung = kontext.anweisung(APP / "katalog", APP / "wissen", stand)
    lauf = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    ablage = DATEN / "laeufe" / lauf
    ablage.mkdir(parents=True)
    with ThreadPoolExecutor(args.parallel) as pool:
        ergebnisse = list(pool.map(lambda nf: gespraech_fuehren(nf[0], nf[1], anweisung, lauf, args.pruefen),
                                   enumerate(gespraeche, 1)))
    version = (APP / "VERSION").read_text().strip() if (APP / "VERSION").exists() else "?"
    (ablage / "ergebnis.json").write_text(json.dumps(
        {"lauf": lauf, "version": version, "schema": schema, "pruefen": args.pruefen, "anweisung": anweisung,
         "gespraeche": ergebnisse},
        ensure_ascii=False, indent=1), encoding="utf-8")
    (ablage / "bericht.md").write_text(bericht(lauf, stand, ergebnisse), encoding="utf-8")
    print(ablage)


if __name__ == "__main__":
    main()
