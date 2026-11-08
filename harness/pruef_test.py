"""Nutzenprobe der Prüfrunde: findet sie falsche Antworten, und lässt sie richtige in Ruhe?

Eingabe: JSON-Liste von Fällen {id, art: falsch|richtig, fall (Referenz-ID oder leer), verlauf, frage, antwort,
erwartet (optional: Zahl, die eine korrekte Antwort enthält)}. Aufruf auf dem VPS als root:
`python3 -I pruef_test.py faelle.json [--parallel 4]`. Ergebnis unter `laeufe/<zeitstempel>-pruefung/`.
"""

import argparse
import datetime
import json
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kontext  # noqa: E402
from lauf import APP, DATEN, datenstand  # noqa: E402
from pruefung import pruefen  # noqa: E402
from sitzung import Sitzungsfehler  # noqa: E402


def probe(nummer, fall, anweisung, lauf):
    arbeit = DATEN / "gespraeche" / f"{lauf}-p{nummer:02d}"
    arbeit.mkdir(parents=True)
    shutil.chown(arbeit, "dwhv3", "dwhv3")
    try:
        e = pruefen(arbeit, anweisung, fall.get("verlauf") or [], fall["frage"], fall["antwort"])
        r = e.pop("runde")
        e.update(sekunden=r.sekunden, sql=sum(1 for i in r.items if i.get("type") == "mcpToolCall"))
    except Sitzungsfehler as f:
        e = {"urteil": "fehler", "grund": str(f)}
    finally:
        shutil.rmtree(arbeit, ignore_errors=True)
    print(f"[{nummer}] {fall['art']:7} {e['urteil']:10} {e.get('sekunden', 0):>6}s {fall['id']}", flush=True)
    return {**{k: fall.get(k) for k in ("id", "art", "fall", "erwartet")}, **e}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("faelle")
    parser.add_argument("--parallel", type=int, default=4)
    args = parser.parse_args()
    faelle = json.loads(Path(args.faelle).read_text(encoding="utf-8"))
    stand, _ = datenstand()
    anweisung = kontext.anweisung(APP / "katalog", APP / "wissen", stand)
    lauf = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    ablage = DATEN / "laeufe" / f"{lauf}-pruefung"
    ablage.mkdir(parents=True)
    with ThreadPoolExecutor(args.parallel) as pool:
        ergebnisse = list(pool.map(lambda nf: probe(nf[0], nf[1], anweisung, lauf), enumerate(faelle, 1)))
    (ablage / "ergebnis.json").write_text(json.dumps(ergebnisse, ensure_ascii=False, indent=1), encoding="utf-8")
    print(ablage)


if __name__ == "__main__":
    main()
