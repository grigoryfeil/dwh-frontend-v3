# Changelog

## 0.4.1 (08.11.2026)

- Dashboards: eigenständige, schlanke HTML-Datei nach den Anleitungen des Plugins statt der Data App, deren ChatGPT-Bedienelemente (Veröffentlichen, Ask ChatGPT) hier ohne Funktion sind.

## 0.4.0 (08.11.2026)

- Dashboards als Ausgabeformat: abgeschottete Anzeige in der Oberfläche, Zeitlimit 25 Minuten, drei Dashboard-Prüffälle.
- Umgebung der Modell-Shell: Node-Unterprozesse ohne Eingabe-Pipe (behebt EPERM im Data-App-Build), Node und python im Pfad, Umgebungsangabe in der Anweisung (kein Netz, kein Browser, Offline-HTML).
- Läufe protokollieren den Zeitpunkt jedes Schritts.

## 0.3.5 (08.11.2026)

- Antwortform: Zu einem Diagramm gehört immer eine Tabelle mit den dargestellten Werten (lesbar und prüfbar).
- Referenzlauf 0.3.4: 21/24, kein zurückgehaltener Fall verfehlt; Konversionskurve in der Lesart des Vertriebsreports.

## 0.3.4 (08.11.2026)

- Katalog: SAE-Standardlesart je Kennzahlfamilie (Spalten standard, standard_quelle), 7 Familien belegt, 4 offen; Konversion: Bulletin-Lesart als Standard, Ersatzquelle vor 0326.
- Themenansichten und Themenindex zeigen den SAE-Standard.

## 0.3.3 (08.11.2026)

- Arbeitsweise: höchstens eine Rückfrage je Frage; nach Antwort oder Präzisierung mit der am besten passenden, durch die Daten gedeckten Lesart rechnen und sie benennen.
- Testtreiber beantwortet Rückfragen nur, wenn eine kam.

## 0.3.2 (08.11.2026)

- Abbruchquote und Studienerfolg am Dashboard „Student Outcomes – Cohort View“ (Eva Elliott) verankert: reife Kohorten ab 2018_H1, ohne Zertifikate; 5 neue Kennzahlen.
- Referenzsatz: Abbruch-Fälle auf das Dashboard umgestellt (auf Grundlage unabhängiger Quelle), zwei neue zurückgehaltene Fälle.

## 0.3.1 (08.11.2026)

- SAE-Wissen an die Kennzahlvarianten angeglichen, Katalog mit älterer KPI-Tabelle aus Drive abgeglichen (08b hat Vorrang).
- Wiederholungslauf 0.3.0: 9/11 Entwicklung, 10/11 zurückgehalten bestanden. Stabil verfehlt nur die Abbruchquote (Lesart).

## 0.3.0 (08.11.2026)

- Katalog mit Quellenordnung: Thema, Eignung, Abdeckung, Beziehungen; Konversionsvarianten mit eigenen IDs (nach Codex-Zweitmeinung).
- Kontext: Anweisung mit Themenindex (2.700 statt 4.700 Wörter), Themenansichten aus Katalog und SAE-Wissen erzeugt.
- Beta-Ablage der Gespräche (DWH_ABLAGE=1), Läufe sichern Werkzeugergebnisse vollständig.
- Referenzsatz mit 22 Fällen (11 zurückgehalten) und deterministischem Vergleich. Erster Lauf: 8/11 Entwicklung, 9/11 zurückgehalten bestanden.

## 0.2.0 (08.11.2026)

- Oberfläche von Claude Design unverändert übernommen und über ein schlankes Backend (`web/`) an den Harness angebunden: Gespräche mit Nachfragen, Fortschritt, Login, Diagramme aus dem Gesprächsverzeichnis.
- Betrieb unter dwhv3.152-53-125-222.sslip.io (systemd-Unit `dwh-frontend-v3-web`, nginx, Let's Encrypt).
- SAE-Wissen als gepflegte Einträge (399) mit Bezügen auf den Katalog.

## 0.1.0 (08.11.2026)

- Grundlage aus dem Grilling vom 08.11.2026 festgehalten (README.md).
- Katalog als gepflegte Tabellen (Objekte, Felder, Kennzahlen) mit Gültigkeit.
- Tracer Bullet: dünner Harness (Sol 6.1 mit Data-Plugin, Werkzeug sql, Anweisung aus Katalog erzeugt) beantwortet erste Fragen Ende-zu-Ende auf dem VPS. Läufe liegen lokal unter laeufe/ und nicht im Repo, weil sie DWH-Zahlen enthalten.
