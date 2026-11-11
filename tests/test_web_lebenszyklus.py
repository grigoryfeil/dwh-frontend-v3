"""Regressionstests für den Gesprächslebenszyklus der Weboberfläche, mit Ersatzmodell statt codex app-server.

Abgesichert sind die Befunde aus dem Code-Review vom 08.11.2026:
- Nach Ruhen (Platzmangel) bekommt die Nachfrage den sichtbaren Verlauf mit.
- Eine Korrektur der Prüfrunde erreicht das Hauptgespräch vor der nächsten Frage.
- Auf eine Rückfrage läuft keine Prüfrunde.
- Dateien einer Runde ändern sich nicht, wenn eine spätere Runde sie überschreibt.
- Nach einem Fehler bleibt das Gespräch für die nächste Frage nutzbar.
- Eine Korrektur der Prüfrunde liefert ihre eigene Datei aus.
- Kopien für den Prüfer und zurück folgen keinem Symlink des Modells.
- Der Verlaufsvorspann nach einer Pause ist begrenzt, ebenso die Zahl behaltener Gespräche.
- Hängt eine Runde nach dem Abbruch, beendet die Notbremse nur den Prozess, das Gespräch bleibt nutzbar.
Dazu die Befunde der Durchsicht vom 10.11.2026:
- Scheitert die Nachverarbeitung einer Runde, endet sie trotzdem und gilt nicht für immer als laufend.
- Abmelden während einer Runde beendet auch den Prüfer und einen Prozess, der gerade erst startet.
Aufruf: python3 -m unittest tests/test_web_lebenszyklus.py (braucht starlette und httpx).
"""

import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

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
    max_behalten = 24
    abbruch_frist = 30

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        basis = self.basis = Path(self.tmp.name)
        (basis / "gespraeche").mkdir()
        (basis / "konten.json").write_text('{"t@x": {"hash": "%s", "aktiv": true}}' % konten.hash_von("geheim"))
        self.haupt = {"gestartet": 0, "eingaben": []}
        self.pruefer = {"gestartet": 0, "eingaben": []}
        e = web_app.Einstellungen(konten=basis / "konten.json", gespraeche=basis / "gespraeche", hosts=["testserver"],
                                  sicher=False, max_gespraeche=self.max_gespraeche, max_behalten=self.max_behalten,
                                  abbruch_frist=self.abbruch_frist, **self.einstellungen(basis))
        app = web_app.erzeuge(e, gespraech_fabrik=lambda cwd: Ersatzmodell(cwd, self.antwort, self.haupt),
                              pruefer_fabrik=lambda cwd: Ersatzmodell(cwd, self.pruefung, self.pruefer))
        self.c = TestClient(app)
        self.assertEqual(self.c.post("/api/anmelden", json={"email": "t@x", "passwort": "geheim"}).status_code, 200)

    def tearDown(self):
        self.tmp.cleanup()

    def einstellungen(self, basis):
        """Weitere Einstellungen einer Testklasse, etwa die Beta-Ablage (tests/test_web_ablage.py)."""
        return {}

    def antwort(self, cwd, text, n):
        return f"Antwort {n}"

    def pruefung(self, cwd, text, n):
        return "[Prüfung: bestätigt] nachgerechnet"

    def frage(self, text, kennung=None, verifizieren=False, speichern=False):
        r = self.c.post("/api/fragen", json={"text": text, "gespraech": kennung, "verifizieren": verifizieren,
                                             "speichern": speichern})
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


class PruefDatei(Grundlage):
    def antwort(self, cwd, text, n):
        (cwd / "dashboard.html").write_text("<html>Stand 100</html>")
        return "Es sind 100. [Dashboard](dashboard.html)"

    def pruefung(self, cwd, text, n):
        self.assertIn("100", (cwd / "dashboard.html").read_text())  # der Prüfer bekam die Kopie
        (cwd / "dashboard.html").write_text("<html>Stand 80</html>")
        return "[Prüfung: korrigiert]\nEs sind 80. [Dashboard](dashboard.html)\n---\n100 war falsch"

    def test_korrektur_liefert_ihre_datei(self):
        _, stand = self.frage("Dashboard bitte", verifizieren=True)
        url = stand["runden"][-1]["dateien"][0]["url"]
        self.assertIn(b"Stand 80", self.c.get(url).content)


class Symlinks(Grundlage):
    def setUp(self):
        super().setUp()
        self.aussen = self.basis / "aussen"
        self.aussen.mkdir()
        (self.aussen / "geheim.txt").write_text("unverändert")

    def antwort(self, cwd, text, n):
        (cwd / "bericht.html").symlink_to(self.aussen / "geheim.txt")  # Falle für die Rückübernahme
        (cwd / "pruefung").symlink_to(self.aussen)  # Falle für das Prüferverzeichnis
        (cwd / "dashboard.html").write_text("<html>Stand 100</html>")
        return "[Dashboard](dashboard.html)"

    def pruefung(self, cwd, text, n):
        (cwd / "bericht.html").write_text("<html>neu</html>")
        return "[Prüfung: korrigiert]\n[Bericht](bericht.html)\n---\nanderer Bericht"

    def test_keinem_symlink_gefolgt(self):
        self.frage("Dashboard bitte", verifizieren=True)
        self.assertEqual((self.aussen / "geheim.txt").read_text(), "unverändert")
        self.assertEqual(sorted(p.name for p in self.aussen.iterdir()), ["geheim.txt"])


class Verlaufsgrenze(Grundlage):
    max_gespraeche = 1

    def antwort(self, cwd, text, n):
        return "x" * 6000

    def test_vorspann_begrenzt(self):
        a = None
        for i in range(8):
            a, _ = self.frage(f"Frage {i}", a)
        self.frage("Anderes Gespräch")
        self.frage("Nachfrage", a)
        letzte = self.haupt["eingaben"][-1]
        self.assertIn("älteren Runden ausgelassen", letzte)
        self.assertNotIn("Frage 0", letzte)
        self.assertLess(len(letzte), 6 * 4200 + 2000)


class Behalten(Grundlage):
    max_gespraeche = 1
    max_behalten = 2

    def test_aelteste_ruhende_enden(self):
        erste, _ = self.frage("Eins")
        self.frage("Zwei")
        self.frage("Drei")
        self.assertEqual(self.c.get(f"/api/gespraeche/{erste}").status_code, 404)


class Haengendes(Ersatzmodell):
    """Ignoriert den Abbruch und endet erst, wenn der Prozess beendet wird (Notbremse)."""

    def __enter__(self):
        self.beendet = threading.Event()
        return super().__enter__()

    def __exit__(self, *_):
        self.beendet.set()
        super().__exit__()

    def frage(self, text, beobachter=None):
        self.protokoll["eingaben"].append(text)
        if len(self.protokoll["eingaben"]) == 1:
            self.beendet.wait(5)
            raise Sitzungsfehler("app-server beendet")
        return Runde("Antwort nach Notbremse")


class Notbremse(Grundlage):
    abbruch_frist = 0.2

    def setUp(self):
        super().setUp()  # dann mit eigener Fabrik für das hängende Modell neu aufsetzen
        e = web_app.Einstellungen(konten=self.basis / "konten.json", gespraeche=self.basis / "gespraeche",
                                  hosts=["testserver"], sicher=False, abbruch_frist=0.2)
        self.c = TestClient(web_app.erzeuge(e, gespraech_fabrik=lambda cwd: Haengendes(cwd, None, self.haupt)))
        self.assertEqual(self.c.post("/api/anmelden", json={"email": "t@x", "passwort": "geheim"}).status_code, 200)

    def test_gespraech_bleibt_nach_notbremse(self):
        r = self.c.post("/api/fragen", json={"text": "Erste", "gespraech": None, "verifizieren": False,
                                             "speichern": False})
        k = r.json()["gespraech"]
        time.sleep(0.1)
        self.assertEqual(self.c.post(f"/api/gespraeche/{k}/abbrechen", json={}).status_code, 202)
        for _ in range(100):
            stand = self.c.get(f"/api/gespraeche/{k}").json()
            if stand["status"] != "laeuft":
                break
            time.sleep(0.05)
        self.assertEqual(stand["status"], "fertig")
        _, stand = self.frage("Zweite", k)
        self.assertEqual(stand["runden"][-1]["antwort"], "Antwort nach Notbremse")
        self.assertEqual(self.haupt["gestartet"], 2)


class Nachverarbeitung(Grundlage):
    def antwort(self, cwd, text, n):
        (cwd / "dashboard.html").write_text("<html>Stand</html>")
        return "[Dashboard](dashboard.html)"

    def test_runde_endet_ohne_rundensicherung(self):
        (self.basis / "runden").write_text("")  # Sicherungsort lässt sich nicht anlegen, wie bei voller Platte
        _, stand = self.frage("Dashboard bitte")
        self.assertEqual(stand["status"], "fertig")
        url = stand["runden"][-1]["dateien"][0]["url"]
        self.assertIn(b"Stand", self.c.get(url).content)  # ohne Sicherung gilt der aktuelle Stand

    def test_unerwarteter_fehler_gibt_die_runde_frei(self):
        with mock.patch.object(web_app.dateien, "uebersetze", side_effect=RuntimeError("kaputt")):
            k, stand = self.frage("Dashboard bitte")
        self.assertEqual(stand["status"], "fertig")
        self.assertEqual(stand["runden"][-1]["fehler"], "interner Fehler")
        _, stand = self.frage("Noch einmal", k)
        self.assertEqual(len(stand["runden"][-1]["dateien"]), 1)
        self.assertEqual(self.haupt["gestartet"], 2)


class Startend(Ersatzmodell):
    """Fährt noch hoch, während das Gespräch geschlossen wird, und legt dabei wie der echte Prozess `.tmp` an."""

    def __init__(self, cwd, antworten, protokoll, startet, weiter):
        super().__init__(cwd, antworten, protokoll)
        self.startet, self.weiter = startet, weiter

    def __enter__(self):
        self.startet.set()
        self.weiter.wait(5)
        (self.cwd / ".tmp").mkdir(parents=True, exist_ok=True)
        return super().__enter__()


class Abmelden(Grundlage):
    def neu(self, **fabriken):
        e = web_app.Einstellungen(konten=self.basis / "konten.json", gespraeche=self.basis / "gespraeche",
                                  hosts=["testserver"], sicher=False)
        self.c = TestClient(web_app.erzeuge(e, **fabriken))
        self.assertEqual(self.c.post("/api/anmelden", json={"email": "t@x", "passwort": "geheim"}).status_code, 200)

    def stelle(self, verifizieren):
        r = self.c.post("/api/fragen", json={"text": "Wie viele?", "gespraech": None, "verifizieren": verifizieren,
                                             "speichern": False})
        self.assertEqual(r.status_code, 202, r.text)
        return r.json()["gespraech"]

    def warte(self, bedingung):
        for _ in range(100):
            if bedingung():
                return True
            time.sleep(0.02)
        return False

    def test_abmelden_beendet_den_pruefer(self):
        pruefer = []
        self.neu(gespraech_fabrik=lambda cwd: Ersatzmodell(cwd, self.antwort, self.haupt),
                 pruefer_fabrik=lambda cwd: pruefer.append(Haengendes(cwd, None, self.pruefer)) or pruefer[-1])
        self.stelle(verifizieren=True)
        self.assertTrue(self.warte(lambda: self.pruefer["eingaben"]))  # der Prüfer rechnet
        self.assertEqual(self.c.post("/api/abmelden", json={}).status_code, 204)
        self.assertTrue(pruefer[0].beendet.wait(1))

    def test_abmelden_beim_start_hinterlaesst_nichts(self):
        startet, weiter, modelle = threading.Event(), threading.Event(), []
        self.neu(gespraech_fabrik=lambda cwd: modelle.append(Startend(cwd, self.antwort, self.haupt, startet, weiter))
                 or modelle[-1])
        k = self.stelle(verifizieren=False)
        self.assertTrue(startet.wait(2))
        self.assertEqual(self.c.post("/api/abmelden", json={}).status_code, 204)
        weiter.set()
        ort = self.basis / "gespraeche" / f"web-{k}"
        self.assertTrue(self.warte(lambda: self.haupt["gestartet"] == 1), "Prozess nicht gestartet")
        self.assertTrue(self.warte(lambda: not modelle[0].offen and not ort.exists()), "Prozess oder Verzeichnis bleibt")
        self.assertEqual(self.haupt["eingaben"], [])


if __name__ == "__main__":
    unittest.main()
