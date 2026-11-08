// Menü „Examples“ (Grigory 04.11.): zeigt, welche Darstellungen möglich sind, nicht welche Inhalte. Ein Klick setzt
// die Frage ins Eingabefeld, ohne sie abzuschicken. Begriffe aus firmenbild/kern.md, keine Zahlen aus der Kopie.
export type Beispiel = { art: string; hinweis: string; frage: string; folge?: boolean };

export const BEISPIELE: Beispiel[] = [
  {
    art: "Short answer",
    hinweis: "One figure, put in context",
    frage: "Wie viele Neueinschreibungen hat der laufende Intake bisher, gemessen am Ziel?",
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
    frage: "Erstelle ein interaktives Dashboard zum laufenden Intake: Opportunities und Enrollments je Campus im Vorjahresvergleich, filterbar nach Produkt.",
  },
];
