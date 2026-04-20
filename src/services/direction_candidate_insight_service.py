"""
Finder 候选词证据聚合与机会状态服务。
"""
from __future__ import annotations

import asyncio
import json
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from statistics import median
from typing import Any

from src.domain.models.direction_candidate import DirectionCandidate
from src.domain.models.direction_candidate_insight import (
    DirectionCandidateEvidence,
    DirectionCandidateOpportunityState,
)
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


@dataclass
class _Aggregate:
    total_items: int = 0
    recent_items_24h: int = 0
    previous_items_24h: int = 0
    recommended_items: int = 0
    ai_recommended_items: int = 0
    unique_sellers: set[str] = field(default_factory=set)
    prices: list[float] = field(default_factory=list)
    signal_counter: Counter[str] = field(default_factory=Counter)
    latest_crawl_time: datetime | None = None


class DirectionCandidateInsightService:
    def __init__(self, db_path: str | None = None, legacy_config_file: str | None = None):
        self.db_path = db_path
        self.legacy_config_file = legacy_config_file

    def with_db_path(self, db_path: str | None) -> "DirectionCandidateInsightService":
        """返回一个新实例，使用指定的 db_path。"""
        svc = DirectionCandidateInsightService(db_path=db_path, legacy_config_file=self.legacy_config_file)
        return svc

    async def refresh_direction_candidates(
        self,
        direction_id: int,
        candidates: list[DirectionCandidate],
    ) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._refresh_direction_candidates_sync, direction_id, candidates)

    async def list_direction_candidates(
        self,
        direction_id: int,
        candidates: list[DirectionCandidate],
    ) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._list_direction_candidates_sync, direction_id, candidates)

    def _refresh_direction_candidates_sync(
        self,
        direction_id: int,
        candidates: list[DirectionCandidate],
    ) -> list[dict[str, Any]]:
        bootstrap_sqlite_storage(self.db_path, legacy_config_file=self.legacy_config_file)
        now = datetime.now(UTC)

        with sqlite_connection(self.db_path) as conn:
            for candidate in candidates:
                evidence, state = self._build_candidate_insight(conn, candidate, now)
                conn.execute(
                    """
                    INSERT INTO radar_candidate_evidence (
                        candidate_id, sample_count, recent_items_24h, previous_items_24h,
                        unique_sellers, recommended_items, ai_recommended_items,
                        median_price, price_spread, signal_hits, top_signals_json,
                        latest_crawl_time, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(candidate_id) DO UPDATE SET
                        sample_count=excluded.sample_count,
                        recent_items_24h=excluded.recent_items_24h,
                        previous_items_24h=excluded.previous_items_24h,
                        unique_sellers=excluded.unique_sellers,
                        recommended_items=excluded.recommended_items,
                        ai_recommended_items=excluded.ai_recommended_items,
                        median_price=excluded.median_price,
                        price_spread=excluded.price_spread,
                        signal_hits=excluded.signal_hits,
                        top_signals_json=excluded.top_signals_json,
                        latest_crawl_time=excluded.latest_crawl_time,
                        updated_at=excluded.updated_at
                    """,
                    (
                        candidate.id,
                        evidence.sample_count,
                        evidence.recent_items_24h,
                        evidence.previous_items_24h,
                        evidence.unique_sellers,
                        evidence.recommended_items,
                        evidence.ai_recommended_items,
                        evidence.median_price,
                        evidence.price_spread,
                        evidence.signal_hits,
                        json.dumps(evidence.top_signals, ensure_ascii=False),
                        evidence.latest_crawl_time.isoformat() if evidence.latest_crawl_time else None,
                        evidence.updated_at.isoformat() if evidence.updated_at else None,
                    ),
                )
                conn.execute(
                    """
                    INSERT INTO radar_opportunity_states (
                        candidate_id, heat_score, momentum_score, commercial_score,
                        competition_score, confidence_score, opportunity_score,
                        status, suggested_action, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(candidate_id) DO UPDATE SET
                        heat_score=excluded.heat_score,
                        momentum_score=excluded.momentum_score,
                        commercial_score=excluded.commercial_score,
                        competition_score=excluded.competition_score,
                        confidence_score=excluded.confidence_score,
                        opportunity_score=excluded.opportunity_score,
                        status=excluded.status,
                        suggested_action=excluded.suggested_action,
                        updated_at=excluded.updated_at
                    """,
                    (
                        candidate.id,
                        state.heat_score,
                        state.momentum_score,
                        state.commercial_score,
                        state.competition_score,
                        state.confidence_score,
                        state.opportunity_score,
                        state.status,
                        state.suggested_action,
                        state.updated_at.isoformat() if state.updated_at else None,
                    ),
                )
            conn.commit()

        return self._list_direction_candidates_sync(direction_id, candidates)

    def _list_direction_candidates_sync(
        self,
        direction_id: int,
        candidates: list[DirectionCandidate],
    ) -> list[dict[str, Any]]:
        bootstrap_sqlite_storage(self.db_path, legacy_config_file=self.legacy_config_file)
        candidate_map = {int(candidate.id or 0): candidate for candidate in candidates}
        if not candidate_map:
            return []

        with sqlite_connection(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT
                    c.id AS candidate_id,
                    e.sample_count,
                    e.recent_items_24h,
                    e.previous_items_24h,
                    e.unique_sellers,
                    e.recommended_items,
                    e.ai_recommended_items,
                    e.median_price,
                    e.price_spread,
                    e.signal_hits,
                    e.top_signals_json,
                    e.latest_crawl_time,
                    e.updated_at AS evidence_updated_at,
                    s.heat_score,
                    s.momentum_score,
                    s.commercial_score,
                    s.competition_score,
                    s.confidence_score,
                    s.opportunity_score,
                    s.status,
                    s.suggested_action,
                    s.updated_at AS state_updated_at
                FROM radar_keyword_candidates c
                LEFT JOIN radar_candidate_evidence e ON e.candidate_id = c.id
                LEFT JOIN radar_opportunity_states s ON s.candidate_id = c.id
                WHERE c.direction_id = ?
                ORDER BY
                    CASE c.lifecycle_status WHEN 'seed' THEN 0 ELSE 1 END,
                    COALESCE(s.opportunity_score, 0) DESC,
                    c.confidence DESC,
                    c.keyword ASC
                """,
                (direction_id,),
            ).fetchall()

        enriched: list[dict[str, Any]] = []
        for row in rows:
            candidate = candidate_map.get(int(row["candidate_id"]))
            if candidate is None:
                continue
            payload = candidate.model_dump(mode="json")
            payload["evidence"] = {
                "sample_count": int(row["sample_count"] or 0),
                "recent_items_24h": int(row["recent_items_24h"] or 0),
                "previous_items_24h": int(row["previous_items_24h"] or 0),
                "unique_sellers": int(row["unique_sellers"] or 0),
                "recommended_items": int(row["recommended_items"] or 0),
                "ai_recommended_items": int(row["ai_recommended_items"] or 0),
                "median_price": float(row["median_price"]) if row["median_price"] is not None else None,
                "price_spread": float(row["price_spread"]) if row["price_spread"] is not None else None,
                "signal_hits": int(row["signal_hits"] or 0),
                "top_signals": json.loads(row["top_signals_json"] or "[]"),
                "latest_crawl_time": row["latest_crawl_time"],
                "updated_at": row["evidence_updated_at"],
            }
            payload["state"] = {
                "heat_score": int(row["heat_score"] or 0),
                "momentum_score": int(row["momentum_score"] or 0),
                "commercial_score": int(row["commercial_score"] or 0),
                "competition_score": int(row["competition_score"] or 0),
                "confidence_score": int(row["confidence_score"] or 0),
                "opportunity_score": int(row["opportunity_score"] or 0),
                "status": row["status"] or "cold",
                "suggested_action": row["suggested_action"] or "collect_more",
                "updated_at": row["state_updated_at"],
            }
            enriched.append(payload)
        return enriched

    def _build_candidate_insight(
        self,
        conn,
        candidate: DirectionCandidate,
        now: datetime,
    ) -> tuple[DirectionCandidateEvidence, DirectionCandidateOpportunityState]:
        rows = conn.execute(
            """
            SELECT keyword, crawl_time, price, seller_nickname, is_recommended, analysis_source, title
            FROM result_items
            WHERE lower(keyword) = lower(?)
            ORDER BY crawl_time DESC
            """,
            (candidate.keyword,),
        ).fetchall()

        aggregate = _Aggregate()
        for row in rows:
            aggregate.total_items += 1

            crawl_time = self._parse_timestamp(row["crawl_time"])
            if crawl_time:
                if aggregate.latest_crawl_time is None or crawl_time > aggregate.latest_crawl_time:
                    aggregate.latest_crawl_time = crawl_time
                age = now - crawl_time
                if age <= timedelta(hours=24):
                    aggregate.recent_items_24h += 1
                elif age <= timedelta(hours=48):
                    aggregate.previous_items_24h += 1

            seller = str(row["seller_nickname"] or "").strip()
            if seller:
                aggregate.unique_sellers.add(seller)

            price = row["price"]
            if isinstance(price, (int, float)):
                aggregate.prices.append(float(price))

            if row["is_recommended"]:
                aggregate.recommended_items += 1
                if str(row["analysis_source"] or "") == "ai":
                    aggregate.ai_recommended_items += 1

            title = str(row["title"] or "")
            for signal in SIGNAL_TERMS:
                if signal and signal in title:
                    aggregate.signal_counter[signal] += 1

        prices = sorted(aggregate.prices)
        median_price = round(float(median(prices)), 2) if prices else None
        price_spread = (
            round(float(prices[-1] - prices[0]), 2)
            if len(prices) >= 2
            else 0.0 if prices else None
        )
        signal_hits = sum(aggregate.signal_counter.values())
        top_signals = [signal for signal, _ in aggregate.signal_counter.most_common(3)]

        evidence = DirectionCandidateEvidence(
            candidate_id=int(candidate.id or 0),
            sample_count=aggregate.total_items,
            recent_items_24h=aggregate.recent_items_24h,
            previous_items_24h=aggregate.previous_items_24h,
            unique_sellers=len(aggregate.unique_sellers),
            recommended_items=aggregate.recommended_items,
            ai_recommended_items=aggregate.ai_recommended_items,
            median_price=median_price,
            price_spread=price_spread,
            signal_hits=signal_hits,
            top_signals=top_signals,
            latest_crawl_time=aggregate.latest_crawl_time,
            updated_at=now,
        )
        state = self._build_opportunity_state(candidate, evidence, now)
        return evidence, state

    def _build_opportunity_state(
        self,
        candidate: DirectionCandidate,
        evidence: DirectionCandidateEvidence,
        now: datetime,
    ) -> DirectionCandidateOpportunityState:
        heat_score = min(35, evidence.sample_count * 2 + evidence.recent_items_24h * 4)
        momentum_score = min(20, max(0, evidence.recent_items_24h - evidence.previous_items_24h) * 5)
        commercial_score = min(18, evidence.signal_hits * 2 + evidence.recommended_items * 3)
        competition_penalty = min(12, max(0, evidence.unique_sellers - 8))
        competition_score = max(0, 12 - competition_penalty)
        confidence_score = min(15, int(round(candidate.confidence * 10)) + min(5, evidence.sample_count))
        spread_score = min(10, int((evidence.price_spread or 0) / 5))

        opportunity_score = max(
            0,
            min(
                100,
                int(round(
                    heat_score
                    + momentum_score
                    + commercial_score
                    + competition_score
                    + confidence_score
                    + spread_score
                )),
            ),
        )

        if opportunity_score >= 75:
            status = "hot"
            suggested_action = "promote"
        elif opportunity_score >= 55:
            status = "test"
            suggested_action = "test_now"
        elif opportunity_score >= 30:
            status = "watch"
            suggested_action = "watch"
        else:
            status = "cold"
            suggested_action = "collect_more"

        return DirectionCandidateOpportunityState(
            candidate_id=int(candidate.id or 0),
            heat_score=heat_score,
            momentum_score=momentum_score,
            commercial_score=commercial_score,
            competition_score=competition_score,
            confidence_score=confidence_score,
            opportunity_score=opportunity_score,
            status=status,  # type: ignore[arg-type]
            suggested_action=suggested_action,  # type: ignore[arg-type]
            updated_at=now,
        )

    def _parse_timestamp(self, value: Any) -> datetime | None:
        text = str(value or "").strip()
        if not text:
            return None
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)
            return parsed.astimezone(UTC)
        except ValueError:
            return None
