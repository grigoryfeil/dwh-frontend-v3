# Changelog

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
