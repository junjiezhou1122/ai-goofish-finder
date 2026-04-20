"""
Finder 方向候选词路由。
"""
from __future__ import annotations

from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException

from src.api.dependencies import (
    get_direction_candidate_insight_service,
    get_direction_candidate_service,
)
from src.services.direction_candidate_insight_service import DirectionCandidateInsightService
from src.services.direction_candidate_service import DirectionCandidateService


router = APIRouter(prefix="/api/finder/directions", tags=["finder-candidates"])


class GenerateCandidatesPayload(BaseModel):
    include_llm: bool = Field(default=True)
    max_llm_candidates: int = Field(default=12, ge=1, le=20)


@router.get("/{direction_id}/candidates", response_model=dict)
async def get_direction_candidates(
    direction_id: int,
    service: DirectionCandidateService = Depends(get_direction_candidate_service),
    insight_service: DirectionCandidateInsightService = Depends(get_direction_candidate_insight_service),
):
    items = await service.list_candidates(direction_id)
    enriched = await insight_service.list_direction_candidates(direction_id, items)
    return {"items": enriched}


@router.post("/{direction_id}/generate-candidates", response_model=dict)
async def generate_direction_candidates(
    direction_id: int,
    payload: GenerateCandidatesPayload | None = None,
    service: DirectionCandidateService = Depends(get_direction_candidate_service),
    insight_service: DirectionCandidateInsightService = Depends(get_direction_candidate_insight_service),
):
    try:
        payload = payload or GenerateCandidatesPayload()
        items, meta = await service.generate_candidates(
            direction_id,
            include_llm=payload.include_llm,
            max_llm_candidates=payload.max_llm_candidates,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    enriched = await insight_service.list_direction_candidates(direction_id, items)
    return {
        "items": enriched,
        "count": len(items),
        **meta,
    }


@router.post("/{direction_id}/refresh-candidates", response_model=dict)
async def refresh_direction_candidates(
    direction_id: int,
    service: DirectionCandidateService = Depends(get_direction_candidate_service),
    insight_service: DirectionCandidateInsightService = Depends(get_direction_candidate_insight_service),
):
    items = await service.list_candidates(direction_id)
    enriched = await insight_service.refresh_direction_candidates(direction_id, items)
    return {"items": enriched, "count": len(enriched)}
