"""The proactive guard: a custom check can't silently reinvent a built-in or a setting."""

import pytest

from henxels.statements import registry as reg
from henxels.statements.registry import custom_collisions, get_statement, statement


@pytest.fixture
def clean_registry():
    """Snapshot/restore the global registry so collision tests don't leak."""
    saved = dict(reg._REGISTRY)
    saved_shadow = set(reg._SHADOWED_BUILTINS)
    yield
    reg._REGISTRY.clear()
    reg._REGISTRY.update(saved)
    reg._SHADOWED_BUILTINS.clear()
    reg._SHADOWED_BUILTINS.update(saved_shadow)


def test_custom_cannot_override_builtin(clean_registry):
    before = get_statement("required_files")
    assert before is not None and before.builtin

    @statement("required_files")  # a custom check colliding with a built-in
    def bogus(scope):
        return "this should never run"

    assert get_statement("required_files") is before  # built-in kept, custom ignored
    assert any("required_files" in m for m in custom_collisions())


def test_settings_name_as_check_is_flagged(clean_registry):
    @statement("warn_about_large_files")  # a setting, not a check (qwen's mistake)
    def reinvented(param, file, scope):
        return None

    msgs = custom_collisions()
    assert any("warn_about_large_files" in m and "setting" in m for m in msgs)


def test_clean_registry_has_no_collisions():
    # the built-ins themselves must never collide
    assert custom_collisions() == []
