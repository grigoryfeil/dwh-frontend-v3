"""Baut die Anweisung an das Modell und die Themenansichten aus den gepflegten Beständen.

Alles wird aus `katalog/` und `wissen/` erzeugt, nie von Hand verdichtet. Die Anweisung enthält je Thema einen
knappen Index. Die Themenansicht (`<kontext>/<thema>.md`) zeigt dazu vollständig, was ein Analyst für das Thema
braucht: Objekte mit Eignung, Abdeckung und Beziehungen, Kennzahlen mit ihren Varianten und Quellen und die
Einträge des SAE-Wissens, die sich auf diese Elemente beziehen.

Themenansichten erzeugen: `python3 -I kontext.py --themen <katalog> <wissen> <ziel>` (beim Ausrollen).
"""

import csv
import datetime
import re
from collections import defaultdict
from pathlib import Path

HIER = Path(__file__).resolve().parent


def _zeilen(datei):
    if not Path(datei).exists():
        return []
    with open(datei, encoding="utf-8-sig", newline="") as f:
        return [z for z in csv.DictReader(f, delimiter=";") if not (z.get("gueltig_bis") or "").strip()]


def _kurz(text, laenge=140):
    text = re.sub(r"\s+", " ", text or "").strip()
    satz = re.split(r"(?<=[.!?])\s", text, maxsplit=1)[0]
    return satz if len(satz) <= laenge else satz[: laenge - 1] + "…"


def _feld(name, wert):
    wert = (wert or "").strip()
    return f"- {name}: {wert}\n" if wert else ""


def _bestand(katalog, wissen):
    objekte = [z for z in _zeilen(Path(katalog) / "objekte.csv") if z["status"] != "entfallen"]
    kennzahlen = _zeilen(Path(katalog) / "kennzahlen.csv")
    eintraege = [z for z in _zeilen(Path(wissen) / "eintraege.csv") if z.get("status") != "veraltet"]
    return objekte, kennzahlen, eintraege


def themenansichten(katalog, wissen):
    objekte, kennzahlen, eintraege = _bestand(katalog, wissen)
    themen = defaultdict(lambda: {"objekte": [], "kennzahlen": []})
    for z in objekte:
        themen[z.get("thema") or "sonstiges"]["objekte"].append(z)
    for z in kennzahlen:
        themen[z.get("thema") or "sonstiges"]["kennzahlen"].append(z)
    ansichten = {}
    for thema, teil in sorted(themen.items()):
        ids = {z["objekt_id"] for z in teil["objekte"]} | {z["kennzahl_id"] for z in teil["kennzahlen"]}
        text = [f"# Thema {thema}\n\nErzeugt aus `katalog/` und `wissen/`. Zeilenweise Details und Felder stehen in "
                f"den CSV-Dateien.\n"]
        if teil["kennzahlen"]:
            text.append("\n## Kennzahlen\n")
            for z in teil["kennzahlen"]:
                text.append(f"\n### `{z['kennzahl_id']}` {z['name']}" + (" (offen)" if z["status"] == "offen" else "")
                            + "\n" + _feld("SAE-Standard", z.get("standard"))
                            + _feld("Definition", z.get("definition")) + _feld("Berechnung", z.get("berechnung"))
                            + _feld("Zähleinheit", z.get("zaehleinheit"))
                            + _feld("Grundgesamtheit", z.get("grundgesamtheit"))
                            + _feld("Zeitbezug", z.get("zeitbezug")) + _feld("Quellen und Abdeckung", z.get("quellen"))
                            + _feld("Verwandt", z.get("verwandt")) + _feld("Anmerkung", z.get("anmerkung")))
        if teil["objekte"]:
            text.append("\n## Objekte\n")
            for z in teil["objekte"]:
                text.append(f"\n### `{z['objekt_id']}` ({z['typ']})" + (" (Bedeutung offen)" if z["status"] == "offen"
                                                                          else "")
                            + "\n" + _feld("Definition", z.get("definition"))
                            + _feld("Eine Zeile", z.get("granularitaet")) + _feld("Schlüssel", z.get("schluessel"))
                            + _feld("Eignung", z.get("eignung")) + _feld("Abdeckung", z.get("abdeckung"))
                            + _feld("Verwandt", z.get("verwandt")))
        def betrifft(eintrag):  # Kennzahl- oder Objekt-ID direkt, Feld-ID über ihr Objekt (objekt.spalte)
            bezuege = [i.strip() for i in (eintrag.get("bezug_ids") or "").split(",") if i.strip()]
            return any(i in ids or i.split(".")[0] in ids for i in bezuege)

        bezogen = [e for e in eintraege if betrifft(e)]
        if bezogen:
            text.append("\n## SAE-Wissen zu diesem Thema\n\n")
            text.extend(f"- {e['aussage'].strip()} ({e.get('quelle', '').strip()}"
                        + (f", Stand {e['quelle_datum']}" if e.get("quelle_datum") else "")
                        + (", offen" if e.get("status") == "offen" else "") + ")\n" for e in bezogen)
        ansichten[thema] = "".join(text)
    return ansichten


def themenindex(katalog, wissen, kontext):
    objekte, kennzahlen, _ = _bestand(katalog, wissen)
    themen = defaultdict(lambda: {"objekte": [], "kennzahlen": []})
    for z in objekte:
        themen[z.get("thema") or "sonstiges"]["objekte"].append(z)
    for z in kennzahlen:
        themen[z.get("thema") or "sonstiges"]["kennzahlen"].append(z)
    teile = []
    for thema, teil in sorted(themen.items()):
        teile.append(f"\n## {thema} (`{kontext}/{thema}.md`)\n")
        teile.extend(f"- Kennzahl `{z['kennzahl_id']}` {z['name']}"
                     + (" (SAE-Standard)" if (z.get("standard") or "").strip().lower() == "ja" else "") + "\n"
                     for z in teil["kennzahlen"])
        teile.extend(f"- `{z['objekt_id']}`: {_kurz(z['definition'])}\n" for z in teil["objekte"])
    return "".join(teile)


def anweisung(katalog, wissen, datenstand, heute=None, kontext=None):
    kontext = Path(kontext or Path(katalog).parent / "kontext")
    vorlage = (HIER / "anweisung.md").read_text(encoding="utf-8")
    if not (Path(wissen) / "eintraege.csv").exists():
        vorlage = re.sub(r"^- SAE-Wissen.*\n", "", vorlage, flags=re.M)
    werte = {
        "katalog": str(katalog), "wissen": str(wissen), "kontext": str(kontext), "datenstand": datenstand,
        "heute": (heute or datetime.date.today()).strftime("%d.%m.%Y"),
        "themen": themenindex(katalog, wissen, kontext),
    }
    return re.sub(r"\{(\w+)\}", lambda m: werte.get(m.group(1), m.group(0)), vorlage)


if __name__ == "__main__":
    import sys
    if sys.argv[1] == "--themen":
        katalog, wissen, ziel = sys.argv[2], sys.argv[3], Path(sys.argv[4])
        ziel.mkdir(parents=True, exist_ok=True)
        for thema, text in themenansichten(katalog, wissen).items():
            (ziel / f"{thema}.md").write_text(text, encoding="utf-8")
            print(f"{thema}: {len(text.split())} Wörter", file=sys.stderr)
    else:
        text = anweisung(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "?")
        print(text)
        print(f"\n[{len(text.split())} Wörter, {len(text)} Zeichen]", file=sys.stderr)
