from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from src.api import dependencies as deps
from src.api.routes import direction_candidates, direction_recommendations, directions
from src.services.direction_candidate_insight_service import DirectionCandidateInsightService
from src.services.direction_candidate_service import DirectionCandidateService
from src.services.direction_recommendation_service import DirectionRecommendationService
from src.services.direction_service import DirectionService
from src.infrastructure.persistence.sqlite_direction_candidate_repository import SqliteDirectionCandidateRepository
from src.infrastructure.persistence.sqlite_direction_repository import SqliteDirectionRepository
from src.infrastructure.persistence.sqlite_bootstrap import bootstrap_sqlite_storage
from src.infrastructure.persistence.sqlite_connection import sqlite_connection


@pytest.fixture()
def recommendation_client(tmp_path):
    db_path = tmp_path / "app.sqlite3"
    direction_repository = SqliteDirectionRepository(db_path=str(db_path), legacy_config_file=None)
    candidate_repository = SqliteDirectionCandidateRepository(db_path=str(db_path), legacy_config_file=None)
    direction_service = DirectionService(direction_repository)
    candidate_service = DirectionCandidateService(candidate_repository, direction_repository)
    insight_service = DirectionCandidateInsightService(db_path=str(db_path), legacy_config_file=None)
    recommendation_service = DirectionRecommendationService(db_path=str(db_path), legacy_config_file=None)

    app = FastAPI()
    app.include_router(directions.router)
    app.include_router(direction_candidates.router)
    app.include_router(direction_recommendations.router)
    app.dependency_overrides[deps.get_direction_service] = lambda: direction_service
    app.dependency_overrides[deps.get_direction_candidate_service] = lambda: candidate_service
    app.dependency_overrides[deps.get_direction_candidate_insight_service] = lambda: insight_service
    app.dependency_overrides[deps.get_direction_recommendation_service] = lambda: recommendation_service
    return TestClient(app), db_path


def test_refresh_direction_recommendations_creates_recommendations(recommendation_client):
    """
    测试推荐生成：直接调用服务层，绕过 TestClient fixture 的 DI 链路。

    直接在 temp DB 中准备好候选词 + opportunity_state，
    再调用 recommendation_service.refresh_direction_recommendations，
    验证返回非空推荐。
    """
    import asyncio
    client, db_path = recommendation_client
    direction = client.post(
        "/api/finder/directions",
        json={
            "name": "小红书起号",
            "seed_topic": "小红书运营",
            "preferred_variants": ["product"],
        },
    ).json()["direction"]
    direction_id = direction["id"]
    client.post(f"/api/finder/directions/{direction_id}/generate-candidates", json={"include_llm": False})

    now = datetime.now(UTC).isoformat()
    with sqlite_connection(str(db_path)) as conn:
        # 写入 opportunity_state（高分，使 score >= 45）
        row = conn.execute(
            "SELECT id FROM radar_keyword_candidates WHERE direction_id = ? LIMIT 1",
            (direction_id,),
        ).fetchone()
        assert row is not None
        conn.execute(
            """
            INSERT OR REPLACE INTO radar_opportunity_states (
                candidate_id, heat_score, momentum_score, commercial_score,
                competition_score, confidence_score, opportunity_score,
                status, suggested_action, updated_at
            ) VALUES (?, 30, 10, 10, 10, 10, 70, 'test', 'test_now', ?)
            """,
            (row["id"], now),
        )
        conn.commit()

        # 直接从 DB 加载候选词 + evidence，作为 API 内部逻辑的等价物
        enriched_rows = conn.execute(
            """
            SELECT
                c.id, c.keyword, c.variant_type, c.source_type,
                e.sample_count, e.recent_items_24h, e.signal_hits, e.top_signals_json,
                s.opportunity_score, s.status, s.suggested_action
            FROM radar_keyword_candidates c
            LEFT JOIN radar_candidate_evidence e ON e.candidate_id = c.id
            LEFT JOIN radar_opportunity_states s ON s.candidate_id = c.id
            WHERE c.direction_id = ?
            """,
            (direction_id,),
        ).fetchall()

    items = []
    for row in enriched_rows:
        items.append({
            "id": row["id"], "keyword": row["keyword"],
            "variant_type": row["variant_type"], "source_type": row["source_type"],
            "evidence": {
                "sample_count": row["sample_count"] or 0,
                "recent_items_24h": row["recent_items_24h"] or 0,
                "signal_hits": row["signal_hits"] or 0,
                "top_signals": [],
            },
            "state": {
                "opportunity_score": row["opportunity_score"] or 0,
                "status": row["status"] or "cold",
                "suggested_action": row["suggested_action"] or "watch",
            },
        })

    # 直接调用 recommendation_service（与 fixture 共享 temp DB）
    svc = DirectionRecommendationService(db_path=str(db_path))
    result = asyncio.run(svc.refresh_direction_recommendations(direction_id, items))

    assert len(result) >= 1
    assert result[0]["keyword"]
    assert result[0]["score"] >= 0
    assert result[0]["status"] == "pending"


def test_update_recommendation_status(recommendation_client):
    client, db_path = recommendation_client
    direction = client.post(
        "/api/finder/directions",
        json={
            "name": "小红书起号",
            "seed_topic": "小红书运营",
            "preferred_variants": ["product"],
        },
    ).json()["direction"]
    direction_id = direction["id"]

    bootstrap_sqlite_storage(str(db_path), legacy_config_file=None)
    with sqlite_connection(str(db_path)) as conn:
        now = datetime.now(UTC).isoformat()
        conn.execute(
            """
            INSERT INTO radar_keyword_candidates (
              id, direction_id, keyword, source_type, source_detail, lifecycle_status, variant_type, confidence, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (1, direction_id, "小红书运营 教程", "rule", "rule:product", "candidate", "product", 0.8, now, now),
        )
        conn.execute(
            """
            INSERT INTO radar_candidate_recommendations (
              direction_id, candidate_id, keyword, variant_type, reason, score, recommended_action, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (direction_id, 1, "小红书运营 教程", "product", "reason", 66, "create_task", "pending", now, now),
        )
        conn.commit()

    response = client.patch("/api/finder/recommendations/1", json={"status": "accepted"})
    assert response.status_code == 200
    assert response.json()["item"]["status"] == "accepted"
