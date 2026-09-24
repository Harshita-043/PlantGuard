"""
Request Context Contract
Defines the structure of contextual information for user requests.
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class RequestContext(BaseModel):
    """
    Contextual information for user requests.

    Attributes:
        user: User profile information
        plant: Specific plant being referenced (if any)
        scan: Recent scan information (if any)
        image: Image data (if provided)
        video: Video data (if provided)
        location: Geographic location information
        crop: Specific crop type (if relevant)
        region: Geographic region for localized advice
        conversation: Conversation history
        previous_results: Results from previous operations
    """
    user: Optional[Dict[str, Any]] = Field(None, description="User profile information")
    plant: Optional[Dict[str, Any]] = Field(None, description="Specific plant being referenced")
    scan: Optional[Dict[str, Any]] = Field(None, description="Recent scan information")
    image: Optional[Any] = Field(None, description="Opaque image data; never included in an LLM prompt")
    video: Optional[Any] = Field(None, description="Opaque video data; never included in an LLM prompt")
    location: Optional[Dict[str, Any]] = Field(None, description="Geographic location")
    crop: Optional[str] = Field(None, description="Specific crop type")
    region: Optional[str] = Field(None, description="Geographic region")
    conversation: Optional[List[Dict[str, Any]]] = Field(None, description="Conversation history")
    previous_results: Optional[List[Dict[str, Any]]] = Field(None, description="Results from previous operations")

    class Config:
        json_schema_extra = {
            "example": {
                "user": {
                    "id": "user_abc123",
                    "name": "John Doe",
                    "preferences": {
                        "units": "metric",
                        "notifications": True
                    }
                },
                "plant": {
                    "id": "plant_789",
                    "name": "Rose Bush",
                    "species": "Rosa",
                    "location": "backyard"
                },
                "scan": {
                    "scan_id": "scan_456",
                    "timestamp": "2026-09-24T09:00:00Z",
                    "plant_id": "plant_789",
                    "overall_health_score": 75.0
                },
                "location": {
                    "city": "Springfield",
                    "country": "USA",
                    "latitude": 39.78,
                    "longitude": -89.65
                },
                "crop": "rose",
                "region": "midwest",
                "previous_results": [
                    {
                        "operation": "leaf_segmentation",
                        "result": {"leaf_count": 5, "healthy_leaves": 3}
                    }
                ]
            }
        }
