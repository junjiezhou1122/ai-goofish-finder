"""
Direction 仓储接口。
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain.models.direction import Direction


class DirectionRepository(ABC):
    @abstractmethod
    async def find_all(self) -> list[Direction]:
        pass

    @abstractmethod
    async def find_by_id(self, direction_id: int) -> Direction | None:
        pass

    @abstractmethod
    async def save(self, direction: Direction) -> Direction:
        pass

    @abstractmethod
    async def delete(self, direction_id: int) -> bool:
        pass
