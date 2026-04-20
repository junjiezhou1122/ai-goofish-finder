"""
Finder 实验路由。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from src.api.dependencies import get_direction_experiment_service
from src.services.direction_experiment_service import DirectionExperimentService


router = APIRouter(prefix="/api/finder/directions", tags=["finder-experiments"])


@router.get("/{direction_id}/experiments", response_model=dict)
async def get_direction_experiments(
    direction_id: int,
    service: DirectionExperimentService = Depends(get_direction_experiment_service),
):
    return {"items": await service.list_direction_experiments(direction_id)}
