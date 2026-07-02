"""Enforcement journeys: the violate → blocked → fix → pass loop through real hooks."""

from tests.e2e.harness import output_of

KEBAB_DOCS = """henxels:
  - henxel: "Docs are kebab-case markdown"
    in: ./docs
    allowed_filetypes: .md
    filename_casing: kebab-case
"""


def test_violation_blocks_commit_then_fix_unblocks(sandbox):
    repo = sandbox.repo()
    sandbox.write(repo, "henxels.yaml", KEBAB_DOCS)
    sandbox.henxels("init", cwd=repo)  # existing contract kept; hooks installed

    sandbox.write(repo, "docs/BadName.md", "# nope\n")
    blocked = sandbox.commit_all(repo, "violate")
    out = output_of(blocked)
    assert blocked.returncode != 0
    assert "Docs are kebab-case markdown" in out  # the sentence is the failure message
    assert "BadName" in out
    assert "henxels.yaml" in out  # the steer: change the contract, that's the only escape

    (repo / "docs/BadName.md").rename(repo / "docs/bad-name.md")
    fixed = sandbox.commit_all(repo, "conform")
    assert fixed.returncode == 0, output_of(fixed)


def test_warn_level_shows_but_never_blocks(sandbox):
    repo = sandbox.repo()
    sandbox.write(repo, "henxels.yaml", KEBAB_DOCS.replace(
        "    filename_casing: kebab-case\n",
        "    filename_casing: kebab-case\n    level: warn\n",
    ))
    sandbox.henxels("init", cwd=repo)
    sandbox.write(repo, "docs/BadName.md", "# tolerated, nagged\n")
    commit = sandbox.commit_all(repo, "warned")
    assert commit.returncode == 0, output_of(commit)
    assert "Docs are kebab-case markdown" in output_of(commit)  # visible nudge


def test_no_verify_is_the_emergency_hatch(sandbox):
    repo = sandbox.repo()
    sandbox.write(repo, "henxels.yaml", KEBAB_DOCS)
    sandbox.henxels("init", cwd=repo)
    sandbox.write(repo, "docs/BadName.md", "# emergency\n")
    assert sandbox.git("add", "-A", cwd=repo).returncode == 0
    bypassed = sandbox.git("commit", "--no-verify", "-m", "emergency", cwd=repo)
    assert bypassed.returncode == 0, output_of(bypassed)


def test_run_before_commit_gate(sandbox):
    repo = sandbox.repo()
    sandbox.write(repo, "henxels.yaml",
                  'henxels:\n  - henxel: "The gate must pass"\n    run_before_commit: "exit 1"\n')
    sandbox.henxels("init", cwd=repo)
    sandbox.write(repo, "file.txt", "x\n")
    blocked = sandbox.commit_all(repo, "gated")
    assert blocked.returncode != 0
    assert "must pass before" in output_of(blocked)

    sandbox.write(repo, "henxels.yaml",
                  'henxels:\n  - henxel: "The gate must pass"\n    run_before_commit: "exit 0"\n')
    passed = sandbox.commit_all(repo, "gate open")
    assert passed.returncode == 0, output_of(passed)


def test_unknown_check_steers_instead_of_crashing(sandbox):
    repo = sandbox.repo()
    sandbox.write(repo, "henxels.yaml",
                  'henxels:\n  - henxel: "Uses a check that does not exist"\n    made_up_check: true\n')
    r = sandbox.henxels("check", "--all", cwd=repo)
    assert r.returncode == 1  # held, not crashed
    assert "made_up_check" in output_of(r)


def test_malformed_contract_is_a_usage_error(sandbox):
    repo = sandbox.repo()
    sandbox.write(repo, "henxels.yaml", "henxels: [unclosed\n")
    r = sandbox.henxels("check", "--all", cwd=repo)
    assert r.returncode == 2, output_of(r)  # exit-code contract: 2 = contract problem
