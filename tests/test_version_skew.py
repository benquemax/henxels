"""Version-skew steering: a newer contract enforced by an older henxels must say so.

A contract authored with newer built-ins (e.g. no_frontmatter, the frontmatter_dates
datetime form) hitting a stale install used to fail with cryptic, misdirecting text:
"unknown check 'no_frontmatter' — import the module that defines it" (real fix:
upgrade) or "check 'frontmatter_dates' errored: unhashable type: 'dict'". These tests
pin the corrected steering — messages that name the running version and point at an
upgrade, plus an opt-in `requires_henxels:` floor that fails fast and clearly.
"""

from henxels import __version__
from henxels.contract import load_contract
from henxels.runner import run_contract
from henxels.statements.registry import get_statement
from henxels.statements.scope import build_scope
from henxels.version_check import requirement_unmet


def _write(tmp_path, text):
    p = tmp_path / "henxels.yaml"
    p.write_text(text, encoding="utf-8")
    return p


# --- the two runner messages ------------------------------------------------

def test_unknown_check_message_names_version_and_both_causes(tmp_path):
    contract = load_contract(_write(
        tmp_path,
        'henxels:\n  - henxel: "Uses a check from the future"\n    totally_new_builtin: true\n',
    ))
    findings = run_contract(contract, tmp_path)
    detail = " ".join(d for f in findings for d in f.details)
    assert "totally_new_builtin" in detail
    assert __version__ in detail            # says what you're running
    assert "upgrade" in detail.lower()      # the likely real fix
    assert "custom" in detail.lower()       # still covers the other cause


def test_errored_check_message_hints_at_version_skew(tmp_path):
    # frontmatter_dates' dict form is a newer shape; an older engine crashed on it.
    # We can't run an old engine here, so force an error with a genuinely bad param
    # and assert the wrapper now carries the upgrade hint.
    contract = load_contract(_write(
        tmp_path,
        'henxels:\n  - henxel: "Boom"\n    in: ./*\n    max_lines: not-a-number\n',
    ))
    (tmp_path / "f.txt").write_text("x\n", encoding="utf-8")
    findings = run_contract(contract, tmp_path)
    detail = " ".join(d for f in findings for d in f.details)
    assert "errored" in detail
    assert __version__ in detail
    assert "upgrad" in detail.lower()


# --- requirement_unmet ------------------------------------------------------

def test_requirement_unmet_when_installed_is_older():
    msg = requirement_unmet(">=0.9", installed="0.5.6")
    assert msg and "0.9" in msg and "0.5.6" in msg and "upgrade" in msg.lower()


def test_requirement_met_is_silent():
    assert requirement_unmet(">=0.6", installed="0.8.0") is None
    assert requirement_unmet("0.6", installed="0.6.0") is None  # bare version = minimum


def test_requirement_absent_or_unknown_is_silent():
    assert requirement_unmet(None, installed="0.1.0") is None
    assert requirement_unmet("", installed="0.1.0") is None
    assert requirement_unmet(">=9.9", installed=None) is None  # source checkout: don't false-block


# --- the contract key + run_contract short-circuit --------------------------

def test_contract_parses_requires_henxels(tmp_path):
    contract = load_contract(_write(tmp_path, 'requires_henxels: ">=0.6"\nhenxels: []\n'))
    assert contract.requires == ">=0.6"


def test_run_contract_blocks_clearly_when_floor_unmet(tmp_path):
    # An impossibly high floor stands in for "your install is too old".
    contract = load_contract(_write(
        tmp_path,
        'requires_henxels: ">=99.0"\n'
        'henxels:\n  - henxel: "Kebab docs"\n    in: ./docs\n    filename_casing: kebab-case\n',
    ))
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "BadName.md").write_text("x\n", encoding="utf-8")
    findings = run_contract(contract, tmp_path)
    # One clear finding about the version, not a pile of per-check noise.
    assert len(findings) == 1
    detail = " ".join(findings[0].details)
    assert "99.0" in detail and __version__ in detail and "upgrade" in detail.lower()


def test_run_contract_normal_when_floor_met(tmp_path):
    contract = load_contract(_write(
        tmp_path,
        'requires_henxels: ">=0.1"\n'
        'henxels:\n  - henxel: "Kebab docs"\n    in: ./docs\n    filename_casing: kebab-case\n',
    ))
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "BadName.md").write_text("x\n", encoding="utf-8")
    findings = run_contract(contract, tmp_path)
    detail = " ".join(d for f in findings for d in f.details)
    assert "BadName" in detail  # the real rule ran; the floor didn't get in the way


def test_statement_registry_still_sane():
    # guardrail: the messages tested above only matter if these are real/absent
    assert get_statement("filename_casing") is not None
    assert get_statement("totally_new_builtin") is None
    build_scope(["./*"], [], ".", {})  # smoke: scope still builds
