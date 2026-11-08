# Referenzsatz

Gegen diesen Satz läuft jede V3-Version automatisch. Grigory liest nur die Zusammenfassung und die strittigen Fälle, nicht jede Antwort im Browser.

## Dateien

| Datei | Inhalt |
|---|---|
| `faelle-entwicklung.json` | Fälle, die beim Entwickeln gelesen und zur Diagnose genutzt werden dürfen |
| `faelle-zurueckgehalten.json` | Fälle, die beim Entwickeln niemand liest; sie zeigen, ob eine Verbesserung über die bearbeiteten Beispiele hinaus trägt |
| `vergleich.py` | deterministischer Vergleich eines Laufs mit dem Satz, ohne Modellrichter |
| `quellen.md` | gefundene Berichte, was taugt und was nicht |

## Ablauf je Version

```bash
python3 referenz/vergleich.py --fragen alle > fragen/referenz.json
```

Auf dem VPS `harness/lauf.py fragen/referenz.json` ausführen, dann:

```bash
python3 referenz/vergleich.py laeufe/<lauf>/ergebnis.json -o laeufe/<lauf>/vergleich.md
```

Für Berichte an entwickelnde Sessions `--verdeckt` setzen: Dann fehlen Frage, Erwartung und Fundstelle verfehlter zurückgehaltener Fälle.

## Aufbau eines Falls

| Feld | Bedeutung |
|---|---|
| `id` | `R-<Thema><Nummer>`, wird nie wiederverwendet |
| `thema` | funnel, bestand, leads, neueinschreibungen, abbruch, umfrage, grenze |
| `art` | `wert` (Zahl erwartet), `grenze` (echte Datengrenze), `quellgrenze` (Grenze der zuerst naheliegenden Quelle ist nicht die Grenze der Frage), `dashboard` (Dashboard als Ausgabe erwartet) |
| `rolle` | `entwicklung` oder `zurueckgehalten`, muss zur Datei passen |
| `fragen` | Gesprächsverlauf, wie ihn `lauf.py` abspielt, siehe unten |
| `lesart` | gemeinte Kennzahl, Abgrenzung, Stichtag, zulässige Alternativen |
| `datenstand` | Bestand der Kopie, auf dem die Referenz gilt |
| `erwartet` | Prüfungen, siehe unten |
| `quelle` | Bericht, Stand, Fundstelle |
| `nachvollzogen` | eigene Rechnung auf der Kopie und ob sie zum Bericht passt |
| `sicherheit` | hoch, mittel oder niedrig mit Grund |

Elemente in `fragen`:

- Ein Text ist eine Frage, die immer gesendet wird. Das gilt auch für echte Nachfragen wie „Und wie war das vor einem Jahr?“ oder Korrekturen wie „Nein, alle Intakes der letzten Jahre als Kurve.“, die auch nach einer direkten Antwort sinnvoll sind.
- `{"falls_rueckfrage": "Ja."}` ist die vorbereitete Antwort auf eine erwartbare Rückfrage. `lauf.py` sendet sie nur, wenn die vorige Antwort mit `[Rückfrage]` beginnt, sonst wird sie übersprungen. Diese Form gilt für jede Folgefrage, die nur eine Rückfrage beantwortet.
- `vergleich.py` legt die Liste Schritt für Schritt auf die Runden: Ein übersprungenes Element lässt das Gespräch vollständig. Kam eine Rückfrage, aber die Antwort fehlt im Lauf, ist der Fall unklar. Wurde die Antwort ohne Rückfrage trotzdem gesendet (Läufe vor der Umstellung), zählt diese Runde nicht.

Prüfungen in `erwartet`, alle beziehen sich auf die Antwort der letzten gewerteten Runde, also der letzten Frage oder der letzten bedingten Antwort, der eine Rückfrage vorausging:

- `zahl`: `werte` (eine oder mehrere zulässige Lesarten) mit `toleranz` oder `toleranz_rel`, oder `bereich`. `einheit: "%"` verlangt ein Prozentzeichen. `kontext` ist ein regulärer Ausdruck, der in derselben Zeile stehen muss, bei Tabellen genügt die Kopfzeile. `werte_unklar` nennt Werte, die eine zulässige Aufschlüsselung statt der Standardaussage sind: Stehen nur sie da, ist der Fall unklar.
- `einschraenkung`: jedes Muster in `muster` kommt vor.
- `verboten`: das Muster kommt nicht vor.
- `dashboard`: prüft die Dateien des Gesprächs, die `lauf.py` unter `laeufe/<lauf>/dateien-<nr>/` ablegt und in `gespraeche[].dateien` listet. Verfehlt, wenn keine `.html`-Datei dabei ist. Sonst muss jeder Eintrag in `kernwerte` in den eingebetteten Daten stehen, gelesen aus den `.html`-Dateien (`<script type="application/json">`-Blöcke, auch auf mehrere Blöcke verteilt, und JSON-Listen von Objekten im Skripttext) und aus mitgelieferten `data.json`:
  - `werte` mit `toleranz` oder `toleranz_rel` wie bei `zahl`.
  - `zeilen` ist eine Liste von Varianten, jede Variante eine Liste von Bedingungen, jede Bedingung eine Liste zulässiger Werte, etwa `[[["2026-10"], ["BO", "Bochum", "SAE Bochum"]]]`. Eine Zeile einer Tabelle (Liste von Objekten) erfüllt eine Bedingung, wenn eines ihrer Felder einen der Werte hat, verglichen ohne Groß- und Sonderzeichen; Datumsangaben wie `2026` oder `2026-10` gelten als Präfix. Der Kernwert ist gefunden, wenn die Summe eines Zahlenfelds über alle Zeilen, die alle Bedingungen einer Variante erfüllen, passt. Feldnamen sind gleichgültig.
  - Mit `einheit: "%"` zählen zusätzlich Summe durch Summe zweier Felder, das Mittel eines Felds (Flags je Person) und bei genau einer Zeile ihr Einzelwert, als Prozent oder Anteil.
  - Steht der Wert nur als lose Zahl in den Daten oder im Text der Seite, ist der Fall unklar, fehlt er, verfehlt mit den nächstliegenden Summen als Fundstelle.
  - `sekunden_max` erzeugt nur einen Hinweis zur Laufzeit der Runde, kein verfehlt.

  Ob das Dashboard richtig rendert, prüft das Skript nicht, das bleibt beim Menschen. Bestanden heißt: Dashboard geliefert, Kernwerte aus den Daten herstellbar. Ob die Standardsicht beim Öffnen diese Werte zeigt, ist damit nicht geprüft.

Ergebnis je Fall: **bestanden**, **verfehlt** oder **unklar**. Unklar heißt: Gespräch endet mit Rückfrage, ist abgebrochen, unvollständig oder ein erwarteter Wert steht nur ohne passenden Kontext da. Unklare Fälle liest Grigory, sie sind kein Fehlschlag des Harness.

## Regeln

1. **Herkunft.** Eine Referenz stammt aus einem SAE-Bericht (Bulletin, Umfragebericht, Goals-Sheet und Ähnliches) oder ist auf der Kopie nachgerechnet und als solche vermerkt. Nie aus einer Modellantwort, nie allein aus Katalog oder SAE-Wissen, gegen deren Fehler der Satz schützen soll. Kennzahldefinitionen der Leitung BI (Kennzahlen v4) dürfen die Lesart bestimmen.
2. **Übernahme eines Berichtswerts** nur, wenn Berichtsstand, Grundgesamtheit und Rechenweg zur Kopie passen. Sonst wird der Fall nachgerechnet mit Vermerk oder fällt weg. Wo mehrere Lesarten vertretbar sind, stehen alle in `werte` oder im `bereich`, mit Begründung in `lesart`.
3. **Wachstum** nur um belegte Fehlerarten (in einem echten Lauf beobachtet, mit Lauf und Fall benannt) und um relevante Geschäftsfragen. Keine Fälle, die nur eine gerade gebaute Regel bestätigen.
4. **Stabilität.** Eine Erwartung wird nicht geändert, damit ein Lauf besteht. Geändert wird sie nur, wenn die Referenz selbst falsch war oder ein neuer Bestand eingespielt ist, mit Vermerk in `nachvollzogen`. Bei neuem Bestand werden alle Fälle neu nachgerechnet und `datenstand` angepasst. `vergleich.py` warnt, wenn Lauf und Referenz verschiedene Bestände haben.
5. **Prüfmechanik** bleibt schlicht: Zahlen, Muster, Verbote. Kein Modellrichter, keine Bewertungsregeln je Fall.

## Zurückhaltung

- Mindestens ein Drittel der Fälle ist `zurueckgehalten`, heute 13 von 27.
- Wer am Harness, an Anweisung, Katalog oder Wissen arbeitet, liest `faelle-zurueckgehalten.json` nicht und übernimmt keine dieser Fragen als Beispiel. Berichte an solche Sessions laufen mit `--verdeckt`.
- Muss ein zurückgehaltener Fall zur Diagnose geöffnet werden, wechselt er nach `entwicklung`, und ein neuer Fall gleicher Art kommt in den zurückgehaltenen Teil.
- Die Datei liegt derzeit im Repo und ist damit für jede Session lesbar. Ob sie getrennt abgelegt wird (etwa nur auf dem VPS), ist offen.

## Stand

27 Fälle auf Bestand `b_20261106t180757z_sooc` (Lieferung 06.11.2026), angelegt 08.11.2026.

| Thema | entwicklung | zurückgehalten |
|---|---:|---:|
| Funnel | 2 | 2 |
| Neueinschreibungen | 1 | 1 |
| Bestand | 2 | 2 |
| Leads | 2 | 3 |
| Abbruch | 3 | 2 |
| Umfrage | 3 | 2 |
| Grenze ohne Daten | 1 | 1 |

Dashboards als Ausgabe prüfen R-B04, R-A05 und R-L05. Davon prüfen echte Datengrenzen R-U03, R-G01, R-B02, R-L04, R-U04, R-G02; Quellgrenzen, die nicht die Grenze der Frage sind, R-F01 (Konversionskurve ab 0325), R-F04, R-N02.

## Änderungen an Prüfungen

| Datum | Fall | Rolle | Änderung | Grund |
|---|---|---|---|---|
| 08.11.2026 | R-A01 | entwicklung | Erwartung von „jüngste reife Kohorte 28,9 % oder 2022_H2 30,0 %“ auf „reife Kohorten ab 2018_H1 30,2 %“, 28,9 % ergibt nur noch unklar | Unabhängige SAE-Quelle: Dashboard „Student Outcomes – Cohort View“ (Eva Elliott, Stand 26.10.2026) legt die Standardaussage fest; Kopie identisch |
| 08.11.2026 | R-A02 | zurückgehalten | Prüfungsänderung auf Grundlage einer unabhängigen Quelle, nicht wegen eines Laufergebnisses: Abbruchquote von Bereich 23,0 bis 29,5 % auf 28,5 % (alle Programme ohne Certificates, ab 2018_H1), 24,9 % mit Certificates ergibt unklar | Dasselbe Dashboard; vorher gab es für die Abbruchquote keinen Berichtsbeleg, alle vier Kopfwerte für alle Programme stimmen mit der Kopie überein |
| 08.11.2026 | R-N01, R-A01 | entwicklung | vorbereitete Antwort auf die Rückfrage als `{"falls_rueckfrage": …}`, Erwartungen unverändert | In Lauf 20261108-154943 beantwortete der Analyst R-A01 ohne Rückfrage richtig, gewertet wurde aber die Runde nach dem ins Leere gelaufenen „Ja.“. Auf den sieben vorhandenen Läufen ändert sich nur dieses Urteil |
| 08.11.2026 | R-A03, R-A04 | entwicklung, zurückgehalten | neu: Effective und Original Award BA, End without Award alle Programme | relevante Geschäftsfragen mit unabhängiger Quelle (dasselbe Dashboard) |
| 08.11.2026 | R-B04, R-A05, R-L05 | entwicklung, entwicklung, zurückgehalten | neu: Dashboard-Fälle zu Bestand, Studienerfolg und Leads mit Prüfart `dashboard` | Dashboards als Ausgabeformat, Probe der Steuersession (Lauf 20261108-165804, Bestands-Dashboard in 702 s); Werte wie R-B01, R-A01 bis R-A04 und R-L01 |
