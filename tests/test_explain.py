"""`henxels explain` (v2) — which henxels govern a path."""

from henxels.contract import Contract, Henxel
from henxels.explain import explain_path

CONTRACT = Contract(henxels=[
    Henxel(text="Docs are kebab-case markdown", locations=["docs"],
           statements={"files_are": ".md", "casing": "kebab-case"}),
    Henxel(text="No setup.py", locations=[""], statements={"forbidden_files": "setup.py"}),
])


def test_explain_lists_matching_henxels():
    out = explain_path(CONTRACT, "docs/intro.md")
    assert "Docs are kebab-case markdown" in out
    assert "casing: kebab-case" in out
    # root-scoped henxel also applies everywhere
    assert "No setup.py" in out


def test_explain_silent_location():
    out = explain_path(Contract(henxels=[Henxel(text="x", locations=["src"], statements={})]), "docs/x.md")
    assert "no henxels apply" in out
