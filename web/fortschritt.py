"""Fortschritt einer Runde für die Oberfläche, aus den Ereignissen des app-servers (Parameter `beobachter`).

Schritte in Klartext: die Überschriften der Denkzusammenfassungen, Datenabfragen mit ihrem Ergebnis in Zeilen,
das Nachschlagen in Katalog und SAE-Wissen. Kein SQL, keine Befehle. Stufen schreiten nur vorwärts:
Frage verstehen, Daten abfragen, auswerten, Antwort schreiben, mit Prüfrunde zuletzt prüfen. Während der Prüfrunde
kommen die Ereignisse vom Prüfgespräch: Sie ergänzen die Schritte, ändern die Stufe aber nicht mehr.
"""

import json
import re
import threading
import time

STUFEN = ("verstehen", "abfragen", "analysieren", "schreiben")
FETT = re.compile(r"\*\*(.+?)\*\*")


def _ueberschrift(text):
    """Überschrift einer Denkzusammenfassung: der fette Titel, sonst der erste Satz, höchstens 120 Zeichen."""
    text = (text or "").strip()
    treffer = FETT.search(text)
    kurz = treffer.group(1) if treffer else re.split(r"(?<=[.!?])\s|\n", text, maxsplit=1)[0]
    kurz = kurz.strip().rstrip(".:")
    return kurz if len(kurz) <= 120 else kurz[:119] + "…"


def _zeilen(item):
    """Zeilenzahl aus dem Ergebnis des Werkzeugs sql, None wenn unbekannt, -1 bei Fehler."""
    if item.get("status") == "failed" or item.get("error"):
        return -1
    for teil in ((item.get("result") or {}).get("content") or []):
        try:
            daten = json.loads(teil.get("text", ""))
        except (ValueError, AttributeError, TypeError):
            continue
        if isinstance(daten, dict):
            if daten.get("fehler"):
                return -1
            if isinstance(daten.get("zeilen"), list):
                return len(daten["zeilen"])
    return None


class Fortschritt:
    def __init__(self, uhr=time.monotonic, pruefen=False):
        self.uhr = uhr
        self.namen = STUFEN + (("pruefen",) if pruefen else ())
        self._pruefung = False
        self.start = uhr()
        self.schritte = []
        self._stufe = 0
        self._sql = 0
        self._sql_offen = 0
        self._nummern = {}  # Kennung des Aufrufs -> Nummer der Abfrage, Abfragen laufen auch parallel
        self._sperre = threading.Lock()

    def sekunden(self):
        return round(self.uhr() - self.start, 1)

    def _schritt(self, text):
        if text and (not self.schritte or self.schritte[-1]["text"] != text):
            self.schritte.append({"s": int(self.uhr() - self.start), "text": text})

    def pruefung_beginnt(self):
        with self._sperre:
            self._pruefung = True
            self._stufe = self.namen.index("pruefen")
            self._schritt("A second analyst is re-checking the answer")

    def ereignis(self, n, turn_id):
        m, p = n.get("method"), n.get("params") or {}
        if p.get("turnId") != turn_id or m not in ("item/started", "item/completed"):
            return
        item = p.get("item") or {}
        art = item.get("type")
        with self._sperre:
            if art == "mcpToolCall" and item.get("server", "dwh") == "dwh":
                if m == "item/started":
                    self._sql += 1
                    self._sql_offen += 1
                    self._nummern[item.get("id")] = self._sql
                    if not self._pruefung:
                        self._stufe = max(self._stufe, 1)
                    self._schritt(f"Querying the data warehouse (query {self._sql})")
                else:
                    self._sql_offen = max(0, self._sql_offen - 1)
                    nummer = self._nummern.get(item.get("id"), self._sql)
                    zeilen = _zeilen(item)
                    if zeilen == -1:
                        self._schritt(f"Query {nummer} failed, adjusting")
                    elif zeilen is not None:
                        self._schritt(f"Query {nummer} returned {zeilen} {'row' if zeilen == 1 else 'rows'}")
            elif art == "reasoning" and m == "item/completed":
                for text in item.get("summary") or []:
                    self._schritt(_ueberschrift(text))
                if self._stufe == 1 and not self._sql_offen and not self._pruefung:
                    self._stufe = 2
            elif art == "commandExecution" and m == "item/started":
                befehl = str(item.get("command", ""))
                if "/katalog" in befehl:
                    self._schritt("Looking up definitions in the catalogue")
                elif "/wissen" in befehl:
                    self._schritt("Looking up SAE knowledge")
            elif art == "agentMessage" and m == "item/started" and item.get("phase") == "final_answer":
                if self._pruefung:
                    self._schritt("Finishing the check")
                else:
                    self._stufe = 3
                    self._schritt("Writing the answer")

    def stufen(self, fertig=False):
        with self._sperre:
            stufe = len(self.namen) if fertig else self._stufe
            aus = []
            for i, name in enumerate(self.namen):
                if i < stufe:
                    status = "uebersprungen" if name in ("abfragen", "analysieren") and not self._sql else "erledigt"
                else:
                    status = "aktiv" if i == stufe else "offen"
                aus.append({"stufe": name, "status": status})
            return aus
