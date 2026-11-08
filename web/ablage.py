"""Beta-Ablage der Gespräche aus dem Browser, damit sie ohne den Nutzer prüfbar sind. Schalter `DWH_ABLAGE=1` in
der Unit, Rückbau vor einer echten Auslieferung.

    <wurzel>/<datum>/<gespraech>/gespraech.json        Benutzer, Versionen, Datenstand, alle Runden vollständig
    <wurzel>/<datum>/<gespraech>/dateien/<runde>/...   in der Runde erzeugte oder geänderte Dateien (Diagramme)
    <wurzel>/anweisungen/<prüfsumme>.txt               Anweisung an das Modell, je Fassung einmal
    <wurzel>/feedback/<zeit>-<zufall>.json             Rückmeldungen aus dem Beta-Menü

Je Runde: Frage, Antwort (Markdown), Zeit, Dauer, Token und jeder Schritt in Reihenfolge: SQL mit Ergebnis (Spalten
und Zeilen, so weit das Werkzeug sie liefert), Shell-Befehle mit Ausgabe, Denkzusammenfassungen, Zwischennachrichten.
`gespraech.json` wird nach jeder Runde neu geschrieben. Ordner 0700, Dateien 0600, Eigentümer ist der Dienst
(dwhv3), sonst nur root. Die Webanwendung schreibt hier nur, keine Route liest daraus.
"""

import datetime
import hashlib
import json
import os
import secrets
import shutil
import stat
import sys
from pathlib import Path

DATEI_MAX = 50_000_000  # größere Dateien bleiben liegen, das Modell könnte die Platte füllen
RUNDE_MAX = 200_000_000


def zeitstempel():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def _json_oder_text(text):
    try:
        return json.loads(text)
    except (TypeError, ValueError):
        return text


def schritt(item):
    """Ein Item der Runde vollständig, in lesbarer Form."""
    art = item.get("type")
    if art == "reasoning":
        return {"art": "denken", "text": "\n\n".join(item.get("summary") or [])}
    if art == "mcpToolCall":
        argumente = item.get("arguments") or {}
        ergebnis = item.get("result") or {}
        inhalt = [_json_oder_text(t.get("text")) for t in ergebnis.get("content") or [] if isinstance(t, dict)]
        return {"art": "sql" if item.get("tool") == "sql" else f"werkzeug {item.get('server')}.{item.get('tool')}",
                "abfrage": argumente.get("abfrage", argumente), "status": item.get("status"),
                "ergebnis": inhalt[0] if len(inhalt) == 1 else inhalt, "fehler": item.get("error"),
                "dauer_ms": item.get("durationMs")}
    if art == "commandExecution":
        return {"art": "befehl", "befehl": item.get("command"), "status": item.get("status"),
                "exitcode": item.get("exitCode"), "ausgabe": item.get("aggregatedOutput"),
                "dauer_ms": item.get("durationMs")}
    if art == "agentMessage":
        return {"art": "antwort" if item.get("phase") == "final_answer" else "nachricht", "text": item.get("text")}
    if art == "fileChange":
        return {"art": "dateiaenderung", "aenderungen": item.get("changes")}
    if art == "userMessage":
        return None
    return {"art": art, "roh": item}


def dateistand(cwd):
    """Sichtbare Dateien des Gesprächsverzeichnisses mit Änderungsmerkmal, ohne versteckte und ohne Symlinks."""
    stand = {}
    cwd = Path(cwd)
    try:
        pfade = list(cwd.rglob("*"))
    except OSError:
        return stand
    for pfad in pfade:
        relativ = pfad.relative_to(cwd)
        if any(teil.startswith(".") for teil in relativ.parts):
            continue
        try:
            info = pfad.lstat()
        except OSError:
            continue
        if stat.S_ISREG(info.st_mode):
            stand[relativ.as_posix()] = (info.st_mtime_ns, info.st_size)
    return stand


def neue_dateien(vorher, jetzt):
    return sorted(name for name, merkmal in jetzt.items() if vorher.get(name) != merkmal)


class Ablage:
    def __init__(self, wurzel):
        self.wurzel = Path(wurzel)

    def _ordner(self, *teile):
        """Jede Stufe einzeln mit 0700, mkdir mit parents gäbe den Zwischenstufen die Umask."""
        pfad = self.wurzel
        pfad.mkdir(mode=0o700, parents=True, exist_ok=True)
        for teil in teile:
            pfad = pfad / teil
            pfad.mkdir(mode=0o700, exist_ok=True)
        return pfad

    @staticmethod
    def _schreibe(pfad, inhalt):
        """Erst in eine temporäre Datei, dann umbenennen: Wer liest, sieht nie eine halbe Datei."""
        zwischen = pfad.with_name(f".{pfad.name}.{secrets.token_hex(4)}")
        with os.fdopen(os.open(zwischen, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb") as datei:
            if isinstance(inhalt, bytes):
                datei.write(inhalt)
            else:
                shutil.copyfileobj(inhalt, datei)
        os.replace(zwischen, pfad)

    @staticmethod
    def _json(daten):
        return json.dumps(daten, ensure_ascii=False, indent=1).encode()

    def anweisung(self, text):
        pruefsumme = hashlib.sha256(text.encode()).hexdigest()[:16]
        pfad = self._ordner("anweisungen") / f"{pruefsumme}.txt"
        if not pfad.exists():
            self._schreibe(pfad, text.encode())
        return pruefsumme

    def gespraech(self, datum, kennung, daten):
        self._schreibe(self._ordner(datum, kennung) / "gespraech.json", self._json(daten))

    def dateien(self, datum, kennung, nummer, namen, oeffne):
        """Kopiert Dateien einer Runde, `oeffne(name)` folgt keinen Verweisen. Liefert die abgelegten Namen."""
        ziel = self.wurzel / datum / kennung / "dateien" / str(nummer)
        abgelegt, summe = [], 0
        for name in namen:
            datei = oeffne(name)
            if datei is None:
                continue
            with datei:
                groesse = os.fstat(datei.fileno()).st_size
                if groesse > DATEI_MAX or summe + groesse > RUNDE_MAX:
                    continue
                pfad = ziel / name
                if ".." in Path(name).parts:
                    continue
                self._ordner(*pfad.parent.relative_to(self.wurzel).parts)
                self._schreibe(pfad, datei)
            summe += groesse
            abgelegt.append(name)
        return abgelegt

    def feedback(self, daten):
        name = f"{datetime.datetime.now().strftime('%Y%m%dT%H%M%S')}-{secrets.token_hex(4)}.json"
        self._schreibe(self._ordner("feedback") / name, self._json(daten))
        return name


def melde(fehler):
    """Ein Fehler der Ablage stört das Gespräch nicht, er geht ins Journal der Unit."""
    print(f"ablage: {type(fehler).__name__}: {str(fehler)[:300]}", file=sys.stderr, flush=True)
