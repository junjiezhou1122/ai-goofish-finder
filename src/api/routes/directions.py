"""
Finder Direction 路由。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from src.api.dependencies import get_direction_service
from src.domain.models.direction import DirectionCreate, DirectionUpdate
from src.services.direction_service import DirectionService


router = APIRouter(prefix="/api/finder/directions", tags=["finder-directions"])


@router.get("", response_model=list[dict])
async def get_directions(service: DirectionService = Depends(get_direction_service)):
    directions = await service.get_all_directions()
    return [direction.model_dump(mode="json") for direction in directions]


@router.get("/{direction_id}", response_model=dict)
async def get_direction(direction_id: int, service: DirectionService = Depends(get_direction_service)):
    direction = await service.get_direction(direction_id)
    if not direction:
        raise HTTPException(status_code=404, detail="方向未找到")
    return direction.model_dump(mode="json")


@router.post("", response_model=dict)
async def create_direction(
    payload: DirectionCreate,
    service: DirectionService = Depends(get_direction_service),
):
    direction = await service.create_direction(payload)
    return {"message": "方向创建成功", "direction": direction.model_dump(mode="json")}


@router.patch("/{direction_id}", response_model=dict)
async def update_direction(
    direction_id: int,
    payload: DirectionUpdate,
    service: DirectionService = Depends(get_direction_service),
):
    try:
        direction = await service.update_direction(direction_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"message": "方向更新成功", "direction": direction.model_dump(mode="json")}


@router.delete("/{direction_id}", response_model=dict)
async def delete_direction(
    direction_id: int,
    service: DirectionService = Depends(get_direction_service),
):
    deleted = await service.delete_direction(direction_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="方向未找到")
    return {"message": "方向删除成功"}
