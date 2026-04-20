"""
Finder 方向推荐模型。
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

RecommendationStatus = Literal["pending", "accepted", "dismissed"]


class DirectionRecommendation(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int | None = None
    direction_id: int
    candidate_id: int
    keyword: str
    reason: str
    score: int
    recommended_action: str
    status: RecommendationStatus = "pending"
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @field_validator("keyword", "reason", "recommended_action", mode="before")
    @classmethod
    def normalize_text(cls, value):
        return str(value or "").strip()
