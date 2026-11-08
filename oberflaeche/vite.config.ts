import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Der Build landet in web/ und wird eingecheckt: Der VPS liefert ihn aus, ohne npm.
// Während der Entwicklung leitet der Dev-Server /api an ein lokales Backend weiter.
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: "../web/statisch",
    emptyOutDir: true,
    assetsInlineLimit: 0, // keine data:-URIs, die Seiten-CSP erlaubt Schriften nur von 'self'
    modulePreload: { polyfill: false },
  },
  server: { proxy: { "/api": "http://127.0.0.1:9171" } },
  test: { environment: "jsdom" },
});
