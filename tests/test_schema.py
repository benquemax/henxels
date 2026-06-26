"""The bundled JSON Schema must stay in lock-step with casing + the statement library."""

import json

from henxels.casing import NAMING_CONVENTIONS
from henxels.schema import SCHEMA_PATH, schema_text
from henxels.statements.registry import all_statements


def _schema():
    return json.loads(schema_text())


def test_schema_is_valid_json():
    assert SCHEMA_PATH.is_file()
    assert _schema()["title"] == "henxels contract"


def test_casing_enum_matches_constant():
    enum = set(_schema()["$defs"]["casingValue"]["enum"])
    assert enum == set(NAMING_CONVENTIONS)


def test_builtin_statements_are_documented():
    henxel_props = set(_schema()["$defs"]["henxel"]["properties"])
    builtin_names = {name for name, d in all_statements().items() if d.builtin}
    missing = builtin_names - henxel_props
    assert not missing, f"schema missing built-in statements: {sorted(missing)}"


def test_top_level_keys():
    props = set(_schema()["properties"])
    assert {"settings", "henxels", "imports"} <= props
