"""
Finder 方向推荐路由。
"""
from __future__ import annotations

from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException

from src.api.dependencies import (
    get_direction_candidate_insight_service,
    get_direction_candidate_service,
    get_direction_recommendation_service,
)
from src.services.direction_candidate_insight_service import DirectionCandidateInsightService
from src.services.direction_candidate_service import DirectionCandidateService
from src.services.direction_recommendation_service import DirectionRecommendationService


router = APIRouter(prefix="/api/finder", tags=["finder-recommendations"])


class RecommendationUpdatePayload(BaseModel):
    status: str = Field(..., min_length=1, max_length=32)


@router.get("/directions/{direction_id}/recommendations", response_model=dict)
async def get_direction_recommendations(
    direction_id: int,
    service: DirectionRecommendationService = Depends(get_direction_recommendation_service),
):
    return {"items": await service.list_direction_recommendations(direction_id)}


@router.post("/directions/{direction_id}/refresh-recommendations", response_model=dict)
async def refresh_direction_recommendations(
    direction_id: int,
    candidate_service: DirectionCandidateService = Depends(get_direction_candidate_service),
    insight_service: DirectionCandidateInsightService = Depends(get_direction_candidate_insight_service),
    recommendation_service: DirectionRecommendationService = Depends(get_direction_recommendation_service),
):
    """刷新推荐：先重新计算候选词洞察（从 result_items 拉取最新市场数据），再生成推荐。"""
    candidates = await candidate_service.list_candidates(direction_id)
    enriched = await insight_service.refresh_direction_candidates(direction_id, candidates)
    items = await recommendation_service.refresh_direction_recommendations(direction_id, enriched)
    return {"items": items, "count": len(items)}


@router.post("/directions/{direction_id}/generate-recommendations", response_model=dict)
async def generate_recommendations_from_current_state(
    direction_id: int,
    candidate_service: DirectionCandidateService = Depends(get_direction_candidate_service),
    insight_service: DirectionCandidateInsightService = Depends(get_direction_candidate_insight_service),
    recommendation_service: DirectionRecommendationService = Depends(get_direction_recommendation_service),
):
    """直接从当前 DB 状态生成推荐（跳过 result_items 洞察刷新）。
    用于：手动已写入 opportunity_states 后直接触发推荐，或在无 result_items 数据时生成推荐。
    """
    candidates = await candidate_service.list_candidates(direction_id)
    enriched = await insight_service.list_direction_candidates(direction_id, candidates)
    items = await recommendation_service.refresh_direction_recommendations(direction_id, enriched)
    return {"items": items, "count": len(items)}


@router.patch("/recommendations/{recommendation_id}", response_model=dict)
async def update_recommendation(
    recommendation_id: int,
    payload: RecommendationUpdatePayload,
    service: DirectionRecommendationService = Depends(get_direction_recommendation_service),
):
    try:
        item = await service.update_recommendation_status(recommendation_id, payload.status)
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "不存在" in message else 400
        raise HTTPException(status_code=status_code, detail=message) from exc
    return {"item": item}
