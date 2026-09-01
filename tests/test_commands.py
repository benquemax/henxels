"""Command gates (run_before_commit / run_before_push) — subprocess behaviour."""

from henxels.commands import run_commands


def test_passing_command_yields_no_findings(tmp_path):
    assert run_commands(["true"], "pre_commit", tmp_path) == []


def test_failing_command_blocks(tmp_path):
    findings = run_commands(["false"], "pre_commit", tmp_path)
    assert len(findings) == 1 and findings[0].is_block


def test_command_gates_run_outside_gits_hook_context(tmp_path, monkeypatch):
    # Git exports GIT_DIR / GIT_INDEX_FILE to hook processes. A gate command
    # (pytest, make, anything that shells out to git in another directory) must
    # not inherit them — they'd silently redirect every git call in the child
    # to the parent repo.
    for var in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_PREFIX", "GIT_COMMON_DIR"):
        monkeypatch.setenv(var, "/somewhere/else")
    probe = 'test -z "$GIT_DIR$GIT_WORK_TREE$GIT_INDEX_FILE$GIT_PREFIX$GIT_COMMON_DIR"'
    assert run_commands([probe], "pre_commit", tmp_path) == []
