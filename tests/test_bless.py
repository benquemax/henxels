"""Bless token mint / verify / consume / expire."""

from henxels import bless


def _root(tmp_path):
    (tmp_path / ".git").mkdir()
    return tmp_path


def test_bless_then_consume(tmp_path):
    root = _root(tmp_path)
    bless.bless(root, "push", "sha123", now=1000)
    assert bless.is_blessed(root, "push", "sha123", now=1100) is True
    assert bless.consume(root, "push", "sha123", now=1100) is True
    # single use: gone afterwards
    assert bless.is_blessed(root, "push", "sha123", now=1100) is False


def test_fingerprint_mismatch(tmp_path):
    root = _root(tmp_path)
    bless.bless(root, "push", "sha123", now=1000)
    assert bless.consume(root, "push", "different", now=1100) is False


def test_expiry(tmp_path):
    root = _root(tmp_path)
    bless.bless(root, "delete", "fp", ttl=600, now=1000)
    assert bless.is_blessed(root, "delete", "fp", now=2000) is False  # 1000s later


def test_missing_token(tmp_path):
    root = _root(tmp_path)
    assert bless.is_blessed(root, "push", "x") is False
    assert bless.consume(root, "push", "x") is False
