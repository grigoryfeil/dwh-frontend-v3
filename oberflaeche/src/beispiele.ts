// Menü „Examples“ (Grigory 04.11.): zeigt, welche Darstellungen möglich sind, nicht welche Inhalte. Ein Klick setzt
// die Frage ins Eingabefeld, ohne sie abzuschicken. Keine Zahlen in den Fragen. Am 10.11.2026 gegen V3 0.6.6 geprüft:
// jede Frage antwortet ohne Rückfrage, das Dashboard in wenigen Minuten.
export type Beispiel = { art: string; hinweis: string; frage: string; folge?: boolean };

export const BEISPIELE: Beispiel[] = [
  {
    art: "Short answer",
    hinweis: "One figure, put in context",
    frage: "Wie hoch ist der aktuelle Studierendenbestand im Vergleich zum Vorjahr?",
  },
  {
    art: "Chart",
    hinweis: "A development over time",
    frage: "Zeig die Opportunities des laufenden Intakes Woche für Woche im Vorjahresvergleich (PCP) als Diagramm.",
  },
  {
    art: "Comparison",
    hinweis: "Campus, products or intakes side by side",
    frage: "Vergleiche die Konversionsrate Opportunity → Enrollment der Campus im letzten abgeschlossenen Intake.",
  },
  {
    art: "Follow-up",
    hinweis: "Refines the previous answer",
    frage: "Wie sieht das ohne Top-ups aus, aufgeteilt nach Campus?",
    folge: true,
  },
  {
    art: "Interactive dashboard",
    hinweis: "Charts and filters, a few minutes",
    frage: "Erstelle ein interaktives Dashboard zu den neuen Leads je Monat im laufenden Jahr, filterbar nach Campus.",
  },
];
