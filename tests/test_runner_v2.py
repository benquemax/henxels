"""The v2 runner: henxels as tests, name-injection, per-file, instruction returns."""

from henxels import statement
from henxels.contract import Contract, Henxel
from henxels.runner import run_contract


def repo(tmp_path, files):
    for rel, content in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    return list(files)


def hx(text, statements, locations=None, level="block"):
    return Henxel(text=text, locations=locations or [""], level=level, statements=statements)


def test_builtins_clean(tmp_path):
    files = repo(tmp_path, {"docs/intro.md": "---\ntitle: t\nsummary: s\n---\n# h\n"})
    c = Contract(henxels=[hx(
        "Docs are kebab markdown with title+summary",
        {"files_are": ".md", "casing": "kebab-case", "frontmatter_has": ["title", "summary"]},
        ["docs"],
    )])
    assert run_contract(c, tmp_path, files) == []


def test_builtins_collect_instructions(tmp_path):
    files = repo(tmp_path, {"docs/Bad_Name.md": "# no frontmatter\n"})
    c = Contract(henxels=[hx(
        "Docs are kebab markdown with title and summary",
        {"casing": "kebab-case", "frontmatter_has": ["title", "summary"]},
        ["docs"],
    )])
    findings = run_contract(c, tmp_path, files)
    assert len(findings) == 1
    f = findings[0]
    assert f.henxel.startswith("Docs are kebab")
    assert any("Bad_Name" in d for d in f.details)
    assert any("title" in d for d in f.details)


# --- per-file injection + instruction-on-fail ----------------------------

@statement("rt_max_lines")
def _rt_max_lines(param, file, scope):
    if scope.line_count(file) > param:
        return f"split it: keep under {param} lines"


def test_per_file_and_instruction(tmp_path):
    files = repo(tmp_path, {
        "src/big.py": "\n".join(str(i) for i in range(10)) + "\n",
        "src/ok.py": "x\n",
    })
    c = Contract(henxels=[hx("No file over 3 lines", {"rt_max_lines": 3}, ["src"])])
    findings = run_contract(c, tmp_path, files)
    assert len(findings) == 1
    details = findings[0].details
    assert any("src/big.py" in d and "split it" in d for d in details)
    assert not any("ok.py" in d for d in details)


# --- bare False falls back to the henxel's sentence ----------------------

@statement("rt_always_false")
def _rt_false(scope):
    return False


def test_false_uses_sentence(tmp_path):
    files = repo(tmp_path, {"a.txt": "x"})
    c = Contract(henxels=[hx("This invariant must hold", {"rt_always_false": True})])
    findings = run_contract(c, tmp_path, files)
    assert findings and findings[0].details == ["This invariant must hold"]


def test_warn_level(tmp_path):
    files = repo(tmp_path, {"a.txt": "x"})
    c = Contract(henxels=[hx("warn me", {"rt_always_false": True}, level="warn")])
    findings = run_contract(c, tmp_path, files)
    assert findings and not findings[0].is_block


# --- the legacy_is_gone_or_tidy_markdown_archive pattern -----------------

@statement("rt_legacy_gone_or_tidy")
def _rt_legacy(scope):
    if not scope.exists("legacy"):
        return None  # gone → passes
    bad = [f for f in scope.files if not f.endswith((".md", ".txt")) or not scope.is_kebab(f)]
    return [f"{f} — not a tidy archive file (use kebab-case .md/.txt)" for f in bad]


def test_legacy_gone_passes(tmp_path):
    files = repo(tmp_path, {"src/a.py": "x"})
    c = Contract(henxels=[hx("legacy gone or tidy", {"rt_legacy_gone_or_tidy": True}, ["legacy"])])
    assert run_contract(c, tmp_path, files) == []


def test_legacy_messy_fails(tmp_path):
    files = repo(tmp_path, {"legacy/Bad.py": "x"})
    c = Contract(henxels=[hx("legacy gone or tidy", {"rt_legacy_gone_or_tidy": True}, ["legacy"])])
    findings = run_contract(c, tmp_path, files)
    assert findings and any("legacy/Bad.py" in d for d in findings[0].details)


def test_unknown_statement_is_actionable(tmp_path):
    files = repo(tmp_path, {"a.txt": "x"})
    c = Contract(henxels=[hx("uses a missing check", {"nonexistent_check": True})])
    findings = run_contract(c, tmp_path, files)
    assert findings and "unknown check" in findings[0].details[0]
