"""`henxels explain` (v2) — which henxels govern a path."""

from henxels.contract import Contract, Henxel
from henxels.explain import explain_data, explain_path

CONTRACT = Contract(henxels=[
    Henxel(text="Docs are kebab-case markdown", locations=["./docs"],
           statements={"allowed_filetypes": ".md", "filename_casing": "kebab-case"}),
    Henxel(text="No setup.py", locations=["./*"], statements={"forbidden_files": "setup.py"}),
])


def test_explain_lists_matching_henxels():
    out = explain_path(CONTRACT, "docs/intro.md")
    assert "Docs are kebab-case markdown" in out
    assert "filename_casing: kebab-case" in out
    # root-scoped henxel also applies everywhere
    assert "No setup.py" in out


def test_explain_data_json_shape():
    data = explain_data(CONTRACT, "docs/intro.md")
    assert data["path"] == "docs/intro.md"
    texts = [h["henxel"] for h in data["henxels"]]
    assert "Docs are kebab-case markdown" in texts
    first = data["henxels"][0]
    assert set(first) == {"henxel", "why", "in", "level", "statements"}


def test_explain_silent_location():
    out = explain_path(Contract(henxels=[Henxel(text="x", locations=["./src"], statements={})]), "docs/x.md")
    assert "no henxels apply" in out


def test_explain_shows_why():
    contract = Contract(henxels=[
        Henxel(text="_now exists in roadmap", locations=["./roadmap"], why="Work shipping this cycle lives here.",
               statements={"required_subfolders": "_now"}),
    ])
    assert "↳ Work shipping this cycle lives here." in explain_path(contract, "roadmap/x.md")
    assert explain_data(contract, "roadmap/x.md")["henxels"][0]["why"] == "Work shipping this cycle lives here."


def test_explain_respects_except():
    contract = Contract(henxels=[
        Henxel(text="Pages are kebab-case", locations=["./*"], excludes=["./raw/*"],
               statements={"filename_casing": "kebab-case"}),
    ])
    assert "Pages are kebab-case" in explain_path(contract, "entities/tom.md")
    assert "no henxels apply" in explain_path(contract, "raw/articles/x.md")  # carved out
