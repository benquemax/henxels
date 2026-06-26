#!/usr/bin/env bash
# henxels hook for Claude Code. Wire it via settings.json (see settings.example.json).
#
#   PreToolUse  (mode: explain) -> steer: print the henxels governing the target path
#                                  so the agent writes the right thing the first time.
#   PostToolUse (mode: check)   -> enforce: run `henxels check` on the written file;
#                                  exit 2 blocks and feeds the violation back to Claude.
#
# Reads the tool-call JSON on stdin (Claude Code passes it). Resolves henxels whether
# it's global or only in a project venv.

mode="${1:-check}"

if command -v henxels >/dev/null 2>&1; then HX=(henxels)
elif command -v uv >/dev/null 2>&1 && [ -f pyproject.toml ]; then HX=(uv run henxels)
else HX=(python3 -m henxels); fi

path="$(python3 - <<'PY' 2>/dev/null || true
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    print(""); sys.exit(0)
print((d.get("tool_input") or {}).get("file_path", ""))
PY
)"
[ -z "$path" ] && exit 0

# Make repo-relative (henxels speaks repo paths).
rel="$(python3 -c 'import os,sys; print(os.path.relpath(sys.argv[1]))' "$path" 2>/dev/null || echo "$path")"

if [ "$mode" = "explain" ]; then
  "${HX[@]}" explain "$rel" 2>/dev/null || true
  exit 0
fi

if ! out="$("${HX[@]}" check "$rel" 2>&1)"; then
  echo "henxels held this change to $rel:" >&2
  echo "$out" >&2
  exit 2   # blocks the tool; Claude sees stderr and can fix
fi
exit 0
