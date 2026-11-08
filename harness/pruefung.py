"""Prüfrunde: ein unabhängiger zweiter Analyst prüft eine Antwort, bevor sie an den Nutzer geht.

Der Prüfer ist ein eigenes Gespräch mit derselben Anweisung (Katalog, SAE-Wissen, Datenzugang) und dem Prüfauftrag
unten. Er sieht Frage, bisherigen Verlauf und Antwort, nicht den Rechenweg, und rechnet die Kernzahlen selbst nach.
Ergebnis: bestätigt (Antwort bleibt) oder korrigiert (seine Fassung ersetzt die Antwort).
Nutzenprobe mit `pruef_test.py` am 08.11.2026 (11/11 falsche korrigiert, 12/12 richtige bestätigt), seither in der
Oberfläche hinter dem Schalter Verify (web/app.py, pruefe). Die Oberfläche nutzt `PRUEFAUFTRAG`, `pruefauftrag_text`
und `auswerten`, der Testtreiber `pruefen`.
"""

import re

from sitzung import Gespraech

PRUEFAUFTRAG = """

# Prüfrunde

In diesem Gespräch beantwortest du keine Frage selbst. Du prüfst die Antwort eines anderen Analysten, bevor sie an
den Nutzer geht.

- Prüfe, ob die Antwort die Frage in der Lesart beantwortet, die zur Frage, zum Gesprächsverlauf und zum SAE-Standard
  passt. Lies dazu die Themenansicht und den Katalog.
- Rechne die Kernzahlen mit eigenen Abfragen nach. Leite die Abgrenzung selbst aus Katalog und SAE-Wissen ab, statt
  den Angaben im Nachweis zu folgen.
- Korrigiere nur, wenn der Nutzer mit der Antwort eine falsche Zahl erhielte oder einen falschen Schluss zöge. Ist die
  Antwort richtig, aber knapper oder weniger genau, als du sie formuliert hättest, bestätige sie und nenne die
  Ergänzung im Satz nach der Kopfzeile. Andere, gleichwertige Darstellungen, Rundungen und Formulierungen sind kein
  Fehler. Eine Korrektur sieht der Nutzer als Fehlerhinweis.

Deine Antwort beginnt mit genau einer dieser Zeilen:
- `[Prüfung: bestätigt]`, danach ein Satz, was du nachgerechnet hast.
- `[Prüfung: korrigiert]`, danach die vollständige korrigierte Antwort an den Nutzer im üblichen Format, ohne Hinweis
  auf die Prüfung. Nach einer Zeile `---` folgt ein Satz, was falsch war.
"""

KOPF = re.compile(r"^\s*\[Prüfung:\s*(bestätigt|korrigiert)\]\s*", re.I)


def pruefauftrag_text(verlauf, frage, antwort, kopiert=()):
    """Eingabe der Prüfrunde. `kopiert`: in der Antwort genannte Dateien, die als Kopie im Arbeitsverzeichnis des
    Prüfers liegen (die Sandbox sperrt ihm das Gesprächsverzeichnis)."""
    teile = []
    if verlauf:
        teile.append("Bisheriger Gesprächsverlauf:\n\n" + "\n\n".join(
            f"Nutzer: {f}\n\nAnalyst: {a}" for f, a in verlauf))
    teile.append(f"Aktuelle Frage des Nutzers:\n\n{frage}")
    teile.append(f"Antwort des Analysten, zu prüfen:\n\n{antwort}")
    if kopiert:
        teile.append(f"Die in der Antwort genannten Dateien liegen als Kopie in deinem Arbeitsverzeichnis: "
                     f"{', '.join(kopiert)}.")
    return "\n\n---\n\n".join(teile)


def mit_korrektur(korrektur, frage):
    """Text der nächsten Frage an den Analysten, nachdem eine Prüfrunde seine vorige Antwort korrigiert hat. Der
    Nutzer sah die korrigierte Fassung, die Nachfrage soll darauf aufbauen (Oberfläche und Testtreiber)."""
    return ("Hinweis der Anwendung: Eine Prüfrunde hat deine vorige Antwort korrigiert. Der Nutzer hat diese "
            f"Fassung gesehen, beziehe dich auf sie:\n\n{korrektur}\n\n---\n\nNeue Frage des Nutzers:\n\n{frage}")


def auswerten(text):
    """(urteil, endgültige Antwort oder None, Begründung). Unlesbares Ergebnis gilt als bestätigt: die Prüfung
    darf eine Antwort nie verschlechtern, nur weil sie selbst scheitert."""
    m = KOPF.match(text or "")
    if not m:
        return "unlesbar", None, (text or "")[:300]
    rest = text[m.end():]
    if m.group(1).lower() == "bestätigt":
        return "bestätigt", None, rest.strip()[:300]
    antwort, _, grund = rest.rpartition("\n---")
    if not antwort.strip():
        antwort, grund = rest, ""
    return "korrigiert", antwort.strip(), grund.strip()[:300]


def pruefen(arbeitsverzeichnis, anweisung, verlauf, frage, antwort, kopiert=(), **optionen):
    """Führt die Prüfrunde in einem eigenen Gespräch. Liefert dict mit urteil, antwort, grund, runde."""
    with Gespraech(arbeitsverzeichnis, anweisung + PRUEFAUFTRAG, **optionen) as g:
        runde = g.frage(pruefauftrag_text(verlauf, frage, antwort, kopiert))
    urteil, neu, grund = auswerten(runde.text)
    return {"urteil": urteil, "antwort": neu, "grund": grund, "runde": runde}
