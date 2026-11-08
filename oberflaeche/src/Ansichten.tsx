// Bildschirme und Bausteine nach Richtung A. Zustand und Abläufe liegen in App.tsx.
import { useEffect, useMemo, useRef, useState, type FormEvent, type KeyboardEvent, type MouseEvent, type Ref } from "react";
import logo from "./assets/sae-solo-grey.svg";
import { dashboardTitel, type Datei, type Runde, type Stufe } from "./api";
import { inline, sprache, zerlege, type Beleg, type Lesart } from "./antwort";
import { BEISPIELE } from "./beispiele";
import { DiagrammAnsicht } from "./Diagramm";
import { dauer, laufzeit, nr, uhrzeit } from "./format";

export type Zug = {
  id: number;
  frage: string;
  zeit: Date;
  verify: boolean;
  schnell: boolean;
  gespraech?: string;
  runde?: Runde; // Stand vom Server, während der Arbeit mit Stufen und Schritten
  fertig?: Date;
  fehler?: "verbindung" | "zeit" | "belegt";
  abbrechen?: boolean;
};
export type Overlay = { url: string; titel: string; nr: number; zeit?: Date };

const STUFEN: Record<string, string> = {
  verstehen: "Understanding question",
  abfragen: "Querying data",
  analysieren: "Analysing",
  diagramm: "Building chart",
  schreiben: "Writing answer",
  pruefen: "Verifying",
  korrigieren: "Refining answer",
};
const STATUS: Record<Stufe["status"], string> = { erledigt: "Done", aktiv: "In progress", offen: "", uebersprungen: "Not needed" };
const HTML = /\.(x?html?|shtml|mht)$/i;
const BILD = /\.(png|jpe?g|gif|webp|svg)$/i;

const html = (h: string) => ({ __html: h });

export function Wortmarke() {
  return (
    <span className="name">
      Data Desk<span className="punkt" />
    </span>
  );
}

// Anmeldung

export function Login(props: { meta: string; meldung: string; onAnmelden: (email: string, passwort: string) => Promise<string | null> }) {
  const [email, setEmail] = useState("");
  const [passwort, setPasswort] = useState("");
  const [meldung, setMeldung] = useState(props.meldung);
  const [busy, setBusy] = useState(false);

  async function absenden(e: FormEvent) {
    e.preventDefault();
    if (busy || !email.trim() || !passwort) return;
    setBusy(true);
    const fehler = await props.onAnmelden(email.trim(), passwort);
    setBusy(false);
    setPasswort("");
    setMeldung(fehler ?? "");
  }

  return (
    <div className="login">
      <div className="login-links">
        <div className="wuerfel" aria-hidden="true">
          <dd-wireframe kind="lattice" cx="0.5" cy="0.475" scale="0.22" />
        </div>
        <img className="marke" src={logo} alt="SAE" />
        <div className="login-titel">
          <div className="wortmarke">
            Data Desk<span className="punkt" />
          </div>
          <div className="unterzeile">Questions about the business, answered from the data warehouse.</div>
        </div>
      </div>
      <div className="login-rechts">
        <form className="login-form" onSubmit={absenden}>
          <h1>Sign in</h1>
          <label className="feld">
            <span>Email</span>
            <input type="text" inputMode="email" autoComplete="username" placeholder="name@sae.edu" value={email} onChange={(e) => setEmail(e.target.value)} autoFocus />
          </label>
          <label className="feld">
            <span>Password</span>
            <input type="password" autoComplete="current-password" placeholder="••••••••" value={passwort} onChange={(e) => setPasswort(e.target.value)} />
          </label>
          <button type="submit" className="knopf" disabled={busy}>
            Sign in
          </button>
          {meldung && (
            <div className="login-meldung" role="alert">
              {meldung}
            </div>
          )}
          <div className="meta">{props.meta}</div>
        </form>
      </div>
    </div>
  );
}

// Rahmen

export function Kopf(props: { speichert: boolean; onBeispiele: () => void; onBeta: () => void; onExport: () => void; onReset: () => void }) {
  return (
    <header className="kopf">
      <div className="kopf-links">
        <img className="marke" src={logo} alt="SAE" />
        <span className="trenner" />
        <Wortmarke />
      </div>
      <div className="kopf-rechts">
        {props.speichert && (
          <span className="beta-hinweis" role="status">
            <span className="lang">Conversation is being saved</span>
            <span className="kurz">Saving</span>
          </span>
        )}
        <button className="textknopf" onClick={props.onBeispiele}>
          Examples
        </button>
        <button className="textknopf" onClick={props.onExport}>
          Export
        </button>
        <button className="textknopf" onClick={props.onReset}>
          Reset
        </button>
        <button className="textknopf" onClick={props.onBeta}>
          <span className="lang">Beta features</span>
          <span className="kurz">Beta</span>
        </button>
      </div>
    </header>
  );
}

export function Banner() {
  return (
    <div className="banner" role="status">
      <b>Connection lost.</b>
      <span>Reconnecting. Your conversation is safe and nothing needs to be re-entered.</span>
    </div>
  );
}

function Schalter({ an, gross }: { an: boolean; gross?: boolean }) {
  return (
    <span className={`schalter ${gross ? "gross" : "klein"} ${an ? "an" : ""}`}>
      <i />
    </span>
  );
}

function absendenMitEnter(e: KeyboardEvent<HTMLTextAreaElement>, absenden: () => void) {
  if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
    e.preventDefault();
    absenden();
  }
}

type Schalterleiste = { verify: boolean; schnell: boolean; onVerify: () => void; onSchnell: () => void };
type Eingabe = { entwurf: string; fokus: number; onEntwurf: (t: string) => void; onFrage: () => void };

// Setzt den Cursor ins Feld, sobald `fokus` steigt (Wahl einer Beispielfrage), nicht beim ersten Zeichnen
function useFokus(feld: { current: HTMLTextAreaElement | null }, fokus: number) {
  useEffect(() => {
    if (fokus) feld.current?.focus();
  }, [fokus]);
}

const SCHNELL_TITEL = "Fast: the answer thinks less deeply. Verify still checks at full depth.";

export function Leer(props: Schalterleiste & Eingabe) {
  const feld = useRef<HTMLTextAreaElement>(null);
  useFokus(feld, props.fokus);
  return (
    <main className="leer">
      <div className="leer-innen">
        <textarea
          ref={feld}
          rows={3}
          maxLength={4000}
          placeholder="Ask a question about the business."
          aria-label="Question"
          value={props.entwurf}
          autoFocus
          onChange={(e) => props.onEntwurf(e.target.value)}
          onKeyDown={(e) => absendenMitEnter(e, props.onFrage)}
        />
        <div className="leer-zeile">
          <div className="schalter-gruppe">
            <button className="pruefen" onClick={props.onVerify} aria-pressed={props.verify}>
              <Schalter an={props.verify} gross />
              <span className="pruefen-text">
                <b>
                  Verify <span>{props.verify ? "On" : "Off"}</span>
                </b>
                <small>Verified answers take longer.</small>
              </span>
            </button>
            <button className="pruefen" onClick={props.onSchnell} aria-pressed={props.schnell} title={SCHNELL_TITEL}>
              <Schalter an={props.schnell} gross />
              <span className="pruefen-text">
                <b>
                  Fast <span>{props.schnell ? "On" : "Off"}</span>
                </b>
                <small>Quicker, less in-depth.</small>
              </span>
            </button>
          </div>
          <button className="knopf" onClick={props.onFrage}>
            Ask
          </button>
        </div>
      </div>
    </main>
  );
}

export function Folge(props: Schalterleiste & Eingabe & { arbeitet: boolean }) {
  const feld = useRef<HTMLTextAreaElement>(null);
  useFokus(feld, props.fokus);
  useEffect(() => {
    // einzeilig, wächst mit Umschalt+Enter
    const f = feld.current;
    if (!f) return;
    f.style.height = "auto";
    f.style.height = `${f.scrollHeight}px`;
  }, [props.entwurf, props.arbeitet]);
  return (
    <div className="folge">
      <div className="folge-innen">
        <div className="folge-rand">Follow-up</div>
        <div className="folge-feld">
          {props.arbeitet ? (
            <span className="folge-warten">You can ask a follow-up once this answer is ready.</span>
          ) : (
            <>
              <textarea
                ref={feld}
                rows={1}
                maxLength={4000}
                placeholder="Ask a follow-up question."
                aria-label="Follow-up question"
                value={props.entwurf}
                onChange={(e) => props.onEntwurf(e.target.value)}
                onKeyDown={(e) => absendenMitEnter(e, props.onFrage)}
              />
              <button className="pruefen" onClick={props.onVerify} aria-pressed={props.verify} title="Verified answers take longer.">
                <Schalter an={props.verify} />
                <b>Verify</b>
                <small>takes longer</small>
              </button>
              <button className="pruefen" onClick={props.onSchnell} aria-pressed={props.schnell} title={SCHNELL_TITEL}>
                <Schalter an={props.schnell} />
                <b>Fast</b>
                <small>less in-depth</small>
              </button>
              <button className="knopf" onClick={props.onFrage}>
                Ask
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export function Fuss({ meta }: { meta: string }) {
  return <footer className="fuss">{meta}</footer>;
}

// Verlauf

export function FrageAbschnitt(props: { n: number; zeit: string; text: string; abschnitt?: Ref<HTMLElement> }) {
  return (
    <section className="abschnitt frage" ref={props.abschnitt}>
      <div className="rand">
        <b>Question {nr(props.n)}</b>
        <span>{props.zeit}</span>
      </div>
      <div className="spalte fragetext" lang={sprache(props.text)}>
        {props.text}
      </div>
    </section>
  );
}

export function ArbeitAbschnitt(props: { zug: Zug; sekunden: number; onAbbrechen: () => void }) {
  const { zug } = props;
  const stufen: Stufe[] =
    zug.runde?.stufen ??
    Object.keys(STUFEN)
      .filter((s) => zug.verify || (s !== "pruefen" && s !== "korrigieren"))
      .map((stufe, i) => ({ stufe, status: i === 0 ? "aktiv" : "offen" }));
  const schritte = zug.runde?.schritte ?? [];
  return (
    <section className="abschnitt">
      <div className="rand arbeit-rand">
        <b>Working</b>
        <span className="zeit" aria-live="off">
          {laufzeit(props.sekunden)}
        </span>
        <small>elapsed</small>
        <button className="unterstrichen" onClick={props.onAbbrechen} disabled={zug.abbrechen}>
          Cancel
        </button>
      </div>
      <div className="spalte arbeit">
        <div className="satz" aria-hidden="true">
          {[100, 94, 98, 71, 90, 96, 58].map((w, i) => (
            <i key={i} style={{ width: `${w}%`, animationDelay: `${i * 0.24}s` }} />
          ))}
        </div>
        <div className="arbeit-spalten">
          <div className="stufen" aria-label="Stages">
            {stufen.map((s, i) => (
              <div key={s.stufe} className={`stufe ${s.status}`}>
                <span className="nr">{nr(i + 1)}</span>
                <span className="label">{STUFEN[s.stufe] ?? s.stufe}</span>
                <span className="leiter" />
                <span className="st">{STATUS[s.status]}</span>
              </div>
            ))}
          </div>
          <div className="schritte" aria-live="polite">
            <b>Analyst’s steps</b>
            {schritte.map((s, i) => (
              <div key={`${i}-${s.text}`} className="schritt">
                <span>{laufzeit(s.s)}</span>
                <span>{s.text}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="arbeit-hinweis">
          {zug.schnell ? "Fast is on, the answer thinks less deeply. " : ""}
          {zug.verify ? `Verify is on. This answer will be checked${zug.schnell ? " at full depth" : ""} before it is shown. ` : ""}
          Answers usually take one to several minutes.
        </div>
      </div>
    </section>
  );
}

export function AntwortAbschnitt(props: { zug: Zug; n: number; arbeitet: boolean; onOption: (t: string) => void; onDashboard: (o: Overlay) => void }) {
  const { zug } = props;
  const text = zug.runde?.antwort ?? "";
  const gespraech = zug.gespraech ?? null;
  const a = useMemo(() => zerlege(text, gespraech), [text, gespraech]);
  const lang = sprache(text);
  const status = zug.runde?.pruefung?.status;
  const vermerk = status === "bestaetigt" ? " · Verified" : status === "korrigiert" ? " · Corrected after verification" : "";
  const meta = zug.fertig ? `${uhrzeit(zug.fertig)} · ${dauer(zug.fertig.getTime() - zug.zeit.getTime())}${vermerk}` : "";

  if (a.art === "keine" || a.art === "rueckfrage" || a.art === "kurzklaerung") {
    return (
      <section className="abschnitt zug" lang={lang}>
        <div className="rand">
          <b>{a.art === "keine" ? "Answer" : a.art === "kurzklaerung" ? "Before building" : "Clarification"}</b>
          <span>{zug.fertig ? uhrzeit(zug.fertig) : ""}</span>
        </div>
        <div className="spalte schmal">
          <p className="titel22" dangerouslySetInnerHTML={html(a.titel)} />
          <div className="text16" dangerouslySetInnerHTML={html(a.rest)} />
          {a.art === "keine" && <Lesarten lesarten={a.lesarten} arbeitet={props.arbeitet} onOption={props.onOption} />}
          {a.art === "rueckfrage" && a.optionen.length > 0 && (
            <div className="optionen">
              {a.optionen.map((o) => (
                <button key={o} disabled={props.arbeitet} onClick={() => props.onOption(o)}>
                  {o}
                </button>
              ))}
            </div>
          )}
          {a.art === "kurzklaerung" && (
            <>
              {a.optionen.length > 0 && (
                <ol className="klaerung">
                  {a.optionen.map((o) => <li key={o} dangerouslySetInnerHTML={html(inline(o, gespraech))} />)}
                </ol>
              )}
              <div className="optionen">
                <button className="so-bauen" disabled={props.arbeitet} onClick={() => props.onOption(lang === "de" ? "So bauen." : "Build it this way.")}>
                  {lang === "de" ? "So bauen" : "Build it this way"}
                </button>
                <span className="meta">{lang === "de" ? "Oder Änderungen unten eingeben." : "Or type changes below."}</span>
              </div>
            </>
          )}
        </div>
      </section>
    );
  }

  const [titel, setTitel] = useState<Record<string, string>>({});
  const dateien = zug.runde?.dateien ?? [];
  const dashboards = dateien.filter((d) => HTML.test(d.name));
  const bilder = dateien.filter((d) => BILD.test(d.name) && !a.bilder.includes(d.url));
  const andere = dateien.filter((d) => !HTML.test(d.name) && !BILD.test(d.name));
  // Ein Link im Text auf ein Dashboard öffnet es im Overlay. Als eigene Seite käme nur sein Quelltext.
  function dashboardLink(e: MouseEvent<HTMLDivElement>) {
    const link = (e.target as HTMLElement).closest("a");
    const ziel = dashboards.find((d) => d.url === link?.getAttribute("href"));
    if (!ziel) return;
    e.preventDefault();
    props.onDashboard({ url: ziel.url, titel: titel[ziel.url] ?? titelAusName(ziel.name), nr: props.n, zeit: zug.fertig });
  }
  const p = zug.runde?.pruefung;
  const hinweis = p && (p.status === "hinweis" || p.status === "gescheitert") && p.hinweis ? p.hinweis : null;

  return (
    <section className="abschnitt zug" lang={lang}>
      <div className="rand">
        <b>Answer</b>
        <span>{meta}</span>
      </div>
      <div className="spalte antwort">
        {a.lead && <p className="lead" dangerouslySetInnerHTML={html(a.lead)} />}
        <Lesarten lesarten={a.lesarten} arbeitet={props.arbeitet} onOption={props.onOption} />
        {a.kennzahlen.length > 0 && (
          <div className="kennzahlen">
            {a.kennzahlen.map((k, i) => (
              <div key={i} className="kennzahl">
                <div className="kennzahl-wert">
                  <b>{k.wert}</b>
                  {k.einheit && <span>{k.einheit}</span>}
                </div>
                <div className="kennzahl-label" dangerouslySetInnerHTML={html(k.label)} />
              </div>
            ))}
          </div>
        )}
        {a.diagramme.map((d, i) => <DiagrammAnsicht key={i} spec={d} lang={lang} />)}
        {a.rest && <div className="md" onClick={dashboardLink} dangerouslySetInnerHTML={html(a.rest)} />}
        {a.unvollstaendig && <div className="meta">Part of this answer could not be displayed.</div>}
        {hinweis && (
          <div className="hinweis">
            <b lang="en">Note after verification</b>
            <span dangerouslySetInnerHTML={html(inline(hinweis, gespraech))} />
          </div>
        )}
        {bilder.map((d) => (
          <figure key={d.url} className="abbildung">
            <img src={d.url} alt={d.name} />
          </figure>
        ))}
        {dashboards.map((d) => (
          <DashboardKarte
            key={d.url}
            datei={d}
            titel={titel[d.url] ?? titelAusName(d.name)}
            onTitel={(t) => setTitel((alt) => ({ ...alt, [d.url]: t }))}
            onOeffnen={() => props.onDashboard({ url: d.url, titel: titel[d.url] ?? titelAusName(d.name), nr: props.n, zeit: zug.fertig })}
          />
        ))}
        <Quellenbeleg belege={a.quellen.length ? a.quellen : mitAnnahmen(zug.runde?.beleg ?? [], a.annahmen)} abfragen={(zug.runde?.abfragen ?? []).filter((q) => !q.fehler).map((q) => q.sql)} />
        {andere.length > 0 && (
          <div className="dateien">
            <b>Files</b>
            {andere.map((d) => (
              <a key={d.url} href={d.url} target="_blank" rel="noopener noreferrer" download={d.name.split("/").pop()}>
                {d.name}
              </a>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

const STUFE: Record<string, string> = { freigegeben: "approved", vorschlag: "provisional", "ohne Katalog": "not in catalogue" };

// Eingeklappter Quellenbeleg: Definitionen mit Stufe, Quellen, Filter, Annahmen und die SQL der Runde. Seit 0.5.0 baut
// ihn die Anwendung (runde.beleg), ein Beleg vom Modell in der Antwort geht vor.
// Knöpfe für andere Lesarten, höchstens zwei (6.7, Runde 6), bei einer Nichtantwort die verwandte Auswertung
function Lesarten(props: { lesarten: Lesart[]; arbeitet: boolean; onOption: (t: string) => void }) {
  if (!props.lesarten.length) return null;
  return (
    <div className="lesart">
      {props.lesarten.map((l) => (
        <button key={l.label} className="umriss" disabled={props.arbeitet} onClick={() => props.onOption(l.prompt)}>
          {l.label}
        </button>
      ))}
    </div>
  );
}

function Quellenbeleg({ belege, abfragen }: { belege: Beleg[]; abfragen: string[] }) {
  if (!belege.length && !abfragen.length) return null;
  const vorlaeufig = belege.some((b) => b.metricDefinitions.some((d) => d.stage !== "freigegeben"));
  const liste = (titel: string, eintraege: string[]) =>
    eintraege.length > 0 && (
      <div className="beleg-teil">
        <b>{titel}</b>
        <ul>{eintraege.map((e) => <li key={e}>{e}</li>)}</ul>
      </div>
    );
  return (
    <details className="quellenbeleg">
      <summary>
        Sources{belege.length > 1 ? ` · ${belege.length}` : ""}
        {vorlaeufig && <span> · definitions provisional</span>}
      </summary>
      {belege.map((b, i) => (
        <div key={i} className="beleg">
          {b.title && <p className="beleg-titel">{b.title}</p>}
          {b.metricDefinitions.length > 0 && (
            <div className="beleg-teil">
              <b>Definitions</b>
              <ul>
                {b.metricDefinitions.map((d, k) => (
                  <li key={k}>
                    {d.label && <strong>{d.label}: </strong>}
                    {d.definition}
                    {d.stage && <span className={`stufe-marke ${d.stage === "freigegeben" ? "" : "offen"}`}>{STUFE[d.stage] ?? d.stage}</span>}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {liste("Assumptions and caveats", [...b.assumptions, ...b.caveats])}
          {liste("Filters and period", [...b.filters, ...(b.reportingPeriod ? [b.reportingPeriod] : [])])}
          {liste("Data sources", b.tables)}
        </div>
      ))}
      {abfragen.length > 0 && (
        <div className="beleg-teil">
          <b>Queries</b>
          {abfragen.map((q, i) => <pre key={i}><code>{q}</code></pre>)}
        </div>
      )}
    </details>
  );
}

// Beleg der Anwendung mit den Annahmen aus der Antwort (0.5.2)
function mitAnnahmen(belege: Beleg[], annahmen: string[]): Beleg[] {
  if (!annahmen.length) return belege;
  const [erster, ...rest] = belege.length ? belege
    : [{ title: "", metricDefinitions: [], tables: [], filters: [], assumptions: [], caveats: [] }];
  return [{ ...erster, assumptions: [...new Set([...annahmen, ...erster.assumptions])] }, ...rest];
}

function titelAusName(name: string) {
  const basis = name.split("/").filter((t) => !/^(dist|build|out|index\.html?)$/i.test(t)).pop() ?? "";
  const t = basis.replace(HTML, "").replace(/[-_]+/g, " ").trim();
  return t ? t[0].toUpperCase() + t.slice(1) : "Dashboard";
}

// Vorschau 1200 px breit, auf 0.3 verkleinert, nicht bedienbar. Wie jede Datei des Modells nur im Rahmen mit
// sandbox="allow-scripts" (Befund 4.4).
function DashboardKarte(props: { datei: Datei; titel: string; onTitel: (t: string) => void; onOeffnen: () => void }) {
  const { titel, onTitel } = props;
  useEffect(() => {
    let aktiv = true;
    dashboardTitel(props.datei.url).then((t) => aktiv && t && onTitel(t));
    return () => {
      aktiv = false;
    };
  }, [props.datei.url]);
  return (
    <div className="dash-karte" role="button" tabIndex={0} onClick={props.onOeffnen} onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && (e.preventDefault(), props.onOeffnen())}>
      <div className="dash-bild">
        <iframe src={props.datei.url} sandbox="allow-scripts" referrerPolicy="no-referrer" loading="lazy" tabIndex={-1} aria-hidden="true" title="" />
      </div>
      <div className="dash-text">
        <div>
          <small>Dashboard</small>
          <strong>{titel}</strong>
          <span>Interactive · opens in a large view</span>
        </div>
        <span className="oeffnen">Open dashboard</span>
      </div>
    </div>
  );
}

export function Unterbrochen(props: { zug: Zug; zeitlimit: number; onNochmal: () => void }) {
  const art = props.zug.fehler;
  const minuten = Math.round(props.zeitlimit / 60);
  const [titel, text, knopf] =
    art === "zeit"
      ? ["This took too long", `The analyst stopped after ${minuten} minutes without a result. A narrower question usually works: a shorter period, or fewer campuses.`, "Ask again"]
      : art === "belegt"
        ? ["All analysts are busy", "Data Desk is answering as many questions as it can right now. Your question is kept, please try again in a few minutes.", "Try again"]
        : ["Connection lost", "The connection dropped while the analyst was working. Your question is kept, nothing else was lost.", "Try again"];
  return (
    <section className="abschnitt zug">
      <div className="rand">
        <b>Interrupted</b>
        <span>{uhrzeit(props.zug.fertig ?? props.zug.zeit)}</span>
      </div>
      <div className="spalte schmal unterbrochen">
        <p className="titel18">{titel}</p>
        <p className="text15">{text}</p>
        <button className="knopf" onClick={props.onNochmal}>
          {knopf}
        </button>
      </div>
    </section>
  );
}

// Überlagerungen

export function Exportmenue(props: { blaetter: number; onPdf: () => void; onExcel: () => void; onSchliessen: () => void }) {
  return (
    <>
      <div className="auffang" onClick={props.onSchliessen} />
      <div className="exportmenue" role="menu">
        <button role="menuitem" onClick={props.onPdf}>
          <b>PDF report</b>
          <span>The whole conversation, typeset for reading and forwarding.</span>
        </button>
        <button role="menuitem" onClick={props.onExcel} disabled={props.blaetter === 0}>
          <b>Excel</b>
          <span>
            {props.blaetter === 0
              ? "No tables in this conversation yet."
              : `All tables, one sheet per answer. ${props.blaetter} ${props.blaetter === 1 ? "sheet" : "sheets"}.`}
          </span>
        </button>
      </div>
    </>
  );
}

// Beispielfragen zu den Darstellungsarten: Ein Klick setzt die Frage ins Eingabefeld, abgeschickt wird sie nicht
export function BeispielMenue(props: { mitAntwort: boolean; onWahl: (frage: string) => void; onSchliessen: () => void }) {
  return (
    <>
      <div className="auffang" onClick={props.onSchliessen} />
      <div className="exportmenue beispielmenue" role="menu" aria-label="Example questions">
        <div className="beta-kopf">
          <b>Example questions</b>
          <span>What Data Desk can show. Pick one to edit it before you ask.</span>
        </div>
        {BEISPIELE.map((b) => (
          // Eine Folgefrage braucht eine Antwort, auf die sie sich bezieht
          <button key={b.art} role="menuitem" onClick={() => props.onWahl(b.frage)} disabled={b.folge && !props.mitAntwort}>
            <b>
              {b.art} <small>{b.folge && !props.mitAntwort ? "After a first answer" : b.hinweis}</small>
            </b>
            <span>{b.frage}</span>
          </button>
        ))}
      </div>
    </>
  );
}

// Beta-Funktionen (Schritt 6.1): Speichern je Gespräch und Feedback, Rückbau vor dem Rollout
export function BetaMenue(props: {
  ablage: boolean;
  speichern: boolean;
  gespraech: boolean;
  onSpeichern: () => void;
  onFeedback: (text: string, mitsenden: boolean) => Promise<string | null>;
  onSchliessen: () => void;
}) {
  const [text, setText] = useState("");
  const [mitsenden, setMitsenden] = useState(true);
  const [busy, setBusy] = useState(false);
  const [meldung, setMeldung] = useState("");

  async function senden(e: FormEvent) {
    e.preventDefault();
    if (!text.trim() || busy) return;
    setBusy(true);
    setMeldung((await props.onFeedback(text.trim(), mitsenden && props.gespraech)) ?? "");
    setBusy(false);
  }

  return (
    <>
      <div className="auffang" onClick={props.onSchliessen} />
      <div className="exportmenue betamenue" role="dialog" aria-label="Beta features">
        <div className="beta-kopf">
          <b>Beta features</b>
          <span>Help us improve Data Desk during development. These features will be removed before the rollout.</span>
        </div>
        {props.ablage ? (
          <>
            <button className="pruefen beta-zeile" onClick={props.onSpeichern} aria-pressed={props.speichern}>
              <Schalter an={props.speichern} gross />
              <span className="pruefen-text">
                <b>Save conversation</b>
                <small>Questions, answers and files of this conversation are stored on the server for the development team.</small>
              </span>
            </button>
            <form className="beta-feedback" onSubmit={senden}>
              <label htmlFor="beta-text">
                <b>Feedback</b>
              </label>
              <textarea
                id="beta-text"
                rows={4}
                maxLength={4000}
                placeholder="What worked, what did not?"
                value={text}
                onChange={(e) => setText(e.target.value)}
              />
              <label className="beta-haken">
                <input
                  type="checkbox"
                  checked={mitsenden && props.gespraech}
                  disabled={!props.gespraech}
                  onChange={(e) => setMitsenden(e.target.checked)}
                />
                Include current conversation
              </label>
              {meldung && <span className="beta-meldung">{meldung}</span>}
              <button className="knopf" type="submit" disabled={busy || !text.trim()}>
                Send feedback
              </button>
            </form>
          </>
        ) : (
          <div className="beta-kopf">
            <span>Saving and feedback are switched off on this server.</span>
          </div>
        )}
      </div>
    </>
  );
}

export function Toast(props: { titel: string; text: string; onSchliessen: () => void }) {
  return (
    <div className="toast" role="status">
      <div>
        <b>{props.titel}</b>
        <span>{props.text}</span>
      </div>
      <button onClick={props.onSchliessen}>Close</button>
    </div>
  );
}

export function DashboardOverlay(props: { overlay: Overlay; onSchliessen: () => void }) {
  const { overlay } = props;
  return (
    <div className="overlay" role="dialog" aria-modal="true" aria-label={overlay.titel}>
      <div className="overlay-panel">
        <div className="overlay-kopf">
          <div>
            <strong>{overlay.titel}</strong>
            <span>
              Dashboard from answer {nr(overlay.nr)}
              {overlay.zeit ? ` · built ${uhrzeit(overlay.zeit)}` : ""}
            </span>
          </div>
          <button className="umriss" onClick={props.onSchliessen} autoFocus>
            Close
          </button>
        </div>
        <div className="overlay-rumpf">
          <iframe src={overlay.url} sandbox="allow-scripts" referrerPolicy="no-referrer" title={overlay.titel} />
        </div>
        <div className="overlay-fuss">Interactive. Filters change the dashboard only, not the conversation. Press Esc to close.</div>
      </div>
    </div>
  );
}

export function ResetDialog(props: { onAbbrechen: () => void; onExport: () => void; onVerwerfen: () => void }) {
  return (
    <div className="dialog-grund" onClick={(e) => e.target === e.currentTarget && props.onAbbrechen()}>
      <div className="dialog" role="dialog" aria-modal="true" aria-labelledby="reset-titel">
        <h2 id="reset-titel">Discard this conversation?</h2>
        <p>Export it first? Discarding clears every question and answer, as if you were opening Data Desk for the first time. There is no history to return to.</p>
        <div className="dialog-fuss">
          <button onClick={props.onAbbrechen}>Cancel</button>
          <div>
            <button className="umriss" onClick={props.onExport}>
              Export
            </button>
            <button className="knopf" onClick={props.onVerwerfen} autoFocus>
              Discard
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
