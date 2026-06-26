"""The bundled JSON Schema must stay in lock-step with the loader/rules."""

import json

from henxels.rules.naming import NAMING_CONVENTIONS
from henxels.schema import SCHEMA_PATH, schema_text


def _schema():
    return json.loads(schema_text())


def test_schema_is_valid_json():
    assert SCHEMA_PATH.is_file()
    assert _schema()["title"] == "henxels contract"


def test_naming_enum_matches_constant():
    enum = set(_schema()["$defs"]["naming"]["enum"])
    assert enum == set(NAMING_CONVENTIONS)


def test_guard_enum_present():
    enum = set(_schema()["$defs"]["guard"]["enum"])
    assert {"off", "bless", "ask"} == enum


def test_version_enum_matches_supported():
    from henxels.config.load import SUPPORTED_VERSION

    assert _schema()["properties"]["henxels"]["enum"] == [SUPPORTED_VERSION]
