"""Public response fields for stored analyses without inference results."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.inference import FullScanResult


class AnalysisFailure(BaseModel):
    """Safe, structured failure details retained for later scan retrieval."""

    code: str
    stage: str
    message: str
    occurred_at: datetime


class AnalysisLifecycleResponse(BaseModel):
    """Safe lifecycle metadata and the result when inference has completed."""

    model_config = ConfigDict(from_attributes=True)

    analysis_id: UUID
    status: Literal["pending", "completed", "failed"]
    created_at: datetime
    image_content_type: str
    image_size_bytes: int
    result_available: bool
    result: FullScanResult | None = None
    failure: AnalysisFailure | None = None


class AnalysisAssetLink(BaseModel):
    """Temporary link to an original image or analysis artifact."""

    storage_key: str
    kind: Literal["original", "artifact"]
    download_url: str
    expires_in_seconds: int | None = None


class AnalysisAssetsResponse(BaseModel):
    """Asset URLs scoped to one owner-authorized analysis."""

    analysis_id: UUID
    assets: list[AnalysisAssetLink]