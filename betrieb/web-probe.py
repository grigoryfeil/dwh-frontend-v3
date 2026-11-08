"""Rauchtest der Weboberfläche über die öffentliche Adresse, als root auf dem VPS.

Meldet sich mit dem Testkonto aus /etc/dwh-frontend-v3/zugang an (das Passwort wird nicht ausgegeben) und stellt die
übergebenen Fragen nacheinander im selben Gespräch, also ab der zweiten als Nachfrage.
Aufruf: python3 -I web-probe.py "Frage" ["Nachfrage" ...]
"""
import http.cookiejar, json, re, ssl, sys, time, urllib.request
B = "https://dwhv3.152-53-125-222.sslip.io"
z = dict(re.findall(r"^(\w+): (.*)$", open("/etc/dwh-frontend-v3/zugang").read(), re.M))
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
def req(pfad, daten=None, methode=None):
    r = urllib.request.Request(B + pfad, data=json.dumps(daten).encode() if daten is not None else None,
                               headers={"Content-Type": "application/json", "Origin": B}, method=methode)
    with op.open(r, timeout=30) as a:
        return a.status, json.loads(a.read() or b"null")
print(req("/api/stand"))
print(req("/api/anmelden", {"email": z["benutzer"], "passwort": z["passwort"]})[0])
k = None
for frage in sys.argv[1:]:
    s, d = req("/api/fragen", {"text": frage, "gespraech": k, "verifizieren": False, "speichern": False, "schnell": False})
    k = d["gespraech"]; t0 = time.time(); letzte = None
    while True:
        time.sleep(3)
        _, st = req(f"/api/gespraeche/{k}")
        r = st["runden"][-1]
        if st["status"] == "laeuft":
            sch = [x["text"] for x in r.get("schritte", [])]
            if sch and sch[-1] != letzte: letzte = sch[-1]; print(f"  {int(time.time()-t0)}s {[x["status"][0] for x in r.get("stufen",[])]} {letzte}", flush=True)
            continue
        print(st["status"], int(time.time()-t0), "s", r.get("fehler"))
        print((r.get("antwort") or "")[:800])
        for d in r.get("dateien") or []:
            with op.open(urllib.request.Request(B + d["url"]), timeout=30) as a:
                print("  Datei", d["name"], a.status, a.headers["Content-Type"], len(a.read()), "Bytes")
        print("----", flush=True); break
