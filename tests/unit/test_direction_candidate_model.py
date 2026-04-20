from pydantic import ValidationError

from src.domain.models.direction_candidate import DirectionCandidate


def test_direction_candidate_accepts_llm_source():
    candidate = DirectionCandidate(
        direction_id=1,
        keyword="小红书起号陪跑",
        source_type="llm",
        source_detail="llm suggestion",
        lifecycle_status="candidate",
        variant_type="service",
        confidence=0.81,
    )

    assert candidate.source_type == "llm"
    assert candidate.variant_type == "service"


def test_direction_candidate_rejects_invalid_source():
    try:
        DirectionCandidate(
            direction_id=1,
            keyword="小红书起号陪跑",
            source_type="manual",
            lifecycle_status="candidate",
            variant_type="service",
            confidence=0.81,
        )
    except ValidationError as exc:
        assert "source_type" in str(exc)
    else:
        raise AssertionError("expected ValidationError")
