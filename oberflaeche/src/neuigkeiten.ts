// Changelog für die Beta-Tester, geöffnet im Fenster „Beta features“. Englisch wie die Oberfläche und getrennt vom
// technischen CHANGELOG.md: nur, was Tester sehen oder bemerken. Neue Einträge oben.
export type Neuigkeit = { version: string; datum: string; titel: string; text: string };

export const NEUIGKEITEN: Neuigkeit[] = [
  {
    version: "0.8.0",
    datum: "10 November 2026",
    titel: "Beta release for testing",
    text: "First version for beta testers: questions in plain language, follow-ups, Verify, and export as PDF or Excel.",
  },
];
