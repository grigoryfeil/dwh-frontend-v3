import { afterEach, describe, expect, it, vi } from "vitest";
import { fragen } from "./api";
import { BEISPIELE } from "./beispiele";

describe("Beispielfragen", () => {
  it("zeigen die Darstellungsarten, darunter das interaktive Dashboard", () => {
    expect(BEISPIELE.map((b) => b.art)).toEqual(["Short answer", "Chart", "Comparison", "Follow-up", "Interactive dashboard"]);
    expect(BEISPIELE.at(-1)!.frage).toMatch(/interaktives Dashboard/);
  });

  it("nennen keine Zahlen aus der Kopie", () => {
    for (const b of BEISPIELE) expect(b.frage).not.toMatch(/\d/);
  });
});

describe("Optionen einer Frage", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("geht mit der Frage an den Server", async () => {
    const abruf = vi.fn(async () => new Response(JSON.stringify({ gespraech: "g" })));
    vi.stubGlobal("fetch", abruf);
    await fragen("Wie viele?", null, { verifizieren: true, speichern: false });
    const [, init] = abruf.mock.calls[0] as unknown as [string, RequestInit];
    expect(JSON.parse(String(init.body))).toEqual({
      text: "Wie viele?",
      gespraech: null,
      verifizieren: true,
      speichern: false,
    });
  });
});
