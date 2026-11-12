from __future__ import annotations

import importlib.util
from pathlib import Path

from construction_pm.knowledge.sqlite_store import SqliteKnowledgeStore

TOOL = Path(__file__).resolve().parents[2] / "tools" / "knowledge_inventory.py"


def _load_tool():
    spec = importlib.util.spec_from_file_location("knowledge_inventory", TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_inventory_reports_validation_separately_from_publication(
    tmp_path, card_factory, publish_factory
) -> None:
    database = tmp_path / "knowledge.sqlite3"
    store = SqliteKnowledgeStore(str(database))
    try:
        store.save_card(card_factory(topic_key="draft.html"))
        store.save_card(publish_factory(card_factory(topic_key="published.html")))
    finally:
        store.close()

    measured = _load_tool().measure(database)

    cards = measured["cards"]
    assert cards["total"] == 2
    assert cards["published"] == 1
    assert cards["draft"] == 1
    # Validation is a different column from publication; a measurement that
    # reads the publication map for "validated" silently reports zero.
    assert cards["by_validation_status"] == {"validated": 2}
    assert cards["validated"] == 2
    assert measured["database"]["schema_version"] == 3


def test_inventory_measurement_does_not_modify_the_database(
    tmp_path, card_factory
) -> None:
    database = tmp_path / "knowledge.sqlite3"
    store = SqliteKnowledgeStore(str(database))
    try:
        store.save_card(card_factory(topic_key="draft.html"))
    finally:
        store.close()

    tool = _load_tool()
    before = tool._sha256(database)
    tool.measure(database)
    assert tool._sha256(database) == before
