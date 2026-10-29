"""Schemas for user dashboard aggregation metrics."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.analysis_lifecycle import AnalysisLifecycleResponse


class HealthTrendPoint(BaseModel):
    analysis_id: UUID
    timestamp: datetime
    health_score: float
    health_status: str
    severity_percentage: Optional[float] = None


class DashboardMetricsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_analyses: int = Field(default=0, ge=0)
    healthy_analyses: int = Field(default=0, ge=0)
    diseased_analyses: int = Field(default=0, ge=0)
    inconclusive_analyses: int = Field(default=0, ge=0)
    failed_analyses: int = Field(default=0, ge=0)
    total_plants: int = Field(default=0, ge=0)
    average_health_score: Optional[float] = None
    disease_distribution: Dict[str, int] = Field(default_factory=dict)
    recent_scans: List[AnalysisLifecycleResponse] = Field(default_factory=list)
    health_trend: List[HealthTrendPoint] = Field(default_factory=list)

