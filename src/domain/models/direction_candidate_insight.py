"""
Finder 候选词证据与机会状态模型。
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

OpportunityStatus = Literal["cold", "watch", "test", "hot"]
SuggestedAction = Literal["collect_more", "watch", "test_now", "promote"]


class DirectionCandidateEvidence(BaseModel):
    model_config = ConfigDict(extra="ignore")

    candidate_id: int
    sample_count: int = 0
    recent_items_24h: int = 0
    previous_items_24h: int = 0
    unique_sellers: int = 0
    recommended_items: int = 0
    ai_recommended_items: int = 0
    median_price: float | None = None
    price_spread: float | None = None
    signal_hits: int = 0
    top_signals: list[str] = []
    latest_crawl_time: datetime | None = None
    updated_at: datetime | None = None


class DirectionCandidateOpportunityState(BaseModel):
    model_config = ConfigDict(extra="ignore")

    candidate_id: int
    heat_score: int = 0
    momentum_score: int = 0
    commercial_score: int = 0
    competition_score: int = 0
    confidence_score: int = 0
    opportunity_score: int = 0
    status: OpportunityStatus = "cold"
    suggested_action: SuggestedAction = "collect_more"
    updated_at: datetime | None = None
