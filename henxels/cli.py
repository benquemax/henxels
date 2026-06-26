"""henxels command-line interface.

    henxels check [--all|--staged] [paths...]   validate against the contract
    henxels explain <path>                       what governs this location

(init / bless / sync / doctor arrive in later phases.)

Exit codes: 0 = clean, 1 = a henxel snapped (block), 2 = usage/config problem.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from henxels.checker import check_paths
from henxels.config.load import Config, ConfigError, find_config, load_config
from henxels.engine import gitinfo
from henxels.engine.discover import discover
from henxels.engine.report import is_fancy, render, render_summary, summarize
from henxels.explain import explain_path
from henxels.findings import Finding


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="henxels",
        description="Suspenders for your repo. Keep your ADHD agent in henxels.",
    )
    sub = parser.add_subparsers(dest="command")

    pi = sub.add_parser("init", help="scaffold the contract, hooks, and AGENTS.md digest")
    pi.add_argument("--no-hooks", action="store_true", help="don't install git hooks")
    pi.add_argument("--no-digest", action="store_true", help="don't write AGENTS.md")
    pi.add_argument("--force", action="store_true", help="overwrite an existing henxels.yaml")
    pi.set_defaults(func=cmd_init)

    pd = sub.add_parser("doctor", help="check that henxels is correctly set up")
    pd.set_defaults(func=cmd_doctor)

    pc = sub.add_parser("check", help="validate files against the contract")
    pc.add_argument("paths", nargs="*", help="specific paths to check")
    pc.add_argument("--all", action="store_true", help="check every governed file")
    pc.add_argument("--staged", action="store_true", help="check staged files only")
    pc.add_argument("--config", default=None, help="path to henxels.yaml")
    pc.add_argument("--plain", action="store_true", help="force plain output")
    pc.set_defaults(func=cmd_check)

    pe = sub.add_parser("explain", help="show the henxels governing a path")
    pe.add_argument("path", help="the path to explain")
    pe.add_argument("--config", default=None, help="path to henxels.yaml")
    pe.set_defaults(func=cmd_explain)

    pb = sub.add_parser("bless", help="consciously override a guard (push|delete)")
    pb.add_argument("action", choices=["push", "delete", "commit"])
    pb.set_defaults(func=cmd_bless)

    ps = sub.add_parser("sync", help="refresh the contract digest in AGENTS.md")
    ps.add_argument("--config", default=None, help="path to henxels.yaml")
    ps.add_argument("--target", default="AGENTS.md", help="file to write the digest into")
    ps.set_defaults(func=cmd_sync)

    # Hidden hook entrypoints (invoked by the installed git hooks).
    p_pc = sub.add_parser("_precommit")
    p_pc.set_defaults(func=cmd_precommit)
    p_pp = sub.add_parser("_prepush")
    p_pp.set_defaults(func=cmd_prepush)

    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 0
    return args.func(args)


def _load(args, root: Path) -> Config:
    path = Path(args.config) if args.config else find_config(root)
    if path is None:
        raise ConfigError(
            "No contract found. Looked for henxels.yaml at the repo root.\n"
            "  Run `henxels init` to create one."
        )
    return load_config(path)


def cmd_check(args) -> int:
    root = Path.cwd()
    try:
        config = _load(args, root)
    except ConfigError as exc:
        print(exc, file=sys.stderr)
        return 2

    rel_paths, check_existence = _select_files(args, root)

    if args.paths or args.staged:
        if not rel_paths:
            print("Nothing to check.")
            return 0

    findings = check_paths(config, root, rel_paths, check_existence=check_existence)
    return _emit(findings, plain=args.plain)


def cmd_explain(args) -> int:
    root = Path.cwd()
    try:
        config = _load(args, root)
    except ConfigError as exc:
        print(exc, file=sys.stderr)
        return 2
    print(explain_path(config, args.path))
    return 0


def cmd_init(args) -> int:
    from henxels.engine.report import BANNER
    from henxels.scaffold import init

    root = Path.cwd()
    fancy = is_fancy()
    if fancy:
        print(BANNER)
        print()

    report = init(
        root,
        install_git_hooks=not args.no_hooks,
        write_digest=not args.no_digest,
        force=args.force,
    )

    state, info = report["contract"]
    if state == "created":
        print(f"✓ henxels.yaml created for a {info} project")
    else:
        print(f"• henxels.yaml already exists ({info}) — left as-is (use --force to replace)")

    hooks = report.get("hooks")
    if hooks is None:
        print("• git hooks: skipped (not a git repo, or --no-hooks)")
    else:
        for hook, outcome in hooks.items():
            mark = "✓" if outcome in ("installed", "updated") else "•"
            print(f"{mark} git hook {hook}: {outcome}")

    if report.get("digest"):
        print(f"✓ AGENTS.md {report['digest']} — agents now see the contract")

    print()
    print("Next:")
    print("  • Tailor the contract: edit henxels.yaml (it's commented; enums autocomplete in your editor).")
    print("  • Ask what governs a spot: henxels explain <path>")
    print("  • Validate everything:    henxels check --all")
    print("  • Re-sync the digest after edits: henxels sync")
    print()
    print("To disobey a rule, change henxels.yaml — that's the whole idea.")
    return 0


def cmd_doctor(args) -> int:
    from henxels.doctor import diagnose

    fancy = is_fancy()
    checks = diagnose(Path.cwd())
    all_ok = True
    for c in checks:
        mark = "✓" if c.ok else "✗"
        if not c.ok:
            all_ok = False
        tail = f" — {c.detail}" if c.detail else ""
        line = f"  {mark} {c.label}{tail}"
        if fancy:
            line = f"  \033[{'32' if c.ok else '31'}m{mark}\033[0m {c.label}{tail}"
        print(line)
    print()
    print("henxels is ready." if all_ok else "Some checks need attention (see above).")
    return 0 if all_ok else 1


def cmd_bless(args) -> int:
    from henxels import bless as bless_mod
    from henxels.engine import gitinfo
    from henxels.rules.guard import collect_deletions

    root = Path.cwd()
    if not gitinfo.is_git_repo(root):
        print("Not a git repo — nothing to bless here.", file=sys.stderr)
        return 2

    if args.action == "push":
        fingerprint = gitinfo.head_sha(root) or "no-head"
        bless_mod.bless(root, "push", fingerprint)
        print("✓ push blessed. Your next `git push` will go through (once).")
        return 0

    if args.action == "delete":
        config = _safe_load(root)
        deletions = collect_deletions(config, root) if config else None
        if deletions is None or deletions.empty:
            print("Nothing staged that needs a delete-bless.")
            return 0
        bless_mod.bless(root, "delete", deletions.fingerprint())
        lost = deletions.files + [p for p, _ in deletions.lines]
        print(f"✓ deletion blessed for: {', '.join(lost)}")
        print("  Your next commit (with exactly these deletions) will go through.")
        return 0

    print("Commit guard is off by default; nothing to bless.")
    return 0


def cmd_sync(args) -> int:
    from henxels.digest import sync_file

    root = Path.cwd()
    try:
        config = _load(args, root)
    except ConfigError as exc:
        print(exc, file=sys.stderr)
        return 2
    action = sync_file(root / args.target, config)
    print(f"✓ {args.target} {action} — contract digest is in sync.")
    return 0


def cmd_precommit(args) -> int:
    from henxels.hookrun import run_precommit

    code, findings = run_precommit(Path.cwd())
    _emit(findings)
    return code


def cmd_prepush(args) -> int:
    from henxels.hookrun import run_prepush

    code, findings = run_prepush(Path.cwd())
    _emit(findings)
    return code


def _safe_load(root: Path) -> Config | None:
    path = find_config(root)
    if path is None:
        return None
    try:
        return load_config(path)
    except ConfigError:
        return None


def _select_files(args, root: Path) -> tuple[list[str], bool]:
    """Decide which files to check and whether to run folder-level existence."""
    if args.paths:
        return [_rel(p, root) for p in args.paths], False
    if args.staged:
        return gitinfo.staged_files(root), False
    if args.all:
        return discover(root), True
    # Default: staged in a git repo, otherwise a full scan.
    if gitinfo.is_git_repo(root):
        return gitinfo.staged_files(root), False
    return discover(root), True


def _rel(p: str, root: Path) -> str:
    path = Path(p)
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _emit(findings: list[Finding], plain: bool = False) -> int:
    fancy = is_fancy() and not plain
    text = render(findings, fancy=fancy)
    if text:
        print(text)
        print()
    print(render_summary(findings, fancy=fancy))
    blocks, _ = summarize(findings)
    return 1 if blocks else 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
