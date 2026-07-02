// First-run bootstrap: fetch the official, checksum-pinned uv binary from Astral's
// GitHub release into the user cache. Runs from the launcher (never postinstall —
// installs with --ignore-scripts must still work). Offline or unsupported platform
// resolves to null and the launcher falls through to its other engines.
"use strict";

const crypto = require("crypto");
const fs = require("fs");
const os = require("os");
const path = require("path");
const zlib = require("zlib");
const { spawnSync } = require("child_process");

const MANIFEST = require("../uv-manifest.json");

function platformKey() {
  const { platform, arch } = process;
  if (platform === "darwin") return arch === "arm64" ? "darwin-arm64" : "darwin-x64";
  if (platform === "win32") {
    if (arch === "x64") return "win32-x64";
    if (arch === "arm64") return "win32-arm64";
    if (arch === "ia32") return "win32-ia32";
    return null;
  }
  if (platform === "linux") {
    // glibcVersionRuntime is absent on musl (Alpine et al).
    let musl = false;
    try {
      musl = !process.report.getReport().header.glibcVersionRuntime;
    } catch {
      musl = fs.existsSync("/etc/alpine-release");
    }
    const libc = musl ? "musl" : "gnu";
    if (arch === "x64") return `linux-x64-${libc}`;
    if (arch === "arm64") return `linux-arm64-${libc}`;
  }
  return null;
}

function cachedUvPath() {
  const cacheRoot = process.env.XDG_CACHE_HOME || path.join(os.homedir(), ".cache");
  const dir = path.join(cacheRoot, "henxels", `uv-${MANIFEST.version}`);
  return path.join(dir, process.platform === "win32" ? "uv.exe" : "uv");
}

function findBinary(dir, name) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      const found = findBinary(full, name);
      if (found) return found;
    } else if (entry.name === name) {
      return full;
    }
  }
  return null;
}

/** Path to a verified uv binary, downloading it once if needed; null when impossible. */
async function ensureUv() {
  const exe = cachedUvPath();
  if (fs.existsSync(exe)) return exe;
  if (process.env.HENXELS_SKIP_BOOTSTRAP) return null;

  const key = platformKey();
  const entry = key && MANIFEST.assets[key];
  if (!entry) return null;

  const url = `https://github.com/astral-sh/uv/releases/download/${MANIFEST.version}/${entry.asset}`;
  process.stderr.write(
    `henxels: first run — fetching its engine (uv ${MANIFEST.version}, one time, cached)…\n`
  );

  let body;
  try {
    const response = await fetch(url, { redirect: "follow" });
    if (!response.ok) {
      process.stderr.write(`henxels: engine download got HTTP ${response.status} from GitHub\n`);
      return null;
    }
    body = Buffer.from(await response.arrayBuffer());
  } catch (error) {
    // offline, proxy, DNS… — say why, then let the launcher try its fallbacks
    process.stderr.write(`henxels: engine download failed (${error.cause || error.message})\n`);
    return null;
  }

  const digest = crypto.createHash("sha256").update(body).digest("hex");
  if (digest !== entry.sha256) {
    throw new Error(
      `henxels: checksum mismatch for ${entry.asset} — expected ${entry.sha256}, got ${digest}. ` +
        "Refusing to run it. Retry; if it persists, report this immediately."
    );
  }

  const dir = path.dirname(exe);
  const staging = fs.mkdtempSync(path.join(os.tmpdir(), "henxels-uv-"));
  try {
    // Decompress .tar.gz ourselves (node's zlib) so GNU tar never needs a gzip
    // binary on PATH; .zip goes to tar as-is — bsdtar on Windows reads zips.
    let archive = path.join(staging, entry.asset);
    if (entry.asset.endsWith(".tar.gz")) {
      body = zlib.gunzipSync(body);
      archive = archive.slice(0, -3);
    }
    fs.writeFileSync(archive, body);
    // bsdtar ships with macOS, Linux distros, and Windows 10+ — and reads .zip too.
    const extracted = spawnSync("tar", ["-xf", archive, "-C", staging], { stdio: ["ignore", "ignore", "inherit"] });
    if (extracted.status !== 0) {
      process.stderr.write("henxels: couldn't extract the engine archive (is `tar` available?)\n");
      return null;
    }
    const binary = findBinary(staging, path.basename(exe));
    if (!binary) {
      process.stderr.write("henxels: engine archive had an unexpected layout\n");
      return null;
    }
    fs.mkdirSync(dir, { recursive: true });
    fs.copyFileSync(binary, exe);
    if (process.platform !== "win32") fs.chmodSync(exe, 0o755);
    return exe;
  } finally {
    fs.rmSync(staging, { recursive: true, force: true });
  }
}

module.exports = { ensureUv, platformKey, cachedUvPath };
