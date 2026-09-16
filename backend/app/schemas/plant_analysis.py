"""
Pydantic schemas for plant analysis requests and responses
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class SeverityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class HealthStatus(str, Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    CRITICAL = "critical"


class PlantAnalysisRequest(BaseModel):
    """Request for plant analysis"""
    # For image analysis: the uploaded file
    # For video analysis: the uploaded file
    # Analysis type determined by endpoint
    pass  # File handling done in route


class LeafResult(BaseModel):
    """Result for a single leaf analysis"""
    leaf_index: int = Field(..., description="Index of the leaf in the analysis")
    bounding_box: List[float] = Field(..., min_items=4, max_items=4, description="[x_min, y_min, width, height] normalized 0-1")
    disease_class: str = Field(..., description="Disease classification (e.g., 'healthy', 'leaf_spot')")
    classification_confidence: float = Field(..., ge=0, le=1, description="Confidence in disease classification")
    all_probabilities: Optional[Dict[str, float]] = Field(None, description="Probabilities for all disease classes")
    disease_mask: Optional[List[List[bool]]] = Field(None, description="Binary mask of diseased regions (True=diseased)")
    diseased_area_ratio: float = Field(..., ge=0, le=1, description="Ratio of diseased pixels to total leaf area")
    disease_bounding_box: List[float] = Field(..., min_items=4, max_items=4, description="[x_min, y_min, width, height] of diseased region normalized")
    severity_score: float = Field(..., ge=0, le=1, description="Severity score (0=healthy, 1=severe)")
    severity_level: SeverityLevel = Field(..., description="Categorical severity level")
    affected_percentage: float = Field(..., ge=0, le=100, description="Percentage of leaf affected")
    leaf_confidence: Optional[float] = Field(None, ge=0, le=1, description="Confidence in leaf detection")
    explainability_heatmap: Optional[List[List[float]]] = Field(None, description="Grad-CAM heatmap (0-1)")


class DiseaseResult(BaseModel):
    """Disease-specific result"""
    disease_class: str
    confidence: float
    description: Optional[str] = None


class SeverityResult(BaseModel):
    """Severity assessment result"""
    score: float = Field(..., ge=0, le=1)
    level: SeverityLevel
    percentage: float = Field(..., ge=0, le=100)
    metrics: Optional[Dict[str, Any]] = None


class ExplainabilityResult(BaseModel):
    """Explainability result"""
    heatmap: List[List[float]] = Field(..., description="Normalized heatmap (0-1)")
    overlay: Optional[List[List[List[float]]]] = Field(None, description="RGB overlay visualization")
    activation_map: Optional[List[List[float]]] = Field(None, description="Raw activation values")


class PlantHealthSummary(BaseModel):
    """Plant-level health summary"""
    overall_health_score: float = Field(..., ge=0, le=100, description="Overall plant health (0-100)")
    health_status: HealthStatus = Field(..., description="Overall health status")
    healthy_leaf_count: int = Field(..., ge=0, description="Number of healthy leaves")
    total_leaf_count: int = Field(..., ge=0, description="Total number of leaves analyzed")
    disease_summary: Dict[str, int] = Field(..., description="Count of each disease type")
    risk_assessment: str = Field(..., description="Overall risk level")
    recommendations: List[str] = Field(..., description="Care recommendations")


class CareRecommendation(BaseModel):
    """Single care recommendation"""
    title: str
    description: str
    priority: str = Field(..., description="high, medium, low")
    category: str = Field(..., description="watering, lighting, treatment, etc.")


class PlantAnalysisResponse(BaseModel):
    """Complete plant analysis response"""
    analysis_id: str = Field(..., description="Unique identifier for this analysis")
    timestamp: datetime = Field(..., description="When the analysis was performed")
    status: str = Field(..., description="Analysis status: completed, failed, processing")
    leaf_results: List[LeafResult] = Field(..., description="Results for each leaf analyzed")
    plant_health_summary: PlantHealthSummary = Field(..., description="Plant-level health summary")
    processing_time_ms: Optional[int] = Field(None, description="Processing time in milliseconds")
    ml_mode: str = Field(..., description="ML mode used: mock or real")