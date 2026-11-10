"""Tests für den Export als PDF und Excel (/api/export.pdf, /api/export.xlsx), mit Ersatzmodell wie
tests/test_web_lebenszyklus.py.

Abgesichert: Zahlen der Antwort werden in Excel echte Zahlen, Formelanfänge bleiben Text, nur eigene Gespräche
lassen sich exportieren, ohne Tabelle gibt es kein Excel, aber ein PDF, Rückfragen und interaktive Dateien gehen
ins PDF, ohne dass ihr Skript läuft.
Aufruf: python3 -m unittest tests/test_export.py (braucht starlette, httpx, reportlab und markdown-it-py).
"""

import io
import sys
import unittest
import zipfile
from pathlib import Path

HIER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HIER))
sys.path.insert(0, str(HIER / "tests"))

from starlette.testclient import TestClient  # noqa: E402

from test_web_lebenszyklus import Grundlage  # noqa: E402
from web import antwort, bericht  # noqa: E402

TABELLE = """Der Bestand beträgt **3.458 Studierende** und ist damit gesunken.

| Campus | Studierende | Anteil | Notiz |
|---|---:|---:|---|
| Berlin | 1.219 | 35,3 % | =HYPERLINK("x") |
| Wien | 1.172 | −2,5 % | stabil |

**Nachweis:** Monatsstand 25.10.2026."""


def blatt(inhalt, nummer=1):
    with zipfile.ZipFile(io.BytesIO(inhalt)) as zf:
        return zf.read(f"xl/worksheets/sheet{nummer}.xml").decode(), zf.namelist()


class Export(Grundlage):
    texte = {}

    def antwort(self, cwd, text, n):
        inhalt = self.texte.get(n, f"Antwort {n}")
        if "dashboard.html" in inhalt:
            (cwd / "dashboard.html").write_text("<html><head><title>Leads je Monat</title></head>"
                                                "<script>window.x=1</script></html>")
        return inhalt

    def test_excel_mit_zahlen_und_entschaerften_formeln(self):
        self.texte = {1: TABELLE}
        k, stand = self.frage("Wie viele Studierende?")
        self.assertEqual(stand["status"], "fertig")
        r = self.c.get(f"/api/export.xlsx?gespraeche={k}")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertIn("SAE-Data-Desk-Tables-", r.headers["content-disposition"])
        xml, namen = blatt(r.content)
        self.assertIn("xl/workbook.xml", namen)
        self.assertIn("<v>1219</v>", xml)  # 1.219 deutsch gelesen
        self.assertIn("<v>0.353</v>", xml)  # 35,3 % als Anteil
        self.assertIn("<v>-0.025</v>", xml)  # Minuszeichen U+2212
        self.assertIn("'=HYPERLINK", xml)  # Formelanfang bleibt Text
        self.assertNotIn("<f>", xml)
        self.assertIn("Wie viele Studierende?", xml)
        self.assertIn("Der Bestand beträgt 3.458 Studierende", xml)

    def test_pdf_ueber_alle_gespraeche_des_verlaufs(self):
        self.texte = {1: TABELLE, 2: "[Rückfrage] Meinst du den Intake **März 2027**?"}
        a, _ = self.frage("Wie viele Studierende?")
        b, _ = self.frage("Neueinschreibungen gegen Ziel?")
        r = self.c.get(f"/api/export.pdf?gespraeche={a},{b}")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.headers["content-type"], "application/pdf")
        self.assertTrue(r.content.startswith(b"%PDF"))
        self.assertIn("SAE-Data-Desk-Report-", r.headers["content-disposition"])

    def test_ohne_tabelle_kein_excel_aber_pdf(self):
        k, _ = self.frage("Hallo")
        self.assertEqual(self.c.get(f"/api/export.xlsx?gespraeche={k}").status_code, 409)
        self.assertEqual(self.c.get(f"/api/export.pdf?gespraeche={k}").status_code, 200)

    def test_nur_eigene_gespraeche(self):
        self.texte = {1: TABELLE}
        k, _ = self.frage("Wie viele Studierende?")
        fremd = TestClient(self.c.app)
        self.assertEqual(fremd.post("/api/anmelden", json={"email": "t@x", "passwort": "geheim"}).status_code, 200)
        self.assertEqual(fremd.get(f"/api/export.pdf?gespraeche={k}").status_code, 409)
        self.assertEqual(fremd.get(f"/api/export.xlsx?gespraeche={k}").status_code, 409)
        self.assertEqual(TestClient(self.c.app).get(f"/api/export.pdf?gespraeche={k}").status_code, 401)
        self.assertEqual(self.c.get("/api/export.pdf?gespraeche=../x,").status_code, 409)

    def test_interaktive_datei_als_hinweis(self):
        self.texte = {1: "Die Leads steigen.\n\n[Dashboard öffnen](dashboard.html)"}
        k, stand = self.frage("Dashboard der Leads")
        self.assertEqual([d["name"] for d in stand["runden"][0]["dateien"]], ["dashboard.html"])
        gelesen = []
        zug = {"frage": "Dashboard der Leads", "zeit": "10:00", "antwort": stand["runden"][0]["antwort"],
               "gespraech": k, "dateien": ["dashboard.html"], "pruefung": {"status": "bestaetigt"},
               "lese": lambda name: gelesen.append(name) or b"<title>Leads je Monat</title>"}
        self.assertTrue(bericht.pdf([zug], "2026-11-06", "0.7.0", __import__("datetime").date(2026, 11, 10))
                        .startswith(b"%PDF"))
        self.assertEqual(gelesen, ["dashboard.html"])  # nur der Titel wird gelesen, das Skript läuft nicht
        self.assertEqual(self.c.get(f"/api/export.pdf?gespraeche={k}").status_code, 200)


class Schrift(unittest.TestCase):
    @unittest.skipUnless(bericht.ERSATZ.exists(), "Ersatzschrift DejaVu fehlt (nur auf dem VPS vorhanden)")
    def test_fehlende_zeichen_in_ersatzschrift(self):
        self.assertEqual(bericht._schrift("Opportunity → <b>Enrollment</b> ≥ 5 % Šimić"),
                         'Opportunity <font name="Ersatz">→</font> <b>Enrollment</b> <font name="Ersatz">≥</font> 5 % '
                         '<font name="Ersatz">Š</font>imi<font name="Ersatz">ć</font>')


class Zerlegung(unittest.TestCase):
    def test_kernaussage_tabelle_und_eigenes_bild(self):
        k = "a" * 32
        a = antwort.zerlege(TABELLE + f"\n\n![Verlauf](/api/gespraeche/{k}/dateien/r2/verlauf.png)", k)
        self.assertEqual(a["art"], "antwort")
        self.assertEqual(a["lead_text"], "Der Bestand beträgt 3.458 Studierende und ist damit gesunken.")
        self.assertEqual(antwort.tabellen(a)[0][1][:3], ["Berlin", "1.219", "35,3 %"])
        self.assertEqual([b["zahlen"] for b in a["bloecke"] if b["typ"] == "tabelle"], [[False, True, True, False]])
        self.assertIn({"typ": "bild", "name": "verlauf.png"}, a["bloecke"])
        self.assertEqual(antwort.sprache(TABELLE), "de")

    def test_rueckfrage(self):
        a = antwort.zerlege("[Rückfrage] Meinst du **März 2027**?", "b" * 32)
        self.assertEqual((a["art"], a["titel"]), ("rueckfrage", "Meinst du <b>März 2027</b>?"))

    def test_fremde_links_bleiben_text(self):
        a = antwort.zerlege('Siehe [hier](javascript:alert(1)) und <b onload="x">fett</b>.', "c" * 32)
        self.assertNotIn("<a ", a["lead"])  # gesperrtes Schema bleibt Text, kein Link
        self.assertNotIn("<b onload", a["lead"])


if __name__ == "__main__":
    unittest.main()
