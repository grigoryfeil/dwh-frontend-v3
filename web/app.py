"""Backend der Oberfläche von DWH Frontend V3: Login, Fragen an den Harness, Nachfragen im selben Gespräch.

Vertrag wie die Oberfläche aus V2 ihn erwartet (`oberflaeche/src/api.ts`): Eine Frage läuft im Hintergrund, die
Seite fragt alle zwei Sekunden den Stand ab. Ein Gespräch ist ein `harness.sitzung.Gespraech`, das zwischen den
Runden offen bleibt und nach Leerlauf endet. Gespräche liegen nur im Arbeitsspeicher und gehören der Session, die
sie begonnen hat. Endet die Session, enden ihre Gespräche. TLS übernimmt nginx.

Bedient wird nur, was die Oberfläche braucht. Export, Feedback, Ablage und Beispiele gibt es nicht, die Oberfläche
kommt ohne sie aus (Antwort 404 bzw. `ablage: false`). Felder ohne V3-Gegenstück (`beleg`, `abfragen`, `pruefung`)
bleiben leer. SQL geht nicht an die Seite. Dateien, die die Antwort im eigenen Gesprächsverzeichnis nennt (etwa
Diagramme und Dashboards), übersetzt web/dateien.py in `dateien` und liefert nur diese aus. Mit eingeschalteter
Beta-Ablage (web/ablage.py) wird jedes Gespräch vollständig abgelegt, die Seite zeigt das an und bietet Feedback.
"""

import asyncio
import datetime
import hashlib
import hmac
import json
import os
import re
import secrets
import shutil
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.requests import Request
from starlette.responses import FileResponse, HTMLResponse, JSONResponse, Response
from starlette.routing import Route

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER.parent / "harness"))
import kontext  # noqa: E402
import lauf  # noqa: E402
from sitzung import Gespraech, Sitzungsfehler  # noqa: E402

from web import ablage as ablage_modul, dateien, fortschritt, konten  # noqa: E402

STATISCH = HIER / "statisch"  # Build von oberflaeche/ (npm run build), eingecheckt, der VPS braucht kein npm
ASSET = re.compile(r"[\w-]+\.(js|css|woff2|svg)")
ASSET_ARTEN = {"js": "text/javascript", "css": "text/css", "woff2": "font/woff2", "svg": "image/svg+xml"}
KENNUNG = re.compile(r"[0-9a-f]{32}")
COOKIE = "__Host-dwhv3"
SEITEN_KOEPFE = {
    "Content-Security-Policy": ("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
                                "img-src 'self' data:; frame-src 'self'; frame-ancestors 'none'; base-uri 'none'; "
                                "form-action 'self'"),
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store",
}


@dataclass
class Einstellungen:
    konten: Path  # von root gepflegt mit web/konten.py, das Backend liest nur
    gespraeche: Path  # je Gespräch ein Arbeitsverzeichnis, beim Ende entfernt
    protokoll: Path | None = None  # nur Technik: Zeit, Token, Status, keine Fragen oder Antworten
    hosts: list = field(default_factory=lambda: ["localhost"])
    sicher: bool = True  # Cookie nur über HTTPS, lokal zum Testen aus
    zeitlimit: int = 600  # Sekunden je Runde
    max_gespraeche: int = 4  # gleichzeitig offene Modellprozesse
    leerlauf: int = 1800  # Sekunden ohne Frage, danach endet ein Gespräch
    abbruch_frist: float = 30  # endet eine abgebrochene Runde so lange nicht, wird das Gespräch geschlossen
    session_leerlauf: int = 3600
    session_absolut: int = 8 * 3600
    direkt: bool = True  # Codex als Kind dieses Prozesses (Unit als dwhv3), sonst über systemd-run (als root)
    ablage: Path | None = None  # Beta-Ablage (web/ablage.py), ohne sie weder Speichern noch Feedback


def datenstand():
    """Stichtag der Lieferung als ISO-Datum und deutsch, aus dem Schema des Lesekontos wie in lauf.py."""
    try:
        deutsch, _schema = lauf.datenstand()
    except (KeyError, ValueError, OSError):
        return None, "?"
    return datetime.datetime.strptime(deutsch, "%d.%m.%Y").date().isoformat(), deutsch


def version():
    for pfad in (HIER.parent / "VERSION", lauf.APP / "VERSION"):
        if pfad.exists():
            return pfad.read_text().strip()
    return "?"


def jetzt_iso():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


class Drossel:
    """Anmeldeversuche je Schlüssel: Eimer mit fünf Versuchen, einer kommt alle 36 Sekunden zurück."""

    def __init__(self, kapazitaet=5, nachfuell_s=36.0):
        self.kapazitaet, self.nachfuell_s = kapazitaet, nachfuell_s
        self._eimer, self._sperre = {}, threading.Lock()

    def verbrauche(self, schluessel):
        with self._sperre:
            jetzt = time.monotonic()
            stand, zeit = self._eimer.get(schluessel, (self.kapazitaet, jetzt))
            stand = min(self.kapazitaet, stand + (jetzt - zeit) / self.nachfuell_s)
            if stand < 1:
                return False, int((1 - stand) * self.nachfuell_s) + 1
            if len(self._eimer) > 1024:
                self._eimer.clear()
            self._eimer[schluessel] = (stand - 1, jetzt)
            return True, 0

    def zuruecksetzen(self, schluessel):
        with self._sperre:
            self._eimer.pop(schluessel, None)


@dataclass
class Session:
    email: str
    begonnen: float
    zuletzt: float
    ref: str = field(default_factory=lambda: secrets.token_hex(8))


class Eintrag:
    """Ein Gespräch der Oberfläche: Modellprozess, Runden und Zustand der laufenden Runde."""

    def __init__(self, kennung, cwd, besitzer, benutzer=None):
        self.kennung, self.cwd, self.besitzer, self.benutzer = kennung, cwd, besitzer, benutzer
        self.begonnen = jetzt_iso()
        self.speichern = False  # Beta-Ablage: Runden, die bei eingeschaltetem Speichern enden, werden abgelegt
        self.archiv = {}  # Nummer -> vollständige Runde für die Ablage, auch für ein späteres Einschalten
        self.gespeichert = set()
        self.ablage_sperre = threading.Lock()
        self.gespraech = None  # wird im Hintergrund gestartet, das dauert einige Sekunden
        self.runden = []
        self.laeuft = False
        self.beendet = False  # nach einem Fehler ist der Zustand des Modellprozesses unklar
        self.abbruch = None
        self.fortschritt = None
        self.zuletzt = time.monotonic()
        self._zu = threading.Lock()

    @property
    def status(self):
        return "laeuft" if self.laeuft else "fehler" if self.beendet else "fertig"

    def schliessen(self):
        self.beendet = True
        if self._zu.acquire(blocking=False):
            if self.gespraech is not None:
                try:
                    self.gespraech.__exit__(None, None, None)
                except Exception:  # noqa: BLE001, auch ein halb gestarteter Prozess wird geschlossen
                    pass
            shutil.rmtree(self.cwd, ignore_errors=True)


def json_body(request_body, felder):
    try:
        daten = json.loads(request_body or b"{}")
    except ValueError:
        return None
    return daten if isinstance(daten, dict) and all(isinstance(daten.get(k, t()), t) for k, t in felder) else None


def erzeuge(e: Einstellungen, gespraech_fabrik=None):
    stand_iso, stand_deutsch = datenstand()
    anweisung = kontext.anweisung(lauf.APP / "katalog", lauf.APP / "wissen", stand_deutsch) \
        if gespraech_fabrik is None else ""
    if gespraech_fabrik is None:
        def gespraech_fabrik(cwd):
            return Gespraech(cwd, anweisung, zeitlimit=e.zeitlimit, direkt=e.direkt)

    ablage = ablage_modul.Ablage(e.ablage) if e.ablage else None
    pruefsumme = None
    if ablage and anweisung:
        try:
            pruefsumme = ablage.anweisung(anweisung)
        except OSError as fehl:
            ablage_modul.melde(fehl)
    for alt in e.gespraeche.glob("web-*"):  # Gespräche überleben keinen Neustart
        shutil.rmtree(alt, ignore_errors=True)
    kontendatei = konten.Konten(e.konten)
    drossel = Drossel()
    sessions = {}  # HMAC des Tokens -> Session
    gespraeche = {}
    sperre = threading.Lock()
    geheim = secrets.token_bytes(32)
    protokoll_sperre = threading.Lock()

    def schluessel(token):
        return hmac.new(geheim, token.encode(), hashlib.sha256).hexdigest()

    def protokolliere(eintrag, nummer, status, runde=None, fehler=None):
        if not e.protokoll:
            return
        zeile = {"zeit": jetzt_iso(), "version": version(), "gespraech": eintrag.kennung, "runde": nummer,
                 "status": status, "fehler": fehler,
                 "codex": getattr(eintrag.gespraech, "codex_version", None)}
        if runde is not None:
            zeile.update(sekunden=runde.sekunden, token=runde.token, modellanfragen=runde.modellanfragen,
                         sql=sum(i.get("type") == "mcpToolCall" for i in runde.items))
        try:
            with protokoll_sperre, open(e.protokoll, "a", encoding="utf-8") as datei:
                datei.write(json.dumps(zeile, ensure_ascii=False) + "\n")
        except OSError:
            pass

    # Sessions

    def session_beenden(schl):
        s = sessions.pop(schl, None)
        if s is None:
            return
        eigene = [g for g in gespraeche.values() if g.besitzer == s.ref]
        for g in eigene:
            del gespraeche[g.kennung]
        return eigene

    def hole_session(request):
        token = request.cookies.get(COOKIE)
        if not token:
            return None
        jetzt = time.monotonic()
        with sperre:
            s = sessions.get(schluessel(token))
            if s is None:
                return None
            if jetzt - s.zuletzt > e.session_leerlauf or jetzt - s.begonnen > e.session_absolut \
                    or not kontendatei.aktiv(s.email):
                eigene = session_beenden(schluessel(token)) or []
            else:
                s.zuletzt = jetzt
                return s
        for g in eigene:
            g.schliessen()
        return None

    def raeumen():
        """Leerlauf: abgelaufene Sessions und ruhende Gespräche schließen, jede Minute."""
        while True:
            time.sleep(60)
            jetzt = time.monotonic()
            zu = []
            with sperre:
                for schl, s in list(sessions.items()):
                    if jetzt - s.zuletzt > e.session_leerlauf or jetzt - s.begonnen > e.session_absolut:
                        zu += session_beenden(schl) or []
                for g in list(gespraeche.values()):
                    if not g.laeuft and jetzt - g.zuletzt > e.leerlauf:
                        del gespraeche[g.kennung]
                        zu.append(g)
            for g in zu:
                g.schliessen()

    threading.Thread(target=raeumen, daemon=True).start()

    def nicht_angemeldet():
        return JSONResponse({"detail": "Bitte anmelden"}, status_code=401)

    def fehler(status, text):
        return JSONResponse({"detail": text}, status_code=status)

    # Runde im Hintergrund

    def sichern(eintrag):
        """Legt alle festgehaltenen, noch nicht abgelegten Runden samt Dateien ab und schreibt das Gespräch neu."""
        datum = eintrag.begonnen[:10]
        try:
            with eintrag.ablage_sperre:
                for n in sorted(set(eintrag.archiv) - eintrag.gespeichert):
                    runde = eintrag.archiv[n]
                    runde["abgelegte_dateien"] = ablage.dateien(datum, eintrag.kennung, n, runde.pop("neue_dateien", []),
                                                                lambda name: dateien.oeffne(eintrag.cwd, name))
                    eintrag.gespeichert.add(n)
                schema = None
                try:
                    schema = lauf.datenstand()[1]
                except (KeyError, ValueError, OSError):
                    pass
                ablage.gespraech(datum, eintrag.kennung, {
                    "gespraech": eintrag.kennung, "benutzer": eintrag.benutzer, "begonnen": eintrag.begonnen,
                    "version": version(), "datenstand": stand_iso, "schema": schema,
                    "codex": getattr(eintrag.gespraech, "codex_version", None),
                    "modell": getattr(eintrag.gespraech, "modell", None),
                    "aufwand": getattr(eintrag.gespraech, "aufwand", None), "anweisung": pruefsumme,
                    "runden": [eintrag.archiv[n] for n in sorted(eintrag.gespeichert)]})
        except OSError as fehl:
            ablage_modul.melde(fehl)

    def archiviere(eintrag, nummer, runde, status, items, vorher, ergebnis=None):
        """Hält die beendete Runde vollständig fest und legt sie ab, wenn Speichern an ist. Vor dem Schließen des
        Gesprächs aufrufen, danach ist sein Verzeichnis fort."""
        if not ablage:
            return
        try:
            neu = ablage_modul.neue_dateien(vorher, ablage_modul.dateistand(eintrag.cwd))
            eintrag_runde = {
                "nummer": nummer, "frage": runde["frage"], "zeit": runde["zeit"], "status": status,
                "fehler": runde.get("fehler"), "verifizieren": runde.get("verifizieren"),
                "antwort": runde.get("antwort"),
                "antwort_modell": ergebnis.text if ergebnis and ergebnis.text != runde.get("antwort") else None,
                "dateien": runde.get("dateien") or [],
                "sekunden": ergebnis.sekunden if ergebnis else None, "token": ergebnis.token if ergebnis else None,
                "modellanfragen": ergebnis.modellanfragen if ergebnis else None,
                "schritte": [s for s in map(ablage_modul.schritt, items) if s], "neue_dateien": neu}
            with eintrag.ablage_sperre:
                eintrag.archiv[nummer] = eintrag_runde
        except Exception as fehl:  # noqa: BLE001, die Ablage stört das Gespräch nie
            ablage_modul.melde(fehl)
            return
        if eintrag.speichern:
            sichern(eintrag)

    def beantworte(eintrag, runde):
        nummer = len(eintrag.runden)
        beobachter = fortschritt.Fortschritt()
        items = []  # abgeschlossene Items der Runde, auch für abgebrochene und gescheiterte Runden
        vorher = ablage_modul.dateistand(eintrag.cwd) if ablage else {}
        with sperre:
            eintrag.fortschritt = beobachter

        def beobachte(n, g):
            beobachter.ereignis(n, g._turn_id)
            p = n.get("params") or {}
            if n.get("method") == "item/completed" and p.get("turnId") == g._turn_id:
                items.append(p.get("item") or {})

        def abgebrochen(ergebnis=None):
            protokolliere(eintrag, nummer, "abgebrochen", ergebnis)
            with sperre:
                runde["abgebrochen"] = True
                eintrag.laeuft, eintrag.abbruch, eintrag.fortschritt = False, None, None
                eintrag.zuletzt = time.monotonic()
            archiviere(eintrag, nummer, runde, "abgebrochen", items, vorher, ergebnis)

        try:
            if eintrag.gespraech is None:
                g = gespraech_fabrik(eintrag.cwd)
                eintrag.gespraech = g
                g.__enter__()
            if eintrag.abbruch:
                raise Sitzungsfehler("Runde abgebrochen")
            g = eintrag.gespraech
            ergebnis = g.frage(runde["frage"], beobachter=lambda n: beobachte(n, g))
        except Exception as fehl:  # noqa: BLE001, jede Ausnahme beendet die Runde
            if eintrag.abbruch and isinstance(fehl, Sitzungsfehler) and eintrag.gespraech is not None \
                    and eintrag.gespraech.thread_id:
                return abgebrochen()
            meldung = str(fehl) if isinstance(fehl, Sitzungsfehler) else "interner Fehler"
            protokolliere(eintrag, nummer, "fehler", fehler=meldung)
            with sperre:
                if eintrag.abbruch:
                    runde["abgebrochen"] = True
                else:
                    runde["fehler"] = meldung
                eintrag.laeuft, eintrag.fortschritt = False, None
            archiviere(eintrag, nummer, runde, "abgebrochen" if eintrag.abbruch else "fehler", items, vorher)
            eintrag.schliessen()
            return
        if eintrag.abbruch:  # wer abbricht, will die Antwort nicht mehr, auch wenn sie schon stand
            return abgebrochen(ergebnis)
        protokolliere(eintrag, nummer, "fertig", ergebnis)
        antwort, gemeldet = dateien.uebersetze(ergebnis.text, eintrag.cwd, eintrag.kennung)
        with sperre:
            runde.update(antwort=antwort, dateien=gemeldet, ms=int(ergebnis.sekunden * 1000),
                         stufen=beobachter.stufen(fertig=True), schritte=beobachter.schritte)
            eintrag.laeuft, eintrag.fortschritt = False, None
            eintrag.zuletzt = time.monotonic()
        archiviere(eintrag, nummer, runde, "fertig", ergebnis.items, vorher, ergebnis)

    # Routen

    def seite(_request):
        return HTMLResponse((STATISCH / "index.html").read_text(encoding="utf-8"))

    def asset(request):
        name = request.path_params["name"]
        pfad = STATISCH / "assets" / name
        if not ASSET.fullmatch(name) or not pfad.is_file():
            return fehler(404, "Datei unbekannt")
        return FileResponse(pfad, media_type=ASSET_ARTEN[name.rsplit(".", 1)[1]],
                            headers={"Cache-Control": "public, max-age=31536000, immutable"})

    def stand_der_daten(_request):
        return JSONResponse({"datenstand": stand_iso, "version": version(), "zeitlimit": e.zeitlimit,
                             "definitionen_vorlaeufig": False})

    async def anmelden(request):
        daten = json_body(await request.body(), [("email", str), ("passwort", str)])
        if daten is None or len(daten.get("email", "")) > 320 or len(daten.get("passwort", "")) > 256:
            return fehler(422, "Ungültige Anmeldung")
        email = konten.normalisiere(daten.get("email", ""))
        adresse = request.client.host if request.client else "?"
        for schl in (f"ip:{adresse}", f"konto:{email}"):
            erlaubt, warte = drossel.verbrauche(schl)
            if not erlaubt:
                return JSONResponse({"detail": f"Zu viele Versuche, bitte in {warte} Sekunden erneut"},
                                    status_code=429, headers={"Retry-After": str(warte)})
        if not kontendatei.pruefe(email, daten.get("passwort", "")):
            return fehler(401, "E-Mail oder Passwort stimmt nicht")
        drossel.zuruecksetzen(f"konto:{email}")
        token = secrets.token_urlsafe(32)
        jetzt = time.monotonic()
        alt = request.cookies.get(COOKIE)
        with sperre:
            zu = session_beenden(schluessel(alt)) if alt else None
            sessions[schluessel(token)] = Session(email, jetzt, jetzt)
        for g in zu or []:
            g.schliessen()
        antwort = JSONResponse({"email": email})
        antwort.set_cookie(COOKIE, token, max_age=e.session_absolut, httponly=True, secure=e.sicher,
                           samesite="strict", path="/")
        return antwort

    def abmelden(request):
        token = request.cookies.get(COOKIE)
        with sperre:
            zu = session_beenden(schluessel(token)) if token else None
        for g in zu or []:
            g.schliessen()
        antwort = Response(status_code=204)
        antwort.delete_cookie(COOKIE, path="/", secure=e.sicher, httponly=True, samesite="strict")
        return antwort

    def ich(request):
        s = hole_session(request)
        if s is None:
            return nicht_angemeldet()
        return JSONResponse({"email": s.email, "ablage": ablage is not None})

    async def fragen(request):
        s = hole_session(request)
        if s is None:
            return nicht_angemeldet()
        # `verifizieren` wird später der optionale Prüfrunden-Schalter (README, Bauweise). Bis dahin angenommen
        # und ignoriert, ebenso `schnell`. `speichern` ist der Schalter der Seite für die Beta-Ablage.
        daten = json_body(await request.body(), [("text", str), ("verifizieren", bool), ("schnell", bool),
                                                 ("speichern", bool)])
        if daten is None:
            return fehler(422, "Ungültige Frage")
        text = (daten.get("text") or "").strip()
        kennung = daten.get("gespraech")
        if not text or len(text) > 4000 or not (kennung is None or isinstance(kennung, str)):
            return fehler(422, "Ungültige Frage")
        runde = {"frage": text, "verifizieren": bool(daten.get("verifizieren")),
                 "schnell": bool(daten.get("schnell")), "zeit": jetzt_iso(),
                 "abfragen": [], "beleg": [], "dateien": []}
        with sperre:
            if kennung is None:
                for g in [g for g in gespraeche.values() if not g.laeuft and g.beendet]:
                    del gespraeche[g.kennung]
                if sum(1 for g in gespraeche.values() if not g.beendet) >= e.max_gespraeche:
                    return fehler(503, "Alle Plätze belegt, bitte später erneut versuchen")
                kennung = secrets.token_hex(16)
                cwd = e.gespraeche / f"web-{kennung}"
                cwd.mkdir(mode=0o750)
                eintrag = Eintrag(kennung, cwd, s.ref, s.email)
                gespraeche[kennung] = eintrag
            else:
                eintrag = gespraeche.get(kennung)
                if eintrag is None or eintrag.besitzer != s.ref:
                    return fehler(404, "Gespräch unbekannt")
                if eintrag.beendet:
                    return fehler(410, "Gespräch beendet, bitte ein neues beginnen")
                if eintrag.laeuft:
                    return fehler(409, "Im Gespräch läuft noch eine Frage")
            eintrag.runden.append(runde)
            eintrag.speichern = bool(daten.get("speichern")) and ablage is not None
            eintrag.laeuft = True
            eintrag.abbruch = None
            eintrag.zuletzt = time.monotonic()
        threading.Thread(target=beantworte, args=(eintrag, runde), daemon=True).start()
        return JSONResponse({"gespraech": kennung}, status_code=202)

    def eigenes(request, s):
        kennung = request.path_params["kennung"]
        eintrag = gespraeche.get(kennung) if KENNUNG.fullmatch(kennung) else None
        return eintrag if eintrag is not None and eintrag.besitzer == s.ref else None

    def gespraech(request):
        s = hole_session(request)
        if s is None:
            return nicht_angemeldet()
        if request.method == "DELETE":
            with sperre:
                eintrag = eigenes(request, s)
                if eintrag is None:
                    return fehler(404, "Gespräch unbekannt")
                if eintrag.laeuft:
                    return fehler(409, "Im Gespräch läuft noch eine Frage")
                del gespraeche[eintrag.kennung]
            eintrag.schliessen()
            return Response(status_code=204)
        with sperre:
            eintrag = eigenes(request, s)
            if eintrag is None:
                return fehler(404, "Gespräch unbekannt")
            runden = [dict(r) for r in eintrag.runden]
            if eintrag.laeuft and eintrag.fortschritt:
                runden[-1].update(stufen=eintrag.fortschritt.stufen(), schritte=list(eintrag.fortschritt.schritte),
                                  sekunden=eintrag.fortschritt.sekunden())
            return JSONResponse({"status": eintrag.status, "runden": runden})

    def datei(request):
        """Nur Dateien, die eine Antwort dieses Gesprächs gemeldet hat (web/dateien.py)."""
        s = hole_session(request)
        if s is None:
            return nicht_angemeldet()
        name = request.path_params["name"]
        with sperre:
            eintrag = eigenes(request, s)
            gemeldet = eintrag is not None and any(d["name"] == name for r in eintrag.runden
                                                   for d in r.get("dateien") or [])
        datei_ = dateien.oeffne(eintrag.cwd, name) if gemeldet else None
        if datei_ is None:
            return fehler(404, "Datei unbekannt")
        with datei_:
            inhalt = datei_.read(50_000_000)
        inhalt, art, koepfe = dateien.auslieferung(name, inhalt, request.headers.get("sec-fetch-dest"))
        return Response(inhalt, media_type=art, headers=koepfe)

    async def speichern_schalten(request):
        """Beta: Speichern an oder aus, gilt für jede Runde, die danach endet. Einschalten legt auch die früheren
        Runden des Gesprächs ab."""
        s = hole_session(request)
        if s is None:
            return nicht_angemeldet()
        daten = json_body(await request.body(), [("an", bool)])
        if not ablage:
            return fehler(503, "Speichern ist auf diesem Server abgeschaltet")
        if daten is None:
            return fehler(422, "Ungültiger Schalter")
        with sperre:
            eintrag = eigenes(request, s)
            if eintrag is None:
                return fehler(404, "Gespräch unbekannt")
            eintrag.speichern = bool(daten.get("an"))
        if eintrag.speichern:
            await asyncio.to_thread(sichern, eintrag)
        return JSONResponse({"speichern": eintrag.speichern})

    async def feedback(request):
        """Beta: Rückmeldung in die Ablage, mit dem Gespräch auf Wunsch auch nachträglich gesichert."""
        s = hole_session(request)
        if s is None:
            return nicht_angemeldet()
        if not ablage:
            return fehler(503, "Feedback ist auf diesem Server abgeschaltet")
        daten = json_body(await request.body(), [("text", str), ("mitsenden", bool)])
        text = (daten or {}).get("text", "").strip()
        kennung = (daten or {}).get("gespraech")
        if not text or len(text) > 4000 or not (kennung is None or isinstance(kennung, str)):
            return fehler(422, "Ungültiges Feedback")
        eintrag = None
        if kennung and daten.get("mitsenden", True):
            with sperre:
                eintrag = gespraeche.get(kennung)
                if eintrag is None or eintrag.besitzer != s.ref:
                    return fehler(404, "Gespräch unbekannt")
            await asyncio.to_thread(sichern, eintrag)
        try:
            name = ablage.feedback({"zeit": jetzt_iso(), "benutzer": s.email, "text": text, "gespraech": kennung,
                                    "ablage": f"{eintrag.begonnen[:10]}/{kennung}" if eintrag else None,
                                    "version": version()})
        except OSError:
            return fehler(503, "Feedback konnte nicht abgelegt werden")
        return JSONResponse({"feedback": name}, status_code=201)

    def abbrechen(request):
        s = hole_session(request)
        if s is None:
            return nicht_angemeldet()
        marke = object()
        with sperre:
            eintrag = eigenes(request, s)
            if eintrag is None:
                return fehler(404, "Gespräch unbekannt")
            if not eintrag.laeuft:
                return fehler(409, "Im Gespräch läuft keine Frage")
            eintrag.abbruch = marke
        try:
            if eintrag.gespraech is not None and eintrag.gespraech.thread_id:
                eintrag.gespraech.unterbrechen()
        except (OSError, ValueError):
            pass

        def notbremse():
            with sperre:
                haengt = eintrag.laeuft and eintrag.abbruch is marke
            if haengt:
                eintrag.schliessen()

        zeitgeber = threading.Timer(e.abbruch_frist, notbremse)
        zeitgeber.daemon = True
        zeitgeber.start()
        return JSONResponse({"gespraech": eintrag.kennung}, status_code=202)

    # Schutz: schreibende Anfragen nur als JSON und von der eigenen Herkunft, feste Sicherheitsköpfe

    herkuenfte = {f"https://{h}" for h in e.hosts} | ({f"http://{h}" for h in e.hosts} if not e.sicher else set())

    class Schutz:
        def __init__(self, app):
            self.app = app

        async def __call__(self, scope, receive, send):
            if scope["type"] != "http":
                return await self.app(scope, receive, send)
            koepfe = {k.decode("latin-1"): v.decode("latin-1") for k, v in scope["headers"]}
            if scope["method"] not in ("GET", "HEAD"):
                grund = None
                herkunft = koepfe.get("origin")
                if herkunft is not None and herkunft not in herkuenfte:
                    grund = (403, "fremde Herkunft")
                elif koepfe.get("sec-fetch-site", "same-origin") not in ("same-origin", "none"):
                    grund = (403, "fremde Herkunft")
                elif not koepfe.get("content-type", "").startswith("application/json"):
                    grund = (415, "nur JSON")
                if grund:
                    return await fehler(*grund)(scope, receive, send)

            async def senden(nachricht):
                if nachricht["type"] == "http.response.start":
                    vorhanden = {k.decode("latin-1").lower() for k, _ in nachricht.get("headers", [])}
                    zusatz = [(k.encode(), v.encode()) for k, v in SEITEN_KOEPFE.items() if k.lower() not in vorhanden]
                    nachricht["headers"] = list(nachricht.get("headers", [])) + zusatz
                await send(nachricht)

            return await self.app(scope, receive, senden)

    routen = [
        Route("/", seite),
        Route("/assets/{name}", asset),
        Route("/api/stand", stand_der_daten),
        Route("/api/anmelden", anmelden, methods=["POST"]),
        Route("/api/abmelden", abmelden, methods=["POST"]),
        Route("/api/ich", ich),
        Route("/api/fragen", fragen, methods=["POST"]),
        Route("/api/gespraeche/{kennung}", gespraech, methods=["GET", "DELETE"]),
        Route("/api/gespraeche/{kennung}/abbrechen", abbrechen, methods=["POST"]),
        Route("/api/gespraeche/{kennung}/dateien/{name:path}", datei),
        Route("/api/gespraeche/{kennung}/speichern", speichern_schalten, methods=["POST"]),
        Route("/api/feedback", feedback, methods=["POST"]),
    ]
    return Starlette(routes=routen, middleware=[Middleware(TrustedHostMiddleware, allowed_hosts=e.hosts),
                                                Middleware(Schutz)])


def aus_umgebung():
    """Startpunkt für uvicorn --factory, Einstellungen aus der Umgebung der Unit."""
    return erzeuge(Einstellungen(
        konten=Path(os.environ["DWH_V3_KONTEN"]),
        gespraeche=Path(os.environ.get("DWH_V3_GESPRAECHE", "/var/lib/dwh-frontend-v3/gespraeche")),
        protokoll=Path(os.environ["DWH_V3_PROTOKOLL"]) if os.environ.get("DWH_V3_PROTOKOLL") else None,
        hosts=os.environ.get("DWH_V3_HOSTS", "localhost").split(","),
        sicher=os.environ.get("DWH_V3_UNSICHER") != "1",
        zeitlimit=int(os.environ.get("DWH_V3_ZEITLIMIT", "600")),
        direkt=os.environ.get("DWH_V3_DIREKT", "1") == "1",
        ablage=Path(os.environ.get("DWH_V3_ABLAGE_PFAD", "/var/lib/dwh-frontend-v3/ablage"))
        if os.environ.get("DWH_ABLAGE") == "1" else None,
    ))
