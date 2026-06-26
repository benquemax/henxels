"""Bundled JSON Schema for ``henxels.yaml`` (editor autocomplete + validation)."""

from pathlib import Path

SCHEMA_PATH = Path(__file__).with_name("henxels.schema.json")


def schema_text() -> str:
    return SCHEMA_PATH.read_text(encoding="utf-8")
