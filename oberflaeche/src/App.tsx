// Zustand und Abläufe: Anmeldung, Frage, Fortschritt, Abbruch, Fehler, Zurücksetzen. Nichts bleibt über das
// Neuladen hinaus, es gibt keinen Verlauf (Briefing). Fortschritt kommt nur vom Server, nie geschätzt.
import { useCallback, useEffect, useRef, useState } from "react";
import * as api from "./api";
import { Abgemeldet, Antwortfehler, Netzfehler, type Info } from "./api";
import {
  AntwortAbschnitt, ArbeitAbschnitt, Banner, BeispielMenue, BetaMenue, DashboardOverlay, Exportmenue, FrageAbschnitt, Folge, Fuss, Kopf, Leer, Login,
  ResetDialog, Toast, Unterbrochen, type Overlay, type Zug,
} from "./Ansichten";
import { datum, uhrzeit } from "./format";

const TAKT = 2000; // Abfrage des Stands, wie bisher
const TAKT_OHNE_NETZ = 5000;
const warte = (ms: number) => new Promise((weiter) => setTimeout(weiter, ms));
const TABELLE = /\n\s*\|?\s*:?-{3,}:?\s*\|/;
const DIAGRAMM = /genui\s*\{\s*"charts_widget_v2"/; // Excel trägt auch die Werte der Diagramme

export default function App() {
  const [phase, setPhase] = useState<"laden" | "login" | "app">("laden");
  const [info, setInfo] = useState<Info>({ datenstand: null, version: "", zeitlimit: 600 });
  const [loginMeldung, setLoginMeldung] = useState("");
  const [zuege, setZuege] = useState<Zug[]>([]);
  const [entwurf, setEntwurf] = useState("");
  const [fokus, setFokus] = useState(0); // jede Erhöhung setzt den Cursor ins Eingabefeld
  const [verify, setVerify] = useState(false);
  const [banner, setBanner] = useState(false);
  const [overlay, setOverlay] = useState<Overlay | null>(null);
  const [dialog, setDialog] = useState(false);
  const [menue, setMenue] = useState<"beispiele" | "export" | "beta" | null>(null); // höchstens eins offen
  const [ablage, setAblage] = useState(false); // Beta: Ablage auf dem Server eingeschaltet
  const [speichern, setSpeichern] = useState(true); // Beta: je Gespräch, standardmäßig an
  const [toast, setToast] = useState<{ titel: string; text: string } | null>(null);
  const [jetzt, setJetzt] = useState(Date.now());

  const gespraech = useRef<string | null>(null);
  const lauf = useRef(0); // jede neue Verfolgung und jedes Zurücksetzen beendet die vorige
  const zaehler = useRef(0);
  const letzteFrage = useRef<HTMLElement>(null);
  const toastZeit = useRef<number>(undefined);

  const laufend = zuege.find((z) => !z.fertig && !z.fehler);
  const blaetter = zuege.filter((z) => z.fertig && !z.fehler && (TABELLE.test(z.runde?.antwort ?? "") || DIAGRAMM.test(z.runde?.antwort ?? ""))).length;
  // Kriterium 5: fester Hinweis, bis der Katalog freigegeben ist
  const meta = [datum(info.datenstand) && `Data as of ${datum(info.datenstand)}`, info.definitionen_vorlaeufig && "Definitions provisional",
    info.version && `V3 ${info.version}`].filter(Boolean).join(" · ");

  const aendere = useCallback((id: number, teil: Partial<Zug>) => {
    setZuege((zs) => zs.map((z) => (z.id === id ? { ...z, ...teil } : z)));
  }, []);

  const allesLeeren = useCallback(() => {
    lauf.current++;
    gespraech.current = null;
    setZuege([]);
    setEntwurf("");
    setVerify(false);
    setBanner(false);
    setOverlay(null);
    setDialog(false);
    setMenue(null);
    setSpeichern(true);
    setToast(null);
  }, []);

  const abgemeldet = useCallback(() => {
    allesLeeren();
    setLoginMeldung("Your session has ended. Please sign in again.");
    setPhase("login");
  }, [allesLeeren]);

  // Beta: Mit ?beispiel=<name> zeigt die Seite einen gespeicherten Dialog zum Lesen (Abnahme 6.8)
  const zeigeBeispiel = useCallback(async () => {
    const name = new URLSearchParams(window.location.search).get("beispiel");
    if (!name) return;
    try {
      const runden = await api.beispiel(name);
      setZuege(
        runden.map((r) => {
          const zeit = new Date(r.zeit ?? Date.now());
          return { id: ++zaehler.current, frage: r.frage, zeit, verify: false, runde: r, fertig: new Date(zeit.getTime() + (r.ms ?? 0)) };
        }),
      );
      zeigeToast("Saved example", "Read only. A new question starts a new conversation.");
    } catch (e) {
      if (e instanceof Abgemeldet) return abgemeldet();
      zeigeToast("Example not found", "Please check the link.");
    }
  }, [abgemeldet]);

  useEffect(() => {
    api.info().then(setInfo, () => {});
    api.ich().then(
      (i) => {
        setAblage(i.ablage);
        setPhase("app");
        void zeigeBeispiel();
      },
      () => setPhase("login"),
    );
  }, []);

  // Laufzeit sekundengenau, solange gearbeitet wird
  useEffect(() => {
    if (!laufend) return;
    setJetzt(Date.now());
    const t = setInterval(() => setJetzt(Date.now()), 1000);
    return () => clearInterval(t);
  }, [laufend?.id]);

  // Esc schließt Dashboard, Exportmenü und Dialog
  useEffect(() => {
    const taste = (e: KeyboardEvent) => {
      if (e.key !== "Escape") return;
      setOverlay(null);
      setMenue(null);
      setDialog(false);
    };
    window.addEventListener("keydown", taste);
    return () => window.removeEventListener("keydown", taste);
  }, []);

  // Neue Frage oben ins Bild
  const anzahl = zuege.length;
  useEffect(() => {
    const ruhig = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    letzteFrage.current?.scrollIntoView({ block: "start", behavior: ruhig ? "auto" : "smooth" });
  }, [anzahl]);

  function schalteSpeichern() {
    const an = !speichern;
    setSpeichern(an);
    // Ohne Gespräch gilt der Schalter ab der ersten Frage, scheitert die Anfrage, bringt ihn die nächste Frage mit
    if (gespraech.current) api.speichern(gespraech.current, an).catch((e) => e instanceof Abgemeldet && abgemeldet());
  }

  async function sendeFeedback(text: string, mitsenden: boolean): Promise<string | null> {
    try {
      await api.feedback(text, gespraech.current, mitsenden);
    } catch (e) {
      if (e instanceof Abgemeldet) {
        abgemeldet();
        return null;
      }
      if (e instanceof Antwortfehler && e.status === 404) return "This conversation is no longer available. Untick it and send again.";
      return "Feedback could not be sent. Please try again.";
    }
    schliesse("beta");
    zeigeToast("Feedback sent", mitsenden ? "Thank you. The conversation was included." : "Thank you.");
    return null;
  }

  const schliesse = (art: typeof menue) => setMenue((m) => (m === art ? null : m));
  const umschalten = (art: typeof menue) => setMenue((m) => (m === art ? null : art));
  const hatErgebnis = zuege.some((z) => z.fertig && !z.fehler);

  function zeigeToast(titel: string, text: string) {
    window.clearTimeout(toastZeit.current);
    schliesse("export");
    setToast({ titel, text });
    toastZeit.current = window.setTimeout(() => setToast(null), 5000);
  }

  // Alle Gespräche des Verlaufs: Nach einem Fehler beginnt die nächste Frage ein neues
  async function exportiere(art: "pdf" | "xlsx") {
    schliesse("export");
    const kennungen = [...new Set(zuege.filter((z) => z.fertig && !z.fehler && z.gespraech).map((z) => z.gespraech!))];
    try {
      const name = await api.exportieren(art, kennungen);
      if (art === "pdf") zeigeToast("PDF report ready", name);
      else zeigeToast("Excel file ready", `${name} · ${blaetter} ${blaetter === 1 ? "sheet" : "sheets"}`);
    } catch (e) {
      if (e instanceof Abgemeldet) return abgemeldet();
      zeigeToast("Export failed", e instanceof Netzfehler ? "The connection dropped. Please try again." : "The file could not be created. Please try again.");
    }
  }

  async function verfolge(kennung: string, id: number) {
    const meins = ++lauf.current;
    let takt = TAKT;
    while (lauf.current === meins) {
      await warte(takt);
      if (lauf.current !== meins) return;
      let s: api.Stand;
      try {
        s = await api.stand(kennung);
        setBanner(false);
        takt = TAKT;
      } catch (e) {
        if (lauf.current !== meins) return;
        if (e instanceof Abgemeldet) return abgemeldet();
        if (e instanceof Netzfehler) {
          setBanner(true);
          takt = TAKT_OHNE_NETZ;
          continue;
        }
        // Gespräch unbekannt, etwa nach einem Neustart des Backends
        setBanner(false);
        gespraech.current = null;
        return aendere(id, { fehler: "verloren", fertig: new Date() });
      }
      if (lauf.current !== meins) return;
      const runde = s.runden.at(-1);
      if (s.status === "laeuft") {
        aendere(id, { runde });
        continue;
      }
      if (s.status === "fehler") gespraech.current = null; // beendet, die nächste Frage beginnt ein neues Gespräch
      if (!runde || runde.abgebrochen) {
        // zurück zum vorherigen Stand, die Frage steht wieder im Eingabefeld
        setZuege((zs) => zs.filter((z) => z.id !== id));
        setEntwurf(runde?.frage ?? "");
        return;
      }
      if (runde.fehler) return aendere(id, { fehler: runde.fehler === "Zeitlimit" ? "zeit" : "verbindung", fertig: new Date() });
      return aendere(id, { runde, fertig: new Date() });
    }
  }

  async function starte(id: number, text: string, optionen: api.Optionen) {
    try {
      let antwort: { gespraech: string };
      try {
        antwort = await api.fragen(text, gespraech.current, optionen);
      } catch (e) {
        // Gespräch inzwischen beendet: nicht still neu beginnen, eine Nachfrage ohne Verlauf ergäbe eine falsche
        // Antwort. Der Nutzer stellt sie bewusst als neue Frage (Unterbrochen, „Ask as new question“).
        if (e instanceof Antwortfehler && (e.status === 404 || e.status === 410) && gespraech.current) {
          gespraech.current = null;
          return aendere(id, { fehler: "verloren", fertig: new Date() });
        }
        throw e;
      }
      gespraech.current = antwort.gespraech;
      aendere(id, { gespraech: antwort.gespraech });
      await verfolge(antwort.gespraech, id);
    } catch (e) {
      if (e instanceof Abgemeldet) return abgemeldet();
      aendere(id, { fehler: e instanceof Antwortfehler && e.status === 503 ? "belegt" : "verbindung", fertig: new Date() });
    }
  }

  function frage(text: string, mitPruefung = verify) {
    const t = text.trim();
    if (!t || laufend) return;
    const id = ++zaehler.current;
    setZuege((zs) => [...zs, { id, frage: t, zeit: new Date(), verify: mitPruefung }]);
    setEntwurf("");
    setVerify(false); // gilt nur für die nächste Frage
    void starte(id, t, { verifizieren: mitPruefung, speichern: ablage && speichern });
  }

  function waehleBeispiel(text: string) {
    setMenue(null);
    setEntwurf(text);
    setFokus((f) => f + 1); // ins Feld, nicht abschicken. Läuft gerade eine Antwort, steht die Frage danach im Folgefeld
  }

  async function abbrechen() {
    if (!laufend || !gespraech.current) return;
    aendere(laufend.id, { abbrechen: true });
    try {
      await api.abbrechen(gespraech.current);
    } catch (e) {
      if (e instanceof Abgemeldet) abgemeldet();
      // 409: Die Runde endete schon, die Verfolgung zeigt das Ergebnis
    }
  }

  function nochmal(zug: Zug) {
    setZuege((zs) => zs.filter((z) => z.id !== zug.id));
    frage(zug.frage, zug.verify);
  }

  async function aufraeumen(kennung: string, laeuftNoch: boolean) {
    // Gespräch und Modellprozess freigeben, eine laufende Runde vorher abbrechen
    try {
      if (laeuftNoch) {
        await api.abbrechen(kennung).catch(() => undefined);
        for (let i = 0; i < 20; i++) {
          await warte(1500);
          if ((await api.stand(kennung)).status !== "laeuft") break;
        }
      }
      await api.beenden(kennung);
    } catch {
      // Sessionende oder Leerlauf räumen es im Backend ohnehin
    }
  }

  function verwerfen() {
    const kennung = gespraech.current;
    const laeuftNoch = !!laufend;
    allesLeeren();
    if (kennung) void aufraeumen(kennung, laeuftNoch);
  }

  async function anmelden(email: string, passwort: string): Promise<string | null> {
    try {
      await api.anmelden(email, passwort);
    } catch (e) {
      if (e instanceof Antwortfehler && e.status === 429) return `Too many attempts. Please try again in ${e.warte ?? 180} seconds.`;
      if (e instanceof Antwortfehler && (e.status === 401 || e.status === 422)) return "Email or password is not correct.";
      return "Sign-in is not available right now. Please try again shortly.";
    }
    allesLeeren();
    setLoginMeldung("");
    setPhase("app");
    api.info().then(setInfo, () => {});
    api.ich().then((i) => setAblage(i.ablage), () => {});
    void zeigeBeispiel();
    return null;
  }

  if (phase === "laden") return <div className="dd laden" />;
  if (phase === "login") {
    return (
      <div className="dd">
        <Login meta={meta} meldung={loginMeldung} onAnmelden={anmelden} />
      </div>
    );
  }

  const letzteId = zuege.at(-1)?.id;

  return (
    <div className="dd">
      <div className="app">
        <Kopf
          speichert={ablage && speichern}
          onBeispiele={() => umschalten("beispiele")}
          onBeta={() => umschalten("beta")}
          onExport={() => (hatErgebnis ? umschalten("export") : setMenue(null))}
          onReset={() => {
            setMenue(null);
            setDialog(true);
          }}
        />
        {banner && <Banner />}
        {zuege.length === 0 ? (
          <Leer
            entwurf={entwurf}
            fokus={fokus}
            verify={verify}
            onEntwurf={setEntwurf}
            onVerify={() => setVerify((v) => !v)}
            onFrage={() => frage(entwurf)}
          />
        ) : (
          <>
            <main className="verlauf">
              <div className="verlauf-innen">
                {zuege.map((z, i) => (
                  <div key={z.id}>
                    <FrageAbschnitt
                      n={i + 1}
                      zeit={z === laufend ? "Just now" : uhrzeit(z.zeit)}
                      text={z.frage}
                      abschnitt={z.id === letzteId ? letzteFrage : undefined}
                    />
                    {z === laufend ? (
                      <ArbeitAbschnitt zug={z} sekunden={(jetzt - z.zeit.getTime()) / 1000} onAbbrechen={abbrechen} />
                    ) : z.fehler ? (
                      <Unterbrochen zug={z} zeitlimit={info.zeitlimit} onNochmal={() => nochmal(z)} />
                    ) : (
                      <AntwortAbschnitt zug={z} n={i + 1} arbeitet={!!laufend} onOption={(o) => frage(o, false)} onDashboard={setOverlay} />
                    )}
                  </div>
                ))}
              </div>
            </main>
            <Folge
              arbeitet={!!laufend}
              entwurf={entwurf}
              fokus={fokus}
              verify={verify}
              onEntwurf={setEntwurf}
              onVerify={() => setVerify((v) => !v)}
              onFrage={() => frage(entwurf)}
            />
          </>
        )}
        <Fuss meta={meta} />
      </div>
      {menue === "export" && (
        <Exportmenue
          blaetter={blaetter}
          onPdf={() => exportiere("pdf")}
          onExcel={() => exportiere("xlsx")}
          onSchliessen={() => setMenue(null)}
        />
      )}
      {menue === "beispiele" && <BeispielMenue mitAntwort={hatErgebnis} onWahl={waehleBeispiel} onSchliessen={() => setMenue(null)} />}
      {menue === "beta" && (
        <BetaMenue
          ablage={ablage}
          speichern={speichern}
          gespraech={!!gespraech.current}
          onSpeichern={schalteSpeichern}
          onFeedback={sendeFeedback}
          onSchliessen={() => setMenue(null)}
        />
      )}
      {toast && <Toast titel={toast.titel} text={toast.text} onSchliessen={() => setToast(null)} />}
      {overlay && <DashboardOverlay overlay={overlay} onSchliessen={() => setOverlay(null)} />}
      {dialog && (
        <ResetDialog
          onAbbrechen={() => setDialog(false)}
          onExport={() => {
            setDialog(false);
            if (hatErgebnis) setMenue("export");
          }}
          onVerwerfen={verwerfen}
        />
      )}
    </div>
  );
}
