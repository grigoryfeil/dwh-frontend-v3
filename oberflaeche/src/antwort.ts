// Antworttext des Modells (Markdown) in die Teile des Entwurfs zerlegen: Lead, Kennzahlen, übriger Text,
// Nichtantwort und Rückfrage. Die Form verlangt die Anweisung in dwh_v2/web.py, fehlt sie, bleibt es Markdown.
//
// Sicherheit (Befund 4.4): kein rohes HTML, Linkziele nur https:, mailto:, # und Dateien des eigenen Gesprächs,
// Bilder nur aus dem eigenen Gespräch. Alles andere wird Text.
import markdownit from "markdown-it";
import type { Token } from "markdown-it";

export type Kennzahl = { wert: string; einheit: string; label: string };
// Host-Verträge aus dwh_v2/anweisungen/analyst.md, wie host_teile in dwh_v2/antwort.py
export type Reihe = { dataKey: string; label?: string; valuePrefix?: string; valueSuffix?: string };
export type Diagramm = {
  chartType: string;
  meta?: { title?: string; description?: string; footer?: string };
  xKey?: string;
  xAxisLabel?: string;
  nameKey?: string;
  valueKey?: string;
  layout?: string;
  series?: Reihe[];
  data?: Record<string, unknown>[];
};
export type Definition = { label?: string; definition?: string; stage?: string };
export type Beleg = {
  title: string;
  metricDefinitions: Definition[];
  tables: string[];
  filters: string[];
  reportingPeriod?: string;
  assumptions: string[];
  caveats: string[];
};
export type Lesart = { label: string; prompt: string };
export type Nachweis = { titel: string; html: string };
export type Antwort =
  | { art: "antwort"; lead: string; kennzahlen: Kennzahl[]; rest: string; tabellen: number; bilder: string[];
      diagramme: Diagramm[]; quellen: Beleg[]; annahmen: string[]; lesarten: Lesart[]; unvollstaendig: boolean;
      nachweis: Nachweis | null }
  | { art: "keine"; titel: string; rest: string; lesarten: Lesart[] }
  | { art: "rueckfrage"; titel: string; rest: string; optionen: string[] }
  | { art: "kurzklaerung"; titel: string; rest: string; optionen: string[] };

const MARKE = /^\s*\[(keine antwort|no answer|rückfrage|rueckfrage|clarification|kurzklärung|kurzklaerung|before building)\]\s*(.*)$/i;
const HOST_ZEILE = /^[ \t>`]*(genui|visualize)\s*(?=\{)/gm;
const BEKANNT = ["charts_widget_v2", "sources", "alternative_reading", "assumptions"];
const objekt = (w: unknown): w is Record<string, unknown> => !!w && typeof w === "object" && !Array.isArray(w);
const LEERER_CODEBLOCK = /^[ \t]*```[\w-]*[ \t]*\n(?:[ \t]*\n)*[ \t]*```[ \t]*$/gm;

function jsonEnde(text: string, start: number): number | null {
  let tiefe = 0;
  let inText = false;
  let maskiert = false;
  for (let i = start; i < text.length; i++) {
    const z = text[i];
    if (inText) {
      if (maskiert) maskiert = false;
      else if (z === "\\") maskiert = true;
      else if (z === '"') inText = false;
    } else if (z === '"') inText = true;
    else if (z === "{") tiefe++;
    else if (z === "}" && --tiefe === 0) return i + 1;
  }
  return null;
}

export type HostTeil = { name: string; inhalt: unknown };

// Text ohne Host-Zeilen und die Teile darin. Kaputtes JSON fällt aus dem Text, ab der Startzeile bis zu ihrem Ende, und
// kommt wie visualize und unbekannte Namen als Teil "ungueltig", damit die Seite sagt, dass etwas fehlt.
export function hostTeile(text: string): { text: string; teile: HostTeil[] } {
  const teile: HostTeil[] = [];
  const aus: string[] = [];
  let pos = 0;
  HOST_ZEILE.lastIndex = 0;
  for (let t = HOST_ZEILE.exec(text); t; t = HOST_ZEILE.exec(text)) {
    aus.push(text.slice(pos, t.index));
    const klammer = t.index + t[0].length;
    let ende = jsonEnde(text, klammer);
    let wert: unknown = null;
    try {
      wert = ende ? JSON.parse(text.slice(klammer, ende)) : null;
    } catch {
      wert = null;
    }
    if (wert === null || ende === null) {
      const nl = text.indexOf("\n", klammer);
      ende = nl < 0 ? text.length : nl;
    }
    if (t[1] === "genui" && objekt(wert) && Object.keys(wert).length === 1) {
      const [name, roh] = Object.entries(wert)[0];
      const inhalt = objekt(roh) && "content" in roh ? roh.content : roh;
      teile.push({ name: BEKANNT.includes(name) ? name : "ungueltig", inhalt });
    } else teile.push({ name: "ungueltig", inhalt: null });
    const zeilenende = text.indexOf("\n", ende);
    const rest = text.slice(ende, zeilenende < 0 ? text.length : zeilenende);
    pos = rest.replace(/[ \t`]/g, "") ? ende : zeilenende < 0 ? text.length : zeilenende;
    HOST_ZEILE.lastIndex = pos;
  }
  aus.push(text.slice(pos));
  return { text: aus.join("").replace(LEERER_CODEBLOCK, ""), teile };
}

const texte = (w: unknown): string[] =>
  Array.isArray(w) ? w.filter((x) => ["string", "number"].includes(typeof x)).map(String) : [];

// Quellenbelege flach je Befund, die verschachtelte Form des Plugins (queries[].source) zusammengeführt
export function quellen(teile: HostTeil[]): Beleg[] {
  const out: Beleg[] = [];
  for (const teil of teile) {
    if (teil.name !== "sources" || !objekt(teil.inhalt) || !Array.isArray(teil.inhalt.items)) continue;
    for (const item of teil.inhalt.items) {
      if (!objekt(item)) continue;
      const schichten: Record<string, unknown>[] = [item];
      for (const q of Array.isArray(item.queries) ? item.queries : []) {
        if (objekt(q)) schichten.push(q);
        if (objekt(q) && objekt(q.source)) schichten.push(q.source);
      }
      const alle = (feld: string) => [...new Set(schichten.flatMap((s) => texte(s[feld])))];
      const definitionen: Definition[] = [];
      for (const s of schichten) {
        for (const d of Array.isArray(s.metricDefinitions) ? s.metricDefinitions : []) {
          if (!objekt(d)) continue;
          // Nur Texte: Ein Objekt an dieser Stelle ließe React die ganze Antwort verwerfen
          const def: Definition = {};
          for (const feld of ["label", "definition", "stage"] as const) if (["string", "number"].includes(typeof d[feld])) def[feld] = String(d[feld]);
          if (!definitionen.some((x) => JSON.stringify(x) === JSON.stringify(def))) definitionen.push(def);
        }
      }
      const zeitraum = schichten.find((s) => s.reportingPeriod)?.reportingPeriod;
      out.push({
        title: String(item.title ?? ""),
        metricDefinitions: definitionen,
        tables: alle("tables"),
        filters: alle("filters"),
        ...(zeitraum ? { reportingPeriod: String(zeitraum) } : {}),
        assumptions: alle("assumptions"),
        caveats: alle("caveats"),
      });
    }
  }
  return out;
}
const ZAHL = /^\s*(\d|[+\-−–]\s?\d)/;
const ZELLE_ZAHL = /^[+\-−–]?\s?[\d.,'\s]*\d[\d.,'\s]*\s?(%|‰|pp|pp\.|pkt\.?|€|eur|mio\.?|tsd\.?|k)?$/i;

export function linkErlaubt(url: string, gespraech: string | null): boolean {
  if (/^(https:|mailto:|#)/i.test(url)) return true;
  return gespraech !== null && eigeneDatei(url, gespraech);
}

function eigeneDatei(url: string, gespraech: string): boolean {
  const praefix = `/api/gespraeche/${gespraech}/dateien/`;
  return url.startsWith(praefix) && url.length > praefix.length && !url.includes("..");
}

function parser(gespraech: string | null, bilder: string[]) {
  const md = markdownit({ html: false, linkify: false, typographer: false });
  md.validateLink = (url) => linkErlaubt(url, gespraech);
  const r = md.renderer.rules;
  r.link_open = (tokens, i, opts, _env, self) => {
    const t = tokens[i];
    if (!linkErlaubt(String(t.attrGet("href") ?? ""), gespraech)) {
      t.meta = { gesperrt: true };
      return "<span>";
    }
    t.attrSet("target", "_blank");
    t.attrSet("rel", "noopener noreferrer");
    return self.renderToken(tokens, i, opts);
  };
  r.link_close = (tokens, i, opts, _env, self) => {
    // das zugehörige link_open steht weiter vorn auf derselben Ebene
    for (let j = i - 1; j >= 0; j--) {
      if (tokens[j].type === "link_open" && tokens[j].level === tokens[i].level) {
        return tokens[j].meta?.gesperrt ? "</span>" : self.renderToken(tokens, i, opts);
      }
    }
    return self.renderToken(tokens, i, opts);
  };
  const bild = r.image!;
  r.image = (tokens, i, opts, env, self) => {
    const src = String(tokens[i].attrGet("src") ?? "");
    if (gespraech === null || !eigeneDatei(src, gespraech)) return md.utils.escapeHtml(tokens[i].content);
    bilder.push(src);
    return bild(tokens, i, opts, env, self);
  };
  r.table_open = () => '<div class="tabelle"><table>';
  r.table_close = () => "</table></div>";
  md.core.ruler.push("zahlenspalten", (state) => zahlenspalten(state.tokens));
  return md;
}

// Spalten, deren Zellen alle Zahlen sind, rechtsbündig wie im Entwurf
function zahlenspalten(tokens: Token[]) {
  for (let i = 0; i < tokens.length; i++) {
    if (tokens[i].type !== "table_open") continue;
    const zeilen: Token[][] = [];
    let zeile: Token[] = [];
    let j = i + 1;
    for (; j < tokens.length && tokens[j].type !== "table_close"; j++) {
      const t = tokens[j];
      if (t.type === "tr_open") zeile = [];
      if (t.type === "th_open" || t.type === "td_open") zeile.push(t);
      if (t.type === "tr_close") zeilen.push(zeile);
    }
    const inhalt = (zelle: Token) => tokens[tokens.indexOf(zelle) + 1]?.content?.trim() ?? "";
    const spalten = Math.max(0, ...zeilen.map((z) => z.length));
    for (let s = 1; s < spalten; s++) {
      const werte = zeilen.slice(1).map((z) => (z[s] ? inhalt(z[s]) : ""));
      if (werte.length && werte.every((w) => w === "" || w === "–" || ZELLE_ZAHL.test(w)) && werte.some((w) => w)) {
        for (const z of zeilen) z[s]?.attrJoin("class", "zahl");
      }
    }
    i = j;
  }
}

// Blöcke der obersten Ebene: von einem öffnenden Token bis zu seinem schließenden, oder ein Einzeltoken
function bloecke(tokens: Token[]): Token[][] {
  const out: Token[][] = [];
  let i = 0;
  while (i < tokens.length) {
    const t = tokens[i];
    if (t.nesting !== 1) {
      out.push([t]);
      i++;
      continue;
    }
    let tiefe = 0;
    let j = i;
    for (; j < tokens.length; j++) {
      tiefe += tokens[j].nesting;
      if (tiefe === 0) break;
    }
    out.push(tokens.slice(i, j + 1));
    i = j + 1;
  }
  return out;
}

function eintraege(block: Token[]): string[] {
  // Rohtext je Listenpunkt, nur der erste Absatz
  const texte: string[] = [];
  let tiefe = 0;
  let neu = false;
  for (const t of block) {
    if (t.type === "list_item_open") {
      tiefe++;
      neu = tiefe === 1;
    } else if (t.type === "list_item_close") tiefe--;
    else if (t.type === "inline" && neu) {
      texte.push(t.content);
      neu = false;
    }
  }
  return texte;
}

function kennzahlen(block: Token[] | undefined, md: ReturnType<typeof markdownit>): Kennzahl[] | null {
  if (!block || block[0].type !== "bullet_list_open") return null;
  const texte = eintraege(block);
  if (!texte.length || texte.length > 6) return null;
  const out: Kennzahl[] = [];
  for (const text of texte) {
    const t = /^\*\*([^*]{1,40})\*\*\s*[:–—-]?\s*(.+)$/s.exec(text.trim());
    if (!t || !ZAHL.test(t[1])) return null;
    const w = /^([+\-−–]?\s?\d[\d.,'\s]*\d|[+\-−–]?\s?\d)\s*(.*)$/.exec(t[1].trim());
    out.push({
      wert: (w ? w[1] : t[1]).replace(/\s+/g, " ").replace(/^-/, "−"),
      einheit: w ? w[2] : "",
      label: md.renderInline(t[2].trim()),
    });
  }
  return out;
}

function istListe(block: Token[]) {
  return block[0].type === "bullet_list_open" || block[0].type === "ordered_list_open";
}

const NACHWEIS = /^(nachweis|evidence|sources?|quellen)\s*:?$/i;

// Abschnitt „Nachweis“ am Ende der Antwort (harness/anweisung.md): ab seiner Überschrift oder ab dem Absatz, der mit
// dem fetten Wort beginnt, bis zum Schluss. Die Seite setzt ihn als eigenen Block ab. Stichworte vor dem Doppelpunkt
// eines Listenpunkts („Daten:“, „Zeitraum:“) werden hervorgehoben.
function nachweisAus(bl: Token[][], ab: number, md: ReturnType<typeof markdownit>, env: Record<string, unknown>): { ab: number; nachweis: Nachweis } | null {
  for (let i = bl.length - 1; i >= ab; i--) {
    const [auf, inhalt] = bl[i];
    let titel = "";
    let anfang: Token[] = [];
    if (auf.type === "heading_open" && NACHWEIS.test((inhalt?.content ?? "").replace(/[*_]/g, "").trim())) {
      titel = inhalt.content.replace(/[*_:]/g, "").trim();
    } else if (auf.type === "paragraph_open") {
      const k = (inhalt?.children ?? []).filter((t) => t.type !== "text" || t.content !== ""); // markdown-it setzt leere Texte davor
      if (k[0]?.type !== "strong_open" || k[1]?.type !== "text" || k[2]?.type !== "strong_close" || !NACHWEIS.test(k[1].content.trim())) continue;
      titel = k[1].content.replace(":", "").trim();
      // Text im selben Absatz („**Nachweis:** Daten …“) bleibt als erster Absatz des Blocks
      const rest = k.slice(3);
      while (rest[0]?.type === "softbreak" || rest[0]?.type === "hardbreak") rest.shift();
      if (rest[0]?.type === "text") rest[0].content = rest[0].content.replace(/^\s*:?\s*/, "");
      if (rest.some((t) => t.type !== "text" || t.content.trim())) {
        inhalt.children = rest;
        anfang = bl[i];
      }
    } else continue;
    const html = md.renderer.render([...anfang, ...bl.slice(i + 1).flat()], md.options, env)
      .replace(/<li>(\s*<p>)?([^<:]{2,30}:)(?=\s)/g, (_t, p: string | undefined, wort: string) => `<li>${p ?? ""}<b>${wort}</b>`);
    return { ab: i, nachweis: { titel, html } };
  }
  return null;
}

// Höchstens zwei Knöpfe für andere Lesarten (6.7, Runde 6), gleiche Beschriftung nur einmal
function lesartenAus(teile: HostTeil[]): Lesart[] {
  const lesarten = new Map<string, Lesart>();
  for (const t of teile) {
    const l = t.inhalt as Lesart;
    if (t.name !== "alternative_reading" || !objekt(t.inhalt) || !l.label || !l.prompt) continue;
    const label = String(l.label);
    if (!lesarten.has(label)) lesarten.set(label, { label, prompt: String(l.prompt) });
  }
  return [...lesarten.values()].slice(0, 2);
}

export function zerlege(text: string, gespraech: string | null): Antwort {
  const bilder: string[] = [];
  const md = parser(gespraech, bilder);
  const host = hostTeile(text.replace(/\r\n/g, "\n"));
  text = host.text;
  const zeilen = text.split("\n");
  const erste = zeilen.findIndex((z) => z.trim() !== "");
  const marke = erste >= 0 ? MARKE.exec(zeilen[erste]) : null;

  if (marke) {
    let rest = zeilen.slice(erste + 1);
    let titel = marke[2].trim();
    if (!titel) {
      const k = rest.findIndex((z) => z.trim() !== "");
      titel = k >= 0 ? rest[k] : "";
      rest = rest.slice(k + 1);
    }
    titel = md.renderInline(titel.replace(/^#+\s*/, "").replace(/^\*\*(.*)\*\*$/, "$1").trim());
    const env = {};
    const tokens = md.parse(rest.join("\n"), env);
    if (/^(keine antwort|no answer)$/i.test(marke[1])) {
      // seit 6.7 mit Knopf für eine eng verwandte Auswertung, die die Daten tragen
      return { art: "keine", titel, rest: md.renderer.render(tokens, md.options, env), lesarten: lesartenAus(host.teile) };
    }
    const bl = bloecke(tokens);
    const letzte = bl.length - 1;
    const optionen = letzte >= 0 && istListe(bl[letzte]) ? eintraege(bl[letzte]).map((o) => o.trim()) : [];
    const ohne = optionen.length ? bl.slice(0, letzte).flat() : tokens;
    const art: "rueckfrage" | "kurzklaerung" = /^(rückfrage|rueckfrage|clarification)$/i.test(marke[1]) ? "rueckfrage" : "kurzklaerung";
    return { art, titel, rest: md.renderer.render(ohne, md.options, env), optionen };
  }

  const env = {};
  const tokens = md.parse(text, env);
  const bl = bloecke(tokens);
  let lead = "";
  let ab = 0;
  if (bl[0]?.[0].type === "paragraph_open") {
    lead = md.renderer.renderInline(bl[0][1].children ?? [], md.options, env);
    ab = 1;
  }
  const kz = ab === 1 ? kennzahlen(bl[1], md) : null;
  if (kz) ab = 2;
  const beleg = nachweisAus(bl, ab, md, env);
  const rest = md.renderer.render(bl.slice(ab, beleg?.ab).flat(), md.options, env);
  const tabellen = tokens.filter((t) => t.type === "table_open").length;
  const diagramme = host.teile.filter((t) => t.name === "charts_widget_v2" && objekt(t.inhalt)).map((t) => t.inhalt as Diagramm);
  const lesarten = lesartenAus(host.teile);
  // Annahmen der Abfrage, seit 0.5.2 eine eigene Zeile des Modells, die die Seite an den Beleg der Anwendung hängt
  const annahmen = [...new Set(host.teile.filter((t) => t.name === "assumptions").flatMap((t) => texte(t.inhalt)))];
  return { art: "antwort", lead, kennzahlen: kz ?? [], rest, tabellen, bilder, diagramme, quellen: quellen(host.teile), annahmen, lesarten,
    unvollstaendig: host.teile.some((t) => t.name === "ungueltig"), nachweis: beleg?.nachweis ?? null };
}

// Prüfhinweis: ein bis zwei Sätze, Links wie in der Antwort
export function inline(text: string, gespraech: string | null): string {
  return parser(gespraech, []).renderInline(text);
}

// Sprache für Silbentrennung und lang-Attribut, Deutsch oder Englisch
export function sprache(text: string): "de" | "en" {
  const de = (text.match(/[äöüß]|\b(der|die|das|und|nicht|wie|welche|ist|sind|im|mit|für|seit|von|zu|den|dem)\b/gi) ?? []).length;
  const en = (text.match(/\b(the|and|which|what|how|is|are|of|for|since|with|to|in)\b/gi) ?? []).length;
  return de > en ? "de" : "en";
}
