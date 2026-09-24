"""
Operation Result Contract
Defines the structure of results from operation execution.
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class OperationResult(BaseModel):
    """
    Result from operation execution.

    Attributes:
        operation_id: Identifier of the executed operation
        success: Whether the operation executed successfully
        result_data: The actual result data from the operation (if successful)
        error_message: Error message (if unsuccessful)
        execution_time_ms: Time taken to execute the operation (in milliseconds)
        timestamp: When the operation completed
    """
    operation_id: str = Field(..., description="Identifier of the executed operation")
    success: bool = Field(..., description="Whether the operation executed successfully")
    result_data: Optional[Dict[str, Any]] = Field(None, description="The actual result data from the operation")
    error_message: Optional[str] = Field(None, description="Error message (if unsuccessful)")
    execution_time_ms: Optional[int] = Field(None, description="Time taken to execute the operation (in milliseconds)")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When the operation completed")
