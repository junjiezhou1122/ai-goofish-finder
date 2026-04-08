"""
雷达分析服务。
基于现有结果表聚合关键词热度、价格带和机会分。
"""
from __future__ import annotations

import asyncio
import json
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from statistics import median
from typing import Any, Literal

from src.infrastructure.persistence.sqlite_bootstrap import bootstrap_sqlite_storage
from src.infrastructure.persistence.sqlite_connection import sqlite_connection


SIGNAL_TERMS = (
    "秒发",
    "自动发货",
    "教程",
    "源码",
    "脚本",
    "模板",
    "代搭建",
    "代配置",
    "永久",
    "合集",
)
PRODUCT_VARIANT_SIGNALS = ("教程", "源码", "脚本", "模板", "合集")
SERVICE_VARIANT_SIGNALS = ("代搭建", "代配置")
DELIVERY_VARIANT_SIGNALS = ("自动发货", "秒发", "永久")
SIGNAL_GROUPS = (
    PRODUCT_VARIANT_SIGNALS,
    SERVICE_VARIANT_SIGNALS,
    DELIVERY_VARIANT_SIGNALS,
)

AnnotationStatus = Literal["watch", "test", "sourced", "risky", "drop"]
PoolSource = Literal["manual", "radar", "recommendation"]
RecommendationStatus = Literal["pending", "accepted", "dismissed"]
RecommendationVariantType = Literal["product", "service", "delivery", "generic"]

DEFAULT_ANNOTATION_STATUS: AnnotationStatus = "watch"
DEFAULT_POOL_SOURCE: PoolSource = "manual"
DEFAULT_RECOMMENDATION_STATUS: RecommendationStatus = "pending"

VALID_SORT_FIELDS = {
    "opportunity_score",
    "recent_items_24h",
    "total_items",
    "growth_delta",
    "signal_hits",
    "median_price",
    "latest_crawl_time",
    "keyword",
}


class RadarNotFoundError(ValueError):
    pass


@dataclass
class KeywordRadarAggregate:
    keyword: str
    total_items: int = 0
    recent_items_24h: int = 0
    previous_items_24h: int = 0
    recommended_items: int = 0
    ai_recommended_items: int = 0
    unique_sellers: set[str] = field(default_factory=set)
    prices: list[float] = field(default_factory=list)
    signal_counter: Counter[str] = field(default_factory=Counter)
    latest_crawl_time: datetime | None = None


@dataclass
class RadarKeywordItem:
    keyword: str
    total_items: int
    recent_items_24h: int
    previous_items_24h: int
    growth_delta: int
    unique_sellers: int
    recommended_items: int
    ai_recommended_items: int
    min_price: float | None
    median_price: float | None
    avg_price: float | None
    max_price: float | None
    price_spread: float | None
    signal_hits: int
    top_signals: list[str]
    opportunity_score: int
    latest_crawl_time: str | None
    annotation_status: AnnotationStatus
    annotation_note: str
    annotation_updated_at: str | None


async def build_radar_overview(limit: int = 12) -> dict[str, Any]:
    return await asyncio.to_thread(_build_radar_overview_sync, limit)


async def list_radar_keywords(
    limit: int = 50,
    *,
    sort_by: str = "opportunity_score",
    sort_order: str = "desc",
) -> list[dict[str, Any]]:
    return await asyncio.to_thread(_list_radar_keywords_sync, limit, sort_by, sort_order)


async def save_keyword_annotation(
    keyword: str,
    *,
    status: AnnotationStatus,
    note: str,
) -> dict[str, Any]:
    return await asyncio.to_thread(_save_keyword_annotation_sync, keyword, status, note)


async def list_keyword_pool() -> list[dict[str, Any]]:
    return await asyncio.to_thread(_list_keyword_pool_sync)


async def create_keyword_pool_item(
    keyword: str,
    *,
    source: PoolSource = DEFAULT_POOL_SOURCE,
    note: str = "",
) -> dict[str, Any]:
    return await asyncio.to_thread(_create_keyword_pool_item_sync, keyword, source, note)


async def update_keyword_pool_item(
    item_id: int,
    *,
    keyword: str | None = None,
    source: str | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    return await asyncio.to_thread(_update_keyword_pool_item_sync, item_id, keyword, source, note)


async def delete_keyword_pool_item(item_id: int) -> dict[str, Any]:
    return await asyncio.to_thread(_delete_keyword_pool_item_sync, item_id)


async def list_radar_snapshots(limit: int = 10) -> list[dict[str, Any]]:
    return await asyncio.to_thread(_list_radar_snapshots_sync, limit)


async def create_radar_snapshot(note: str = "") -> dict[str, Any]:
    return await asyncio.to_thread(_create_radar_snapshot_sync, note)


async def get_radar_snapshot(snapshot_id: int) -> dict[str, Any]:
    return await asyncio.to_thread(_get_radar_snapshot_sync, snapshot_id)


async def list_radar_snapshot_keywords(snapshot_id: int, limit: int = 50) -> list[dict[str, Any]]:
    return await asyncio.to_thread(_list_radar_snapshot_keywords_sync, snapshot_id, limit)


async def list_radar_recommendations(
    limit: int = 20,
    *,
    min_score: int = 0,
    variant_types: list[str] | None = None,
) -> list[dict[str, Any]]:
    return await asyncio.to_thread(_list_radar_recommendations_sync, limit, min_score, variant_types)


async def refresh_radar_recommendations(
    limit: int = 20,
    *,
    min_score: int = 0,
    variant_types: list[str] | None = None,
) -> list[dict[str, Any]]:
    return await asyncio.to_thread(_refresh_radar_recommendations_sync, limit, min_score, variant_types)


async def update_radar_recommendation(
    recommendation_id: int,
    *,
    status: RecommendationStatus,
    add_to_pool: bool = False,
) -> dict[str, Any]:
    return await asyncio.to_thread(
        _update_radar_recommendation_sync,
        recommendation_id,
        status,
        add_to_pool,
    )


def _build_radar_overview_sync(limit: int) -> dict[str, Any]:
    keyword_items = _list_radar_keywords_sync(
        limit=0,
        sort_by="opportunity_score",
        sort_order="desc",
    )
    top_opportunities = keyword_items[: max(limit, 1)]
    total_items = sum(int(item["total_items"]) for item in keyword_items)
    recent_items = sum(int(item["recent_items_24h"]) for item in keyword_items)
    scores = [int(item["opportunity_score"]) for item in keyword_items]
    signal_counter: Counter[str] = Counter()
    for item in keyword_items:
        for signal in item["top_signals"]:
            signal_counter[signal] += 1

    return {
        "summary": {
            "keywords_tracked": len(keyword_items),
            "total_items": total_items,
            "recent_items_24h": recent_items,
            "high_opportunity_keywords": sum(1 for score in scores if score >= 70),
            "average_opportunity_score": round(sum(scores) / len(scores), 1) if scores else 0,
        },
        "top_opportunities": top_opportunities,
        "top_signals": [
            {"term": term, "count": count}
            for term, count in signal_counter.most_common(8)
        ],
    }


def _list_radar_keywords_sync(
    limit: int,
    sort_by: str = "opportunity_score",
    sort_order: str = "desc",
) -> list[dict[str, Any]]:
    bootstrap_sqlite_storage()
    rows = _load_radar_rows()
    keyword_map = _aggregate_rows(rows)
    annotations = _load_keyword_annotations()
    keyword_items = [
        _serialize_keyword_item(_build_keyword_item(keyword, aggregate, annotations.get(keyword)))
        for keyword, aggregate in keyword_map.items()
    ]
    _sort_keyword_items(keyword_items, sort_by, sort_order)
    if limit and limit > 0:
        return keyword_items[:limit]
    return keyword_items


def _sort_keyword_items(items: list[dict[str, Any]], sort_by: str, sort_order: str) -> None:
    normalized_sort_by = sort_by if sort_by in VALID_SORT_FIELDS else "opportunity_score"
    reverse = str(sort_order).lower() != "asc"

    def key_func(item: dict[str, Any]) -> tuple[Any, ...]:
        primary: Any
        if normalized_sort_by == "keyword":
            primary = str(item.get("keyword") or "").lower()
        elif normalized_sort_by == "latest_crawl_time":
            primary = str(item.get("latest_crawl_time") or "")
        else:
            primary = item.get(normalized_sort_by)
            if primary is None:
                primary = -1

        return (
            primary,
            int(item.get("opportunity_score") or 0),
            int(item.get("recent_items_24h") or 0),
            int(item.get("total_items") or 0),
            str(item.get("latest_crawl_time") or ""),
            str(item.get("keyword") or "").lower(),
        )

    items.sort(key=key_func, reverse=reverse)


def _load_radar_rows() -> list[dict[str, Any]]:
    with sqlite_connection() as conn:
        rows = conn.execute(
            """
            SELECT keyword, crawl_time, price, seller_nickname, is_recommended, analysis_source, title
            FROM result_items
            WHERE keyword IS NOT NULL AND TRIM(keyword) != ''
            ORDER BY crawl_time DESC, id DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def _load_keyword_annotations() -> dict[str, dict[str, Any]]:
    with sqlite_connection() as conn:
        rows = conn.execute(
            """
            SELECT keyword, status, note, updated_at
            FROM keyword_annotations
            """
        ).fetchall()
    return {
        str(row["keyword"]): {
            "status": _normalize_annotation_status(row["status"]),
            "note": str(row["note"] or ""),
            "updated_at": str(row["updated_at"] or "") or None,
        }
        for row in rows
    }


def _save_keyword_annotation_sync(keyword: str, status: AnnotationStatus, note: str) -> dict[str, Any]:
    bootstrap_sqlite_storage()
    clean_keyword = str(keyword or "").strip()
    if not clean_keyword:
        raise ValueError("关键词不能为空")

    normalized_status = _normalize_annotation_status(status)
    normalized_note = str(note or "").strip()
    updated_at = _serialize_timestamp(datetime.now(timezone.utc))

    with sqlite_connection() as conn:
        conn.execute(
            """
            INSERT INTO keyword_annotations (keyword, status, note, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(keyword) DO UPDATE SET
                status = excluded.status,
                note = excluded.note,
                updated_at = excluded.updated_at
            """,
            (clean_keyword, normalized_status, normalized_note, updated_at),
        )
        conn.commit()

    return {
        "keyword": clean_keyword,
        "status": normalized_status,
        "note": normalized_note,
        "updated_at": updated_at,
    }


def _list_keyword_pool_sync() -> list[dict[str, Any]]:
    bootstrap_sqlite_storage()
    with sqlite_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, keyword, source, note, created_at, updated_at
            FROM radar_keyword_pool
            ORDER BY updated_at DESC, id DESC
            """
        ).fetchall()
    return [_serialize_pool_row(dict(row)) for row in rows]


def _create_keyword_pool_item_sync(keyword: str, source: PoolSource, note: str) -> dict[str, Any]:
    bootstrap_sqlite_storage()
    clean_keyword = _normalize_keyword(keyword)
    normalized_source = _normalize_pool_source(source)
    normalized_note = str(note or "").strip()
    now = _serialize_timestamp(datetime.now(timezone.utc))

    with sqlite_connection() as conn:
        _upsert_pool_item(conn, clean_keyword, normalized_source, normalized_note, now)
        conn.commit()
        row = _load_pool_row_by_keyword(conn, clean_keyword)
    if row is None:
        raise RadarNotFoundError("候选关键词不存在")
    return _serialize_pool_row(dict(row))


def _update_keyword_pool_item_sync(
    item_id: int,
    keyword: str | None,
    source: str | None,
    note: str | None,
) -> dict[str, Any]:
    bootstrap_sqlite_storage()
    with sqlite_connection() as conn:
        row = _load_pool_row_by_id(conn, item_id)
        if row is None:
            raise RadarNotFoundError("候选关键词不存在")

        next_keyword = _normalize_keyword(keyword) if keyword is not None else str(row["keyword"])
        next_source = _normalize_pool_source(source) if source is not None else _normalize_pool_source(row["source"])
        next_note = str(note).strip() if note is not None else str(row["note"] or "")
        now = _serialize_timestamp(datetime.now(timezone.utc))

        conn.execute(
            """
            UPDATE radar_keyword_pool
            SET keyword = ?, source = ?, note = ?, updated_at = ?
            WHERE id = ?
            """,
            (next_keyword, next_source, next_note, now, item_id),
        )
        conn.commit()
        updated = _load_pool_row_by_id(conn, item_id)
    if updated is None:
        raise RadarNotFoundError("候选关键词不存在")
    return _serialize_pool_row(dict(updated))


def _delete_keyword_pool_item_sync(item_id: int) -> dict[str, Any]:
    bootstrap_sqlite_storage()
    with sqlite_connection() as conn:
        row = _load_pool_row_by_id(conn, item_id)
        if row is None:
            raise RadarNotFoundError("候选关键词不存在")
        conn.execute("DELETE FROM radar_keyword_pool WHERE id = ?", (item_id,))
        conn.commit()
    return {"deleted": True, "id": item_id}


def _create_radar_snapshot_sync(note: str) -> dict[str, Any]:
    bootstrap_sqlite_storage()
    keyword_items = _list_radar_keywords_sync(
        limit=0,
        sort_by="opportunity_score",
        sort_order="desc",
    )
    created_at = _serialize_timestamp(datetime.now(timezone.utc))
    normalized_note = str(note or "").strip()
    keyword_count = len(keyword_items)
    average_score = round(
        sum(int(item["opportunity_score"]) for item in keyword_items) / keyword_count,
        1,
    ) if keyword_items else 0
    top_keyword = keyword_items[0]["keyword"] if keyword_items else None

    with sqlite_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO radar_snapshot_runs (note, created_at, keyword_count, average_score, top_keyword)
            VALUES (?, ?, ?, ?, ?)
            """,
            (normalized_note, created_at, keyword_count, average_score, top_keyword),
        )
        snapshot_id = int(cursor.lastrowid or 0)
        if keyword_items:
            conn.executemany(
                """
                INSERT INTO radar_snapshot_keywords (
                    snapshot_id,
                    keyword,
                    opportunity_score,
                    recent_items_24h,
                    total_items,
                    unique_sellers,
                    recommended_items,
                    signal_hits,
                    median_price,
                    price_spread,
                    latest_crawl_time
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        snapshot_id,
                        item["keyword"],
                        item["opportunity_score"],
                        item["recent_items_24h"],
                        item["total_items"],
                        item["unique_sellers"],
                        item["recommended_items"],
                        item["signal_hits"],
                        item["median_price"],
                        item["price_spread"],
                        item["latest_crawl_time"],
                    )
                    for item in keyword_items
                ],
            )
        conn.commit()
        snapshot = _load_snapshot_summary_by_id(conn, snapshot_id)
    if snapshot is None:
        raise RadarNotFoundError("快照不存在")
    return snapshot


def _list_radar_snapshots_sync(limit: int) -> list[dict[str, Any]]:
    bootstrap_sqlite_storage()
    with sqlite_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, note, created_at, keyword_count, average_score, top_keyword
            FROM radar_snapshot_runs
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [_serialize_snapshot_row(dict(row)) for row in rows]


def _get_radar_snapshot_sync(snapshot_id: int) -> dict[str, Any]:
    bootstrap_sqlite_storage()
    with sqlite_connection() as conn:
        snapshot = _load_snapshot_summary_by_id(conn, snapshot_id)
    if snapshot is None:
        raise RadarNotFoundError("快照不存在")
    return snapshot


def _list_radar_snapshot_keywords_sync(snapshot_id: int, limit: int) -> list[dict[str, Any]]:
    bootstrap_sqlite_storage()
    with sqlite_connection() as conn:
        snapshot = _load_snapshot_summary_by_id(conn, snapshot_id)
        if snapshot is None:
            raise RadarNotFoundError("快照不存在")
        rows = conn.execute(
            """
            SELECT
                keyword,
                opportunity_score,
                recent_items_24h,
                total_items,
                unique_sellers,
                recommended_items,
                signal_hits,
                median_price,
                price_spread,
                latest_crawl_time
            FROM radar_snapshot_keywords
            WHERE snapshot_id = ?
            ORDER BY opportunity_score DESC, recent_items_24h DESC, total_items DESC, keyword ASC
            LIMIT ?
            """,
            (snapshot_id, limit),
        ).fetchall()
    return [_serialize_snapshot_keyword_row(dict(row)) for row in rows]


def _list_radar_recommendations_sync(
    limit: int,
    min_score: int = 0,
    variant_types: list[str] | None = None,
) -> list[dict[str, Any]]:
    bootstrap_sqlite_storage()
    normalized_min_score = max(0, int(min_score or 0))
    normalized_variant_types = _normalize_variant_types(variant_types)
    with sqlite_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, keyword, reason, score, signal_terms_json, source_keywords_json, status, created_at, updated_at
            FROM radar_keyword_recommendations
            ORDER BY
                CASE status
                    WHEN 'pending' THEN 0
                    WHEN 'accepted' THEN 1
                    ELSE 2
                END,
                score DESC,
                updated_at DESC,
                id DESC
            """
        ).fetchall()
    items = [_serialize_recommendation_row(dict(row)) for row in rows]
    filtered = [
        item for item in items
        if item["score"] >= normalized_min_score
        and (not normalized_variant_types or item["variant_type"] in normalized_variant_types)
    ]
    if limit and limit > 0:
        return filtered[:limit]
    return filtered


def _refresh_radar_recommendations_sync(
    limit: int,
    min_score: int = 0,
    variant_types: list[str] | None = None,
) -> list[dict[str, Any]]:
    bootstrap_sqlite_storage()
    keyword_items = _list_radar_keywords_sync(
        limit=0,
        sort_by="opportunity_score",
        sort_order="desc",
    )

    with sqlite_connection() as conn:
        pool_rows = conn.execute("SELECT keyword FROM radar_keyword_pool").fetchall()
        pool_keywords = {str(row["keyword"]).strip() for row in pool_rows if row["keyword"]}
        candidates = _build_recommendation_candidates(keyword_items, pool_keywords)
        now = _serialize_timestamp(datetime.now(timezone.utc))
        for candidate in candidates:
            conn.execute(
                """
                INSERT INTO radar_keyword_recommendations (
                    keyword,
                    reason,
                    score,
                    signal_terms_json,
                    source_keywords_json,
                    status,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(keyword) DO UPDATE SET
                    reason = excluded.reason,
                    score = excluded.score,
                    signal_terms_json = excluded.signal_terms_json,
                    source_keywords_json = excluded.source_keywords_json,
                    status = CASE
                        WHEN radar_keyword_recommendations.status IN ('accepted', 'dismissed')
                            THEN radar_keyword_recommendations.status
                        ELSE excluded.status
                    END,
                    updated_at = excluded.updated_at
                """,
                (
                    candidate["keyword"],
                    candidate["reason"],
                    candidate["score"],
                    json.dumps(candidate["signal_terms"], ensure_ascii=False),
                    json.dumps(candidate["source_keywords"], ensure_ascii=False),
                    DEFAULT_RECOMMENDATION_STATUS,
                    now,
                    now,
                ),
            )
        conn.commit()

    return _list_radar_recommendations_sync(limit, min_score, variant_types)


def _build_recommendation_candidates(
    keyword_items: list[dict[str, Any]],
    pool_keywords: set[str],
) -> list[dict[str, Any]]:
    tracked_keywords = {str(item.get("keyword") or "").strip() for item in keyword_items}
    candidate_map: dict[str, dict[str, Any]] = {}

    for item in keyword_items:
        keyword = str(item.get("keyword") or "").strip()
        if not keyword:
            continue

        opportunity_score = int(item.get("opportunity_score") or 0)
        recent_items = int(item.get("recent_items_24h") or 0)
        signal_hits = int(item.get("signal_hits") or 0)
        if opportunity_score < 50 or (recent_items <= 0 and signal_hits <= 0):
            continue

        source_signals = [signal for signal in item.get("top_signals") or [] if signal in SIGNAL_TERMS]
        if not source_signals:
            continue

        for signal_group in SIGNAL_GROUPS:
            present_signals = [signal for signal in source_signals if signal in signal_group]
            if not present_signals:
                continue

            for candidate_keyword in _build_signal_group_candidates(keyword, signal_group):
                if candidate_keyword in tracked_keywords or candidate_keyword in pool_keywords:
                    continue

                existing = candidate_map.setdefault(
                    candidate_keyword,
                    {
                        "keyword": candidate_keyword,
                        "score": 0,
                        "signal_terms": set(),
                        "source_keywords": set(),
                        "support_count": 0,
                        "variant_type": _detect_variant_type(candidate_keyword),
                    },
                )
                variant_bonus = _variant_type_bonus(existing["variant_type"])
                freshness_boost = min(10, recent_items * 2)
                evidence_boost = min(12, signal_hits * 2)
                existing["score"] = max(
                    existing["score"],
                    min(100, opportunity_score + variant_bonus + freshness_boost + evidence_boost),
                )
                existing["signal_terms"].update(present_signals)
                existing["source_keywords"].add(keyword)
                existing["support_count"] += 1

    results: list[dict[str, Any]] = []
    for candidate in candidate_map.values():
        source_keywords = sorted(candidate["source_keywords"])
        signal_terms = sorted(candidate["signal_terms"])
        support_bonus = min(14, max(0, candidate["support_count"] - 1) * 5)
        score = min(100, int(candidate["score"]) + support_bonus)
        results.append(
            {
                "keyword": candidate["keyword"],
                "reason": _build_recommendation_reason(
                    source_keywords,
                    signal_terms,
                    str(candidate["variant_type"]),
                ),
                "score": score,
                "signal_terms": signal_terms,
                "source_keywords": source_keywords,
                "variant_type": str(candidate["variant_type"]),
            }
        )

    results.sort(
        key=lambda item: (
            int(item["score"]),
            len(item["source_keywords"]),
            len(item["signal_terms"]),
            item["keyword"],
        ),
        reverse=True,
    )
    return results


def _build_signal_group_candidates(keyword: str, signal_group: tuple[str, ...]) -> list[str]:
    clean_keyword = keyword.strip()
    results: list[str] = []
    for signal in signal_group:
        if signal in clean_keyword:
            continue
        results.append(f"{clean_keyword} {signal}".strip())
    return results


def _detect_variant_type(keyword: str) -> str:
    if any(signal in keyword for signal in PRODUCT_VARIANT_SIGNALS):
        return "product"
    if any(signal in keyword for signal in SERVICE_VARIANT_SIGNALS):
        return "service"
    if any(signal in keyword for signal in DELIVERY_VARIANT_SIGNALS):
        return "delivery"
    return "generic"


def _variant_type_bonus(variant_type: str) -> int:
    if variant_type == "product":
        return 12
    if variant_type == "service":
        return 9
    if variant_type == "delivery":
        return 7
    return 4


def _build_recommendation_reason(
    source_keywords: list[str],
    signal_terms: list[str],
    variant_type: str,
) -> str:
    source_text = '、'.join(source_keywords[:2]) if source_keywords else '近期热词'
    signal_text = '、'.join(signal_terms[:2]) if signal_terms else '强信号词'
    if variant_type == "product":
        return f"{source_text} 的商品形态已经跑出热度，适合继续拆成 {signal_text} 这类可直接售卖的虚拟品词。"
    if variant_type == "service":
        return f"{source_text} 的服务需求在抬头，可以继续测试 {signal_text} 这类偏交付服务的关键词。"
    if variant_type == "delivery":
        return f"{source_text} 标题里反复出现 {signal_text}，说明用户对交付速度和自动化卖点敏感。"
    return f"{source_text} 最近热度较高，标题里频繁出现 {signal_text} 等强信号词。"


def _update_radar_recommendation_sync(
    recommendation_id: int,
    status: RecommendationStatus,
    add_to_pool: bool,
) -> dict[str, Any]:
    bootstrap_sqlite_storage()
    normalized_status = _normalize_recommendation_status(status)
    updated_at = _serialize_timestamp(datetime.now(timezone.utc))

    with sqlite_connection() as conn:
        row = conn.execute(
            """
            SELECT id, keyword, reason, score, signal_terms_json, source_keywords_json, status, created_at, updated_at
            FROM radar_keyword_recommendations
            WHERE id = ?
            """,
            (recommendation_id,),
        ).fetchone()
        if row is None:
            raise RadarNotFoundError("推荐关键词不存在")

        conn.execute(
            "UPDATE radar_keyword_recommendations SET status = ?, updated_at = ? WHERE id = ?",
            (normalized_status, updated_at, recommendation_id),
        )

        if normalized_status == "accepted" and add_to_pool:
            _upsert_pool_item(
                conn,
                _normalize_keyword(row["keyword"]),
                "recommendation",
                str(row["reason"] or "").strip(),
                updated_at,
            )

        conn.commit()
        updated = conn.execute(
            """
            SELECT id, keyword, reason, score, signal_terms_json, source_keywords_json, status, created_at, updated_at
            FROM radar_keyword_recommendations
            WHERE id = ?
            """,
            (recommendation_id,),
        ).fetchone()
    if updated is None:
        raise RadarNotFoundError("推荐关键词不存在")
    return _serialize_recommendation_row(dict(updated))


def _aggregate_rows(rows: list[dict[str, Any]]) -> dict[str, KeywordRadarAggregate]:
    now = datetime.now(timezone.utc)
    keyword_map: dict[str, KeywordRadarAggregate] = {}

    for row in rows:
        keyword = str(row.get("keyword") or "").strip()
        if not keyword:
            continue

        aggregate = keyword_map.setdefault(keyword, KeywordRadarAggregate(keyword=keyword))
        aggregate.total_items += 1

        crawl_time = _parse_timestamp(row.get("crawl_time"))
        if crawl_time:
            if aggregate.latest_crawl_time is None or crawl_time > aggregate.latest_crawl_time:
                aggregate.latest_crawl_time = crawl_time
            age = now - crawl_time
            if age <= timedelta(hours=24):
                aggregate.recent_items_24h += 1
            elif age <= timedelta(hours=48):
                aggregate.previous_items_24h += 1

        if row.get("is_recommended"):
            aggregate.recommended_items += 1
            if str(row.get("analysis_source") or "") == "ai":
                aggregate.ai_recommended_items += 1

        seller = str(row.get("seller_nickname") or "").strip()
        if seller:
            aggregate.unique_sellers.add(seller)

        price = row.get("price")
        if isinstance(price, (int, float)):
            aggregate.prices.append(float(price))

        title = str(row.get("title") or "")
        if title:
            for signal in SIGNAL_TERMS:
                if signal in title:
                    aggregate.signal_counter[signal] += 1

    return keyword_map


def _build_keyword_item(
    keyword: str,
    aggregate: KeywordRadarAggregate,
    annotation: dict[str, Any] | None,
) -> RadarKeywordItem:
    prices = sorted(aggregate.prices)
    min_price = round(prices[0], 2) if prices else None
    max_price = round(prices[-1], 2) if prices else None
    median_price = round(float(median(prices)), 2) if prices else None
    avg_price = round(sum(prices) / len(prices), 2) if prices else None
    price_spread = round((max_price - min_price), 2) if min_price is not None and max_price is not None else None
    growth_delta = aggregate.recent_items_24h - aggregate.previous_items_24h
    signal_hits = sum(aggregate.signal_counter.values())
    top_signals = [term for term, _count in aggregate.signal_counter.most_common(3)]
    opportunity_score = _calculate_opportunity_score(
        total_items=aggregate.total_items,
        recent_items_24h=aggregate.recent_items_24h,
        previous_items_24h=aggregate.previous_items_24h,
        unique_sellers=len(aggregate.unique_sellers),
        recommended_items=aggregate.recommended_items,
        price_spread=price_spread,
        signal_hits=signal_hits,
    )

    annotation_status = _normalize_annotation_status(
        annotation.get("status") if annotation else DEFAULT_ANNOTATION_STATUS
    )
    annotation_note = str(annotation.get("note") or "") if annotation else ""
    annotation_updated_at = annotation.get("updated_at") if annotation else None

    return RadarKeywordItem(
        keyword=keyword,
        total_items=aggregate.total_items,
        recent_items_24h=aggregate.recent_items_24h,
        previous_items_24h=aggregate.previous_items_24h,
        growth_delta=growth_delta,
        unique_sellers=len(aggregate.unique_sellers),
        recommended_items=aggregate.recommended_items,
        ai_recommended_items=aggregate.ai_recommended_items,
        min_price=min_price,
        median_price=median_price,
        avg_price=avg_price,
        max_price=max_price,
        price_spread=price_spread,
        signal_hits=signal_hits,
        top_signals=top_signals,
        opportunity_score=opportunity_score,
        latest_crawl_time=_serialize_timestamp(aggregate.latest_crawl_time),
        annotation_status=annotation_status,
        annotation_note=annotation_note,
        annotation_updated_at=annotation_updated_at,
    )


def _calculate_opportunity_score(
    *,
    total_items: int,
    recent_items_24h: int,
    previous_items_24h: int,
    unique_sellers: int,
    recommended_items: int,
    price_spread: float | None,
    signal_hits: int,
) -> int:
    heat_score = min(35, total_items * 2 + recent_items_24h * 4)
    momentum_score = min(20, max(0, recent_items_24h - previous_items_24h) * 5)
    recommendation_score = min(15, recommended_items * 3)
    seller_score = min(12, unique_sellers * 2)
    spread_score = min(10, int((price_spread or 0) / 5))
    signal_score = min(12, signal_hits * 2)
    crowding_penalty = min(10, max(0, unique_sellers - 10))

    score = (
        heat_score
        + momentum_score
        + recommendation_score
        + seller_score
        + spread_score
        + signal_score
        - crowding_penalty
    )
    return max(0, min(100, int(round(score))))


def _load_pool_row_by_id(conn: Any, item_id: int) -> Any:
    return conn.execute(
        "SELECT id, keyword, source, note, created_at, updated_at FROM radar_keyword_pool WHERE id = ?",
        (item_id,),
    ).fetchone()


def _load_pool_row_by_keyword(conn: Any, keyword: str) -> Any:
    return conn.execute(
        "SELECT id, keyword, source, note, created_at, updated_at FROM radar_keyword_pool WHERE keyword = ?",
        (keyword,),
    ).fetchone()


def _upsert_pool_item(conn: Any, keyword: str, source: PoolSource, note: str, timestamp: str | None) -> None:
    clean_keyword = _normalize_keyword(keyword)
    normalized_source = _normalize_pool_source(source)
    normalized_note = str(note or "").strip()
    now = timestamp or _serialize_timestamp(datetime.now(timezone.utc))
    conn.execute(
        """
        INSERT INTO radar_keyword_pool (keyword, source, note, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(keyword) DO UPDATE SET
            source = excluded.source,
            note = CASE
                WHEN TRIM(excluded.note) != '' THEN excluded.note
                ELSE radar_keyword_pool.note
            END,
            updated_at = excluded.updated_at
        """,
        (clean_keyword, normalized_source, normalized_note, now, now),
    )


def _load_snapshot_summary_by_id(conn: Any, snapshot_id: int) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT id, note, created_at, keyword_count, average_score, top_keyword
        FROM radar_snapshot_runs
        WHERE id = ?
        """,
        (snapshot_id,),
    ).fetchone()
    if row is None:
        return None
    return _serialize_snapshot_row(dict(row))


def _serialize_pool_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "keyword": str(row["keyword"] or ""),
        "source": _normalize_pool_source(row["source"]),
        "note": str(row["note"] or ""),
        "created_at": str(row["created_at"] or "") or None,
        "updated_at": str(row["updated_at"] or "") or None,
    }


def _serialize_snapshot_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "note": str(row["note"] or ""),
        "created_at": str(row["created_at"] or "") or None,
        "keyword_count": int(row["keyword_count"] or 0),
        "average_score": float(row["average_score"] or 0),
        "top_keyword": str(row["top_keyword"] or "") or None,
    }


def _serialize_snapshot_keyword_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "keyword": str(row["keyword"] or ""),
        "opportunity_score": int(row["opportunity_score"] or 0),
        "recent_items_24h": int(row["recent_items_24h"] or 0),
        "total_items": int(row["total_items"] or 0),
        "unique_sellers": int(row["unique_sellers"] or 0),
        "recommended_items": int(row["recommended_items"] or 0),
        "signal_hits": int(row["signal_hits"] or 0),
        "median_price": float(row["median_price"]) if row["median_price"] is not None else None,
        "price_spread": float(row["price_spread"]) if row["price_spread"] is not None else None,
        "latest_crawl_time": str(row["latest_crawl_time"] or "") or None,
    }


def _serialize_recommendation_row(row: dict[str, Any]) -> dict[str, Any]:
    signal_terms = _load_json_list(row.get("signal_terms_json"))
    source_keywords = _load_json_list(row.get("source_keywords_json"))
    keyword = str(row["keyword"] or "")
    variant_type = _normalize_variant_type(row.get("variant_type") or _detect_variant_type(keyword))
    return {
        "id": int(row["id"]),
        "keyword": keyword,
        "reason": str(row["reason"] or ""),
        "score": int(row["score"] or 0),
        "signal_terms": signal_terms,
        "source_keywords": source_keywords,
        "variant_type": variant_type,
        "status": _normalize_recommendation_status(row["status"]),
        "created_at": str(row["created_at"] or "") or None,
        "updated_at": str(row["updated_at"] or "") or None,
    }


def _load_json_list(value: Any) -> list[str]:
    if not value:
        return []
    try:
        loaded = json.loads(str(value))
    except json.JSONDecodeError:
        return []
    if not isinstance(loaded, list):
        return []
    return [str(item).strip() for item in loaded if str(item).strip()]


def _normalize_keyword(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError("关键词不能为空")
    return text


def _normalize_annotation_status(value: Any) -> AnnotationStatus:
    text = str(value or "").strip().lower()
    if text in {"watch", "test", "sourced", "risky", "drop"}:
        return text  # type: ignore[return-value]
    return DEFAULT_ANNOTATION_STATUS


def _normalize_pool_source(value: Any) -> PoolSource:
    text = str(value or "").strip().lower()
    if text in {"manual", "radar", "recommendation"}:
        return text  # type: ignore[return-value]
    return DEFAULT_POOL_SOURCE


def _normalize_recommendation_status(value: Any) -> RecommendationStatus:
    text = str(value or "").strip().lower()
    if text in {"pending", "accepted", "dismissed"}:
        return text  # type: ignore[return-value]
    return DEFAULT_RECOMMENDATION_STATUS


def _normalize_variant_type(value: Any) -> RecommendationVariantType:
    text = str(value or "").strip().lower()
    if text in {"product", "service", "delivery", "generic"}:
        return text  # type: ignore[return-value]
    return "generic"


def _normalize_variant_types(values: list[str] | None) -> set[RecommendationVariantType]:
    if not values:
        return set()
    normalized = {_normalize_variant_type(value) for value in values if str(value or '').strip()}
    return {value for value in normalized if value != "generic"} | ({"generic"} if "generic" in normalized else set())


def _parse_timestamp(value: Any) -> datetime | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None

    normalized = text.replace("Z", "+00:00")
    candidates = (
        normalized,
        normalized.replace(" ", "T"),
        text,
    )
    for candidate in candidates:
        try:
            parsed = datetime.fromisoformat(candidate)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except ValueError:
            continue
    return None


def _serialize_timestamp(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(timezone.utc).isoformat()


def _serialize_keyword_item(item: RadarKeywordItem) -> dict[str, Any]:
    return {
        "keyword": item.keyword,
        "total_items": item.total_items,
        "recent_items_24h": item.recent_items_24h,
        "previous_items_24h": item.previous_items_24h,
        "growth_delta": item.growth_delta,
        "unique_sellers": item.unique_sellers,
        "recommended_items": item.recommended_items,
        "ai_recommended_items": item.ai_recommended_items,
        "min_price": item.min_price,
        "median_price": item.median_price,
        "avg_price": item.avg_price,
        "max_price": item.max_price,
        "price_spread": item.price_spread,
        "signal_hits": item.signal_hits,
        "top_signals": item.top_signals,
        "opportunity_score": item.opportunity_score,
        "latest_crawl_time": item.latest_crawl_time,
        "annotation_status": item.annotation_status,
        "annotation_note": item.annotation_note,
        "annotation_updated_at": item.annotation_updated_at,
    }
