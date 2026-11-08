# DWH Frontend V3

Ein Analyst für die SAE: Entscheider stellen Freitextfragen zu den Daten des Data Warehouse (Segment BI Analytics) und bekommen eine fachlich eingeordnete Antwort. Der Grundgedanke: Nicht jede Frage verdient ein eigenes Dashboard.

V3 ist ein Neuansatz. V2 (`grigoryfeil/dwh-frontend-v2`) ist gescheitert und eingefroren. Aus V2 wird nichts ungeprüft übernommen. Lieber neu denken als ein falsches Learning übernehmen.

Stand der Grundlage: Grilling vom 08.11.2026. Gesteuert wird nach dem Skill `harness`.

## Zweck und Nutzer

- **Nutzer:** Grigory und eine kleine Gruppe Entscheider der SAE ohne SQL-Kenntnis.
- **Eine gute Antwort** besteht aus:
  - einer Kernaussage mit Zahl in ein bis drei Sätzen,
  - einer Tabelle oder einem Diagramm, wo es hilft,
  - einem Nachweis: Daten, Zeitraum, Definition, Annahmen.
- **SQL** wird nie gezeigt, auch nicht auf ausdrücklichen Wunsch (Entscheidung 08.11.2026). Der Rechenweg steht in Worten im Nachweis.
- **Dashboards und Diagramme** kommen als schlanke Offline-HTML-Datei unter der Antwort. Die Antwort selbst bleibt ohne die Datei lesbar.
- **Nachfragen** des Nutzers im selben Gespräch funktionieren von Anfang an, auch nach einer Pause: Ein ruhendes Gespräch bekommt beim Fortsetzen den sichtbaren Verlauf mit.
- **Antwortzeit:** meist unter 3 Minuten, Dashboards 5 bis 13 Minuten, mit sichtbarem Fortschritt. Zeitlimit 25 Minuten je Runde. Die Kosten pro Frage werden gemessen.

## Haltung zur Qualität

- **Der eine schwere Fehler** ist eine falsche Zahl, die plausibel aussieht. Er wird nicht über Verbote und Regelwerke bekämpft. Das Halluzinationsverbot aus V1 und die Regelrunden aus V2 haben das System lahmgelegt.
- **Bei Mehrdeutigkeit** entscheidet der Analyst mit Urteil:
  - Er fragt nach, wenn die naheliegenden Lesarten zu wesentlich verschiedenen Antworten führen und der Nutzer das mit einem Satz klären kann. Die Nachfrage ist qualifiziert: eine gezielte Frage mit konkreter Empfehlung, sodass ein „ja“ reicht.
  - Er fragt höchstens einmal je Frage. Gibt es einen SAE-Standard oder lassen sich die Lesarten nebeneinander zeigen, rechnet er statt zu fragen.
  - Andernfalls rechnet er mit einer offen benannten Annahme.
  - Er hält keine Antwort aus Vorsicht zurück.
- **Wo das Gleichgewicht** zwischen Fragen und Rechnen liegt, zeigen echte Antworten. Es wird nicht vorab festgelegt.

## Bauweise: dünner Harness

- **Ein Agent:** OpenAI Sol 6.1 mit dem Data-Plugin.
- **Datenzugriff:** nur lesend auf die DWH-Kopie.
- **Kontext:** Katalog und SAE-Wissen.
- **Option:** ein Schalter für eine Prüfrunde („Verify“). Ein unabhängiges zweites Gespräch rechnet die Antwort nach, bevor sie erscheint, und korrigiert sie bei Bedarf. Die Kopfzeile zeigt „Verified“ oder „Corrected after verification“.
- **Kein** Router, keine Regel- oder Bedeutungsschicht, kein Pflicht-Verifier.
- **Eine weitere Komponente** kommt nur, wenn echte Ausgaben eine benannte Fehlerursache zeigen, die sie behebt, und der Effekt auf Fällen trägt, an denen nicht getunt wurde.

## Bausteine

| Baustein | Herkunft | Umgang in V3 |
|---|---|---|
| Oberfläche (Claude Design) | V2 `oberflaeche/`, Entwurf `design_handoff_sae_data_desk/` | Übernommen, nur minimal ergänzt (Versionsanzeige, Prüfvermerk) |
| DWH-Kopie | MariaDB-Container auf dem VPS, ein Schema je Lieferung | Eingefrorener Bestand während der Entwicklung |
| Katalog (Objekte, KPI-Definitionen) | V2-Katalog `katalog/1.2` | Erst nach Review übernehmen |
| SAE-Wissen (E-Mails, Docs, Wiki) | V2 `firmenbild/` | Erst nach Review übernehmen, später gegen die Quellen abgleichen |
| VPS-Betrieb | V2 `betrieb/` | Entschlackt übernehmen, kein Ballast |
| Harness-Logik aus V2 | Prompts, Schichten, Regeln | Wird nicht übernommen |

## Katalog und SAE-Wissen: gepflegte Bestände

Ob der Analyst die Bedeutung der DWH-Elemente und das SAE-Wissen versteht, ist ein zentraler Erfolgsfaktor. Beides ist deshalb ein gepflegter Bestand, der sich ändern und wachsen kann. Es ist keine verdichtete Fassung.

- **Katalog** (`katalog/`): drei verknüpfte Tabellen.
  - Objekte: Tabellen und Views.
  - Felder: Spalten.
  - Kennzahlen.
  - Jede Zeile ist ein Element mit Definition, Quelle der Definition, Gültigkeit (`gueltig_ab`, `gueltig_bis`), Datenstand und Status.
- **SAE-Wissen** (`wissen/`): einzelne Einträge mit Aussage, Thema, Quelle, Datum und Gültigkeit. Wo ein Eintrag ein DWH-Element betrifft, verweist er auf dessen Katalog-ID.
- **Historie durch neue Zeilen:** Ändert sich eine Definition, bekommt die alte Zeile ein `gueltig_bis`, und eine neue kommt dazu. So werden Zahlen eines Zeitraums mit der Definition dieses Zeitraums gelesen.
- **Format:** CSV im Repo, semikolongetrennt und in Excel bearbeitbar. Git versioniert jede Änderung.
- **Herkunft des Modellkontexts:** Was das Modell sieht, wird aus diesen Beständen erzeugt und nie von Hand verdichtet.

## Benannte Annahmen

Diese Annahmen gelten, bis eine echte Ausgabe ihnen widerspricht.

- **Modellzugang:** Das Modell läuft über `codex app-server` mit ChatGPT-Login, weil das Data-Plugin nur so verfügbar ist.
- **Oberfläche:** Sie behält ihren API-Vertrag aus V2. Das Backend bedient davon nur, was V3 braucht.
- **Datenstand:** Vorerst gilt der jüngste Bestand auf dem VPS (Stichtag 06.11.2026), bis ein frischer eingespielt wird.
- **Ausschlüsse:** Spalten mit Abbruch- oder Kündigungsgründen und Freitexte der Umfragen sind nicht in der Kopie. Fehlende DWH-Objekte stehen in `betrieb/dwh-luecken.md`.

## Bewusst offen (Fog)

- **Beurteilung von Richtigkeit und Nutzen:** Das klärt sich an echten Antworten, die Grigory beurteilt, nicht vorab. Modellurteile ersetzen das nicht. In V2 waren sich Modellrichter nur in 58 bis 67 % der Fälle einig.

## Arbeitsweise

- **Steuerung:** Eine zentrale Steuersession steuert, versioniert und führt zusammen.
- **Parallelität:** Unabhängige Arbeitspakete laufen parallel in eigenen Sessions, jede in einem eigenen Worktree und auf einem eigenen Zweig.
- **Grigory wird eingebunden**, wenn echte Ausgaben vorliegen oder wenn ein Fix nicht trägt. Dann kommt eine Diagnose statt der nächsten Reparaturrunde.
- **Betrieb:** Beta mit einem geteilten Konto `tester` für zwei bis drei Tester und Beta-Ablage aller Gespräche (`betrieb/ablage-auswertung.py` schlägt daraus Referenzfälle vor). Ein täglicher Selbsttest prüft die ganze Kette. Eingespielt wird nur, wenn kein Gespräch läuft (`betrieb/einrichtung.sh` bricht sonst ab).
- **Sandbox der Modell-Shell:** kein Netz, kein Zugriff auf andere Gespräche, Zugangsdaten und `/tmp`, temporäre Dateien je Gespräch.

## Versionierung

- Die Versionen lauten `0.MINOR.PATCH`. Die Oberfläche zeigt sie als „V3 0.x.y“.
- **PATCH:** kleine Iterationen und Verbesserungen.
- **MINOR:** Funktionsänderungen.
- Die Null vorn bleibt bis zur Freigabe als echte Auslieferung.
- Jede Version bekommt einen Tag `vX.Y.Z` und einen Eintrag in [CHANGELOG.md](CHANGELOG.md). Die aktuelle Version steht in `VERSION`.
