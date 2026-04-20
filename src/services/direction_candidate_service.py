"""
Finder 方向候选词服务。
"""
from __future__ import annotations

from src.domain.models.direction_candidate import DirectionCandidate
from src.domain.repositories.direction_candidate_repository import DirectionCandidateRepository
from src.domain.repositories.direction_repository import DirectionRepository
from src.infrastructure.persistence.sqlite_bootstrap import bootstrap_sqlite_storage
from src.infrastructure.persistence.sqlite_connection import sqlite_connection
from src.services.keyword_expansion_service import (
    build_cooccurrence_candidates,
    build_llm_candidates,
    build_rule_based_candidates,
)


class DirectionCandidateService:
    def __init__(
        self,
        candidate_repository: DirectionCandidateRepository,
        direction_repository: DirectionRepository,
        db_path: str | None = None,
        legacy_config_file: str | None = None,
    ):
        self.candidate_repository = candidate_repository
        self.direction_repository = direction_repository
        self.db_path = db_path
        self.legacy_config_file = legacy_config_file

    async def list_candidates(self, direction_id: int) -> list[DirectionCandidate]:
        return await self.candidate_repository.find_by_direction_id(direction_id)

    async def generate_candidates(
        self,
        direction_id: int,
        *,
        include_llm: bool = True,
        max_llm_candidates: int = 12,
    ) -> tuple[list[DirectionCandidate], dict[str, int | bool]]:
        direction = await self.direction_repository.find_by_id(direction_id)
        if not direction:
            raise ValueError(f"方向 {direction_id} 不存在")

        generated_candidates = build_rule_based_candidates(direction)
        cooccurrence_candidates = self._build_cooccurrence_candidates(direction, generated_candidates)
        generated_candidates.extend(cooccurrence_candidates)
        llm_candidates: list[DirectionCandidate] = []
        if include_llm:
            llm_candidates = await build_llm_candidates(
                direction,
                generated_candidates,
                max_candidates=max_llm_candidates,
            )
            generated_candidates.extend(llm_candidates)
        if not generated_candidates:
            return [], {
                "include_llm": include_llm,
                "rule_generated": 0,
                "llm_generated": 0,
            }
        saved = await self.candidate_repository.save_many(generated_candidates)
        return saved, {
            "include_llm": include_llm,
            "rule_generated": len([item for item in generated_candidates if item.source_type == "rule"]),
            "cooccurrence_generated": len(cooccurrence_candidates),
            "llm_generated": len(llm_candidates),
        }

    def _build_cooccurrence_candidates(
        self,
        direction,
        existing_candidates: list[DirectionCandidate],
    ) -> list[DirectionCandidate]:
        bootstrap_sqlite_storage(self.db_path, legacy_config_file=self.legacy_config_file)
        with sqlite_connection(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT title, keyword
                FROM result_items
                WHERE lower(keyword) = lower(?) OR title LIKE ?
                ORDER BY crawl_time DESC
                LIMIT 300
                """,
                (direction.seed_topic, f"%{direction.seed_topic}%"),
            ).fetchall()
        titles = [str(row["title"] or "") for row in rows if row["title"]]
        return build_cooccurrence_candidates(direction, titles, existing_candidates)
