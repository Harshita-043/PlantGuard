"""
Pydantic Schemas for API Requests and Responses
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


# Health check schemas
class HealthResponse(BaseModel):
    message: str


# Scan-related schemas
class LeafResultBase(BaseModel):
    leaf_index: int
    bounding_box: List[float] = Field(..., min_items=4, max_items=4)  # [x, y, width, height] normalized
    disease_class: str
    classification_confidence: float = Field(..., ge=0, le=1)
    all_probabilities: Optional[Dict[str, float]] = None
    disease_mask: Optional[List[List[bool]]] = None  # 2D boolean array (would be serialized differently in practice)
    diseased_area_ratio: float = Field(..., ge=0, le=1)
    disease_bounding_box: List[float] = Field(..., min_items=4, max_items=4)  # [x, y, width, height] normalized
    severity_score: float = Field(..., ge=0, le=1)
    severity_level: str  # low, medium, high
    affected_percentage: float = Field(..., ge=0, le=100)
    severity_metrics: Optional[Dict[str, Any]] = None
    explainability_heatmap: Optional[List[List[float]]] = None  # 2D float array (0-1)
    explainability_overlay: Optional[List[List[List[float]]]] = None  # 3D array for RGB overlay
    leaf_confidence: Optional[float] = Field(None, ge=0, le=1)


class LeafResult(LeafResultBase):
    id: int
    scan_id: int
    created_at: datetime

    class Config:
        orm_mode = True


class HealthReportBase(BaseModel):
    overall_health_score: float = Field(..., ge=0, le=100)
    risk_assessment: str  # low, medium, high
    healthy_leaf_count: int = Field(..., ge=0)
    total_leaf_count: int = Field(..., ge=0)
    disease_summary: Dict[str, Any]
    recommendations: List[str]


class HealthReport(HealthReportBase):
    id: int
    scan_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class PlantScanBase(BaseModel):
    plant_name: Optional[str] = None
    scan_type: str = "image"  # image, video, live
    status: str = "completed"  # pending, processing, completed, failed
    overall_health_score: Optional[float] = Field(None, ge=0, le=100)
    risk_assessment: Optional[str] = None  # low, medium, high


class PlantScanCreate(PlantScanBase):
    image_url: str


class PlantScan(PlantScanBase):
    id: int
    user_id: int
    image_url: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


# API Response Schemas
class ScanResponse(BaseModel):
    scan_id: str
    message: str
    status: str


class ScanSummary(BaseModel):
    id: str
    plant_name: Optional[str] = None
    date: datetime
    status: str
    overall_health_score: Optional[float] = None


class ScanDetail(BaseModel):
    id: str
    plant_name: Optional[str] = None
    date: datetime
    status: str
    image_url: Optional[str] = None
    leaf_results: List[LeafResultBase]
    health_report: HealthReportBase


class HealthReportResponse(BaseModel):
    scan_id: str
    overall_health_score: float = Field(..., ge=0, le=100)
    health_status: str  # excellent, good, fair, poor, critical
    recommendations: List[str]


# File upload schema (for documentation)
class FileUploadResponse(BaseModel):
    filename: str
    content_type: str
    size: int