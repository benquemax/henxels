"""Contract-driven checks (commands run by the hooks)."""

from henxels.checks import run_checks
from henxels.config.load import Config
from henxels.hookrun import run_precommit


def test_passing_check_no_findings(tmp_path):
    cfg = Config(checks={"pre_commit": ["true"]})
    assert run_checks(cfg, "pre_commit", tmp_path) == []


def test_failing_check_blocks(tmp_path):
    cfg = Config(checks={"pre_commit": ["false"]})
    findings = run_checks(cfg, "pre_commit", tmp_path)
    assert len(findings) == 1
    assert findings[0].is_block
    assert findings[0].henxel == "checks"


def test_string_command_coerced(tmp_path):
    cfg = Config(checks={"pre_commit": "true"})
    assert run_checks(cfg, "pre_commit", tmp_path) == []


def test_stage_without_checks(tmp_path):
    assert run_checks(Config(), "pre_commit", tmp_path) == []


def test_precommit_runs_checks(git_repo):
    (git_repo / "henxels.yaml").write_text(
        'henxels: 1\nchecks:\n  pre_commit:\n    - "false"\n', encoding="utf-8"
    )
    (git_repo / "a.txt").write_text("hi\n", encoding="utf-8")
    import subprocess

    subprocess.run(["git", "add", "."], cwd=git_repo, check=True, capture_output=True)
    code, findings = run_precommit(git_repo)
    assert code == 1
    assert any(f.henxel == "checks" for f in findings)
