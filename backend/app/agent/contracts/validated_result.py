"""
Validated Result Contract
Defines the structure of validated operation results.
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from .operation_result import OperationResult


class ValidatedResult(BaseModel):
    """
    Validated operation result after passing through the result validator.

    Attributes:
        operation_id: Identifier of the operation
        validated: Whether the result passed validation
        validated_data: The validated result data (if validation passed)
        validation_errors: List of validation errors (if validation failed)
        validation_warnings: List of validation warnings (if any)
        original_result: The original operation result
        timestamp: When validation was performed
    """
    operation_id: str = Field(..., description="Identifier of the operation")
    validated: bool = Field(..., description="Whether the result passed validation")
    validated_data: Optional[Dict[str, Any]] = Field(None, description="The validated result data")
    validation_errors: List[str] = Field(default_factory=list, description="List of validation errors")
    validation_warnings: List[str] = Field(default_factory=list, description="List of validation warnings")
    original_result: OperationResult = Field(..., description="The original operation result")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When validation was performed")
