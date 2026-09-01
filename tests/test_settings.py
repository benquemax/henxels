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
    assert got == {"above": 0.9, "ignore": ["x"], "at_most": 20, "budget": None}
    assert settings.similarity(Contract(settings={"warn_about_similar_files": True}))["above"] == 0.85
    got = settings.similarity(Contract(settings={"warn_about_similar_files": {"at_most": 3}}))
    assert got["at_most"] == 3


def test_similarity_budget_forms():
    from henxels import settings

    assert settings.similarity(Contract(settings={"warn_about_similar_files": True}))["budget"] is None
    got = settings.similarity(Contract(settings={"warn_about_similar_files": {"budget": 30}}))
    assert got["budget"] == 30.0
    got = settings.similarity(Contract(settings={"warn_about_similar_files": {"budget": "30s"}}))
    assert got["budget"] == 30.0
    got = settings.similarity(Contract(settings={"warn_about_similar_files": {"budget": "5m"}}))
    assert got["budget"] == 300.0
    got = settings.similarity(Contract(settings={"warn_about_similar_files": {"budget": "1h"}}))
    assert got["budget"] == 3600.0
