# Katalog

Der Katalog beschreibt, was die Objekte, Felder und Kennzahlen der DWH-Kopie bedeuten. Er ist ein gepflegter Bestand und die Quelle der Wahrheit für diese Bedeutungen: eine Zeile je Element, keine verdichtete Fassung. Was das Modell zu sehen bekommt, wird daraus erzeugt.

## Dateien

| Datei | Inhalt |
|---|---|
| `objekte.csv` | eine Zeile je Tabelle oder View |
| `felder.csv` | eine Zeile je Spalte eines Objekts |
| `kennzahlen.csv` | eine Zeile je Kennzahl |
| `review.md` | Bericht zur Erstbefüllung: Übernahmen, Streichungen, Widersprüche, offene Fragen |

Format: CSV, Semikolon als Trennzeichen, UTF-8 mit BOM, Texte mit Semikolon, Anführungszeichen oder Zeilenumbruch stehen in Anführungszeichen. Die Dateien öffnen direkt in deutschem Excel. Beim Speichern aus Excel „CSV UTF-8 (durch Trennzeichen getrennt)“ wählen. Zeilenumbrüche innerhalb einer Zelle sind erlaubt und trennen in `werte` und `anmerkung` einzelne Aussagen.

## Spalten

### Gemeinsame Spalten

| Spalte | Bedeutung |
|---|---|
| `definition` | Was das Element fachlich bedeutet, in Sprache der SAE. Nur aus einer Quelle, nie erfunden. Leer, wenn keine Quelle eine Definition hergibt. |
| `quelle_definition` | Woher die Definition stammt, so konkret, dass man sie nachschlagen kann: Dokument, Blatt, Nummer, Person und Datum. Kennzeichen wie `[Leitung BI, 02.11.2026]`, `[CG, 06.11.2026]` oder `[Vorschlag aus Drive/Repos]` bleiben aus der Quelle erhalten. |
| `gueltig_ab` | Erster Tag, ab dem die Definition für die Daten gilt (Stichtag, Ereignisdatum oder Studienstart, je nach Element). Leer heißt: seit Beginn oder unbekannt. |
| `gueltig_bis` | Letzter Tag, bis zu dem die Definition für die Daten gilt. Leer heißt: gilt aktuell. |
| `datenstand` | Bestand der Kopie, gegen den die Zeile geprüft wurde, etwa `b_20261106t180757z_sooc` (Lieferung vom 06.11.2026). |
| `status` | `aktiv`, `neu`, `entfallen` oder `offen`, siehe unten. |
| `anmerkung` | Alles, was zur Bedeutung gehört, aber keine Definition ist: Zeitbezug, Herkunft, Datenbefunde, Einschränkungen, Konflikte zwischen Quellen, Vermutungen. Jede Aussage beginnt mit ihrer Art, siehe unten. |

Gültigkeit bezieht sich auf die Zeit der Daten, nicht auf das Datum, an dem jemand die Zeile geschrieben hat. So werden Zahlen eines Zeitraums mit der Definition dieses Zeitraums gelesen. Beispiel: `kpis_leads` hat zwei Zeilen, bis zum Stichtag 08.08.2026 ohne Leads ohne Abschluss, ab 09.08.2026 mit ihnen.

### objekte.csv

| Spalte | Bedeutung |
|---|---|
| `objekt_id` | Stabile Kennung, bei der Erstbefüllung der Name im DWH. Bleibt gleich, auch wenn das Objekt umbenannt wird. |
| `name` | Name des Objekts im DWH (Schema `bi_statistics`). |
| `typ` | `Tabelle` oder `View`, wie im Quell-DWH. In der Kopie liegen alle Objekte als Tabellen vor. |
| `granularitaet` | Was eine Zeile ist. |
| `schluessel` | Spalten, die eine Zeile fachlich eindeutig machen. Der in der Kopie deklarierte Schlüssel steht in `anmerkung`, wenn er abweicht. |

### felder.csv

| Spalte | Bedeutung |
|---|---|
| `feld_id` | Stabile Kennung `objekt_id.spalte`. |
| `objekt_id` | Objekt, zu dem die Spalte gehört. |
| `name` | Spaltenname im DWH. |
| `datentyp` | Datentyp in der Kopie. |
| `werte` | Kodierungen, Wertebereich und Bedeutung einzelner Codes. Werte aus Quellen sind als solche gekennzeichnet. „Im Bestand …“ und „Bereich im Bestand …“ sind beobachtete Werte des genannten Datenstands, keine Definition. |
| `verweist_auf` | `feld_id` des Ziels, wenn die Spalte auf ein anderes Objekt verweist (n:1). |

### kennzahlen.csv

| Spalte | Bedeutung |
|---|---|
| `kennzahl_id` | Stabile Kennung. `kk.*` sind die Kernkennzahlen aus dem Kennzahlenkatalog der Leitung BI, die übrigen tragen die Kennung aus der V2-Bedeutungsschicht. |
| `name` | Name der Kennzahl in Sprache der SAE. |
| `berechnung` | Wie die Kennzahl fachlich entsteht, mit Bezug auf `feld_id`s und bei Quoten auf `kennzahl_id`s. |
| `einheit` | Einheit, in Klammern die Zähleinheit. |

## Status

| Status | Bedeutung |
|---|---|
| `aktiv` | Das Element liegt im Datenstand vor, seine Definition ist belegt. |
| `neu` | Das Element ist mit dem genannten Datenstand neu hinzugekommen und noch nicht von der SAE geprüft. |
| `offen` | Die Definition fehlt oder ist noch nicht bestätigt. Die erste Aussage in `anmerkung` sagt, was offen ist. |
| `entfallen` | Das Element ist im Datenstand nicht (mehr) vorhanden, etwa ein Objekt aus dem Objektindex, das nicht geliefert wurde. `anmerkung` nennt den Grund. |

## Arten von Aussagen in `anmerkung`

| Beginn | Bedeutung |
|---|---|
| `Offen:` | was an der Zeile noch zu klären ist |
| `Neu:` / `Nicht geliefert:` | Herkunft des Status |
| `Zeitbezug`, `Herkunft`, `Zählweise`, `Merkmale`, `Verknüpfung`, `Personenbezug` | Text der genannten Quelle |
| `Bewertung im Objektindex:` | Urteil des Objektindex über die Datenlage |
| `Ergänzung:` | Korrektur oder Ergänzung zur Quelle, mit Kennzeichen der Person |
| `Datenbefund` | am Datenstand gemessene Tatsache, mit Herkunft der Messung |
| `Konflikt` | Widerspruch zwischen Quellen und welche Fassung gilt |
| `Vermutung, nicht belegt` | Vermutung aus Daten oder maschineller Einordnung, keine Definition |

## Pflegeregeln

- **IDs bleiben stabil.** Eine ID wird nie umgewidmet und nie wiederverwendet.
- **Definitionen nur aus Quellen.** Jede Definition nennt ihre Quelle in `quelle_definition`. Eine Vermutung steht höchstens in `anmerkung` und ist als Vermutung gekennzeichnet.
- **Beschreiben, nicht anweisen.** Der Katalog sagt, was ein Element bedeutet. Er enthält keine Anweisungen an ein Modell und keine Regeln, die nur einen bekannten Testfall reparieren.
- **Ändert sich eine Definition, wird die alte Zeile nicht überschrieben.** Sie bekommt `gueltig_bis`, und eine neue Zeile mit derselben ID und `gueltig_ab` kommt dazu.
- **Stellt sich eine Definition als falsch heraus**, gilt sie für keinen Zeitraum. Die alte Zeile bekommt `status = entfallen` und in `anmerkung` den Grund und das Datum, die neue Zeile übernimmt ihren Gültigkeitsbereich.
- **Widersprechen sich Quellen**, gilt die belegte Fassung. Der Widerspruch steht als `Konflikt` in `anmerkung`.
- **Neue Lieferung:** `datenstand` der geprüften Zeilen nachziehen. Neue Objekte und Spalten bekommen eine Zeile mit `status = neu`, auch ohne Definition. Fehlende bekommen `status = entfallen`, ihre Zeile bleibt stehen.
- **Vollständigkeit:** Jedes Objekt und jede Spalte der Kopie hat eine Zeile, auch ohne bekannte Definition.
