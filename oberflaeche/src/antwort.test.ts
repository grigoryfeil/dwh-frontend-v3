import { describe, expect, it } from "vitest";
import { hostTeile, inline, linkErlaubt, quellen, sprache, zerlege } from "./antwort";

const G = "abc123";
const DATEI = `/api/gespraeche/${G}/dateien/`;

describe("Antwort zerlegen", () => {
  it("Lead, Kennzahlen und Rest", () => {
    const a = zerlege(
      "Drei von sechs Standorten wuchsen schneller.\n\n- **3 von 6** Standorte schneller\n- **+5,0 %** Median Wachstum\n- **-1,5 Pp** Veränderung\n\nCampus A sticht heraus.\n\n| Campus | 2025 | Anteil |\n|---|---|---|\n| A | 1.000 | 12,0 % |\n| B | 800 | – |\n",
      G,
    );
    expect(a.art).toBe("antwort");
    if (a.art !== "antwort") return;
    expect(a.lead).toBe("Drei von sechs Standorten wuchsen schneller.");
    expect(a.kennzahlen).toEqual([
      { wert: "3", einheit: "von 6", label: "Standorte schneller" },
      { wert: "+5,0", einheit: "%", label: "Median Wachstum" },
      { wert: "−1,5", einheit: "Pp", label: "Veränderung" },
    ]);
    expect(a.rest).toContain("<p>Campus A sticht heraus.</p>");
    expect(a.rest).toContain('<div class="tabelle"><table>');
    expect(a.rest).toContain('<th class="zahl">2025</th>');
    expect(a.rest).toContain('<td class="zahl">12,0 %</td>');
    expect(a.rest).toContain("<td>A</td>");
    expect(a.tabellen).toBe(1);
  });

  it("gewöhnliche Liste nach dem Lead bleibt Liste", () => {
    const a = zerlege("Ergebnis.\n\n- Tabelle studierende\n- Filter Campus", G);
    if (a.art !== "antwort") throw new Error();
    expect(a.kennzahlen).toEqual([]);
    expect(a.rest).toContain("<li>Tabelle studierende</li>");
  });

  it("Nichtantwort mit Titel", () => {
    const a = zerlege("[Keine Antwort]\nDie Daten können das nicht beantworten.\n\nDas DWH enthält keine Arbeitgeber.", G);
    expect(a).toEqual({ art: "keine", titel: "Die Daten können das nicht beantworten.", rest: "<p>Das DWH enthält keine Arbeitgeber.</p>\n", lesarten: [] });
  });

  it("Nichtantwort mit Knopf für eine verwandte Auswertung (6.7)", () => {
    const a = zerlege('[Keine Antwort]\nGründe fehlen.\n\nNur der Zeitpunkt.\n\ngenui{"alternative_reading":{"label":"Abbruchquote","prompt":"Wie hoch ist die Abbruchquote?"}}', G);
    if (a.art !== "keine") throw new Error();
    expect(a.lesarten).toEqual([{ label: "Abbruchquote", prompt: "Wie hoch ist die Abbruchquote?" }]);
    expect(a.rest).not.toContain("genui");
  });

  it("Rückfrage mit Optionen", () => {
    const a = zerlege("[Rückfrage] **Welche Studiengänge zählen als neu?**\n\nEs gibt keine feste Definition.\n\n- Ab 2025 gestartet\n- Ab 2024 gestartet", G);
    expect(a).toEqual({
      art: "rueckfrage",
      titel: "Welche Studiengänge zählen als neu?",
      rest: "<p>Es gibt keine feste Definition.</p>\n",
      optionen: ["Ab 2025 gestartet", "Ab 2024 gestartet"],
    });
  });
});

describe("Sicherheit", () => {
  it("kein rohes HTML", () => {
    const a = zerlege("Text <img src=x onerror=alert(1)> <script>alert(1)</script>", G);
    if (a.art !== "antwort") throw new Error();
    expect(a.lead).not.toContain("<img");
    expect(a.lead).not.toContain("<script");
  });

  it.each([
    "[x](javascript:alert(1))",
    "<javascript:alert(1)>",
    "[x][r]\n\n[r]: javascript:alert(1)",
    "[x](http://fremd.example)",
    "[x](data:text/html,hi)",
    "[x](/api/gespraeche/fremd/dateien/a.html)",
    "[x](//fremd.example/a)",
  ])("Linkziel %s wird Text", (md) => {
    const a = zerlege(md, G);
    if (a.art !== "antwort") throw new Error();
    expect(a.lead + a.rest).not.toMatch(/<a /);
  });

  it("erlaubte Linkziele", () => {
    const a = zerlege(`[a](https://sae.edu) [b](mailto:x@sae.edu) [c](#k) [d](${DATEI}chart.png)`, G);
    if (a.art !== "antwort") throw new Error();
    expect(a.lead.match(/<a /g)?.length).toBe(4);
    expect(a.lead).toContain('target="_blank"');
    expect(a.lead).toContain('rel="noopener noreferrer"');
  });

  it("Bilder nur aus dem eigenen Gespräch", () => {
    const a = zerlege(`![fremd](https://fremd.example/x.png)\n\n![eigen](${DATEI}chart.png)`, G);
    if (a.art !== "antwort") throw new Error();
    expect(a.lead).not.toContain("<img");
    expect(a.rest).toContain(`<img src="${DATEI}chart.png"`);
    expect(a.bilder).toEqual([`${DATEI}chart.png`]);
  });

  it("Prüfhinweis inline mit Linkfilter", () => {
    expect(inline("Siehe [x](javascript:alert(1)) und **fett**", G)).not.toContain("<a ");
    expect(inline("**fett**", G)).toBe("<strong>fett</strong>");
    expect(linkErlaubt(`${DATEI}a/../../b`, G)).toBe(false);
  });
});

describe("Sprache", () => {
  it("erkennt Deutsch und Englisch", () => {
    expect(sprache("Wie hat sich die Abbruchquote seit 2024 entwickelt?")).toBe("de");
    expect(sprache("Which campuses grew enrolments faster than their spend?")).toBe("en");
  });
});

// Dieselben Fälle wie in tests/test_antwort.py, damit Seite und PDF dieselben Host-Zeilen lesen
const DIAGRAMM =
  'genui{"charts_widget_v2":{"content":{"chartType":"bar","meta":{"title":"Neu nach Standort"},"xKey":"s","series":[{"dataKey":"n","label":"Neu"}],"data":[{"s":"HH","n":120},{"s":"B","n":95}]}}}';
const QUELLEN =
  'genui{"sources":{"content":{"schemaVersion":1,"items":[{"id":"neu","title":"Neueinschreibungen","metricDefinitions":[{"label":"Neueinschreibung","definition":"Vertrag ohne Storno.","stage":"vorschlag"}],"tables":["vertraege"],"filters":["Intake: 0926"]}]}}}';
const LESART = 'genui{"alternative_reading":{"label":"Nach Studienjahr","prompt":"Wie viele im Studienjahr 2025/26?"}}';

describe("Host-Verträge", () => {
  it("Host-Zeilen verschwinden aus dem Text und kommen als Teile", () => {
    const { text, teile } = hostTeile(`HH liegt vorn.\n\n${DIAGRAMM}\n\nB folgt.\n${LESART}\n\n${QUELLEN}\n`);
    expect(text.split(/\s+/).filter(Boolean)).toEqual(["HH", "liegt", "vorn.", "B", "folgt."]);
    expect(teile.map((t) => t.name)).toEqual(["charts_widget_v2", "alternative_reading", "sources"]);
  });

  it("über mehrere Zeilen, im Codeblock, kaputt oder als visualize", () => {
    const { text, teile } = hostTeile(
      'Ergebnis.\n\n```\ngenui{"charts_widget_v2": {"content": {\n  "chartType": "line", "data": [{"x": "a}"}]}}}\n```\n\ngenui{"sources": {kaputt\nvisualize{"path":"/x.html"}\nSchluss.',
    );
    expect(text.split(/\s+/).filter(Boolean)).toEqual(["Ergebnis.", "Schluss."]);
    expect(teile).toEqual([
      { name: "charts_widget_v2", inhalt: { chartType: "line", data: [{ x: "a}" }] } },
      { name: "ungueltig", inhalt: null },
      { name: "ungueltig", inhalt: null },
    ]);
    expect(zerlege('Ergebnis.\ngenui{"app_block":{"content":"<p>x</p>"}}', G)).toMatchObject({ unvollstaendig: true });
  });

  it("Antwort mit Diagramm, Quellenbeleg und anderer Lesart", () => {
    const a = zerlege(`Im Kalenderjahr 2026 kamen 215 neu.\n\n- **215** Neueinschreibungen\n\n${DIAGRAMM}\n${LESART}\n${QUELLEN}`, G);
    if (a.art !== "antwort") throw new Error(a.art);
    expect(a.lead).toBe("Im Kalenderjahr 2026 kamen 215 neu.");
    expect(a.rest).toBe("");
    expect(a.diagramme[0].chartType).toBe("bar");
    expect(a.quellen[0]).toMatchObject({ title: "Neueinschreibungen", tables: ["vertraege"], filters: ["Intake: 0926"] });
    expect(a.quellen[0].metricDefinitions[0].stage).toBe("vorschlag");
    expect(a.lesarten).toEqual([{ label: "Nach Studienjahr", prompt: "Wie viele im Studienjahr 2025/26?" }]);
  });

  it("höchstens zwei andere Lesarten, gleiche Beschriftung nur einmal (6.7, Runde 6)", () => {
    const zweite = 'genui{"alternative_reading":{"label":"Nur Kernprodukte","prompt":"Wie viele Kernprodukte 2026?"}}';
    const dritte = 'genui{"alternative_reading":{"label":"Nach Geschäftsjahr","prompt":"Wie viele im Geschäftsjahr?"}}';
    const a = zerlege(`Im Kalenderjahr 2026 kamen 215 neu.\n\n${LESART}\n${LESART}\n${zweite}\n${dritte}`, G);
    if (a.art !== "antwort") throw new Error(a.art);
    expect(a.lesarten.map((l) => l.label)).toEqual(["Nach Studienjahr", "Nur Kernprodukte"]);
  });

  it("Annahmen-Zeile der Antwort (0.5.2) wird gelesen und nicht als fehlender Teil gemeldet", () => {
    const a = zerlege('Im Septemberintake 2026 kamen 215 neu.\n\ngenui{"assumptions":["Septemberintake 2026","nur Kernprodukte"]}', G);
    if (a.art !== "antwort") throw new Error(a.art);
    expect(a.annahmen).toEqual(["Septemberintake 2026", "nur Kernprodukte"]);
    expect(a.unvollstaendig).toBe(false);
    expect(a.rest).toBe("");
  });

  it("verschachtelte Quellen des Plugins", () => {
    const b = quellen([{ name: "sources", inhalt: { items: [{ title: "A", assumptions: ["Annahme."], queries: [{ reportingPeriod: "2026", source: { label: "V", tables: ["t1"], caveats: ["E."], metricDefinitions: [{ label: "X", definition: "Y.", stage: "freigegeben" }] } }] }] } }]);
    expect(b).toEqual([{ title: "A", metricDefinitions: [{ label: "X", definition: "Y.", stage: "freigegeben" }], tables: ["t1"], filters: [], reportingPeriod: "2026", assumptions: ["Annahme."], caveats: ["E."] }]);
  });

  it("Kurzklärung mit Fragen und Vorschlägen", () => {
    const a = zerlege("[Kurzklärung]\nIch baue ein Dashboard zu Leads.\n\n- Zeitraum? Vorschlag: 2026 bis heute\n- Gliederung? Vorschlag: nach Standort", G);
    expect(a).toMatchObject({ art: "kurzklaerung", titel: "Ich baue ein Dashboard zu Leads.", optionen: ["Zeitraum? Vorschlag: 2026 bis heute", "Gliederung? Vorschlag: nach Standort"] });
  });
});

describe("Nachweis am Ende der Antwort", () => {
  const antwort = (text: string) => {
    const a = zerlege(text, G);
    if (a.art !== "antwort") throw new Error();
    return a;
  };

  it("fetter Absatz mit Liste wird ein eigener Block, Stichworte hervorgehoben", () => {
    const a = antwort("Ergebnis.\n\n| A | B |\n|---|---|\n| x | 1 |\n\n**Nachweis**\n\n- Daten: Bestand je Stichtag.\n- Zeitraum: 2026.\n");
    expect(a.nachweis).toEqual({ titel: "Nachweis", html: "<ul>\n<li><b>Daten:</b> Bestand je Stichtag.</li>\n<li><b>Zeitraum:</b> 2026.</li>\n</ul>\n" });
    expect(a.rest).toContain("<table>");
    expect(a.rest).not.toContain("Nachweis");
    expect(a.rest).not.toContain("Bestand je Stichtag");
  });

  it("Überschrift und englisches Wort", () => {
    const a = antwort("Result.\n\nSome text.\n\n## Evidence\n\nBooked revenue, intake September 2026.");
    expect(a.nachweis).toEqual({ titel: "Evidence", html: "<p>Booked revenue, intake September 2026.</p>\n" });
    expect(a.rest).toBe("<p>Some text.</p>\n");
  });

  it("Text im selben Absatz bleibt erhalten", () => {
    const a = antwort("Ergebnis.\n\n**Nachweis:** Daten aus dem CRM, Stichtag 6. November 2026.");
    expect(a.nachweis).toEqual({ titel: "Nachweis", html: "<p>Daten aus dem CRM, Stichtag 6. November 2026.</p>\n" });
    expect(a.rest).toBe("");
  });

  it("ohne Nachweis bleibt alles im Text, auch fette Zwischentitel", () => {
    const a = antwort("Ergebnis.\n\n**Einordnung**\n\nNachweis führen wir später.");
    expect(a.nachweis).toBeNull();
    expect(a.rest).toContain("<strong>Einordnung</strong>");
  });
});
