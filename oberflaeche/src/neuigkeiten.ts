// Changelog für die Beta-Tester, geöffnet im Fenster „Beta features“. Englisch wie die Oberfläche und getrennt vom
// technischen CHANGELOG.md: nur, was Tester sehen oder bemerken. Neue Einträge oben.
export type Neuigkeit = { version: string; datum: string; titel: string; text: string };

export const NEUIGKEITEN: Neuigkeit[] = [
  {
    version: "0.8.0",
    datum: "10 November 2026",
    titel: "Beta release for testing",
    text:
      "First version of SAE Data Desk for beta testers. Ask questions about students, enrolments, the sales funnel and " +
      "study progress in plain language, follow up in the same conversation, check answers with Verify and export " +
      "them as a PDF report or Excel file.",
  },
];
