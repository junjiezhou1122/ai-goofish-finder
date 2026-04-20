"""
Finder 实验与学习反馈模型。
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

ExperimentStatus = Literal["draft", "running", "completed", "failed", "cancelled"]
FeedbackType = Literal["recommendation_accept", "recommendation_dismiss", "task_created"]


class DirectionExperiment(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int | None = None
    direction_id: int
    candidate_id: int | None = None
    recommendation_id: int | None = None
    task_id: int | None = None
    task_name: str | None = None
    keyword: str
    status: ExperimentStatus = "draft"
    source: str = "finder"
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DirectionLearningFeedback(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int | None = None
    direction_id: int
    candidate_id: int | None = None
    recommendation_id: int | None = None
    task_id: int | None = None
    feedback_type: FeedbackType
    feedback_value: str
    note: str | None = None
    created_at: datetime | None = None
