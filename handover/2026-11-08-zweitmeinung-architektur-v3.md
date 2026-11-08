# Zweitmeinung: Architektur von DWH Frontend V3 nach dem ersten Fehlgriff

**Von:** Claude für Grigory, 08.11.2026 · **An:** Codex, Modell Astra

## Auftrag

Prüfe, ob Claudes Diagnose des ersten echten Fehlgriffs von V3 zutrifft und ob der vorgeschlagene Umbau die richtige Grundsatzentscheidung ist. Prüfe unabhängig, widersprich mit Begründung, wo du anderer Meinung bist, und nenne, was am Vorschlag für das Ziel entbehrlich ist.

## Ausgangslage

**Was V3 ist.** Ein dünner LLM-Harness für Entscheider der SAE ohne SQL-Kenntnis. Sie stellen Freitextfragen zu einer MariaDB-Kopie des Data Warehouse (Segment BI Analytics, Bestand vom 06.11.2026).

- **Ein Agent:** GPT-6.1 Sol über `codex app-server` mit dem Plugin `data-analytics@openai-curated-remote`.
- **Ein Werkzeug:** `sql` über ein Lesekonto.
- **Anweisung:** rund 4.700 Wörter (`developerInstructions`). Sie enthält Rolle, Arbeitsweise, Antwortform und aus dem Katalog erzeugte Übersichten. Details liest das Modell per Shell in den Katalog-CSVs nach.

**Vorgeschichte.** V2 ist am 08.11. gescheitert. Qualität wurde über Prompt-Regeln, eine Bedeutungsschicht mit eigenem `kennzahl`-Werkzeug, einen Verifier und einen Messapparat aus Modellurteilen gesteuert. Nichts davon hat das Ergebnis messbar bewegt. Deine damalige Architekturprüfung liegt unter Material. V3 setzt deshalb bewusst dünn an. Neue Komponenten kommen nur, wenn eine benannte Fehlerursache sie verlangt.

**Bisherige Ergebnisse.** Der erste Testsatz (7 Fragen) lief gut und reproduzierbar: gleiche Zahlen in zwei Läufen, sinnvolle Rückfragen. Dann stellte der Nutzer im Browser diese Frage:

> „Erstelle eine Grafik zum Verlauf der Konvertierungsrate von Opps zu Enrollments.“ Auf die Rückfrage folgte: „Nein, alle Intakes der letzten Jahre als Kurve.“

Die Antwort lautete: „Eine belastbare Mehrjahreskurve ist mit dieser Datenkopie nicht möglich.“ Gezeigt wurden nur zwei Intakes aus 2026. Der Nutzer hält das für falsch. Seine Begründung: Neuverträge und Opportunities sind je Intake erfasst, daraus ergibt sich die Rate einfach. Er sieht die Ursache in der Gesamtarchitektur, nicht im Einzelfall. Außerdem will er die Qualität nicht per Einzelfrage im Browser prüfen müssen.

**Von Claude erhobene Fakten** (Abfragen auf der Kopie, 08.11.):
- **Neuverträge (CAS)** gibt es in `enrollments_gsan` lückenlos für alle Intakes seit vor 2021, mit Spitzen im März und September.
- **Gesamtzahlen der Opportunities je Intake** gibt es erst ab Intake 0325:
  - `sales_cohort_persons` (je Person, Intakes 0325, 0925, 0326, 0926 und Folgende),
  - `dashboard_opps` (Stichtage, 0326 und Folgende),
  - `opps_raw` (0925, 0926),
  - `kpis_opps` (25T3, 26T3),
  - `sales_kpis_opps` (nur Wochenbewegungen ab Oktober 2025).
- **Folge:** Vor 2025 fehlt in der Kopie der Nenner. Die Salesforce-Strecke setzt im Frühjahr 2025 ein.
- **Die Quellen liefern für denselben Intake sehr verschiedene Raten.** Für 0926 sind es 22,5 % in `dashboard_opps` (Salesforce-Einschreibung durch alle Opps je Produktkategorie) und 7,3 % in `sales_cohort_persons`.
- **Der Trace des Modells** (`laeufe/20261108-144709/ergebnis.json`, zweite Runde): Das Modell liest die Katalogzeilen mehrerer Funnel-Tabellen, fragt dann aber nur `dashboard_opps` ab, die Quelle der Kennzahldefinition `kk.cr_opp_enrollment`, und erklärt den Rest für nicht vergleichbar. Die übrigen Quellen fragt es nie ab. Ein großer Teil der Schritte entfällt auf das Lesen von Plugin-Anleitungen und auf das Diagramm.

**Claudes Diagnose, drei Ursachen:**
1. **Die Kopie ist dünner als angenommen:** Vor 2025 gibt es keine Opportunity-Gesamtzahlen. Das ist eine Datenfrage.
2. **Konkurrierende Quellen, keine maßgebliche:** Mehrere Quellen konkurrieren für dieselbe Kennzahl. Der Katalog beschreibt jedes Objekt für sich, benennt aber nicht, welche Quelle je Kennzahl und Zeitraum maßgeblich ist und wie die Quellen zueinander stehen. Das Modell weicht ins vorsichtige „geht nicht“ aus.
3. **Das Plugin wird an seinem Design vorbei genutzt:** Es erwartet Fachwissen als First-Party-Domäne (`$CODEX_HOME/athena/runtime/local/<domain>/runtime/README.md`, siehe `shared/metric-definitions.md`). Darauf baut sein Ablauf auf: erst Definitionen und maßgebliche Quelle klären, dann rechnen. V3 reicht den Katalog daran vorbei über die Anweisung.

**Claudes Vorschlag:**
- **(a) Katalog als Plugin-Domäne:** Katalog und SAE-Wissen werden als Domäne in der vom Plugin erwarteten Form bereitgestellt, automatisch erzeugt aus den gepflegten CSVs. Die bleiben Quelle der Wahrheit.
- **(b) Maßgebliche Quelle im Katalog:** Der Katalog bekommt eine Angabe zur maßgeblichen Quelle je Kennzahl und Zeitraum samt Beziehung der Quellen. Der Entwurf kommt aus Daten und Kennzahlenkatalog der Leitung BI, Strittiges geht gesammelt an den Nutzer.
- **(c) Automatischer Referenzsatz:** Er entsteht aus Standardberichten der SAE (Wochenreport, Data-Studio-Auswertungen, Kennzahlen der Leitung BI) als unabhängige Wahrheit. Jede Version läuft dagegen, der Nutzer sieht nur Zusammenfassung und strittige Fälle.

## Fragen

1. **Diagnose:** Stimmt sie? Fehlt eine Ursache, oder ist eine falsch gewichtet? Besonders: Liegt die Hauptursache eher im Verhalten des Modells (Definitionstreue vor Beantworten) als im Kontext?
2. **Vorschlag (a):** Ist er unter `codex app-server` mit ChatGPT-Login technisch tragfähig, und lohnt er? Welche Form müsste die Domäne haben? Prüfe dazu die Plugin-Texte unter Material und, falls lokal vorhanden, deine eigene Installation des Plugins.
3. **Vorschlag (b):** Ist das der richtige Ort für das Wissen „welche Quelle wofür“? Oder gehört es in die Datenbank, etwa als kuratierte Views je Kernkennzahl über alle Intakes (zum Beispiel CAS-Neuverträge geteilt durch Salesforce-Opps)? V2 hatte mit einer Bedeutungsschicht samt `kennzahl`-Werkzeug keinen Erfolg. Grenze die Vorschläge davon ab.
4. **Vorschlag (c):** Ist er als Prüfung ohne den Nutzer tragfähig, und wo liegt die Gefahr, wieder einen wachsenden Messapparat zu bauen?
5. **Entbehrlich und Alternative:** Was am Vorschlag ist entbehrlich? Gibt es eine einfachere Grundsatzalternative, die du vorziehen würdest, etwa ohne Plugin oder mit anderem Kontextzuschnitt?

## Material

- `/Users/grigoryfeil/Desktop/DWH Frontend V3/README.md`: Grundlage aus dem Grilling
- `/Users/grigoryfeil/Desktop/DWH Frontend V3/harness/` (`anweisung.md`, `kontext.py`, `sitzung.py`, `lauf.py`) und `/Users/grigoryfeil/Desktop/DWH Frontend V3/betrieb/codex-config.toml`
- `/Users/grigoryfeil/Desktop/DWH Frontend V3/katalog/README.md`, `katalog/review.md`, `katalog/objekte.csv`, `katalog/felder.csv`, `katalog/kennzahlen.csv`
- `/Users/grigoryfeil/Desktop/DWH Frontend V3/wissen/README.md`
- `/Users/grigoryfeil/Desktop/DWH Frontend V3/laeufe/20261108-144709/ergebnis.json`: Trace des Fehlgriffs
- `/Users/grigoryfeil/Desktop/DWH Frontend V3/laeufe/20261108-141024/bericht.md`: erster Testsatz
- `/Users/grigoryfeil/Desktop/DWH Frontend V3/handover/material-plugin/`: Auszüge aus dem Data-Plugin
- `/Users/grigoryfeil/Desktop/KI Projekte/DWH Frontend V2/handover/2026-11-07-zweitmeinung-architektur-v3-ergebnis.md`: deine Architekturprüfung zu V2

## Kriterien

- Das Urteil beruht auf den Fakten und dem Trace, nicht auf allgemeinen Empfehlungen.
- Klar getrennt ist, was eine Datenfrage, eine Kontextfrage und eine Verhaltensfrage des Modells ist.
- Jede vorgeschlagene Komponente ist mit der Fehlerursache begründet, die sie behebt. Nichts darf V2 wiederholen.
- Die Empfehlung ist konkret genug, dass Claude sie umsetzen oder verwerfen kann.

## Grenzen

- Das Material ist der Ausgangspunkt. Recherchiere und nutze deine Werkzeuge, wo du es für nötig hältst. Keine Nachrichten an Dritte.
- Nur lesen. Nichts im Projekt ändern, keine Verbindung zum VPS oder zur Datenbank.
- Sprache Deutsch, generisches Maskulinum, Kommas oder Punkte statt Gedankenstrichen und Semikolons.

## Rückgabe

In deiner Schlussantwort: Urteil in einem Satz, wichtigste Befunde je Frage, begründete Widersprüche zu Claudes Diagnose und Vorschlag, deine Empfehlung, offene Unsicherheiten.
