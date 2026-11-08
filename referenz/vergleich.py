"""Vergleicht ein Laufergebnis von harness/lauf.py deterministisch mit dem Referenzsatz.

Aufruf:
  python3 referenz/vergleich.py laeufe/<lauf>/ergebnis.json            Markdown-Zusammenfassung auf stdout
  python3 referenz/vergleich.py ergebnis.json -o vergleich.md          zusätzlich in Datei
  python3 referenz/vergleich.py ergebnis.json --verdeckt               ohne Einzelheiten zurückgehaltener Fälle
  python3 referenz/vergleich.py --fragen entwicklung > fragen/ref.json Fragendatei für lauf.py erzeugen
                                (entwicklung, zurueckgehalten oder alle)

Fragenliste eines Falls: Texte und bedingte Antworten {"falls_rueckfrage": "Ja."}. lauf.py sendet eine bedingte
Antwort nur, wenn die vorige Antwort mit [Rückfrage] beginnt. Wurde sie übersprungen, ist das Gespräch trotzdem
vollständig. Wurde sie ohne Rückfrage dennoch gesendet (älterer Treiber), zählt die Runde nicht.

Kein Modellrichter. Je Fall wird die Antwort der letzten gewerteten Runde geprüft:
  zahl            ein erwarteter Wert (Liste `werte` mit `toleranz` bzw. `toleranz_rel`, oder `bereich`) steht in der
                  Antwort, wenn `kontext` gesetzt ist, in einer Zeile, die auf `kontext` passt. Steht statt dessen nur
                  ein Wert aus `werte_unklar` da (zulässige Aufschlüsselung, nicht die Standardaussage), ist das unklar.
  einschraenkung  jedes Muster in `muster` kommt in der Antwort vor (reguläre Ausdrücke, Groß/klein egal).
  verboten        das Muster kommt nicht vor.
  dashboard       eine .html-Datei liegt unter den Dateien des Gesprächs (laeufe/<lauf>/dateien-<nr>/), und jeder
                  Kernwert steht in den eingebetteten Daten (HTML oder mitgelieferte data.json): als Summe eines
                  Zahlenfelds über die Zeilen, die die Bedingungen einer Variante in `zeilen` erfüllen, bei
                  `einheit: "%"` auch als Quotient zweier Summen. Steht er nur als lose Zahl da, ist das unklar.
                  Fehlen passende Zeilen, zählt ein Wert, der im gerenderten Standardzustand sichtbar ist (Chromium als
                  nobody ohne Netz, nur auf dem VPS). Ein Wert mit Bedingungen, der dort nicht steht, ist unklar
                  (Filter nötig). `sekunden_max` gibt nur einen Hinweis zur Laufzeit. Die Gestaltung prüft der Mensch.
Ergebnis je Fall: bestanden, verfehlt oder unklar. Unklar heißt: deterministisch nicht entscheidbar, etwa weil das
Gespräch mit einer Rückfrage endet, abgebrochen ist oder ein Wert nur ohne passenden Kontext vorkommt.
"""

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
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


def ist_bedingt(element):
    return isinstance(element, dict)


def fragetext(element):
    return element["falls_rueckfrage"] if ist_bedingt(element) else element


def ist_rueckfrage(runde):
    return (runde.get("antwort") or "").lstrip().startswith("[Rückfrage]")


def abgleichen(fragen, runden):
    """Legt die Fragenliste eines Falls auf die Runden eines Gesprächs.

    Liefert ("voll", Index der gewerteten Runde), ("teil", fehlende Frage) oder None, wenn es ein anderes Gespräch ist.
    Gewertet wird die letzte Runde zu einer Frage oder zu einer bedingten Antwort, der eine Rückfrage vorausging.
    """
    i, gewertet = 0, None
    for element in fragen:
        text = norm(fragetext(element))
        trifft = i < len(runden) and norm(runden[i].get("frage")) == text
        if ist_bedingt(element):
            berechtigt = i > 0 and ist_rueckfrage(runden[i - 1])
            if trifft:
                if berechtigt:
                    gewertet = i
                i += 1          # ohne Rückfrage gesendet (älterer Treiber): Runde zählt nicht
            elif berechtigt:
                return ("teil", fragetext(element)) if i == len(runden) else None
            continue            # übersprungen, weil keine Rückfrage kam
        if not trifft:
            return ("teil", fragetext(element)) if 0 < i == len(runden) else None
        gewertet, i = i, i + 1
    return ("voll", gewertet) if i == len(runden) else None


def gespraech_finden(fall, gespraeche):
    """Gespräch zum Fall. Liefert (gespraech, ("voll", Rundenindex) oder ("teil", fehlende Frage)) oder (None, None)."""
    teilweise = (None, None)
    for g in gespraeche:
        treffer = abgleichen(fall["fragen"], g.get("runden", []))
        if treffer and treffer[0] == "voll":
            return g, treffer
        if treffer and teilweise[0] is None:
            teilweise = (g, treffer)
    return teilweise


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


def schluessel(wert):
    """Vergleichsform eines Zeilenwerts: klein, nur Buchstaben und Ziffern; die Uhrzeit eines Datums entfällt."""
    t = str(wert)
    if re.match(r"\d{4}-\d{2}-\d{2}[T ]", t):
        t = t[:10]
    return re.sub(r"[^0-9a-zäöüß]", "", t.lower())


def bedingung_erfuellt(zeile, alternativen):
    """Ein Feld der Zeile hat einen der Werte. Datumsangaben wie 2026 oder 2026-10 gelten als Präfix."""
    werte = [schluessel(v) for v in zeile.values() if isinstance(v, (str, int)) and not isinstance(v, bool)]
    for a in alternativen:
        k, datum = schluessel(a), re.fullmatch(r"\d{4}(-\d{2}){0,2}", str(a))
        if any(w == k or (datum and w.startswith(k)) for w in werte):
            return True
    return False


def ist_zahl(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def tabellen(daten, pfad="$"):
    """(Pfad, Zeilen) je Liste von Objekten in eingebetteten Daten."""
    if isinstance(daten, dict):
        for k, v in daten.items():
            yield from tabellen(v, f"{pfad}.{k}")
    elif isinstance(daten, list):
        zeilen = [z for z in daten if isinstance(z, dict)]
        if zeilen:
            yield pfad, zeilen
        for i, v in enumerate(daten):
            if isinstance(v, (list, dict)):
                yield from tabellen(v, f"{pfad}[{i}]")


def blaetter(daten):
    if isinstance(daten, dict):
        daten = list(daten.values())
    if isinstance(daten, list):
        for v in daten:
            yield from blaetter(v)
    elif ist_zahl(daten):
        yield daten


def html_daten(text):
    """JSON-Daten einer HTML-Datei und der übrige Text (ohne eingebettete Skriptbündel) für lose Zahlen.

    <script type="application/json">-Blöcke werden einzeln oder, wenn die Daten auf mehrere Blöcke verteilt sind,
    aufeinanderfolgend zusammengesetzt gelesen. Zusätzlich JSON-Listen von Objekten im übrigen Skripttext."""
    daten, puffer = [], ""
    muster = r"<script[^>]*type=[\"']application/json[\"'][^>]*>(.*?)</script>"
    for koerper in re.findall(muster, text, re.S | re.I):
        koerper = koerper.replace("<\\/", "</")
        for kandidat in (puffer + koerper, koerper):
            try:
                daten.append(json.loads(kandidat))
                puffer = ""
                break
            except ValueError:
                pass
        else:
            puffer += koerper
    rest = re.sub(muster, " ", text, flags=re.S | re.I)
    rest = re.sub(r"data:[\w/+.-]+;base64,[A-Za-z0-9+/=]+", " ", rest)
    dekoder, pos = json.JSONDecoder(), 0
    for m in re.finditer(r"\[\s*\{\s*\"", rest):
        if m.start() < pos:
            continue
        try:
            obj, ende = dekoder.raw_decode(rest, m.start())
            daten.append(obj)
            pos = ende
        except ValueError:
            pass
    return daten, rest


def dashboard_quellen(ordner, namen):
    """[(Dateiname, Daten, loser Text)] aus den .html-Dateien und mitgelieferten data.json eines Gesprächs."""
    quellen = []
    for n in namen:
        pfad = ordner / n
        if not pfad.is_file():
            continue
        text = pfad.read_text(encoding="utf-8", errors="replace")
        if n.lower().endswith((".html", ".htm")):
            daten, rest = html_daten(text)
            quellen.append((n, daten, rest))
        elif Path(n).name == "data.json":
            try:
                quellen.append((n, [json.loads(text)], ""))
            except ValueError:
                pass
    return quellen


def gerendert(pfad):
    """Sichtbarer Text der Seite nach dem Ausführen ihrer Skripte (Standardzustand), oder None.

    Schlanke Dashboards rechnen Kennzahlen erst im Browser. Chromium läuft dafür als Nutzer nobody, ohne Netz
    (Proxy ins Leere), in einem Wegwerfverzeichnis. Nur auf dem VPS (root, runuser, chromium vorhanden)."""
    chromium, runuser = shutil.which("chromium"), shutil.which("runuser")
    if not chromium or not runuser or os.geteuid() != 0:
        return None
    with tempfile.TemporaryDirectory() as tmp:
        os.chmod(tmp, 0o777)
        kopie = Path(tmp) / "seite.html"
        shutil.copy(pfad, kopie)
        os.chmod(kopie, 0o644)
        try:
            dom = subprocess.run(
                [runuser, "-u", "nobody", "--", "env", f"HOME={tmp}", chromium, "--headless=new", "--no-sandbox",
                 "--disable-gpu", "--proxy-server=127.0.0.1:9", "--virtual-time-budget=8000", f"--user-data-dir={tmp}/p",
                 "--dump-dom", f"file://{kopie}"], capture_output=True, text=True, timeout=90).stdout
        except (subprocess.TimeoutExpired, OSError):
            return None
    dom = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", dom)
    return html.unescape(re.sub(r"<[^>]+>", " ", dom))


def kernwert_kandidaten(zeilen, anteil):
    """(Wert, Beschreibung) aus den Zeilen: Summen je Zahlenfeld, bei Anteilen Quotienten, Mittel und Einzelwerte."""
    summen = {}
    for z in zeilen:
        for f, v in z.items():
            if ist_zahl(v):
                summen[f] = summen.get(f, 0) + v
    n = len(zeilen)
    if not anteil:
        return [(s, f"Summe {f} über {n} Zeilen") for f, s in summen.items()]
    kandidaten = [(s / n * 100, f"Mittel {f} über {n} Zeilen × 100") for f, s in summen.items()]
    kandidaten += [(summen[a] / summen[b] * 100, f"Summe {a} / Summe {b} über {n} Zeilen")
                   for a in summen for b in summen if a != b and summen[b]]
    if n == 1:
        kandidaten += [(s, f"Wert {f}") for f, s in summen.items()]
    return kandidaten


def kernwert_finden(k, quellen, sicht=None):
    """Sucht einen Kernwert in den Tabellen der Dashboard-Daten, dann im gerenderten Standardzustand (`sicht`:
    Dateiname -> sichtbarer Text). Liefert (ok|unklar|verfehlt, Fundtext)."""
    varianten = k.get("zeilen") or [[]]
    anteil = k.get("einheit") == "%"
    naechste = None
    for datei, daten, _ in quellen:
        for pfad, zeilen in tabellen(daten):
            for variante in varianten:
                treffer = [z for z in zeilen if all(bedingung_erfuellt(z, b) for b in variante)]
                if not treffer:
                    continue
                kandidaten = kernwert_kandidaten(treffer, anteil)
                for wert, wie in kandidaten:
                    if passt(wert, k):
                        return "ok", f"{wie} = {wert:g} in {datei}, {pfad}"
                if naechste is None and kandidaten and variante:
                    nah = ", ".join(f"{wie} = {wert:g}" for wert, wie in kandidaten[:3])
                    naechste = f"Zeilen zu {' / '.join(b[0] for b in variante)} in {datei}, {pfad}: {nah}"
    for datei, text in (sicht or {}).items():
        for wert, _, fund in zahlen(text or ""):
            if passt(wert, k):
                return "ok", f"im gerenderten Dashboard sichtbar: {fund} in {datei}"
    for datei, daten, rest in quellen:
        lose = list(blaetter(daten)) + [float(z) for z in re.findall(r"(?<![\w.])\d+(?:\.\d+)?(?![\w.])", rest)]
        for v in lose:
            if passt(v, k) or (anteil and abs(v) <= 1 and passt(v * 100, k)):
                return "unklar", f"Wert {v:g} nur als einzelne Zahl ohne passende Zeilen in {datei}"
    if any(sicht.values() if sicht else []) and any(k.get("zeilen") or [[]]):
        # Wert mit Bedingungen (etwa ein Programm): im Standardzustand nicht zu sehen, braucht einen Filter
        return "unklar", (naechste or "keine Zeilen in den Daten") + "; im Standardzustand nicht sichtbar, Filter nötig"
    return "verfehlt", naechste or "keine Zeilen zu den Bedingungen in den eingebetteten Daten"


def dashboard_pruefen(p, g, runde, basis):
    """Liefert (Status, Gründe, Hinweise) für die Prüfart dashboard."""
    hinweise = []
    if p.get("sekunden_max") and (runde.get("sekunden") or 0) > p["sekunden_max"]:
        hinweise.append(f"Laufzeit {runde['sekunden']:.0f} s über der Grenze von {p['sekunden_max']} s")
    namen = g.get("dateien") or []
    html = [n for n in namen if n.lower().endswith((".html", ".htm"))]
    if not html:
        return "verfehlt", ["kein Dashboard: keine .html-Datei unter den Dateien des Gesprächs"], hinweise
    ordner = basis / f"dateien-{g.get('nummer', 0):02d}"
    quellen = dashboard_quellen(ordner, html + [n for n in namen if Path(n).name == "data.json"])
    if not quellen:
        return "unklar", [f"Dateien des Gesprächs fehlen lokal unter {ordner}"], hinweise
    sicht = {n: gerendert(ordner / n) for n in html if (ordner / n).is_file()}
    status, gruende = "ok", []
    for k in p["kernwerte"]:
        ergebnis, fund = kernwert_finden(k, quellen, sicht)
        if ergebnis != "ok":
            gruende.append(f"{k.get('name', 'Kernwert')}: erwartet {erwartung_text(k)}; {fund}")
            status = "verfehlt" if ergebnis == "verfehlt" or status == "verfehlt" else "unklar"
    return status, gruende, hinweise


def fall_pruefen(fall, gespraeche, basis=Path(".")):
    g, treffer = gespraech_finden(fall, gespraeche)
    if g is None:
        return {"status": "nicht gelaufen", "gruende": []}
    if g.get("fehler"):
        return {"status": "unklar", "gruende": [f"Gespräch abgebrochen: {g['fehler'][:160]}"]}
    fehlerhaft = [r for r in g["runden"] if r.get("fehler")]
    if fehlerhaft:
        return {"status": "unklar", "gruende": [f"Runde mit Fehler: {fehlerhaft[0]['fehler'][:160]}"]}
    if treffer[0] == "teil":
        return {"status": "unklar",
                "gruende": [f"Gespräch unvollständig, im Lauf fehlt: „{treffer[1]}“ (gelaufene Runden: {len(g['runden'])})"]}
    runde = g["runden"][treffer[1]]
    antwort = runde.get("antwort") or ""
    if antwort.lstrip().startswith("[Rückfrage]"):
        return {"status": "unklar", "gruende": [f"Antwort endet mit Rückfrage: {antwort.strip()[:200]}"]}
    gruende, status, hinweise = [], "bestanden", []
    for p in fall["erwartet"]:
        name = p.get("name", p["art"])
        if p["art"] == "dashboard":
            ergebnis, mehr, notiz = dashboard_pruefen(p, g, runde, basis)
            gruende += [f"{name}: {m}" for m in mehr]
            hinweise += notiz
            if ergebnis != "ok":
                status = "verfehlt" if ergebnis == "verfehlt" else (status if status == "verfehlt" else "unklar")
        elif p["art"] == "zahl":
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
    return {"status": status, "gruende": gruende, "hinweise": hinweise}


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
            frage = [e for e in f["fragen"] if not ist_bedingt(e)][-1]
            zeilen.append(f"- **{f['id']}** ({f['rolle']}, {f['thema']}): {frage}")
            zeilen += [f"  - {g}" for g in ergebnisse[f["id"]]["gruende"]]
        zeilen.append("")
    mit_hinweis = [f for f in faelle if ergebnisse[f["id"]].get("hinweise")]
    if mit_hinweis:
        zeilen += ["## Hinweise", "", "Nur zur Kenntnis, kein Einfluss auf das Ergebnis.", ""]
        zeilen += [f"- **{f['id']}** ({ergebnisse[f['id']]['status']}): {'; '.join(ergebnisse[f['id']]['hinweise'])}"
                   for f in mit_hinweis]
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
    basis = Path(args.ergebnis).resolve().parent
    ergebnisse = {f["id"]: fall_pruefen(f, lauf.get("gespraeche", []), basis) for f in faelle}
    text = bericht(lauf, faelle, ergebnisse, args.verdeckt)
    print(text)
    if args.ausgabe:
        Path(args.ausgabe).write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
