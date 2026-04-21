"""
Finder 候选词推荐服务。
"""
from __future__ import annotations

from datetime import UTC, datetime

from src.domain.models.direction_recommendation import DirectionRecommendation
from src.infrastructure.persistence.sqlite_bootstrap import bootstrap_sqlite_storage
from src.infrastructure.persistence.sqlite_connection import sqlite_connection


class DirectionRecommendationService:
    def __init__(self, db_path: str | None = None, legacy_config_file: str | None = None):
        self.db_path = db_path
        self.legacy_config_file = legacy_config_file

    def _build_reason(self, item: dict) -> str:
        evidence = item.get("evidence") or {}
        state = item.get("state") or {}
        parts: list[str] = []
        recent = int(evidence.get("recent_items_24h") or 0)
        recommended = int(evidence.get("recommended_items") or 0)
        signal_hits = int(evidence.get("signal_hits") or 0)
        top_signals = list(evidence.get("top_signals") or [])
        score = int(state.get("opportunity_score") or 0)

        if recent > 0:
            parts.append(f"最近24小时新增 {recent} 条样本")
        if recommended > 0:
            parts.append(f"已有 {recommended} 条推荐结果")
        if signal_hits > 0:
            parts.append(f"标题中累计命中 {signal_hits} 次强信号词")
        if top_signals:
            parts.append(f"高频信号词包括 {'、'.join(top_signals[:2])}")
        if not parts:
            parts.append(f"当前机会分 {score}，建议继续验证")
        return "；".join(parts)

    def _build_action(self, item: dict) -> str:
        state = item.get("state") or {}
        suggested = str(state.get("suggested_action") or "watch")
        mapping = {
            "collect_more": "collect_more",
            "watch": "watch",
            "test_now": "create_task",
            "promote": "create_task",
        }
        return mapping.get(suggested, "watch")

    def _load_feedback_bias(self, conn, direction_id: int) -> dict[int, dict[str, int]]:
        rows = conn.execute(
            """
            SELECT candidate_id, feedback_type, COUNT(1) AS total
            FROM radar_learning_feedback
            WHERE direction_id = ? AND candidate_id IS NOT NULL
            GROUP BY candidate_id, feedback_type
            """,
            (direction_id,),
        ).fetchall()
        result: dict[int, dict[str, int]] = {}
        for row in rows:
            candidate_id = int(row["candidate_id"])
            bucket = result.setdefault(candidate_id, {})
            bucket[str(row["feedback_type"])] = int(row["total"] or 0)
        return result

    async def refresh_direction_recommendations(self, direction_id: int, candidate_items: list[dict]) -> list[dict]:
        import asyncio

        return await asyncio.to_thread(self._refresh_direction_recommendations_sync, direction_id, candidate_items)

    async def list_direction_recommendations(self, direction_id: int) -> list[dict]:
        import asyncio

        return await asyncio.to_thread(self._list_direction_recommendations_sync, direction_id)

    async def get_recommendation(self, recommendation_id: int) -> dict | None:
        import asyncio

        return await asyncio.to_thread(self._get_recommendation_sync, recommendation_id)

    def _get_recommendation_sync(self, recommendation_id: int) -> dict | None:
        bootstrap_sqlite_storage(self.db_path, legacy_config_file=self.legacy_config_file)
        with sqlite_connection(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT id, direction_id, candidate_id, keyword, variant_type, reason, score, recommended_action, status, created_at, updated_at
                FROM radar_candidate_recommendations WHERE id = ?
                """,
                (recommendation_id,),
            ).fetchone()
            if row is None:
                return None
            return DirectionRecommendation(**dict(row)).model_dump(mode="json")

    async def update_recommendation_status(self, recommendation_id: int, status: str) -> dict:
        import asyncio

        return await asyncio.to_thread(self._update_recommendation_status_sync, recommendation_id, status)

    def _refresh_direction_recommendations_sync(self, direction_id: int, candidate_items: list[dict]) -> list[dict]:
        bootstrap_sqlite_storage(self.db_path, legacy_config_file=self.legacy_config_file)
        now = datetime.now(UTC).isoformat()
        with sqlite_connection(self.db_path) as conn:
            feedback_bias = self._load_feedback_bias(conn, direction_id)
            for item in candidate_items:
                state = item.get("state") or {}
                candidate_id = int(item.get("id") or 0)
                if candidate_id <= 0:
                    continue
                feedback = feedback_bias.get(candidate_id, {})
                accepted = int(feedback.get("recommendation_accept", 0))
                dismissed = int(feedback.get("recommendation_dismiss", 0))
                created_tasks = int(feedback.get("task_created", 0))
                score = int(state.get("opportunity_score") or 0) + accepted * 5 + created_tasks * 8 - dismissed * 6
                score = max(0, min(100, score))
                if score < 45:
                    continue

                reason = self._build_reason(item)
                if accepted or dismissed or created_tasks:
                    reason = f"{reason}；历史反馈：接受 {accepted} / 忽略 {dismissed} / 建任务 {created_tasks}"
                recommended_action = self._build_action(item)
                keyword = str(item.get("keyword") or "")
                existing = conn.execute(
                    "SELECT id, status, created_at FROM radar_candidate_recommendations WHERE candidate_id = ?",
                    (candidate_id,),
                ).fetchone()
                if existing:
                    status = str(existing["status"] or "pending")
                    created_at = str(existing["created_at"] or now)
                    conn.execute(
                        """
                        UPDATE radar_candidate_recommendations
                        SET keyword = ?, variant_type = ?, reason = ?, score = ?, recommended_action = ?, updated_at = ?
                        WHERE candidate_id = ?
                        """,
                        (keyword, item.get("variant_type"), reason, score, recommended_action, now, candidate_id),
                    )
                else:
                    status = "pending"
                    created_at = now
                    conn.execute(
                        """
                        INSERT INTO radar_candidate_recommendations (
                            direction_id, candidate_id, keyword, variant_type, reason, score,
                            recommended_action, status, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (direction_id, candidate_id, keyword, item.get("variant_type"), reason, score, recommended_action, status, created_at, now),
                    )

            conn.commit()
        return self._list_direction_recommendations_sync(direction_id)

    def _list_direction_recommendations_sync(self, direction_id: int) -> list[dict]:
        bootstrap_sqlite_storage(self.db_path, legacy_config_file=self.legacy_config_file)
        with sqlite_connection(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT id, direction_id, candidate_id, keyword, variant_type, reason, score, recommended_action, status, created_at, updated_at
                FROM radar_candidate_recommendations
                WHERE direction_id = ?
                ORDER BY score DESC, updated_at DESC
                """,
                (direction_id,),
            ).fetchall()
        return [DirectionRecommendation(**dict(row)).model_dump(mode="json") for row in rows]

    def _update_recommendation_status_sync(self, recommendation_id: int, status: str) -> dict:
        normalized = str(status or "").strip().lower()
        if normalized not in {"pending", "accepted", "dismissed"}:
            raise ValueError("推荐状态不合法")
        bootstrap_sqlite_storage(self.db_path, legacy_config_file=self.legacy_config_file)
        now = datetime.now(UTC).isoformat()
        with sqlite_connection(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT id, direction_id, candidate_id, keyword, variant_type, reason, score, recommended_action, status, created_at, updated_at
                FROM radar_candidate_recommendations WHERE id = ?
                """,
                (recommendation_id,),
            ).fetchone()
            if row is None:
                raise ValueError("推荐不存在")
            direction_id = int(row["direction_id"])
            candidate_id = int(row["candidate_id"]) if row["candidate_id"] is not None else None
            conn.execute(
                "UPDATE radar_candidate_recommendations SET status = ?, updated_at = ? WHERE id = ?",
                (normalized, now, recommendation_id),
            )
            conn.execute(
                """
                INSERT INTO radar_learning_feedback (
                    direction_id, candidate_id, recommendation_id, task_id,
                    feedback_type, feedback_value, note, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    direction_id,
                    candidate_id,
                    recommendation_id,
                    None,
                    "recommendation_accept" if normalized == "accepted" else "recommendation_dismiss",
                    normalized,
                    f"推荐状态更新为 {normalized}",
                    now,
                ),
            )
            conn.commit()
            updated = conn.execute(
                """
                SELECT id, direction_id, candidate_id, keyword, variant_type, reason, score, recommended_action, status, created_at, updated_at
                FROM radar_candidate_recommendations WHERE id = ?
                """,
                (recommendation_id,),
            ).fetchone()
        return DirectionRecommendation(**dict(updated)).model_dump(mode="json")
