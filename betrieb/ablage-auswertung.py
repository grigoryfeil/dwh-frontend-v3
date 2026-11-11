"""Auswertung der Beta-Ablage, als root auf dem VPS.

Liest die Gespräche und Rückmeldungen eines Zeitraums aus der Ablage (web/ablage.py) und schreibt:
- einen Bericht (Markdown) mit Kennzahlen, der Nutzung je Nutzer und Sitzung (Nutzerlog, nur Sitzungen mit
  eingeschaltetem Speichern) und je Runde Frage, Ergebnis, Dauer, Auffälligkeiten,
- eine Fragendatei für harness/lauf.py mit den auffälligen Gesprächen (Rückmeldung, Fehler, Abbruch, sehr lang).
  Aus ihnen werden neue Referenzfälle, nachdem ein Mensch die richtige Antwort belegt hat.
Beides landet unter /var/lib/dwh-frontend-v3/laeufe/ (root, nicht im Bereich der Modell-Shell, nicht in git).

Aufruf: python3 -I ablage-auswertung.py [von JJJJ-MM-TT] [bis JJJJ-MM-TT]   (ohne Angabe: alles)
"""
import collections, datetime, json, sys
from pathlib import Path

ABLAGE = Path("/var/lib/dwh-frontend-v3/ablage")
ZIEL = Path("/var/lib/dwh-frontend-v3/laeufe")
LANG_S = 600


def im_zeitraum(tag, von, bis):
    return (not von or tag >= von) and (not bis or tag <= bis)


def lies_nutzung(von, bis):
    zeilen = []
    for datei in sorted((ABLAGE / "nutzung").glob("20??-??.jsonl")):
        try:
            text = datei.read_text(encoding="utf-8")
        except OSError:
            continue
        for zeile in text.splitlines():
            try:
                zeilen.append(json.loads(zeile))
            except ValueError:  # eine beim Absturz halb geschriebene Zeile
                pass
    return [z for z in zeilen if im_zeitraum((z.get("zeit") or "")[:10], von, bis)]


def minuten(sekunden):
    return f"{sekunden / 60:.0f} min"


def nutzung(zeilen):
    """Abschnitt Nutzung aus den Zeilen des Nutzerlogs: je Nutzer eine Summe, je Sitzung eine Zeile."""
    zeilen = sorted(zeilen, key=lambda z: z.get("zeit") or "")
    starts = [z["zeit"] for z in zeilen if z.get("ereignis") == "dienststart"]
    sitzungen = collections.defaultdict(list)
    for z in zeilen:
        if z.get("sitzung"):
            sitzungen[z["sitzung"]].append(z)
    tabelle, je_nutzer = [], collections.defaultdict(collections.Counter)
    for ereignisse in sitzungen.values():
        nutzer = ereignisse[0].get("benutzer", "?")
        ende = next((z for z in ereignisse if z["ereignis"] == "ende"), None)
        beginn = ende["beginn"] if ende else ereignisse[0]["zeit"]
        letzte = ereignisse[-1]["zeit"]
        if ende:
            aktiv, grund = ende.get("aktiv_s") or 0, ende.get("grund", "?")
        else:  # ohne Ende im Log: noch offen, oder der Dienst endete hart, dann zählt das letzte Ereignis
            aktiv = (datetime.datetime.fromisoformat(letzte) - datetime.datetime.fromisoformat(beginn)).total_seconds()
            grund = "dienst neu gestartet" if any(s > letzte for s in starts) else "offen"
        runden = [z for z in ereignisse if z["ereignis"] == "runde"]
        gespraeche = {z["gespraech"] for z in ereignisse if z["ereignis"] in ("speichern", "runde")}
        rueck = sum(z["ereignis"] == "feedback" for z in ereignisse)
        je_nutzer[nutzer].update(sitzungen=1, aktiv=aktiv, gespraeche=len(gespraeche), runden=len(runden),
                                 rueckmeldungen=rueck, rechenzeit=sum(z.get("sekunden") or 0 for z in runden))
        tabelle.append(f"| {beginn[:16].replace('T', ' ')} | {nutzer} | {minuten(aktiv)} | {grund} | "
                       f"{len(gespraeche)} | {len(runden)} | {rueck} |")
    if not tabelle:
        return ["\n## Nutzung\n", "Keine Sitzung mit eingeschaltetem Speichern im Zeitraum.\n"]
    aus = ["\n## Nutzung\n",
           "Nur Sitzungen, in denen ein Gespräch mit eingeschaltetem Speichern lief. Aktive Zeit: Anmeldung bis letzte "
           "Anfrage. Runden: nur aus Gesprächen mit eingeschaltetem Schalter.\n",
           "| Nutzer | Sitzungen | aktive Zeit | Gespräche | Runden | Wartezeit auf Antworten | Rückmeldungen |",
           "|---|---:|---:|---:|---:|---:|---:|"]
    aus += [f"| {n} | {c['sitzungen']} | {minuten(c['aktiv'])} | {c['gespraeche']} | {c['runden']} | "
            f"{minuten(c['rechenzeit'])} | {c['rueckmeldungen']} |" for n, c in sorted(je_nutzer.items())]
    aus += ["\n### Sitzungen\n", "| Beginn | Nutzer | aktiv | Ende | Gespräche | Runden | Rückmeldungen |",
            "|---|---|---:|---|---:|---:|---:|"] + sorted(tabelle)
    return aus + [""]


def main():
    von = sys.argv[1] if len(sys.argv) > 1 else ""
    bis = sys.argv[2] if len(sys.argv) > 2 else ""
    gespraeche = []
    for datei in sorted(ABLAGE.glob("20??-??-??/*/gespraech.json")):
        if im_zeitraum(datei.parent.parent.name, von, bis):
            try:
                gespraeche.append(json.loads(datei.read_text(encoding="utf-8")))
            except (OSError, ValueError):
                pass
    rueckmeldungen = []
    for datei in sorted((ABLAGE / "feedback").glob("*.json")):
        try:
            f = json.loads(datei.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if im_zeitraum((f.get("zeit") or "")[:10], von, bis):
            rueckmeldungen.append(f)
    zu_gespraech = collections.defaultdict(list)
    for f in rueckmeldungen:
        if f.get("gespraech"):
            zu_gespraech[f["gespraech"]].append(f)

    zaehler = collections.Counter()
    dauern, zeilen, auffaellig = [], [], []
    for g in gespraeche:
        kennung = g.get("gespraech", "?")
        zeilen.append(f"\n## Gespräch {kennung[:8]} ({g.get('begonnen', '')[:16]}, V3 {g.get('version', '?')})\n")
        gruende_gespraech = []
        for r in g.get("runden", []):
            zaehler["runden"] += 1
            status = r.get("status") or "?"
            zaehler[f"status {status}"] += 1
            sek = r.get("sekunden") or 0
            dauern.append(sek)
            antwort = r.get("antwort") or ""
            schritte = r.get("schritte") or []
            sql_fehler = sum(1 for s in schritte if s.get("art") == "sql" and (s.get("fehler") or
                             (isinstance(s.get("ergebnis"), dict) and s["ergebnis"].get("fehler"))))
            merk = []
            if antwort.lstrip().startswith("[Rückfrage]"):
                merk.append("Rückfrage"); zaehler["rueckfragen"] += 1
            if r.get("verifizieren"):
                zaehler["mit pruefrunde"] += 1
            if status != "fertig":
                merk.append(status); gruende_gespraech.append(status)
            if sek > LANG_S:
                merk.append(f"lang ({sek / 60:.0f} min)"); gruende_gespraech.append("lang")
            if sql_fehler:
                merk.append(f"{sql_fehler} SQL-Fehler"); zaehler["sql-fehler"] += sql_fehler
            if r.get("dateien"):
                merk.append(f"{len(r['dateien'])} Datei(en)"); zaehler["mit dateien"] += 1
            zeilen.append(f"- **{r.get('frage', '')[:300]}**  \n  {status}, {sek:.0f} s"
                          + (f", {', '.join(merk)}" if merk else "")
                          + f"  \n  {antwort.strip()[:400].replace(chr(10), ' ')}\n")
        for f in zu_gespraech.get(kennung, []):
            zeilen.append(f"> Rückmeldung ({f.get('zeit', '')[:16]}, {f.get('benutzer', '?')}): {f.get('text', '')}\n")
            gruende_gespraech.append("Rückmeldung")
        if gruende_gespraech:
            fragen = [r.get("frage", "") for r in g.get("runden", []) if r.get("frage")]
            auffaellig.append({"gespraech": kennung, "gruende": sorted(set(gruende_gespraech)), "fragen": fragen})

    ohne = [f for f in rueckmeldungen if not f.get("gespraech")]
    sortiert = sorted(dauern)
    median = sortiert[len(sortiert) // 2] if sortiert else 0
    kopf = [f"# Beta-Ablage {von or 'Anfang'} bis {bis or 'heute'}\n",
            f"{len(gespraeche)} Gespräche, {zaehler['runden']} Runden, {len(rueckmeldungen)} Rückmeldungen, "
            f"Median {median:.0f} s je Runde, {sum(1 for d in dauern if d > LANG_S)} Runden über {LANG_S // 60} min.\n",
            "| Merkmal | Anzahl |\n|---|---:|"]
    kopf += [f"| {k} | {v} |" for k, v in sorted(zaehler.items())]
    kopf.append(f"\n{len(auffaellig)} auffällige Gespräche stehen in der Fragendatei.\n")
    kopf += nutzung(lies_nutzung(von, bis))
    if ohne:
        kopf.append("\n## Rückmeldungen ohne Gespräch\n")
        kopf += [f"- {f.get('zeit', '')[:16]}, {f.get('benutzer', '?')}: {f.get('text', '')}" for f in ohne]

    stempel = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    bericht = ZIEL / f"ablage-{stempel}.md"
    fragen = ZIEL / f"ablage-{stempel}-fragen.json"
    bericht.write_text("\n".join(kopf + zeilen) + "\n", encoding="utf-8")
    fragen.write_text(json.dumps([a["fragen"] for a in auffaellig], ensure_ascii=False, indent=1), encoding="utf-8")
    (ZIEL / f"ablage-{stempel}-auffaellig.json").write_text(json.dumps(auffaellig, ensure_ascii=False, indent=1),
                                                            encoding="utf-8")
    print(bericht)
    print(fragen)


if __name__ == "__main__":
    main()
