import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";
import "./wireframe.js"; // Würfel der Anmeldung, aus der Übergabe unverändert
import App from "./App";

createRoot(document.getElementById("app")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
