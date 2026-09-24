"""
Final Response Contract
Defines the structure of the final response to the user.
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class FinalResponse(BaseModel):
    """
    Final response to the user after complete processing.

    Attributes:
        request_id: Identifier of the original user request
        response_id: Unique identifier for this response
        timestamp: When the response was generated
        status: Overall status of the processing (success, partial_success, failure)
        message: Human-readable response message
        data: Structured data resulting from the processing
        suggestions: Optional follow-up suggestions or actions
        processing_time_ms: Total processing time (in milliseconds)
        ml_mode: Indicates whether ML integration is available
    """
    request_id: str = Field(..., description="Identifier of the original user request")
    response_id: str = Field(..., description="Unique identifier for this response")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When the response was generated")
    status: str = Field(..., description="Overall status: success, partial_success, failure")
    message: str = Field(..., description="Human-readable response message")
    data: Optional[Dict[str, Any]] = Field(None, description="Structured data resulting from the processing")
    suggestions: Optional[List[str]] = Field(None, description="Optional follow-up suggestions or actions")
    processing_time_ms: int = Field(..., description="Total processing time (in milliseconds)")
    ml_mode: str = Field(..., description="ML integration status")
