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
- **Nutzungsurteile und Antwortlogik:** Aus 08b „Wofür“, „Nutzen für“, „Nicht nutzen für“. Aus der Bedeutungsschicht `eignet_sich_*`, `ableitbar`, `typische_fragen`, `fallstricke`, `hinweise`, `verwandt`, `nicht_moeglich`, Standards für Stichtag und Vergleichsbasis sowie Prüfzeiträume. Sie steuern Antworten und beschreiben keine Bedeutung. Fallstricke, die Tatsachen sind, stehen über die Bewertung im Objektindex weiter in `anmerkung`.
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
