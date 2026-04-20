"""
Finder 实验与学习反馈服务。
"""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from src.domain.models.direction_experiment import DirectionExperiment
from src.domain.models.task import Task
from src.infrastructure.persistence.sqlite_bootstrap import bootstrap_sqlite_storage
from src.infrastructure.persistence.sqlite_connection import sqlite_connection


class DirectionExperimentService:
    def __init__(self, db_path: str | None = None, legacy_config_file: str | None = None):
        self.db_path = db_path
        self.legacy_config_file = legacy_config_file

    async def create_task_experiment(
        self,
        *,
        direction_id: int,
        candidate_id: int | None,
        recommendation_id: int | None,
        task: Task,
    ) -> dict:
        return await asyncio.to_thread(
            self._create_task_experiment_sync,
            direction_id,
            candidate_id,
            recommendation_id,
            task,
        )

    async def list_direction_experiments(self, direction_id: int) -> list[dict]:
        return await asyncio.to_thread(self._list_direction_experiments_sync, direction_id)

    async def record_feedback(
        self,
        *,
        direction_id: int,
        candidate_id: int | None,
        recommendation_id: int | None,
        task_id: int | None,
        feedback_type: str,
        feedback_value: str,
        note: str | None = None,
    ) -> None:
        await asyncio.to_thread(
            self._record_feedback_sync,
            direction_id,
            candidate_id,
            recommendation_id,
            task_id,
            feedback_type,
            feedback_value,
            note,
        )

    def _create_task_experiment_sync(
        self,
        direction_id: int,
        candidate_id: int | None,
        recommendation_id: int | None,
        task: Task,
    ) -> dict:
        bootstrap_sqlite_storage(self.db_path, legacy_config_file=self.legacy_config_file)
        now = datetime.now(UTC).isoformat()
        with sqlite_connection(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO radar_experiments (
                    direction_id, candidate_id, recommendation_id, task_id, task_name,
                    keyword, status, source, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    direction_id,
                    candidate_id,
                    recommendation_id,
                    task.id,
                    task.task_name,
                    task.keyword,
                    "draft",
                    "finder",
                    now,
                    now,
                ),
            )
            experiment_id = int(cursor.lastrowid or 0)
            conn.commit()
        self._record_feedback_sync(
            direction_id,
            candidate_id,
            recommendation_id,
            task.id,
            "task_created",
            "created",
            f"任务 {task.task_name} 已从 Finder 推荐创建",
        )
        return {
            "id": experiment_id,
            "direction_id": direction_id,
            "candidate_id": candidate_id,
            "recommendation_id": recommendation_id,
            "task_id": task.id,
            "task_name": task.task_name,
            "keyword": task.keyword,
            "status": "draft",
            "source": "finder",
            "created_at": now,
            "updated_at": now,
        }

    def _list_direction_experiments_sync(self, direction_id: int) -> list[dict]:
        bootstrap_sqlite_storage(self.db_path, legacy_config_file=self.legacy_config_file)
        with sqlite_connection(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT e.id, e.direction_id, e.candidate_id, e.recommendation_id, e.task_id, e.task_name, e.keyword,
                       e.status, e.source, e.created_at, e.updated_at,
                       t.is_running,
                       (
                         SELECT COUNT(1)
                         FROM result_items r
                         WHERE lower(r.keyword) = lower(e.keyword)
                       ) AS sample_count,
                       (
                         SELECT MAX(r.crawl_time)
                         FROM result_items r
                         WHERE lower(r.keyword) = lower(e.keyword)
                       ) AS latest_crawl_time
                FROM radar_experiments e
                LEFT JOIN tasks t ON t.id = e.task_id
                WHERE e.direction_id = ?
                ORDER BY e.created_at DESC
                """,
                (direction_id,),
            ).fetchall()

            serialized: list[dict] = []
            for row in rows:
                status = str(row["status"] or "draft")
                is_running = bool(row["is_running"]) if row["is_running"] is not None else False
                sample_count = int(row["sample_count"] or 0)
                next_status = status
                if row["task_id"] is None:
                    next_status = "cancelled"
                elif is_running:
                    next_status = "running"
                elif sample_count > 0:
                    next_status = "completed"
                else:
                    next_status = "draft"

                if next_status != status:
                    conn.execute(
                        "UPDATE radar_experiments SET status = ?, updated_at = ? WHERE id = ?",
                        (next_status, datetime.now(UTC).isoformat(), int(row["id"])),
                    )
                payload = DirectionExperiment(
                    **{
                        "id": row["id"],
                        "direction_id": row["direction_id"],
                        "candidate_id": row["candidate_id"],
                        "recommendation_id": row["recommendation_id"],
                        "task_id": row["task_id"],
                        "task_name": row["task_name"],
                        "keyword": row["keyword"],
                        "status": next_status,
                        "source": row["source"],
                        "created_at": row["created_at"],
                        "updated_at": row["updated_at"],
                    }
                ).model_dump(mode="json")
                payload["sample_count"] = sample_count
                payload["latest_crawl_time"] = row["latest_crawl_time"]
                serialized.append(payload)
            conn.commit()
        return serialized

    def _record_feedback_sync(
        self,
        direction_id: int,
        candidate_id: int | None,
        recommendation_id: int | None,
        task_id: int | None,
        feedback_type: str,
        feedback_value: str,
        note: str | None,
    ) -> None:
        bootstrap_sqlite_storage(self.db_path, legacy_config_file=self.legacy_config_file)
        now = datetime.now(UTC).isoformat()
        with sqlite_connection(self.db_path) as conn:
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
                    task_id,
                    feedback_type,
                    feedback_value,
                    note,
                    now,
                ),
            )
            conn.commit()

    async def report_task_result(
        self,
        experiment_id: int,
        *,
        sample_count: int | None = None,
        ai_recommended_count: int = 0,
        running_minutes: int = 0,
    ) -> None:
        """
        任务执行完成后报告结果，写入实验状态更新 + 学习反馈。

        这使得 Finder 的推荐系统能感知"哪些候选词验证后确实有样本"，
        从而在推荐时更有信心推高分词。

        Args:
            experiment_id: 实验 ID
            sample_count: 任务执行新增的样本数，None 时自动从 result_items 统计
            ai_recommended_count: AI 推荐命中数
            running_minutes: 任务运行时长（分钟）
        """
        await asyncio.to_thread(
            self._report_task_result_sync,
            experiment_id,
            sample_count,
            ai_recommended_count,
            running_minutes,
        )

    def _report_task_result_sync(
        self,
        experiment_id: int,
        sample_count: int | None,
        ai_recommended_count: int,
        running_minutes: int,
    ) -> None:
        bootstrap_sqlite_storage(self.db_path, legacy_config_file=self.legacy_config_file)
        now = datetime.now(UTC).isoformat()

        with sqlite_connection(self.db_path) as conn:
            # 查实验信息（用于获取 direction_id / candidate_id / keyword）
            row = conn.execute(
                "SELECT direction_id, candidate_id, keyword FROM radar_experiments WHERE id = ?",
                (experiment_id,),
            ).fetchone()
            if not row:
                return

            direction_id = int(row["direction_id"] or 0)
            candidate_id = row["candidate_id"]
            keyword = str(row["keyword"] or "")

            # 如果未传入 sample_count，从 result_items 自动统计
            if sample_count is None and keyword:
                count_row = conn.execute(
                    "SELECT COUNT(1) AS cnt FROM result_items WHERE lower(keyword) = lower(?)",
                    (keyword,),
                ).fetchone()
                sample_count = int(count_row["cnt"] or 0) if count_row else 0

            if sample_count is None:
                sample_count = 0

            # 更新实验状态 → completed
            conn.execute(
                "UPDATE radar_experiments SET status = ?, updated_at = ? WHERE id = ?",
                ("completed", now, experiment_id),
            )

            # 写学习反馈
            conn.execute(
                """
                INSERT INTO radar_learning_feedback (
                    direction_id, candidate_id, task_id,
                    feedback_type, feedback_value, note, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    direction_id,
                    candidate_id,
                    experiment_id,
                    "task_result",
                    f"sample:{sample_count}|ai:{ai_recommended_count}|duration:{running_minutes}m",
                    f"实验 id={experiment_id} 任务完成，新增 {sample_count} 条样本",
                    now,
                ),
            )

            # 如果有 candidate_id，更新其 evidence（累加本次样本到 recommended_items）
            if candidate_id:
                conn.execute(
                    """
                    UPDATE radar_candidate_evidence
                    SET recommended_items = recommended_items + ?,
                        ai_recommended_items = ai_recommended_items + ?,
                        updated_at = ?
                    WHERE candidate_id = ?
                    """,
                    (sample_count, ai_recommended_count, now, candidate_id),
                )

            conn.commit()
