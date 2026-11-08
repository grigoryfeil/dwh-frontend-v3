"""Dateien, die das Modell im eigenen Gesprächsverzeichnis ablegt und in der Antwort nennt, etwa Diagramme.

Das Modell verweist mit absolutem Pfad (`/var/lib/dwh-frontend-v3/gespraeche/web-<id>/bild.png`) oder relativ
(`bild.png`) darauf. Solche Verweise werden in den Vertrag der Oberfläche übersetzt
(`/api/gespraeche/<id>/dateien/<name>`) und als `dateien` der Runde gemeldet. Nur gemeldete Dateien werden
ausgeliefert, nur reguläre Dateien innerhalb des Verzeichnisses, ohne Symlinks: Bilder, Tabellen und Dashboards.
Andere Pfade bleiben Text.

Dashboards (Data App des Data-Plugins) sind eigenständiges HTML mit Skript und eingebetteten Daten. Sie laufen nur im
Rahmen der eigenen Seite (`Sec-Fetch-Dest: iframe`, `frame-ancestors 'self'`) in einer Sandbox mit fremdem Ursprung,
ohne Netz (kein `connect-src`), ohne Formulare und Navigation. Als eigene Seite aufgerufen kommen sie als Quelltext,
der nichts ausführt; so liest die Oberfläche auch den Titel. SVG bleibt draußen, es trüge Skript in ein `<img>`.
"""

import os
import re
import stat
from urllib.parse import quote, unquote

ARTEN = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "gif": "image/gif", "webp": "image/webp",
         "csv": "text/csv", "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
         "html": "text/html; charset=utf-8", "htm": "text/html; charset=utf-8"}
BILD = {"png", "jpg", "jpeg", "gif", "webp"}
HTML = {"html", "htm"}
NAME = re.compile(r"[\w][\w.\- ]{0,200}(?:/[\w][\w.\- ]{0,200}){0,4}")
KOEPFE = {"Content-Security-Policy": "default-src 'none'; sandbox", "X-Content-Type-Options": "nosniff"}
# data: in script-src, weil die Laufzeit der Data App als <script src="data:..."> in der Datei steckt. Das ist kein
# Netz und erlaubt nichts, was 'unsafe-inline' nicht schon erlaubt. Kein connect-src: Nachladen bleibt gesperrt.
DASHBOARD_CSP = ("sandbox allow-scripts; default-src 'none'; script-src 'unsafe-inline' data:; style-src 'unsafe-inline'; "
                 "img-src data: blob:; font-src data:; base-uri 'none'; form-action 'none'; frame-ancestors 'self'")
# Knöpfe der Data App, die nur in ChatGPT funktionieren (Veröffentlichen, Fragen, Bearbeiten, Menü), wie in V2
AUSBLENDEN = (b"<style>.dashboard-publish-button,.dashboard-publish-confirm,.publish-review-dialog,.dashboard-ask-anchor,"
              b".dashboard-ask-button,.dashboard-ask-panel,.dashboard-header-edit-button,"
              b".dashboard-header-overflow-button{display:none!important}</style>")
ANKER = [re.compile(rb"<" + tag + rb"\b[^>]{0,1000}>", re.I) for tag in (rb"head", rb"html", rb"!doctype")]


def auslieferung(name, inhalt, ziel):
    """Inhalt, Medientyp und Köpfe für eine gemeldete Datei. `ziel` ist Sec-Fetch-Dest der Anfrage."""
    endung = name.rsplit(".", 1)[-1].lower()
    if endung in HTML:
        koepfe = {"Content-Security-Policy": DASHBOARD_CSP, "X-Content-Type-Options": "nosniff",
                  "Content-Disposition": "inline"}
        if ziel != "iframe":
            return inhalt, "text/plain; charset=utf-8", koepfe
        for anker in ANKER:  # hinter <head>, sonst <html> oder den Doctype, davor fiele es in den Quirks-Modus
            if treffer := anker.search(inhalt):
                return inhalt[:treffer.end()] + AUSBLENDEN + inhalt[treffer.end():], ARTEN[endung], koepfe
        return AUSBLENDEN + inhalt, ARTEN[endung], koepfe
    art = "inline" if endung in BILD else f"attachment; filename=\"{quote(name.split('/')[-1])}\""
    return inhalt, ARTEN[endung], {**KOEPFE, "Content-Disposition": art}


def oeffne(cwd, name):
    """Öffnet cwd/name Teil für Teil ohne Symlinks zu folgen, None wenn es keine reguläre Datei ist."""
    try:
        fd = os.open(cwd, os.O_RDONLY | os.O_DIRECTORY)
    except OSError:
        return None
    try:
        teile = name.split("/")
        for teil in teile[:-1]:
            neu = os.open(teil, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = neu
        datei = os.open(teile[-1], os.O_RDONLY | os.O_NOFOLLOW, dir_fd=fd)
    except OSError:
        return None
    finally:
        os.close(fd)
    if not stat.S_ISREG(os.fstat(datei).st_mode):
        os.close(datei)
        return None
    return os.fdopen(datei, "rb")


def gueltig(cwd, name):
    if not NAME.fullmatch(name) or ".." in name or name.rsplit(".", 1)[-1].lower() not in ARTEN:
        return False
    datei = oeffne(cwd, name)
    if datei is None:
        return False
    datei.close()
    return True


def uebersetze(text, cwd, kennung):
    """Antworttext mit übersetzten Verweisen und die Liste der Dateien [{name, url}] in Reihenfolge."""
    basis = str(cwd).rstrip("/")
    gefunden = {}

    def url(name):
        gefunden.setdefault(name, f"/api/gespraeche/{kennung}/dateien/{quote(name)}")
        return gefunden[name]

    def absolut(m):
        name = unquote(m.group(1))
        return url(name) if gueltig(cwd, name) else m.group(0)

    # absolute Pfade überall im Text, auch mit file://
    text = re.sub(r"(?:file://)?" + re.escape(basis) + r"/([^\s)\]\"'<>`]+)", absolut, text)

    def relativ(m):
        ziel = unquote(m.group(2).removeprefix("./"))
        if re.match(r"^[a-z][a-z0-9+.-]*:|^/|^#", m.group(2), re.I) or not gueltig(cwd, ziel):
            return m.group(0)
        return f"{m.group(1)}({url(ziel)}{m.group(3) or ''})"

    # relative Ziele in Markdown-Links und -Bildern: [text](bild.png) und ![text](bild.png "Titel")
    text = re.sub(r"(\]\s*)\(\s*<?([^\s)<>]+)>?(\s+\"[^\"]*\")?\s*\)", relativ, text)
    return text, [{"name": n, "url": u} for n, u in gefunden.items()]
