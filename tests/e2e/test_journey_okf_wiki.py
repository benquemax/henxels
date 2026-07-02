"""OKF wiki journeys: the okf-llm-wiki template lived end-to-end.

Scaffold mode: an agent grows a wiki inside blocking rules — every OKF violation class
is caught at commit time with an actionable instruction. Migrate mode: warnings ride
through commits until the wiki conforms, then the rules are promoted and start blocking.
"""

import shlex
import subprocess
import sys

import pytest

from tests.e2e.harness import E2E_COMMAND, output_of


def _concept(title: str, extra_body: str = "") -> str:
    slug = title.lower().replace(" ", "-")
    return (
        f"---\ntype: Metric\ntitle: {slug}\ndescription: {title} for the journey.\n"
        f"timestamp: 2026-07-02\n---\n\n# {title}\n\n"
        f"Derived over [the index](/index.md).\n{extra_body}"
    )


def _list_in_index(sandbox, repo, wiki, slug):
    index = repo / wiki / "index.md"
    index.write_text(
        index.read_text(encoding="utf-8") + f"* [{slug}]({slug}.md) - journey concept\n",
        encoding="utf-8",
    )


def test_scaffold_journey_catches_every_violation_class(sandbox):
    repo = sandbox.repo()
    r = sandbox.henxels("init", "--template", "okf-llm-wiki", cwd=repo)
    assert r.returncode == 0, output_of(r)
    assert "green at birth" in r.stdout

    assert sandbox.commit_all(repo, "adopt henxels + okf wiki").returncode == 0

    # A conforming concept sails through the hooks.
    sandbox.write(repo, "wiki/customer-count.md", _concept("Customer count"))
    _list_in_index(sandbox, repo, "wiki", "customer-count")
    ok = sandbox.commit_all(repo, "add customer-count")
    assert ok.returncode == 0, output_of(ok)

    # Missing type — the one OKF MUST.
    sandbox.write(repo, "wiki/broken-concept.md",
                  "---\ntitle: broken\ndescription: x.\ntimestamp: 2026-07-02\n---\n\n"
                  "See [the index](/index.md).\n")
    _list_in_index(sandbox, repo, "wiki", "broken-concept")
    blocked = sandbox.commit_all(repo, "missing type")
    assert blocked.returncode != 0
    assert "add frontmatter key 'type'" in output_of(blocked)

    sandbox.write(repo, "wiki/broken-concept.md", _concept("Broken concept"))
    assert sandbox.commit_all(repo, "type added").returncode == 0

    # A dead bundle-absolute link.
    sandbox.write(repo, "wiki/orders-metric.md",
                  _concept("Orders metric", "Joins [orders](/tables/orders.md).\n"))
    _list_in_index(sandbox, repo, "wiki", "orders-metric")
    dead = sandbox.commit_all(repo, "dead link")
    assert dead.returncode != 0
    assert "dead link /tables/orders.md" in output_of(dead)

    sandbox.write(repo, "wiki/orders-metric.md", _concept("Orders metric"))
    assert sandbox.commit_all(repo, "link removed").returncode == 0

    # Editing a concept without bumping its timestamp (diff-aware, commit-time only).
    conventions = repo / "wiki/wiki-conventions.md"
    conventions.write_text(
        conventions.read_text(encoding="utf-8") + "\nRefined guidance.\n", encoding="utf-8"
    )
    stale = sandbox.commit_all(repo, "edit without bump")
    assert stale.returncode != 0
    assert "'timestamp' wasn't bumped" in output_of(stale)

    text = conventions.read_text(encoding="utf-8")
    conventions.write_text(text.replace("timestamp: ", "timestamp: 2099-01-01 # was ", 1), encoding="utf-8")
    assert sandbox.commit_all(repo, "edit with bump").returncode == 0

    # A reserved file growing frontmatter.
    sandbox.write(repo, "wiki/tables/index.md", "---\ntitle: Tables\n---\n\n# Tables\n")
    reserved = sandbox.commit_all(repo, "frontmatter on index")
    assert reserved.returncode != 0
    assert "remove the frontmatter block" in output_of(reserved)

    sandbox.write(repo, "wiki/tables/index.md", "# Tables\n")
    assert sandbox.commit_all(repo, "reserved file clean").returncode == 0

    # A near-duplicate concept: awareness beats blocking — commit passes, but warns.
    near_copy = (repo / "wiki/customer-count.md").read_text(encoding="utf-8")
    sandbox.write(repo, "wiki/customer-count-two.md", near_copy.replace("Customer count", "Customer count two"))
    _list_in_index(sandbox, repo, "wiki", "customer-count-two")
    dup = sandbox.commit_all(repo, "near duplicate")
    assert dup.returncode == 0, output_of(dup)
    assert "similar" in output_of(dup).lower()


def test_migrate_journey_warn_then_promote(sandbox):
    repo = sandbox.repo()
    sandbox.write(repo, "wiki/notes.md", "Legacy knowledge. No frontmatter, no links.\n")
    assert sandbox.commit_all(repo, "pre-henxels history").returncode == 0

    r = sandbox.henxels("init", "--template", "okf-llm-wiki", cwd=repo)
    assert r.returncode == 0, output_of(r)
    assert "migration plan" in r.stdout
    assert not (repo / "wiki/wiki-conventions.md").exists()  # nothing written into their wiki

    # Warnings ride through commits: unrelated work is never blocked.
    sandbox.write(repo, "README.md", "hello\n")
    unrelated = sandbox.commit_all(repo, "unrelated work")
    assert unrelated.returncode == 0, output_of(unrelated)

    # Migrate: make the wiki conform, exactly as the findings instruct.
    sandbox.write(repo, "wiki/notes.md", _concept("Notes"))
    sandbox.write(repo, "wiki/index.md", "# Bundle\n\n* [notes](notes.md) - legacy knowledge\n")
    assert sandbox.commit_all(repo, "migrate wiki to OKF").returncode == 0
    check = sandbox.henxels("check", "--all", cwd=repo)
    assert check.returncode == 0, output_of(check)

    # Promote: delete the warn lines — the rules now block.
    contract = repo / "henxels.yaml"
    contract.write_text(contract.read_text(encoding="utf-8").replace("    level: warn\n", ""),
                        encoding="utf-8")
    assert sandbox.commit_all(repo, "promote wiki rules to blocking").returncode == 0

    sandbox.write(repo, "wiki/regression.md", "no frontmatter again\n")
    blocked = sandbox.commit_all(repo, "regression attempt")
    assert blocked.returncode != 0
    assert "add frontmatter key 'type'" in output_of(blocked)


def test_ambiguity_error_instruction_is_literally_executable(sandbox):
    repo = sandbox.repo()
    for i in range(3):
        sandbox.write(repo, f"pages/p{i}.md", "x\n")
    failed = sandbox.henxels("init", "--template", "okf-llm-wiki", cwd=repo)
    assert failed.returncode == 1

    # The error carries the exact command; run it verbatim.
    line = next(ln.strip() for ln in output_of(failed).splitlines() if "--wiki-dir pages" in ln)
    args = shlex.split(line)
    rerun = sandbox.henxels(*args[args.index("init"):], cwd=repo)
    assert rerun.returncode == 0, output_of(rerun)
    assert "./pages/*" in (repo / "henxels.yaml").read_text(encoding="utf-8")


@pytest.mark.skipif(sys.platform == "win32", reason="pty is POSIX-only")
def test_tty_picklist_settles_ambiguity(sandbox):
    import os
    import pty

    repo = sandbox.repo()
    for i in range(3):
        sandbox.write(repo, f"pages/p{i}.md", "x\n")

    master, slave = pty.openpty()
    try:
        proc = subprocess.Popen(
            [*E2E_COMMAND, "init", "--template", "okf-llm-wiki"],
            cwd=str(repo), env=sandbox.env, stdin=slave, stdout=slave, stderr=slave,
        )
        os.write(master, b"1\n")  # pick the first candidate: pages/
        os.close(slave)
        chunks = []
        try:
            while True:
                chunk = os.read(master, 4096)
                if not chunk:
                    break
                chunks.append(chunk)
        except OSError:
            pass  # EIO on child exit is the normal pty EOF
        assert proc.wait(timeout=120) == 0, b"".join(chunks).decode(errors="replace")
    finally:
        os.close(master)
    assert "./pages/*" in (repo / "henxels.yaml").read_text(encoding="utf-8")
