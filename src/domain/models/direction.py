"""
Finder Direction 领域模型。
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

DirectionVariant = Literal["product", "service", "delivery", "generic"]
DirectionRiskLevel = Literal["low", "medium", "high"]
DirectionStatus = Literal["active", "paused", "archived"]


_ALLOWED_VARIANTS = {"product", "service", "delivery", "generic"}
_ALLOWED_RISK_LEVELS = {"low", "medium", "high"}
_ALLOWED_STATUSES = {"active", "paused", "archived"}


def _normalize_variants(value) -> list[DirectionVariant]:
    if value is None:
        return ["product", "service", "delivery"]

    raw_values = value if isinstance(value, (list, tuple, set)) else [value]
    normalized: list[DirectionVariant] = []
    seen: set[str] = set()
    for item in raw_values:
        text = str(item or "").strip().lower()
        if not text:
            continue
        if text not in _ALLOWED_VARIANTS:
            raise ValueError("preferred_variants 包含不支持的类型")
        if text in seen:
            continue
        seen.add(text)
        normalized.append(text)  # type: ignore[arg-type]

    return normalized or ["product", "service", "delivery"]


def _normalize_string(value: Optional[str]) -> str:
    return str(value or "").strip()


def _normalize_optional_string(value: Optional[str]) -> Optional[str]:
    text = _normalize_string(value)
    return text or None


def _normalize_risk_level(value: Optional[str]) -> DirectionRiskLevel:
    text = _normalize_string(value).lower() or "medium"
    if text not in _ALLOWED_RISK_LEVELS:
        raise ValueError("risk_level 必须是 low / medium / high")
    return text  # type: ignore[return-value]


def _normalize_status(value: Optional[str]) -> DirectionStatus:
    text = _normalize_string(value).lower() or "active"
    if text not in _ALLOWED_STATUSES:
        raise ValueError("status 必须是 active / paused / archived")
    return text  # type: ignore[return-value]


class Direction(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int | None = None
    name: str
    seed_topic: str
    user_goal: str | None = None
    preferred_variants: list[DirectionVariant] = Field(default_factory=lambda: ["product", "service", "delivery"])
    risk_level: DirectionRiskLevel = "medium"
    status: DirectionStatus = "active"
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @field_validator("name", "seed_topic", mode="before")
    @classmethod
    def normalize_required_text(cls, value):
        text = _normalize_string(value)
        if not text:
            raise ValueError("字段不能为空")
        return text

    @field_validator("user_goal", mode="before")
    @classmethod
    def normalize_optional_text(cls, value):
        return _normalize_optional_string(value)

    @field_validator("preferred_variants", mode="before")
    @classmethod
    def normalize_preferred_variants(cls, value):
        return _normalize_variants(value)

    @field_validator("risk_level", mode="before")
    @classmethod
    def normalize_risk(cls, value):
        return _normalize_risk_level(value)

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status_value(cls, value):
        return _normalize_status(value)



class DirectionCreate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    seed_topic: str
    user_goal: str | None = None
    preferred_variants: list[DirectionVariant] = Field(default_factory=lambda: ["product", "service", "delivery"])
    risk_level: DirectionRiskLevel = "medium"
    status: DirectionStatus = "active"

    @field_validator("name", "seed_topic", mode="before")
    @classmethod
    def normalize_required_text(cls, value):
        text = _normalize_string(value)
        if not text:
            raise ValueError("字段不能为空")
        return text

    @field_validator("user_goal", mode="before")
    @classmethod
    def normalize_optional_text(cls, value):
        return _normalize_optional_string(value)

    @field_validator("preferred_variants", mode="before")
    @classmethod
    def normalize_preferred_variants(cls, value):
        return _normalize_variants(value)

    @field_validator("risk_level", mode="before")
    @classmethod
    def normalize_risk(cls, value):
        return _normalize_risk_level(value)

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status_value(cls, value):
        return _normalize_status(value)


class DirectionUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str | None = None
    seed_topic: str | None = None
    user_goal: str | None = None
    preferred_variants: list[DirectionVariant] | None = None
    risk_level: DirectionRiskLevel | None = None
    status: DirectionStatus | None = None

    @field_validator("name", "seed_topic", mode="before")
    @classmethod
    def normalize_required_text(cls, value):
        if value is None:
            return value
        text = _normalize_string(value)
        if not text:
            raise ValueError("字段不能为空")
        return text

    @field_validator("user_goal", mode="before")
    @classmethod
    def normalize_optional_text(cls, value):
        if value is None:
            return value
        return _normalize_optional_string(value)

    @field_validator("preferred_variants", mode="before")
    @classmethod
    def normalize_preferred_variants(cls, value):
        if value is None:
            return value
        return _normalize_variants(value)

    @field_validator("risk_level", mode="before")
    @classmethod
    def normalize_risk(cls, value):
        if value is None:
            return value
        return _normalize_risk_level(value)

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status_value(cls, value):
        if value is None:
            return value
        return _normalize_status(value)
