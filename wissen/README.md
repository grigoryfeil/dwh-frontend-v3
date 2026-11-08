# SAE-Wissen

Gepflegter Bestand einzelner Aussagen, mit denen der Analyst DWH-Zahlen der SAE fachlich einordnet. Jede Zeile in `eintraege.csv` ist eine Aussage mit Quelle und Gültigkeit. Der Bestand ist keine verdichtete Fassung: Was das Modell sieht, wird aus diesen Zeilen erzeugt, nicht von Hand zusammengefasst.

Aufgenommen wird Wissen, das Zahlen erklärt: Organisation und Standorte, Studienangebot und Abschlüsse, Semester- und Jahreslogik, Bewerbungs- und Einschreibezyklen, interne Begriffe, Ereignisse wie Schließungen, Umstellungen und Systemwechsel. Nicht aufgenommen werden allgemeine Firmenbeschreibung, Handlungsanweisungen oder Antwortregeln an ein Modell, Zählregeln und Definitionen von DWH-Elementen (die gehören in den Katalog unter `katalog/`) und Reparaturen für einzelne Testfälle.

## Format

CSV, Semikolon als Trenner, UTF-8 mit BOM, Felder mit Semikolon, Anführungszeichen oder Zeilenumbruch in doppelten Anführungszeichen. In Excel direkt bearbeitbar. Daten als `JJJJ-MM-TT`, `JJJJ-MM` oder `JJJJ`, je nachdem, wie genau die Quelle ist.

## Spalten

| Spalte | Bedeutung |
| --- | --- |
| `eintrag_id` | Stabile Kennung, Themenkürzel plus laufende Nummer (`FUN-044`). Wird nie neu vergeben und nie umnummeriert, auch wenn das Thema wechselt. |
| `thema` | Eines der Themen unten. |
| `aussage` | Eine einzelne Aussage in ganzen Sätzen, so knapp wie möglich, ohne Bewertung und ohne Anweisung an ein Modell. |
| `bezug_ids` | Katalog-IDs, wenn die Aussage ein DWH-Element betrifft, kommagetrennt: `objekt_id` (Tabellen- oder View-Name), `feld_id` (`objekt.spalte`) oder `kennzahl_id`. Leer, wenn kein DWH-Element betroffen ist. |
| `quelle` | Konkrete Herkunft: Dokumenttitel, Ort (Drive, Basecamp-Projekt, Gmail, Wiki-Seite), Rolle des Verfassers. Mehrere Quellen mit ` / ` getrennt, die tragende zuerst. |
| `quelle_datum` | Datum der tragenden Quelle. |
| `gueltig_ab` | Seit wann der Sachverhalt in der Wirklichkeit gilt. Leer, wenn er seit jeher oder seit unbekannt gilt. |
| `gueltig_bis` | Bis wann der Sachverhalt galt. Leer, solange er gilt. |
| `status` | `aktiv`, `veraltet` oder `offen` (siehe unten). |
| `anmerkung` | Belegstand (etwa „einfach belegt“), Widersprüche, Prüfbedarf, Verweis auf die ersetzende Zeile. |

## Status

- **aktiv:** Die Aussage ist durch die genannte Quelle belegt und gilt im Zeitraum `gueltig_ab` bis `gueltig_bis`.
- **veraltet:** Der Sachverhalt gilt nicht mehr. Die Zeile bleibt stehen, weil Zahlen bis `gueltig_bis` mit ihr gelesen werden. Die Anmerkung nennt die Zeile, die sie ersetzt.
- **offen:** Die Aussage ist nicht sicher belegt, Quellen widersprechen sich, sie ist nur abgeleitet oder eine Festlegung aus V2, die für V3 nicht bestätigt ist. Die Anmerkung sagt, was fehlt.

## Themen

| Thema | Kürzel | Inhalt |
| --- | --- | --- |
| organisation | ORG | Konzern, Gesellschaften, zentrale Bereiche, Rollen, Kreise, Media University |
| standorte | STA | Campus, Kürzel, DUO und DOL, Besonderheiten einzelner Standorte |
| studienangebot | ANG | Produkte, Abschlüsse und Level, Dauern und FTE, Partnerhochschulen, Zulassung, Verträge, Zahlungspläne, Kurscodes, ADE-Level |
| fachbereiche | FAC | Fachbereiche und ihre Kürzel, Umbenennungen, Angebot je Campus, Neuheiten und Teach-out |
| kalender | KAL | Intakes, Study Periods, Census Date, Geschäftsjahr, Budget- und Berichtszyklus |
| funnel | FUN | Lead, Tour, Opportunity, Enrollment, Status und Stages, Konzern- und Cockpit-Stufen, Funnel-Kennzahlen wie sie die SAE nutzt, Kanäle |
| ziele | ZIE | Wer Ziele setzt, Zielfassungen und ihre Abgrenzung, Zwischenziele |
| studienverlauf | VER | Bestandsbegriffe, Kunde und Abbruch, Academic States, Retention-Zahlen in Umlauf, Prüfungsgremien |
| umfragen | UMF | Semesterumfrage, Kursstartumfrage |
| begriffe | BEG | Interne Begriffe, Abkürzungen und Synonyme |
| systeme | SYS | Salesforce, CAS, Cockpit, Dashboards, was nicht im DWH liegt |
| ereignisse | ERG | Ereignisse und Umstellungen, die Zahlen erklären |

Ein neues Thema bekommt ein neues Kürzel und eine Zeile in dieser Tabelle.

## Pflegeregeln

1. **Eine Aussage je Zeile.** Zusammengesetzte Aussagen werden geteilt, wenn sich die Teile unabhängig ändern können.
2. **Nichts überschreiben.** Ändert sich ein Sachverhalt, bekommt die alte Zeile `gueltig_bis` und `status=veraltet`, und eine neue Zeile mit neuer ID und `gueltig_ab` kommt dazu. Die Anmerkung der alten Zeile verweist auf die neue.
3. **Fehler korrigieren** ist kein Wechsel des Sachverhalts: Die fehlerhafte Zeile wird `veraltet` mit der Anmerkung „Korrektur, ersetzt durch …“, `gueltig_bis` bleibt leer.
4. **IDs bleiben stabil.** Keine ID wird gelöscht, umnummeriert oder wiederverwendet. Neue Zeilen bekommen die nächste freie Nummer ihres Themas.
5. **Jede Aussage mit Quelle.** Unbelegtes kommt nicht hinein oder nur mit `status=offen` und Vermerk, was fehlt. Eine Quelle ist konkret: Titel, Ort, Rolle, Datum. „V2-Firmenbild“ allein ist keine Quelle.
6. **Personen als Rollen.** Keine Namen, keine Daten über einzelne Studierende oder Mitarbeitende, keine Gesundheits- oder Gehaltsangaben.
7. **Zahlen aus Quellen** (Ziele, Quoten aus Berichten) stehen mit Stand und Quelle. Zahlen aus der DWH-Kopie stehen hier nicht, Befunde aus Abfragen gehören in den Katalog.
8. **Bezug zum Katalog:** `bezug_ids` nennt die IDs aus `katalog/`. Ändert sich dort eine ID, wird sie hier nachgezogen.
9. **Prüfstand:** Welche Einträge beim Quellenabgleich zuerst zu prüfen sind und was beim Aufbau übernommen, gestrichen und zusammengeführt wurde, steht in `review.md`.
