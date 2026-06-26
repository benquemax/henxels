#!/usr/bin/env node
// Thin launcher: henxels' engine is Python. This shim lets node projects run it via
// `npx henxels` without caring how Python is installed. We try, in order: a henxels
// already on PATH, uvx (zero-install), then `python -m henxels`. The first one that
// actually exists wins; if none do, we explain exactly what to install.
"use strict";

const { spawnSync } = require("child_process");

const argv = process.argv.slice(2);

const attempts = [
  ["henxels", argv],
  ["uvx", ["henxels", ...argv]],
  ["python3", ["-m", "henxels", ...argv]],
  ["python", ["-m", "henxels", ...argv]],
];

for (const [cmd, args] of attempts) {
  const result = spawnSync(cmd, args, { stdio: "inherit" });
  if (result.error && result.error.code === "ENOENT") {
    continue; // this runtime isn't installed — try the next
  }
  process.exit(result.status === null ? 1 : result.status);
}

process.stderr.write(
  [
    "henxels needs Python (it's a Python tool with a node-friendly launcher).",
    "",
    "Install it one of these ways, then re-run:",
    "  • uv (recommended):  https://docs.astral.sh/uv/   then  uvx henxels <cmd>",
    "  • pipx:              pipx install henxels",
    "  • pip:               python -m pip install henxels",
    "",
  ].join("\n")
);
process.exit(127);
