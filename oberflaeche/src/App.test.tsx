import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";

const json = (daten: unknown) => new Response(JSON.stringify(daten), { headers: { "Content-Type": "application/json" } });
const weiter = () => act(async () => void (await vi.advanceTimersByTimeAsync(0)));
const knopf = (ort: HTMLElement, text: string) =>
  [...ort.querySelectorAll("button")].find((b) => b.textContent?.trim() === text) as HTMLButtonElement | undefined;

describe("Abbruch einer laufenden Runde", () => {
  let ort: HTMLElement;
  let root: Root;

  beforeEach(() => {
    vi.useFakeTimers();
    vi.stubGlobal("IS_REACT_ACT_ENVIRONMENT", true);
    vi.stubGlobal("matchMedia", () => ({ matches: true }));
    Element.prototype.scrollIntoView = () => {};
    ort = document.body.appendChild(document.createElement("div"));
    root = createRoot(ort);
  });

  afterEach(() => {
    act(() => root.unmount());
    ort.remove();
    vi.unstubAllGlobals();
    vi.useRealTimers();
  });

  async function frageStellen(abbruch: () => Promise<Response>) {
    vi.stubGlobal("fetch", async (url: string) => {
      if (url === "/api/stand") return json({ datenstand: null, version: "0", zeitlimit: 600 });
      if (url === "/api/ich") return json({ email: "t@x", ablage: false });
      if (url === "/api/fragen") return json({ gespraech: "g" });
      if (url.endsWith("/abbrechen")) return abbruch();
      return json({ status: "laeuft", runden: [{ frage: "Wie viele?" }] });
    });
    await act(async () => root.render(<App />));
    await weiter();
    const feld = ort.querySelector("textarea")!;
    await act(async () => {
      Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value")!.set!.call(feld, "Wie viele?");
      feld.dispatchEvent(new Event("input", { bubbles: true }));
    });
    await act(async () => knopf(ort, "Ask")!.click());
    await weiter();
    await act(async () => knopf(ort, "Cancel")!.click());
    await weiter();
  }

  it("gibt den Knopf wieder frei, wenn der Abbruch den Server nicht erreicht", async () => {
    await frageStellen(async () => {
      throw new TypeError("kein Netz");
    });
    expect(knopf(ort, "Cancel")!.disabled).toBe(false);
  });

  it("lässt den Knopf gesperrt, wenn der Abbruch angenommen ist", async () => {
    await frageStellen(async () => json({ gespraech: "g" }));
    expect(knopf(ort, "Cancel")!.disabled).toBe(true);
  });
});
