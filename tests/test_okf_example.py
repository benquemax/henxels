"""The OKF example contracts, executed straight out of the docs.

README.md and docs/enforcing-okf.md promise a contract for Open Knowledge Format
bundles. These tests extract that exact YAML (and the guide's custom check) from the
markdown and run it against a conformant bundle and against broken ones — so the
example can never quietly drift from the statement library. A doc that lies is worse
than no doc.
"""

import re
from pathlib import Path

from henxels.contract import load_contract
from henxels.runner import run_contract
from henxels.statements.registry import all_statements

REPO = Path(__file__).resolve().parents[1]

_FENCE = re.compile(r"```(\w+)\n(.*?)```", re.DOTALL)


def _fenced_blocks(path: Path, lang: str) -> list[str]:
    text = path.read_text(encoding="utf-8")
    return [m.group(2) for m in _FENCE.finditer(text) if m.group(1) == lang]


def _okf_contract(path: Path) -> str:
    blocks = [b for b in _fenced_blocks(path, "yaml") if "no_frontmatter" in b]
    assert len(blocks) == 1, f"expected exactly one OKF contract block in {path.name}"
    return blocks[0]


DOCS_CONTRACT = _okf_contract(REPO / "docs" / "enforcing-okf.md")
README_CONTRACT = _okf_contract(REPO / "README.md")

# The guide's custom check, registered by executing the doc's own code block. Compiled
# under this file's name so well_formed_statements treats it as a test fixture, not as
# a statement contributed by the repo.
_custom_blocks = [b for b in _fenced_blocks(REPO / "docs" / "enforcing-okf.md", "python") if "@statement" in b]
assert len(_custom_blocks) == 1
exec(compile(_custom_blocks[0], __file__, "exec"))  # noqa: S102 - doc code under test


# --- a conformant bundle (mirrors the guide's worked example) --------------

BUNDLE = {
    "wiki/index.md": (
        '---\nokf_version: "0.1"\n---\n\n# Knowledge bundle\n\n## Concepts\n\n'
        "* [Data glossary](glossary.md) - shared vocabulary\n"
        "* [Tables](tables/index.md) - warehouse tables\n"
        "* [Metrics](metrics/index.md) - business metrics\n"
    ),
    "wiki/glossary.md": (
        "---\ntype: Playbook\ntitle: Data glossary\ndescription: Shared vocabulary.\n"
        "timestamp: 2026-06-30T09:00:00Z\n---\n\n# Data glossary\n\n"
        "A customer is any account with an order — see the\n"
        "[customers table](/tables/customers.md).\n"
    ),
    "wiki/log.md": (
        "# Bundle update log\n\n## 2026-06-30\n\n* **Update**: Clarified the glossary.\n\n"
        "## 2026-06-12\n\n* **Creation**: Initial bundle.\n"
    ),
    "wiki/tables/index.md": "# Tables\n\n* [customers](customers.md) - one row per account\n",
    "wiki/tables/customers.md": (
        "---\ntype: BigQuery Table\ntitle: customers\ndescription: One row per account.\n"
        "resource: bigquery://project/dataset/customers\ntimestamp: 2026-06-12T14:30:00Z\n---\n\n"
        "# Schema\n\nFeeds the [revenue metric](/metrics/revenue.md).\n\n"
        "# Citations\n\n[1] [Warehouse design doc](/references/warehouse.pdf)\n"
    ),
    "wiki/metrics/index.md": "# Metrics\n\n* [revenue](revenue.md) - recognized revenue\n",
    "wiki/metrics/revenue.md": (
        "---\ntype: Metric\ntitle: revenue\ndescription: Recognized revenue per month.\n"
        "timestamp: 2026-06-12\n---\n\n# Definition\n\n"
        "Sum of paid invoices over the [customers table](../tables/customers.md).\n"
    ),
}


def build_bundle(root: Path, include_references: bool = True) -> None:
    files = dict(BUNDLE)
    if include_references:
        files["wiki/references/warehouse.pdf"] = "not really a pdf"
    for rel, content in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")


def check(root: Path, contract_yaml: str) -> list[str]:
    """Run a contract over the bundle; return the per-file instructions."""
    (root / "henxels.yaml").write_text(contract_yaml, encoding="utf-8")
    contract = load_contract(root / "henxels.yaml")
    findings = run_contract(contract, root)
    return [detail for f in findings for detail in f.details]


# --- the examples only name statements that exist ---------------------------

def test_example_contracts_use_known_statements(tmp_path):
    known = set(all_statements())
    for contract_yaml in (DOCS_CONTRACT, README_CONTRACT):
        (tmp_path / "henxels.yaml").write_text(contract_yaml, encoding="utf-8")
        for hx in load_contract(tmp_path / "henxels.yaml").henxels:
            unknown = set(hx.statements) - known
            assert not unknown, f"example names unknown statement(s): {sorted(unknown)}"


# --- conformant bundles pass -------------------------------------------------

def test_docs_contract_holds_on_conformant_bundle(tmp_path):
    build_bundle(tmp_path)
    assert check(tmp_path, DOCS_CONTRACT) == []


def test_readme_contract_holds_on_conformant_bundle(tmp_path):
    build_bundle(tmp_path, include_references=False)  # the README variant has no references/ carve-out
    assert check(tmp_path, README_CONTRACT) == []


# --- every OKF conformance rule fires when broken ---------------------------

def test_empty_type_is_flagged(tmp_path):
    build_bundle(tmp_path)
    (tmp_path / "wiki/glossary.md").write_text(
        "---\ntype:\ntitle: Data glossary\ndescription: x.\ntimestamp: 2026-06-30\n---\n\n"
        "See [customers](/tables/customers.md).\n",
        encoding="utf-8",
    )
    out = check(tmp_path, DOCS_CONTRACT)
    assert any("'type' is empty" in i for i in out)


def test_type_outside_taxonomy_is_flagged(tmp_path):
    build_bundle(tmp_path)
    text = (tmp_path / "wiki/glossary.md").read_text(encoding="utf-8")
    (tmp_path / "wiki/glossary.md").write_text(text.replace("type: Playbook", "type: Gizmo"), encoding="utf-8")
    out = check(tmp_path, DOCS_CONTRACT)
    assert any("'type': 'Gizmo' not allowed" in i for i in out)


def test_non_iso_timestamp_is_flagged(tmp_path):
    build_bundle(tmp_path)
    text = (tmp_path / "wiki/glossary.md").read_text(encoding="utf-8")
    (tmp_path / "wiki/glossary.md").write_text(
        text.replace("timestamp: 2026-06-30T09:00:00Z", "timestamp: yesterday"), encoding="utf-8"
    )
    out = check(tmp_path, DOCS_CONTRACT)
    assert any("ISO 8601 datetime" in i for i in out)


def test_dead_bundle_absolute_link_is_flagged(tmp_path):
    build_bundle(tmp_path)
    with (tmp_path / "wiki/metrics/revenue.md").open("a", encoding="utf-8") as fh:
        fh.write("Feeds [orders](/tables/orders.md).\n")
    out = check(tmp_path, DOCS_CONTRACT)
    assert any("dead link /tables/orders.md" in i for i in out)


def test_dead_relative_link_is_flagged(tmp_path):
    build_bundle(tmp_path)
    with (tmp_path / "wiki/glossary.md").open("a", encoding="utf-8") as fh:
        fh.write("Compare [old notes](./notes.md).\n")
    out = check(tmp_path, DOCS_CONTRACT)
    assert any("dead link ./notes.md" in i for i in out)


def test_orphan_concept_is_flagged(tmp_path):
    build_bundle(tmp_path)
    (tmp_path / "wiki/churn.md").write_text(
        "---\ntype: Metric\ntitle: churn\ndescription: Monthly churn.\ntimestamp: 2026-06-30\n---\n\nNo links.\n",
        encoding="utf-8",
    )
    index = tmp_path / "wiki/index.md"
    index.write_text(
        index.read_text(encoding="utf-8") + "* [churn](churn.md) - monthly churn\n", encoding="utf-8"
    )
    out = check(tmp_path, DOCS_CONTRACT)
    assert any("churn.md" in i and "outbound" in i for i in out)


def test_frontmatter_on_nested_index_is_flagged(tmp_path):
    build_bundle(tmp_path)
    (tmp_path / "wiki/tables/index.md").write_text(
        "---\ntitle: Tables\n---\n\n# Tables\n\n* [customers](customers.md) - one row per account\n",
        encoding="utf-8",
    )
    out = check(tmp_path, DOCS_CONTRACT)
    assert any("wiki/tables/index.md" in i and "remove the frontmatter block" in i for i in out)


def test_bundle_root_index_may_declare_okf_version(tmp_path):
    build_bundle(tmp_path)  # the root index.md in the fixture carries okf_version frontmatter
    assert check(tmp_path, DOCS_CONTRACT) == []


def test_unlisted_top_level_concept_is_flagged(tmp_path):
    build_bundle(tmp_path)
    (tmp_path / "wiki/churn.md").write_text(
        "---\ntype: Metric\ntitle: churn\ndescription: Monthly churn.\ntimestamp: 2026-06-30\n---\n\n"
        "Over the [customers table](/tables/customers.md).\n",
        encoding="utf-8",
    )
    out = check(tmp_path, DOCS_CONTRACT)
    assert any("add it to wiki/index.md" in i for i in out)


def test_doc_custom_check_log_headings_are_dates(tmp_path):
    from henxels.statements.registry import get_statement
    from henxels.statements.scope import build_scope

    fn = get_statement("log_headings_are_dates").fn
    (tmp_path / "log.md").write_text("# Log\n\n## 2026-06-30\n\n* b.\n\n## 2026-06-12\n\n* a.\n", encoding="utf-8")
    scope = build_scope(["./*"], ["log.md"], tmp_path, {})
    assert fn("log.md", scope) == []

    (tmp_path / "log.md").write_text("# Log\n\n## June 30\n\n* x.\n\n## 2026-06-12\n\n* a.\n", encoding="utf-8")
    assert fn("log.md", scope)


def test_log_sections_must_be_iso_dates_newest_first(tmp_path):
    build_bundle(tmp_path)
    (tmp_path / "wiki/log.md").write_text(
        "# Bundle update log\n\n## June 30\n\n* x.\n\n## 2026-06-12\n\n* a.\n\n## 2026-06-30\n\n* b.\n",
        encoding="utf-8",
    )
    out = check(tmp_path, DOCS_CONTRACT)
    assert any("## YYYY-MM-DD" in i for i in out)
    assert any("newest first" in i for i in out)


def test_stray_filetype_in_bundle_is_flagged(tmp_path):
    build_bundle(tmp_path)
    (tmp_path / "wiki/notes.txt").write_text("loose scratch\n", encoding="utf-8")
    out = check(tmp_path, DOCS_CONTRACT)
    assert any("notes.txt" in i for i in out)


def test_non_kebab_concept_name_is_flagged(tmp_path):
    build_bundle(tmp_path)
    (tmp_path / "wiki/tables/OrderItems.md").write_text(
        "---\ntype: BigQuery Table\ntitle: order items\ndescription: Line items.\ntimestamp: 2026-06-30\n---\n\n"
        "Joins the [customers table](./customers.md).\n",
        encoding="utf-8",
    )
    out = check(tmp_path, DOCS_CONTRACT)
    assert any("OrderItems" in i for i in out)


# --- the README variant enforces the same core --------------------------------

def test_readme_contract_flags_empty_type_and_reserved_frontmatter(tmp_path):
    build_bundle(tmp_path, include_references=False)
    (tmp_path / "wiki/glossary.md").write_text(
        "---\ntype:\ntitle: Data glossary\ndescription: x.\ntimestamp: 2026-06-30\n---\n\n"
        "See [customers](/tables/customers.md).\n",
        encoding="utf-8",
    )
    (tmp_path / "wiki/tables/index.md").write_text(
        "---\ntitle: Tables\n---\n\n# Tables\n\n* [customers](customers.md) - one row per account\n",
        encoding="utf-8",
    )
    out = check(tmp_path, README_CONTRACT)
    assert any("'type' is empty" in i for i in out)
    assert any("remove the frontmatter block" in i for i in out)
