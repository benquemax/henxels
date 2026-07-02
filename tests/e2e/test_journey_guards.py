"""Guard journeys: delete/push protections and the one-shot bless tokens."""

from tests.e2e.harness import output_of

DELETE_GUARD = "settings:\n  confirm_before_deleting:\n    over_lines: 3\n"
PUSH_GUARD = "settings:\n  confirm_before_push: true\n"

SIX_LINES = "one\ntwo\nthree\nfour\nfive\nsix\n"


def test_delete_guard_and_one_shot_bless(sandbox):
    repo = sandbox.repo()
    sandbox.write(repo, "henxels.yaml", DELETE_GUARD)
    sandbox.write(repo, "a.txt", SIX_LINES)
    sandbox.write(repo, "b.txt", SIX_LINES)
    sandbox.henxels("init", cwd=repo)
    assert sandbox.commit_all(repo, "seed").returncode == 0

    (repo / "a.txt").unlink()
    blocked = sandbox.commit_all(repo, "drop a")
    assert blocked.returncode != 0
    assert "bless delete" in output_of(blocked)

    assert sandbox.henxels("bless", "delete", cwd=repo).returncode == 0
    assert sandbox.commit_all(repo, "drop a, deliberately").returncode == 0

    (repo / "b.txt").unlink()  # the token was consumed — a new deletion needs a new bless
    reblocked = sandbox.commit_all(repo, "drop b")
    assert reblocked.returncode != 0
    assert "bless delete" in output_of(reblocked)


def test_push_guard_and_one_shot_bless(sandbox):
    repo = sandbox.repo()
    sandbox.write(repo, "henxels.yaml", PUSH_GUARD)
    sandbox.henxels("init", cwd=repo)
    assert sandbox.commit_all(repo, "seed").returncode == 0
    sandbox.bare_remote(repo)

    blocked = sandbox.git("push", "-u", "origin", "main", cwd=repo)
    assert blocked.returncode != 0
    assert "bless push" in output_of(blocked)

    assert sandbox.henxels("bless", "push", cwd=repo).returncode == 0
    assert sandbox.git("push", "-u", "origin", "main", cwd=repo).returncode == 0

    sandbox.write(repo, "more.txt", "x\n")
    assert sandbox.commit_all(repo, "more").returncode == 0
    reblocked = sandbox.git("push", cwd=repo)  # consumed — push is guarded again
    assert reblocked.returncode != 0
    assert "bless push" in output_of(reblocked)


def test_failing_pre_push_gate_blocks_even_when_blessed(sandbox):
    repo = sandbox.repo()
    sandbox.write(
        repo, "henxels.yaml",
        'settings:\n  confirm_before_push: true\nhenxels:\n'
        '  - henxel: "The gate must pass before every push"\n    run_before_push: "exit 1"\n',
    )
    sandbox.henxels("init", cwd=repo)
    assert sandbox.commit_all(repo, "seed").returncode == 0
    sandbox.bare_remote(repo)
    assert sandbox.henxels("bless", "push", cwd=repo).returncode == 0

    pushed = sandbox.git("push", "-u", "origin", "main", cwd=repo)
    assert pushed.returncode != 0  # the bless clears the guard, never the contract
    assert "must pass before" in output_of(pushed)
