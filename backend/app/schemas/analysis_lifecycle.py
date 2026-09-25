"""Public response fields for stored analyses without inference results."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AnalysisLifecycleResponse(BaseModel):
    """Safe analysis metadata; private object keys and owner IDs stay internal."""

    model_config = ConfigDict(from_attributes=True)

    analysis_id: UUID
    status: Literal["pending", "completed", "failed"]
    created_at: datetime
    image_content_type: str
    image_size_bytes: int
    result_available: bool
