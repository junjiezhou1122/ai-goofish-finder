"""
Finder Direction 服务。
"""
from __future__ import annotations

from datetime import UTC, datetime

from src.domain.models.direction import Direction, DirectionCreate, DirectionUpdate
from src.domain.repositories.direction_repository import DirectionRepository


class DirectionService:
    def __init__(self, repository: DirectionRepository):
        self.repository = repository

    async def get_all_directions(self) -> list[Direction]:
        return await self.repository.find_all()

    async def get_direction(self, direction_id: int) -> Direction | None:
        return await self.repository.find_by_id(direction_id)

    async def create_direction(self, payload: DirectionCreate) -> Direction:
        now = datetime.now(UTC)
        direction = Direction(**payload.model_dump(), created_at=now, updated_at=now)
        saved = await self.repository.save(direction)

        # 注册定时刷新任务（lazy import 避免循环依赖）
        try:
            from src.services.direction_scheduler import register_direction_refresh
            register_direction_refresh(saved)
        except Exception:
            # 测试环境或 event loop 未启动时不阻塞方向创建
            import logging
            logging.getLogger(__name__).warning("无法注册方向刷新任务（scheduler 未就绪）", exc_info=True)

        return saved

    async def update_direction(self, direction_id: int, payload: DirectionUpdate) -> Direction:
        existing = await self.repository.find_by_id(direction_id)
        if not existing:
            raise ValueError(f"方向 {direction_id} 不存在")
        updated = existing.model_copy(update={**payload.model_dump(exclude_unset=True), "updated_at": datetime.now(UTC)})
        return await self.repository.save(updated)

    async def delete_direction(self, direction_id: int) -> bool:
        # 移除定时刷新任务
        try:
            from src.services.direction_scheduler import unregister_direction_refresh
            unregister_direction_refresh(direction_id)
        except Exception:
            import logging
            logging.getLogger(__name__).warning("无法移除方向刷新任务（scheduler 未就绪）", exc_info=True)
        return await self.repository.delete(direction_id)
