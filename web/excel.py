"""Excel-Export des Gesprächs: ein Blatt je Antwort mit ihren Tabellen, nur Standardbibliothek.

Unverändert aus V2 (`dwh_v2/excel.py`), dort nach V1 `web/excel.py`: Jeder Text wird gegen Formelinjektion entschärft, die Mappe enthält nie ein Formelelement.
Zellen, die nach der Schreibweise der Antwortsprache eindeutig eine Zahl sind, stehen als Zahl in der Zelle, mit
so vielen Nachkommastellen wie im Text, Prozente als Anteil im Prozentformat. Alles andere bleibt Text.
"""

import io
import re
import zipfile
from decimal import Decimal
from xml.sax.saxutils import escape, quoteattr

# In XML 1.0 unzulässig: Steuerzeichen außer Tab, LF, CR, dazu Surrogate und FFFE/FFFF.
_UNZULAESSIG = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff￾￿]")
# Excel liest _xHHHH_ in Zelltexten als Zeichencode, der Unterstrich wird dann maskiert.
_EXCEL_CODE = re.compile(r"_(x[0-9A-Fa-f]{4}_)")
_FORMELSTART = frozenset("=+-@\t\r\n|＝＋－＠")
_BLATT_VERBOTEN = re.compile(r"[\[\]:*?/\\]")
_MINUS = "-−–"

_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_FETT = 1


def mappe(blaetter):
    """blaetter: je Antwort {"name", "kopf": [(Beschriftung, Text)], "tabellen": [[Zeile, …]], "sprache": "de"|"en"},
    die erste Zeile jeder Tabelle ist ihr Kopf. Gibt die .xlsx als Bytes zurück."""
    formate = []  # Zahlenformate in der Reihenfolge ihres ersten Auftretens, Stil 2 + Index
    namen = []
    xmls = []
    for b in blaetter:
        reihen = [[_text(beschriftung, _FETT), _text(wert)] for beschriftung, wert in b["kopf"]]
        for tabelle in b["tabellen"]:
            reihen.append([])
            reihen.append([_text(zelle, _FETT) for zelle in tabelle[0]])
            for zeile in tabelle[1:]:
                reihen.append([_zelle(zelle, b.get("sprache"), formate) for zelle in zeile])
        namen.append(_blattname(b["name"], namen))
        xmls.append(_sheet(reihen))

    puffer = io.BytesIO()
    with zipfile.ZipFile(puffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", _content_types(len(xmls)))
        zf.writestr("_rels/.rels", _RELS)
        zf.writestr("xl/workbook.xml", _workbook(namen))
        zf.writestr("xl/_rels/workbook.xml.rels", _workbook_rels(len(xmls)))
        zf.writestr("xl/styles.xml", _styles(formate))
        for nummer, xml in enumerate(xmls, start=1):
            zf.writestr(f"xl/worksheets/sheet{nummer}.xml", xml)
    return puffer.getvalue()


def zahl(text, sprache):
    """(Wert als Dezimalstring, Excel-Zahlenformat) oder None, wenn der Text nicht eindeutig eine Zahl ist.
    Tausender und Dezimalzeichen nach der Sprache: Deutsch 1.234,5, Englisch 1,234.5."""
    t = str(text).strip()
    prozent = t.endswith("%")
    if prozent:
        t = t[:-1].rstrip()
    negativ = bool(t) and t[0] in _MINUS
    if t and t[0] in "+" + _MINUS:
        t = t[1:].lstrip()
    tausend, komma = (".", ",") if sprache == "de" else (",", ".")
    treffer = re.fullmatch(rf"(\d{{1,3}}(?:{re.escape(tausend)}\d{{3}})+|\d+)(?:{re.escape(komma)}(\d+))?", t)
    if not treffer:
        return None
    stellen = treffer[2] or ""
    wert = Decimal(treffer[1].replace(tausend, "") + ("." + stellen if stellen else ""))
    if negativ:
        wert = -wert
    nachkomma = "." + "0" * len(stellen) if stellen else ""
    if prozent:
        return format(wert.scaleb(-2), "f"), "0" + nachkomma + "%"
    return format(wert, "f"), "#,##0" + nachkomma


def entschaerft(text):
    """Bereinigt Steuerzeichen und stellt Formelanfängen ein ' voran."""
    text = _UNZULAESSIG.sub("", str(text))
    rest = text.lstrip(" ")
    if rest and rest[0] in _FORMELSTART:
        return "'" + text
    return text


def spaltenbuchstabe(nummer):
    """1 → A, 26 → Z, 27 → AA."""
    buchstaben = ""
    while nummer:
        nummer, rest = divmod(nummer - 1, 26)
        buchstaben = chr(ord("A") + rest) + buchstaben
    return buchstaben


def _zelle(text, sprache, formate):
    gefunden = zahl(text, sprache)
    if gefunden is None:
        return _text(text)
    wert, fmt = gefunden
    if fmt not in formate:
        formate.append(fmt)
    return f' s="{2 + formate.index(fmt)}"', f"<v>{wert}</v>", len(str(text))


def _text(text, stil=0):
    inhalt = _EXCEL_CODE.sub(r"_x005F_\1", entschaerft(text))
    breite = len(inhalt)
    inhalt = escape(inhalt).replace("\r", "&#13;")
    attribute = ' t="inlineStr"' + (f' s="{stil}"' if stil else "")
    return attribute, f'<is><t xml:space="preserve">{inhalt}</t></is>', breite


def _sheet(reihen):
    breiten = {}
    xml = []
    for nummer, zellen in enumerate(reihen, start=1):
        teile = []
        for spalte, (attribute, inhalt, breite) in enumerate(zellen, start=1):
            breiten[spalte] = max(breiten.get(spalte, 0), breite)
            teile.append(f'<c r="{spaltenbuchstabe(spalte)}{nummer}"{attribute}>{inhalt}</c>')
        xml.append(f'<row r="{nummer}">{"".join(teile)}</row>' if teile else f'<row r="{nummer}"/>')
    spalten = "".join(f'<col min="{s}" max="{s}" width="{min(max(b + 2, 10), 60)}" customWidth="1"/>'
                      for s, b in sorted(breiten.items()))
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            f'<worksheet xmlns="{_NS}" xmlns:r="{_NS_R}">' + (f"<cols>{spalten}</cols>" if spalten else "")
            + f'<sheetData>{"".join(xml)}</sheetData></worksheet>')


def _blattname(wunsch, vergeben):
    name = _BLATT_VERBOTEN.sub("", _UNZULAESSIG.sub("", str(wunsch))).strip().strip("'")[:31].strip() or "Sheet"
    kandidat, n = name, 1
    while kandidat.lower() in (v.lower() for v in vergeben):
        n += 1
        zusatz = f" ({n})"
        kandidat = name[:31 - len(zusatz)].rstrip() + zusatz
    return kandidat


def _workbook(namen):
    blaetter = "".join(f'<sheet name={quoteattr(name)} sheetId="{i}" r:id="rId{i}"/>'
                       for i, name in enumerate(namen, start=1))
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            f'<workbook xmlns="{_NS}" xmlns:r="{_NS_R}"><sheets>{blaetter}</sheets></workbook>')


def _content_types(anzahl):
    blaetter = "".join(f'<Override PartName="/xl/worksheets/sheet{i}.xml" '
                       'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
                       for i in range(1, anzahl + 1))
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            f'{blaetter}<Override PartName="/xl/styles.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
            "</Types>")


def _workbook_rels(anzahl):
    blaetter = "".join(f'<Relationship Id="rId{i}" '
                       'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
                       f'Target="worksheets/sheet{i}.xml"/>' for i in range(1, anzahl + 1))
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            f'{blaetter}<Relationship Id="rId{anzahl + 1}" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
            'Target="styles.xml"/></Relationships>')


def _styles(formate):
    numfmts = "".join(f'<numFmt numFmtId="{164 + i}" formatCode={quoteattr(f)}/>' for i, f in enumerate(formate))
    xfs = "".join(f'<xf numFmtId="{164 + i}" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>'
                  for i in range(len(formate)))
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            f'<styleSheet xmlns="{_NS}">'
            + (f'<numFmts count="{len(formate)}">{numfmts}</numFmts>' if formate else "")
            + '<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font>'
            '<font><b/><sz val="11"/><name val="Calibri"/></font></fonts>'
            '<fills count="2"><fill><patternFill patternType="none"/></fill>'
            '<fill><patternFill patternType="gray125"/></fill></fills>'
            '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
            '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
            f'<cellXfs count="{2 + len(formate)}"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
            f'<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/>{xfs}</cellXfs>'
            '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
            "</styleSheet>")


_RELS = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
         '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
         '<Relationship Id="rId1" '
         'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
         'Target="xl/workbook.xml"/></Relationships>')
