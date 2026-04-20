"""
基于 SQLite 的方向候选词仓储实现。
"""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from src.domain.models.direction_candidate import DirectionCandidate
from src.domain.repositories.direction_candidate_repository import DirectionCandidateRepository
from src.infrastructure.persistence.sqlite_bootstrap import bootstrap_sqlite_storage
from src.infrastructure.persistence.sqlite_connection import sqlite_connection


def _row_to_candidate(row) -> DirectionCandidate:
    return DirectionCandidate(**dict(row))


class SqliteDirectionCandidateRepository(DirectionCandidateRepository):
    def __init__(self, db_path: str | None = None, legacy_config_file: str | None = None):
        self.db_path = db_path
        self.legacy_config_file = legacy_config_file

    async def find_by_direction_id(self, direction_id: int) -> list[DirectionCandidate]:
        return await asyncio.to_thread(self._find_by_direction_id_sync, direction_id)

    async def save_many(self, candidates: list[DirectionCandidate]) -> list[DirectionCandidate]:
        return await asyncio.to_thread(self._save_many_sync, candidates)

    def _find_by_direction_id_sync(self, direction_id: int) -> list[DirectionCandidate]:
        bootstrap_sqlite_storage(self.db_path, legacy_config_file=self.legacy_config_file)
        with sqlite_connection(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM radar_keyword_candidates
                WHERE direction_id = ?
                ORDER BY
                    CASE lifecycle_status WHEN 'seed' THEN 0 ELSE 1 END,
                    confidence DESC,
                    keyword ASC
                """,
                (direction_id,),
            ).fetchall()
        return [_row_to_candidate(row) for row in rows]

    def _save_many_sync(self, candidates: list[DirectionCandidate]) -> list[DirectionCandidate]:
        if not candidates:
            return []

        bootstrap_sqlite_storage(self.db_path, legacy_config_file=self.legacy_config_file)
        now = datetime.now(UTC).isoformat()
        direction_id = candidates[0].direction_id
        with sqlite_connection(self.db_path) as conn:
            for candidate in candidates:
                existing = conn.execute(
                    """
                    SELECT id, created_at, lifecycle_status
                    FROM radar_keyword_candidates
                    WHERE direction_id = ? AND keyword = ?
                    """,
                    (candidate.direction_id, candidate.keyword),
                ).fetchone()
                created_at = str(existing["created_at"]) if existing and existing["created_at"] else (
                    candidate.created_at.isoformat() if candidate.created_at else now
                )
                lifecycle_status = (
                    str(existing["lifecycle_status"])
                    if existing and existing["lifecycle_status"]
                    else candidate.lifecycle_status
                )

                if existing:
                    conn.execute(
                        """
                        UPDATE radar_keyword_candidates
                        SET source_type = ?, source_detail = ?, lifecycle_status = ?,
                            variant_type = ?, confidence = ?, updated_at = ?
                        WHERE id = ?
                        """,
                        (
                            candidate.source_type,
                            candidate.source_detail,
                            lifecycle_status,
                            candidate.variant_type,
                            candidate.confidence,
                            now,
                            int(existing["id"]),
                        ),
                    )
                else:
                    conn.execute(
                        """
                        INSERT INTO radar_keyword_candidates (
                            direction_id, keyword, source_type, source_detail,
                            lifecycle_status, variant_type, confidence,
                            created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            direction_id,
                            candidate.keyword,
                            candidate.source_type,
                            candidate.source_detail,
                            lifecycle_status,
                            candidate.variant_type,
                            candidate.confidence,
                            created_at,
                            now,
                        ),
                    )
            conn.commit()
        return self._find_by_direction_id_sync(direction_id)
