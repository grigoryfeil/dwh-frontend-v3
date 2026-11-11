"""Tests der Beta-Ablage (web/ablage.py) und ihrer Anbindung in web/app.py, mit Ersatzmodell.

Abgesichert ist, was die Beta verlangt (11.11.2026):
- Eine Sitzung steht nur im Nutzerlog, wenn in ihr ein Gespräch mit eingeschaltetem Speichern lief. Dann stehen dort
  auch die Anmeldung von vorher, die Runden, das Feedback und das Ende mit Grund und Dauer.
- Runden stehen nur im Nutzerlog und in der Ablage, solange der Schalter ihres Gesprächs an ist.
- Ein Feedback geht nie verloren und nennt genau das, was in der Ablage steht: mit und ohne Gespräch, bei laufender
  Runde und wenn das Sichern des Gesprächs scheitert.
- Auch eine unerwartet gescheiterte Runde steht in der Ablage.
- Ein geordnetes Ende des Dienstes schließt die Sitzungen im Nutzerlog.
- Schreiben hinterlässt keine halben Dateien, Ordner und Dateien gehören nur dem Dienst.
Aufruf: python3 -m unittest tests/test_web_ablage.py (braucht starlette und httpx).
"""

import importlib.util
import json
import stat
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

from tests.test_web_lebenszyklus import Grundlage  # noqa: E402
from web import ablage as ablage_modul, app as web_app  # noqa: E402

ANMELDUNG = {"email": "t@x", "passwort": "geheim"}


class MitAblage(Grundlage):
    def einstellungen(self, basis):
        return {"ablage": basis / "ablage"}

    def warte(self, bedingung, text="Bedingung tritt nicht ein"):
        for _ in range(200):
            if bedingung():
                return
            time.sleep(0.02)
        self.fail(text)

    def nutzung(self, *ereignisse):
        """Zeilen des Nutzerlogs in Schreibreihenfolge, auf Wunsch nur bestimmte Ereignisse."""
        zeilen = [json.loads(z) for datei in sorted((self.basis / "ablage" / "nutzung").glob("*.jsonl"))
                  for z in datei.read_text().splitlines()]
        return [z for z in zeilen if not ereignisse or z["ereignis"] in ereignisse]

    def gespraech(self, kennung):
        dateien = list((self.basis / "ablage").glob(f"20??-??-??/{kennung}/gespraech.json"))
        return json.loads(dateien[0].read_text()) if dateien else None

    def sende_feedback(self, text, kennung=None, mitsenden=True):
        r = self.c.post("/api/feedback", json={"text": text, "gespraech": kennung, "mitsenden": mitsenden})
        self.assertEqual(r.status_code, 201, r.text)
        return json.loads((self.basis / "ablage" / "feedback" / r.json()["feedback"]).read_text())


class Nutzerlog(MitAblage):
    def test_ohne_speichern_keine_spur(self):
        k, _ = self.frage("Wie viele Studierende?")
        self.assertEqual(self.c.post("/api/abmelden", json={}).status_code, 204)
        self.assertEqual([z["ereignis"] for z in self.nutzung()], ["dienststart"])
        self.assertIsNone(self.gespraech(k))

    def test_mit_speichern_steht_die_sitzung_im_log(self):
        k, _ = self.frage("Wie viele Studierende?", speichern=True)
        self.warte(lambda: self.nutzung("runde"))
        self.assertEqual(self.c.post("/api/abmelden", json={}).status_code, 204)
        zeilen = self.nutzung()
        self.assertEqual([z["ereignis"] for z in zeilen], ["dienststart", "anmeldung", "speichern", "runde", "ende"])
        anmeldung, schalter, runde, ende = zeilen[1:]
        self.assertEqual({z["sitzung"] for z in zeilen[1:]}, {anmeldung["sitzung"]})
        self.assertEqual({z["benutzer"] for z in zeilen[1:]}, {"t@x"})
        self.assertEqual((schalter["gespraech"], schalter["an"]), (k, True))
        self.assertEqual((runde["gespraech"], runde["runde"], runde["status"], runde["gesichert"]),
                         (k, 1, "fertig", True))
        self.assertEqual(ende["grund"], "abmeldung")
        self.assertEqual(ende["beginn"], anmeldung["zeit"])
        self.assertGreaterEqual(ende["aktiv_s"], 0)
        abgelegt = self.gespraech(k)
        self.assertEqual((abgelegt["sitzung"], abgelegt["benutzer"]), (anmeldung["sitzung"], "t@x"))
        self.assertEqual([r["frage"] for r in abgelegt["runden"]], ["Wie viele Studierende?"])
        self.assertNotIn("Wie viele", json.dumps(zeilen))  # das Log enthält keine Inhalte

    def test_spaeter_eingeschaltet_traegt_die_anmeldung_nach(self):
        k, _ = self.frage("Erste Frage")
        self.assertEqual(self.nutzung("anmeldung"), [])
        self.assertEqual(self.c.post(f"/api/gespraeche/{k}/speichern", json={"an": True}).status_code, 200)
        self.assertEqual(len(self.nutzung("anmeldung")), 1)
        self.assertEqual(len(self.gespraech(k)["runden"]), 1)
        self.assertEqual(self.nutzung("runde"), [])  # die erste Runde endete bei ausgeschaltetem Schalter

    def test_abgeschaltetes_gespraech_bleibt_ohne_runden(self):
        k, _ = self.frage("Erste Frage", speichern=True)
        self.warte(lambda: self.nutzung("runde"))
        self.frage("Zweite Frage", k, speichern=False)
        time.sleep(0.1)
        self.assertEqual([z["an"] for z in self.nutzung("speichern")], [True, False])
        self.assertEqual([z["runde"] for z in self.nutzung("runde")], [1])
        self.assertEqual(len(self.gespraech(k)["runden"]), 1)

    def test_nur_dienst_darf_lesen(self):
        self.frage("Wie viele Studierende?", speichern=True)
        self.warte(lambda: self.nutzung("runde"))
        ordner = self.basis / "ablage" / "nutzung"
        self.assertEqual(stat.S_IMODE(ordner.stat().st_mode), 0o700)
        self.assertEqual({stat.S_IMODE(d.stat().st_mode) for d in ordner.iterdir()}, {0o600})


class Leerlauf(MitAblage):
    def einstellungen(self, basis):
        return {"ablage": basis / "ablage", "session_leerlauf": 0.5}

    def test_ablauf_nennt_grund_und_aktive_zeit(self):
        self.frage("Wie viele Studierende?", speichern=True)
        time.sleep(0.7)
        self.assertEqual(self.c.get("/api/ich").status_code, 401)
        ende = self.nutzung("ende")[-1]
        self.assertEqual(ende["grund"], "leerlauf")
        self.assertLess(ende["aktiv_s"], ende["dauer_s"] + 1)


class Dienstende(MitAblage):
    def test_geordnetes_ende_schliesst_die_sitzung(self):
        with TestClient(self.c.app) as c:
            self.assertEqual(c.post("/api/anmelden", json=ANMELDUNG).status_code, 200)
            self.c = c
            self.frage("Wie viele Studierende?", speichern=True)
        self.assertEqual([z["grund"] for z in self.nutzung("ende")], ["dienstende"])


class Feedback(MitAblage):
    def test_ohne_gespraech(self):
        f = self.sende_feedback("Die Schrift ist zu klein")
        self.assertEqual((f["text"], f["benutzer"], f["gespraech"], f["ablage"], f["mitsenden"], f["runden"]),
                         ("Die Schrift ist zu klein", "t@x", None, None, False, []))
        self.assertTrue(f["sitzung"] and f["version"] and f["zeit"])
        self.assertEqual(self.nutzung("feedback"), [])  # Sitzung ohne Speichern steht nicht im Nutzerlog

    def test_mit_gespraech_bei_ausgeschaltetem_schalter(self):
        k, _ = self.frage("Wie viele Studierende?")
        f = self.sende_feedback("Die Zahl stimmt nicht", k)
        self.assertEqual((f["gespraech"], f["mitsenden"], f["runden"]), (k, True, [1]))
        self.assertEqual(self.gespraech(k)["runden"][0]["antwort"], "Antwort 1")
        self.assertTrue((self.basis / "ablage" / f["ablage"] / "gespraech.json").is_file())

    def test_ohne_mitsenden_bleibt_das_gespraech_draussen(self):
        k, _ = self.frage("Wie viele Studierende?")
        f = self.sende_feedback("Allgemeiner Hinweis", k, mitsenden=False)
        self.assertEqual((f["gespraech"], f["mitsenden"], f["ablage"], f["runden"]), (k, False, None, []))
        self.assertIsNone(self.gespraech(k))

    def test_gespeichertes_gespraech_wird_auch_ohne_mitsenden_genannt(self):
        k, _ = self.frage("Wie viele Studierende?", speichern=True)
        self.warte(lambda: self.gespraech(k))
        f = self.sende_feedback("Allgemeiner Hinweis", k, mitsenden=False)
        self.assertEqual((f["mitsenden"], f["runden"]), (False, [1]))
        self.assertTrue(f["ablage"].endswith(k))
        self.assertEqual([(z["feedback"][-5:], z["gespraech"]) for z in self.nutzung("feedback")], [(".json", k)])

    def test_fremde_kennung_wird_nicht_uebernommen(self):
        f = self.sende_feedback("Hinweis", "x" * 500, mitsenden=False)
        self.assertIsNone(f["gespraech"])
        r = self.c.post("/api/feedback", json={"text": "Hinweis", "gespraech": "0" * 32, "mitsenden": True})
        self.assertEqual(r.status_code, 404)

    def test_scheitert_das_sichern_bleibt_das_feedback_und_sagt_es(self):
        k, _ = self.frage("Wie viele Studierende?")
        with mock.patch.object(ablage_modul.Ablage, "gespraech", side_effect=OSError("Platte voll")), \
                mock.patch.object(ablage_modul, "melde"):
            f = self.sende_feedback("Die Zahl stimmt nicht", k)
        self.assertEqual((f["text"], f["mitsenden"], f["ablage"], f["runden"]),
                         ("Die Zahl stimmt nicht", True, None, []))
        f = self.sende_feedback("Zweiter Versuch", k)  # der nächste Aufruf holt das Gespräch nach
        self.assertEqual(f["runden"], [1])
        self.assertEqual(len(self.gespraech(k)["runden"]), 1)

    def test_scheitert_das_feedback_selbst_erfaehrt_es_der_tester(self):
        with mock.patch.object(ablage_modul.Ablage, "feedback", side_effect=OSError("Platte voll")), \
                mock.patch.object(ablage_modul, "melde"):
            r = self.c.post("/api/feedback", json={"text": "Hinweis", "gespraech": None, "mitsenden": False})
        self.assertEqual(r.status_code, 503)


class LaufendeRunde(MitAblage):
    def setUp(self):
        self.weiter = threading.Event()
        super().setUp()

    def antwort(self, cwd, text, n):
        self.weiter.wait(5)
        return f"Antwort {n}"

    def test_feedback_waehrend_der_runde_legt_sie_nach_ihrem_ende_ab(self):
        r = self.c.post("/api/fragen", json={"text": "Lange Frage", "gespraech": None, "verifizieren": False,
                                             "speichern": False})
        k = r.json()["gespraech"]
        f = self.sende_feedback("Das dauert zu lange", k)
        self.assertEqual((f["runde_laeuft"], f["runden"], f["ablage"]), (1, [], None))
        self.weiter.set()
        self.warte(lambda: self.gespraech(k), "laufende Runde wurde nicht abgelegt")
        self.assertEqual(self.gespraech(k)["runden"][0]["antwort"], "Antwort 1")
        self.frage("Folgefrage", k)  # Schalter aus und kein neues Feedback: Die Folgerunde bleibt draußen
        time.sleep(0.1)
        self.assertEqual(len(self.gespraech(k)["runden"]), 1)


class GescheiterteRunde(MitAblage):
    def test_unerwarteter_fehler_steht_in_der_ablage(self):
        with mock.patch.object(web_app.dateien, "uebersetze", side_effect=RuntimeError("kaputt")):
            k, stand = self.frage("Dashboard bitte", speichern=True)
            self.assertEqual(stand["runden"][-1]["fehler"], "interner Fehler")
            self.warte(lambda: self.gespraech(k), "gescheiterte Runde fehlt in der Ablage")
        runde = self.gespraech(k)["runden"][0]
        self.assertEqual((runde["frage"], runde["status"], runde["fehler"]),
                         ("Dashboard bitte", "fehler", "interner Fehler"))
        self.assertEqual([z["status"] for z in self.nutzung("runde")], ["fehler"])


class Schreiben(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ablage = ablage_modul.Ablage(Path(self.tmp.name) / "ablage")

    def tearDown(self):
        self.tmp.cleanup()

    def test_gescheitertes_schreiben_hinterlaesst_nichts(self):
        self.ablage.gespraech("2026-11-11", "a" * 32, {"runden": [1]})
        with mock.patch.object(ablage_modul.os, "replace", side_effect=OSError("Platte voll")):
            with self.assertRaises(OSError):
                self.ablage.gespraech("2026-11-11", "a" * 32, {"runden": [1, 2]})
        ordner = self.ablage.wurzel / "2026-11-11" / ("a" * 32)
        self.assertEqual([d.name for d in ordner.iterdir()], ["gespraech.json"])
        self.assertEqual(json.loads((ordner / "gespraech.json").read_text()), {"runden": [1]})  # alte Fassung bleibt

    def test_nutzung_je_monat_und_nur_angehaengt(self):
        self.ablage.nutzung([{"zeit": "2026-11-30T23:59:00+01:00", "ereignis": "anmeldung"},
                             {"zeit": "2026-12-01T00:01:00+01:00", "ereignis": "ende"}])
        self.ablage.nutzung([{"zeit": "2026-11-30T23:59:30+01:00", "ereignis": "runde"}])
        ordner = self.ablage.wurzel / "nutzung"
        self.assertEqual(sorted(d.name for d in ordner.iterdir()), ["2026-11.jsonl", "2026-12.jsonl"])
        november = [json.loads(z)["ereignis"] for z in (ordner / "2026-11.jsonl").read_text().splitlines()]
        self.assertEqual(november, ["anmeldung", "runde"])


class Auswertung(unittest.TestCase):
    def test_nutzung_je_nutzer_und_sitzung(self):
        spec = importlib.util.spec_from_file_location("auswertung", HIER / "betrieb" / "ablage-auswertung.py")
        auswertung = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(auswertung)
        a, b = {"sitzung": "a", "benutzer": "anna@x"}, {"sitzung": "b", "benutzer": "ben@x"}
        text = "\n".join(auswertung.nutzung([
            {"zeit": "2026-11-11T09:00:00+01:00", "ereignis": "dienststart"},
            {"zeit": "2026-11-11T09:05:00+01:00", "ereignis": "anmeldung", **a},
            {"zeit": "2026-11-11T09:06:00+01:00", "ereignis": "speichern", "gespraech": "g1", "an": True, **a},
            {"zeit": "2026-11-11T09:08:00+01:00", "ereignis": "runde", "gespraech": "g1", "sekunden": 120, **a},
            {"zeit": "2026-11-11T09:09:00+01:00", "ereignis": "feedback", "gespraech": "g1", **a},
            {"zeit": "2026-11-11T09:35:00+01:00", "ereignis": "ende", "grund": "abmeldung",
             "beginn": "2026-11-11T09:05:00+01:00", "aktiv_s": 1800, **a},
            {"zeit": "2026-11-11T10:00:00+01:00", "ereignis": "anmeldung", **b},
            {"zeit": "2026-11-11T10:10:00+01:00", "ereignis": "runde", "gespraech": "g2", "sekunden": 60, **b},
            {"zeit": "2026-11-11T11:00:00+01:00", "ereignis": "dienststart"}]))
        self.assertIn("| anna@x | 1 | 30 min | 1 | 1 | 2 min | 1 |", text)
        self.assertIn("| 2026-11-11 09:05 | anna@x | 30 min | abmeldung | 1 | 1 | 1 |", text)
        self.assertIn("| 2026-11-11 10:00 | ben@x | 10 min | dienst neu gestartet | 1 | 1 | 0 |", text)
        self.assertIn("Keine Sitzung", "\n".join(auswertung.nutzung([])))


if __name__ == "__main__":
    unittest.main()
