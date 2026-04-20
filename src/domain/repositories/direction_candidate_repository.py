"""
Finder 方向候选词仓储接口。
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain.models.direction_candidate import DirectionCandidate


class DirectionCandidateRepository(ABC):
    @abstractmethod
    async def find_by_direction_id(self, direction_id: int) -> list[DirectionCandidate]:
        pass

    @abstractmethod
    async def save_many(self, candidates: list[DirectionCandidate]) -> list[DirectionCandidate]:
        pass
