# Changelog

## 0.2.0 (08.11.2026)

- Oberfläche von Claude Design unverändert übernommen und über ein schlankes Backend (`web/`) an den Harness angebunden: Gespräche mit Nachfragen, Fortschritt, Login, Diagramme aus dem Gesprächsverzeichnis.
- Betrieb unter dwhv3.152-53-125-222.sslip.io (systemd-Unit `dwh-frontend-v3-web`, nginx, Let's Encrypt).
- SAE-Wissen als gepflegte Einträge (399) mit Bezügen auf den Katalog.

## 0.1.0 (08.11.2026)

- Grundlage aus dem Grilling vom 08.11.2026 festgehalten (README.md).
- Katalog als gepflegte Tabellen (Objekte, Felder, Kennzahlen) mit Gültigkeit.
- Tracer Bullet: dünner Harness (Sol 6.1 mit Data-Plugin, Werkzeug sql, Anweisung aus Katalog erzeugt) beantwortet erste Fragen Ende-zu-Ende auf dem VPS. Läufe liegen lokal unter laeufe/ und nicht im Repo, weil sie DWH-Zahlen enthalten.
