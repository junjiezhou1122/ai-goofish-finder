from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from src.api import dependencies as deps
from src.api.routes import direction_candidates, directions
from src.infrastructure.persistence.sqlite_direction_candidate_repository import SqliteDirectionCandidateRepository
from src.infrastructure.persistence.sqlite_direction_repository import SqliteDirectionRepository
from src.services.direction_candidate_service import DirectionCandidateService
from src.services.direction_candidate_insight_service import DirectionCandidateInsightService
from src.services.direction_service import DirectionService


@pytest.fixture()
def direction_candidate_client(tmp_path):
    db_path = tmp_path / "app.sqlite3"
    direction_repository = SqliteDirectionRepository(db_path=str(db_path), legacy_config_file=None)
    candidate_repository = SqliteDirectionCandidateRepository(db_path=str(db_path), legacy_config_file=None)
    direction_service = DirectionService(direction_repository)
    candidate_service = DirectionCandidateService(candidate_repository, direction_repository)
    insight_service = DirectionCandidateInsightService(db_path=str(db_path), legacy_config_file=None)

    app = FastAPI()
    app.include_router(directions.router)
    app.include_router(direction_candidates.router)
    app.dependency_overrides[deps.get_direction_service] = lambda: direction_service
    app.dependency_overrides[deps.get_direction_candidate_service] = lambda: candidate_service
    app.dependency_overrides[deps.get_direction_candidate_insight_service] = lambda: insight_service
    return TestClient(app)


def test_generate_and_list_candidates(direction_candidate_client):
    create_direction_response = direction_candidate_client.post(
        "/api/finder/directions",
        json={
            "name": "小红书起号",
            "seed_topic": "小红书运营",
            "user_goal": "找适合轻服务的词",
            "preferred_variants": ["product", "service"],
        },
    )
    assert create_direction_response.status_code == 200
    direction_id = create_direction_response.json()["direction"]["id"]

    generate_response = direction_candidate_client.post(
        f"/api/finder/directions/{direction_id}/generate-candidates",
        json={"include_llm": False},
    )
    assert generate_response.status_code == 200
    generated = generate_response.json()
    assert generated["count"] >= 1
    assert generated["include_llm"] is False
    assert generated["llm_generated"] == 0
    keywords = {item["keyword"] for item in generated["items"]}
    assert "小红书运营 教程" in keywords
    assert "小红书运营 代搭建" in keywords

    list_response = direction_candidate_client.get(
        f"/api/finder/directions/{direction_id}/candidates"
    )
    assert list_response.status_code == 200
    listed_keywords = {item["keyword"] for item in list_response.json()["items"]}
    assert keywords == listed_keywords


def test_generate_candidates_for_missing_direction_returns_404(direction_candidate_client):
    response = direction_candidate_client.post("/api/finder/directions/999/generate-candidates")
    assert response.status_code == 404


def test_refresh_candidates_endpoint_returns_enriched_payload(direction_candidate_client):
    create_direction_response = direction_candidate_client.post(
        "/api/finder/directions",
        json={
            "name": "小红书起号",
            "seed_topic": "小红书运营",
            "preferred_variants": ["product"],
        },
    )
    direction_id = create_direction_response.json()["direction"]["id"]
    generate_response = direction_candidate_client.post(
        f"/api/finder/directions/{direction_id}/generate-candidates",
        json={"include_llm": False},
    )
    assert generate_response.status_code == 200

    refresh_response = direction_candidate_client.post(
        f"/api/finder/directions/{direction_id}/refresh-candidates"
    )
    assert refresh_response.status_code == 200
    payload = refresh_response.json()
    assert payload["count"] >= 1
    assert "state" in payload["items"][0]
    assert "evidence" in payload["items"][0]
