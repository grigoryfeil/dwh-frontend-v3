"""Zerlegt eine Antwort für den Export (web/bericht.py, web/excel.py) so, wie die Oberfläche sie zeigt
(oberflaeche/src/antwort.ts): Rückfrage oder Antwort, Kernaussage als erster Absatz, danach Kennzahlen, Text, Listen,
Tabellen und eingebettete Bilder.

Übernommen aus V2 (`dwh_v2/antwort.py`), ohne die Host-Verträge (`genui`), die V3 nicht kennt. Inline-Text kommt als
ReportLab-Markup (escaped, nur <b>, <i>, <strike>, <font>, <br/> und https-Links), Tabellenzellen als Klartext.
"""

import re
from html import escape
from urllib.parse import unquote

from markdown_it import MarkdownIt

from web import dateien

MARKE = re.compile(r"^\s*\[(keine antwort|no answer|rückfrage|rueckfrage|clarification|kurzklärung|kurzklaerung"
                   r"|before building)\]\s*(.*)$", re.I)
ZAHL = re.compile(r"^\s*(\d|[+\-−–]\s?\d)")
ZELLE_ZAHL = re.compile(r"^[+\-−–]?\s?[\d.,'\s]*\d[\d.,'\s]*\s?(%|‰|pp|pp\.|pkt\.?|€|eur|mio\.?|tsd\.?|k)?$", re.I)
KENNZAHL = re.compile(r"^\*\*([^*]{1,40})\*\*\s*[:–—-]?\s*(.+)$", re.S)
WERT = re.compile(r"^([+\-−–]?\s?\d[\d.,'\s]*\d|[+\-−–]?\s?\d)\s*(.*)$", re.S)


def _parser(kennung):
    md = MarkdownIt("commonmark", {"html": False, "linkify": False, "typographer": False}).enable(["table",
                                                                                                    "strikethrough"])
    md.validateLink = lambda url: bool(re.match(r"(https:|mailto:|#|/api/gespraeche/)", url, re.I))
    md.eigene = f"/api/gespraeche/{kennung}/dateien/"
    return md


def _eigene_datei(md, url):
    """Name der gemeldeten Datei im eigenen Gespräch (ohne Rundenvorsatz `r<nummer>/`) oder None."""
    if url.startswith(md.eigene) and len(url) > len(md.eigene) and ".." not in url:
        return dateien.aufloesen(unquote(url[len(md.eigene):]))[1]
    return None


def _inline(kinder):
    teile, links = [], []
    for t in kinder or []:
        if t.type == "text":
            teile.append(escape(t.content))
        elif t.type == "softbreak":
            teile.append(" ")
        elif t.type == "hardbreak":
            teile.append("<br/>")
        elif t.type in ("strong_open", "strong_close"):
            teile.append("<b>" if t.nesting == 1 else "</b>")
        elif t.type in ("em_open", "em_close"):
            teile.append("<i>" if t.nesting == 1 else "</i>")
        elif t.type in ("s_open", "s_close"):
            teile.append("<strike>" if t.nesting == 1 else "</strike>")
        elif t.type == "code_inline":
            teile.append(f'<font face="Courier">{escape(t.content)}</font>')
        elif t.type == "link_open":
            ziel = str(t.attrGet("href") or "")
            links.append(bool(re.match(r"(https:|mailto:)", ziel, re.I)))
            if links[-1]:
                teile.append(f'<a href="{escape(ziel)}">')
        elif t.type == "link_close":
            if links and links.pop():
                teile.append("</a>")
        elif t.type == "image":
            teile.append(escape(_klartext(t.children)))
    return "".join(teile)


def _klartext(kinder):
    teile = []
    for t in kinder or []:
        if t.type in ("text", "code_inline"):
            teile.append(t.content)
        elif t.type in ("softbreak", "hardbreak"):
            teile.append(" ")
        elif t.type == "image":
            teile.append(_klartext(t.children))
    return "".join(teile)


def _bloecke(tokens):
    """Blöcke der obersten Ebene: von einem öffnenden Token bis zu seinem schließenden, oder ein Einzeltoken."""
    aus, i = [], 0
    while i < len(tokens):
        if tokens[i].nesting != 1:
            aus.append(tokens[i:i + 1])
            i += 1
            continue
        tiefe, j = 0, i
        while j < len(tokens):
            tiefe += tokens[j].nesting
            if tiefe == 0:
                break
            j += 1
        aus.append(tokens[i:j + 1])
        i = j + 1
    return aus


def _eintraege(block):
    """Inline-Token je Listenpunkt, nur der erste Absatz."""
    aus, tiefe, neu = [], 0, False
    for t in block:
        if t.type == "list_item_open":
            tiefe += 1
            neu = tiefe == 1
        elif t.type == "list_item_close":
            tiefe -= 1
        elif t.type == "inline" and neu:
            aus.append(t)
            neu = False
    return aus


def _tabelle(block):
    zeilen, zeile = [], []
    for i, t in enumerate(block):
        if t.type == "tr_open":
            zeile = []
        elif t.type in ("th_open", "td_open"):
            zeile.append(_klartext(block[i + 1].children).strip())
        elif t.type == "tr_close":
            zeilen.append(zeile)
    spalten = max((len(z) for z in zeilen), default=0)
    zahlen = []
    for s in range(spalten):
        werte = [z[s] if s < len(z) else "" for z in zeilen[1:]]
        zahlen.append(s > 0 and bool(werte) and any(werte)
                      and all(w in ("", "–") or ZELLE_ZAHL.match(w) for w in werte))
    return {"typ": "tabelle", "zeilen": zeilen, "zahlen": zahlen}


def _block(md, block):
    art = block[0].type
    if art == "paragraph_open":
        kinder = [k for k in block[1].children or [] if not (k.type == "text" and not k.content.strip())]
        if len(kinder) == 1 and kinder[0].type == "image":
            name = _eigene_datei(md, str(kinder[0].attrGet("src") or ""))
            if name:
                return [{"typ": "bild", "name": name}]
        return [{"typ": "absatz", "text": _inline(block[1].children)}]
    if art == "heading_open":
        return [{"typ": "ueberschrift", "text": _inline(block[1].children)}]
    if art in ("bullet_list_open", "ordered_list_open"):
        return [{"typ": "liste", "nummeriert": art == "ordered_list_open",
                 "punkte": [_inline(t.children) for t in _eintraege(block)]}]
    if art == "table_open":
        return [_tabelle(block)]
    if art in ("fence", "code_block"):
        return [{"typ": "code", "text": block[0].content.rstrip("\n")}]
    if art == "blockquote_open":
        return [b for innen in _bloecke(block[1:-1]) for b in _block(md, innen)]
    return []


def _kennzahlen(md, block):
    if not block or block[0].type != "bullet_list_open":
        return None
    eintraege = _eintraege(block)
    if not eintraege or len(eintraege) > 6:
        return None
    aus = []
    for t in eintraege:
        k = KENNZAHL.match(t.content.strip())
        if not k or not ZAHL.match(k[1]):
            return None
        w = WERT.match(k[1].strip())
        wert = re.sub(r"\s+", " ", w[1] if w else k[1])
        aus.append({"wert": re.sub(r"^-", "−", wert), "einheit": w[2] if w else "",
                    "label": _inline(md.parseInline(k[2].strip())[0].children)})
    return aus


def zerlege(text, kennung):
    """Antwort: {"art": "antwort", "lead", "lead_text", "kennzahlen", "bloecke"}. Rückfrage, Kurzklärung und
    Nichtantwort: {"art", "titel", "bloecke", "optionen"}."""
    md = _parser(kennung)
    zeilen = text.replace("\r\n", "\n").split("\n")
    erste = next((i for i, z in enumerate(zeilen) if z.strip()), None)
    marke = MARKE.match(zeilen[erste]) if erste is not None else None

    if marke:
        rest = zeilen[erste + 1:]
        titel = marke[2].strip()
        if not titel:
            k = next((i for i, z in enumerate(rest) if z.strip()), None)
            titel = rest[k] if k is not None else ""
            rest = rest[k + 1:] if k is not None else []
        titel = re.sub(r"^\*\*(.*)\*\*$", r"\1", re.sub(r"^#+\s*", "", titel).strip())
        titel = _inline(md.parseInline(titel)[0].children) if titel else ""
        bl = _bloecke(md.parse("\n".join(rest)))
        if marke[1].lower() in ("keine antwort", "no answer"):
            return {"art": "keine", "titel": titel, "bloecke": [b for x in bl for b in _block(md, x)], "optionen": []}
        optionen = []
        if bl and bl[-1][0].type in ("bullet_list_open", "ordered_list_open"):
            optionen = [_klartext(t.children).strip() for t in _eintraege(bl[-1])]
            bl = bl[:-1]
        art = "rueckfrage" if marke[1].lower() in ("rückfrage", "rueckfrage", "clarification") else "kurzklaerung"
        return {"art": art, "titel": titel, "bloecke": [b for x in bl for b in _block(md, x)], "optionen": optionen}

    bl = _bloecke(md.parse("\n".join(zeilen)))
    lead = lead_text = ""
    kennzahlen = None
    if bl and bl[0][0].type == "paragraph_open" and _block(md, bl[0])[0]["typ"] == "absatz":
        lead, lead_text = _inline(bl[0][1].children), _klartext(bl[0][1].children)
        bl = bl[1:]
        kennzahlen = _kennzahlen(md, bl[0] if bl else None)
        if kennzahlen:
            bl = bl[1:]
    return {"art": "antwort", "lead": lead, "lead_text": lead_text, "kennzahlen": kennzahlen or [],
            "bloecke": [b for x in bl for b in _block(md, x)]}


def tabellen(zerlegt):
    """Alle Tabellen der Antwort als Zeilen aus Texten, die erste Zeile ist der Kopf."""
    return [b["zeilen"] for b in zerlegt["bloecke"] if b["typ"] == "tabelle" and b["zeilen"]]


def sprache(text):
    """Deutsch oder Englisch, wie sprache() in oberflaeche/src/antwort.ts."""
    de = len(re.findall(r"[äöüß]|\b(der|die|das|und|nicht|wie|welche|ist|sind|im|mit|für|seit|von|zu|den|dem)\b",
                        text, re.I))
    en = len(re.findall(r"\b(the|and|which|what|how|is|are|of|for|since|with|to|in)\b", text, re.I))
    return "de" if de > en else "en"
