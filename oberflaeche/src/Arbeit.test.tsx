import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ArbeitAbschnitt, type Zug } from "./Ansichten";

// Rollliste der Analystenschritte (0.7.2): folgt neuen Schritten, außer jemand hat selbst nach oben gerollt
const zug = (n: number): Zug =>
  ({ id: 1, frage: "Wie viele?", zeit: new Date(), verify: false,
     runde: { frage: "Wie viele?", schritte: Array.from({ length: n }, (_, i) => ({ s: i, text: `Schritt ${i}` })) } }) as unknown as Zug;

describe("Rollliste der Schritte", () => {
  let ort: HTMLElement;
  let root: Root;
  let gerollt: number[];

  beforeEach(() => {
    vi.stubGlobal("IS_REACT_ACT_ENVIRONMENT", true);
    vi.stubGlobal("matchMedia", () => ({ matches: true }));
    gerollt = [];
    Element.prototype.scrollTo = function (this: Element, o?: ScrollToOptions | number) {
      if (this.classList.contains("schritt-liste")) gerollt.push(typeof o === "object" ? (o.top ?? 0) : 0);
    } as typeof Element.prototype.scrollTo;
    ort = document.body.appendChild(document.createElement("div"));
    root = createRoot(ort);
  });

  afterEach(() => {
    act(() => root.unmount());
    ort.remove();
    vi.unstubAllGlobals();
  });

  const zeige = (n: number) => act(() => root.render(<ArbeitAbschnitt zug={zug(n)} sekunden={10} onAbbrechen={() => {}} />));

  function rolleAuf(scrollTop: number) {
    const f = ort.querySelector(".schritt-liste") as HTMLElement;
    Object.defineProperty(f, "scrollHeight", { configurable: true, value: 400 });
    Object.defineProperty(f, "clientHeight", { configurable: true, value: 188 });
    f.scrollTop = scrollTop;
    act(() => f.dispatchEvent(new Event("scroll")));
    return f;
  }

  it("zeigt eine Linie statt der Platzhalterzeilen und zwei Rolllisten", async () => {
    await zeige(3);
    expect(ort.querySelectorAll(".laeuft")).toHaveLength(1);
    expect(ort.querySelector(".satz")).toBeNull();
    expect(ort.querySelector('[aria-label="Stages"]')).not.toBeNull();
    expect(ort.querySelectorAll(".schritt-liste .schritt")).toHaveLength(3);
  });

  it("folgt neuen Schritten, solange niemand nach oben gerollt hat", async () => {
    await zeige(3);
    gerollt = [];
    rolleAuf(212); // unten
    await zeige(4);
    expect(gerollt).toHaveLength(1);
  });

  it("bleibt stehen, wenn jemand nach oben gerollt hat, und blendet oben aus", async () => {
    await zeige(3);
    const f = rolleAuf(40);
    expect(f.classList.contains("ausblenden")).toBe(true);
    gerollt = [];
    await zeige(4);
    expect(gerollt).toHaveLength(0);
    rolleAuf(212); // wieder unten: folgt wieder
    await zeige(5);
    expect(gerollt).toHaveLength(1);
  });
});
