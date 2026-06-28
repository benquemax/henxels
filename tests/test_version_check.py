"""The update nudge: correct when outdated, silent when it should be, never networked in tests."""

from henxels import version_check as vc


def test_parse_and_compare():
    assert vc._parse("0.4.1") == (0, 4, 1)
    assert vc._parse("0.5.0") > vc._parse("0.4.9")
    assert vc._parse("0.4") < vc._parse("0.4.1")


def test_notice_when_outdated():
    n = vc.update_notice(installed="0.3.0", latest="0.4.0", env={})
    assert n and "0.4.0" in n and "0.3.0" in n
    assert "init" in n  # nudge to refresh hooks + schema after upgrading


def test_no_notice_when_current_or_newer():
    assert vc.update_notice(installed="0.4.0", latest="0.4.0", env={}) is None
    assert vc.update_notice(installed="0.4.1", latest="0.4.0", env={}) is None  # local dev ahead of PyPI


def test_opt_out_and_ci_silence_it():
    assert vc.update_notice(installed="0.1.0", latest="9.9.9", env={"HENXELS_NO_UPDATE_CHECK": "1"}) is None
    assert vc.update_notice(installed="0.1.0", latest="9.9.9", env={"CI": "true"}) is None


def test_missing_values_no_notice():
    # latest=None means "couldn't determine" — must NOT fall through to a network lookup
    assert vc.update_notice(installed="0.3.0", latest=None, env={}) is None
    assert vc.update_notice(installed=None, latest="0.4.0", env={}) is None


def test_cache_is_used_without_network(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    vc._write_cache("0.9.9", now=1000.0)
    assert vc.latest_version(now=1000.0 + 10) == "0.9.9"  # fresh cache → no fetch
