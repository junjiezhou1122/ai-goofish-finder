from datetime import UTC, datetime, timedelta

from src.domain.models.direction_candidate import DirectionCandidate
from src.services.direction_candidate_insight_service import DirectionCandidateInsightService


def test_insight_service_builds_positive_opportunity_state_when_evidence_exists(tmp_path):
    service = DirectionCandidateInsightService(db_path=str(tmp_path / "app.sqlite3"), legacy_config_file=None)
    candidate = DirectionCandidate(
        id=1,
        direction_id=1,
        keyword="小红书运营 教程",
        source_type="rule",
        source_detail="rule:product",
        lifecycle_status="candidate",
        variant_type="product",
        confidence=0.8,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    from src.infrastructure.persistence.sqlite_bootstrap import bootstrap_sqlite_storage
    from src.infrastructure.persistence.sqlite_connection import sqlite_connection

    bootstrap_sqlite_storage(str(tmp_path / "app.sqlite3"), legacy_config_file=None)
    with sqlite_connection(str(tmp_path / "app.sqlite3")) as conn:
      conn.execute(
          """
          INSERT INTO radar_directions (name, seed_topic, user_goal, preferred_variants_json, risk_level, status, created_at, updated_at)
          VALUES (?, ?, ?, ?, ?, ?, ?, ?)
          """,
          ("方向", "小红书运营", "", '["product"]', "medium", "active", datetime.now(UTC).isoformat(), datetime.now(UTC).isoformat()),
      )
      conn.execute(
          """
          INSERT INTO radar_keyword_candidates (
            id, direction_id, keyword, source_type, source_detail, lifecycle_status, variant_type, confidence, created_at, updated_at
          ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
          """,
          (
              1, 1, candidate.keyword, candidate.source_type, candidate.source_detail, candidate.lifecycle_status,
              candidate.variant_type, candidate.confidence, datetime.now(UTC).isoformat(), datetime.now(UTC).isoformat(),
          ),
      )
      now = datetime.now(UTC)
      conn.execute(
          """
          INSERT INTO result_items (
            result_filename, keyword, task_name, crawl_time, publish_time, price, price_display, item_id,
            title, link, link_unique_key, seller_nickname, is_recommended, analysis_source, keyword_hit_count, raw_json
          ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
          """,
          (
              "test.jsonl",
              candidate.keyword,
              "task",
              now.isoformat(),
              now.isoformat(),
              99.0,
              "99",
              "item-1",
              "小红书运营 教程 自动发货",
              "http://example.com/1",
              "key-1",
              "seller-a",
              1,
              "ai",
              1,
              "{}",
          ),
      )
      conn.commit()

    enriched = service._refresh_direction_candidates_sync(1, [candidate])
    assert enriched[0]["state"]["opportunity_score"] > 0
    assert enriched[0]["evidence"]["sample_count"] == 1
