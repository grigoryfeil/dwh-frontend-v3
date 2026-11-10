"""Backend der Oberfläche von DWH Frontend V3: Login, Fragen an den Harness, Nachfragen im selben Gespräch.

Vertrag wie die Oberfläche aus V2 ihn erwartet (`oberflaeche/src/api.ts`): Eine Frage läuft im Hintergrund, die
Seite fragt alle zwei Sekunden den Stand ab. Ein Gespräch ist ein `harness.sitzung.Gespraech`, das zwischen den
Runden offen bleibt. Nach Leerlauf, bei Platzmangel oder nach einem Fehler ruht es: Der Modellprozess endet, Verlauf und
Dateien bleiben, die nächste Frage setzt mit dem sichtbaren Verlauf fort. Gespräche liegen nur im Arbeitsspeicher und gehören der Session, die
sie begonnen hat. Endet die Session, enden ihre Gespräche. TLS übernimmt nginx.

Bedient wird nur, was die Oberfläche braucht. Beispiele gibt es nicht, die Oberfläche kommt ohne sie aus (Antwort 404).
Den Export als PDF und Excel bauen web/bericht.py und web/excel.py aus den beantworteten Runden der eigenen Gespräche. Ablage und Feedback gibt es nur mit eingeschalteter Beta-Ablage, sonst `ablage: false`. Felder ohne V3-Gegenstück (`beleg`, `abfragen`) bleiben
leer. SQL geht nie an die Seite (Entscheidung Grigory, 08.11.2026), `abfragen` bleibt deshalb immer leer. Mit dem
Schalter `verifizieren` prüft ein zweites Gespräch die Antwort (harness/pruefung.py), das Ergebnis steht in `pruefung`. Dateien, die die Antwort im eigenen Gesprächsverzeichnis nennt (etwa
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
import pruefung  # noqa: E402
from sitzung import Gespraech, Sitzungsfehler  # noqa: E402

from web import ablage as ablage_modul, antwort as antwort_modul, bericht, dateien, excel, fortschritt  # noqa: E402
from web import konten  # noqa: E402

STATISCH = HIER / "statisch"  # Build von oberflaeche/ (npm run build), eingecheckt, der VPS braucht kein npm
ASSET = re.compile(r"[\w-]+\.(js|css|woff2|svg)")
ASSET_ARTEN = {"js": "text/javascript", "css": "text/css", "woff2": "font/woff2", "svg": "image/svg+xml"}
KENNUNG = re.compile(r"[0-9a-f]{32}")
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
VERLAUF_RUNDEN, VERLAUF_ZEICHEN = 6, 4000  # Verlaufsvorspann nach einer Pause (an_das_modell)
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
    max_behalten: int = 24  # behaltene Gespräche insgesamt (laufend und ruhend), darüber endet das älteste ruhende
    leerlauf: int = 1800  # Sekunden ohne Frage, danach ruht ein Gespräch (Prozess frei, Verlauf bleibt)
    abbruch_frist: float = 30  # endet eine abgebrochene Runde so lange nicht, wird ihr Prozess beendet (Notbremse)
    session_leerlauf: int = 4 * 3600  # Beta: Pausen zwischen Fragen sind länger als eine Stunde
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
        self.pruefer = None  # Prüfgespräch der laufenden Runde, nur während der Prüfrunde
        self.korrektur = None  # von der Prüfrunde korrigierte Antwort, die das Modell noch nicht kennt
        self.runden_ort = None  # gesicherte Dateien je Runde, außerhalb des Arbeitsverzeichnisses (web/dateien.py)
        self.runden = []
        self.laeuft = False
        self.beendet = False  # geschlossen (Session-Ende, Löschen), danach keine Fragen mehr
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
            for prozess in (self.pruefer, self.gespraech):  # auch eine laufende Prüfrunde endet mit dem Gespräch
                if prozess is not None:
                    try:
                        prozess.__exit__(None, None, None)
                    except Exception:  # noqa: BLE001, auch ein halb gestarteter Prozess wird geschlossen
                        pass
            shutil.rmtree(self.cwd, ignore_errors=True)
            if self.runden_ort:
                shutil.rmtree(self.runden_ort, ignore_errors=True)


def json_body(request_body, felder):
    try:
        daten = json.loads(request_body or b"{}")
    except ValueError:
        return None
    return daten if isinstance(daten, dict) and all(isinstance(daten.get(k, t()), t) for k, t in felder) else None


def erzeuge(e: Einstellungen, gespraech_fabrik=None, pruefer_fabrik=None):
    stand_iso, stand_deutsch = datenstand()
    anweisung = kontext.anweisung(lauf.APP / "katalog", lauf.APP / "wissen", stand_deutsch) \
        if gespraech_fabrik is None else ""
    if gespraech_fabrik is None:
        def aktuelle_anweisung():  # je Gespräch neu, damit „heute“ stimmt, auch wenn der Dienst Wochen läuft
            return kontext.anweisung(lauf.APP / "katalog", lauf.APP / "wissen", stand_deutsch)

        def gespraech_fabrik(cwd):
            return Gespraech(cwd, aktuelle_anweisung(), zeitlimit=e.zeitlimit, direkt=e.direkt)

        def pruefer_fabrik(cwd):
            return Gespraech(cwd, aktuelle_anweisung() + pruefung.PRUEFAUFTRAG, zeitlimit=e.zeitlimit,
                             direkt=e.direkt)
    elif pruefer_fabrik is None:
        pruefer_fabrik = gespraech_fabrik

    ablage = ablage_modul.Ablage(e.ablage) if e.ablage else None
    pruefsumme = None
    if ablage and anweisung:
        try:
            pruefsumme = ablage.anweisung(anweisung)
        except OSError as fehl:
            ablage_modul.melde(fehl)
    runden_basis = e.gespraeche.parent / "runden"  # für die Modell-Shell gesperrt (codex-config.toml)
    for alt in list(e.gespraeche.glob("web-*")) + list(runden_basis.glob("*")):  # Gespräche überleben keinen Neustart
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
                ruhend = []
                for g in list(gespraeche.values()):
                    if not g.laeuft and jetzt - g.zuletzt > e.session_absolut:
                        del gespraeche[g.kennung]
                        zu.append(g)
                    elif not g.laeuft and g.gespraech is not None and jetzt - g.zuletzt > e.leerlauf:
                        ruhend.append(loese_prozess(g))
            for g in zu:
                g.schliessen()
            for prozess in ruhend:
                beende_prozess(prozess)

    def loese_prozess(g):
        """Unter der Sperre: löst den Modellprozess eines ruhenden Gesprächs. Verlauf und Dateien bleiben, die nächste
        Frage startet einen neuen Prozess und bekommt den sichtbaren Verlauf mit (beantworte). Rückgabe: der Prozess,
        der außerhalb der Sperre zu beenden ist."""
        prozess, g.gespraech, g.korrektur = g.gespraech, None, None
        return prozess

    def beende_prozess(prozess):
        if prozess is not None:
            try:
                prozess.__exit__(None, None, None)
            except Exception:  # noqa: BLE001, auch ein halb gestarteter Prozess wird beendet
                pass

    def platz_schaffen():
        """Unter der Sperre: ist kein Modellprozess frei, ruht das am längsten unbenutzte Gespräch. Rückgabe: der zu
        beendende Prozess, None wenn ein Platz frei ist, False wenn alle Prozesse gerade arbeiten."""
        aktiv = [g for g in gespraeche.values() if not g.beendet and (g.laeuft or g.gespraech is not None)]
        if len(aktiv) < e.max_gespraeche:
            return None
        ruhig = sorted((g for g in aktiv if not g.laeuft), key=lambda g: g.zuletzt)
        return loese_prozess(ruhig[0]) if ruhig else False

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
                "pruefung": runde.get("pruefung"),
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

    def pruefe(eintrag, runde, text, beobachter):
        """Prüfrunde in einem eigenen Gespräch im Unterverzeichnis `pruefung`. Liefert (endgültige Antwort, Ergebnis
        für `pruefung`). Scheitert die Prüfung, bleibt die Antwort und die Seite zeigt einen Hinweis."""
        beobachter.pruefung_beginnt()
        start = time.monotonic()
        verlauf = [(r["frage"], r.get("antwort") or "") for r in eintrag.runden[:-1] if r.get("antwort")]
        cwd = eintrag.cwd / "pruefung"
        try:
            # Frisch anlegen: Das Modell hätte hier einen Symlink hinterlassen können
            if cwd.is_symlink() or cwd.is_file():
                cwd.unlink()
            elif cwd.exists():
                shutil.rmtree(cwd)
            cwd.mkdir()
            # Die Sandbox sperrt das Gesprächsverzeichnis für den Prüfer: genannte Dateien bekommt er als Kopie
            _, genannt = dateien.uebersetze(text, eintrag.cwd, eintrag.kennung)
            kopiert = sorted(dateien.sichere(eintrag.cwd, cwd, [d["name"] for d in genannt]))
            p = pruefer_fabrik(cwd)
            with sperre:
                eintrag.pruefer = p
            try:
                p.__enter__()
                if eintrag.abbruch or eintrag.beendet:  # beendet: inzwischen geschlossen, ohne diesen Prüfer zu sehen
                    raise Sitzungsfehler("Runde abgebrochen")
                r = p.frage(pruefung.pruefauftrag_text(verlauf, runde["frage"], text, kopiert),
                            beobachter=lambda n: beobachter.ereignis(n, p._turn_id))
            finally:
                with sperre:
                    eintrag.pruefer = None
                p.__exit__(None, None, None)
            urteil, neu, grund = pruefung.auswerten(r.text)
        except Exception as fehl:  # noqa: BLE001, eine gescheiterte Prüfung verschlechtert die Antwort nie
            urteil, neu, grund = "gescheitert", None, str(fehl)[:200]
        ms = int((time.monotonic() - start) * 1000)
        if urteil == "korrigiert" and neu:
            # Korrigierte Dateien des Prüfers übernehmen, damit seine Verweise auf seine Fassung zeigen
            _, korrigiert = dateien.uebersetze(neu, cwd, eintrag.kennung)
            dateien.sichere(cwd, eintrag.cwd, [d["name"] for d in korrigiert])
            return neu, {"status": "korrigiert", "hinweis": None, "ms": ms, "grund": grund}
        if urteil == "bestätigt":
            return text, {"status": "bestaetigt", "hinweis": None, "ms": ms, "grund": grund}
        return text, {"status": "gescheitert", "ms": ms, "grund": grund,
                      "hinweis": "The verification could not be completed, so this answer is unverified."}

    def an_das_modell(eintrag, runde):
        """Text der Runde für das Modell. Nach einer Pause (neuer Prozess) steht davor der Verlauf, wie der Nutzer ihn
        sieht, nach einer Korrektur der Prüfrunde deren Fassung: Nachfragen bauen auf dem auf, was der Nutzer las."""
        frage = runde["frage"]
        frueher = [(r["frage"], r["antwort"]) for r in eintrag.runden[:-1] if r.get("antwort")]
        if eintrag.gespraech is None and frueher:
            # Begrenzt: die jüngsten Runden, lange Antworten gekürzt, sonst wüchse die Eingabe mit jeder Runde
            neueste = frueher[-VERLAUF_RUNDEN:]
            verlauf = "\n\n".join(f"Nutzer: {f}\n\nAnalyst: {a if len(a) <= VERLAUF_ZEICHEN else a[:VERLAUF_ZEICHEN] + ' …'}"
                                  for f, a in neueste)
            ausgelassen = (f" (die {len(frueher) - len(neueste)} älteren Runden ausgelassen)"
                           if len(frueher) > len(neueste) else "")
            return ("Hinweis der Anwendung: Dieses Gespräch wurde nach einer Pause neu gestartet. Bisheriger Verlauf, "
                    f"wie der Nutzer ihn sieht{ausgelassen}:\n\n{verlauf}\n\n---\n\nNeue Frage des Nutzers:\n\n{frage}")
        if eintrag.korrektur:
            return pruefung.mit_korrektur(eintrag.korrektur, frage)
        return frage

    def beantworte(eintrag, runde):
        nummer = len(eintrag.runden)
        beobachter = fortschritt.Fortschritt(pruefen=bool(runde.get("verifizieren")))
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

        text_modell = an_das_modell(eintrag, runde)
        try:
            if eintrag.gespraech is None:
                g = gespraech_fabrik(eintrag.cwd)
                eintrag.gespraech = g
                g.__enter__()
            if eintrag.beendet:  # inzwischen geschlossen (Abmelden, Session-Ende), ohne diesen Prozess zu sehen
                raise Sitzungsfehler("Gespräch beendet")
            if eintrag.abbruch:
                raise Sitzungsfehler("Runde abgebrochen")
            g = eintrag.gespraech
            ergebnis = g.frage(text_modell, beobachter=lambda n: beobachte(n, g))
            eintrag.korrektur = None  # erst jetzt kennt das Modell die Korrektur, ein früherer Abbruch behält sie
        except Exception as fehl:  # noqa: BLE001, jede Ausnahme beendet die Runde
            if eintrag.abbruch and isinstance(fehl, Sitzungsfehler) and eintrag.gespraech is not None \
                    and eintrag.gespraech.thread_id:
                return abgebrochen()
            meldung = str(fehl) if isinstance(fehl, Sitzungsfehler) else "interner Fehler"
            protokolliere(eintrag, nummer, "fehler", fehler=meldung)
            # Der Zustand des Modellprozesses ist unklar: nur ihn beenden. Das Gespräch bleibt, die nächste Frage
            # startet einen neuen Prozess mit dem sichtbaren Verlauf (an_das_modell). Den Prozess unter derselben
            # Sperre lösen, die die Runde freigibt, sonst träfe das Beenden eine schon angenommene Folgefrage.
            with sperre:
                if eintrag.abbruch:
                    runde["abgebrochen"] = True
                else:
                    runde["fehler"] = meldung
                prozess = loese_prozess(eintrag)
                eintrag.laeuft, eintrag.fortschritt = False, None
            archiviere(eintrag, nummer, runde, "abgebrochen" if eintrag.abbruch else "fehler", items, vorher)
            beende_prozess(prozess)
            return
        if eintrag.abbruch:  # wer abbricht, will die Antwort nicht mehr, auch wenn sie schon stand
            return abgebrochen(ergebnis)
        text, ergebnis_pruefung = ergebnis.text, None
        if runde.get("verifizieren") and not text.lstrip().startswith("[Rückfrage]"):
            text, ergebnis_pruefung = pruefe(eintrag, runde, text, beobachter)
            if eintrag.abbruch:
                return abgebrochen(ergebnis)
            if ergebnis_pruefung["status"] == "korrigiert":
                eintrag.korrektur = text
        protokolliere(eintrag, nummer, "fertig", ergebnis)
        antwort, gemeldet = dateien.uebersetze(text, eintrag.cwd, eintrag.kennung, nummer)
        dateien.sichere(eintrag.cwd, eintrag.runden_ort / str(nummer), [d["name"] for d in gemeldet])
        with sperre:
            if ergebnis_pruefung:
                runde["pruefung"] = ergebnis_pruefung
            runde.update(antwort=antwort, dateien=gemeldet, ms=int(ergebnis.sekunden * 1000),
                         stufen=beobachter.stufen(fertig=True), schritte=beobachter.schritte)
            eintrag.laeuft, eintrag.fortschritt = False, None
            eintrag.zuletzt = time.monotonic()
        archiviere(eintrag, nummer, runde, "fertig", ergebnis.items, vorher, ergebnis)

    def runde_im_hintergrund(eintrag, runde):
        """Thread einer Runde. Scheitert `beantworte` unerwartet, etwa in der Nachverarbeitung, endet die Runde als
        Fehler, statt für immer als laufend zu gelten und einen Platz zu belegen. Wurde das Gespräch während der
        Runde geschlossen, bleibt nichts zurück, was die Runde danach noch gestartet oder angelegt hat."""
        try:
            beantworte(eintrag, runde)
        except Exception as fehl:  # noqa: BLE001, jede Ausnahme beendet die Runde
            print(f"runde: {type(fehl).__name__}: {str(fehl)[:300]}", file=sys.stderr, flush=True)
            with sperre:
                offen = eintrag.laeuft and eintrag.runden[-1] is runde  # sonst war die Runde schon freigegeben
                if offen:
                    runde["fehler"] = "interner Fehler"
                    prozess = loese_prozess(eintrag)
                    eintrag.laeuft, eintrag.fortschritt = False, None
                    eintrag.zuletzt = time.monotonic()
            if offen:
                beende_prozess(prozess)
        finally:
            if eintrag.beendet:
                with sperre:
                    prozess = loese_prozess(eintrag)
                beende_prozess(prozess)
                shutil.rmtree(eintrag.cwd, ignore_errors=True)
                if eintrag.runden_ort:
                    shutil.rmtree(eintrag.runden_ort, ignore_errors=True)

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
        drossel.zuruecksetzen(f"ip:{adresse}")  # Beta: mehrere Tester hinter einer Firmenadresse, nur Fehlversuche zählen
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
        # `verifizieren` schaltet die Prüfrunde ein (pruefe). `speichern` ist der Schalter der Seite für die Beta-Ablage.
        daten = json_body(await request.body(), [("text", str), ("verifizieren", bool), ("speichern", bool)])
        if daten is None:
            return fehler(422, "Ungültige Frage")
        text = (daten.get("text") or "").strip()
        kennung = daten.get("gespraech")
        if not text or len(text) > 4000 or not (kennung is None or isinstance(kennung, str)):
            return fehler(422, "Ungültige Frage")
        runde = {"frage": text, "verifizieren": bool(daten.get("verifizieren")), "zeit": jetzt_iso(),
                 "abfragen": [], "beleg": [], "dateien": []}
        zu_alt = []  # über `max_behalten` hinaus behaltene ruhende Gespräche, außerhalb der Sperre zu schließen
        with sperre:
            if kennung is None:
                for g in [g for g in gespraeche.values() if not g.laeuft and g.beendet]:
                    del gespraeche[g.kennung]
                frei = platz_schaffen()
                if frei is False:
                    return fehler(503, "Alle Plätze belegt, bitte später erneut versuchen")
                kennung = secrets.token_hex(16)
                cwd = e.gespraeche / f"web-{kennung}"
                cwd.mkdir(mode=0o750)
                eintrag = Eintrag(kennung, cwd, s.ref, s.email)
                eintrag.runden_ort = runden_basis / kennung
                gespraeche[kennung] = eintrag
                ruhig = sorted((g for g in gespraeche.values() if not g.laeuft and g is not eintrag),
                               key=lambda g: g.zuletzt)
                zu_alt = ruhig[:max(0, len(gespraeche) - e.max_behalten)]
                for g in zu_alt:
                    del gespraeche[g.kennung]
            else:
                eintrag = gespraeche.get(kennung)
                if eintrag is None or eintrag.besitzer != s.ref:
                    return fehler(404, "Gespräch unbekannt")
                if eintrag.beendet:
                    return fehler(410, "Gespräch beendet, bitte ein neues beginnen")
                if eintrag.laeuft:
                    return fehler(409, "Im Gespräch läuft noch eine Frage")
                frei = platz_schaffen() if eintrag.gespraech is None else None
                if frei is False:
                    return fehler(503, "Alle Plätze belegt, bitte später erneut versuchen")
            eintrag.runden.append(runde)
            eintrag.speichern = bool(daten.get("speichern")) and ablage is not None
            eintrag.laeuft = True
            eintrag.abbruch = None
            eintrag.zuletzt = time.monotonic()
        beende_prozess(frei or None)
        for g in zu_alt:
            g.schliessen()
        threading.Thread(target=runde_im_hintergrund, args=(eintrag, runde), daemon=True).start()
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

    def oeffne_gemeldet(eintrag, nummer, name):
        """Gemeldete Datei einer Runde: der gesicherte Stand der Runde, ohne Sicherung der aktuelle. Sonst None."""
        datei_ = dateien.oeffne(eintrag.runden_ort, f"{nummer}/{name}") if nummer and eintrag.runden_ort else None
        return datei_ or dateien.oeffne(eintrag.cwd, name)

    def datei(request):
        """Nur Dateien, die eine Antwort dieses Gesprächs gemeldet hat (web/dateien.py)."""
        s = hole_session(request)
        if s is None:
            return nicht_angemeldet()
        nummer, name = dateien.aufloesen(request.path_params["name"])
        with sperre:
            eintrag = eigenes(request, s)
            gemeldet = eintrag is not None and any(d["name"] == name for i, r in enumerate(eintrag.runden, 1)
                                                   if nummer in (None, i) for d in r.get("dateien") or [])
        datei_ = oeffne_gemeldet(eintrag, nummer, name) if gemeldet else None
        if datei_ is None:
            return fehler(404, "Datei unbekannt")
        with datei_:
            inhalt = datei_.read(50_000_000)
        inhalt, art, koepfe = dateien.auslieferung(name, inhalt, request.headers.get("sec-fetch-dest"))
        return Response(inhalt, media_type=art, headers=koepfe)

    def beantwortete(request, s):
        """Beantwortete Runden (Eintrag, Nummer, Runde) der genannten eigenen Gespräche in dieser Reihenfolge, ohne
        laufende, abgebrochene und gescheiterte. Die Seite nennt alle Gespräche ihres Verlaufs, nach einem Fehler sind
        es mehrere. Fremde und unbekannte Kennungen fallen still weg."""
        kennungen = list(dict.fromkeys(request.query_params.get("gespraeche", "").split(",")))[:50]
        with sperre:
            eintraege = [gespraeche.get(k) for k in kennungen if KENNUNG.fullmatch(k)]
            return [(e, nummer, dict(r)) for e in eintraege if e is not None and e.besitzer == s.ref
                    for nummer, r in enumerate(e.runden, 1) if r.get("antwort")]

    def herunterladen(inhalt, art, name, endung):
        heute = datetime.date.today().isoformat()
        return Response(inhalt, media_type=art, headers={
            "Content-Disposition": f'attachment; filename="SAE-Data-Desk-{name}-{heute}.{endung}"',
            "X-Content-Type-Options": "nosniff", "Cache-Control": "no-store"})

    def export_pdf(request):
        s = hole_session(request)
        if s is None:
            return nicht_angemeldet()
        runden = beantwortete(request, s)
        if not runden:
            return fehler(409, "Noch keine Antwort zum Exportieren")
        zuege = []
        for eintrag, nummer, runde in runden:
            namen = [d["name"] for d in runde.get("dateien") or []]

            def lese(name, eintrag=eintrag, nummer=nummer, namen=namen):
                datei_ = oeffne_gemeldet(eintrag, nummer, name) if name in namen else None
                if datei_ is None:
                    return None
                with datei_:
                    return datei_.read(dateien.GROESSE_MAX)

            zuege.append({"frage": runde["frage"], "zeit": (runde.get("zeit") or "")[11:16], "antwort": runde["antwort"],
                          "gespraech": eintrag.kennung, "dateien": namen, "pruefung": runde.get("pruefung"),
                          "lese": lese})
        stand, _ = datenstand()
        inhalt = bericht.pdf(zuege, stand, version(), datetime.date.today())
        return herunterladen(inhalt, "application/pdf", "Report", "pdf")

    def export_excel(request):
        s = hole_session(request)
        if s is None:
            return nicht_angemeldet()
        stand, _ = datenstand()
        blaetter = []
        for nummer, (eintrag, _, runde) in enumerate(beantwortete(request, s), start=1):
            zerlegt = antwort_modul.zerlege(runde["antwort"], eintrag.kennung)
            tabellen = antwort_modul.tabellen(zerlegt)
            if tabellen:
                kopf = [("Question", runde["frage"]), ("Answer", zerlegt.get("lead_text", ""))]
                if stand:
                    kopf.append(("Data as of", bericht.datum_kurz(stand)))
                blaetter.append({"name": f"Question {nummer:02d}", "kopf": kopf, "tabellen": tabellen,
                                 "sprache": antwort_modul.sprache(runde["antwort"])})
        if not blaetter:
            return fehler(409, "Keine Tabellen im Gespräch")
        return herunterladen(excel.mappe(blaetter), XLSX, "Tables", "xlsx")

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
        with sperre:
            ziel = eintrag.pruefer or eintrag.gespraech
        try:
            if ziel is not None and ziel.thread_id:
                ziel.unterbrechen()
        except Exception:  # noqa: BLE001, die Notbremse unten greift auch dann
            pass

        def notbremse():
            # Hängt die Runde nach dem Abbruch weiter: nur den Prozess beenden, das Gespräch ruht wie nach einem
            # Fehler und setzt mit dem sichtbaren Verlauf fort. Die hängende Runde endet dann mit einem Fehler.
            with sperre:
                haengt = eintrag.laeuft and eintrag.abbruch is marke
                if not haengt:
                    prozess = None
                elif eintrag.pruefer is not None:  # Prüfrunde hängt: der Hauptprozess bleibt
                    prozess = eintrag.pruefer
                else:
                    prozess = loese_prozess(eintrag)
            beende_prozess(prozess)

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
        Route("/api/export.pdf", export_pdf),
        Route("/api/export.xlsx", export_excel),
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
