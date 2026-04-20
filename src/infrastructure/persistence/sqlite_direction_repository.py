"""
基于 SQLite 的 Direction 仓储实现。
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime

from src.domain.models.direction import Direction
from src.domain.repositories.direction_repository import DirectionRepository
from src.infrastructure.persistence.sqlite_bootstrap import bootstrap_sqlite_storage
from src.infrastructure.persistence.sqlite_connection import sqlite_connection


def _row_to_direction(row) -> Direction:
    payload = dict(row)
    payload["preferred_variants"] = json.loads(payload.pop("preferred_variants_json") or "[]")
    return Direction(**payload)


class SqliteDirectionRepository(DirectionRepository):
    def __init__(self, db_path: str | None = None, legacy_config_file: str | None = None):
        self.db_path = db_path
        self.legacy_config_file = legacy_config_file

    async def find_all(self) -> list[Direction]:
        return await asyncio.to_thread(self._find_all_sync)

    async def find_by_id(self, direction_id: int) -> Direction | None:
        return await asyncio.to_thread(self._find_by_id_sync, direction_id)

    async def save(self, direction: Direction) -> Direction:
        return await asyncio.to_thread(self._save_sync, direction)

    async def delete(self, direction_id: int) -> bool:
        return await asyncio.to_thread(self._delete_sync, direction_id)

    def _find_all_sync(self) -> list[Direction]:
        bootstrap_sqlite_storage(self.db_path, legacy_config_file=self.legacy_config_file)
        with sqlite_connection(self.db_path) as conn:
            rows = conn.execute("SELECT * FROM radar_directions ORDER BY updated_at DESC, id DESC").fetchall()
        return [_row_to_direction(row) for row in rows]

    def _find_by_id_sync(self, direction_id: int) -> Direction | None:
        bootstrap_sqlite_storage(self.db_path, legacy_config_file=self.legacy_config_file)
        with sqlite_connection(self.db_path) as conn:
            row = conn.execute("SELECT * FROM radar_directions WHERE id = ?", (direction_id,)).fetchone()
        return _row_to_direction(row) if row else None

    def _save_sync(self, direction: Direction) -> Direction:
        bootstrap_sqlite_storage(self.db_path, legacy_config_file=self.legacy_config_file)
        with sqlite_connection(self.db_path) as conn:
            direction_id = direction.id
            created_at = direction.created_at
            if direction_id is None:
                created_at = created_at or datetime.utcnow()
                updated_at = direction.updated_at or created_at
                payload = direction.model_copy(update={
                    "created_at": created_at,
                    "updated_at": updated_at,
                }).model_dump(mode="json")
                payload["preferred_variants_json"] = json.dumps(
                    payload.pop("preferred_variants") or [],
                    ensure_ascii=False,
                )
                payload.pop("id", None)
                cursor = conn.execute(
                    """
                    INSERT INTO radar_directions (
                        name, seed_topic, user_goal, preferred_variants_json,
                        risk_level, status, created_at, updated_at
                    ) VALUES (
                        :name, :seed_topic, :user_goal, :preferred_variants_json,
                        :risk_level, :status, :created_at, :updated_at
                    )
                    """,
                    payload,
                )
                direction_id = int(cursor.lastrowid or 0)
            else:
                existing = conn.execute(
                    "SELECT created_at FROM radar_directions WHERE id = ?",
                    (direction_id,),
                ).fetchone()
                if existing and existing["created_at"]:
                    created_at = datetime.fromisoformat(str(existing["created_at"]))
                elif created_at is None:
                    created_at = datetime.utcnow()
                updated_at = direction.updated_at or datetime.utcnow()
                payload = direction.model_copy(update={
                    "id": direction_id,
                    "created_at": created_at,
                    "updated_at": updated_at,
                }).model_dump(mode="json")
                payload["preferred_variants_json"] = json.dumps(
                    payload.pop("preferred_variants") or [],
                    ensure_ascii=False,
                )
                conn.execute(
                    """
                    INSERT OR REPLACE INTO radar_directions (
                        id, name, seed_topic, user_goal, preferred_variants_json,
                        risk_level, status, created_at, updated_at
                    ) VALUES (
                        :id, :name, :seed_topic, :user_goal, :preferred_variants_json,
                        :risk_level, :status, :created_at, :updated_at
                    )
                    """,
                    payload,
                )
            conn.commit()
        return Direction(**{**direction.model_dump(), "id": direction_id, "created_at": created_at, "updated_at": updated_at})

    def _delete_sync(self, direction_id: int) -> bool:
        bootstrap_sqlite_storage(self.db_path, legacy_config_file=self.legacy_config_file)
        with sqlite_connection(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM radar_directions WHERE id = ?", (direction_id,))
            conn.commit()
        return bool(cursor.rowcount)
