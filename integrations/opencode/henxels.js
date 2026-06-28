// henxels plugin for OpenCode.
// Place at .opencode/plugins/henxels.js (project) or ~/.config/opencode/plugins/.
//
// Two things:
//  1. tool.execute.before — if the contract sets `ask_me_before_staging: true`, block
//     the agent from running `git add` / `git commit` itself (git has no pre-add hook,
//     so steering alone leaks; this is the real enforcement). Push stays guarded by the
//     henxels pre-push hook + `bless`.
//  2. tool.execute.after — after the agent writes/edits a file, run `henxels check` on
//     it; if a henxel holds the change back, throw so OpenCode surfaces it to the agent.
//
// Defensive by design: if a field isn't shaped the way we expect (OpenCode version
// drift), the hook simply does nothing rather than breaking your tools.

import { execFileSync } from "node:child_process"
import { readFileSync } from "node:fs"

const CONTRACTS = ["henxels.yaml", ".henxels.yaml", "henxels.yml", ".henxels.yml"]

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

function stagingGuarded(cwd) {
  for (const name of CONTRACTS) {
    try {
      return /ask_me_before_staging:\s*true/.test(readFileSync(`${cwd}/${name}`, "utf8"))
    } catch {} // no such contract file — try the next
  }
  return false
}

export const HenxelsPlugin = async ({ project }) => {
  const cwd = project?.worktree || process.cwd()
  return {
    "tool.execute.before": async (input) => {
      const command = input?.args?.command
      if (typeof command !== "string") return // not a shell command we can read
      if (!/\bgit\s+(?:add|commit)\b/.test(command)) return
      if (!stagingGuarded(cwd)) return
      throw new Error(
        "henxels: this repo sets ask_me_before_staging — do not `git add` or `git commit` " +
          "yourself. Finish your edits, then ask the user to review the diff and stage it.",
      )
    },

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
