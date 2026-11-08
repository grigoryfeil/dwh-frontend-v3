# Review des Aufbaus SAE-Wissen

Stand 08.11.2026. Aufgebaut aus dem V2-Firmenbild und gegen die Rohfunde unter `/Users/grigoryfeil/firmenbild-scan/` geprüft. Ergebnis: 399 Einträge in 12 Themen, davon 35 `offen` und 11 `veraltet`.

## Vorgehen

1. **Ausgangsmaterial:** die gepflegte V2-Schicht (`firmenbild/schicht/kern.md` und die Module Studium, Marketing-Funnel, Studienqualität), dazu `wiki-befund.md`, `offene-fragen.md` und einzelne Ereignisse aus `vorrat/`. Jede Aussage wurde in einzelne Zeilen zerlegt, das V2-Quellenkürzel wurde in Dokument, Ort, Rolle und Datum aufgelöst.
2. **Prüfung gegen die Rohfunde:** Vier Blöcke wurden Eintrag für Eintrag gegen `claude/*.md`, `codex/*.md` und die Anhänge geprüft. Wo der Rohfund etwas anderes sagt, gilt der Rohfund. Die Quellenangabe wurde dann auf die Rohquelle umgestellt. Studienangebot, Kalender, Funnel, Ziele, Studienverlauf, Umfragen und Fachbereiche sind vollständig geprüft. Organisation, Standorte, Begriffe, Systeme und Ereignisse sind nur an den tragenden Aussagen stichprobenhaft geprüft.

| Block | Einträge | bestätigt | teilweise | abweichend | nicht gefunden | nicht prüfbar |
| --- | --- | --- | --- | --- | --- | --- |
| Studienangebot | 72 | 49 | 16 | 0 | 0 | 7 |
| Kalender, Funnel | 92 | 64 | 16 | 3 | 0 | 9 |
| Ziele, Studienverlauf, Umfragen, Fachbereiche | 127 | 86 | 22 | 3 | 5 | 11 |
| Organisation, Standorte, Begriffe, Systeme, Ereignisse | 98 | Stichprobe von rund 35 Einträgen, keine Abweichung in der Sache, mehrere Präzisierungen |

„Teilweise“ hieß meist: Der Kern stimmt, ein Zusatz aus V2 (Datum, Monat, Begründung) stand nicht in der Quelle. Solche Zusätze wurden gestrichen oder als Anmerkung gekennzeichnet.

## Übernommen

- **Was:** alles, was DWH-Zahlen einordnet: Region, Campus und Organisation, Produkte mit Dauer und FTE, Kurscodes, Fachbereiche und Angebot je Campus, Intakes, Study Periods, Census Date, Geschäftsjahr und Budgetzyklus, Funnelstufen mit Status, Stages und Customer Lifecycle, Funnelkennzahlen so, wie die SAE sie nutzt, Zielfassungen, Bestandsbegriffe, Abbruch- und Retention-Zahlen in Umlauf, Semesterumfrage, Begriffe, Systeme und Ereignisse.
- **Neu aus den Rohfunden:** Bestand je Fachbereich März 2026 (ANG-073), Census-View-Reihe FY23 bis FY28 (VER-047), Verteilung der Zielkürzung 0926 (ZIE-022), Planannahmen zu Intakes (ZIE-021), Lücken im DWH laut Audit (SYS-018), Wirkungsdatum des Genfer Buy-outs (ERG-017), dritte Lesart von „Kernprodukt“ (BEG-029).
- **Historie als Zeilen:** Wo sich ein Sachverhalt geändert hat, stehen alte und neue Zeile nebeneinander: Middlesex und Hertfordshire (ANG-006, ANG-005), PCP-Regel (FUN-053, FUN-054), CR Lead → Opportunity (FUN-043, FUN-044), Nurturing (FUN-008, FUN-009), Follow-up-Quote (FUN-056, FUN-057), Non-EEA-Gebühr (ANG-053, ANG-054), Teilnahmeziel der Umfrage (UMF-011, UMF-012), Modul- und Semesterumfrage (UMF-001, UMF-002), Genf (ERG-012).

## Korrigiert gegenüber V2

- **Census Date:** V2 setzte „Kursstart plus 14 Tage, 0926 am 21.09.2026“. Die Rohquellen nennen 23.09.2026 für 0926 und 27.03.2024 für 0324, beide Male Mittwoch der dritten Woche, 16 Tage nach Kursstart. Eine schriftliche Regel fehlt. Beide Lesarten stehen als `offen` (KAL-010, KAL-011).
- **Top-up und Kernprodukt:** V2 übernahm „Top-up ist kein Kernprodukt“. Basecamp-Mitteilungen von Administration und Academics zählen Top-up-Bachelor und Master zu den Kernprodukten, das Marketing-Reporting nicht. Drei Lesarten, als `offen` geführt (ANG-034, BEG-008, BEG-029, FUN-060).
- **Application:** V2 nannte als dritte Bedeutung den Salesforce-Status. In Wochen-Excel, CFO-Tabelle und DWH ist Application die Opportunity (FUN-039).
- **PCP:** Umstellung am 13.10.2025, Wortlaut „zum selben Zeitpunkt im Vorjahr“, nicht „Kalenderwoche ab September“. Der Gebrauch blieb uneinheitlich (FUN-053, FUN-054).
- **Weitere:** Hertfordshire seit 2022 ohne gesicherten Monat (ANG-005), Software Engineering ist Herts-validiert, anders als V2 (ANG-008), Kursstartumfrage laut Mail wieder aufgenommen, laut Leiter BI nicht aufgegriffen (UMF-025), Feldzeit August 2026 bis 22.08. (UMF-006), Vertriebsprämie nur in Grundzügen belegt (ZIE-017), Intake einer Opportunity von Hand geändert heißt „fällt aus dem Reporting“ (FUN-023), Fast-Track nur für den Bachelor auf Deutschland und Amsterdam beschränkt (ANG-031), Voice Acting auch nicht in Genf (FAC-024), Budgetablauf als Ablauf 2026, nicht als fester Jahreskalender (KAL-015).

## Gestrichen

- **Antwortregeln an das Modell:** „So liest Sol …“, „Sol nennt …“, „ohne Angabe gilt …“, die Methodendiskussion zur Weiterempfehlung (Net Promoter Score, Forced Choice) und Hinweise, wie Zahlen zu präsentieren sind. Grund: keine Handlungsanweisungen im Wissen.
- **Zählregeln und Definitionen von DWH-Elementen:** der V2-Wegweiser Frage → Objekt, Filter wie `NOT LIKE 'MU-%'`, Mindestfallzahlen der Umfrage, Kennzahlformeln aus `bedeutung/`. Grund: gehören in den Katalog.
- **Befunde aus Abfragen der DWH-Kopie:** MPMC teils unter DUO, teils unter Bochum, Level-6-Belegung in `report_module_students`, Startmonat 2016-04 ohne Nettovertrag, Zahlungsplan nur als Zahlencode in `enrollments_gsan.payment_plan_type`, fehlender Academic State. Grund: technische Datenbefunde, Übergabe an den Katalog.
- **Vorrat Finance und HR ohne Bezug zu DWH-Zahlen:** P&L-Kaskade, Kostenstellenschema, Steuerungsquoten, Staff Survey, CapEx-Regel, Staff-Rabatte, EBITDA-Ziele außer der Lage in ERG-007. Grund: diese Daten liegen nicht im DWH.
- **Prozesse und Tagesgeschäft:** Berichtswege der Umfrage, Call-Rhythmus, Klickanleitungen, Untervermietung, Schwestermarken außer MU und ICMP. Grund: erklären keine Zahl.

## Zusammengeführt

- **Die zwei Fassungen des Kerns** (eingefrorene `kern.md` v0.12.0 und gepflegte `schicht/kern.md`) unterschieden sich fast nur in Antwort- und Zählregeln. Übernommen sind die gemeinsamen Sachaussagen, damit entfällt der Konflikt.
- **Mehrfach erzählte Sachverhalte** stehen jetzt je einmal: Genf (in V2 an fünf Stellen, jetzt STA-002, ERG-011 bis ERG-014, ERG-017, ZIE-016), Census Date (Kern, Studium, Funnel), Kernprodukte (Kern, Studium, Funnel, offene Fragen), Customer Lifecycle (Studium, Funnel), DUO (Kern, Studium, Studienqualität, Wiki-Befund), Zielfassungen (Kern, Funnel, offene Fragen).

## Quellenlage

- **Rohfund bestätigt:** gut zwei Drittel der vollständig geprüften Einträge (199 von 291), meist mit Basecamp-, Drive- oder Gmail-Quelle samt Datum und Rolle.
- **Nur Wiki (26 Einträge):** Die Wiki-Rohtexte liegen nicht im Scan, nur der V2-Befund mit Seitennamen und Seitendatum. Die Einträge tragen den Vermerk „Nur Wiki-Beleg“.
- **Tragend ist der Leiter BI (16 Einträge):** Festlegungen aus dem V2-Dialog vom 02. und 06.11.2026. Wo Rohquellen widersprechen, stehen sie als `offen`.
- **Bericht Semesterumfrage August 2026:** im Scan nur das Deckblatt. Fünf Kennzahlen daraus sind `offen` (UMF-014, -015, -016, -020, -022).
- **`bezug_ids`:** am 08.11.2026 gegen `katalog/` nachgetragen, 194 von 399 Einträgen verweisen auf Objekte, Felder oder Kennzahlen. Alle IDs sind per Skript gegen den Katalog geprüft.

## Zuerst prüfen beim Quellenabgleich

Tragend und unsicher, in dieser Reihenfolge:

1. **KAL-010, KAL-011 Census Date:** Regel und Datum 0926 (21.09. oder 23.09.) im CAS und beim Head of Administration klären. Hängt an No Show, Enrollment-Endstand und Vertriebsprämie.
2. **ANG-034, BEG-008, BEG-009, BEG-029, FUN-060 Kernprodukt und Top-up:** Welche Abgrenzung gilt in welchem Bericht. Jede Zielerreichung hängt daran.
3. **ZIE-012, ZIE-013, ZIE-015 Zielfassungen:** Welche Fassung `dashboard_goals` abbildet und welche für 0327 gilt (690, 620, 587, 582 oder 581).
4. **FUN-019 Opportunity ohne Tour:** Festlegung des Leiters BI gegen die Rohdefinition „Opportunity = absolvierte Tour“.
5. **VER-001, VER-005 Bestandsbegriffe:** Stichtag 25. und Beginn 2019 nur aus dem Objektindex, der CFO spricht von zwei Stichtagen im Jahr.
6. **FUN-054 PCP:** „Selber Zeitpunkt“, „selbe Kalenderwoche“ oder „gleicher Abstand zum Kursstart“. Schriftliche Definition einholen.
7. **STA-005, STA-006, STA-009 DUO:** Zuordnung von Level 6 und Mastern zu Campus, seit wann.
8. **KAL-003 August- und Oktoberstarts zum Septemberintake:** nur Festlegung, im Index widersprüchlich.
9. **FUN-009, FUN-010 Nurturing und automatische Statuswechsel:** nur Wiki, verzerren Lead-Status an Stichtagen.
10. **VER-015 bis VER-017 Academic States:** nur Wiki, nötig für die Lesart von Abbruch und Pause.
11. **ANG-047, ANG-057, ANG-058 AZAV 12 Monate und Zahlungsplan-Codes:** widersprüchliche Lesarten, AZAV-Fälle im CAS sonst nicht erkennbar.
12. **ERG-011, ERG-017 Genf:** wirtschaftliche Wirkung 01.09.2026, Austritt Ende September, Closing Anfang Oktober. Für Zeitreihen den maßgeblichen Stichtag festlegen.

## Nicht geschafft

- Organisation, Standorte, Begriffe, Systeme und Ereignisse sind nicht Eintrag für Eintrag gegen die Rohfunde geprüft, nur die tragenden Aussagen.
- Die Wiki-Seiten und der Umfragebericht August 2026 sind nicht am Original gelesen.
- `bezug_ids` müssen nachgezogen werden, wenn sich IDs im Katalog ändern.
