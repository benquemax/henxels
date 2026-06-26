"""Reporter: fancy/plain gating and rendering grouped by henxel sentence."""

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


def _finding():
    return Finding(
        level=BLOCK,
        henxel="Docs are kebab-case markdown",
        path="",
        message="",
        details=["docs/Bad_Name.md — rename to kebab-case"],
        steer="change this henxel in henxels.yaml",
    )


def test_render_plain_groups_by_sentence():
    out = render([_finding()], fancy=False)
    assert "\033[" not in out
    assert "Docs are kebab-case markdown" in out
    assert "docs/Bad_Name.md — rename to kebab-case" in out
    assert "→ change this henxel" in out


def test_render_fancy_has_ansi():
    assert "\033[" in render([_finding()], fancy=True)


def test_render_empty():
    assert render([], fancy=False) == ""


def test_summarize_counts():
    findings = [Finding(BLOCK, "a", "", "m"), Finding(WARN, "b", "", "m")]
    assert summarize(findings) == (1, 1)


def test_summary_all_clear():
    assert "hold" in render_summary([], fancy=False)


def test_summary_block_says_held_not_snapped():
    s = render_summary([Finding(BLOCK, "Push is guarded", "", "m")], fancy=False)
    assert "held by 1 henxel" in s
    assert "snapped" not in s
