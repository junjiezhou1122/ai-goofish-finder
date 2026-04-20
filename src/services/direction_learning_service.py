"""
Finder 学习反馈汇总与扩词调参服务。
"""
from __future__ import annotations

import asyncio
import json

from src.infrastructure.persistence.sqlite_bootstrap import bootstrap_sqlite_storage
from src.infrastructure.persistence.sqlite_connection import sqlite_connection


# 扩词调参阈值配置
_LLM_REJECT_THRESHOLD = 0.6  # 推荐拒绝率 > 60% 时，降低 LLM 扩词权重
_LLM_ACCEPT_THRESHOLD = 0.7  # 推荐接受率 > 70% 时，提升 LLM 扩词权重
_DELIVERY_ACCEPT_RATE = 0.65  # delivery 类型接受率 > 65% 时，提升其 confidence 上限


class DirectionLearningService:
    def __init__(self, db_path: str | None = None, legacy_config_file: str | None = None):
        self.db_path = db_path
        self.legacy_config_file = legacy_config_file

    async def get_direction_summary(self, direction_id: int) -> dict:
        return await asyncio.to_thread(self._get_direction_summary_sync, direction_id)

    def _get_direction_summary_sync(self, direction_id: int) -> dict:
        bootstrap_sqlite_storage(self.db_path, legacy_config_file=self.legacy_config_file)
        with sqlite_connection(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT feedback_type, COUNT(1) AS total
                FROM radar_learning_feedback
                WHERE direction_id = ?
                GROUP BY feedback_type
                """,
                (direction_id,),
            ).fetchall()
            experiments_row = conn.execute(
                """
                SELECT
                    COUNT(1) AS total_experiments,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS completed_experiments,
                    SUM(CASE WHEN status = 'running' THEN 1 ELSE 0 END) AS running_experiments
                FROM radar_experiments
                WHERE direction_id = ?
                """,
                (direction_id,),
            ).fetchone()

        counters = {str(row["feedback_type"]): int(row["total"] or 0) for row in rows}
        return {
            "accepted_recommendations": counters.get("recommendation_accept", 0),
            "dismissed_recommendations": counters.get("recommendation_dismiss", 0),
            "created_tasks": counters.get("task_created", 0),
            "total_experiments": int(experiments_row["total_experiments"] or 0) if experiments_row else 0,
            "completed_experiments": int(experiments_row["completed_experiments"] or 0) if experiments_row else 0,
            "running_experiments": int(experiments_row["running_experiments"] or 0) if experiments_row else 0,
        }

    async def adjust_expansion_weights(self, direction_id: int) -> dict:
        """
        根据历史反馈调整扩词策略参数，并将调参结果写回 radar_directions 表。

        调参逻辑：
        - 推荐拒绝率高 → 降低 LLM 扩词权重（多用规则扩词，减少噪音）
        - 推荐接受率高 → 提升 LLM 扩词权重（LLM 扩词效果好，多用）
        - delivery 类型接受率高 → 提升 delivery 变体的 confidence 上限

        Returns:
            dict: 调参变更摘要，包含各参数的新旧值
        """
        return await asyncio.to_thread(self._adjust_expansion_weights_sync, direction_id)

    def _adjust_expansion_weights_sync(self, direction_id: int) -> dict:
        bootstrap_sqlite_storage(self.db_path, legacy_config_file=self.legacy_config_file)

        summary = self._get_direction_summary_sync(direction_id)
        accepted = summary["accepted_recommendations"]
        dismissed = summary["dismissed_recommendations"]
        total = accepted + dismissed

        changes: dict = {}

        # 查当前扩词参数
        with sqlite_connection(self.db_path) as conn:
            row = conn.execute(
                "SELECT expansion_config_json FROM radar_directions WHERE id = ?",
                (direction_id,),
            ).fetchone()
            if not row:
                return {"error": f"方向 {direction_id} 不存在"}

            try:
                config = json.loads(row["expansion_config_json"] or "{}")
            except Exception:
                config = {}

            # 初始化默认值
            config.setdefault("llm_weight", 1.0)
            config.setdefault("rule_weight", 1.0)
            config.setdefault("variant_boost", {})
            config.setdefault("last_adjusted_at", None)

        # 调参逻辑
        if total >= 5:  # 至少 5 条反馈才触发调参，避免样本太少时波动
            from datetime import UTC, datetime

            reject_rate = dismissed / total if total > 0 else 0

            if reject_rate > _LLM_REJECT_THRESHOLD:
                old = config["llm_weight"]
                config["llm_weight"] = round(max(0.1, old - 0.2), 2)
                changes["llm_weight"] = {"before": old, "after": config["llm_weight"], "reason": f"拒绝率 {reject_rate:.0%} 过高"}

            elif accepted > 0 and (accepted / total) > _LLM_ACCEPT_THRESHOLD:
                old = config["llm_weight"]
                config["llm_weight"] = round(min(2.0, old + 0.1), 2)
                changes["llm_weight"] = {"before": old, "after": config["llm_weight"], "reason": f"接受率 {accepted/total:.0%} 良好"}

            # delivery 类型效果追踪
            delivery_row = conn.execute(
                """
                SELECT COUNT(1) AS total,
                       SUM(CASE WHEN r.status = 'accepted' THEN 1 ELSE 0 END) AS accepted
                FROM radar_candidate_recommendations r
                WHERE r.direction_id = ? AND r.variant_type = 'delivery'
                """,
                (direction_id,),
            ).fetchone()

            if delivery_row and int(delivery_row["total"] or 0) >= 3:
                delivery_rate = int(delivery_row["accepted"] or 0) / max(1, int(delivery_row["total"]))
                if delivery_rate > _DELIVERY_ACCEPT_RATE:
                    old_boost = config["variant_boost"].get("delivery", 0.0)
                    new_boost = round(min(0.3, old_boost + 0.05), 2)
                    config["variant_boost"]["delivery"] = new_boost
                    changes["variant_boost_delivery"] = {"before": old_boost, "after": new_boost, "reason": f"delivery 接受率 {delivery_rate:.0%}"}

            config["last_adjusted_at"] = datetime.now(UTC).isoformat()

        # 写回数据库
        with sqlite_connection(self.db_path) as conn:
            conn.execute(
                "UPDATE radar_directions SET expansion_config_json = ? WHERE id = ?",
                (json.dumps(config, ensure_ascii=False), direction_id),
            )
            conn.commit()

        return {"direction_id": direction_id, "adjustments": changes if changes else "no_change"}
