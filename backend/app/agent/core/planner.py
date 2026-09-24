"""
Planner Component
Responsible for generating structured plans from user requests.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from ..contracts.user_request import UserRequest
from ..contracts.request_context import RequestContext
from ..contracts.agent_plan import AgentPlan
from ..contracts.planned_operation import PlannedOperation
from ...llm.service import get_llm_service
from ...llm.interface import LLMService


class PlannerComponent:
    """
    Planner component responsible for generating structured plans from user requests.

    The planner takes a user request and context and generates a structured plan
    consisting of operations to be executed by the agentic system.
    """

    def __init__(self):
        self.logger = logging.getLogger("agent.planner")
        self.logger.info("Initializing PlannerComponent")
        self._ready = False
        self.llm_service: Optional[LLMService] = None

    def initialize(self) -> None:
        """Initialize the planner component."""
        self.logger.info("PlannerComponent initialized")
        try:
            self.llm_service = get_llm_service()
            self.llm_service.initialize()
        except Exception as exc:
            self.logger.info("LLM planning is unavailable; using deterministic planning: %s", exc)
            self.llm_service = None
        self._ready = True

    def is_ready(self) -> bool:
        """Check if the planner component is ready.

        Returns:
            bool: True if component is ready, False otherwise
        """
        return self._ready

    def get_component_name(self) -> str:
        """Get the component name.

        Returns:
            str: Component name
        """
        return "PlannerComponent"

    def generate_plan(self, user_request: UserRequest, request_context: RequestContext) -> AgentPlan:
        """
        Generate a structured plan from a user request and context.

        Args:
            user_request: The user request to process
            request_context: Contextual information for the request

        Returns:
            AgentPlan: Structured plan consisting of operations to execute
        """
        self.logger.info(f"Generating plan for request {user_request.request_id}")

        # Use LLM-enhanced planning if available
        if self.llm_service and self.llm_service.is_ready():
            return self._generate_llm_plan(user_request, request_context)
        else:
            # Fallback to deterministic planner
            operations = self._generate_basic_operations(user_request, request_context)

            plan = AgentPlan(
                request_id=user_request.request_id,
                operations=operations,
                reasoning="Basic deterministic plan generation (LLM unavailable)"
            )

            self.logger.info(f"Generated plan with {len(operations)} operations for request {user_request.request_id}")
            return plan

    def _generate_llm_plan(self, user_request: UserRequest, request_context: RequestContext) -> AgentPlan:
        """Generate a plan using the LLM service."""
        self.logger.info(f"Generating LLM-enhanced plan for request {user_request.request_id}")

        # Create a prompt for the LLM to generate a plan
        safe_context = request_context.model_dump(exclude={"image", "video", "user", "conversation"})
        safe_context["has_image"] = request_context.image is not None
        safe_context["has_video"] = request_context.video is not None
        prompt = f"""
        You are an AI agent that creates structured plans for plant health analysis.

        User request: {user_request.message}
        Request ID: {user_request.request_id}
        Timestamp: {user_request.timestamp}

        Context:
        {safe_context if request_context else "No additional context"}

        Available capabilities:
        - leaf_segmentation: Segments leaves from whole plant images
        - disease_classification: Classifies disease type for each leaf
        - disease_segmentation: Segments diseased regions within leaves
        - severity: Calculates disease severity metrics
        - explainability: Generates Grad-CAM visualizations for model predictions
        - video_tracking: Tracks leaves across video frames
        - plant_aggregator: Aggregates leaf-level results into plant-level assessment

        Generate a structured plan as a JSON object with the following structure:
        {{
          "request_id": "string",
          "operations": [
            {{
              "operation_id": "string",
              "capability": "string (one of the available capabilities)",
              "arguments": {{}},
              "reason": "string explaining why this operation is needed",
              "dependencies": ["list of operation_ids that must complete before this operation"],
              "context_requirements": ["list of context keys needed for this operation"]
            }}
          ],
          "reasoning": "string explaining the overall planning approach"
        }}

        Only include operations that are necessary to fulfill the user request.
        Make sure to respect dependencies (operations that need results from other operations).
        Focus on creating a logical, efficient plan that addresses the user's needs.
        """

        try:
            # Generate structured plan using LLM
            llm_response = self.llm_service.generate_structured(
                prompt=prompt,
                schema=AgentPlan,
                temperature=0.3,  # Lower temperature for more focused planning
                max_tokens=2000
            )

            self.logger.info(f"Generated LLM-enhanced plan with {len(llm_response.operations)} operations for request {user_request.request_id}")
            return llm_response
        except Exception as e:
            self.logger.warning(f"LLM planning failed: {str(e)}, falling back to deterministic planning")
            # Fallback to deterministic planner
            operations = self._generate_basic_operations(user_request, request_context)

            plan = AgentPlan(
                request_id=user_request.request_id,
                operations=operations,
                reasoning="Basic deterministic plan generation (LLM fallback)"
            )

            self.logger.info(f"Generated plan with {len(operations)} operations for request {user_request.request_id}")
            return plan

    def _generate_basic_operations(self, user_request: UserRequest, request_context: RequestContext) -> List[PlannedOperation]:
        """Generate basic operations for common request types.

        This is a simplified implementation for demonstration.
        A real implementation would use more sophisticated planning logic.
        """
        operations = []

        # Basic plant analysis request - segment leaves, then classify each leaf
        if any(keyword in user_request.message.lower() for keyword in ["analyze", "scan", "check", "disease", "health"]):
            # Leaf segmentation operation
            operations.append(PlannedOperation(
                operation_id="op_leaf_segmentation",
                capability="leaf_segmentation",
                arguments={},
                reason="Segment leaves from the whole plant image",
                context_requirements=["image"]
            ))

            # We'll add disease classification operations after segmentation results are available
            # In a real implementation, these would be dynamically added based on segmentation results
            operations.append(PlannedOperation(
                operation_id="op_disease_classification_0",
                capability="disease_classification",
                arguments={"leaf_index": 0},
                reason="Classify disease for first leaf",
                dependencies=["op_leaf_segmentation"],
                context_requirements=["image"]
            ))

            operations.append(PlannedOperation(
                operation_id="op_disease_classification_1",
                capability="disease_classification",
                arguments={"leaf_index": 1},
                reason="Classify disease for second leaf",
                dependencies=["op_leaf_segmentation"],
                context_requirements=["image"]
            ))

        # If no specific operation matched, provide a basic health check
        if not operations:
            operations.append(PlannedOperation(
                operation_id="op_basic_analysis",
                capability="plant_analysis",
                arguments={},
                reason="Perform basic plant health analysis",
                context_requirements=["image"]
            ))

        return operations
