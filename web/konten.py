"""Konten der Oberfläche: je E-Mail ein scrypt-Hash, gepflegt von root, gelesen vom Backend.

Kontendatei (JSON, root:dwhv3 0640): {"<email>": {"hash": "scrypt$n$r$p$salz$hash", "aktiv": true}}.
Pflege auf dem VPS als root: `python3 -I /opt/dwh-frontend-v3/app/web/konten.py setzen <name> < passwortdatei`, `sperren <name>`.
"""

import hashlib
import hmac
import json
import os
import secrets
import sys
import threading
from pathlib import Path

N, R, P = 2**15, 8, 1
SPEICHER = 64 * 1024 * 1024


def normalisiere(email):
    return (email or "").strip().lower()


def hash_von(passwort, salz=None, n=N, r=R, p=P):
    salz = salz or secrets.token_bytes(16)
    wert = hashlib.scrypt(passwort.encode(), salt=salz, n=n, r=r, p=p, maxmem=SPEICHER, dklen=32)
    return f"scrypt${n}${r}${p}${salz.hex()}${wert.hex()}"


def stimmt(passwort, gespeichert):
    try:
        _, n, r, p, salz, wert = gespeichert.split("$")
        neu = hash_von(passwort, bytes.fromhex(salz), int(n), int(r), int(p))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(neu.rsplit("$", 1)[1], wert)


class Konten:
    """Liest die Kontendatei bei jeder Änderung neu, so wirken Sperren ohne Neustart."""

    def __init__(self, pfad):
        self.pfad = Path(pfad)
        self._stand, self._konten = None, {}
        self._sperre = threading.Lock()
        self._attrappe = hash_von(secrets.token_urlsafe(16))

    def _lade(self):
        try:
            merkmal = self.pfad.stat().st_mtime_ns
        except OSError:
            return {}
        with self._sperre:
            if merkmal != self._stand:
                try:
                    daten = json.loads(self.pfad.read_text(encoding="utf-8") or "{}")
                except (OSError, ValueError):
                    daten = {}
                self._konten = daten if isinstance(daten, dict) else {}
                self._stand = merkmal
            return self._konten

    def aktiv(self, email):
        konto = self._lade().get(normalisiere(email))
        return isinstance(konto, dict) and konto.get("aktiv", True) and isinstance(konto.get("hash"), str)

    def pruefe(self, email, passwort):
        konto = self._lade().get(normalisiere(email))
        ok = stimmt(passwort, konto["hash"] if self.aktiv(email) else self._attrappe)
        return ok and self.aktiv(email)


def _schreibe(pfad, konten):
    neu = Path(f"{pfad}.neu")
    neu.write_text(json.dumps(konten, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    try:
        st = os.stat(pfad)
        os.chown(neu, st.st_uid, st.st_gid)
        os.chmod(neu, st.st_mode & 0o777)
    except FileNotFoundError:
        os.chmod(neu, 0o640)
    os.replace(neu, pfad)


def main(argv):
    pfad = os.environ.get("DWH_V3_KONTEN", "/etc/dwh-frontend-v3/konten.json")
    if len(argv) != 2 or argv[0] not in ("setzen", "sperren"):
        sys.exit("Aufruf: python3 -I konten.py setzen|sperren <name>  (Passwort für setzen auf stdin)")
    befehl, email = argv[0], normalisiere(argv[1])
    try:
        konten = json.loads(Path(pfad).read_text(encoding="utf-8") or "{}")
    except FileNotFoundError:
        konten = {}
    if befehl == "setzen":
        passwort = sys.stdin.readline().rstrip("\n")
        if len(passwort) < 12:
            sys.exit("Passwort zu kurz (mindestens 12 Zeichen)")
        konten[email] = {"hash": hash_von(passwort), "aktiv": True}
    else:
        if email not in konten:
            sys.exit("Konto unbekannt")
        konten[email]["aktiv"] = False
    _schreibe(pfad, konten)
    print(f"{befehl}: {email}")


if __name__ == "__main__":
    main(sys.argv[1:])
