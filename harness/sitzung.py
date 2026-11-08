"""Gespräch mit dem Modell über `codex app-server` (JSON-RPC, eine Nachricht je Zeile).

Ein Gespräch ist ein app-server-Prozess mit einem Thread, jede Frage eine Runde. Der Prozess läuft als Nutzer
`dwhv3` in einer transienten systemd-Unit (`systemd-run --pipe`). Shell-Sandbox, Datenwerkzeug und Plugin legt
`codex-home/config.toml` fest.
"""

import json
import queue
import subprocess
import threading
import time
from dataclasses import dataclass, field

CODEX = "/opt/dwh-frontend-v3/codex/aktuell/bin/codex"
CODEX_HOME = "/var/lib/dwh-frontend-v3/codex-home"
NODE = "/opt/dwh-frontend-v3/node/bin"

SYSTEMD_RUN = [
    "systemd-run", "--pipe", "--wait", "--quiet", "--collect",
    "-p", "User=dwhv3", "-p", "Group=dwhv3",
    "-p", "TemporaryFileSystem=/run",
    "-p", "BindPaths=/run/dwh-frontend-db/mysqld.sock",
    "-p", "PrivateTmp=yes", "-p", "NoNewPrivileges=yes", "-p", "MemoryMax=2G",
    "-p", "RuntimeMaxSec=3600",
    "-E", f"CODEX_HOME={CODEX_HOME}", "-E", "HOME=/var/lib/dwh-frontend-v3",
    "-E", f"PATH={NODE}:/usr/bin:/bin", "-E", f"CODEX_MCP_NODE_PATH={NODE}/node",
    "-E", "LANG=C.UTF-8", "-E", "SHELL=/bin/bash", "-E", "RUST_LOG=off",
]


class Sitzungsfehler(Exception):
    pass


@dataclass
class Runde:
    text: str
    items: list = field(default_factory=list)
    token: dict = field(default_factory=dict)
    sekunden: float = 0.0
    modellanfragen: int = 0


class Gespraech:
    def __init__(self, arbeitsverzeichnis, anweisung, modell="gpt-6.1-sol", aufwand="high", zeitlimit=900):
        self.cwd = str(arbeitsverzeichnis)
        self.anweisung = anweisung
        self.modell = modell
        self.aufwand = aufwand
        self.zeitlimit = zeitlimit
        self._id = 0
        self._zeilen = queue.Queue()
        self.thread_id = None
        self.codex_version = None

    def __enter__(self):
        befehl = SYSTEMD_RUN + ["-p", f"WorkingDirectory={self.cwd}", CODEX, "app-server", "--strict-config",
                                "--stdio"]
        self._prozess = subprocess.Popen(befehl, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                         stderr=subprocess.DEVNULL, text=True, bufsize=1)
        threading.Thread(target=self._lies, daemon=True).start()
        frist = time.monotonic() + 90
        start = self._anfrage("initialize", {"clientInfo": {"name": "dwh-frontend-v3", "title": "DWH Frontend V3",
                                                            "version": "0"}}, frist)
        self.codex_version = start.get("userAgent")
        self._senden({"method": "initialized", "params": {}})
        thread = self._anfrage("thread/start", {
            "model": self.modell, "cwd": self.cwd, "approvalPolicy": "never", "ephemeral": True,
            "serviceName": "dwh-frontend-v3", "developerInstructions": self.anweisung,
        }, frist)
        self.thread_id = (thread.get("thread") or {}).get("id")
        if not self.thread_id:
            raise Sitzungsfehler("kein Thread angelegt")
        return self

    def __exit__(self, *_):
        if self._prozess.poll() is None:
            self._prozess.stdin.close()
            try:
                self._prozess.wait(10)
            except subprocess.TimeoutExpired:
                self._prozess.kill()

    def frage(self, text, beobachter=None):
        start = time.monotonic()
        frist = start + self.zeitlimit
        antwort = self._anfrage("turn/start", {"threadId": self.thread_id, "model": self.modell,
                                               "effort": self.aufwand,
                                               "input": [{"type": "text", "text": text}]}, frist)
        turn_id = (antwort.get("turn") or {}).get("id")
        items, token, schluss, letzte, fehler, anfragen = [], {}, None, None, "", 0
        while True:
            n = self._lesen(frist)
            m, p = n.get("method"), n.get("params") or {}
            if beobachter and m:
                beobachter(n)
            if m == "item/completed" and p.get("turnId") == turn_id:
                item = p.get("item") or {}
                items.append(item)
                if item.get("type") == "agentMessage":
                    letzte = item.get("text")
                    if item.get("phase") == "final_answer":
                        schluss = item.get("text")
            elif m == "thread/tokenUsage/updated" and p.get("turnId") == turn_id:
                anfragen += 1
                for k, w in ((p.get("tokenUsage") or {}).get("last") or {}).items():
                    if isinstance(w, int):
                        token[k] = token.get(k, 0) + w
            elif m == "error":
                fehler = str((p.get("error") or {}).get("message", ""))[:300]
            elif m == "turn/completed" and (p.get("turn") or {}).get("id") == turn_id:
                status = p["turn"].get("status", "")
                if status != "completed":
                    meldung = (p["turn"].get("error") or {}).get("message") or fehler
                    raise Sitzungsfehler(f"Runde {status}: {str(meldung)[:300]}")
                return Runde(text=schluss or letzte or "", items=items, token=token,
                             sekunden=round(time.monotonic() - start, 1), modellanfragen=anfragen)

    # JSON-RPC

    def _anfrage(self, methode, params, frist):
        kennung = self._senden({"method": methode, "params": params}, mit_kennung=True)
        while True:
            n = self._lesen(frist)
            if n.get("id") == kennung and "method" not in n:
                if "error" in n:
                    raise Sitzungsfehler(f"{methode}: {n['error'].get('message', n['error'])}")
                return n.get("result") or {}

    def _senden(self, nachricht, mit_kennung=False):
        if mit_kennung:
            self._id += 1
            nachricht = {"id": self._id, **nachricht}
        self._prozess.stdin.write(json.dumps(nachricht) + "\n")
        self._prozess.stdin.flush()
        return self._id

    def _lies(self):
        for zeile in self._prozess.stdout:
            self._zeilen.put(zeile)
        self._zeilen.put("")

    def _lesen(self, frist):
        while True:
            try:
                zeile = self._zeilen.get(timeout=max(frist - time.monotonic(), 0))
            except queue.Empty:
                raise Sitzungsfehler("Zeitlimit") from None
            if not zeile:
                raise Sitzungsfehler("app-server beendet")
            n = json.loads(zeile)
            if "method" in n and "id" in n:  # Anfrage des Servers: Formulare ablehnen, sonst zurückweisen
                if n["method"] == "mcpServer/elicitation/request":
                    self._senden({"id": n["id"], "result": {"action": "decline"}})
                else:
                    self._senden({"id": n["id"], "error": {"code": -32601, "message": "nicht unterstützt"}})
                continue
            return n
