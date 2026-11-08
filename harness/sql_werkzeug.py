"""MCP-Server `dwh` mit genau einem Werkzeug: `sql`, lesend auf der DWH-Kopie.

Codex startet ihn als Kindprozess außerhalb der Shell-Sandbox des Modells. Nur dieser Prozess liest die
Optionsdatei des Lesekontos (`DWH_OPTIONSDATEI`) und erreicht den DB-Socket. Das Lesekonto darf nur SELECT.
"""

import configparser
import datetime
import decimal
import json
import os

import pymysql

ZEILEN_MAX = int(os.environ.get("DWH_ZEILEN_MAX", "1000"))
OPTIONSDATEI = os.environ["DWH_OPTIONSDATEI"]


def _schema():
    optionen = configparser.ConfigParser(interpolation=None)
    optionen.read(OPTIONSDATEI)
    return optionen["client"]["database"]


def _json_wert(wert):
    if isinstance(wert, decimal.Decimal):
        return str(wert)
    if isinstance(wert, (datetime.date, datetime.datetime, datetime.time)):
        return wert.isoformat()
    if isinstance(wert, datetime.timedelta):
        return str(wert)
    if isinstance(wert, (bytes, bytearray)):
        return wert.hex()
    return wert


def sql_ausfuehren(abfrage):
    try:
        verbindung = pymysql.connect(read_default_file=OPTIONSDATEI)
    except pymysql.MySQLError as fehler:
        return {"fehler": str(fehler)}
    offen = []
    try:
        # Ungepuffert: Der normale Cursor lädt das ganze Ergebnis schon bei execute in den Speicher, die Zeilengrenze
        # käme zu spät. Nach der Grenze wird die Verbindung geschlossen, ohne den Rest zu lesen.
        cursor = verbindung.cursor(pymysql.cursors.SSCursor)
        offen.append(cursor)
        cursor.execute(abfrage)
        if cursor.description is None:
            return {"spalten": [], "zeilen": [], "gekuerzt": False}
        spalten = [b[0] for b in cursor.description]
        zeilen = [[_json_wert(w) for w in z] for z in cursor.fetchmany(ZEILEN_MAX + 1)]
        return {"spalten": spalten, "zeilen": zeilen[:ZEILEN_MAX], "gekuerzt": len(zeilen) > ZEILEN_MAX}
    except pymysql.MySQLError as fehler:
        return {"fehler": str(fehler)}
    finally:
        for cursor in offen:  # den ungelesenen Rest verwerfen statt ihn beim Aufräumen doch noch abzuholen
            if cursor._result is not None:
                cursor._result.unbuffered_active = False
                cursor._result = None
        try:
            verbindung.close()
        except Exception:  # noqa: BLE001, beim Abbruch eines ungelesenen Ergebnisses
            pass


def main():
    from mcp.server.mcpserver import MCPServer
    from mcp.types import ToolAnnotations

    mcp = MCPServer("dwh")
    beschreibung = (
        f"Führt eine lesende SQL-Abfrage (MariaDB 10.6) auf der DWH-Kopie aus. Standardschema ist `{_schema()}`. "
        f"Liefert JSON mit `spalten`, `zeilen` und `gekuerzt` (mehr als {ZEILEN_MAX} Zeilen) oder `fehler`. "
        "Dezimalzahlen kommen als exakter Text."
    )

    @mcp.tool(description=beschreibung, annotations=ToolAnnotations(readOnlyHint=True))
    def sql(abfrage: str) -> str:
        return json.dumps(sql_ausfuehren(abfrage), ensure_ascii=False)

    mcp.run()


if __name__ == "__main__":
    main()
