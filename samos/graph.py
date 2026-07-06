"""Core graph store: entities, relationships, observations, events.

This module links all sam-os modules together. Every module can write its own
optimized tables, but it should also feed the graph store so the data is
queryable as a unified graph.
"""

from __future__ import annotations

import json
from datetime import datetime

from .db import get_conn


def _now() -> str:
    return datetime.now().isoformat()


def ensure_entity(
    module: str,
    entity_type: str,
    name: str,
    entity_key: str | None = None,
    meta: dict | None = None,
) -> int:
    """Get or create an entity and return its id."""
    key = entity_key or name
    with get_conn() as c:
        row = c.execute(
            "SELECT id FROM entities WHERE module=? AND entity_type=? AND entity_key=?",
            (module, entity_type, key),
        ).fetchone()
        if row:
            entity_id = row["id"]
            if meta is not None:
                c.execute(
                    "UPDATE entities SET name=?, meta=? WHERE id=?",
                    (name, json.dumps(meta), entity_id),
                )
            return entity_id
        c.execute(
            "INSERT INTO entities (module, entity_type, name, entity_key, meta) VALUES (?, ?, ?, ?, ?)",
            (module, entity_type, name, key, json.dumps(meta) if meta else None),
        )
        return c.execute("SELECT last_insert_rowid()").fetchone()[0]


def get_entity(module: str, entity_type: str, entity_key: str) -> dict | None:
    with get_conn() as c:
        row = c.execute(
            "SELECT * FROM entities WHERE module=? AND entity_type=? AND entity_key=?",
            (module, entity_type, entity_key),
        ).fetchone()
    return dict(row) if row else None


def add_observation(entity_id: int, obs_key: str, obs_value: str | int | float | dict | None) -> dict:
    """Record a timestamped observation for an entity."""
    value = json.dumps(obs_value) if not isinstance(obs_value, str) else obs_value
    with get_conn() as c:
        c.execute(
            "INSERT INTO observations (entity_id, obs_key, obs_value, observed_at) VALUES (?, ?, ?, ?)",
            (entity_id, obs_key, value, _now()),
        )
    return {"entity_id": entity_id, "obs_key": obs_key, "obs_value": value}


def get_observations(
    entity_id: int | None = None,
    obs_key: str | None = None,
    limit: int = 100,
) -> list[dict]:
    with get_conn() as c:
        sql = "SELECT * FROM observations WHERE 1=1"
        params: list = []
        if entity_id is not None:
            sql += " AND entity_id=?"
            params.append(entity_id)
        if obs_key is not None:
            sql += " AND obs_key=?"
            params.append(obs_key)
        sql += " ORDER BY observed_at DESC LIMIT ?"
        params.append(limit)
        rows = c.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def add_relationship(
    source_id: int,
    target_id: int,
    rel_type: str,
    meta: dict | None = None,
) -> dict:
    with get_conn() as c:
        c.execute(
            "INSERT INTO relationships (source_id, target_id, rel_type, meta) VALUES (?, ?, ?, ?)",
            (source_id, target_id, rel_type, json.dumps(meta) if meta else None),
        )
    return {"source_id": source_id, "target_id": target_id, "rel_type": rel_type}


def get_relationships(entity_id: int, direction: str = "both") -> list[dict]:
    """Return relationships where entity is source, target, or both."""
    with get_conn() as c:
        rows = []
        if direction in ("source", "both"):
            rows += c.execute(
                """
                SELECT r.*, e.name AS target_name, e.entity_type AS target_type
                FROM relationships r
                JOIN entities e ON r.target_id=e.id
                WHERE r.source_id=?
                """,
                (entity_id,),
            ).fetchall()
        if direction in ("target", "both"):
            rows += c.execute(
                """
                SELECT r.*, e.name AS source_name, e.entity_type AS source_type
                FROM relationships r
                JOIN entities e ON r.source_id=e.id
                WHERE r.target_id=?
                """,
                (entity_id,),
            ).fetchall()
    return [dict(r) for r in rows]


def log_event(
    module: str,
    event_type: str,
    entity_id: int | None = None,
    payload: dict | None = None,
) -> dict:
    with get_conn() as c:
        c.execute(
            "INSERT INTO events (module, event_type, entity_id, payload, occurred_at) VALUES (?, ?, ?, ?, ?)",
            (module, event_type, entity_id, json.dumps(payload) if payload else None, _now()),
        )
    return {"module": module, "event_type": event_type, "entity_id": entity_id}


def get_events(
    module: str | None = None,
    event_type: str | None = None,
    entity_id: int | None = None,
    limit: int = 100,
) -> list[dict]:
    with get_conn() as c:
        sql = "SELECT * FROM events WHERE 1=1"
        params: list = []
        if module is not None:
            sql += " AND module=?"
            params.append(module)
        if event_type is not None:
            sql += " AND event_type=?"
            params.append(event_type)
        if entity_id is not None:
            sql += " AND entity_id=?"
            params.append(entity_id)
        sql += " ORDER BY occurred_at DESC LIMIT ?"
        params.append(limit)
        rows = c.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def search_entities(query: str, module: str | None = None, limit: int = 20) -> list[dict]:
    """Simple substring search across entity names."""
    with get_conn() as c:
        sql = "SELECT * FROM entities WHERE name LIKE ?"
        params: list = [f"%{query}%"]
        if module is not None:
            sql += " AND module=?"
            params.append(module)
        sql += " ORDER BY module, entity_type, name LIMIT ?"
        params.append(limit)
        rows = c.execute(sql, params).fetchall()
    return [dict(r) for r in rows]
