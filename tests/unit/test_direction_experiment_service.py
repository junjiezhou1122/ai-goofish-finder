from datetime import UTC, datetime

from src.domain.models.task import Task
from src.infrastructure.persistence.sqlite_bootstrap import bootstrap_sqlite_storage
from src.infrastructure.persistence.sqlite_connection import sqlite_connection
from src.services.direction_experiment_service import DirectionExperimentService


def test_experiment_service_updates_status_from_task_and_samples(tmp_path):
    db_path = str(tmp_path / "app.sqlite3")
    bootstrap_sqlite_storage(db_path, legacy_config_file=None)

    with sqlite_connection(db_path) as conn:
        now = datetime.now(UTC).isoformat()
        conn.execute(
            """
            INSERT INTO radar_directions (id, name, seed_topic, user_goal, preferred_variants_json, risk_level, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (1, "方向", "小红书运营", "", '["product"]', "medium", "active", now, now),
        )
        conn.execute(
            """
            INSERT INTO tasks (
                id, task_name, enabled, keyword, description, analyze_images,
                max_pages, personal_only, min_price, max_price, cron,
                ai_prompt_base_file, ai_prompt_criteria_file, account_state_file,
                account_strategy, free_shipping, new_publish_option, region,
                decision_mode, keyword_rules_json, is_running
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (9, "Finder 推荐任务", 1, "小红书运营 教程", "", 1, 1, 1, None, None, None, "prompts/base_prompt.txt", "", None, "auto", 1, None, None, "ai", "[]", 0),
        )
        conn.execute(
            """
            INSERT INTO radar_experiments (
                direction_id, candidate_id, recommendation_id, task_id, task_name, keyword, status, source, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (1, None, None, 9, "Finder 推荐任务", "小红书运营 教程", "draft", "finder", now, now),
        )
        conn.execute(
            """
            INSERT INTO result_items (
              result_filename, keyword, task_name, crawl_time, publish_time, price, price_display, item_id,
              title, link, link_unique_key, seller_nickname, is_recommended, analysis_source, keyword_hit_count, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("finder.jsonl", "小红书运营 教程", "Finder 推荐任务", now, now, 88.0, "88", "item-1", "小红书运营 教程", "http://example.com/1", "key-1", "seller-a", 1, "ai", 1, "{}"),
        )
        conn.commit()

    service = DirectionExperimentService(db_path=db_path, legacy_config_file=None)
    experiments = service._list_direction_experiments_sync(1)
    assert experiments[0]["status"] == "completed"
    assert experiments[0]["sample_count"] == 1
