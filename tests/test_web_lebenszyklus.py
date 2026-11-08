"""Regressionstests für den Gesprächslebenszyklus der Weboberfläche, mit Ersatzmodell statt codex app-server.

Abgesichert sind die Befunde aus dem Code-Review vom 08.11.2026:
- Nach Ruhen (Platzmangel) bekommt die Nachfrage den sichtbaren Verlauf mit.
- Eine Korrektur der Prüfrunde erreicht das Hauptgespräch vor der nächsten Frage.
- Auf eine Rückfrage läuft keine Prüfrunde.
- Dateien einer Runde ändern sich nicht, wenn eine spätere Runde sie überschreibt.
- Nach einem Fehler bleibt das Gespräch für die nächste Frage nutzbar.
Aufruf: python3 -m unittest tests/test_web_lebenszyklus.py (braucht starlette und httpx).
"""

import sys
import tempfile
import time
import unittest
from pathlib import Path

HIER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HIER))

from starlette.testclient import TestClient  # noqa: E402

from web import app as web_app, konten  # noqa: E402
from sitzung import Sitzungsfehler  # noqa: E402


class Runde:
    def __init__(self, text):
        self.text, self.items, self.token, self.sekunden, self.modellanfragen = text, [], {}, 0.1, 1


class Ersatzmodell:
    """Ein Modellprozess. `antworten` ist eine Funktion (cwd, eingabe, nummer) -> Antworttext oder Ausnahme."""

    def __init__(self, cwd, antworten, protokoll):
        self.cwd, self.antworten, self.protokoll = Path(cwd), antworten, protokoll
        self.thread_id, self._turn_id, self.eingaben, self.offen = "t", "u", [], False

    def __enter__(self):
        self.offen = True
        self.protokoll["gestartet"] += 1
        return self

    def __exit__(self, *_):
        self.offen = False

    def frage(self, text, beobachter=None):
        self.eingaben.append(text)
        self.protokoll["eingaben"].append(text)
        ergebnis = self.antworten(self.cwd, text, len(self.protokoll["eingaben"]))
        if isinstance(ergebnis, Exception):
            raise ergebnis
        return Runde(ergebnis)

    def unterbrechen(self):
        pass


class Grundlage(unittest.TestCase):
    max_gespraeche = 4

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        basis = Path(self.tmp.name)
        (basis / "gespraeche").mkdir()
        (basis / "konten.json").write_text('{"t@x": {"hash": "%s", "aktiv": true}}' % konten.hash_von("geheim"))
        self.haupt = {"gestartet": 0, "eingaben": []}
        self.pruefer = {"gestartet": 0, "eingaben": []}
        e = web_app.Einstellungen(konten=basis / "konten.json", gespraeche=basis / "gespraeche", hosts=["testserver"],
                                  sicher=False, max_gespraeche=self.max_gespraeche)
        app = web_app.erzeuge(e, gespraech_fabrik=lambda cwd: Ersatzmodell(cwd, self.antwort, self.haupt),
                              pruefer_fabrik=lambda cwd: Ersatzmodell(cwd, self.pruefung, self.pruefer))
        self.c = TestClient(app)
        self.assertEqual(self.c.post("/api/anmelden", json={"email": "t@x", "passwort": "geheim"}).status_code, 200)

    def tearDown(self):
        self.tmp.cleanup()

    def antwort(self, cwd, text, n):
        return f"Antwort {n}"

    def pruefung(self, cwd, text, n):
        return "[Prüfung: bestätigt] nachgerechnet"

    def frage(self, text, kennung=None, verifizieren=False):
        r = self.c.post("/api/fragen", json={"text": text, "gespraech": kennung, "verifizieren": verifizieren,
                                             "speichern": False})
        self.assertEqual(r.status_code, 202, r.text)
        kennung = r.json()["gespraech"]
        for _ in range(200):
            stand = self.c.get(f"/api/gespraeche/{kennung}").json()
            if stand["status"] != "laeuft":
                return kennung, stand
            time.sleep(0.02)
        self.fail("Runde endet nicht")


class Ruhen(Grundlage):
    max_gespraeche = 1

    def test_nachfrage_nach_ruhen_bekommt_verlauf(self):
        a, _ = self.frage("Wie viele Studierende?")
        self.frage("Ganz anderes Thema")  # nur ein Platz: Gespräch a ruht
        _, stand = self.frage("Und davon in Berlin?", a)
        letzte = self.haupt["eingaben"][-1]
        self.assertIn("Bisheriger Verlauf", letzte)
        self.assertIn("Wie viele Studierende?", letzte)
        self.assertIn("Antwort 1", letzte)
        self.assertEqual(self.haupt["gestartet"], 3)
        self.assertEqual(stand["status"], "fertig")


class Pruefrunde(Grundlage):
    def antwort(self, cwd, text, n):
        return "[Rückfrage] Meinst du X?" if "unklar" in text else "Es sind 100."

    def pruefung(self, cwd, text, n):
        return "[Prüfung: korrigiert]\nEs sind 80.\n---\n100 war falsch"

    def test_korrektur_erreicht_das_modell(self):
        k, stand = self.frage("Wie viele?", verifizieren=True)
        self.assertEqual(stand["runden"][-1]["antwort"], "Es sind 80.")
        self.assertEqual(stand["runden"][-1]["pruefung"]["status"], "korrigiert")
        self.frage("Und die Hälfte davon?", k)
        letzte = self.haupt["eingaben"][-1]
        self.assertIn("Es sind 80.", letzte)
        self.assertIn("Prüfrunde", letzte)

    def test_keine_pruefung_auf_rueckfrage(self):
        _, stand = self.frage("Etwas unklar", verifizieren=True)
        self.assertTrue(stand["runden"][-1]["antwort"].startswith("[Rückfrage]"))
        self.assertEqual(self.pruefer["gestartet"], 0)


class Dateien(Grundlage):
    def antwort(self, cwd, text, n):
        (cwd / "dashboard.html").write_text(f"<html><body>Stand {n}</body></html>")
        return "[Dashboard](dashboard.html)"

    def test_alte_runde_behaelt_ihre_datei(self):
        k, stand1 = self.frage("Dashboard Oktober")
        _, stand2 = self.frage("Jetzt September", k)
        url1, url2 = stand2["runden"][0]["dateien"][0]["url"], stand2["runden"][1]["dateien"][0]["url"]
        self.assertNotEqual(url1, url2)
        self.assertIn(b"Stand 1", self.c.get(url1).content)
        self.assertIn(b"Stand 2", self.c.get(url2).content)


class Fehler(Grundlage):
    def antwort(self, cwd, text, n):
        return Sitzungsfehler("Runde failed: Login abgelaufen") if n == 1 else "Antwort nach Fehler"

    def test_gespraech_bleibt_nach_fehler(self):
        k, stand = self.frage("Erste Frage")
        self.assertEqual(stand["status"], "fertig")
        self.assertIn("Login", stand["runden"][-1]["fehler"])
        _, stand = self.frage("Zweite Frage", k)
        self.assertEqual(stand["runden"][-1]["antwort"], "Antwort nach Fehler")
        self.assertEqual(self.haupt["gestartet"], 2)


if __name__ == "__main__":
    unittest.main()
