# Review der Erstbefüllung

Stand 08.11.2026, Datenstand `b_20261106t180757z_sooc` (Lieferung vom 06.11.2026).

## Ergebnis

| Datei | Zeilen | davon entfallen | gelieferte Zeilen mit Definition | Status offen |
|---|---|---|---|---|
| `objekte.csv` | 117 | 13 | 104 von 104 (100 %) | 15 |
| `felder.csv` | 1.266 | 116 | 644 von 1.150 (56 %) | 649 |
| `kennzahlen.csv` | 74 | 0 | 74 von 74 (100 %) | 26 |

Die Kopie hat 102 Objekte und 1.149 Spalten, alle haben eine Zeile. Zwei Objekte und eine Spalte haben je zwei Zeilen, weil sich ihre Bedeutung über die Zeit der Daten ändert (`kpis_leads` am 09.08.2026, `SF_Tours_by_Department` am 20.02.2023, `sales_kpis_tasks.num_total` am 11.10.2026). Entfallen sind 13 Objekte des Objektindex, die nicht geliefert wurden, mit den 111 Spalten, die der Objektindex für sie kennt (für 9 nicht ausführbare Views gibt es keine Spaltenliste), und 5 bewusst ausgeschlossene Spalten (Kündigungsgründe mit Gesundheitsangaben, Freitexte der Umfrage).

## Quellen und ihr Rang

1. **Schema der Kopie** (`information_schema`, nur lesend): maßgeblich für Vollständigkeit, Datentypen und deklarierte Schlüssel. Es enthält keine Kommentare zu Tabellen oder Spalten.
2. **Objektindex 08b** (DWH-Team, 06.11.2026) mit den Korrekturen der Leitung BI vom 02.11. und den Prüfungen und Festlegungen von CG vom 06.11.: führende Quelle für Objekte, für die bestätigten Antworten, die Kennzahlen v4 und die Begriffe des Funnels. 08 und 08a sind Vorfassungen und in 08b enthalten.
3. **V2-Bedeutungsschicht** (Stand 07.11.2026): Hauptquelle der Spaltenbedeutungen und der übrigen Kennzahlen. Sie beruht überwiegend auf 08b, ergänzt um 47 Projektfestlegungen ohne SAE-Quelle (`festlegungen.md`).
4. **V2-Katalog v7** (aus derselben Lieferung): Fakten zum Datenstand (Zeilenzahlen, beobachtete Werte, Wertebereiche), skriptgeprüfte Datenbefunde, Ausschlussnotizen. Stichproben gegen die Kopie stimmen exakt.
5. **DWH-Referenz-Excel**: aus der Bedeutungsschicht erzeugt, deshalb keine eigene Quelle.

Für Widersprüche zwischen V2 und DWH-Team habe ich zusätzlich die Entscheidungen vom 06.11. in V2 `planung/korrekturen-objektindex-2026-11-06.md` (Abschnitte 5 und 9) gelesen.

## Übernommen

- **Objekte:** Inhalt, Zeilenbegriff, Zeitbezug, Herkunft, Zählweise, Merkmale, Verknüpfung, Personenbezug und die Bewertung des Datenzustands aus 08b, nahezu wörtlich. Die Spalte „Korrektur oder Ergänzung“ ist bereinigt übernommen, mit den Kennzeichen der Personen. Der fachliche Schlüssel stammt aus der Bedeutungsschicht, der deklarierte aus der Kopie.
- **Felder, in dieser Rangfolge:** DWH-Kommentare (2), bestätigte Antworten aus 08b und die Begriffe des Funnels (58, von Hand gefasst), Bedeutungsschicht (446), Texte des Objektindex (80), Zwillingsviews (58). Zwillinge sind fünf Views, die laut 08b inhaltlich identisch mit einer definierten Tabelle sind oder deren Quelle. `werte` enthält Werte aus den Quellen, die Campuslegende sowie beobachtete Ausprägungen (bis 25 Werte) und Bereiche des Datenstands.
- **Kennzahlen:** Die 8 Kernkennzahlen (7 aus den Kennzahlen v4, `kk.leads` aus Katalog v7) sind von Hand gefasst. 66 Kennzahlen kommen aus der Bedeutungsschicht, ihre Berechnung ist aus deren Feldern zusammengesetzt und gegen die vorhandenen `feld_id`s geprüft. Kennzahlen mit Sicherheit „belegt“ sind aktiv, solche mit „festgelegt“ oder „ungeklärt“ offen.

## Gestrichen und warum

- **Anweisungen an das Modell:** etwa „nennen“, „nicht nutzen“, „herausfiltern“, „ohne Angabe gilt“, „steht im Ergebnis“. Rund 100 Stellen sind in Beschreibungen umgeformt oder gestrichen. Wo eine Anweisung eine Tatsache trug, steht jetzt die Tatsache: aus „nie summieren“ wird „nicht additiv“, aus „erst summieren, dann verbinden“ wird „verbindbar nach Verdichtung auf …“.
- **Nutzungsurteile und Antwortlogik:** Aus 08b „Wofür“, „Nutzen für“, „Nicht nutzen für“. Aus der Bedeutungsschicht `eignet_sich_*`, `ableitbar`, `typische_fragen`, `fallstricke`, `hinweise`, `verwandt`, `nicht_moeglich`, Standards für Stichtag und Vergleichsbasis sowie Prüfzeiträume. Sie steuern Antworten und beschreiben keine Bedeutung. Fallstricke, die Tatsachen sind, stehen über die Bewertung im Objektindex weiter in `anmerkung`. Das war bei Eignung und Beziehungen zu weit gegriffen: Sie sind Fachwissen und stehen seit der zweiten Runde beschreibend in eigenen Spalten (siehe unten).
- **14 V2-Kennzahlen:** 5 sind nach einem Messfall aus Diagnose C1 entstanden (F43, F45), 7 sind Varianten „über alle reifen Kohorten“ für den Grundprompt (F31), 2 sind Bestandteile der V2-Lead-Rate, die vom DWH-Team abweicht. Das sind die Testfall-Reparaturen, an denen V2 gescheitert ist.
- **Maschinelle Vorschläge des V2-Katalogs:** Rollen, Dimensionen, 278 Messgrößen, 353 Verknüpfungen und die Modellentwürfe unter den Notizen sind keine Definitionen. Bei Feldern ohne Definition stehen Rolle und Dimension als gekennzeichnete Vermutung in `anmerkung`.
- **Vorfassung v3 der Kernkennzahlen:** keine Historienzeilen. Sie war ein Vorschlag und galt nie als Definition der SAE.
- **Regeln über Objekte hinweg** (Genf, Media University, Produktgruppen, Intake-Zuordnung): keine eigenen Zeilen. Sie gehören ins SAE-Wissen und stehen hier nur, wo sie eine Kennzahl definieren.
- **Personenbezogene Werte:** keine Ausprägungen von Kennungen, Namen oder Freitext.

## Widersprüche und Auflösung

| Thema | Widerspruch | Geltende Fassung |
|---|---|---|
| Headcount | Objektindex ohne DUO, Leitung BI mit DUO | mit DUO (Kennzahlen v4, K3) |
| Neueinschreibungen | Objektindex zählt Personen netto, Leitung BI Verträge über das Census Date hinaus | Verträge (K2) |
| Opportunity | Leitung BI: Interessent mit Beratungsgespräch (Campus Tour). Grigory, 06.11.: Opportunity in Salesforce, Gespräch nicht immer eingetragen | Die Rechnung ist in beiden Fassungen gleich, und laut Prüfung CG hat nur rund 60 % der Opportunities eine Tour. Der Wortlaut folgt deshalb der Rechnung, beide Fassungen sind notiert. |
| Lead-Rate | DWH-Team: alle im Zeitraum angelegten Opportunities. V2: nur Personen, deren Lead im selben Zeitraum liegt, passend zum Wochenreport | DWH-Team (K6), V2-Fassung als Konflikt notiert |
| Top-up der Media University | Grigory: zählt zu topup. Leitung BI und CG: ausgesetzt, MU ganz ausgeschlossen | K2, derzeit kein aktiver Fall |
| Medienvorkurs | Leitung BI, 02.11.: nicht im Kernziel. Festlegung seit 04.05.2026 (Daniel Cross via CG): Kernprodukt | Kernprodukt, ausdrücklich überholt |
| Herbstziel | Leitung BI, 02.11.: nur 0926. CG, 06.11.: 0926 plus 08xx und 10xx, Dubletten gelöscht | CG, 06.11. |
| Zahlen im Objektindex | Zeilenzahlen und Zeiträume stammen aus einer älteren Kopie (StudentStatistics: 40.073 Zeilen bis 25.09.2026, im Bestand 40.608 bis 25.10.2026) | Fakten aus Katalog v7, gleiche Lieferung wie der Bestand |

## Nicht geschafft und Grenzen

- **506 gelieferte Felder ohne Definition (44 %).** Kein Dokument erklärt sie. Schwerpunkte sind `obt_semester` (64 von 79), die zur Löschung vorgesehenen Views `view_datastudio_*` und `bi_*_comparison` sowie `enrollments_gsan` (23 von 27). Bei 23 Objekten hat keine Spalte eine Definition.
- **Spaltentexte der Bedeutungsschicht** sind nicht einzeln gegengeprüft. Ersetzt habe ich sie nur dort, wo eine bestätigte Antwort genauer war.
- **Berechnungen der 66 V2-Kennzahlen** sind maschinell zusammengesetzt und auf vorhandene Felder geprüft, aber nicht jede einzeln fachlich gegengelesen.
- **Die Blätter „Selbst geklärt“ (165) und „Hinweise fürs Audit“ (168)** sind nicht zeilenweise eingearbeitet. Sie wirken über die Objekttexte und Antworten und eignen sich für das SAE-Wissen.
- **Annahme zur Pflege:** Eine Definition, die sich als falsch herausstellt, bekommt `status = entfallen` statt `gueltig_bis`, weil sie für keinen Zeitraum galt (README, Pflegeregeln). Das bitte bestätigen.

## Offene fachliche Fragen an die SAE

1. **Studienverlauf (`obt_*`, Klärung am 09.11.2026):** Welche Fassung ist maßgeblich, `obt_outcomes` oder `v_obt_outcomes` (Frage 12)? Dazu: Ausschlüsse in `obt_semester` (13), konkurrierende Endergebnisse (51), Pausen in der Risikozeit (52), angebrochene Intervalle (53), Reife je Programm (55), ausstehende BA-Bewertung oder Downgrade (56), Abschlussdauer (57), Regel für `is_provisional` (58), Semester nach dem Baudatum (60, 61) und 686 `record_id` ohne Vertragstreffer.
2. **Opportunity:** Gilt der Wortlaut mit Beratungsgespräch oder die Opportunity in Salesforce? Die Antwort des Salesteams steht aus (Offene Punkte 9).
3. **Lead-Rate:** Zählt der Zähler alle im Zeitraum angelegten Opportunities oder nur solche, deren Lead im selben Zeitraum liegt? Wie rechnet der Wochenreport?
4. **Top-up mit der Media University:** Gehört es zu topup, oder ist es mit der MU ausgeschlossen?
5. **Campuscode ROT:** 25 Verträge in `v_sales_prediction_data`, aber kein Eintrag in `dim_campus`. Was ist ROT, und gehört es zur Region?
6. **`enrollments_gsan.active`:** Was bedeutet 0? Der Wert deckt sich nicht mit der Gültigkeit (Frage 17, zurückgestellt).
7. **`dim_quarter_key_date`:** Was bedeuten `graduation_wave` und die Benennung in `quarter_label` (Fragen 69, 70)?
8. **Brüche in den kpis-Tabellen:** Wohin gingen die Unknown-Opportunities am 09.08.2026 (Frage 33)? Warum enthält 25T3 nur ein Viertel der Leads von 26T3 (Frage 27)?
9. **Nullspalten:** `sales_kpis_leads.num_total` und `num_applications` sind durchgehend 0, `sales_kpis_tours.num_total` weicht von der Statussumme ab. Ist das ein Ladefehler oder eine andere Bedeutung?
10. **Prognose in `v_enrollments_region`:** Was hat die Prüfung der Formel am 09.11.2026 ergeben (Frage 50)?
11. **`SF_Tours_somewhere`:** Bestätigt der Abgleich der Summen, dass es Tours mit Tour Type Unknown sind (Frage 45)?
12. **Spaltenkommentare:** Kann das DWH-Team die 506 Spalten ohne Definition im DWH kommentieren? Das wäre die stärkste Quelle für den Katalog.

## Zweite Runde: Quellenordnung, Eignung und Kennzahlvarianten (08.11.2026)

**Anlass.** Auf die Frage nach dem Verlauf der Konversion von Opportunities zu Enrollments über alle Intakes hat der Harness nur `dashboard_opps` abgefragt und daraus geschlossen, eine Mehrjahreskurve sei nicht möglich. Die Zweitmeinung von Codex (`handover/2026-11-08-zweitmeinung-architektur-v3-ergebnis.md`) fand zwei Ursachen im Katalog: Unter `kk.cr_opp_enrollment` standen zwei verschiedene Geschäftskennzahlen, und mit den Modellregeln waren auch Eignung und Beziehungen der Quellen gestrichen worden.

**Neue Spalten.**

| Datei | Neue Spalten | gefüllt |
|---|---|---|
| `objekte.csv` | `thema`, `eignung`, `abdeckung`, `verwandt` | thema, eignung und abdeckung in allen 117 Zeilen, verwandt in 101 |
| `kennzahlen.csv` | `thema`, `zaehleinheit`, `grundgesamtheit`, `zeitbezug`, `quellen`, `verwandt` | alle 78 Zeilen, verwandt in 49 |
| `felder.csv` | keine | 14 Korrekturen, siehe unten |

- **Eignung:** Von Hand gefasst für die Funnel-Quellen, bei denen die gemessene Abdeckung die Eignung bestimmt (`dashboard_opps`, `kpis_opps`, `opps_raw`, `sales_cohort_persons`, `cockpit_l2e_parts`, `v_sales_prediction_data`), und für 36 Objekte ohne V2-Steckbrief, deren Text im Objektindex als Anweisung formuliert ist („Gesperrt, nicht abfragen …“). Für 75 Objekte stammt sie aus den Feldern `eignet_sich_fuer` und `eignet_sich_nicht_fuer` der V2-Steckbriefe, die auf dem Objektindex beruhen. Anweisende Wendungen sind in Beschreibungen umgeformt.
- **Abdeckung:** Für alle 102 gelieferten Objekte gemessen (Zeilenzahl, Spanne der Zeitspalte, je Intake oder Kohorte die Spanne der Stände), für die Funnel-Quellen zusätzlich der letzte Stand bis zum Census Date. Nur `SELECT` mit `MIN`, `MAX`, `COUNT` und `GROUP BY`, über `/etc/dwh-frontend-v3/dwh-leser.cnf`.
- **Verwandt:** Für 55 Objekte aus Funnel, Leads, Einschreibungen, Zielen, Aktivitäten und Stammdaten von Hand, für die übrigen aus der Herkunft im Objektindex abgeleitet („abgeleitet aus“, „Grundlage von“).
- **Kennzahlen:** Zähleinheit, Grundgesamtheit, Zeitbezug und Verwandte der 66 V2-Kennzahlen kommen aus deren Steckbriefen. Für die 8 Kernkennzahlen und die neuen Varianten sind sie von Hand gefasst. `quellen` nennt die Objekte aus der Berechnung mit gemessener Abdeckung.

**Kennzahlvarianten der Konversion Opportunity zu Enrollment.** `kk.cr_opp_enrollment` behält Kennung und Bedeutung (Kennzahlen v4, K6). Vier Lesarten sind neu, also fünf Varianten:

| Kennung | Lesart | Zähleinheit | Quelle und Abdeckung | Status |
|---|---|---|---|---|
| `kk.cr_opp_enrollment` | Salesforce, eingeschriebene je alle Opportunities derselben Produktkategorie zum Stichtag | Opportunity | `dashboard_opps`: 0326, 0926, 0327 läuft | aktiv |
| `cr_opp_enrollment_bulletin` | Weekly Bulletin: Core-Einschreibungen je alle Opportunities des Intakes | Opportunity | `dashboard_opps`: 0326, 0926, 0327 läuft | aktiv |
| `vertraege_je_opportunity` | CAS-Neuverträge je Salesforce-Opportunity, Verhältnis zweier Systeme | Vertrag je Opportunity | Zähler `v_sales_prediction_data` ab 2016, Nenner `dashboard_opps` und für 0925 `kpis_opps`: gemeinsam 0925, 0326, 0926 | offen |
| `cr_kohorte_opp_enrollment` | heutiger Stand einer Recruiting-Kohorte | Person | `sales_cohort_persons`: 0325 bis 0327 | offen |
| `cr_cockpit_enrolled` | Konzern-Cockpit, targetable zu enrolled, damalige Stände | Person mit Opportunity | `cockpit_l2e_parts`: 0325 bis 0327 | offen |

Zur Einordnung die gemessenen Rohwerte, ohne die Ausschlüsse von Genf und Media University, also keine geprüften Kennzahlwerte:

| Intake | K6 Core | Bulletin | Core-Verträge je Opportunity | Kohorte heute | Cockpit |
|---|---|---|---|---|---|
| 0325 | keine Quelle | keine Quelle | kein Nenner | 33,2 % (1.397 / 4.211) | 17,8 % (633 / 3.560) |
| 0925 | keine Quelle | keine Quelle (Bulletin: 21,6 %) | 24,8 % (1.335 / 5.387) | 34,9 % (2.160 / 6.196) | 21,2 % (1.050 / 4.948) |
| 0326 | 18,1 % (480 / 2.648) | 16,8 % (480 / 2.854) | 22,8 % (652 / 2.854) | 30,9 % (1.139 / 3.689) | 17,6 % (550 / 3.128) |
| 0926 | 20,2 % (1.015 / 5.027) | 17,6 % (1.015 / 5.771) | 17,8 % (1.028 / 5.771) | 27,8 % (1.671 / 6.021) | 18,5 % (897 / 4.850) |

Die Bulletin-Lesart trifft für 0926 den Wert des Bulletins (17,2 bis 17,6 %, FUN-047). Das stützt ihre Berechnung aus `dashboard_opps`.

**Befund zur Abdeckung der Funnel-Quellen.** Eine Opportunity-Gesamtzahl gibt es in der Kopie für höchstens fünf Intakes, 0325 bis 0327:

- `dashboard_opps` beginnt mit 0326 (Stände ab 07.09.2025).
- `kpis_opps` führt nur 0925 und 0926, mit Endstand 0925 am 21.09.2025.
- `opps_raw` führt 0925 und 0926, aber 0925 endet am 07.09.2025, vor dem Census Date.
- `cockpit_l2e_parts` führt damalige Stände für 0325 bis 0327.
- `sales_cohort_persons` führt Personen ab Kampagne 2025-2026, also ab 0325, nach heutigem Stand.

Neuverträge dagegen reichen in `v_sales_prediction_data` bis September 2016 zurück, Wochenstände künftiger Einschreibungen in `Goals_Future_Enrolments` bis 19T3, Tours in `SF_Tours_by_Intake` bis 2014, vor Februar 2023 aber ohne Intake. Eine Kurve über mehr Intakes scheitert also am Nenner, nicht am Zähler. Dass Salesforce erst 2025 eingesetzt wurde, folgt daraus nicht: Opportunity-Anlagen reichen in `sales_cohort_persons` bis 03.10.2022 zurück.

**Korrekturen an bestehenden Zeilen.**

- `kk.cr_opp_enrollment`: Die Anmerkung, die Bulletin-Lesart sei eine V2-Festlegung ohne SAE-Quelle, war falsch. Quelle ist das Bulletin (FUN-046), V2 hat sie als F24 übernommen. Sie steht jetzt als eigene Kennzahl.
- `kk.neueinschreibungen`: `start_month` hat das Format JJJJ-MM, nicht MMJJ.
- `pipeline_value`: Die Berechnung begann mit „in None“, einem Fehler der Erstbefüllung. Sie ist aus der Definition ergänzt.
- `felder.csv`: 13 Werteangaben gaben eine Häufigkeit als Bedeutung wieder („Leer bedeutet: Oft“), jetzt „Häufig leer.“ und Ähnliches. `cockpit_l2e_parts.intake` nennt die Zuordnung zum SAE-Intake.

**Einträge in `wissen/eintraege.csv` im Widerspruch zu den neuen Kennungen oder zur Beleglage** (nur aufgelistet, nicht geändert):

| Eintrag | Bezug heute | Widerspruch | Folgerung für das SAE-Wissen |
|---|---|---|---|
| FUN-046 | `kk.cr_opp_enrollment` | Beschreibt die Bulletin-Lesart (Core auf alle Opportunities), nicht K6 je Produktkategorie. Zur Beleglage hatte das Wissen recht, der Katalog ist korrigiert. | Bezug auf `cr_opp_enrollment_bulletin` |
| FUN-047 | `kk.cr_opp_enrollment` | Die Größenordnungen gehören zur Bulletin-Lesart. „Mit Zertifikaten“ (Amsterdam 32,3 %) ist eine weitere Abgrenzung ohne eigene Kennung. | Bezug auf `cr_opp_enrollment_bulletin` |
| FUN-001 | `kk.cr_opp_enrollment` u. a. | Die zweite Konversionsrate der Vertriebssteuerung ist die des Bulletins. | Bezug um `cr_opp_enrollment_bulletin` ergänzen |
| FUN-048 | `kk.cr_opp_enrollment` | Der Verzug der Einschreibungen betrifft jede Stichtagslesart, kein Widerspruch in der Sache. | Bezug um `cr_opp_enrollment_bulletin` ergänzen |
| FUN-060 | `kk.neueinschreibungen` | Die Core-Einschreibungen des Wochenreports sind nach dem Datenbefund eingeschriebene Opportunities in Salesforce, keine CAS-Verträge. | Bezug prüfen: `opportunities_eingeschrieben`, `cr_opp_enrollment_bulletin` |
| FUN-038 | `cockpit_l2e_parts` | Die Cockpit-Rate hat jetzt eine eigene Kennung. | Bezug um `cr_cockpit_enrolled` ergänzen |
| FUN-042 | leer | Raten als Verhältnis aktueller Bestände entsprechen `cr_kohorte_opp_enrollment` und dem Cockpit. | Bezug setzen |
| FUN-037 | `cockpit_l2e_parts` | Das Cockpit führe admitted erst seit Oktober 2026. Die Kopie zeigt admitted an früheren Ständen (0925 am 21.09.2025: 631, 0926 am 20.09.2026: 704). | prüfen, vermutlich rückwirkend befüllt |

Alle Bezüge im SAE-Wissen verweisen auf vorhandene Katalogkennungen.

**Grenzen dieser Runde.**

- Eignung aus den V2-Steckbriefen kann Projektfestlegungen von V2 enthalten, sie ist nicht Satz für Satz gegen den Objektindex geprüft.
- `verwandt` ist für 44 Objekte nur aus der Herkunft abgeleitet und nennt dort keine Abgrenzungen. 16 Objekte haben keine belegte Beziehung.
- Zähleinheit, Grundgesamtheit und Zeitbezug der 66 V2-Kennzahlen sind übernommen, nicht einzeln geprüft.
- Die Rohwerte oben sind Messungen ohne die Ausschlüsse. Als Kennzahlwerte taugen sie erst nach Anwendung der Grundgesamtheit.

**Neue offene Fragen an die SAE.**

13. **Welche Konversion ist gemeint?** Meint die SAE mit „Konversion Opportunity zu Enrollment“ die Rate je Produktkategorie (K6) oder die des Bulletins (Core auf alle Opportunities)? Die Kennzahlen v4 und das Bulletin weichen voneinander ab.
14. **Verträge je Opportunity:** Gehören Top-ups, Zusatzverträge, Verlängerungen und Produktwechsel zur selben Grundgesamtheit wie die Opportunities? Erst dann ist das Verhältnis als Geschäftskennzahl lesbar.
15. **Historische Opportunity-Zahlen:** Gibt es Endstände der Opportunities vor 0325 in Salesforce oder in den Wochen-Excel des Bulletins, die das DWH-Team liefern könnte? Ohne sie bleibt jede Konversionskurve auf fünf Intakes begrenzt.
