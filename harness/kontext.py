"""Baut die Anweisung an das Modell aus `anweisung.md` und den gepflegten Beständen.

Die Übersichten werden aus den Katalog-Tabellen erzeugt, nie von Hand verdichtet: je aktuell gültigem Objekt bzw.
jeder Kennzahl eine Zeile. Details liest das Modell selbst in den CSV-Dateien nach.
"""

import csv
import datetime
import re
from pathlib import Path

HIER = Path(__file__).resolve().parent


def _zeilen(datei):
    with open(datei, encoding="utf-8-sig", newline="") as f:
        return [z for z in csv.DictReader(f, delimiter=";") if not (z.get("gueltig_bis") or "").strip()]


def _kurz(text, laenge=160):
    text = re.sub(r"\s+", " ", text or "").strip()
    satz = re.split(r"(?<=[.!?])\s", text, maxsplit=1)[0]
    return satz if len(satz) <= laenge else satz[: laenge - 1] + "…"


def objekte(katalog):
    zeilen = []
    for z in _zeilen(Path(katalog) / "objekte.csv"):
        if z["status"] == "entfallen":
            continue
        offen = " (Bedeutung offen)" if z["status"] == "offen" else ""
        zeilen.append(f"- `{z['objekt_id']}` ({z['typ']}){offen}: {_kurz(z['definition'])} "
                      f"Eine Zeile: {_kurz(z['granularitaet'], 100)}")
    return "\n".join(zeilen)


def kennzahlen(katalog):
    return "\n".join(
        f"- `{z['kennzahl_id']}` {z['name']}{' (offen)' if z['status'] == 'offen' else ''}: {_kurz(z['definition'])}"
        for z in _zeilen(Path(katalog) / "kennzahlen.csv")
    )


def anweisung(katalog, wissen, datenstand, heute=None):
    vorlage = (HIER / "anweisung.md").read_text(encoding="utf-8")
    if not (Path(wissen) / "eintraege.csv").exists():
        vorlage = re.sub(r"^- SAE-Wissen.*\n", "", vorlage, flags=re.M)
    werte = {
        "katalog": str(katalog), "wissen": str(wissen), "datenstand": datenstand,
        "heute": (heute or datetime.date.today()).strftime("%d.%m.%Y"),
        "objekte": objekte(katalog), "kennzahlen": kennzahlen(katalog),
    }
    return re.sub(r"\{(\w+)\}", lambda m: werte.get(m.group(1), m.group(0)), vorlage)


if __name__ == "__main__":
    import sys
    text = anweisung(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "?")
    print(text)
    print(f"\n[{len(text.split())} Wörter, {len(text)} Zeichen]", file=sys.stderr)
