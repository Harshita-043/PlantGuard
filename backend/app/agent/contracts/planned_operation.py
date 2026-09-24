"""
Planned Operation Contract
Defines the structure of individual operations within a plan.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class PlannedOperation(BaseModel):
    """
    Individual operation within a planner-generated plan.

    Attributes:
        operation_id: Unique identifier for this operation within the plan
        capability: The capability/service to invoke (e.g., "leaf_segmentation")
        arguments: Arguments to pass to the capability
        dependencies: List of operation_ids that must complete before this operation
        reason: Explanation of why this operation is needed
        context_requirements: Context data required for this operation
    """
    operation_id: str = Field(..., description="Unique identifier for this operation within the plan")
    capability: str = Field(..., description="The capability/service to invoke")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Arguments to pass to the capability")
    dependencies: List[str] = Field(default_factory=list, description="List of operation_ids that must complete before this operation")
    reason: str = Field(..., description="Explanation of why this operation is needed")
    context_requirements: List[str] = Field(default_factory=list, description="Context data required for this operation")

    class Config:
        json_schema_extra = {
            "example": {
                "operation_id": "op_1",
                "capability": "leaf_segmentation",
                "arguments": {},
                "dependencies": [],
                "reason": "First, segment leaves from the whole plant image",
                "context_requirements": ["image"]
            }
        }