# Zweitmeinung: Code- und Betriebs-Review DWH Frontend V3 vor der Beta

**Von:** Claude für Grigory, 08.11.2026 · **An:** Codex (Astra)

## Auftrag
Prüfe den Code und die Betriebsdateien von DWH Frontend V3 auf Fehler, die in der Beta in den nächsten Tagen echte Nutzer treffen würden: falsche oder fremde Daten sichtbar, Sicherheitslücken, Abstürze, hängende Gespräche, stille Fehler. Prüfe unabhängig, widersprich mit Begründung, wo du anderer Meinung bist, und nenne, was für das Ziel entbehrlich ist.

## Kontext
V3 ist eine dünne Harness: GPT-6.1 Sol über `codex app-server` beantwortet Freitextfragen von SAE-Entscheidern zu einer Kopie des Data Warehouse (MariaDB, nur lesend über das MCP-Werkzeug `sql`). Weboberfläche (Starlette hinter nginx, React-Oberfläche) mit Login, Gesprächen im Arbeitsspeicher, Dashboards als vom Modell erzeugtes HTML in einem abgeschotteten iframe, optionaler Prüfrunde (zweites Gespräch prüft die Antwort), Beta-Ablage der Gespräche. Die Modell-Shell läuft in der Codex-Sandbox ohne Netz. Beta: ein einziges geteiltes Konto `tester` für zwei bis drei Personen gleichzeitig, dazu ein internes Testkonto. Alles läuft auf einem VPS, auf dem auch V1 und V2 liegen.

## Material
Repository `/Users/grigoryfeil/Desktop/DWH Frontend V3`, darin:
- `README.md` (Grundlage, Annahmen, Bauweise)
- `web/` (Backend: `app.py`, `konten.py`, `dateien.py`, `ablage.py`, `fortschritt.py`)
- `harness/` (`sitzung.py` app-server-Anbindung, `sql_werkzeug.py`, `kontext.py`, `pruefung.py`, `lauf.py`, `anweisung.md`)
- `betrieb/` (`codex-config.toml` mit Sandbox und Berechtigungen, `einrichtung.sh`, `web-einrichtung.sh`, `dwh-frontend-v3-web.service`, `nginx-dwhv3`, `umgebung/`, `selbsttest.py`)
- `oberflaeche/src/` (React, nur soweit für Anzeige von Antworten, Dateien und iframe relevant)

## Kriterien
- Jeder Befund hat ein konkretes Fehlerszenario: welche Eingabe oder welcher Zustand, was dann passiert, wen es trifft. Ohne Szenario kein Befund.
- Nach Schwere sortiert: kritisch (Daten- oder Zugangsleck, falsche Zahl ohne Hinweis), hoch (Ausfall oder hängendes Gespräch in normaler Nutzung), mittel (seltener Fehler mit Umgehung).
- Je Befund Datei und Zeile, kurze Begründung, kleinster sinnvoller Fix.
- Besonders ansehen: Sitzungen und Gespräche bei einem geteilten Konto mit mehreren gleichzeitigen Nutzern, Dateiauslieferung und Pfadprüfung, iframe und CSP für Modell-HTML, Sandbox-Regeln und was das Modell lesen oder auslösen kann, Prompt-Injektion über Daten im DWH, Fehlerpfade (abgelaufener Codex-Login, Datenbank weg, Platte voll, Neustart der Unit mitten im Gespräch, Zeitlimit), Nebenläufigkeit und Sperren in `web/app.py`, Einspielen während laufender Gespräche.

## Grenzen
- Das Material ist der Ausgangspunkt. Recherchiere und nutze deine Werkzeuge, wo du es für nötig hältst. Keine Nachrichten an Dritte.
- Nur lesen, nichts ändern. Kein Zugriff auf den VPS oder andere Server.
- Nicht lesen: `referenz/` (enthält einen zurückgehaltenen Testsatz), `handover/material-plugin/`, `laeufe/`.
- Keine Stil-, Benennungs- oder Umbauvorschläge, keine Architekturdebatte (die Architektur wurde heute bereits geprüft, siehe `handover/2026-11-08-zweitmeinung-architektur-v3-ergebnis.md`). Keine Testabdeckung als Selbstzweck.
- Sprache Deutsch, generisches Maskulinum, Kommas oder Punkte statt Gedankenstrichen und Semikolons

## Rückgabe
In deiner Schlussantwort: Urteil in einem Satz, Befunde nach Schwere (Datei:Zeile, Szenario, Fix), begründete Widersprüche, offene Unsicherheiten.
