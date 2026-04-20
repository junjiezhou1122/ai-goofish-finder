from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from src.api import dependencies as deps
from src.api.routes import directions
from src.infrastructure.persistence.sqlite_direction_repository import SqliteDirectionRepository
from src.services.direction_service import DirectionService


@pytest.fixture()
def direction_client(tmp_path):
    db_path = tmp_path / "app.sqlite3"
    repository = SqliteDirectionRepository(db_path=str(db_path))
    service = DirectionService(repository)

    app = FastAPI()
    app.include_router(directions.router)
    app.dependency_overrides[deps.get_direction_service] = lambda: service
    return TestClient(app)


def test_create_list_update_delete_direction(direction_client):
    payload = {
        "name": "小红书起号",
        "seed_topic": "小红书运营",
        "user_goal": "找自动交付和轻服务类词",
        "preferred_variants": ["product", "service", "delivery"],
        "risk_level": "medium",
    }

    response = direction_client.post("/api/finder/directions", json=payload)
    assert response.status_code == 200
    created = response.json()["direction"]
    direction_id = int(created["id"])
    assert direction_id >= 0
    assert created["name"] == payload["name"]
    assert created["preferred_variants"] == payload["preferred_variants"]
    assert created["status"] == "active"
    assert created["created_at"]
    assert created["updated_at"]

    list_response = direction_client.get("/api/finder/directions")
    assert list_response.status_code == 200
    directions_payload = list_response.json()
    assert len(directions_payload) == 1
    assert directions_payload[0]["seed_topic"] == payload["seed_topic"]

    patch_response = direction_client.patch(
        f"/api/finder/directions/{direction_id}",
        json={"risk_level": "high", "status": "paused", "preferred_variants": ["service"]},
    )
    assert patch_response.status_code == 200
    updated = patch_response.json()["direction"]
    assert updated["risk_level"] == "high"
    assert updated["status"] == "paused"
    assert updated["preferred_variants"] == ["service"]

    get_response = direction_client.get(f"/api/finder/directions/{direction_id}")
    assert get_response.status_code == 200
    assert get_response.json()["name"] == payload["name"]

    delete_response = direction_client.delete(f"/api/finder/directions/{direction_id}")
    assert delete_response.status_code == 200

    missing_response = direction_client.get(f"/api/finder/directions/{direction_id}")
    assert missing_response.status_code == 404


def test_create_direction_rejects_invalid_variant(direction_client):
    response = direction_client.post(
        "/api/finder/directions",
        json={
            "name": "AI 绘画",
            "seed_topic": "AI 绘画副业",
            "preferred_variants": ["unknown"],
        },
    )
    assert response.status_code == 422
