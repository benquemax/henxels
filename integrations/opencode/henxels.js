// henxels plugin for OpenCode.
// Place at .opencode/plugins/henxels.js (project) or ~/.config/opencode/plugins/.
//
// After the agent writes/edits a file, run `henxels check` on it; if a henxel holds
// the change back, throw so OpenCode surfaces it to the agent (which fixes next turn).
// The git hooks still enforce at commit — this just makes the agent aware earlier.
//
// We use tool.execute.after so the file exists and content checks (frontmatter,
// markdown_lint) are valid. (If you only want steering, swap to tool.execute.before
// and call `explain` instead of `check`.)

import { execFileSync } from "node:child_process"

function henxels(args, cwd) {
  // Resolve henxels: global first, else the project's uv environment.
  try {
    return execFileSync("henxels", args, { cwd, encoding: "utf8" })
  } catch (e) {
    if (e.code === "ENOENT") {
      return execFileSync("uv", ["run", "henxels", ...args], { cwd, encoding: "utf8" })
    }
    throw e // non-zero exit (a held henxel) lands here with stdout/stderr populated
  }
}

export const HenxelsPlugin = async ({ project }) => {
  const cwd = project?.worktree || process.cwd()
  return {
    "tool.execute.after": async (input, output) => {
      if (!["edit", "write"].includes(input.tool)) return
      const filePath = output?.args?.filePath
      if (!filePath) return
      try {
        henxels(["check", filePath], cwd)
      } catch (e) {
        const detail = (e.stdout || "") + (e.stderr || "")
        throw new Error(`henxels held this change to ${filePath}:\n${detail || e.message}`)
      }
    },
  }
}
