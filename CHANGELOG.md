# Changelog

## 0.7.0 (10.11.2026)

- Export: Die Knöpfe „PDF report“ und „Excel“ funktionieren. Bisher fehlte die Gegenstelle auf dem Server, jeder Klick endete mit „Export failed“. Übernommen aus V2 und auf das Antwortformat von V3 umgestellt (`web/antwort.py`, `web/bericht.py`, `web/excel.py`, Routen `/api/export.pdf` und `/api/export.xlsx`).
  - PDF: alle beantworteten Runden des Verlaufs mit Frage, Kernaussage, Tabellen, Text, Nachweis und dem Ergebnis von Verify, Kopf und Fuß mit Datenstand und Version. Diagramme und Dashboards sind HTML-Seiten des Modells und erscheinen als Hinweiskasten mit Titel, ihr Skript läuft auf dem Server nicht (Entscheidung Grigory, 10.11.2026). Bilder stehen im Report.
  - Excel: ein Blatt je Antwort mit Tabelle, oben Frage, Kernaussage und Datenstand. Zahlen nach der Schreibweise der Antwortsprache werden echte Zahlen, Prozente Anteile im Prozentformat, Formelanfänge bleiben Text.
  - Nur eigene Gespräche der Session, fremde Kennungen fallen still weg. Ohne Tabelle kein Excel (409).
- Betrieb: neue Abhängigkeiten `reportlab==5.0.1` und `markdown-it-py==4.2.0` (wie in V2), Schrift IBM Plex (OFL) und Logo unter `web/druck/`.
- Tests: `tests/test_export.py`, 8 neue. Backend zusammen 22.

## 0.6.8 (10.11.2026)

- Beispielfragen (Menü „Examples“) gegen 0.6.6 geprüft und zwei ersetzt. Die Kurzantwort „Neueinschreibungen des laufenden Intakes gemessen am Ziel“ endete immer in einer Rückfrage (welcher Intake), ersetzt durch den Studierendenbestand im Vorjahresvergleich (48 s). Das Dashboard zum laufenden Intake brauchte 8,5 Minuten, zu lang für ein Beispiel, ersetzt durch neue Leads je Monat mit Campusfilter (4,3 Minuten). Diagramm, Vergleich und Nachfrage beantworten ohne Rückfrage.

## 0.6.7 (10.11.2026)

Durchsicht des Codes vor dem Beta-Start, Korrekturen mit Regressionstests.

- Runde: Scheitert die Nachverarbeitung einer Antwort, endet die Runde trotzdem. Vorher blieb das Gespräch für immer „läuft“ und belegte einen Platz, etwa wenn sich die Rundensicherung einer Datei bei voller Platte nicht anlegen ließ. Ohne Sicherung gilt wie vorgesehen der aktuelle Stand der Datei, jeder andere unerwartete Fehler zeigt sich als Fehler der Runde.
- Abmelden und Session-Ende während einer Runde: Auch der Prozess der Prüfrunde endet sofort. Vorher rechnete er bis zu 25 Minuten ungezählt weiter. Ein Prozess, der beim Schließen gerade erst startet, wird beendet, und es bleibt kein Gesprächsverzeichnis zurück, das das Einspielen sperrt.
- Oberfläche: Erreicht „Cancel“ den Server nicht (Netz, Drossel), wird der Knopf wieder frei. Vorher blieb er bis zum Ende der Runde gesperrt.
- Betrieb: Selbsttest und Rauchtest (`web-probe.py`) melden sich am Ende ab. Vorher blieb ihr Gespräch bis zum Session-Ende offen, nach dem Rauchtest immer, nach dem Selbsttest bei Zeitüberschreitung, und `betrieb/wartung.sh` verweigerte so lange das Einspielen.
- Regressionstests: 14 im Backend, 2 neue in der Oberfläche (die neuen scheitern am Stand davor).

## 0.6.6 (09.11.2026)

- Katalog und Wissen: Antworten von C. Graf (BI-Team, 09.11.2026) auf die 13 Lücken des BI-Excels und die Änderungen des Objektindex 08c eingearbeitet (Commit 0d74651). Neun Kennzahlen bestätigt oder abgegrenzt, `cr_lead_enrollment` und `pipeline_value` neu definiert, `dauer_lead_enrollment` entfallen, `follow_up_quote` als offene Lücke. Studienverlauf (obt-Objekte) mit der Kollegin geklärt: Quelle bleibt `obt_outcomes`, Werte zum Baudatum. Offen bleiben Nichtabschlussquote, Prognoseformel, Definition Opportunity (Salesteam), P4 und die Nachlieferungen des DWH-Teams (Follow-up, Preise, Opportunities vor 0325).

## 0.6.5 (09.11.2026)

- Oberfläche: Knopf „Sign out“ ganz rechts in der Menüleiste. Er beendet die Session auf dem Server samt ihrer offenen Gespräche (vorhandene Route `/api/abmelden`) und führt zur Anmeldung mit dem Hinweis „You have signed out.“. In der Beta-Ablage gespeicherte Gespräche bleiben.

## 0.6.4 (09.11.2026)

- Sprache: Lässt eine Frage keine Sprache erkennen (nur Zahlen oder Zeichen), antwortet das Modell in der Sprache des bisherigen Gesprächs, zu Beginn auf Englisch wie die Oberfläche. Vorher kam auf eine reine Zeichenfolge eine deutsche Antwort. Kein Schalter, eine Regel in `harness/anweisung.md`. Probe `fragen/sprache-rueckfall.json`: reine Zeichenfolge englisch, Nachfrage „2025?“ bleibt im englischen und im deutschen Gespräch in dessen Sprache.

## 0.6.3 (09.11.2026)

Zweite Prüfung durch Codex Astra (`handover/2026-11-09-zweitmeinung-haertung-review-ergebnis.md`): Befunde zu den Änderungen aus 0.6.0 behoben.

- Prüfrunde: Eine offene Korrektur bleibt bis zur erfolgreichen Übergabe an das Modell erhalten, auch wenn eine Nachfrage abgebrochen wird. Korrigierte Dateien des Prüfers werden übernommen, die Antwort zeigt seine Fassung. Der Prüfer bekommt ein frisch angelegtes Verzeichnis.
- Fehlerpfad: Der Modellprozess wird unter derselben Sperre gelöst, die die Runde freigibt. Eine schon angenommene Folgefrage verliert ihren Prozess nicht mehr.
- Dateien: Rundenstände liegen außerhalb des Arbeitsverzeichnisses (`/var/lib/dwh-frontend-v3/runden`, für die Modell-Shell gesperrt). Alle Kopien laufen über `schreibe_sicher` (keinem Symlink folgen, keine Sonderdateien, exklusiv anlegen), größer als 50 MB wird nicht gesichert. Fehlt eine Sicherung, gilt der aktuelle Stand.
- Grenzen: höchstens 24 behaltene Gespräche, darüber endet das älteste ruhende. Der Verlaufsvorspann nach einer Pause nimmt die jüngsten 6 Runden, Antworten auf 4.000 Zeichen gekürzt.
- Oberfläche: Ist ein Gespräch wirklich beendet (etwa nach einem Neustart), erscheint „This conversation has ended“ statt einer still neu gestellten Frage ohne Verlauf.
- Einspielen: gemeinsame Sperre in `betrieb/wartung.sh` für beide Einspielwege, zählt auch ruhende Gespräche.
- Modell-Shell: `.profile` für `dwhv3` ergänzt den Pfad wieder, den die Login-Shell (`bash -lc`) über `/etc/profile` zurücksetzt. Vorher fehlten `python` und `node` (37 Fehlversuche in einem Lauf).
- Notbremse nach hängendem Abbruch beendet nur den Prozess, das Gespräch ruht und bleibt nutzbar.
- Antwort: keine Technik der Umgebung (Befehle, Serverpfade, nicht ausführbare Prüfschritte), Dateien als relativer Link.
- Grenzfalltest der Beta bestanden (Sprache, Ruhen, 10 Runden, drei Tester, Eingaben, Sandbox, Neustart), Skript `betrieb/web-grenzfaelle.py`.
- Prüfrunde: Korrektur nur, wenn der Nutzer sonst eine falsche Zahl erhielte oder einen falschen Schluss zöge, eine Hauptzahl abweichend vom SAE-Standard ohne Anlass zählt als falsche Zahl. Nutzenprobe danach: 11/11 falsche korrigiert, 13/13 richtige bestätigt (darunter die vorher unnötig korrigierte Definitionsantwort). Messung auf 0.6.2 (Breitensatz, 50 geprüfte Antworten): 1 Korrektur, unnötig, kein übersehener Fehler, 45 s Zusatzzeit. Schalter bleibt optional, Standard aus.
- Testtreiber: Der Prüfer bekommt die genannten Dateien als Kopie wie in der Oberfläche (gemeinsamer Text in `pruefauftrag_text`).
- Regressionstests: 10 (die neuen scheitern am Stand davor).
- Prüfläufe 0.6.3: Weboberfläche 10/10, Dashboard mit Prüfrunde (Prüfer mit Dateikopie, alle Werte bestätigt, keine fehlenden Befehle mehr), Selbsttest grün.

## 0.6.2 (08.11.2026)

- Testtreiber: `--pruefen` fährt jede Antwort durch die Prüfrunde wie der Schalter Verify, mit Weitergabe der Korrektur an die nächste Frage. Der Text dieser Weitergabe kommt für Oberfläche und Testtreiber aus `pruefung.mit_korrektur`.

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
