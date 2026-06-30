"""henxels command-line interface (v2).

    henxels init                       scaffold contract + hooks + AGENTS.md digest
    henxels check [--all|--staged] […] run the contract (every henxel is a test)
    henxels explain <path>             what governs this location
    henxels catalogue                  browse the statements you can use
    henxels create-new-statement <n>   scaffold a local custom statement
    henxels contribute [name]          how to upstream a reusable statement
    henxels bless <push|delete>        consciously override a protection
    henxels sync                       refresh the AGENTS.md digest
    henxels doctor                     check the setup

Exit codes: 0 = clean, 1 = held by a henxel, 2 = usage/contract problem.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from henxels import settings
from henxels.contract import (
    Contract,
    ContractError,
    apply_imports,
    find_contract,
    load_contract,
)
from henxels.diffinfo import staged_diff
from henxels.engine import gitinfo
from henxels.engine.discover import discover
from henxels.engine.report import is_fancy, render, render_summary, summarize
from henxels.explain import explain_path
from henxels.findings import Finding
from henxels.runner import run_contract


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="henxels",
        description="Suspenders for your repo. Keep your ADHD agent in henxels.",
    )
    sub = parser.add_subparsers(dest="command")

    pi = sub.add_parser("init", help="scaffold the contract, hooks, and AGENTS.md digest")
    pi.add_argument("--no-hooks", action="store_true")
    pi.add_argument("--no-digest", action="store_true")
    pi.add_argument("--force", action="store_true")
    pi.set_defaults(func=cmd_init)

    pc = sub.add_parser("check", help="run the contract")
    pc.add_argument("paths", nargs="*")
    pc.add_argument("--all", action="store_true")
    pc.add_argument("--staged", action="store_true")
    pc.add_argument("--config", default=None)
    pc.add_argument("--plain", action="store_true")
    pc.set_defaults(func=cmd_check)

    pe = sub.add_parser("explain", help="show the henxels governing a path")
    pe.add_argument("path")
    pe.add_argument("--config", default=None)
    pe.add_argument("--json", action="store_true", help="machine-readable output for agent tooling")
    pe.set_defaults(func=cmd_explain)

    pcat = sub.add_parser("catalogue", help="browse the statements you can use")
    pcat.set_defaults(func=cmd_catalogue)

    pn = sub.add_parser("create-new-statement", help="scaffold a custom statement")
    pn.add_argument("name")
    pn.set_defaults(func=cmd_create_statement)

    pcon = sub.add_parser("contribute", help="how to upstream a reusable statement")
    pcon.add_argument("name", nargs="?", default=None)
    pcon.set_defaults(func=cmd_contribute)

    pb = sub.add_parser("bless", help="consciously override a protection")
    pb.add_argument("action", choices=["push", "delete"])
    pb.set_defaults(func=cmd_bless)

    ps = sub.add_parser("sync", help="refresh the AGENTS.md digest")
    ps.add_argument("--config", default=None)
    ps.add_argument("--target", default="AGENTS.md")
    ps.set_defaults(func=cmd_sync)

    pd = sub.add_parser("doctor", help="check that henxels is correctly set up")
    pd.set_defaults(func=cmd_doctor)

    pint = sub.add_parser("integrate", help="install an agent-harness integration (e.g. opencode)")
    pint.add_argument("harness")
    pint.set_defaults(func=cmd_integrate)

    # Git passes arguments to its hooks (pre-push gets "<remote> <url>"); swallow them.
    p_pc = sub.add_parser("_precommit")
    p_pc.add_argument("hook_args", nargs="*")
    p_pc.set_defaults(func=cmd_precommit)
    p_pp = sub.add_parser("_prepush")
    p_pp.add_argument("hook_args", nargs="*")
    p_pp.set_defaults(func=cmd_prepush)

    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 0
    return args.func(args)


# --- helpers -------------------------------------------------------------

def _load(root: Path, config_path: str | None = None) -> Contract:
    path = Path(config_path) if config_path else find_contract(root)
    if path is None:
        raise ContractError(
            "No contract found. Looked for henxels.yaml at the repo root.\n"
            "  Run `henxels init` to create one."
        )
    contract = load_contract(path)
    apply_imports(contract, root=root)
    return contract


def _notify_update() -> None:
    """Print an upgrade nudge to stderr (so stdout stays machine-clean). Never raises."""
    try:
        from henxels.version_check import update_notice

        notice = update_notice()
        if notice:
            print(notice, file=sys.stderr)
    except Exception:  # noqa: BLE001 - an update check must never affect the command
        pass


def _emit(findings: list[Finding], plain: bool = False) -> int:
    fancy = is_fancy() and not plain
    text = render(findings, fancy=fancy)
    if text:
        print(text)
        print()
    print(render_summary(findings, fancy=fancy))
    blocks, _ = summarize(findings)
    return 1 if blocks else 0


# --- commands ------------------------------------------------------------

def cmd_check(args) -> int:
    root = Path.cwd()
    try:
        contract = _load(root, args.config)
    except ContractError as exc:
        print(exc, file=sys.stderr)
        return 2

    staged_mode = False
    if args.paths:
        files = [_rel(p, root) for p in args.paths]
    elif args.staged:
        files, staged_mode = gitinfo.staged_files(root), True
    elif args.all:
        files = discover(root)
    elif gitinfo.is_git_repo(root):
        files, staged_mode = gitinfo.staged_files(root), True
    else:
        files = discover(root)

    if (args.paths or args.staged) and not files:
        print("Nothing to check.")
        return 0

    # Diff-aware statements (append_only, immutable, bump_updated_on_change) only make
    # sense against staged change — outside that, diff is None and they pass.
    diff = staged_diff(root) if staged_mode else None
    findings = run_contract(contract, root, files, diff=diff)
    sim = settings.similarity(contract)
    if sim:
        from henxels.similarity import warn_similar

        findings.extend(warn_similar(sim, root, files))

    large = settings.large_files(contract)
    if large:
        from henxels.filesize import warn_large_files

        findings.extend(warn_large_files(large, root, files))

    from henxels.statements.registry import custom_collisions

    collisions = custom_collisions()
    if collisions:
        findings.append(
            Finding(level="warn", henxel="A custom check reinvents a built-in", path="", message="", details=collisions)
        )
    code = _emit(findings, plain=args.plain)
    _notify_update()
    return code


def cmd_explain(args) -> int:
    root = Path.cwd()
    try:
        contract = _load(root, args.config)
    except ContractError as exc:
        print(exc, file=sys.stderr)
        return 2
    if args.json:
        import json

        from henxels.explain import explain_data

        print(json.dumps(explain_data(contract, args.path), indent=2))
    else:
        print(explain_path(contract, args.path))
    return 0


def cmd_catalogue(args) -> int:
    from henxels.catalogue import render_catalogue

    root = Path.cwd()
    try:
        _load(root)  # load + import so custom statements show up
    except ContractError:
        pass
    print(render_catalogue())
    return 0


def cmd_create_statement(args) -> int:
    from henxels.catalogue import create_statement_scaffold
    from henxels.invocation import henxels_cmd

    path, action = create_statement_scaffold(args.name, Path.cwd())
    print(f"✓ {path.name} {action} — added a template statement '{args.name}'.")
    print("Next:")
    print("  • Fill in the function (it's auto-loaded — no imports: needed).")
    print(f"  • Use it in a henxel:  {args.name}: <param>")
    print(f"  • Reusable beyond this repo?  {henxels_cmd()} contribute {args.name}")
    return 0


def cmd_contribute(args) -> int:
    from henxels.catalogue import contribute_guide, contribute_snippet

    root = Path.cwd()
    try:
        _load(root)
    except ContractError:
        pass
    print(contribute_guide(args.name))
    if args.name:
        snippet = contribute_snippet(args.name)
        if snippet:
            source, test_stub = snippet
            print("\n--- ready-to-paste built-in (add builtin=True + a help= string) ---\n")
            print(source)
            print("\n--- test stub for tests/test_statements.py ---\n")
            print(test_stub)
    return 0


def cmd_init(args) -> int:
    from henxels.engine.report import BANNER
    from henxels.scaffold import init

    root = Path.cwd()
    if is_fancy():
        print(BANNER)
        print()

    report = init(root, install_git_hooks=not args.no_hooks, write_digest=not args.no_digest, force=args.force)

    state, info = report["contract"]
    if state == "created":
        print(f"✓ henxels.yaml created for a {info} project")
    else:
        print("• henxels.yaml already exists — left as-is (use --force to replace)")
    hooks = report.get("hooks")
    if hooks is None:
        print("• git hooks: skipped (not a git repo, or --no-hooks)")
    else:
        for hook, outcome in hooks.items():
            mark = "✓" if outcome in ("installed", "updated") else "•"
            print(f"{mark} git hook {hook}: {outcome}")
        shadowed = report.get("hooks_shadowed")
        if shadowed:
            print(f"⚠ git hooks won't fire: core.hooksPath={shadowed} shadows .git/hooks.")
            print("    Unset it (`git config --unset core.hooksPath`), or call")
            print("    `henxels _precommit` / `henxels _prepush` from those hooks.")
    if report.get("digest"):
        print(f"✓ AGENTS.md {report['digest']} — agents now see the contract")
    if report.get("schema"):
        print(f"✓ {report['schema']} — editor autocomplete for henxels.yaml")
        print("    (install a YAML language-server extension, e.g. Red Hat YAML, to see it)")

    from henxels.invocation import henxels_cmd

    hx = henxels_cmd()
    print()
    print("Next:")
    print(f"  • Tailor the rules: edit henxels.yaml (browse `{hx} catalogue` for statements).")
    print(f"  • Ask what governs a spot: {hx} explain <path>")
    print(f"  • Validate everything:    {hx} check --all")
    print("  • Commit henxels.yaml, AGENTS.md, and .henxels/ — they're your contract")
    print("    (don't gitignore .henxels/: it holds the editor schema + any custom checks).")
    print("  • Tell contributors how to install henxels: add it to your README")
    print("    (the committed contract assumes `henxels` is installed).")
    print("  • To disobey a rule, change henxels.yaml — that's the whole idea.")
    if hx != "henxels":
        print(f"  • Tip: `uv tool install henxels` (or pipx) puts `henxels` on your PATH so you can drop `{hx.rsplit(' ', 1)[0]} `.")
    return 0


def cmd_doctor(args) -> int:
    from henxels.doctor import diagnose

    fancy = is_fancy()
    all_ok = True
    for c in diagnose(Path.cwd()):
        mark = "✓" if c.ok else "✗"
        all_ok = all_ok and c.ok
        tail = f" — {c.detail}" if c.detail else ""
        if fancy:
            print(f"  \033[{'32' if c.ok else '31'}m{mark}\033[0m {c.label}{tail}")
        else:
            print(f"  {mark} {c.label}{tail}")
    print()
    print("henxels is ready." if all_ok else "Some checks need attention (see above).")
    _notify_update()
    return 0 if all_ok else 1


def cmd_integrate(args) -> int:
    from henxels.integrate import write_integration

    try:
        path, action = write_integration(args.harness, Path.cwd())
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2
    rel = path.relative_to(Path.cwd()) if path.is_absolute() else path
    print(f"✓ {rel} {action} — {args.harness} integration installed.")
    return 0


def cmd_sync(args) -> int:
    from henxels.digest import sync_file

    root = Path.cwd()
    try:
        contract = _load(root, args.config)
    except ContractError as exc:
        print(exc, file=sys.stderr)
        return 2
    action = sync_file(root / args.target, contract)
    print(f"✓ {args.target} {action} — contract digest is in sync.")
    return 0


def cmd_bless(args) -> int:
    from henxels import bless as bless_mod
    from henxels.guard import collect_deletions

    root = Path.cwd()
    if not gitinfo.is_git_repo(root):
        print("Not a git repo — nothing to bless here.", file=sys.stderr)
        return 2

    if args.action == "push":
        bless_mod.bless(root, "push", gitinfo.head_sha(root) or "no-head")
        print("✓ push blessed. Your next `git push` will go through (once).")
        return 0

    contract = None
    try:
        contract = _load(root)
    except ContractError:
        pass
    over = (settings.delete_protection(contract) or {"over_lines": 5})["over_lines"] if contract else 5
    deletions = collect_deletions(root, over)
    if deletions.empty:
        print("Nothing staged that needs a delete-bless.")
        return 0
    bless_mod.bless(root, "delete", deletions.fingerprint())
    lost = deletions.files + [p for p, _ in deletions.lines]
    print(f"✓ deletion blessed for: {', '.join(lost)}")
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


def _rel(p: str, root: Path) -> str:
    path = Path(p)
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
