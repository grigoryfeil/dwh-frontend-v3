# Changelog

## 0.6.1 (08.11.2026)

- Schalter „Fast“ vollständig entfernt (Oberfläche, Typen, Backend, Betriebsskripte, Tests). Er war aus V2 übernommen und ohne Wirkung. Einziger Schalter ist „Verify“.

## 0.6.0 (08.11.2026)

Härtung vor der Beta nach drei Reviews (Codex Astra, Code-Review Standards und Spezifikation), siehe `handover/2026-11-08-zweitmeinung-code-beta-ergebnis.md`.

- Gesprächslebenszyklus: Nach Leerlauf, bei Platzmangel oder nach einem Fehler ruht ein Gespräch (Modellprozess frei, Verlauf und Dateien bleiben). Die nächste Frage setzt mit dem sichtbaren Verlauf fort. Plätze zählen nur laufende Prozesse, bei Bedarf ruht das am längsten unbenutzte Gespräch. Session-Leerlauf 4 Stunden.
- Prüfrunde: Korrekturen erreichen das Hauptgespräch vor der nächsten Frage. Keine Prüfrunde auf Rückfragen. Abbruch ohne Wettlauf.
- Dateien je Runde unveränderlich gesichert (`.runden/<n>/`), eine spätere Runde ändert ältere Antworten nicht mehr. Öffnen ohne FIFO-Falle.
- Sandbox: `/tmp` gesperrt, temporäre Dateien je Gespräch (`TMPDIR`).
- „Heute“ in der Anweisung je Gespräch statt beim Start des Dienstes.
- Drosselung: nginx trennt Lesen (300/min) und Schreiben (60/min) je Adresse, erfolgreiche Anmeldung setzt den Adresszähler zurück. Fehlerhafte nginx-Fassung wird beim Einspielen zurückgespielt.
- SQL-Werkzeug liest ungepuffert, die Zeilengrenze schützt den Speicher.
- Einspielen bricht ab, solange Modellprozesse laufen (`ERZWINGEN=1` übergeht das).
- Prüfrunde bekommt die in der Antwort genannten Dateien als Kopie (die Sandbox sperrt das Gesprächsverzeichnis).
- Katalog nach 08b nachgezogen (Session BI-Team): `cr_cockpit_enrolled` und `programmgebuehr` ersetzt. Themenansichten blenden Kennzahlen mit `status=entfallen` aus, die Anweisung erklärt den Status.
- Prüfläufe 0.6.0: Weboberfläche 10/10, Dashboards 5/5 ohne verweigerte `/tmp`-Zugriffe, Diagramm mit Nachfrage und Prüfrunde bestätigt, Selbsttest grün, SQL-Grenze bei Riesenergebnis 0,0 s und 31 MB.
- Regressionstests `tests/test_web_lebenszyklus.py` (scheitern an 0.5.1, bestehen an 0.6.0). README und Docstrings auf den Stand gebracht.

## 0.5.1 (08.11.2026)

- Oberfläche: Die Kopfzeile einer geprüften Antwort zeigt „Verified“ oder „Corrected after verification“.

## 0.5.0 (08.11.2026)

- Prüfrunde: Mit dem Schalter „Verify“ prüft ein unabhängiges zweites Gespräch die Antwort gegen die Daten, bevor sie angezeigt wird (rechnet Kernzahlen selbst nach, prüft Lesart und Abgrenzung). Korrekturen ersetzen die Antwort, eine gescheiterte Prüfung lässt sie mit Hinweis stehen. Nutzenprobe: 11/11 falsche Antworten korrigiert, 12/12 richtige bestätigt, im Mittel rund 45 s zusätzlich.
- Beta: täglicher Selbsttest über die öffentliche Adresse (Timer 06:30, Protokoll `selbsttest.jsonl`), Auswertung der Beta-Ablage mit Vorschlägen für neue Referenzfälle (`betrieb/ablage-auswertung.py`).
- Katalog: SAE-Standard der Abschlussquote aus 08b. Excel für das BI-Team mit Definitionen und 47 offenen Punkten (`handover/`).

## 0.4.7 (08.11.2026)

- Beta-Konto `tester` aus V2 übernommen (gleicher Hash, gleiches Passwort). Kontenprüfung versteht dafür auch argon2-Hashes.

## 0.4.6 (08.11.2026)

- Antwort: SQL wird nie gezeigt, auch nicht auf ausdrücklichen Wunsch (Entscheidung Grigory). Stattdessen Beschreibung von Daten, Abgrenzungen und Rechenschritten in Worten.

## 0.4.5 (08.11.2026)

- Antwort: Wird ein Diagramm oder Dashboard als Datei geliefert, bleibt die Antwort ohne Datei lesbar (Kernaussage mit Zahl, Wertetabelle bzw. wichtigste Werte). Befund: Antworten mit Datei enthielten oft keine Tabelle, einmal keine Kernzahl.
- Referenzvergleich: Dashboard-Kernwerte werden auch im gerenderten Standardzustand gesucht (Chromium als nobody ohne Netz). Werte, die einen Filter brauchen, sind unklar statt verfehlt.
- Referenzlauf 0.4.4: zurückgehalten 13/13, Entwicklung 12/14 (1 verfehlt: Konversionskurve ohne Werte im Text).

## 0.4.4 (08.11.2026)

- Arbeitsweise: Rückfrage nur bei echter Mehrdeutigkeit. Gibt es einen SAE-Standard oder lassen sich die Lesarten nebeneinander zeigen, wird gerechnet und die andere Lesart im Nachweis genannt (Befund Breitentest: 8 von 33 unnötigen Rückfragen).

## 0.4.3 (08.11.2026)

- Sandbox: Gesprächsverzeichnis für die Modell-Shell gesperrt, nur das eigene Arbeitsverzeichnis bleibt zugänglich. Vorher waren Dateien anderer Gespräche lesbar (Befund Grenztest, geprüft mit `codex sandbox`).
- Testtreiber entfernt sein Arbeitsverzeichnis nach dem Sichern der Dateien.

## 0.4.2 (08.11.2026)

- SAE-Wissen STA-016: Kürzel der Media University (MU-BER, MU-COL, MU-FFM, MU-ONL), MUC ist München. Behebt eine Abweichung im Stabilitätstest (Ausschluss über „MU%“ entfernte München).
- Testmaterial: Stabilitätssatz, Grenzfragen, synthetischer Breitensatz, Betriebstest der Weboberfläche (`betrieb/web-last.py`).

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
