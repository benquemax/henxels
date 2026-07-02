"""First-run journeys: from a fresh machine to a green, hook-guarded repo."""

from tests.e2e.harness import output_of


def test_init_to_first_commit(sandbox):
    repo = sandbox.repo()
    r = sandbox.henxels("init", cwd=repo)
    assert r.returncode == 0, output_of(r)
    assert "henxels.yaml created" in r.stdout
    for rel in ("henxels.yaml", "AGENTS.md", ".henxels/henxels.schema.json"):
        assert (repo / rel).is_file(), f"init did not write {rel}"

    check = sandbox.henxels("check", "--all", cwd=repo)
    assert check.returncode == 0, output_of(check)

    commit = sandbox.commit_all(repo, "adopt henxels")
    assert commit.returncode == 0, output_of(commit)
    assert "henxels hold" in output_of(commit)  # the pre-commit hook actually fired


def test_reinit_keeps_the_contract(sandbox):
    repo = sandbox.repo()
    sandbox.henxels("init", cwd=repo)
    (repo / "henxels.yaml").write_text("henxels:\n  - henxel: \"Mine\"\n    required_files: README.md\n",
                                       encoding="utf-8")
    again = sandbox.henxels("init", cwd=repo)
    assert again.returncode == 0
    assert "already exists" in again.stdout
    assert "Mine" in (repo / "henxels.yaml").read_text(encoding="utf-8")


def test_doctor_green_after_init(sandbox):
    repo = sandbox.repo()
    sandbox.henxels("init", cwd=repo)
    doctor = sandbox.henxels("doctor", cwd=repo)
    assert doctor.returncode == 0, output_of(doctor)


def test_shadowed_core_hookspath_is_flagged(sandbox):
    repo = sandbox.repo()
    sandbox.git("config", "core.hooksPath", ".husky", cwd=repo)
    r = sandbox.henxels("init", cwd=repo)
    assert r.returncode == 0
    assert "core.hooksPath" in output_of(r)  # init warns instead of silently no-opping


def test_check_finds_the_contract_from_a_subdirectory(sandbox):
    # Users run henxels from wherever their terminal happens to be — like git,
    # it should find the contract at the repo root.
    repo = sandbox.repo()
    sandbox.henxels("init", cwd=repo)
    sub = repo / "src" / "deep"
    sub.mkdir(parents=True)
    r = sandbox.henxels("check", "--all", cwd=sub)
    assert r.returncode == 0, output_of(r)
