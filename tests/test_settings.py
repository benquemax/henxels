"""Settings accessors normalize the loose YAML into predictable values."""

from henxels import settings
from henxels.contract import Contract


def test_push_and_stage():
    c = Contract(settings={"confirm_before_push": True, "ask_me_before_staging": True})
    assert settings.confirm_before_push(c) is True
    assert settings.ask_me_before_staging(c) is True
    assert settings.confirm_before_push(Contract()) is False


def test_delete_protection_forms():
    assert settings.delete_protection(Contract()) is None
    assert settings.delete_protection(Contract(settings={"confirm_before_deleting": True})) == {"over_lines": 5}
    got = settings.delete_protection(Contract(settings={"confirm_before_deleting": {"over_lines": 9}}))
    assert got == {"over_lines": 9}


def test_similarity_forms():
    assert settings.similarity(Contract()) is None
    got = settings.similarity(Contract(settings={"warn_about_similar_files": {"above": 0.9, "ignore": ["x"]}}))
    assert got == {"above": 0.9, "ignore": ["x"]}
    assert settings.similarity(Contract(settings={"warn_about_similar_files": True}))["above"] == 0.85
