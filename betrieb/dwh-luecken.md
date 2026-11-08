# Lücken auf DWH-Seite (für das DWH-Team)

Stand: Lieferversuch vom 08.11.2026 (`20261108T153607Z-oemf`), Segment `bi_statistics`, Exportkonto der Frontend-Kopie. Die Lieferung wurde verworfen, weil sie keine neuen Wochendaten enthielt. V3 arbeitet weiter auf dem Bestand vom 06.11.2026.

## 1. Objekte, die sich nicht exportieren lassen (11)

Der Export meldet für alle elf `fehlendes_basisobjekt`. Die View verweist auf eine Tabelle oder View, die im DWH fehlt oder für das Exportkonto nicht lesbar ist, etwa wegen fehlender CAS-Rechte.

| Objekt | Bereich |
|---|---|
| `sf_applications_weekly_by_department` | Salesforce-Wochenstände |
| `sf_enrollments_weekly_by_department` | Salesforce-Wochenstände |
| `sf_tasks_completed_weekly_by_department` | Salesforce-Wochenstände |
| `sf_tasks_total_weekly_by_department` | Salesforce-Wochenstände |
| `sf_tours_attended_weekly_by_department` | Salesforce-Wochenstände |
| `sf_tours_lost_weekly_by_department` | Salesforce-Wochenstände |
| `v_event_stream` | Studienverlauf |
| `v_obt_semester` | Studienverlauf |
| `view_campus_intake_dim` | Dimension Standort und Intake |
| `view_date_intake_spine` | Stichtage je Intake |
| `view_department_dim` | Dimension Fachbereich |

**Bitte prüfen:** Gibt es das Basisobjekt, und kann das Exportkonto es lesen? Lässt es sich reparieren oder freigeben?

## 2. Opportunities vor 2025

Opportunity-Gesamtzahlen je Intake gibt es im Segment erst ab Intake März 2025 (`sales_cohort_persons`, `kpis_opps`, `opps_raw`, `dashboard_opps`). Für Konversionsverläufe über mehrere Jahre fehlt damit der Nenner. Das SAE-Wissen erwähnt Salesforce-Opportunities ab 2022.

**Bitte prüfen:** Lässt sich die Salesforce-Historie vor April 2025 ins Segment laden?

## 3. Bewusst ausgeschlossen (keine Lücke)

Abbruchgründe und Objekte nach Abbruchgrund (`v_early_terminations_by_reason`, `v_enrollments_by_termination_reason` und die Spalten `reason_of_termination*`) sowie die Freitexte der Semesterumfrage. Diese Ausschlüsse sind gewollt und bleiben bestehen.

## 4. Wochenladung

Der Stand vom 08.11. war inhaltlich gleich dem vom 06.11. Die letzten Wochenstichtage (01.11.) waren noch nicht durch neuere ersetzt. Die nächste Lieferung folgt nach der nächsten Wochenladung des DWH.
