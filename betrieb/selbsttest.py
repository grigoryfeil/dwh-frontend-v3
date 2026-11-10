"""Täglicher Selbsttest von DWH Frontend V3 über die öffentliche Adresse, als root (Timer dwh-frontend-v3-selbsttest).

Prüft die ganze Kette, an der ein Beta-Nutzer scheitern würde: nginx und Zertifikat, Anmeldung, Codex-Login beim
Modellanbieter, Datenbank und Antwort. Meldet sich mit dem internen Testkonto aus /etc/dwh-frontend-v3/zugang an
(nicht dem Beta-Konto), stellt eine kurze Frage ohne Ablage und meldet sich wieder ab, das beendet das Gespräch.
Ergebnis: eine Zeile in /var/lib/dwh-frontend-v3/selbsttest.jsonl, Exitcode 1 bei Fehler (systemctl --failed).
"""
import http.cookiejar, json, re, sys, time, urllib.error, urllib.request

B = "https://dwhv3.152-53-125-222.sslip.io"
PROTOKOLL = "/var/lib/dwh-frontend-v3/selbsttest.jsonl"
FRAGE = "Wie viele Studierende haben wir aktuell insgesamt? Bitte nur die Zahl mit Stichtag."
GRENZE_S = 300


def main():
    t0, eintrag = time.time(), {"zeit": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def req(pfad, daten=None, methode=None):
        r = urllib.request.Request(B + pfad, data=json.dumps(daten).encode() if daten is not None else None,
                                   headers={"Content-Type": "application/json", "Origin": B}, method=methode)
        try:
            with op.open(r, timeout=30) as a:
                return a.status, json.loads(a.read() or b"null")
        except urllib.error.HTTPError as f:
            return f.code, None

    try:
        z = dict(re.findall(r"^(\w+): (.*)$", open("/etc/dwh-frontend-v3/zugang").read(), re.M))
        s, stand = req("/api/stand")
        eintrag["stand"] = stand
        if s != 200:
            raise RuntimeError(f"Seite nicht erreichbar (HTTP {s})")
        if req("/api/anmelden", {"email": z["benutzer"], "passwort": z["passwort"]})[0] != 200:
            raise RuntimeError("Anmeldung gescheitert")
        s, d = req("/api/fragen", {"text": FRAGE, "gespraech": None, "verifizieren": False, "speichern": False})
        if s != 202:
            raise RuntimeError(f"Frage nicht angenommen (HTTP {s})")
        kennung = d["gespraech"]
        try:
            while True:
                time.sleep(5)
                s, st = req(f"/api/gespraeche/{kennung}")
                if s != 200:
                    raise RuntimeError(f"Gespräch nicht lesbar (HTTP {s})")
                if st["status"] != "laeuft":
                    break
                if time.time() - t0 > GRENZE_S:
                    req(f"/api/gespraeche/{kennung}/abbrechen", {})
                    raise RuntimeError(f"keine Antwort nach {GRENZE_S} s")
            r = st["runden"][-1]
            if st["status"] != "fertig" or r.get("fehler"):
                raise RuntimeError(f"Runde {st['status']}: {(r.get('fehler') or '')[:200]}")
            if not re.search(r"\d", r.get("antwort") or ""):
                raise RuntimeError("Antwort ohne Zahl: " + (r.get("antwort") or "")[:200])
        finally:
            # Abmelden beendet die Session samt Gespräch, auch wenn die Runde noch läuft (Löschen gäbe dann 409 und
            # das Gespräch bliebe bis zum Session-Ende offen, so lange verweigert betrieb/wartung.sh das Einspielen)
            req("/api/abmelden", {})
        eintrag.update(ok=True)
    except Exception as fehler:  # noqa: BLE001, jeder Fehler ist ein Befund
        eintrag.update(ok=False, fehler=str(fehler)[:300])
    eintrag["sekunden"] = round(time.time() - t0)
    with open(PROTOKOLL, "a", encoding="utf-8") as f:
        f.write(json.dumps(eintrag, ensure_ascii=False) + "\n")
    print(json.dumps(eintrag, ensure_ascii=False))
    sys.exit(0 if eintrag["ok"] else 1)


if __name__ == "__main__":
    main()
