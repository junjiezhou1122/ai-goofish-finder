"""
Finder 方向候选词领域模型。
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.domain.models.direction import DirectionVariant

CandidateSourceType = Literal["seed", "rule", "llm", "cooccurrence"]
CandidateLifecycleStatus = Literal["seed", "candidate", "validating", "validated", "rejected", "archived"]

_ALLOWED_SOURCE_TYPES = {"seed", "rule", "llm", "cooccurrence"}
_ALLOWED_LIFECYCLE_STATUSES = {"seed", "candidate", "validating", "validated", "rejected", "archived"}


def _normalize_keyword(value: str | None) -> str:
    return str(value or "").strip()


def _normalize_optional_text(value: str | None) -> str | None:
    text = _normalize_keyword(value)
    return text or None


def _normalize_source_type(value: str | None) -> CandidateSourceType:
    text = _normalize_keyword(value).lower() or "rule"
    if text not in _ALLOWED_SOURCE_TYPES:
        raise ValueError("source_type 必须是 seed / rule / llm / cooccurrence")
    return text  # type: ignore[return-value]


def _normalize_lifecycle_status(value: str | None) -> CandidateLifecycleStatus:
    text = _normalize_keyword(value).lower() or "candidate"
    if text not in _ALLOWED_LIFECYCLE_STATUSES:
        raise ValueError("lifecycle_status 不合法")
    return text  # type: ignore[return-value]


def _normalize_confidence(value: float | int | str | None) -> float:
    try:
        confidence = float(value if value is not None else 0.5)
    except (TypeError, ValueError):
        confidence = 0.5
    return max(0.0, min(1.0, round(confidence, 4)))


class DirectionCandidate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int | None = None
    direction_id: int
    keyword: str
    source_type: CandidateSourceType = "rule"
    source_detail: str | None = None
    lifecycle_status: CandidateLifecycleStatus = "candidate"
    variant_type: DirectionVariant = "generic"
    confidence: float = Field(default=0.5, ge=0, le=1)
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @field_validator("keyword", mode="before")
    @classmethod
    def normalize_keyword_field(cls, value):
        text = _normalize_keyword(value)
        if not text:
            raise ValueError("keyword 不能为空")
        return text

    @field_validator("source_detail", mode="before")
    @classmethod
    def normalize_source_detail(cls, value):
        return _normalize_optional_text(value)

    @field_validator("source_type", mode="before")
    @classmethod
    def normalize_source_type_field(cls, value):
        return _normalize_source_type(value)

    @field_validator("lifecycle_status", mode="before")
    @classmethod
    def normalize_lifecycle_status_field(cls, value):
        return _normalize_lifecycle_status(value)

    @field_validator("confidence", mode="before")
    @classmethod
    def normalize_confidence_field(cls, value):
        return _normalize_confidence(value)
