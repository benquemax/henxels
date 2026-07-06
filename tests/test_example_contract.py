"""The shipped example contract must parse under the CURRENT engine.

`examples/henxels.yaml.example` is often the first real contract someone browsing the
repo reads. A superseded-schema example is worse than none: it happened once — a
`guards:`/`tree:`/`canonical:` file survived a rebuild and the engine parsed it to an
empty, inert contract that silently enforced nothing while reporting "all henxels
hold". These tests keep the example honest — non-empty, every statement real, and free
of the old top-level keys — so it can never quietly rot again.
"""

from pathlib import Path

import yaml

from henxels.contract import apply_imports, load_contract
from henxels.runner import run_contract
from henxels.statements.registry import all_statements

EXAMPLE = Path(__file__).resolve().parent.parent / "examples" / "henxels.yaml.example"

# Top-level keys from the pre-v2 "structure-first" schema. Their presence means the
# example is a schema behind — the engine drops them and produces nothing.
SUPERSEDED_KEYS = {"guards", "similarity", "canonical", "tree", "plugins"}


def test_example_exists():
    assert EXAMPLE.is_file(), "the annotated example contract went missing"


def test_example_parses_to_a_nonempty_contract():
    contract = load_contract(EXAMPLE)
    assert contract.settings, "example declares no settings — superseded/empty schema?"
    assert contract.henxels, "example declares no henxels — superseded/empty schema?"


def test_example_has_no_superseded_top_level_keys():
    raw = yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))
    resurfaced = SUPERSEDED_KEYS & set(raw)
    assert not resurfaced, f"superseded top-level keys are back: {sorted(resurfaced)}"


def test_every_henxel_actually_checks_something():
    contract = load_contract(EXAMPLE)
    inert = [h.text for h in contract.henxels if not h.statements]
    assert not inert, f"these henxels carry no checks (decoration, not enforcement): {inert}"


def test_every_statement_in_the_example_is_a_real_check():
    contract = load_contract(EXAMPLE)
    apply_imports(contract, root=EXAMPLE.parent)
    known = set(all_statements())
    for hx in contract.henxels:
        unknown = set(hx.statements) - known
        assert not unknown, f"{hx.text!r} names non-existent check(s): {sorted(unknown)}"


def test_example_runs_without_any_statement_erroring(tmp_path):
    # Against an empty tree, statements may report violations (missing required files,
    # etc.) — that's fine. What must never happen is a statement *crashing*, which the
    # runner surfaces as an "errored:" instruction (e.g. a wrong param shape).
    contract = load_contract(EXAMPLE)
    apply_imports(contract, root=EXAMPLE.parent)
    findings = run_contract(contract, tmp_path)
    errored = [d for f in findings for d in f.details if "errored:" in d]
    assert not errored, errored
