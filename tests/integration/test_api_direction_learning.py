from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from src.api import dependencies as deps
from src.api.routes import direction_learning
from src.services.direction_learning_service import DirectionLearningService
from src.infrastructure.persistence.sqlite_bootstrap import bootstrap_sqlite_storage
from src.infrastructure.persistence.sqlite_connection import sqlite_connection


@pytest.fixture()
def learning_client(tmp_path):
    db_path = str(tmp_path / "app.sqlite3")
    bootstrap_sqlite_storage(db_path, legacy_config_file=None)
    service = DirectionLearningService(db_path=db_path, legacy_config_file=None)
    app = FastAPI()
    app.include_router(direction_learning.router)
    app.dependency_overrides[deps.get_direction_learning_service] = lambda: service
    return TestClient(app), db_path


def test_direction_learning_summary(learning_client):
    client, db_path = learning_client
    now = datetime.now(UTC).isoformat()
    with sqlite_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO radar_directions (id, name, seed_topic, user_goal, preferred_variants_json, risk_level, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (1, "方向", "小红书运营", "", '["product"]', "medium", "active", now, now),
        )
        conn.execute(
            """
            INSERT INTO radar_learning_feedback (
                direction_id, candidate_id, recommendation_id, task_id, feedback_type, feedback_value, note, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (1, None, None, None, "recommendation_accept", "accepted", "", now),
        )
        conn.execute(
            """
            INSERT INTO radar_experiments (
                direction_id, candidate_id, recommendation_id, task_id, task_name, keyword, status, source, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (1, None, None, None, None, "小红书运营 教程", "completed", "finder", now, now),
        )
        conn.commit()

    response = client.get("/api/finder/directions/1/learning-summary")
    assert response.status_code == 200
    summary = response.json()["summary"]
    assert summary["accepted_recommendations"] == 1
    assert summary["total_experiments"] == 1
