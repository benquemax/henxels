#!/usr/bin/env node
// henxels for JS repos, no Python required. The engine is Python, but this launcher
// owns getting it: it prefers engines pinned to THIS package's version (so npm and
// PyPI can never skew), bootstrapping the official checksum-pinned uv binary on first
// run — uv then provisions Python by itself on machines that have none. PATH engines
// remain as offline fallbacks, and every dead end explains the next move.
"use strict";

const { spawnSync } = require("child_process");

const { ensureUv } = require("./bootstrap.cjs");
const PIN = require("../package.json").version;

const argv = process.argv.slice(2);

function run(cmd, args) {
  const result = spawnSync(cmd, args, { stdio: "inherit" });
  if (result.error && result.error.code === "ENOENT") return null; // not installed — next
  process.exit(result.status === null ? 1 : result.status);
}

(async () => {
  // Explicit override for tests, CI, and power users: a command string we append to.
  const override = process.env.HENXELS_ENGINE;
  if (override) {
    const parts = override.split(" ").filter(Boolean);
    const result = spawnSync(parts[0], [...parts.slice(1), ...argv], { stdio: "inherit" });
    process.exit(result.status === null ? 1 : result.status);
  }

  // Pinned engines first — the version you npm-installed is the version that runs.
  run("uvx", [`henxels@${PIN}`, ...argv]);

  let uv = null;
  try {
    uv = await ensureUv();
  } catch (error) {
    process.stderr.write(`${error.message}\n`);
    process.exit(1); // a checksum mismatch must never fall through to another engine
  }
  if (uv) run(uv, ["tool", "run", `henxels@${PIN}`, ...argv]);

  // Offline fallbacks: whatever henxels the machine already has.
  run("henxels", argv);
  run("python3", ["-m", "henxels", ...argv]);
  run("python", ["-m", "henxels", ...argv]);

  process.stderr.write(
    [
      `henxels ${PIN} couldn't start: no engine found and the one-time bootstrap`,
      "(downloading uv from GitHub) didn't succeed — often that just means offline.",
      "",
      "Any one of these fixes it:",
      "  • get back online and re-run (the engine is fetched once, then cached)",
      "  • install uv:   https://docs.astral.sh/uv/",
      `  • or with Python around:  pip install henxels==${PIN}`,
      "",
    ].join("\n")
  );
  process.exit(127);
})();
