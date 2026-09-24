"""
User Request Contract
Defines the structure of incoming user requests to the agentic system.
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class UserRequest(BaseModel):
    """
    Application-level representation of a user request.

    Attributes:
        request_id: Unique identifier for this request
        user_id: Identifier for the user making the request
        message: The user's natural language request/message
        timestamp: When the request was received
        context: Additional contextual information (optional)
    """
    request_id: str = Field(..., description="Unique identifier for this request")
    user_id: str = Field(..., description="Identifier for the user making the request")
    message: str = Field(..., description="The user's natural language request/message")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When the request was received")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional contextual information")

    class Config:
        json_schema_extra = {
            "example": {
                "request_id": "req_123456789",
                "user_id": "user_abc123",
                "message": "My rose plant has yellow spots on the leaves, what should I do?",
                "timestamp": "2026-09-24T10:30:00Z",
                "context": {
                    "plant_id": "plant_789",
                    "location": "backyard",
                    "season": "summer"
                }
            }
        }