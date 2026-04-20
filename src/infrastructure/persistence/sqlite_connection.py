"""
SQLite 连接与 schema 初始化。
"""
from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from src.infrastructure.persistence.storage_names import DEFAULT_DATABASE_PATH


BUSY_TIMEOUT_MS = 5000

SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS app_metadata (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY,
        task_name TEXT NOT NULL,
        enabled INTEGER NOT NULL,
        keyword TEXT NOT NULL,
        description TEXT,
        analyze_images INTEGER NOT NULL,
        max_pages INTEGER NOT NULL,
        personal_only INTEGER NOT NULL,
        min_price TEXT,
        max_price TEXT,
        cron TEXT,
        ai_prompt_base_file TEXT NOT NULL,
        ai_prompt_criteria_file TEXT NOT NULL,
        account_state_file TEXT,
        account_strategy TEXT NOT NULL,
        free_shipping INTEGER NOT NULL,
        new_publish_option TEXT,
        region TEXT,
        decision_mode TEXT NOT NULL,
        keyword_rules_json TEXT NOT NULL,
        is_running INTEGER NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS result_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        result_filename TEXT NOT NULL,
        keyword TEXT NOT NULL,
        task_name TEXT NOT NULL,
        crawl_time TEXT NOT NULL,
        publish_time TEXT,
        price REAL,
        price_display TEXT,
        item_id TEXT,
        title TEXT,
        link TEXT,
        link_unique_key TEXT NOT NULL,
        seller_nickname TEXT,
        is_recommended INTEGER NOT NULL,
        analysis_source TEXT,
        keyword_hit_count INTEGER NOT NULL,
        raw_json TEXT NOT NULL,
        UNIQUE(result_filename, link_unique_key)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS price_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        keyword_slug TEXT NOT NULL,
        keyword TEXT NOT NULL,
        task_name TEXT NOT NULL,
        snapshot_time TEXT NOT NULL,
        snapshot_day TEXT NOT NULL,
        run_id TEXT NOT NULL,
        item_id TEXT NOT NULL,
        title TEXT,
        price REAL NOT NULL,
        price_display TEXT,
        tags_json TEXT NOT NULL,
        region TEXT,
        seller TEXT,
        publish_time TEXT,
        link TEXT,
        UNIQUE(keyword_slug, run_id, item_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS radar_directions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        seed_topic TEXT NOT NULL,
        user_goal TEXT,
        preferred_variants_json TEXT NOT NULL,
        risk_level TEXT NOT NULL,
        status TEXT NOT NULL,
        expansion_config_json TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS radar_keyword_candidates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        direction_id INTEGER NOT NULL,
        keyword TEXT NOT NULL,
        source_type TEXT NOT NULL,
        source_detail TEXT,
        lifecycle_status TEXT NOT NULL,
        variant_type TEXT NOT NULL,
        confidence REAL NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE(direction_id, keyword),
        FOREIGN KEY (direction_id) REFERENCES radar_directions(id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS radar_candidate_evidence (
        candidate_id INTEGER PRIMARY KEY,
        sample_count INTEGER NOT NULL,
        recent_items_24h INTEGER NOT NULL,
        previous_items_24h INTEGER NOT NULL,
        unique_sellers INTEGER NOT NULL,
        recommended_items INTEGER NOT NULL,
        ai_recommended_items INTEGER NOT NULL,
        median_price REAL,
        price_spread REAL,
        signal_hits INTEGER NOT NULL,
        top_signals_json TEXT NOT NULL,
        latest_crawl_time TEXT,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (candidate_id) REFERENCES radar_keyword_candidates(id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS radar_opportunity_states (
        candidate_id INTEGER PRIMARY KEY,
        heat_score INTEGER NOT NULL,
        momentum_score INTEGER NOT NULL,
        commercial_score INTEGER NOT NULL,
        competition_score INTEGER NOT NULL,
        confidence_score INTEGER NOT NULL,
        opportunity_score INTEGER NOT NULL,
        status TEXT NOT NULL,
        suggested_action TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (candidate_id) REFERENCES radar_keyword_candidates(id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS radar_candidate_recommendations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        direction_id INTEGER NOT NULL,
        candidate_id INTEGER NOT NULL UNIQUE,
        keyword TEXT NOT NULL,
        variant_type TEXT,
        reason TEXT NOT NULL,
        score INTEGER NOT NULL,
        recommended_action TEXT NOT NULL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (direction_id) REFERENCES radar_directions(id) ON DELETE CASCADE,
        FOREIGN KEY (candidate_id) REFERENCES radar_keyword_candidates(id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS radar_experiments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        direction_id INTEGER NOT NULL,
        candidate_id INTEGER,
        recommendation_id INTEGER,
        task_id INTEGER,
        task_name TEXT,
        keyword TEXT NOT NULL,
        status TEXT NOT NULL,
        source TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (direction_id) REFERENCES radar_directions(id) ON DELETE CASCADE,
        FOREIGN KEY (candidate_id) REFERENCES radar_keyword_candidates(id) ON DELETE SET NULL,
        FOREIGN KEY (recommendation_id) REFERENCES radar_candidate_recommendations(id) ON DELETE SET NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS radar_learning_feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        direction_id INTEGER NOT NULL,
        candidate_id INTEGER,
        recommendation_id INTEGER,
        task_id INTEGER,
        feedback_type TEXT NOT NULL,
        feedback_value TEXT NOT NULL,
        note TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (direction_id) REFERENCES radar_directions(id) ON DELETE CASCADE,
        FOREIGN KEY (candidate_id) REFERENCES radar_keyword_candidates(id) ON DELETE SET NULL,
        FOREIGN KEY (recommendation_id) REFERENCES radar_candidate_recommendations(id) ON DELETE SET NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS keyword_annotations (
        keyword TEXT PRIMARY KEY,
        status TEXT NOT NULL,
        note TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS radar_keyword_pool (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        keyword TEXT NOT NULL UNIQUE,
        source TEXT NOT NULL,
        note TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS radar_snapshot_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        note TEXT NOT NULL,
        created_at TEXT NOT NULL,
        keyword_count INTEGER NOT NULL,
        average_score REAL NOT NULL,
        top_keyword TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS radar_snapshot_keywords (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        snapshot_id INTEGER NOT NULL,
        keyword TEXT NOT NULL,
        opportunity_score INTEGER NOT NULL,
        recent_items_24h INTEGER NOT NULL,
        total_items INTEGER NOT NULL,
        unique_sellers INTEGER NOT NULL,
        recommended_items INTEGER NOT NULL,
        signal_hits INTEGER NOT NULL,
        median_price REAL,
        price_spread REAL,
        latest_crawl_time TEXT,
        FOREIGN KEY (snapshot_id) REFERENCES radar_snapshot_runs(id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS radar_keyword_recommendations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        keyword TEXT NOT NULL UNIQUE,
        reason TEXT NOT NULL,
        score INTEGER NOT NULL,
        signal_terms_json TEXT NOT NULL,
        source_keywords_json TEXT NOT NULL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_tasks_name ON tasks(task_name)",
    """
    CREATE INDEX IF NOT EXISTS idx_results_filename_crawl
    ON result_items(result_filename, crawl_time DESC)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_results_filename_publish
    ON result_items(result_filename, publish_time DESC)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_results_filename_price
    ON result_items(result_filename, price DESC)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_results_filename_recommended
    ON result_items(result_filename, is_recommended, analysis_source, crawl_time DESC)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_snapshots_keyword_time
    ON price_snapshots(keyword_slug, snapshot_time DESC)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_snapshots_keyword_item_time
    ON price_snapshots(keyword_slug, item_id, snapshot_time DESC)
    """,
    "CREATE INDEX IF NOT EXISTS idx_radar_directions_status ON radar_directions(status)",
    "CREATE INDEX IF NOT EXISTS idx_radar_directions_updated_at ON radar_directions(updated_at DESC)",
    """
    CREATE INDEX IF NOT EXISTS idx_radar_keyword_candidates_direction_status
    ON radar_keyword_candidates(direction_id, lifecycle_status, updated_at DESC)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_radar_opportunity_states_score
    ON radar_opportunity_states(opportunity_score DESC, updated_at DESC)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_radar_candidate_recommendations_direction_score
    ON radar_candidate_recommendations(direction_id, score DESC, updated_at DESC)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_radar_experiments_direction_created
    ON radar_experiments(direction_id, created_at DESC)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_radar_learning_feedback_direction_created
    ON radar_learning_feedback(direction_id, created_at DESC)
    """,
    "CREATE INDEX IF NOT EXISTS idx_keyword_pool_keyword ON radar_keyword_pool(keyword)",
    """
    CREATE INDEX IF NOT EXISTS idx_radar_snapshot_keywords_snapshot_score
    ON radar_snapshot_keywords(snapshot_id, opportunity_score DESC)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_radar_recommendations_status_score
    ON radar_keyword_recommendations(status, score DESC, updated_at DESC)
    """,
)


def get_database_path() -> str:
    return os.getenv("APP_DATABASE_FILE", DEFAULT_DATABASE_PATH)


def _prepare_database_file(path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)


def _apply_pragmas(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")


def init_schema(conn: sqlite3.Connection) -> None:
    for statement in SCHEMA_STATEMENTS:
        conn.execute(statement)
    conn.commit()


@contextmanager
def sqlite_connection(
    db_path: str | None = None,
) -> Iterator[sqlite3.Connection]:
    path = db_path or get_database_path()
    _prepare_database_file(path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        _apply_pragmas(conn)
        yield conn
    finally:
        conn.close()
