"""Prüfrunde: ein unabhängiger zweiter Analyst prüft eine Antwort, bevor sie an den Nutzer geht.

Der Prüfer ist ein eigenes Gespräch mit derselben Anweisung (Katalog, SAE-Wissen, Datenzugang) und dem Prüfauftrag
unten. Er sieht Frage, bisherigen Verlauf und Antwort, nicht den Rechenweg, und rechnet die Kernzahlen selbst nach.
Ergebnis: bestätigt (Antwort bleibt) oder korrigiert (seine Fassung ersetzt die Antwort).
Stand 08.11.2026: nur im Testtreiber (`pruef_test.py`), in der Oberfläche erst, wenn der Nutzen belegt ist.
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
- Korrigiere nur, was nachweislich falsch oder irreführend ist. Andere, gleichwertige Darstellungen, Rundungen und
  Formulierungen sind kein Fehler.

Deine Antwort beginnt mit genau einer dieser Zeilen:
- `[Prüfung: bestätigt]`, danach ein Satz, was du nachgerechnet hast.
- `[Prüfung: korrigiert]`, danach die vollständige korrigierte Antwort an den Nutzer im üblichen Format, ohne Hinweis
  auf die Prüfung. Nach einer Zeile `---` folgt ein Satz, was falsch war.
"""

KOPF = re.compile(r"^\s*\[Prüfung:\s*(bestätigt|korrigiert)\]\s*", re.I)


def pruefauftrag_text(verlauf, frage, antwort):
    teile = []
    if verlauf:
        teile.append("Bisheriger Gesprächsverlauf:\n\n" + "\n\n".join(
            f"Nutzer: {f}\n\nAnalyst: {a}" for f, a in verlauf))
    teile.append(f"Aktuelle Frage des Nutzers:\n\n{frage}")
    teile.append(f"Antwort des Analysten, zu prüfen:\n\n{antwort}")
    return "\n\n---\n\n".join(teile)


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


def pruefen(arbeitsverzeichnis, anweisung, verlauf, frage, antwort, **optionen):
    """Führt die Prüfrunde in einem eigenen Gespräch. Liefert dict mit urteil, antwort, grund, runde."""
    with Gespraech(arbeitsverzeichnis, anweisung + PRUEFAUFTRAG, **optionen) as g:
        runde = g.frage(pruefauftrag_text(verlauf, frage, antwort))
    urteil, neu, grund = auswerten(runde.text)
    return {"urteil": urteil, "antwort": neu, "grund": grund, "runde": runde}
