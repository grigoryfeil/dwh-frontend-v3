"""Vergleicht ein Laufergebnis von harness/lauf.py deterministisch mit dem Referenzsatz.

Aufruf:
  python3 referenz/vergleich.py laeufe/<lauf>/ergebnis.json            Markdown-Zusammenfassung auf stdout
  python3 referenz/vergleich.py ergebnis.json -o vergleich.md          zusätzlich in Datei
  python3 referenz/vergleich.py ergebnis.json --verdeckt               ohne Einzelheiten zurückgehaltener Fälle
  python3 referenz/vergleich.py --fragen entwicklung > fragen/ref.json Fragendatei für lauf.py erzeugen
                                (entwicklung, zurueckgehalten oder alle)

Kein Modellrichter. Je Fall wird die Antwort der letzten Runde geprüft:
  zahl            ein erwarteter Wert (Liste `werte` mit `toleranz` bzw. `toleranz_rel`, oder `bereich`) steht in der
                  Antwort, wenn `kontext` gesetzt ist, in einer Zeile, die auf `kontext` passt. Steht statt dessen nur
                  ein Wert aus `werte_unklar` da (zulässige Aufschlüsselung, nicht die Standardaussage), ist das unklar.
  einschraenkung  jedes Muster in `muster` kommt in der Antwort vor (reguläre Ausdrücke, Groß/klein egal).
  verboten        das Muster kommt nicht vor.
Ergebnis je Fall: bestanden, verfehlt oder unklar. Unklar heißt: deterministisch nicht entscheidbar, etwa weil das
Gespräch mit einer Rückfrage endet, abgebrochen ist oder ein Wert nur ohne passenden Kontext vorkommt.
"""

import argparse
import json
import re
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
DATEIEN = {"entwicklung": HIER / "faelle-entwicklung.json", "zurueckgehalten": HIER / "faelle-zurueckgehalten.json"}

ZAHL = re.compile(
    r"(?<![\w.,])[-−–]?(?:\d{1,3}(?:\.\d{3})+(?:,\d+)?"   # 1.234 oder 1.234,5 (deutsch)
    r"|\d{1,3}(?: \d{3})+(?:,\d+)?"                  # 1 234 mit schmalem Leerzeichen
    r"|\d+,\d+"                                          # 17,6
    r"|\d+\.\d{1,2}(?!\d)"                               # 17.6 (englisch)
    r"|\d+)(?![\w])"
)


def faelle_laden(rollen=("entwicklung", "zurueckgehalten")):
    faelle = []
    for rolle in rollen:
        pfad = DATEIEN[rolle]
        if not pfad.exists():
            continue
        daten = json.loads(pfad.read_text(encoding="utf-8"))
        for f in daten["faelle"]:
            if f.get("rolle") != rolle:
                raise SystemExit(f"{pfad.name}: Fall {f['id']} hat rolle={f.get('rolle')}")
            faelle.append(f)
    ids = [f["id"] for f in faelle]
    doppelt = {i for i in ids if ids.count(i) > 1}
    if doppelt:
        raise SystemExit(f"Doppelte Fall-IDs: {sorted(doppelt)}")
    return faelle


def zahl_lesen(text):
    t = text.replace("−", "-").replace("–", "-").replace(" ", "")
    if re.fullmatch(r"-?\d{1,3}(?:\.\d{3})+(?:,\d+)?", t):
        t = t.replace(".", "").replace(",", ".")
    elif "," in t:
        t = t.replace(",", ".")
    return float(t)


def zahlen(zeile):
    """(Wert, Prozent ja/nein, Fundtext) je Zahl einer Zeile."""
    ergebnis = []
    for m in ZAHL.finditer(zeile):
        try:
            wert = zahl_lesen(m.group(0))
        except ValueError:
            continue
        rest = zeile[m.end():m.end() + 12]
        ergebnis.append((wert, bool(re.match(r"\s?(%|Prozent|Pkt)", rest)), m.group(0)))
    return ergebnis


def norm(text):
    return re.sub(r"\s+", " ", text or "").strip().lower()


def gespraech_finden(fall, gespraeche):
    """Gespräch mit denselben Fragen. Liefert (gespraech, vollständig)."""
    soll = [norm(q) for q in fall["fragen"]]
    teilweise = None
    for g in gespraeche:
        ist = [norm(r.get("frage")) for r in g.get("runden", [])]
        if ist == soll:
            return g, True
        if ist and soll[:len(ist)] == ist and teilweise is None:
            teilweise = g
    return teilweise, False


def passt(wert, pruefung):
    if "bereich" in pruefung:
        lo, hi = pruefung["bereich"]
        return lo <= wert <= hi
    for w in pruefung["werte"]:
        tol = pruefung.get("toleranz", 0)
        if "toleranz_rel" in pruefung:
            tol = max(tol, abs(w) * pruefung["toleranz_rel"])
        if abs(wert - w) <= tol + 1e-9:
            return True
    return False


def erwartung_text(p):
    einheit = " %" if p.get("einheit") == "%" else ""
    if "bereich" in p:
        return f"{p['bereich'][0]} bis {p['bereich'][1]}{einheit}"
    werte = " oder ".join(f"{w:g}" for w in p["werte"])
    tol = f" ± {p['toleranz']:g}" if p.get("toleranz") else ""
    tol = f" ± {p['toleranz_rel'] * 100:g} %" if p.get("toleranz_rel") else tol
    return f"{werte}{einheit}{tol}"


def zeilen_mit_kontext(antwort):
    """(Zeile, Kontexttext) je nicht leerer Zeile. Bei Tabellenzeilen gehört die Kopfzeile der Tabelle dazu."""
    ergebnis, kopf = [], None
    for zeile in antwort.splitlines():
        if not zeile.strip():
            kopf = None
            continue
        if zeile.lstrip().startswith("|"):
            if re.fullmatch(r"\s*\|[\s:|-]+\|?\s*", zeile):
                continue
            if kopf is None:
                kopf = zeile
            ergebnis.append((zeile, f"{kopf} {zeile}"))
        else:
            kopf = None
            ergebnis.append((zeile, zeile))
    return ergebnis


def zahl_pruefen(p, antwort):
    zeilen = zeilen_mit_kontext(antwort)
    kontext = re.compile(p["kontext"], re.I) if p.get("kontext") else None
    prozent = p.get("einheit") == "%"
    ohne_kontext = None
    for zeile, umfeld in zeilen:
        for wert, ist_prozent, fund in zahlen(zeile):
            if prozent and not ist_prozent:
                continue
            if not passt(wert, p):
                continue
            if kontext is None or kontext.search(umfeld):
                return "ok", f"„{fund}“ in: {zeile.strip()[:160]}"
            ohne_kontext = ohne_kontext or f"„{fund}“ ohne passenden Kontext in: {zeile.strip()[:160]}"
    if ohne_kontext:
        return "unklar", ohne_kontext
    if p.get("werte_unklar"):
        # zulässige Aufschlüsselung statt der Standardaussage: Grigory entscheidet
        ersatz = {k: v for k, v in p.items() if k not in ("bereich", "werte_unklar")}
        ersatz["werte"] = p["werte_unklar"]
        ergebnis, fund = zahl_pruefen(ersatz, antwort)
        if ergebnis != "verfehlt":
            return "unklar", f"nur Aufschlüsselung statt Standardaussage: {fund}"
    # Fundstelle für verfehlt: Zahlen aus Zeilen mit passendem Kontext
    kandidaten = []
    for zeile, umfeld in zeilen:
        if kontext is None or kontext.search(umfeld):
            treffer = [f for _, ist_p, f in zahlen(zeile) if ist_p or not prozent]
            if treffer:
                kandidaten.append(f"{', '.join(treffer[:6])} in: {zeile.strip()[:140]}")
    fund = kandidaten[0] if kandidaten else "kein passender Wert in der Antwort"
    return "verfehlt", fund


def fall_pruefen(fall, gespraeche):
    g, vollstaendig = gespraech_finden(fall, gespraeche)
    if g is None:
        return {"status": "nicht gelaufen", "gruende": []}
    if g.get("fehler"):
        return {"status": "unklar", "gruende": [f"Gespräch abgebrochen: {g['fehler'][:160]}"]}
    if not vollstaendig:
        return {"status": "unklar",
                "gruende": [f"Lauf enthält nur {len(g['runden'])} von {len(fall['fragen'])} Fragen des Falls"]}
    runde = g["runden"][-1]
    if runde.get("fehler"):
        return {"status": "unklar", "gruende": [f"Runde mit Fehler: {runde['fehler'][:160]}"]}
    antwort = runde.get("antwort") or ""
    if antwort.lstrip().startswith("[Rückfrage]"):
        return {"status": "unklar", "gruende": [f"Antwort endet mit Rückfrage: {antwort.strip()[:200]}"]}
    gruende, status = [], "bestanden"
    for p in fall["erwartet"]:
        name = p.get("name", p["art"])
        if p["art"] == "zahl":
            ergebnis, fund = zahl_pruefen(p, antwort)
            if ergebnis == "ok":
                continue
            gruende.append(f"{name}: erwartet {erwartung_text(p)}; {fund}")
            status = "verfehlt" if ergebnis == "verfehlt" else (status if status == "verfehlt" else "unklar")
        elif p["art"] == "einschraenkung":
            fehlt = [m for m in p["muster"] if not re.search(m, antwort, re.I)]
            if fehlt:
                gruende.append(f"{name}: Einschränkung nicht benannt (fehlende Muster: {', '.join(fehlt)}); "
                               f"Antwortbeginn: {antwort.strip()[:160]}")
                status = "verfehlt"
        elif p["art"] == "verboten":
            m = re.search(p["muster"], antwort, re.I)
            if m:
                a, b = max(0, m.start() - 60), min(len(antwort), m.end() + 60)
                gruende.append(f"{name}: unzulässige Aussage: …{antwort[a:b].strip()}…")
                status = "verfehlt"
        else:
            raise SystemExit(f"Fall {fall['id']}: unbekannte Prüfart {p['art']}")
    return {"status": status, "gruende": gruende}


def bericht(lauf, faelle, ergebnisse, verdeckt=False):
    zeilen = [f"# Referenzvergleich Lauf {lauf.get('lauf', '?')}", "",
              f"Version {lauf.get('version', '?')}, Bestand `{lauf.get('schema', '?')}`, {len(faelle)} Referenzfälle.", ""]
    abweichend = sorted({f["datenstand"] for f in faelle if f.get("datenstand") != lauf.get("schema")})
    if abweichend:
        zeilen += [f"**Achtung:** Referenzen gelten für Bestand {', '.join(abweichend)}, der Lauf nutzt "
                   f"`{lauf.get('schema')}`. Abweichungen können am Datenstand liegen.", ""]
    stati = ["bestanden", "verfehlt", "unklar", "nicht gelaufen"]
    zeilen += ["| Rolle | " + " | ".join(stati) + " |", "|---|" + "---:|" * len(stati)]
    for rolle in ("entwicklung", "zurueckgehalten"):
        zahl = [sum(1 for f in faelle if f["rolle"] == rolle and ergebnisse[f["id"]]["status"] == s) for s in stati]
        zeilen.append(f"| {rolle} | " + " | ".join(map(str, zahl)) + " |")
    zeilen.append("")
    for status in ("verfehlt", "unklar"):
        betroffen = [f for f in faelle if ergebnisse[f["id"]]["status"] == status]
        if not betroffen:
            continue
        zeilen += [f"## {status.capitalize()}", ""]
        for f in betroffen:
            if verdeckt and f["rolle"] == "zurueckgehalten":
                zeilen.append(f"- **{f['id']}** ({f['rolle']}, {f['thema']}): Einzelheiten verdeckt")
                continue
            zeilen.append(f"- **{f['id']}** ({f['rolle']}, {f['thema']}): {f['fragen'][-1]}")
            zeilen += [f"  - {g}" for g in ergebnisse[f["id"]]["gruende"]]
        zeilen.append("")
    for status in ("bestanden", "nicht gelaufen"):
        ids = [f["id"] for f in faelle if ergebnisse[f["id"]]["status"] == status]
        if ids:
            zeilen += [f"**{status.capitalize()}:** {', '.join(ids)}", ""]
    return "\n".join(zeilen)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("ergebnis", nargs="?", help="ergebnis.json eines Laufs")
    parser.add_argument("-o", "--ausgabe", help="Markdown zusätzlich in diese Datei schreiben")
    parser.add_argument("--verdeckt", action="store_true",
                        help="Frage, Erwartung und Fundstelle zurückgehaltener Fälle weglassen (für entwickelnde Sessions)")
    parser.add_argument("--fragen", choices=["entwicklung", "zurueckgehalten", "alle"],
                        help="statt zu vergleichen eine Fragendatei für lauf.py ausgeben")
    args = parser.parse_args()
    if args.fragen:
        rollen = ("entwicklung", "zurueckgehalten") if args.fragen == "alle" else (args.fragen,)
        json.dump([f["fragen"] for f in faelle_laden(rollen)], sys.stdout, ensure_ascii=False, indent=1)
        print()
        return
    if not args.ergebnis:
        parser.error("ergebnis.json fehlt")
    lauf = json.loads(Path(args.ergebnis).read_text(encoding="utf-8"))
    faelle = faelle_laden()
    ergebnisse = {f["id"]: fall_pruefen(f, lauf.get("gespraeche", [])) for f in faelle}
    text = bericht(lauf, faelle, ergebnisse, args.verdeckt)
    print(text)
    if args.ausgabe:
        Path(args.ausgabe).write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
