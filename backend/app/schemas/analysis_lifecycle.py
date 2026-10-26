"""Public response fields for stored analyses without inference results."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.inference import FullScanResult


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
