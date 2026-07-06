"""Tests for the core graph store."""

import os
from pathlib import Path

import pytest

from samos import db as db_module
from samos.graph import (
    add_observation,
    add_relationship,
    ensure_entity,
    get_entity,
    get_events,
    get_observations,
    get_relationships,
    log_event,
    search_entities,
)


@pytest.fixture
def graph_db(tmp_path: Path, monkeypatch):
    """Use a temp SQLite file for graph tests."""
    db_path = tmp_path / "graph.db"
    monkeypatch.setenv("SAMOS_DB_PATH", str(db_path))
    monkeypatch.setattr(db_module, "DB_PATH", db_path)
    db_module.init_db()
    return db_path


def test_ensure_and_get_entity(graph_db):
    entity_id = ensure_entity("test", "person", "Alice", entity_key="alice")
    assert entity_id > 0
    entity = get_entity("test", "person", "alice")
    assert entity["name"] == "Alice"


def test_observations(graph_db):
    entity_id = ensure_entity("test", "metric", "weight", entity_key="weight")
    add_observation(entity_id, "kg", 70.5)
    obs = get_observations(entity_id=entity_id)
    assert len(obs) == 1
    assert obs[0]["obs_key"] == "kg"


def test_relationships(graph_db):
    a = ensure_entity("test", "person", "Alice", entity_key="alice2")
    b = ensure_entity("test", "person", "Bob", entity_key="bob2")
    add_relationship(a, b, "knows")
    rels = get_relationships(a, direction="source")
    assert len(rels) == 1
    assert rels[0]["rel_type"] == "knows"


def test_events(graph_db):
    log_event("test", "login", payload={"ip": "127.0.0.1"})
    events = get_events(module="test", event_type="login")
    assert len(events) == 1
    assert "127.0.0.1" in events[0]["payload"]


def test_search_entities(graph_db):
    ensure_entity("test", "note", "Grocery list", entity_key="grocery")
    results = search_entities("Grocery", module="test")
    assert len(results) >= 1
