"""Reporter: fancy/plain gating and rendering."""

from henxels.engine.report import is_fancy, render, render_summary, summarize
from henxels.findings import BLOCK, WARN, Finding


class _TTY:
    def isatty(self):
        return True


class _Pipe:
    def isatty(self):
        return False


def test_is_fancy_requires_tty():
    assert is_fancy(stream=_TTY(), env={}) is True
    assert is_fancy(stream=_Pipe(), env={}) is False


def test_is_fancy_opt_outs():
    assert is_fancy(stream=_TTY(), env={"NO_COLOR": "1"}) is False
    assert is_fancy(stream=_TTY(), env={"CI": "true"}) is False
    assert is_fancy(stream=_TTY(), env={"HENXELS_PLAIN": "1"}) is False


def _finding():
    return Finding(
        level=BLOCK,
        henxel="placement",
        path="src/foo_test.py",
        message="test files are forbidden under src/",
        reason="tests live in tests/",
        steer="create tests/foo_test.py instead",
        fix="edit henxels.yaml to allow it",
    )


def test_render_plain_has_no_ansi():
    out = render([_finding()], fancy=False)
    assert "\033[" not in out
    assert "src/foo_test.py" in out
    assert "placement" in out
    assert "tests live in tests/" in out
    assert "→ create tests/foo_test.py instead" in out


def test_render_fancy_has_ansi():
    out = render([_finding()], fancy=True)
    assert "\033[" in out


def test_render_empty():
    assert render([], fancy=False) == ""


def test_summarize_counts():
    findings = [
        Finding(BLOCK, "a", "p1", "m"),
        Finding(WARN, "b", "p2", "m"),
        Finding(WARN, "c", "p3", "m"),
    ]
    assert summarize(findings) == (1, 2)


def test_summary_all_clear():
    assert "hold" in render_summary([], fancy=False)
