"""Betriebstest der Weboberfläche über die öffentliche Adresse, als root auf dem VPS.

Prüft, was ein einzelner Rauchtest (web-probe.py) nicht sieht:
- Gleichzeitigkeit: so viele Gespräche wie Plätze, ein weiteres wird abgewiesen (503).
- Trennung: eine zweite Anmeldung sieht die Gespräche der ersten nicht (404).
- Abbruch: eine laufende Runde endet nach dem Abbruch zügig, das Gespräch bleibt für eine Nachfrage nutzbar.
Speichert nichts in der Beta-Ablage. Gibt nur Status, Zeiten und Antwortanfänge aus, keine Zugangsdaten.
Aufruf: python3 -I web-last.py [plaetze]
"""
import http.cookiejar, json, re, sys, threading, time, urllib.error, urllib.request

B = "https://dwhv3.152-53-125-222.sslip.io"
Z = dict(re.findall(r"^(\w+): (.*)$", open("/etc/dwh-frontend-v3/zugang").read(), re.M))
PLAETZE = int(sys.argv[1]) if len(sys.argv) > 1 else 4


class Nutzer:
    def __init__(self):
        self.op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        assert self.req("/api/anmelden", {"email": Z["benutzer"], "passwort": Z["passwort"]})[0] == 200

    def req(self, pfad, daten=None, methode=None):
        r = urllib.request.Request(B + pfad, data=json.dumps(daten).encode() if daten is not None else None,
                                   headers={"Content-Type": "application/json", "Origin": B}, method=methode)
        try:
            with self.op.open(r, timeout=30) as a:
                return a.status, json.loads(a.read() or b"null")
        except urllib.error.HTTPError as f:
            return f.code, None

    def frage(self, text, kennung=None):
        return self.req("/api/fragen", {"text": text, "gespraech": kennung, "verifizieren": False,
                                        "speichern": False})

    def warte(self, kennung, grenze=1800):
        t0 = time.time()
        while time.time() - t0 < grenze:
            time.sleep(3)
            s, st = self.req(f"/api/gespraeche/{kennung}")
            if s != 200:
                return f"HTTP {s}", None, time.time() - t0
            if st["status"] != "laeuft":
                r = st["runden"][-1]
                return st["status"], r, time.time() - t0
        return "zeitgrenze", None, time.time() - t0


def zeile(name, ok, text):
    print(f"[{'ok' if ok else 'FEHLER'}] {name}: {text}", flush=True)


a, b = Nutzer(), Nutzer()

# 1. Gleichzeitigkeit
FRAGEN = ["Wie viele Studierende haben wir aktuell insgesamt?",
          "Wie viele Leads kamen im Oktober 2026 herein?",
          "Wie viele Neueinschreibungen hatte der Intake September 2026?",
          "Wie hoch war die Weiterempfehlung in der letzten Semesterumfrage?",
          "Welcher Campus hat die meisten Studierenden?", "Wie viele Opportunities gab es 2026?"]
kennungen = []
for f in FRAGEN[:PLAETZE]:
    s, d = a.frage(f)
    kennungen.append(d["gespraech"] if s == 202 else None)
zeile("Plätze belegen", all(kennungen), f"{sum(map(bool, kennungen))}/{PLAETZE} angenommen")
s, _ = a.frage(FRAGEN[PLAETZE % len(FRAGEN)])
zeile("Überlauf abweisen", s == 503, f"HTTP {s}")

# 2. Trennung zwischen Anmeldungen
s, _ = b.req(f"/api/gespraeche/{kennungen[0]}")
zeile("Fremdes Gespräch lesen", s == 404, f"HTTP {s}")
s, _ = b.req(f"/api/gespraeche/{kennungen[0]}/abbrechen", {})
zeile("Fremdes Gespräch abbrechen", s == 404, f"HTTP {s}")

ergebnisse = {}
def sammle(k):
    ergebnisse[k] = a.warte(k)
threads = [threading.Thread(target=sammle, args=(k,)) for k in kennungen if k]
[t.start() for t in threads]
[t.join() for t in threads]
for k in kennungen:
    status, r, sek = ergebnisse.get(k, ("fehlt", None, 0))
    antwort = ((r or {}).get("antwort") or (r or {}).get("fehler") or "").replace("\n", " ")[:140]
    zeile("Gleichzeitige Runde", status == "fertig", f"{status} nach {sek:.0f} s: {antwort}")
for k in kennungen:
    a.req(f"/api/gespraeche/{k}", methode="DELETE")

# 3. Abbruch und Weiterarbeit im selben Gespräch
s, d = a.frage("Bau mir ein Dashboard zur Lead-Entwicklung der letzten drei Jahre nach Quelle und Campus.")
k = d["gespraech"]
time.sleep(40)
t0 = time.time()
s, _ = a.req(f"/api/gespraeche/{k}/abbrechen", {})
status, r, _ = a.warte(k, 120)
zeile("Abbruch", s == 202 and status != "laeuft", f"HTTP {s}, danach {status} nach {time.time() - t0:.0f} s, "
      f"abgebrochen={(r or {}).get('abgebrochen')}, Fehler: {((r or {}).get('fehler') or '')[:80]}")
s, _ = a.frage("Dann nur kurz: Wie viele Leads hatten wir im Oktober 2026?", k)
status2, r2, sek = a.warte(k) if s == 202 else (f"HTTP {s}", None, 0)
zeile("Nachfrage nach Abbruch", status2 == "fertig",
      f"{status2} nach {sek:.0f} s: {((r2 or {}).get('antwort') or '').replace(chr(10), ' ')[:140]}")
a.req(f"/api/gespraeche/{k}", methode="DELETE")
