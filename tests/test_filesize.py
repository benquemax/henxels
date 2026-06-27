"""Large-file warnings: unit-aware threshold, estimate-only tokens, warn never block."""

from henxels import settings
from henxels.contract import Contract
from henxels.filesize import parse_threshold, warn_large_files


def test_parse_threshold_units():
    assert parse_threshold("8000 tokens") == (8000.0, "tokens")
    assert parse_threshold("3kb") == (3.0, "kb")
    assert parse_threshold("3 kb") == (3.0, "kb")          # optional space
    assert parse_threshold("200 LINES") == (200.0, "lines")  # case-insensitive


def test_parse_threshold_requires_unit():
    assert parse_threshold("500000") is None   # bare number rejected — no guessing
    assert parse_threshold("lots") is None


def test_warn_tokens_over(tmp_path):
    (tmp_path / "big.md").write_text("x" * 40000)  # ~10000 estimated tokens
    out = warn_large_files({"over": "8000 tokens", "ignore": []}, tmp_path, ["big.md"])
    assert out and "estimated" in out[0].details[0]
    assert out[0].level == "warn"


def test_warn_tokens_under(tmp_path):
    (tmp_path / "small.md").write_text("tiny file\n")
    assert warn_large_files({"over": "8000 tokens", "ignore": []}, tmp_path, ["small.md"]) == []


def test_warn_bytes(tmp_path):
    (tmp_path / "b.bin").write_bytes(b"x" * 5000)  # 5000 > 3*1024
    assert warn_large_files({"over": "3 kb", "ignore": []}, tmp_path, ["b.bin"])


def test_warn_lines(tmp_path):
    (tmp_path / "p.md").write_text("line\n" * 250)
    assert warn_large_files({"over": "200 lines", "ignore": []}, tmp_path, ["p.md"])


def test_warn_respects_ignore(tmp_path):
    (tmp_path / "big.md").write_text("x" * 40000)
    assert warn_large_files({"over": "8000 tokens", "ignore": ["*.md"]}, tmp_path, ["big.md"]) == []


def test_invalid_threshold_is_silent(tmp_path):
    (tmp_path / "big.md").write_text("x" * 40000)
    assert warn_large_files({"over": "500000", "ignore": []}, tmp_path, ["big.md"]) == []


def test_settings_large_files_forms():
    assert settings.large_files(Contract()) is None
    got = settings.large_files(Contract(settings={"warn_about_large_files": {"over": "3 kb", "ignore": ["x"]}}))
    assert got == {"over": "3 kb", "ignore": ["x"]}
    assert settings.large_files(Contract(settings={"warn_about_large_files": True}))["over"] == "8000 tokens"
