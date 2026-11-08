// Diagramm der Antwort nach dem Host-Vertrag charts_widget_v2 (dwh_v2/anweisungen/analyst.md): Balken stehend und
// liegend, Linie, Kreis als Ring, Streuung. Selbst gezeichnet als SVG in Schwarz und Grau wie der Entwurf, ohne
// Bibliothek. Werte kommen als Zahl, als Text aus SQL-Dezimalzahlen oder als null für fehlend.
import type { ReactElement } from "react";
import type { Diagramm as Spec, Reihe } from "./antwort";

const FARBEN = ["#1c1c1c", "#8a8d90", "#c9c9c6", "#55595c", "#a6a9ac", "#e3e3e0"];
const B = 720; // Breite des viewBox, das SVG skaliert mit der Spalte

// Text aus dem JSON des Modells: Objekte an dieser Stelle würden React die ganze Antwort verwerfen lassen
const text = (w: unknown) => (typeof w === "string" || typeof w === "number" ? String(w) : "");

function zahl(w: unknown): number | null {
  if (typeof w === "number") return Number.isFinite(w) ? w : null;
  if (typeof w === "string" && /^\s*-?\d+(\.\d+)?\s*$/.test(w)) return Number(w);
  return null;
}

function format(lang: string, w: number, reihe?: Reihe) {
  const ziffern = Math.abs(w) >= 100 || Number.isInteger(w) ? 0 : Math.abs(w) >= 10 ? 1 : 2;
  const zahltext = new Intl.NumberFormat(lang === "de" ? "de-DE" : "en-GB", { maximumFractionDigits: ziffern }).format(w);
  return `${text(reihe?.valuePrefix)}${zahltext}${text(reihe?.valueSuffix)}`;
}

// Runde Achsenwerte: Schrittweite 1, 2 oder 5 mal Zehnerpotenz. Balken beginnen bei null, Linien und Streuung nicht.
function skala(werte: number[], mitNull = true, schritte = 4) {
  let min = Math.min(...(mitNull ? [0] : []), ...werte);
  let max = Math.max(...(mitNull ? [0] : []), ...werte);
  if (min === max) [min, max] = [min - 1, max + 1];
  const roh = (max - min || 1) / schritte;
  const potenz = 10 ** Math.floor(Math.log10(roh));
  const schritt = [1, 2, 5, 10].map((f) => f * potenz).find((s) => s >= roh) ?? roh;
  const unten = Math.floor(min / schritt) * schritt;
  const oben = Math.max(Math.ceil(max / schritt) * schritt, unten + schritt);
  const ticks: number[] = [];
  for (let t = unten; t <= oben + schritt / 2; t += schritt) ticks.push(Number(t.toPrecision(12)));
  return { unten, oben, ticks };
}

const kurz = (t: string, n: number) => (t.length > n ? `${t.slice(0, n - 1)}…` : t);

export function DiagrammAnsicht(props: { spec: Spec; lang: string }) {
  const s = props.spec;
  const daten = Array.isArray(s.data) ? s.data.slice(0, 200) : [];
  const reihen = (Array.isArray(s.series) ? s.series : []).filter((r) => r && typeof r.dataKey === "string");
  const titel = text(s.meta?.title);
  const beschreibung = text(s.meta?.description);
  const fuss = text(s.meta?.footer);
  let svg: ReactElement | null = null;
  if (s.chartType === "pie") svg = <Ring spec={s} daten={daten} lang={props.lang} />;
  else if (reihen.length && (s.xKey || s.chartType === "scatter")) {
    if (s.chartType === "line") svg = <Linien spec={s} daten={daten} reihen={reihen} lang={props.lang} />;
    else if (s.chartType === "scatter") svg = <Streuung spec={s} daten={daten} reihen={reihen} lang={props.lang} />;
    else if (s.layout === "vertical") svg = <Liegend spec={s} daten={daten} reihen={reihen} lang={props.lang} />;
    else svg = <Stehend spec={s} daten={daten} reihen={reihen} lang={props.lang} />;
  }
  // Ein Diagramm, das sich nicht zeichnen lässt, verschwindet nicht still (Zweitmeinung 6.3)
  if (!svg || !daten.length) return <div className="meta">A chart in this answer could not be displayed{titel ? `: ${titel}` : ""}.</div>;
  return (
    <figure className="diagramm" aria-label={titel || undefined}>
      {(titel || beschreibung) && (
        <figcaption>
          {titel && <b>{titel}</b>}
          {beschreibung && <span>{beschreibung}</span>}
        </figcaption>
      )}
      {reihen.length > 1 && s.chartType !== "pie" && s.chartType !== "scatter" && (
        <div className="legende">
          {reihen.map((r, i) => (
            <span key={r.dataKey}>
              <i style={{ background: FARBEN[i % FARBEN.length] }} />
              {text(r.label) || r.dataKey}
            </span>
          ))}
        </div>
      )}
      {svg}
      {fuss && <span className="diagramm-fuss">{fuss}</span>}
    </figure>
  );
}

const werteAus = (daten: Record<string, unknown>[], reihen: Reihe[]) =>
  daten.flatMap((d) => reihen.map((r) => zahl(d[r.dataKey]))).filter((w): w is number => w !== null);

type Teil = { spec: Spec; daten: Record<string, unknown>[]; reihen: Reihe[]; lang: string };

function Achse(props: { y: (w: number) => number; ticks: number[]; links: number; rechts: number; lang: string; reihe: Reihe }) {
  return (
    <g className="achse">
      {props.ticks.map((t) => (
        <g key={t}>
          <line x1={props.links} x2={props.rechts} y1={props.y(t)} y2={props.y(t)} stroke={t === 0 || t === props.ticks[0] ? "#1c1c1c" : "#ededeb"} />
          <text x={props.links - 8} y={props.y(t) + 4} textAnchor="end">{format(props.lang, t, props.reihe)}</text>
        </g>
      ))}
    </g>
  );
}

function Stehend({ spec, daten, reihen, lang }: Teil) {
  const H = 300, L = 64, R = B - 8, O = 24, U = H - 44;
  const werte = werteAus(daten, reihen);
  if (!werte.length) return null;
  const { unten, oben, ticks } = skala(werte);
  const y = (w: number) => U - ((w - unten) / (oben - unten)) * (U - O);
  const band = (R - L) / daten.length;
  const gruppe = band * 0.72;
  const breite = gruppe / reihen.length;
  const jede = Math.ceil(daten.length / 12);
  const mitWerten = daten.length * reihen.length <= 24;
  return (
    <svg viewBox={`0 0 ${B} ${H}`} role="img">
      <Achse y={y} ticks={ticks} links={L} rechts={R} lang={lang} reihe={reihen[0]} />
      {daten.map((d, i) => (
        <g key={i}>
          {reihen.map((r, k) => {
            const w = zahl(d[r.dataKey]);
            if (w === null) return null;
            const x = L + i * band + (band - gruppe) / 2 + k * breite;
            return (
              <g key={r.dataKey}>
                <rect x={x} y={Math.min(y(w), y(0))} width={Math.max(breite - 2, 1)} height={Math.abs(y(0) - y(w))}
                  fill={FARBEN[k % FARBEN.length]}><title>{`${String(d[spec.xKey!] ?? "")}: ${format(lang, w, r)}`}</title></rect>
                {mitWerten && <text className="wert" x={x + breite / 2 - 1} y={w >= 0 ? y(w) - 6 : y(w) + 14} textAnchor="middle">{format(lang, w, r)}</text>}
              </g>
            );
          })}
          {i % jede === 0 && (
            <text className="kategorie" x={L + i * band + band / 2} y={U + 20} textAnchor="middle">
              {kurz(String(d[spec.xKey!] ?? ""), Math.max(4, Math.floor(band * jede / 8)))}
            </text>
          )}
        </g>
      ))}
      {spec.xAxisLabel && <text className="kategorie" x={(L + R) / 2} y={H - 4} textAnchor="middle">{spec.xAxisLabel}</text>}
    </svg>
  );
}

function Liegend({ spec, daten, reihen, lang }: Teil) {
  const zeile = 14 + 12 * reihen.length, L = 184, R = B - 72, O = 8;
  const H = O + zeile * daten.length + 8;
  const werte = werteAus(daten, reihen);
  if (!werte.length) return null;
  const { unten, oben } = skala(werte);
  const x = (w: number) => L + ((w - unten) / (oben - unten)) * (R - L);
  return (
    <svg viewBox={`0 0 ${B} ${H}`} role="img">
      <line x1={x(0)} x2={x(0)} y1={O} y2={H - 8} stroke="#1c1c1c" />
      {daten.map((d, i) => (
        <g key={i}>
          <text className="kategorie" x={L - 10} y={O + i * zeile + zeile / 2 + 4} textAnchor="end">{kurz(String(d[spec.xKey!] ?? ""), 26)}</text>
          {reihen.map((r, k) => {
            const w = zahl(d[r.dataKey]);
            const yy = O + i * zeile + 7 + k * 12;
            if (w === null) return <text key={r.dataKey} className="wert" x={x(0) + 6} y={yy + 9}>–</text>;
            return (
              <g key={r.dataKey}>
                <rect x={Math.min(x(w), x(0))} y={yy} height={10} width={Math.max(Math.abs(x(w) - x(0)), 1)} fill={FARBEN[k % FARBEN.length]} />
                <text className="wert" x={Math.max(x(w), x(0)) + 6} y={yy + 9}>{format(lang, w, r)}</text>
              </g>
            );
          })}
        </g>
      ))}
    </svg>
  );
}

function Linien({ spec, daten, reihen, lang }: Teil) {
  const H = 300, L = 64, R = B - 16, O = 24, U = H - 44, E = 32;
  const werte = werteAus(daten, reihen);
  if (!werte.length) return null;
  const { unten, oben, ticks } = skala(werte, false);
  const y = (w: number) => U - ((w - unten) / (oben - unten)) * (U - O);
  const x = (i: number) => (daten.length === 1 ? (L + R) / 2 : L + E + (i / (daten.length - 1)) * (R - L - 2 * E));
  const jede = Math.ceil(daten.length / 10);
  const mitWerten = daten.length <= 12 && reihen.length === 1;
  return (
    <svg viewBox={`0 0 ${B} ${H}`} role="img">
      <Achse y={y} ticks={ticks} links={L} rechts={R} lang={lang} reihe={reihen[0]} />
      {reihen.map((r, k) => {
        // Fehlende Werte unterbrechen die Linie
        const stuecke: string[][] = [[]];
        daten.forEach((d, i) => {
          const w = zahl(d[r.dataKey]);
          if (w === null) stuecke.push([]);
          else stuecke[stuecke.length - 1].push(`${x(i)},${y(w)}`);
        });
        return (
          <g key={r.dataKey}>
            {stuecke.filter((p) => p.length > 1).map((p, j) => (
              <polyline key={j} points={p.join(" ")} fill="none" stroke={FARBEN[k % FARBEN.length]} strokeWidth={2} />
            ))}
            {daten.map((d, i) => {
              const w = zahl(d[r.dataKey]);
              return w === null ? null : (
                <g key={i}>
                  <circle cx={x(i)} cy={y(w)} r={3} fill={FARBEN[k % FARBEN.length]}><title>{`${String(d[spec.xKey!] ?? "")}: ${format(lang, w, r)}`}</title></circle>
                  {mitWerten && <text className="wert" x={x(i)} y={y(w) - 9} textAnchor="middle">{format(lang, w, r)}</text>}
                </g>
              );
            })}
          </g>
        );
      })}
      {daten.map((d, i) => i % jede === 0 && (
        <text key={i} className="kategorie" x={x(i)} y={U + 20} textAnchor="middle">{kurz(String(d[spec.xKey!] ?? ""), 12)}</text>
      ))}
    </svg>
  );
}

function Streuung({ spec, daten, reihen, lang }: Teil) {
  const H = 320, L = 64, R = B - 16, O = 16, U = H - 44;
  const punkte = daten.map((d) => ({ x: zahl(d[spec.xKey ?? ""]), y: zahl(d[reihen[0].dataKey]) }))
    .filter((p): p is { x: number; y: number } => p.x !== null && p.y !== null);
  if (!punkte.length) return null;
  const sx = skala(punkte.map((p) => p.x), false);
  const sy = skala(punkte.map((p) => p.y), false);
  const x = (w: number) => L + ((w - sx.unten) / (sx.oben - sx.unten)) * (R - L);
  const y = (w: number) => U - ((w - sy.unten) / (sy.oben - sy.unten)) * (U - O);
  return (
    <svg viewBox={`0 0 ${B} ${H}`} role="img">
      <Achse y={y} ticks={sy.ticks} links={L} rechts={R} lang={lang} reihe={reihen[0]} />
      {sx.ticks.map((t) => <text key={t} className="kategorie" x={x(t)} y={U + 20} textAnchor="middle">{format(lang, t)}</text>)}
      {punkte.map((p, i) => <circle key={i} cx={x(p.x)} cy={y(p.y)} r={4} fill="#1c1c1c" fillOpacity={0.7} />)}
      {spec.xAxisLabel && <text className="kategorie" x={(L + R) / 2} y={H - 4} textAnchor="middle">{spec.xAxisLabel}</text>}
    </svg>
  );
}

function Ring({ spec, daten, lang }: { spec: Spec; daten: Record<string, unknown>[]; lang: string }) {
  const name = spec.nameKey ?? spec.xKey ?? "";
  const schluessel = spec.valueKey ?? spec.series?.[0]?.dataKey ?? "";
  const teile = daten.map((d) => ({ name: String(d[name] ?? ""), w: zahl(d[schluessel]) ?? 0 })).filter((t) => t.w > 0);
  const summe = teile.reduce((a, t) => a + t.w, 0);
  if (!summe) return null;
  const H = Math.max(200, 28 * teile.length + 24), M = 110, r = 90;
  let winkel = -Math.PI / 2;
  return (
    <svg viewBox={`0 0 ${B} ${H}`} role="img">
      {teile.map((t, i) => {
        const anteil = t.w / summe;
        const a0 = winkel;
        winkel += anteil * 2 * Math.PI;
        const gross = anteil > 0.5 ? 1 : 0;
        const p = (a: number, rr: number) => `${M + rr * Math.cos(a)},${H / 2 + rr * Math.sin(a)}`;
        const ri = r * 0.58;
        const d = anteil >= 0.9999
          ? `M ${p(0, r)} A ${r} ${r} 0 1 1 ${p(Math.PI, r)} A ${r} ${r} 0 1 1 ${p(0, r)} Z ` +
            `M ${p(0, ri)} A ${ri} ${ri} 0 1 0 ${p(Math.PI, ri)} A ${ri} ${ri} 0 1 0 ${p(0, ri)} Z`
          : `M ${p(a0, r)} A ${r} ${r} 0 ${gross} 1 ${p(winkel, r)} L ${p(winkel, r * 0.58)} A ${r * 0.58} ${r * 0.58} 0 ${gross} 0 ${p(a0, r * 0.58)} Z`;
        return (
          <g key={i}>
            <path d={d} fillRule="evenodd" fill={FARBEN[i % FARBEN.length]} stroke="#fff" strokeWidth={1} />
            <rect x={260} y={12 + i * 28} width={10} height={10} fill={FARBEN[i % FARBEN.length]} />
            <text className="kategorie" x={280} y={21 + i * 28}>{kurz(t.name, 34)}</text>
            <text className="wert" x={B - 8} y={21 + i * 28} textAnchor="end">
              {`${format(lang, t.w, spec.series?.[0])} · ${format(lang, Math.round(anteil * 1000) / 10)} %`}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
