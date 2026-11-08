// Schnittstelle zu dwh_v2/web.py. Schreibende Anfragen nur als JSON (Schutz in der Middleware).
import type { Beleg } from "./antwort";

export type Stufe = { stufe: string; status: "erledigt" | "aktiv" | "offen" | "uebersprungen" };
export type Schritt = { s: number; text: string };
export type Datei = { name: string; url: string };
export type Pruefung = { status: "bestaetigt" | "korrigiert" | "hinweis" | "gescheitert"; hinweis?: string | null; ms?: number };
export type Runde = {
  frage: string;
  verifizieren?: boolean;
  schnell?: boolean;
  antwort?: string;
  ms?: number;
  zeit?: string; // Beginn der Runde, gesetzt vom Server
  dateien?: Datei[];
  abfragen?: { sql: string; fehler: boolean }[]; // SQL der Runde für den Quellenbeleg
  beleg?: Beleg[]; // Quellenbeleg der Anwendung (dwh_v2/beleg.py), seit 0.5.0 statt des Belegs vom Modell
  pruefung?: Pruefung;
  fehler?: string;
  abgebrochen?: boolean;
  stufen?: Stufe[];
  schritte?: Schritt[];
  sekunden?: number;
};
export type Stand = { status: "laeuft" | "fertig" | "fehler"; runden: Runde[] };
export type Info = { datenstand: string | null; version: string; zeitlimit: number; definitionen_vorlaeufig?: boolean };

export class Abgemeldet extends Error {}
export class Netzfehler extends Error {} // keine Verbindung, Gateway-Fehler oder Drossel: später erneut
export class Antwortfehler extends Error {
  constructor(readonly status: number, readonly detail: string, readonly warte?: number) {
    super(detail);
  }
}

async function anfrage(url: string, init?: RequestInit): Promise<Response> {
  let r: Response;
  try {
    r = await fetch(url, { credentials: "same-origin", ...init });
  } catch {
    throw new Netzfehler();
  }
  if (r.status === 401 && url !== "/api/anmelden") throw new Abgemeldet();
  if (r.status === 502 || r.status === 504 || (r.status === 429 && url !== "/api/anmelden")) throw new Netzfehler();
  if (!r.ok) {
    const inhalt = await r.json().catch(() => ({}));
    throw new Antwortfehler(r.status, String(inhalt.detail ?? r.status), Number(r.headers.get("Retry-After")) || undefined);
  }
  return r;
}

const json = (body: unknown): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export const info = async (): Promise<Info> => (await anfrage("/api/stand")).json();
export const ich = async (): Promise<{ email: string; ablage: boolean }> => (await anfrage("/api/ich")).json();
export const anmelden = async (email: string, passwort: string) => (await anfrage("/api/anmelden", json({ email, passwort }))).json();
// schnell: geringerer Denkaufwand nur für die Antwort, der Verifier prüft immer gründlich (dwh_v2/web.py)
export type Optionen = { verifizieren: boolean; speichern: boolean; schnell: boolean };
export const fragen = async (text: string, gespraech: string | null, optionen: Optionen): Promise<{ gespraech: string }> =>
  (await anfrage("/api/fragen", json({ text, gespraech, ...optionen }))).json();
// Beta-Funktionen (Schritt 6.1), Rückbau vor dem Rollout
export const speichern = (gespraech: string, an: boolean) => anfrage(`/api/gespraeche/${gespraech}/speichern`, json({ an }));
export const feedback = (text: string, gespraech: string | null, mitsenden: boolean) =>
  anfrage("/api/feedback", json({ text, gespraech, mitsenden }));
// Export kommt vom Backend (ein Download aus dem Rahmen ist gesperrt) und wird als Datei gespeichert
export async function exportieren(art: "pdf" | "xlsx", gespraeche: string[]): Promise<string> {
  const r = await anfrage(`/api/export.${art}?gespraeche=${gespraeche.map(encodeURIComponent).join(",")}`);
  const name = /filename="([^"]+)"/.exec(r.headers.get("Content-Disposition") ?? "")?.[1] ?? `SAE-Data-Desk.${art}`;
  const url = URL.createObjectURL(await r.blob());
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 60000);
  return name;
}
export const stand = async (gespraech: string): Promise<Stand> => (await anfrage(`/api/gespraeche/${gespraech}`)).json();
// Beta: gespeicherter Beispieldialog zum Lesen (Abnahme 6.8)
export const beispiel = async (name: string): Promise<Runde[]> =>
  (await (await anfrage(`/api/beispiele/${encodeURIComponent(name)}`)).json()).runden;
export const abbrechen = (gespraech: string) => anfrage(`/api/gespraeche/${gespraech}/abbrechen`, json({}));
export const beenden = (gespraech: string) =>
  anfrage(`/api/gespraeche/${gespraech}`, { method: "DELETE", headers: { "Content-Type": "application/json" } });

// Titel eines Dashboards: Das Backend liefert HTML außerhalb des Rahmens als Quelltext, der hier nichts ausführt
export async function dashboardTitel(url: string): Promise<string | null> {
  try {
    const r = await fetch(url, { credentials: "same-origin" });
    if (!r.ok) return null;
    const t = /<title[^>]*>([^<]{1,200})<\/title>/i.exec(await r.text());
    const titel = t ? new DOMParser().parseFromString(t[1], "text/html").documentElement.textContent?.trim() : "";
    return titel || null;
  } catch {
    return null;
  }
}
