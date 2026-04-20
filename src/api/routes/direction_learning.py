"""
Finder 学习摘要路由。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from src.api.dependencies import get_direction_learning_service
from src.services.direction_learning_service import DirectionLearningService


router = APIRouter(prefix="/api/finder/directions", tags=["finder-learning"])


@router.get("/{direction_id}/learning-summary", response_model=dict)
async def get_direction_learning_summary(
    direction_id: int,
    service: DirectionLearningService = Depends(get_direction_learning_service),
):
    return {"summary": await service.get_direction_summary(direction_id)}
