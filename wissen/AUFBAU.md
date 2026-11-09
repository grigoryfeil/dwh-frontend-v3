# Aufbau des Katalogs im DWH

Stand: Grilling vom 09.11.2026 mit Grigory. Diese Datei ist die Vorlage für den Katalog. Die Inhalte selbst liegen im DWH, nicht im Repo.

## Wofür

Der Katalog ist das Datenlexikon des DWH. Er sagt, was jedes Objekt und jedes Feld bedeutet, wie die SAE ihre Kennzahlen definiert und rechnet und welches Fachwissen man braucht, um Zahlen einzuordnen. Er ist geschrieben für einen Analysten, der neu bei der SAE anfängt. Damit taugt er zugleich für das BI-Team als Ort der internen Definitionen und für DWH Frontend V3, dessen Modell ihn per SQL liest.

Leitlinien:

- **Eine Quelle:** Der Katalog liegt im DWH und wird nur dort gepflegt. Kein Excel und keine Repo-Datei daneben.
- **So einfach wie möglich:** vier Tabellen, wenige Spalten, kurze Einträge. Lang wird ein Eintrag nur, wo eine Falle oder Abgrenzung es verlangt.
- **Erweiterbar ohne Umbau:** Neue Bereiche wie Finance oder HR, neue Objekte und neue Kennzahlen sind immer neue Zeilen. Es gibt keine Themenspalte, weil sich Themen überlagern. Ordnung entsteht über Verweise und Stichworte.

## Die vier Tabellen

Schema `katalog` im DWH. Es geht mit jeder Lieferung in die Kopie des Frontends, damit Zahlen und Definitionen denselben Stand haben. Mit * markierte Spalten sind Pflicht.

### `objekte`: eine Zeile je Tabelle oder View

| Spalte | Inhalt |
|---|---|
| `objekt`* | Name im DWH. |
| `beschreibung`* | Was es ist und wofür man es nimmt, ein bis zwei Sätze. |
| `eine_zeile_ist`* | Granularität, etwa „ein Standort“ oder „ein Stand je Stichtag, Campus und Produkt“. |
| `herkunft`* | Quellsystem: CAS, Salesforce, Konzern, manuell gepflegt. |
| `hinweise` | Fallen und wofür man das Objekt nicht nimmt, mit dem besseren Objekt. Wenige Sätze, Einzelheiten zu Spalten gehören zu den Feldern. |

### `felder`: eine Zeile je Spalte, für jede Spalte jedes Objekts

| Spalte | Inhalt |
|---|---|
| `objekt`*, `feld`* | Objekt und Spaltenname im DWH. |
| `beschreibung`* | Ein Satz, auch wenn der Name scheinbar alles sagt. |
| `werte` | Codes und ihre Bedeutung, wo es feste Werte gibt. |
| `verweist_auf` | `objekt.feld`, mit dem verknüpft wird. |
| `hinweise` | Fallen beim Filtern oder Zählen. |

### `kennzahlen`: eine Zeile je KPI oder Variante

| Spalte | Inhalt |
|---|---|
| `kennzahl`* | Lesbare, stabile Kennung, klein und mit Unterstrich, etwa `opportunities`. |
| `name`* | Name, wie er bei der SAE heißt. |
| `synonyme` | Andere Namen, unter denen danach gefragt wird, kommagetrennt. |
| `definition`* | Fachdefinition in Prosa: was gezählt wird, für wen (Grundgesamtheit, Ausschlüsse), zu welchem Zeitpunkt (Stichtag, Zeitraum, Kohorte). |
| `berechnung`* | Rechenweg im DWH in Worten: welche Objekte und Felder, welche Abgrenzungen, welcher Stichtag. |
| `standard` | `ja`, wenn dies der SAE-Standard ist. Bei einer Variante die Kennung des Standards. Leer, wenn es keinen Standard gibt. |

### `wissen`: ein Fakt je Zeile

| Spalte | Inhalt |
|---|---|
| `nr`* | Laufende Nummer, wird nie neu vergeben. |
| `aussage`* | Ein Fakt in ein bis drei ganzen Sätzen. |
| `stichworte`* | Freie Suchwörter, kommagetrennt, mehrere erlaubt. |
| `bezug` | Betroffene Objekte, Felder (`objekt.feld`) oder Kennzahlen, kommagetrennt. |

### Gemeinsame Spalten in allen vier Tabellen

| Spalte | Inhalt |
|---|---|
| `status`* | `belegt` oder `offen`. |
| `anmerkung` | Bei `offen`: was fehlt oder sich widerspricht. |
| `gueltig_ab`, `gueltig_bis` | Nur, wenn sich ein Sachverhalt geändert hat (siehe Pflege). |
| `geaendert_am` | Setzt die Datenbank selbst. |

Technisches wie Datentyp, Zeilenzahl und abgedeckten Zeitraum liefert das DWH selbst. Das pflegt niemand im Katalog.

## Was wohin gehört

- **Wissen** beschreibt, wie die SAE in der Wirklichkeit funktioniert: Organisation, Standorte, Studienangebot, Kalender, Begriffe, Ereignisse. Ein Wissenseintrag ist auch ohne DWH verständlich.
- **Objekte, Felder und Kennzahlen** beschreiben, wie das im DWH abgebildet ist, samt Zählregeln und Fallen.
- **Kennzahlen** tragen Fachdefinition und Rechenweg im selben Eintrag, damit beides nicht auseinanderläuft. Das Wissen enthält keine KPI-Definitionen.
- **Nicht in den Katalog:** Zahlen aus dem DWH, Anweisungen an ein Modell, Namen von Personen, Daten über einzelne Studierende oder Mitarbeitende, Quellenangaben, also wer eine Angabe wann belegt hat.

Beispiel: Dass die Media University eine Schwestermarke mit Campus in Berlin, Köln, Frankfurt und online ist, ist Wissen. Dass sie im Feld `dim_campus.campus_code` die Kürzel `MU-BER`, `MU-COL`, `MU-FFM` und `MU-ONL` trägt und man sie über `MU-%` ausschließt, nie über `MU%` (das schließt München mit aus), steht bei diesem Feld unter `werte` und `hinweise`.

## Beispielzeilen

Die Beispiele zeigen Form und Länge. Ihr Inhalt wird bei der Erstbefüllung geprüft.

`objekte`:

| objekt | beschreibung | eine_zeile_ist | herkunft | hinweise |
|---|---|---|---|---|
| dim_campus | Standorte der SAE und der Media University mit Kürzel, Salesforce-Name, Anzeigename, Land und Sprache. Übersetzt Kürzel und Namen ineinander. | ein Standort | manuell gepflegt | Kennt nur den heutigen Stand. Andere Schreibweisen löst `dim_campus_alias` auf, historische CAS-Codes `DimCampusOutcomes`. |

`kennzahlen` (gekürzt):

| kennzahl | name | definition | berechnung | standard |
|---|---|---|---|---|
| opportunities | Opportunities | Opportunities eines Intakes in Salesforce in allen Zuständen (verloren, offen, eingeschrieben, storniert), ohne Media University, Stand am Census Date des Intakes. | Aus `dashboard_opps` die vier Zustandsspalten summiert, jüngster Stichtag bis zum Census Date aus `v_intake_census`. Nicht über Stichtage summierbar. | ja |

## Pflege

- **Neues im DWH** (Objekt, Spalte, Bereich): neue Zeilen anlegen. Ein Eintrag ohne gesicherte Bedeutung kommt mit `status=offen` und Anmerkung hinein.
- **Sachverhalt ändert sich** (neue Definition, Umstellung, Schließung): Die alte Zeile bekommt `gueltig_bis`, und eine neue Zeile mit `gueltig_ab` kommt dazu. So werden Zahlen eines Zeitraums mit der Definition dieses Zeitraums gelesen.
- **Fehler:** direkt in der Zeile korrigieren.
- **Kennungen** (`kennzahl`, `nr`) bleiben stabil, werden nie umbenannt oder wiederverwendet, weil andere Einträge darauf verweisen.

## Tabellen anlegen (Entwurf für MariaDB)

Das DWH-Team passt Datentypen und Schema an das Quellsystem an.

```sql
CREATE SCHEMA katalog;

CREATE TABLE katalog.objekte (
  id             INT AUTO_INCREMENT PRIMARY KEY,
  objekt         VARCHAR(128) NOT NULL,
  beschreibung   TEXT NOT NULL,
  eine_zeile_ist VARCHAR(255) NOT NULL,
  herkunft       VARCHAR(128) NOT NULL,
  hinweise       TEXT,
  status         ENUM('belegt','offen') NOT NULL DEFAULT 'offen',
  anmerkung      TEXT,
  gueltig_ab     DATE,
  gueltig_bis    DATE,
  geaendert_am   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE katalog.felder (
  id             INT AUTO_INCREMENT PRIMARY KEY,
  objekt         VARCHAR(128) NOT NULL,
  feld           VARCHAR(128) NOT NULL,
  beschreibung   TEXT NOT NULL,
  werte          TEXT,
  verweist_auf   VARCHAR(255),
  hinweise       TEXT,
  status         ENUM('belegt','offen') NOT NULL DEFAULT 'offen',
  anmerkung      TEXT,
  gueltig_ab     DATE,
  gueltig_bis    DATE,
  geaendert_am   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE katalog.kennzahlen (
  id             INT AUTO_INCREMENT PRIMARY KEY,
  kennzahl       VARCHAR(64) NOT NULL,
  name           VARCHAR(255) NOT NULL,
  synonyme       VARCHAR(500),
  definition     TEXT NOT NULL,
  berechnung     TEXT NOT NULL,
  standard       VARCHAR(64),
  status         ENUM('belegt','offen') NOT NULL DEFAULT 'offen',
  anmerkung      TEXT,
  gueltig_ab     DATE,
  gueltig_bis    DATE,
  geaendert_am   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE katalog.wissen (
  id             INT AUTO_INCREMENT PRIMARY KEY,
  nr             INT NOT NULL,
  aussage        TEXT NOT NULL,
  stichworte     VARCHAR(500) NOT NULL,
  bezug          VARCHAR(1000),
  status         ENUM('belegt','offen') NOT NULL DEFAULT 'offen',
  anmerkung      TEXT,
  gueltig_ab     DATE,
  gueltig_bis    DATE,
  geaendert_am   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

## Übergang

1. **Erstbefüllung:** Der heutige Bestand (`katalog/*.csv`, `wissen/eintraege.csv`), der Objektindex 08b und die Antworten des BI-Teams im Excel vom 08.11.2026 werden in die vier Tabellen übertragen und dabei gekürzt. Nicht Belegtes kommt als `offen`. 08b ist Rohstoff, nicht Vorlage. Ergebnis: `handover/2026-11-09-katalog-erstbefuellung.xlsx`, je Tabelle ein Blatt.
2. **Einbau:** Das DWH-Team legt das Schema an, lädt die Erstbefüllung und nimmt das Schema in den Export der Frontend-Kopie auf.
3. **Umstellung des Frontends:** Das Modell liest den Katalog selbst per SQL. Die erzeugten Themenansichten (`harness/kontext.py`) und die CSV-Bestände im Repo entfallen. Bis dahin arbeitet das Frontend unverändert mit den CSV-Dateien.

Annahmen: Die bestehenden Kennungen der Kennzahlen bleiben erhalten, nur ohne das Präfix `kk.`. Das Schema `katalog` lässt sich bei Bedarf auch zwischen zwei Lieferungen nachliefern.
