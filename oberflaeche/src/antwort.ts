// Antworttext des Modells (Markdown) in die Teile des Entwurfs zerlegen: Lead, Kennzahlen, übriger Text, Nachweis,
// Nichtantwort und Rückfrage. Die Form verlangt harness/anweisung.md, fehlt sie, bleibt es Markdown.
//
// Sicherheit (Befund 4.4): kein rohes HTML, Linkziele nur https:, mailto:, # und Dateien des eigenen Gesprächs,
// Bilder nur aus dem eigenen Gespräch. Alles andere wird Text.
import markdownit from "markdown-it";
import type { Token } from "markdown-it";

export type Kennzahl = { wert: string; einheit: string; label: string };
export type Nachweis = { titel: string; html: string };
export type Antwort =
  | { art: "antwort"; lead: string; kennzahlen: Kennzahl[]; rest: string; tabellen: number; bilder: string[];
      unvollstaendig: boolean; nachweis: Nachweis | null }
  | { art: "keine"; titel: string; rest: string }
  | { art: "rueckfrage"; titel: string; rest: string; optionen: string[] }
  | { art: "kurzklaerung"; titel: string; rest: string; optionen: string[] };

const MARKE = /^\s*\[(keine antwort|no answer|rückfrage|rueckfrage|clarification|kurzklärung|kurzklaerung|before building)\]\s*(.*)$/i;
const HOST_ZEILE = /^[ \t>`]*(genui|visualize)\s*(?=\{)/gm;
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

// Schutzfilter: V3 liefert Diagramme und Quellen als Datei oder im Text, das Daten-Plugin kennt aber auch Zeilen für
// den Host (`genui{…}`, `visualize{…}`), die diese Seite nicht darstellt. Solche Zeilen fallen samt ihrem JSON aus dem
// Text, auch über mehrere Zeilen, im Codeblock oder kaputt, und die Seite sagt, dass etwas fehlt (`entfernt`).
export function ohneHostZeilen(text: string): { text: string; entfernt: boolean } {
  const aus: string[] = [];
  let pos = 0;
  let entfernt = false;
  HOST_ZEILE.lastIndex = 0;
  for (let t = HOST_ZEILE.exec(text); t; t = HOST_ZEILE.exec(text)) {
    entfernt = true;
    aus.push(text.slice(pos, t.index));
    const klammer = t.index + t[0].length;
    let ende = jsonEnde(text, klammer);
    try {
      if (ende) JSON.parse(text.slice(klammer, ende));
    } catch {
      ende = null;
    }
    if (ende === null) {
      const nl = text.indexOf("\n", klammer);
      ende = nl < 0 ? text.length : nl;
    }
    const zeilenende = text.indexOf("\n", ende);
    const rest = text.slice(ende, zeilenende < 0 ? text.length : zeilenende);
    pos = rest.replace(/[ \t`]/g, "") ? ende : zeilenende < 0 ? text.length : zeilenende;
    HOST_ZEILE.lastIndex = pos;
  }
  aus.push(text.slice(pos));
  return { text: aus.join("").replace(LEERER_CODEBLOCK, ""), entfernt };
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

export function zerlege(text: string, gespraech: string | null): Antwort {
  const bilder: string[] = [];
  const md = parser(gespraech, bilder);
  const host = ohneHostZeilen(text.replace(/\r\n/g, "\n"));
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
      return { art: "keine", titel, rest: md.renderer.render(tokens, md.options, env) };
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
  return { art: "antwort", lead, kennzahlen: kz ?? [], rest, tabellen, bilder, unvollstaendig: host.entfernt, nachweis: beleg?.nachweis ?? null };
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
