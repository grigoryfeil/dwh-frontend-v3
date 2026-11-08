// Vorgeladen in jeden Node-Prozess der Modell-Shell (NODE_OPTIONS über shell_environment_policy in codex-config.toml).
// Die Sandbox verbietet die Socketpaare, die Node für eine Eingabe-Pipe anlegt: spawnSync ohne eigene stdio-Angabe
// scheitert mit EPERM, unter anderem im Build der Data App des Plugins. Ohne Eingabe wird stdin deshalb ignoriert,
// eine Eingabe läuft über eine Datei. Ausgabe und Fehlerausgabe bleiben Pipes, die die Sandbox erlaubt.
// Befund: Lauf 20261108-172458, alle fünf Dashboard-Gespräche, jedes Modell baute dafür einen eigenen Umweg.
"use strict";
const cp = require("node:child_process");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");

const original = cp.spawnSync;
cp.spawnSync = function spawnSync(befehl, args, optionen) {
  if (!Array.isArray(args) && args && typeof args === "object") {
    optionen = args;
    args = [];
  }
  optionen = optionen || {};
  if (optionen.stdio !== undefined) return original.call(this, befehl, args, optionen);
  const { input, ...rest } = optionen;
  let eingabe = "ignore";
  let ordner = null;
  if (input !== undefined) {
    ordner = fs.mkdtempSync(path.join(os.tmpdir(), "spawn-"));
    const datei = path.join(ordner, "stdin");
    fs.writeFileSync(datei, input);
    eingabe = fs.openSync(datei, "r");
  }
  try {
    return original.call(this, befehl, args, { ...rest, stdio: [eingabe, "pipe", "pipe"] });
  } finally {
    if (typeof eingabe === "number") fs.closeSync(eingabe);
    if (ordner) fs.rmSync(ordner, { recursive: true, force: true });
  }
};
require("node:module").syncBuiltinESMExports();
