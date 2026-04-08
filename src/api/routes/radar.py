"""
雷达分析路由。
"""
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Query

from src.services.radar_service import (
    RadarNotFoundError,
    build_radar_overview,
    create_keyword_pool_item,
    create_radar_snapshot,
    delete_keyword_pool_item,
    get_radar_snapshot,
    list_keyword_pool,
    list_radar_keywords,
    list_radar_recommendations,
    list_radar_snapshot_keywords,
    list_radar_snapshots,
    refresh_radar_recommendations,
    save_keyword_annotation,
    update_keyword_pool_item,
    update_radar_recommendation,
)


router = APIRouter(prefix="/api/radar", tags=["radar"])


class KeywordAnnotationPayload(BaseModel):
    status: str = Field(..., min_length=1, max_length=32)
    note: str = Field(default="", max_length=1000)


class KeywordPoolCreatePayload(BaseModel):
    keyword: str = Field(..., min_length=1, max_length=100)
    source: str = Field(default="manual", min_length=1, max_length=32)
    note: str = Field(default="", max_length=1000)


class KeywordPoolUpdatePayload(BaseModel):
    keyword: str | None = Field(default=None, min_length=1, max_length=100)
    source: str | None = Field(default=None, min_length=1, max_length=32)
    note: str | None = Field(default=None, max_length=1000)


class SnapshotCreatePayload(BaseModel):
    note: str = Field(default="", max_length=1000)


class RecommendationUpdatePayload(BaseModel):
    status: str = Field(..., min_length=1, max_length=32)
    add_to_pool: bool = False


@router.get("/overview")
async def get_radar_overview(limit: int = Query(12, ge=1, le=100)):
    try:
        return await build_radar_overview(limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"加载雷达概览失败: {exc}")


@router.get("/keywords")
async def get_radar_keywords(
    limit: int = Query(50, ge=1, le=200),
    sort_by: str = Query("opportunity_score"),
    sort_order: str = Query("desc"),
):
    try:
        return {
            "items": await list_radar_keywords(
                limit,
                sort_by=sort_by.strip(),
                sort_order=sort_order.strip().lower(),
            )
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"加载关键词雷达失败: {exc}")


@router.put("/keywords/{keyword}")
async def update_keyword_annotation(keyword: str, payload: KeywordAnnotationPayload):
    try:
        annotation = await save_keyword_annotation(
            keyword,
            status=payload.status.strip().lower(),
            note=payload.note,
        )
        return {"annotation": annotation}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"保存关键词标注失败: {exc}")


@router.get("/pool")
async def get_keyword_pool():
    try:
        return {"items": await list_keyword_pool()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"加载候选词池失败: {exc}")


@router.post("/pool")
async def create_pool_item(payload: KeywordPoolCreatePayload):
    try:
        item = await create_keyword_pool_item(
            payload.keyword,
            source=payload.source.strip().lower(),
            note=payload.note,
        )
        return {"item": item}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"创建候选词失败: {exc}")


@router.put("/pool/{item_id}")
async def update_pool_item(item_id: int, payload: KeywordPoolUpdatePayload):
    try:
        item = await update_keyword_pool_item(
            item_id,
            keyword=payload.keyword.strip() if payload.keyword is not None else None,
            source=payload.source.strip().lower() if payload.source is not None else None,
            note=payload.note,
        )
        return {"item": item}
    except RadarNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"更新候选词失败: {exc}")


@router.delete("/pool/{item_id}")
async def remove_pool_item(item_id: int):
    try:
        return await delete_keyword_pool_item(item_id)
    except RadarNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"删除候选词失败: {exc}")


@router.get("/snapshots")
async def get_radar_snapshots(limit: int = Query(10, ge=1, le=100)):
    try:
        return {"items": await list_radar_snapshots(limit)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"加载快照列表失败: {exc}")


@router.post("/snapshots")
async def create_snapshot(payload: SnapshotCreatePayload):
    try:
        snapshot = await create_radar_snapshot(payload.note)
        return {"snapshot": snapshot}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"创建快照失败: {exc}")


@router.get("/snapshots/{snapshot_id}")
async def get_snapshot(snapshot_id: int):
    try:
        return {"snapshot": await get_radar_snapshot(snapshot_id)}
    except RadarNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"加载快照失败: {exc}")


@router.get("/snapshots/{snapshot_id}/keywords")
async def get_snapshot_keywords(
    snapshot_id: int,
    limit: int = Query(50, ge=1, le=500),
):
    try:
        return {"items": await list_radar_snapshot_keywords(snapshot_id, limit)}
    except RadarNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"加载快照关键词失败: {exc}")


@router.get("/recommendations")
async def get_radar_recommendations(
    limit: int = Query(20, ge=1, le=100),
    min_score: int = Query(0, ge=0, le=100),
    variant_type: list[str] = Query(default=[]),
):
    try:
        return {
            "items": await list_radar_recommendations(
                limit,
                min_score=min_score,
                variant_types=variant_type,
            )
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"加载推荐关键词失败: {exc}")


@router.post("/recommendations/refresh")
async def refresh_recommendations(
    limit: int = Query(20, ge=1, le=100),
    min_score: int = Query(0, ge=0, le=100),
    variant_type: list[str] = Query(default=[]),
):
    try:
        return {
            "items": await refresh_radar_recommendations(
                limit,
                min_score=min_score,
                variant_types=variant_type,
            )
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"刷新推荐关键词失败: {exc}")


@router.put("/recommendations/{recommendation_id}")
async def update_recommendation(
    recommendation_id: int,
    payload: RecommendationUpdatePayload,
):
    try:
        item = await update_radar_recommendation(
            recommendation_id,
            status=payload.status.strip().lower(),
            add_to_pool=payload.add_to_pool,
        )
        return {"item": item}
    except RadarNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"更新推荐关键词失败: {exc}")
