"""Regenerate npm/uv-manifest.json — the checksum-pinned uv the npm launcher bootstraps.

Run on a uv release bump:  python npm/tools/update_uv_manifest.py [tag]
Fetches the (latest by default) astral-sh/uv release and records, per platform we
support, the asset name and its official sha256. The launcher refuses any download
that doesn't match, so this file IS the supply-chain trust anchor — review its diff.
"""

from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

# npm's (process.platform, arch, libc) → uv release asset.
PLATFORMS = {
    "linux-x64-gnu": "uv-x86_64-unknown-linux-gnu.tar.gz",
    "linux-arm64-gnu": "uv-aarch64-unknown-linux-gnu.tar.gz",
    "linux-x64-musl": "uv-x86_64-unknown-linux-musl.tar.gz",
    "linux-arm64-musl": "uv-aarch64-unknown-linux-musl.tar.gz",
    "darwin-x64": "uv-x86_64-apple-darwin.tar.gz",
    "darwin-arm64": "uv-aarch64-apple-darwin.tar.gz",
    "win32-x64": "uv-x86_64-pc-windows-msvc.zip",
    "win32-arm64": "uv-aarch64-pc-windows-msvc.zip",
    "win32-ia32": "uv-i686-pc-windows-msvc.zip",
}


def _get(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "henxels-manifest-updater"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def main() -> int:
    tag = sys.argv[1] if len(sys.argv) > 1 else None
    if tag is None:
        release = json.loads(_get("https://api.github.com/repos/astral-sh/uv/releases/latest"))
        tag = release["tag_name"]

    base = f"https://github.com/astral-sh/uv/releases/download/{tag}"
    assets = {}
    for key, asset in PLATFORMS.items():
        digest = _get(f"{base}/{asset}.sha256").decode("utf-8").split()[0].lower()
        assert len(digest) == 64, f"{asset}: unexpected sha256 file format"
        assets[key] = {"asset": asset, "sha256": digest}
        print(f"  {key:18} {asset}  {digest[:12]}…")

    manifest = {"version": tag, "assets": assets}
    out = Path(__file__).resolve().parent.parent / "uv-manifest.json"
    out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"✓ {out} pinned to uv {tag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
