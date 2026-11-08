**Den geprüften Stand 0.5.1 würde ich für die gemeinsame Beta noch nicht freigeben, weil Gesprächsinhalte über temporäre Dateien zugänglich werden können und mehrere Fortsetzungswege unbemerkt mit einem falschen Kontext arbeiten.**

Geprüft wurde der lokale Commit `eac0a45`. Ich habe nichts geändert, keine Betriebsserver kontaktiert und die ausgeschlossenen Verzeichnisse nicht gelesen. Die unten genannten Simulationen liefen im Speicher mit Ersatz für Modell, HTTP und Dateischreibzugriffe.

1. **Kritisch, gemeinsam zugängliches `/tmp` unterläuft die Gesprächstrennung.**  
   Stellen: [codex-config.toml:105](</Users/grigoryfeil/Desktop/DWH Frontend V3/betrieb/codex-config.toml:105>), [Web-Unit:40](</Users/grigoryfeil/Desktop/DWH Frontend V3/betrieb/dwh-frontend-v3-web.service:40>), [sitzung.py:70](</Users/grigoryfeil/Desktop/DWH Frontend V3/harness/sitzung.py:70>).  
   **Szenario:** Ein Analyst legt Abfrageergebnisse oder nutzerspezifische Angaben in `/tmp/daten.json` ab. Ein anderes Gespräch kann diese Datei lesen oder überschreiben, auch nach einer Prompt-Injektion. Alle Modellprozesse laufen als `dwhv3` innerhalb derselben Web-Unit. `PrivateTmp` isoliert deren temporären Bereich gegenüber anderen Diensten, nicht die Gespräche untereinander. Die Codex-Freigabe erlaubt dort Lesen und Schreiben. [systemd-Dokumentation](https://raw.githubusercontent.com/systemd/systemd/main/man/systemd.exec.xml), [OpenAI-Berechtigungsdokumentation](https://learn.chatgpt.com/docs/permissions).  
   **Kleinster Fix:** Einen tatsächlich getrennten temporären Bereich je Gespräch bereitstellen. Nur unterschiedliche Dateinamen oder `TMPDIR` bei weiterhin lesbarem gemeinsamen `/tmp` reichen nicht.

2. **Kritisch, Prüferkorrekturen erreichen den ursprünglichen Analysten nicht.**  
   Stellen: [app.py:355](</Users/grigoryfeil/Desktop/DWH Frontend V3/web/app.py:355>), [app.py:392](</Users/grigoryfeil/Desktop/DWH Frontend V3/web/app.py:392>), [app.py:420](</Users/grigoryfeil/Desktop/DWH Frontend V3/web/app.py:420>).  
   **Szenario:** Der Analyst antwortet „100“, der Prüfer korrigiert auf „80“. Der Nutzer sieht „80“ und fragt „Wie viel ist die Hälfte davon?“. Der weiterverwendete Analyst kennt weiterhin seine „100“. Die Simulation bestätigt, dass ihm ausschließlich die neue Frage übergeben wird, keine Korrektur.  
   **Kleinster Fix:** Die korrigierte Antwort vor der nächsten Frage ausdrücklich in den Analystenkontext übernehmen. Bis dahin die optionale Prüfrunde abschalten.

3. **Kritisch, alte Antworten können nachträglich andere Diagrammwerte zeigen.**  
   Stellen: [dateien.py:92](</Users/grigoryfeil/Desktop/DWH Frontend V3/web/dateien.py:92>), [app.py:566](</Users/grigoryfeil/Desktop/DWH Frontend V3/web/app.py:566>).  
   **Szenario:** Runde eins erzeugt `dashboard.html` für Oktober. Auf „Jetzt September“ überschreibt das Modell dieselbe Datei. Beide Antworten verweisen auf dieselbe URL. Beim erneuten Öffnen zeigt die Oktober-Antwort das September-Dashboard, ohne Hinweis. Die identischen URLs sind lokal nachvollzogen.  
   **Kleinster Fix:** Gemeldete Dateien beim Abschluss jeder Runde unveränderlich sichern und über eine rundenspezifische URL ausliefern.

4. **Kritisch, nach Leerlauf werden Folgefragen still ohne Vorgeschichte beantwortet.**  
   Stellen: [App.tsx:228](</Users/grigoryfeil/Desktop/DWH Frontend V3/oberflaeche/src/App.tsx:228>), [app.py:263](</Users/grigoryfeil/Desktop/DWH Frontend V3/web/app.py:263>).  
   **Szenario:** Nach mehr als 30 Minuten fragt der Nutzer „Und davon nur Deutschland?“. Das Backend hat das Gespräch entfernt. Die Oberfläche fängt 404 beziehungsweise 410 ab und sendet dieselbe Frage automatisch als neues Gespräch. Der sichtbare Verlauf bleibt bestehen, dem Modell fehlt er vollständig. Diesen Ablauf habe ich mit der ursprünglichen Frontend-Funktion reproduziert.  
   **Kleinster Fix:** Den Kontextverlust anzeigen und die Frage nicht automatisch isoliert neu senden. Alternativ den relevanten Verlauf ausdrücklich übertragen.

5. **Hoch, Neuladen kann sämtliche Gesprächsplätze blockieren.**  
   Stellen: [App.tsx:36](</Users/grigoryfeil/Desktop/DWH Frontend V3/oberflaeche/src/App.tsx:36>), [app.py:506](</Users/grigoryfeil/Desktop/DWH Frontend V3/web/app.py:506>).  
   **Szenario:** Nutzer laden die Seite neu oder schließen Tabs. Die Gesprächskennung geht im Browser verloren, die Modellprozesse bleiben bis zum Leerlaufende bestehen. Nach insgesamt vier solchen Gesprächen erhalten auch andere Tester 503, obwohl gerade niemand arbeitet. Die Backend-Simulation bestätigt das.  
   **Kleinster Fix:** Gesprächskennungen über Neuladen erhalten und wieder zuordnen. Zusätzlich verwaiste, ruhende Gespräche bei Kapazitätsmangel gezielt freigeben.

6. **Hoch, drei Nutzer hinter derselben Firmenadresse überschreiten die nginx-Drossel durch normales Polling.**  
   Stellen: [nginx-dwhv3:4](</Users/grigoryfeil/Desktop/DWH Frontend V3/betrieb/nginx-dwhv3:4>), [nginx-dwhv3:21](</Users/grigoryfeil/Desktop/DWH Frontend V3/betrieb/nginx-dwhv3:21>), [App.tsx:12](</Users/grigoryfeil/Desktop/DWH Frontend V3/oberflaeche/src/App.tsx:12>).  
   **Szenario:** Drei Tester hinter derselben öffentlichen IP erzeugen mit laufenden Gesprächen ungefähr 90 Statusabfragen pro Minute. Erlaubt sind 60 für sämtliche Routen zusammen. Nach Verbrauch des Bursts entstehen 429, auch für neue Fragen oder Abbrüche. Beim fehlgeschlagenen Abbruch bleibt dessen Knopf zudem deaktiviert.  
   **Kleinster Fix:** Statusabfragen separat drosseln und die Grenze an der vorgesehenen Parallelität ausrichten. Schreibende Aktionen dürfen nicht vom Polling verdrängt werden.

7. **Hoch, die SQL-Zeilengrenze begrenzt den Speicherverbrauch nicht.**  
   Stelle: [sql_werkzeug.py:39](</Users/grigoryfeil/Desktop/DWH Frontend V3/harness/sql_werkzeug.py:39>).  
   **Szenario:** Das Modell fragt viele Detailzeilen ab oder erzeugt versehentlich einen stark vervielfachenden Join. Der normale PyMySQL-Cursor puffert das vollständige Ergebnis bereits bei `execute`. Das anschließende `fetchmany(1001)` kommt für den Speicherschutz zu spät. Ein großes Ergebnis kann den Datenwerkzeugprozess oder weitere Prozesse unter dem gemeinsamen Speicherlimit treffen. Dieses Pufferverhalten ist im lokal installierten Treibercode bestätigt.  
   **Kleinster Fix:** Ungepuffert lesen, nach der Ergebnisgrenze die Verbindung kontrolliert beenden und eine wirksame Datenbank-Laufzeitgrenze setzen.

8. **Hoch, Einspielen beendet laufende Gespräche ohne kontrollierten Übergang.**  
   Stellen: [einrichtung.sh:58](</Users/grigoryfeil/Desktop/DWH Frontend V3/betrieb/einrichtung.sh:58>), [web-einrichtung.sh:55](</Users/grigoryfeil/Desktop/DWH Frontend V3/betrieb/web-einrichtung.sh:55>), [app.py:194](</Users/grigoryfeil/Desktop/DWH Frontend V3/web/app.py:194>).  
   **Szenario:** Während eines Dashboards wird eine Beta-Korrektur eingespielt. Zunächst werden die Dateien unter laufenden Prozessen ausgetauscht, anschließend wird die Unit neu gestartet. Sessions und Gespräche verschwinden. Die laufende Runde wurde noch nicht archiviert, ihr Arbeitsverzeichnis wird beim Start gelöscht.  
   **Kleinster Fix:** Für die Beta genügt ein kontrolliertes Wartungsfenster. Neue Fragen sperren, laufende Runden auslaufen lassen oder ihren Abbruch sichern, danach Anwendung austauschen und neu starten.

9. **Mittel, fehlerhafte Diagrammdaten können die gesamte Oberfläche verwerfen.**  
   Stellen: [Diagramm.tsx:44](</Users/grigoryfeil/Desktop/DWH Frontend V3/oberflaeche/src/Diagramm.tsx:44>), [Diagramm.tsx:84](</Users/grigoryfeil/Desktop/DWH Frontend V3/oberflaeche/src/Diagramm.tsx:84>), [Diagramm.tsx:136](</Users/grigoryfeil/Desktop/DWH Frontend V3/oberflaeche/src/Diagramm.tsx:136>).  
   **Szenario:** Das Modell liefert ein Diagramm mit `data: [null]` oder einem Objekt als `xAxisLabel`. Beide Fälle werfen im ursprünglichen Renderer eine Ausnahme, lokal reproduziert. Eine Fehlergrenze um das Diagramm fehlt. Der Nutzer verliert dadurch auch den lesbaren Antworttext.  
   **Kleinster Fix:** Datenzeilen und Beschriftungen vor dem Rendern validieren und Diagrammfehler lokal abfangen.

10. **Mittel, eine benannte Pipe kann eine Runde dauerhaft hängen lassen.**  
    Stellen: [dateien.py:66](</Users/grigoryfeil/Desktop/DWH Frontend V3/web/dateien.py:66>), [app.py:416](</Users/grigoryfeil/Desktop/DWH Frontend V3/web/app.py:416>).  
    **Szenario:** Im Arbeitsverzeichnis liegt eine FIFO namens `bericht.csv`, die das Modell verlinkt. `os.open` wartet auf einen Schreibpartner, bevor `fstat` den Dateityp prüfen kann. Dieser Schritt erfolgt nach der Modellrunde und außerhalb ihres Zeitlimits. Der Gesprächsstatus bleibt laufend, auch das Beenden des Modellprozesses löst diesen Dateizugriff nicht.  
    **Kleinster Fix:** Mit `O_NONBLOCK` öffnen und anschließend reguläre Dateien prüfen. Die Nachverarbeitung muss außerdem einen zuverlässig abschließenden Fehlerpfad bekommen.

11. **Mittel, fehlgeschlagene Ablage bleibt für den Nutzer unsichtbar.**  
    Stellen: [app.py:286](</Users/grigoryfeil/Desktop/DWH Frontend V3/web/app.py:286>), [app.py:301](</Users/grigoryfeil/Desktop/DWH Frontend V3/web/app.py:301>), [app.py:594](</Users/grigoryfeil/Desktop/DWH Frontend V3/web/app.py:594>).  
    **Szenario:** Die Platte ist voll. Die Oberfläche meldet weiterhin eingeschaltetes Speichern, der Fehler landet ausschließlich im Journal. Die Kopierliste wird schon vor erfolgreicher Ablage entfernt. Bei einem Kopierfehler fehlen dadurch auch einem Wiederholungsversuch die Dateinamen. Das Verschlucken des Fehlers und die vorzeitige Zustandsänderung sind simuliert bestätigt.  
    **Kleinster Fix:** Erst nach erfolgreichem Schreiben den gespeicherten Zustand fortschreiben. Fehler an die Oberfläche zurückmelden und Wiederholungsinformationen erhalten.

12. **Mittel, „Speichern aus“ kann angezeigt werden, obwohl weiter gespeichert wird.**  
    Stelle: [App.tsx:131](</Users/grigoryfeil/Desktop/DWH Frontend V3/oberflaeche/src/App.tsx:131>).  
    **Szenario:** Während einer laufenden Antwort schaltet der Nutzer die Ablage aus. Die Anfrage scheitert durch Netzverlust oder die oben beschriebene Drossel. Der Schalter zeigt bereits „aus“, sämtliche Fehler außer Abmeldung werden ignoriert. Der Server archiviert die Runde weiterhin.  
    **Kleinster Fix:** Den Schalter erst nach Bestätigung umstellen oder bei Fehler zurücksetzen und einen Hinweis anzeigen.

Ich widerspreche einer pauschalen Ablehnung des geteilten Kontos: **Die HTTP-Zuordnung verwendet eine eigene Session-Referenz, nicht den Kontonamen.** Zwei simulierte Anmeldungen als `tester` erhielten für dasselbe Gespräch korrekt 200 beziehungsweise 404. Separate Konten würden die gemeinsame temporäre Arbeitsfläche nicht beheben.

Ebenso ist `allow-scripts` im iframe hier für sich genommen kein nachgewiesenes Zugangsleck. `allow-same-origin` fehlt, die Dateiauslieferung setzt zusätzlich eine Sandbox-CSP und die Hauptseite begrenzt Frames auf die eigene Herkunft. Auch die Pfadprüfung mit komponentenweisem `O_NOFOLLOW` ist grundsätzlich sinnvoll. Die iframe- und CSP-Regeln muss man zusammen bewerten, insbesondere die Begrenzung durch `frame-src`. [CSP-Spezifikation](https://www.w3.org/TR/CSP3/#directive-frame-src).

Für die Beta entbehrlich sind das Fertigbauen von PDF-/Excel-Export und Beispielarchiv sowie eine verpflichtende Prüfrunde. Nicht verfügbare Funktionen können ausgeblendet bleiben. Zur Absicherung der genannten Korrekturen genügen gezielte Regressionen dieser konkreten Fehlerfälle.

**Offen bleiben die tatsächliche Durchsetzung der Sandbox auf dem VPS, die effektiven Datenbankrechte und Zeitlimits, der freie Speicherplatz sowie das Verhalten der installierten Codex-Version bei Loginablauf und Prozessabbruch.** Der reguläre Fehlerpfad zeigt Modellfehler und Zeitlimits an, ein erfolgreicher Wiederanlauf ist damit noch nicht belegt. Einen erfolgreichen Prompt-Injektionsangriff über echte DWH-Inhalte habe ich nicht nachgewiesen. Der gemeinsame temporäre Bereich liefert dafür allerdings bereits einen konkreten möglichen Schadensweg.