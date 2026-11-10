"""PDF-Report des Gesprächs, übernommen aus V2 (`dwh_v2/bericht.py`, Entwurf Richtung A): A4, laufender Kopf und
Fuß, je Runde Frage, Antwort mit Kennzahlen, Text, Tabellen, Bildern und dem Ergebnis von Verify.

Maße stehen wie im Entwurf in Pixeln bei 96 dpi und werden mit px() in Punkt umgerechnet. Diagramme und Dashboards
sind in V3 HTML-Seiten des Modells. Das Backend kann sie nicht abbilden, ohne ihr Skript auszuführen, sie erscheinen
als Hinweiskasten (Entscheidung Grigory, 01.11. für V2, 10.11. für V3). Bilder (PNG, JPEG) stehen im Report.
"""

import io
import re
from datetime import date
from html import escape
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import (BaseDocTemplate, Frame, HRFlowable, Image, Indenter, KeepTogether, PageTemplate,
                                Paragraph, Spacer, Table, TableStyle)

from web.antwort import zerlege

DRUCK = Path(__file__).parent / "druck"
INK, TEXT2, BODY, TEXT3 = HexColor("#1C1C1C"), HexColor("#55595C"), HexColor("#33363A"), HexColor("#74777A")
RULE, ORANGE = HexColor("#E3E3E0"), HexColor("#FF6900")
HTML = re.compile(r"\.(html?|xhtml)$", re.I)
BILD = re.compile(r"\.(png|jpe?g|gif|webp)$", re.I)
VERIFY = {"bestaetigt": "<b>Verify</b> A second review confirmed this answer.",
          "korrigiert": "<b>Verify</b> A second review corrected this answer. The corrected version is shown."}
ZAHLWORT = ["No", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten", "Eleven", "Twelve"]
MONATE = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]


def px(wert):
    return wert * 0.75


SEITE_B, SEITE_H = A4
RAND = px(72)
RANDSPALTE = px(96) + px(24)  # Randspalte und Abstand
BREITE = SEITE_B - 2 * RAND
TEXTBREITE = BREITE - RANDSPALTE
KOPF_LINIE = SEITE_H - px(86)
FUSS_LINIE = px(72)

for _schnitt in (300, 400, 500, 600):
    pdfmetrics.registerFont(TTFont(f"Plex{_schnitt}", str(DRUCK / f"IBMPlexSans-{_schnitt}.ttf")))
pdfmetrics.registerFontFamily("Plex400", normal="Plex400", bold="Plex600", italic="Plex400", boldItalic="Plex600")
# IBM Plex liegt hier nur mit Latin-1 vor. Was fehlt (Pfeile, ≥, Š, Ł …), setzt _schrift in DejaVu Sans, wenn das
# System sie hat (VPS: fonts-dejavu-core), sonst bleibt das Zeichen ein Kästchen.
PLEX = set(TTFont("PlexZeichen", str(DRUCK / "IBMPlexSans-400.ttf")).face.charToGlyph)
ERSATZ = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
if ERSATZ.exists():
    pdfmetrics.registerFont(TTFont("Ersatz", str(ERSATZ)))
FEHLT = re.compile(r"[^\x00-\x7f]+")


def _schrift(markup):
    """Setzt Zeichen, die IBM Plex nicht hat, in die Ersatzschrift. Tags und Entities sind ASCII und bleiben."""
    if not ERSATZ.exists():
        return markup

    def ersetze(m):
        return "".join(f'<font name="Ersatz">{c}</font>' if ord(c) not in PLEX else c for c in m[0])
    return FEHLT.sub(ersetze, markup)


def P(text, stil, **mehr):
    return Paragraph(_schrift(text), stil, **mehr)


def _stil(name, groesse, zeile, schnitt=400, farbe=INK, **mehr):
    return ParagraphStyle(name, fontName=f"Plex{schnitt}", fontSize=px(groesse), leading=px(zeile), textColor=farbe,
                          **mehr)


TITEL = _stil("titel", 32, 38, 300)
META = _stil("meta", 11, 16, farbe=TEXT2)
RANDLABEL = _stil("randlabel", 8, 12, 600)
RANDZEIT = _stil("randzeit", 8, 12, farbe=TEXT3)
FRAGE = _stil("frage", 15, 21, 500)
LEAD = _stil("lead", 12.5, 19)
LEAD_TITEL = _stil("leadtitel", 12.5, 19, 500)
ABSATZ = _stil("absatz", 10, 15, farbe=BODY, spaceAfter=px(8))
UEBERSCHRIFT = _stil("ueberschrift", 10, 15, 600, spaceBefore=px(4), spaceAfter=px(4))
PUNKT = _stil("punkt", 10, 15, farbe=BODY, leftIndent=px(14), bulletIndent=px(2), spaceAfter=px(2))
CODE = ParagraphStyle("code", fontName="Courier", fontSize=px(8.5), leading=px(12), textColor=BODY,
                      spaceAfter=px(8))
ZELLE = _stil("zelle", 9, 13)
ZELLE_ZAHL = _stil("zellezahl", 9, 13, alignment=TA_RIGHT)
KOPFZELLE = _stil("kopfzelle", 9, 13, 500)
KOPFZELLE_ZAHL = _stil("kopfzellezahl", 9, 13, 500, alignment=TA_RIGHT)
KZ_LABEL = _stil("kzlabel", 8, 12, farbe=TEXT2)
NOTIZ_LABEL = _stil("notizlabel", 8, 12, 600)
NOTIZ = _stil("notiz", 10, 15)
KLEIN = _stil("klein", 8, 12, farbe=TEXT3)
KASTEN_TITEL = _stil("kastentitel", 12.5, 19, 300)


def datum_lang(tag):
    return f"{tag.day} {MONATE[tag.month - 1]} {tag.year}"


def datum_kurz(iso):
    """2026-10-30 → 30 Oct 2026"""
    tag = date.fromisoformat(iso)
    return f"{tag.day} {MONATE[tag.month - 1][:3]} {tag.year}"


class _Leinwand(canvas.Canvas):
    """Zeichnet Kopf und Fuß erst beim Speichern, wenn die Seitenzahl feststeht."""

    def __init__(self, *args, kopf, **kwargs):
        super().__init__(*args, **kwargs)
        self._kopf = kopf
        self._seiten = []

    def showPage(self):
        self._seiten.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        for nummer, zustand in enumerate(self._seiten, start=1):
            self.__dict__.update(zustand)
            self._rahmen(nummer, len(self._seiten))
            super().showPage()
        super().save()

    def _rahmen(self, nummer, anzahl):
        datum, fuss = self._kopf
        oben = SEITE_H - px(68)
        logo_h = px(14)
        self.drawImage(str(DRUCK / "sae-solo-grey.png"), RAND, oben - px(3), width=logo_h * 332 / 213,
                       height=logo_h, mask="auto")
        x = RAND + logo_h * 332 / 213 + px(10)
        self.setFont("Plex500", px(10))
        self.setFillColor(INK)
        self.drawString(x, oben, "Data Desk")
        x += pdfmetrics.stringWidth("Data Desk", "Plex500", px(10)) + px(1.5)
        self.setFillColor(ORANGE)
        self.rect(x, oben, px(3), px(3), stroke=0, fill=1)
        self.setFont("Plex400", px(10))
        self.setFillColor(TEXT2)
        self.drawString(x + px(10), oben, "Conversation report")
        self.drawRightString(SEITE_B - RAND, oben, datum)
        self.setStrokeColor(INK)
        self.setLineWidth(px(1))
        self.line(RAND, KOPF_LINIE, SEITE_B - RAND, KOPF_LINIE)

        self.setStrokeColor(RULE)
        self.line(RAND, FUSS_LINIE, SEITE_B - RAND, FUSS_LINIE)
        self.setFont("Plex400", px(9))
        self.setFillColor(TEXT3)
        self.drawString(RAND, FUSS_LINIE - px(18), fuss)
        self.drawRightString(SEITE_B - RAND, FUSS_LINIE - px(18), f"{nummer} / {anzahl}")


def pdf(zuege, datenstand, version, heute):
    """zuege: je beantwortete Runde {"frage", "zeit" (HH:MM), "antwort", "gespraech", "dateien" (Namen),
    "pruefung" (oder None), "lese" (Name → Bytes oder None)}. Gibt das PDF als Bytes zurück."""
    stand = f"Data as of {datum_kurz(datenstand)} · " if datenstand else ""
    puffer = io.BytesIO()
    dokument = BaseDocTemplate(puffer, pagesize=A4, title="Conversation report", author="SAE Data Desk",
                               leftMargin=RAND, rightMargin=RAND)
    rahmen = Frame(RAND, FUSS_LINIE + px(16), BREITE, KOPF_LINIE - px(32) - FUSS_LINIE - px(16), id="text",
                   leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    dokument.addPageTemplates([PageTemplate(id="seite", frames=[rahmen])])

    anzahl = len(zuege)
    menge = f"{ZAHLWORT[anzahl] if anzahl < len(ZAHLWORT) else anzahl} question{'s' if anzahl != 1 else ''}"
    teile = [P("Conversation report", TITEL), Spacer(1, px(8)),
             P(escape(f"{menge} · {datum_lang(heute)} · {stand}Version {version}"), META),
             Spacer(1, px(32))]
    for nummer, zug in enumerate(zuege, start=1):
        kopf, rest = _runde(nummer, zug)
        # Seitenwechsel zwischen den Runden: Frage, Lead und erster Teil der Antwort stehen zusammen
        teile += [KeepTogether(kopf), *rest, Spacer(1, px(24))]

    def leinwand(*args, **kwargs):
        return _Leinwand(*args, kopf=(datum_lang(heute), f"{stand}Version {version} · Confidential"), **kwargs)

    dokument.build(teile, canvasmaker=leinwand)
    return puffer.getvalue()


def _zeile(rand, inhalt):
    """Randspalte mit Beschriftung neben der Textspalte."""
    tabelle = Table([[rand, inhalt]], colWidths=[RANDSPALTE, TEXTBREITE])
    tabelle.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                 ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 0),
                                 ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
    return tabelle


def _runde(nummer, zug):
    a = zerlege(zug["antwort"], zug["gespraech"])
    teile = [HRFlowable(width="100%", thickness=px(1), color=INK, spaceBefore=0, spaceAfter=px(16)),
             _zeile([P(f"Question {nummer:02d}", RANDLABEL), P(escape(zug["zeit"]), RANDZEIT)],
                    P(escape(zug["frage"]), FRAGE)),
             Spacer(1, px(14))]
    if a["art"] == "antwort":
        if a["lead"]:
            teile.append(_zeile(P("Answer", RANDLABEL), P(a["lead"], LEAD)))
            teile.append(Spacer(1, px(12)))
        innen = _kennzahlen(a["kennzahlen"]) if a["kennzahlen"] else []
    else:
        teile.append(_zeile(P({"keine": "Answer", "kurzklaerung": "Before building"}.get(a["art"], "Clarification"),
                                      RANDLABEL),
                            P(a["titel"], LEAD_TITEL)))
        teile.append(Spacer(1, px(12)))
        innen = []
    innen += [f for b in a["bloecke"] for f in _block(b, zug)]
    if a["art"] in ("rueckfrage", "kurzklaerung"):
        innen += [P(escape(o), PUNKT, bulletText="–") for o in a["optionen"]]

    p = zug.get("pruefung") or {}
    if p.get("status") in ("hinweis", "gescheitert") and p.get("hinweis"):
        innen += _hinweis(zerlege(p["hinweis"], zug["gespraech"]))
    elif p.get("status") in VERIFY:
        innen += [P(VERIFY[p["status"]], KLEIN), Spacer(1, px(8))]
    gezeigt = {b["name"] for b in a["bloecke"] if b["typ"] == "bild"}
    andere = []
    for name in zug["dateien"]:
        if BILD.search(name) and name not in gezeigt:
            innen += _bild(name, zug)
        elif HTML.search(name):
            innen += _dashboard(name, zug)
        elif not BILD.search(name):
            andere.append(name)
    if andere:
        innen.append(P("<b>Files</b> " + escape(" · ".join(andere)), KLEIN))
    if not innen:
        return teile, []
    return teile + [Indenter(left=RANDSPALTE), innen[0]], [*innen[1:], Indenter(left=-RANDSPALTE)]


def _kennzahlen(kennzahlen):
    """Je Reihe eine Tabellenzeile, die nie umbricht. Kein KeepTogether hier: Verschachtelt meldet es eine
    Riesenhöhe und schiebt den Kopf der Runde auf die nächste Seite."""
    spalten = min(len(kennzahlen), 3)
    luecke = px(16)
    breite = (TEXTBREITE - (spalten - 1) * luecke) / spalten  # je Kennzahl eine eigene Linie, Lücken dazwischen
    zellen = []
    for k in kennzahlen:
        einheit = f' <font name="Plex400" size="{px(10)}" color="#55595C">{escape(k["einheit"])}</font>' \
            if k["einheit"] else ""
        zellen.append([HRFlowable(width=breite, thickness=px(1), color=RULE, spaceBefore=0, spaceAfter=px(6),
                                  hAlign="LEFT"),
                       P(f'{escape(k["wert"])}{einheit}', _stil("kz", 28, 32, 300)),
                       Spacer(1, px(4)), P(k["label"], KZ_LABEL)])
    reihen = [zellen[i:i + spalten] for i in range(0, len(zellen), spalten)]
    reihen[-1] += [""] * (spalten - len(reihen[-1]))
    tabelle = Table(reihen, colWidths=[breite + luecke] * (spalten - 1) + [breite])
    tabelle.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                 ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 0),
                                 ("BOTTOMPADDING", (0, 0), (-1, -1), px(12))]))
    return [tabelle, Spacer(1, px(4))]


def _block(b, zug):
    if b["typ"] == "absatz":
        return [P(b["text"], ABSATZ)]
    if b["typ"] == "ueberschrift":
        return [P(b["text"], UEBERSCHRIFT)]
    if b["typ"] == "liste":
        return [P(t, PUNKT, bulletText=f"{i}." if b["nummeriert"] else "–")
                for i, t in enumerate(b["punkte"], start=1)] + [Spacer(1, px(6))]
    if b["typ"] == "code":
        return [P(escape(b["text"]).replace("\n", "<br/>"), CODE)]
    if b["typ"] == "tabelle":
        return [_tabelle(b), Spacer(1, px(12))]
    if b["typ"] == "bild":
        return _bild(b["name"], zug)
    return []


def _tabelle(b):
    zeilen = b["zeilen"]
    spalten = max(len(z) for z in zeilen)
    zahlen = b["zahlen"] + [False] * (spalten - len(b["zahlen"]))
    # Breite nach dem längsten Inhalt, die erste Spalte mindestens ein Viertel
    laengen = [max(len(z[s]) if s < len(z) else 0 for z in zeilen) + 4 for s in range(spalten)]
    laengen[0] = max(laengen[0], sum(laengen) / 4)
    breiten = [TEXTBREITE * l / sum(laengen) for l in laengen]
    daten = []
    for r, zeile in enumerate(zeilen):
        reihe = []
        for s in range(spalten):
            text = escape(zeile[s]) if s < len(zeile) else ""
            stil = (KOPFZELLE_ZAHL if zahlen[s] else KOPFZELLE) if r == 0 else (ZELLE_ZAHL if zahlen[s] else ZELLE)
            reihe.append(P(text, stil))
        daten.append(reihe)
    tabelle = Table(daten, colWidths=breiten, repeatRows=1)
    tabelle.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), px(8)), ("RIGHTPADDING", (-1, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), px(3)), ("BOTTOMPADDING", (0, 0), (-1, -1), px(4)),
        ("LINEBELOW", (0, 0), (-1, 0), px(1), INK), ("LINEBELOW", (0, 1), (-1, -1), px(1), RULE)]))
    return tabelle


def _bild(name, zug):
    """Diagramm des Modells auf Textbreite, höchstens 340 px hoch. Unlesbares erscheint als Dateiname."""
    inhalt = zug["lese"](name)
    try:
        if inhalt is None:
            raise ValueError("Datei fehlt")
        leser = ImageReader(io.BytesIO(inhalt))
        breite, hoehe = leser.getSize()
        if breite * hoehe > 40_000_000:
            raise ValueError("zu groß")
    except Exception:  # noqa: BLE001, jede kaputte Datei des Modells wird Text
        return [P("<b>Chart</b> " + escape(name), KLEIN), Spacer(1, px(8))]
    massstab = min(TEXTBREITE / breite, px(340) / hoehe)
    return [Image(io.BytesIO(inhalt), width=breite * massstab, height=hoehe * massstab, hAlign="LEFT"),
            Spacer(1, px(12))]


def _dashboard(name, zug):
    titel = None
    inhalt = zug["lese"](name)
    if inhalt:
        treffer = re.search(rb"<title[^>]*>(.*?)</title>", inhalt[:200_000], re.I | re.S)
        if treffer:
            titel = " ".join(treffer[1].decode("utf-8", "replace").split())[:120] or None
    titel = titel or titel_aus_name(name)
    kasten = Table([[[P("Chart or dashboard", KLEIN), P(escape(titel), KASTEN_TITEL),
                      Spacer(1, px(4)),
                      P(escape(f"“{titel}” is interactive and not part of the printed report. "
                                       "Open it in Data Desk while the conversation is still open."), KLEIN)]]],
                   colWidths=[TEXTBREITE])
    kasten.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), px(1), RULE), ("LEFTPADDING", (0, 0), (-1, -1), px(16)),
                                ("RIGHTPADDING", (0, 0), (-1, -1), px(16)), ("TOPPADDING", (0, 0), (-1, -1), px(12)),
                                ("BOTTOMPADDING", (0, 0), (-1, -1), px(14))]))
    return [kasten, Spacer(1, px(12))]


def titel_aus_name(name):
    """Wie titelAusName in oberflaeche/src/Ansichten.tsx."""
    teile = [t for t in name.split("/") if not re.fullmatch(r"(dist|build|out|index\.html?)", t, re.I)]
    t = re.sub(r"[-_]+", " ", HTML.sub("", teile[-1] if teile else "")).strip()
    return t[0].upper() + t[1:] if t else "Dashboard"


def _hinweis(a):
    if a["art"] == "antwort":
        text = " ".join([a["lead"]] + [b["text"] for b in a["bloecke"] if b["typ"] == "absatz"]).strip()
    else:
        text = a["titel"]
    notiz = Table([[[P("Note after verification", NOTIZ_LABEL), Spacer(1, px(4)), P(text, NOTIZ)]]],
                  colWidths=[TEXTBREITE])
    notiz.setStyle(TableStyle([("LINEABOVE", (0, 0), (-1, 0), px(1), INK), ("LINEBELOW", (0, -1), (-1, -1), px(1), RULE),
                               ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                               ("TOPPADDING", (0, 0), (-1, -1), px(10)), ("BOTTOMPADDING", (0, 0), (-1, -1), px(12))]))
    return [notiz, Spacer(1, px(12))]
