"""Schemas for plant entity and plant tracking workflows."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.analysis_lifecycle import AnalysisLifecycleResponse


class PlantCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(..., min_length=1, max_length=128, description="User-assigned plant name")
    species: Optional[str] = Field(None, max_length=128, description="Botanical or common species name")
    location: Optional[str] = Field(None, max_length=128, description="Garden, pot, or greenhouse location")
    notes: Optional[str] = Field(None, max_length=512, description="Agronomic or care notes")


class PlantUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: Optional[str] = Field(None, min_length=1, max_length=128)
    species: Optional[str] = Field(None, max_length=128)
    location: Optional[str] = Field(None, max_length=128)
    notes: Optional[str] = Field(None, max_length=512)


class PlantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    name: str
    species: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    total_scans: int = 0
    health_status: Optional[str] = None
    latest_analysis: Optional[AnalysisLifecycleResponse] = None


class PlantDetailResponse(PlantResponse):
    recent_scans: List[AnalysisLifecycleResponse] = Field(default_factory=list)
    health_trend: List[Dict[str, Any]] = Field(default_factory=list)

