"""v2 digest rendering and the managed-block round-trip."""

from henxels.contract import Contract, Henxel
from henxels.digest import BEGIN, render_digest, sync_file, update_block

CONTRACT = Contract(
    settings={"confirm_before_push": True, "ask_me_before_staging": True},
    henxels=[
        Henxel(text="Docs are kebab-case markdown", locations=["./docs"], statements={"filename_casing": "kebab-case"}),
        Henxel(text="Parking lot exists", locations=["./*"], level="warn", statements={"required_files": "_todo.md"}),
        Henxel(text="_now exists in roadmap", locations=["./roadmap"], why="Holds work that ships this cycle.",
               statements={"required_subfolders": "_now"}),
    ],
)


def test_render_digest():
    d = render_digest(CONTRACT)
    assert "Docs are kebab-case markdown (in ./docs)" in d
    assert "Parking lot exists" in d and "_(warn)_" in d
    assert "bless push" in d
    assert "Git etiquette" in d and "git add" in d  # prominent, imperative staging directive
    assert "henxels catalogue" in d
    assert "contribute" in d
    assert "↳ Holds work that ships this cycle." in d  # why: rides into the digest


def test_update_block_appends_and_replaces():
    out = update_block("# Project\n\nNotes.\n", "DIGEST")
    assert BEGIN in out and out.startswith("# Project") and "DIGEST" in out
    out2 = update_block(out, "NEW")
    assert "NEW" in out2 and out2.count(BEGIN) == 1


def test_sync_file_preserves_human_text(tmp_path):
    target = tmp_path / "AGENTS.md"
    assert sync_file(target, CONTRACT) == "created"
    target.write_text(target.read_text() + "\n## mine\nkeep\n", encoding="utf-8")
    assert sync_file(target, CONTRACT) == "updated"
    after = target.read_text()
    assert "keep" in after and after.count(BEGIN) == 1
