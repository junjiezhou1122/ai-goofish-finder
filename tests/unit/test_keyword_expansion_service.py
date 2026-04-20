from datetime import UTC, datetime

from src.domain.models.direction import Direction
from src.services.keyword_expansion_service import build_cooccurrence_candidates, build_rule_based_candidates


def test_build_rule_based_candidates_contains_seed_and_rule_variants():
    direction = Direction(
        id=1,
        name="小红书起号",
        seed_topic="小红书运营",
        preferred_variants=["product", "service", "delivery"],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    candidates = build_rule_based_candidates(direction)
    keywords = {candidate.keyword for candidate in candidates}

    assert "小红书运营" in keywords
    assert "小红书起号" in keywords
    assert "小红书运营 教程" in keywords
    assert "小红书运营 代搭建" in keywords
    assert "小红书运营 自动发货" in keywords


def test_build_rule_based_candidates_deduplicates_existing_suffix():
    direction = Direction(
        id=2,
        name="AI 绘画教程",
        seed_topic="AI 绘画",
        preferred_variants=["product"],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    candidates = build_rule_based_candidates(direction)
    keywords = [candidate.keyword for candidate in candidates]

    assert keywords.count("AI 绘画教程") == 1


def test_build_cooccurrence_candidates_uses_market_titles():
    direction = Direction(
        id=3,
        name="小红书起号",
        seed_topic="小红书运营",
        preferred_variants=["product", "service"],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    existing = build_rule_based_candidates(direction)
    titles = [
        "小红书运营 起号陪跑 自动发货",
        "小红书运营 起号陪跑 模板",
        "小红书运营 代做 资料",
    ]

    candidates = build_cooccurrence_candidates(direction, titles, existing, max_candidates=5)
    keywords = {candidate.keyword for candidate in candidates}
    assert any("陪跑" in keyword or "代做" in keyword for keyword in keywords)
