#!/usr/bin/env bash
# Generic henxels glue for any harness that can run a shell command around a tool call.
# Point your harness's "before a file write" hook here with the target path:
#
#     henxels-steer.sh explain <path>     # steer: print the rules for that path
#     henxels-steer.sh check   <path>     # enforce: exit 1 if the file violates a henxel
#
# Use `explain` before a write (path-based: catches wrong name / wrong place / forbidden)
# and `check` after a write (also checks content: frontmatter, markdown_lint, …).
# Whatever your harness supports, the git hooks `henxels init` installed still enforce
# the whole contract at commit/push — this is just earlier, in-loop awareness.

mode="${1:-check}"
path="${2:-}"
[ -z "$path" ] && { echo "usage: henxels-steer.sh <explain|check> <path>" >&2; exit 0; }

if command -v henxels >/dev/null 2>&1; then HX=(henxels)
elif command -v uv >/dev/null 2>&1 && [ -f pyproject.toml ]; then HX=(uv run henxels)
else HX=(python3 -m henxels); fi

rel="$(python3 -c 'import os,sys; print(os.path.relpath(sys.argv[1]))' "$path" 2>/dev/null || echo "$path")"
exec "${HX[@]}" "$mode" "$rel"
