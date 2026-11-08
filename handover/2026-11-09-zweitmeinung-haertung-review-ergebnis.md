**v0.6.2 ist noch nicht beta-tauglich, weil Prüferkorrekturen in bestimmten Fortsetzungen verloren gehen, korrigierte Dashboards falsch ausgeliefert werden können und der neue Fehlerpfad laufende Folgerunden beenden kann.**

Geprüft ist Commit `1abfa069`, identisch mit `v0.6.2`, gegen `v0.5.1` und den Bericht vom 08.11. Ich habe nichts verändert, keine Betriebsserver kontaktiert und die ausgeschlossenen Verzeichnisse nicht gelesen. Die beschriebenen Simulationen verwenden Originalfunktionen mit Ersatzmodellen und Dateioperationen im Speicher.

1. **Kritisch, die korrigierte Dashboard-Datei kann durch die falsche Datei ersetzt werden. Neu durch die Prüferkopien.**  
   Stellen: [web/app.py:379](</Users/grigoryfeil/Desktop/DWH Frontend V3/web/app.py:379>), [web/app.py:485](</Users/grigoryfeil/Desktop/DWH Frontend V3/web/app.py:485>).  
   **Szenario:** Der Analyst erzeugt `dashboard.html` mit 100. Der Prüfer korrigiert seine Kopie unter `pruefung/dashboard.html` auf 80 und antwortet mit `[Dashboard](dashboard.html)`. Die anschließende Übersetzung löst diesen relativen Link wieder im Hauptverzeichnis auf. Der Nutzer bekommt den korrigierten Text und Prüfvermerk, aber das Dashboard mit 100. **Im Speicher reproduziert.**  
   **Kleinster Fix:** Dateiverweise einer Prüferkorrektur ihrem tatsächlichen Ursprungsverzeichnis zuordnen und die korrigierten Dateien vor der Rundensicherung übernehmen.

2. **Kritisch, Abbrechen kann eine noch nicht übermittelte Prüferkorrektur löschen. Unvollständige Behebung des alten Befunds 2.**  
   Stelle: [web/app.py:445](</Users/grigoryfeil/Desktop/DWH Frontend V3/web/app.py:445>).  
   **Szenario:** Der Nutzer hat die korrigierten 80 gesehen, der Hauptprozess kennt noch seine 100. Er stellt eine Nachfrage und bricht sie ab, bevor `g.frage()` aufgerufen wird. `eintrag.korrektur` wurde bereits gelöscht. Der Abbruchpfad behält den Hauptprozess. Die nächste Nachfrage erhält deshalb weder die Korrektur noch einen neu aufgebauten Verlauf und kann wieder auf 100 rechnen. **Der Verlust der Korrektur ist reproduziert.**  
   **Kleinster Fix:** Die ausstehende Korrektur erst nach erfolgreicher Modellrunde löschen. Bei Abbruch vor oder während der Übermittlung behalten.

3. **Kritisch, `.runden/` ist versioniert, aber nicht unveränderlich. Alter Befund 3 nur teilweise behoben.**  
   Stellen: [web/dateien.py:97](</Users/grigoryfeil/Desktop/DWH Frontend V3/web/dateien.py:97>), [codex-config.toml:121](</Users/grigoryfeil/Desktop/DWH Frontend V3/betrieb/codex-config.toml:121>).  
   **Szenario:** Eine spätere Modellrunde verändert, etwa durch rekursive Dateibearbeitung oder Prompt-Injektion, `.runden/1/dashboard.html`. Dieses Verzeichnis gehört weiterhin zum beschreibbaren Arbeitsbereich. Die alte Antwort liefert danach unter unveränderter URL andere Zahlen aus. Die Dateiroute erkennt die Veränderung nicht.  
   **Kleinster Fix:** Rundensicherungen außerhalb des für das Modell beschreibbaren Arbeitsverzeichnisses halten. Unterschiedliche Unterverzeichnisse innerhalb desselben Schreibbereichs sichern nur gegen das gewöhnliche Überschreiben von `dashboard.html`.

4. **Kritisch, tatsächlicher Kontextverlust führt weiterhin zu stillen neuen Gesprächen. Alter Befund 4 teilweise offen.**  
   Stellen: [App.tsx:207](</Users/grigoryfeil/Desktop/DWH Frontend V3/oberflaeche/src/App.tsx:207>), [App.tsx:225](</Users/grigoryfeil/Desktop/DWH Frontend V3/oberflaeche/src/App.tsx:225>).  
   **Szenario:** Die Notbremse schließt ein Gespräch. Die Oberfläche verwirft dessen Kennung, behält aber die bisherigen Antworten. Auf „Und davon Deutschland?“ beginnt sie ein neues Gespräch ohne Vorgeschichte. Auch der automatische Wiederholungsversuch bei 404 oder 410 besteht unverändert. Das normale Ruhen verhindert diesen Fehler inzwischen, die verbliebenen Schließpfade nicht.  
   **Kleinster Fix:** Einen tatsächlichen Gesprächsverlust sichtbar anzeigen und die Folgefrage nicht automatisch ohne Kontext senden.

5. **Hoch, die Aufräumroutine einer Fehlerrunde beendet eine bereits laufende Folgerunde. Neuer Wettlauf.**  
   Stelle: [web/app.py:467](</Users/grigoryfeil/Desktop/DWH Frontend V3/web/app.py:467>).  
   **Szenario:** Nach einem Modellfehler wird `laeuft=False` gesetzt. Während anschließend archiviert wird, nimmt das Backend bereits die nächste Frage an. Diese verwendet den noch zugeordneten Prozess. Danach führt die alte Fehlerrunde `loese_prozess(eintrag)` aus und beendet ihn. **Reproduziert mit 202 für die neue Frage und anschließendem Beenden ihres aktiven Prozesses.**  
   **Kleinster Fix:** Das Gespräch bis zum Abschluss des Aufräumens als laufend behandeln. Den zu beendenden Prozess unter derselben Sperre eindeutig abtrennen, bevor neue Fragen zugelassen werden.

6. **Hoch, neue Kopierziele erlauben Symlink-Umleitung und führen die FIFO-Falle wieder ein.**  
   Stellen: [web/dateien.py:100](</Users/grigoryfeil/Desktop/DWH Frontend V3/web/dateien.py:100>), [web/app.py:379](</Users/grigoryfeil/Desktop/DWH Frontend V3/web/app.py:379>).  
   **Szenario:** Das Modell legt `.runden/1/bericht.csv` oder `pruefung/bericht.csv` als Symlink auf die beschreibbare `codex-home/auth.json` an. Das Backend folgt beim Kopieren diesem Link und überschreibt die Zugangsdaten außerhalb der Modell-Sandbox. Weitere Modellstarts können für alle Tester scheitern. Ist das Kopierziel stattdessen eine FIFO ohne Leser, blockiert `open(..., "wb")` außerhalb des Modellzeitlimits. Ein Prozessabbruch löst diesen Dateizugriff nicht.  
   **Kleinster Fix:** Auch Zielpfade komponentenweise ohne Symlink-Verfolgung öffnen, bestehende Sonderdateien ablehnen und neue Dateien exklusiv anlegen. Für Rundensicherungen zusätzlich Befund 3 beachten.

7. **Hoch, die Einspielsperre stellt kein Wartungsfenster sicher. Alter Befund 8 bleibt offen.**  
   Stellen: [einrichtung.sh:9](</Users/grigoryfeil/Desktop/DWH Frontend V3/betrieb/einrichtung.sh:9>), [einrichtung.sh:66](</Users/grigoryfeil/Desktop/DWH Frontend V3/betrieb/einrichtung.sh:66>), [web-einrichtung.sh:55](</Users/grigoryfeil/Desktop/DWH Frontend V3/betrieb/web-einrichtung.sh:55>).  
   **Szenario:** Beim einmaligen `pgrep` läuft kein Modellprozess. Während Installation und Kopieren nimmt die weiterhin erreichbare Anwendung eine neue Frage an. Anschließend werden ihre Dateien ausgetauscht und der Dienst neu gestartet. Außerdem sind ausschließlich ruhende Gespräche für `pgrep` unsichtbar und verlieren beim Einspielen trotzdem ihren Verlauf. Der direkte Aufruf von `web-einrichtung.sh` umgeht die Prüfung vollständig.  
   **Kleinster Fix:** Vor der Prüfung neue Fragen sperren, laufende Runden auslaufen lassen und erst danach austauschen. Beide Einspielwege müssen denselben Schutz verwenden.

8. **Hoch, ruhende Gespräche und Rundensicherungen können die gemeinsamen Ressourcen erschöpfen. Neu verschärft.**  
   Stellen: [web/app.py:297](</Users/grigoryfeil/Desktop/DWH Frontend V3/web/app.py:297>), [web/app.py:270](</Users/grigoryfeil/Desktop/DWH Frontend V3/web/app.py:270>), [web/dateien.py:101](</Users/grigoryfeil/Desktop/DWH Frontend V3/web/dateien.py:101>).  
   **Szenario:** Neue Gespräche verdrängen nur Prozesse. Verlauf, Archivdaten und Arbeitsverzeichnisse bleiben bis zum Sessionende erhalten. Bei `max_gespraeche=1` blieben in der Simulation nach 100 Gesprächen alle 100 Einträge erhalten. Zusätzlich kopiert jede Runde gemeldete Dateien ohne Größenbudget, auch bei ausgeschaltetem Speichern. Vierzig Versionen einer 50-MB-Datei benötigen rund 2 GB zusätzlich. Bei entsprechend wenig freier Platte treffen Schreibfehler auch andere Tester.  
   **Kleinster Fix:** Die Gesamtmenge der behaltenen Gesprächsdaten und Snapshots begrenzen. Bei ausgeschöpftem Budget neue Last sichtbar ablehnen. Die vorhandenen Größenprüfungen der Beta-Ablage auch beim Snapshot-Kopieren anwenden.

9. **Mittel, fehlgeschlagene Rundensicherungen werden als verfügbare Dateien veröffentlicht. Neu.**  
   Stellen: [web/dateien.py:102](</Users/grigoryfeil/Desktop/DWH Frontend V3/web/dateien.py:102>), [web/app.py:490](</Users/grigoryfeil/Desktop/DWH Frontend V3/web/app.py:490>).  
   **Szenario:** Die Snapshot-Kopie scheitert wegen voller Platte. Der Fehler wird verschluckt, die Antwort enthält trotzdem den neuen Dateilink. Der Nutzer erhält eine fehlende oder unvollständige Datei. **Das lautlose Weiterlaufen bei Kopierfehler ist reproduziert.**  
   **Kleinster Fix:** Kopiererfolg zurückgeben, Dateien erst nach vollständiger Sicherung veröffentlichen und Fehlschläge an der Antwort anzeigen.

10. **Mittel, fehlerhafte Diagrammdaten können weiterhin die Oberfläche verwerfen. Alter Befund 9 unverändert.**  
    Stellen: [Diagramm.tsx:84](</Users/grigoryfeil/Desktop/DWH Frontend V3/oberflaeche/src/Diagramm.tsx:84>), [Diagramm.tsx:136](</Users/grigoryfeil/Desktop/DWH Frontend V3/oberflaeche/src/Diagramm.tsx:136>).  
    **Szenario:** Ein Diagramm enthält `data: [null]` oder ein Objekt als `xAxisLabel`. Beide Renderfehler sind erneut reproduziert. Eine lokale Fehlergrenze fehlt.  
    **Kleinster Fix:** Daten und Beschriftungen validieren, Renderfehler am einzelnen Diagramm abfangen.

11. **Mittel, Archivierungsfehler bleiben unsichtbar und verlieren Wiederholungsinformationen. Alter Befund 11 unverändert.**  
    Stelle: [web/app.py:320](</Users/grigoryfeil/Desktop/DWH Frontend V3/web/app.py:320>).  
    **Szenario:** Bei einem Kopierfehler wird `neue_dateien` bereits aus dem Rundeneintrag entfernt. Fehler erscheinen nur im Journal, die Oberfläche zeigt weiterhin eingeschaltetes Speichern.  
    **Kleinster Fix:** Den gespeicherten Zustand erst nach erfolgreicher Ablage fortschreiben und den Fehler sichtbar zurückgeben.

12. **Mittel, „Speichern aus“ kann weiterhin angezeigt werden, obwohl gespeichert wird. Alter Befund 12 unverändert.**  
    Stelle: [App.tsx:129](</Users/grigoryfeil/Desktop/DWH Frontend V3/oberflaeche/src/App.tsx:129>).  
    **Szenario:** Der Nutzer schaltet während einer Runde Speichern aus. Die Anfrage scheitert am Netz, der Schalter bleibt trotzdem aus. Das Backend archiviert weiterhin.  
    **Kleinster Fix:** Erst nach Bestätigung umschalten oder bei Fehler zurücksetzen und informieren.

Der Abgleich mit dem Bericht vom 08.11. ergibt:

| Alter Befund | Stand in 0.6.2 |
|---|---|
| 1. Gemeinsames `/tmp` | Konfiguration korrigiert. `/tmp` gesperrt, eigenes `TMPDIR`. Tatsächliche Sandbox-Durchsetzung hier nicht überprüft. |
| 2. Prüferkorrektur fehlt im Hauptgespräch | Normalfall behoben, Abbruchlücke siehe oben. |
| 3. Alte Dateilinks zeigen neue Inhalte | Gewöhnliches Überschreiben behoben, Unveränderlichkeit nicht hergestellt. |
| 4. Kontextverlust nach Leerlauf | Normales Ruhen behoben, tatsächlicher Gesprächsverlust weiterhin problematisch. |
| 5. Verwaiste Gespräche blockieren Plätze | Für abgeschlossene Runden behoben. Platzschaffen gibt deren Prozesse frei. |
| 6. Polling verdrängt Schreibzugriffe | In der Konfiguration behoben. Vier laufende Gespräche erzeugen etwa 120 Statusabfragen pro Minute, unter den vorgesehenen 300. |
| 7. SQL-Ergebnis vollständig gepuffert | Durch `SSCursor` im Code behoben. Datenbankzeitlimit weiterhin nicht nachgewiesen. |
| 8. Einspielen unter laufender Nutzung | Nur abgeschwächt, nicht zuverlässig behoben. |
| 9. Diagrammfehler | Offen. |
| 10. FIFO beim Lesen | Für Quelldateien behoben. Neue Kopierziele können erneut blockieren. |
| 11. Unsichtbare Ablagefehler | Offen. |
| 12. Falscher Speicherstatus | Offen. |

**Meinen früheren Vorschlag, für die Platzfreigabe zwingend Gesprächskennungen über Neuladen zu erhalten, würde ich einschränken:** Das neue Platzschaffen löst die damalige Kapazitätsblockade bereits. Im regulären Ablauf wählen `raeumen` und `platz_schaffen` unter der Sperre keine laufende Runde aus. Der nachgewiesene Wettlauf entsteht im Fehlerabschluss.

Für das Härtungsziel entbehrlich sind die Verlängerung des Session-Leerlaufs auf vier Stunden und der zusätzliche CLI-Prüfmodus. Letzterer ist nützlich, aber keine Voraussetzung für die Beta und bei Dateien nicht gleichwertig zur Webprüfung, weil [harness/lauf.py:74](</Users/grigoryfeil/Desktop/DWH Frontend V3/harness/lauf.py:74>) keine Prüferkopien bereitstellt. Das Entfernen des wirkungslosen Fast-Schalters ist sinnvoll, behebt aber keinen der Blocker.

**Offene Unsicherheiten:** Die vollständigen Backendtests konnte ich wegen fehlendem Starlette nicht starten. Die gezielten Simulationen ersetzen keinen Test mit echten Codex-Prozessen. Ungeprüft bleiben Sandbox-Durchsetzung, Prozessnachkommen beim Beenden, Datenbankzeitlimits und verfügbare Betriebsressourcen.

Der Verlaufsvorspann übernimmt sämtliche bisherigen Antworten ohne Größenbegrenzung. Bereits 40 Antworten mit je 10.000 Zeichen ergeben in der Simulation eine neue Eingabe mit rund 401.000 Zeichen. Ob die eingesetzte Codex-Version das zuverlässig verarbeitet oder ablehnt, ist offen. Ebenso ist ein Sprachwechsel durch den deutschen Vorspann nicht nachgewiesen. Die Anweisung verlangt weiterhin die Sprache der Nutzerfrage. Daraus mache ich ohne Modellprobe keinen zusätzlichen Befund.