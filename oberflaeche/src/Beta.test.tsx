import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { BetaMenue } from "./Ansichten";

// Changelog für die Tester im Fenster „Beta features“ (0.8.0)
describe("Changelog im Beta-Fenster", () => {
  let ort: HTMLElement;
  let root: Root;

  beforeEach(() => {
    vi.stubGlobal("IS_REACT_ACT_ENVIRONMENT", true);
    ort = document.body.appendChild(document.createElement("div"));
    root = createRoot(ort);
  });

  afterEach(() => {
    act(() => root.unmount());
    ort.remove();
    vi.unstubAllGlobals();
  });

  const knopf = (text: string) => [...ort.querySelectorAll("button")].find((b) => b.querySelector("b")?.textContent === text || b.textContent?.trim() === text);

  for (const ablage of [true, false]) {
    it(`öffnet den Changelog und kehrt zurück (Ablage ${ablage ? "an" : "aus"})`, () => {
      act(() =>
        root.render(
          <BetaMenue ablage={ablage} speichern gespraech={false} onSpeichern={() => {}} onFeedback={async () => null} onSchliessen={() => {}} />,
        ),
      );
      act(() => knopf("Changelog")!.click());
      expect(ort.textContent).toContain("0.8.0 · 10 November 2026");
      expect(ort.textContent).toContain("Beta release for testing");
      expect(ort.querySelector(".beta-feedback")).toBeNull();
      act(() => knopf("Back")!.click());
      expect(ort.textContent).toContain("Beta features");
      expect(ort.querySelector(".changelog")).toBeNull();
    });
  }
});
