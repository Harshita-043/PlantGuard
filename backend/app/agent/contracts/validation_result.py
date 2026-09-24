"""
Validation Result Contract
Defines the structure of validation results from the deterministic validator.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class ValidationResult(BaseModel):
    """
    Result from the deterministic validation layer.

    Attributes:
        valid: Whether the plan passed validation
        errors: List of validation errors (if any)
        warnings: List of validation warnings (if any)
        normalized_arguments: Normalized/processed arguments (if any)
        timestamp: When validation was performed
    """
    valid: bool = Field(..., description="Whether the plan passed validation")
    errors: List[str] = Field(default_factory=list, description="List of validation errors")
    warnings: List[str] = Field(default_factory=list, description="List of validation warnings")
    normalized_arguments: Optional[Dict[str, Any]] = Field(None, description="Normalized/processed arguments")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When validation was performed")

    class Config:
        json_schema_extra = {
            "example": {
                "valid": True,
                "errors": [],
                "warnings": ["Optional context 'previous_results' not provided, using defaults"],
                "normalized_arguments": {
                    "operations": [
                        {
                            "operation_id": "op_1",
                            "capability": "leaf_segmentation",
                            "arguments": {},
                            "dependencies": [],
                            "reason": "First, segment leaves from the whole plant image",
                            "context_requirements": ["image"]
                        }
                    ]
                },
                "timestamp": "2026-09-24T10:30:00Z"
            }
        }