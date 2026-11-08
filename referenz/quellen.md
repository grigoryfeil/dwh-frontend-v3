# Quellen des Referenzsatzes

Gesucht am 08.11.2026 in Google Drive, Gmail (nur lesend, nichts heruntergeladen oder gesendet), in den lokalen Rohfunden `~/firmenbild-scan/` (Basecamp-Auszüge der Bulletins) und im Objektindex 08b. Nachgerechnet auf `b_20261106t180757z_sooc` mit dem Lesekonto, nur SELECT. Ausführliche Fundtabelle des Such-Agenten: Notizordner der Session-Gruppe, `referenz-quellenfunde.md`.

## Taugt

| Quelle | Stand, Fundort | Was sie trägt | Abgleich mit der Kopie | Fälle |
|---|---|---|---|---|
| Semesterumfrage-GSAN-Bericht August 2026 (Final), Leiter BI und BI-Team | 30.08.2026, Drive-ID `1SlXPCcuwTNdElUx86ucuuLRF_o2Jff3K` | Weiterempfehlung Region 81,7 %, Fragendurchschnitt 3,86, 847 Antworten, Diploma 84,7 gegen Bachelor 72,7 %, je Standort ab 10 Antworten, Zeitreihe ab 2023 | alle geprüften Werte identisch | R-U01, R-U02, R-U03, R-U05 |
| Weekly Marketing & Sales Bulletin, Leitung Marketing & Sales | Basecamp, Posts 02.11.2026 und 21.09.2026 (Rohauszüge `~/firmenbild-scan/claude/pcp/bc-10465381052.txt`, `bc-10322911848.txt`) | Enrollments 0327 je Campus (01.11.), Enrollments und Opportunities 0926 je Campus (20.09.), Wochen-Leads je Campus, Leads seit Jahresbeginn gegen Vorjahr in Prozent | Enrollments 0327: 13 von 14 Campus gleich; Enrollments 0926 Region 1.012 gegen 1.015; Opportunities 0926 5.885 gegen 5.771 (opps_raw 5.897); Wochen-Leads 1.257 gegen 1.266; Leads-Veränderung je Campus ±3 Prozentpunkte | R-F01, R-F02, R-F03, R-F04, R-L02, R-L03 |
| Goals-Sheets je Intake (BI-Team, Salesforce per Goals ETL) | Drive, „2026 - Goals - Intake 0326“, „… 0926“, „2027 - Goals - Intake 0327“ | Ist Study (Diploma, Bachelor, Top-ups, Master) je Campus und Woche | 0327 am 01.11.: 132 gegen 133 (Kern plus Top-up); 0926: 1.124 am 20.09. gegen CAS 1.147; 0326 final 707, Kern 611 gegen CAS 652 | Gegenprobe zu R-F03, R-N01, R-N02 |
| Objektindex 08b, Blatt Kennzahlen v4 (Leitung BI, 02.11.2026) | `~/Desktop/KI Projekte/SAE DWH – Arbeitspaket/08b_…xlsx` | Definitionen Headcount, Neueinschreibungen, Abbruchquote, Weiterempfehlung | Definitionsquelle, keine Zahlen | Lesart von R-B01, R-B03, R-N01, R-N02, R-A01 |
| attrition_executive_summary_20260430.pdf, Data Analyst BI | 30.04.2026, Drive | 30,5 % = 4.121 von 13.490, ausdrücklich Nichtabschluss | Zahl auf der Kopie nicht reproduzierbar (obt_outcomes 2016 bis 2023: 17.517 Datensätze), taugt nur für die Einordnung | R-A02 |

## Taugt nicht oder nur eingeschränkt

| Quelle | Grund |
|---|---|
| Bulletin 02.11.2026, Opportunities 0327 je Campus (Summe 2.430) | Kopie zeigt am selben Stichtag 1.734 in dashboard_opps und v_opps_enriched (einschließlich Opportunities ohne Produkt); Abgrenzung des Bulletins (vermutlich Opportunities ohne Produkt oder anderer Bericht) nicht nachvollziehbar. Für 0926 passt dieselbe Größe dagegen. |
| Bulletin, CR Lead zu Opportunity der letzten 120 Tage (Region rund 10,5 %) | Katalogfassung kk.cr_lead_opp auf sales_cohort_persons ergibt 24,0 % (4.096 neue Opportunities auf 17.094 Leads). Zähler der Kohortentabelle ist rund doppelt so groß wie in den Stichtagsquellen. Nicht als Referenz verwendet. |
| sales_cohort_persons als Basis für Konversion je Intake | Kohorten 0925 und 0926 haben 11.485 und 22.848 Personen mit Opportunity, die Stichtagsquellen rund 5.400 und 5.800. Raten 18,8 % und 7,3 % sind daher keine vergleichbare Reihe. |
| 2026_report_salesforce_cas_data_comparison.pdf | nur Anteile (90 % exakt, 98,5 % bis ±1), keine absoluten Zahlen; dient als Begründung, Salesforce- und CAS-Zählung nebeneinander zuzulassen |
| CFO-Tabelle „FY27_SAE GSAN_Intake 926 Adjustment 120“, Sheet „Conversion Rate Opportunities->Enrollments“ | Planungswerte bzw. Gewinnanteil je Kalenderjahr (2025 27,02 %), keine Rate je Intake in einer Abgrenzung der Kopie |
| Headcount-Report, Reporting Packs, „Enrol status for Final budget“ | nur als Mail-Anhang, ohne Download nicht lesbar; Bestandsfälle sind deshalb nur nachgerechnet |
| Retention-Unterlagen (Retention v2, Mail „Retention Rate Korrektur“) | Quartalsraten für die Umsatzprognose (5 % gegen rund 3,5 %), andere Kennzahl als die Abbruchquote |
| Konzern-Vorlage „Leads - Weekly Reporting Template“ | Testdaten eines fremden Campus |

## Befunde für den Katalog

Beim Nachrechnen aufgefallen, nicht Teil dieses Auftrags:

- `cockpit_l2e_parts` (Konzern-Cockpit) führt Wochenstände ab Intake 0325 (Spring 2025, ab 08.09.2024) und ist damit die Quelle für Konversion über alle Intakes ab 0325. dashboard_opps beginnt erst mit 0326, kpis_opps und opps_raw decken nur 0925 und 0926 ab.
- dashboard_opps 0326 fällt zwischen 15.03. und 29.03.2026 von 575 auf 480 Kern-Enrollments (Opportunities 2.934 auf 2.648), also vor dem Census Date. Die Katalogregel „jüngster Stand bis Census“ nimmt damit den bereinigten Wert, das Goals-Sheet zeigt Ende März 699 Study.
- Die Bulletin-Lesart der CR Opportunity zu Enrollment (Kern auf alle Opportunities, 17,6 % für 0926) und die Katalogfassung (gleiche Produktkategorie, 20,2 %) sind verschiedene Kennzahlen, wie die Zweitmeinung festhält. R-F02 prüft, ob der Analyst die Bulletin-Lesart findet, wenn sie verlangt ist.
- kk.cr_lead_opp reproduziert die Bulletinrate nicht (siehe oben).
