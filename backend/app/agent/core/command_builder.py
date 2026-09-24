"""
Command Builder Component
Responsible for converting validated plans into safe internal execution commands.
"""
from typing import List, Optional, Dict, Any
import logging

from ..contracts.user_request import UserRequest
from ..contracts.request_context import RequestContext
from ..contracts.agent_plan import AgentPlan
from ..contracts.planned_operation import PlannedOperation
from ..contracts.validation_result import ValidationResult
from ..contracts.execution_command import ExecutionCommand


class CommandBuilderComponent:
    """
    Command builder component responsible for converting validated plans
    into safe internal execution commands.

    The command builder takes a validated plan and converts it into
    execution commands that can be safely executed by registered capability handlers.
    """

    def __init__(self):
        self.logger = logging.getLogger("agent.command_builder")
        self.logger.info("Initializing CommandBuilderComponent")
        self._ready = False
        # Map capability names to service methods
        self._capability_to_service_method = {
            "leaf_segmentation": "segment_leaves",
            "disease_classification": "classify_disease",
            "disease_segmentation": "segment_disease",
            "severity": "calculate_severity",
            "explainability": "generate_explanation",
            "video_tracking": "track_leaves",
            "plant_aggregator": "aggregate_leaf_results",
            "plant_analysis": "analyze_image"  # Default for plant analysis
        }

    def initialize(self) -> None:
        """Initialize the command builder component."""
        self.logger.info("CommandBuilderComponent initialized")
        self._ready = True

    def is_ready(self) -> bool:
        """Check if the command builder component is ready.

        Returns:
            bool: True if component is ready, False otherwise
        """
        return self._ready

    def get_component_name(self) -> str:
        """Get the component name.

        Returns:
            str: Component name
        """
        return "CommandBuilderComponent"

    def build_commands(self, user_request: UserRequest, request_context: RequestContext,
                      validated_plan: AgentPlan, validation_result: ValidationResult) -> List[ExecutionCommand]:
        """
        Build execution commands from a validated plan.

        Args:
            user_request: The original user request
            request_context: Contextual information for the request
            validated_plan: The validated plan to build commands for
            validation_result: The result of validation (contains normalized arguments if available)

        Returns:
            List[ExecutionCommand]: List of safe execution commands
        """
        self.logger.info(f"Building commands for request {user_request.request_id}")

        if not validation_result.valid:
            return []

        commands = []

        # Use normalized arguments from validation if available, otherwise use original plan
        operations_to_use = validated_plan.operations
        if validation_result.normalized_arguments and "operations" in validation_result.normalized_arguments:
            operations_to_use = [
                PlannedOperation.model_validate(operation)
                for operation in validation_result.normalized_arguments["operations"]
            ]

        for operation in operations_to_use:
            command = self._build_command_for_operation(
                user_request, request_context, operation
            )
            if command:
                commands.append(command)

        self.logger.info(f"Built {len(commands)} commands for request {user_request.request_id}")
        return commands

    def _build_command_for_operation(self, user_request: UserRequest,
                                   request_context: RequestContext,
                                   operation: PlannedOperation) -> Optional[ExecutionCommand]:
        """Build an execution command for a single operation.

        Args:
            user_request: The original user request
            request_context: Contextual information for the request
            operation: The operation to build a command for

        Returns:
            Optional[ExecutionCommand]: The execution command, or None if unable to build
        """
        self.logger.debug(f"Building command for operation {operation.operation_id}")

        # Validate that we can build a command for this capability
        service_method = self._capability_to_service_method.get(operation.capability)
        if not service_method:
            self.logger.warning(f"No service method mapping for capability: {operation.capability}")
            return None

        # Build the service arguments
        service_args = self._build_service_arguments(
            operation, user_request, request_context
        )

        # Create the execution command
        command = ExecutionCommand(
            command_id=f"cmd_{operation.operation_id}",
            operation_id=operation.operation_id,
            capability=operation.capability,
            service_method=service_method,
            service_args=service_args
        )

        self.logger.debug(f"Built command {command.command_id} for operation {operation.operation_id}")
        return command

    def _build_service_arguments(self, operation: PlannedOperation,
                               user_request: UserRequest,
                               request_context: RequestContext) -> Dict[str, Any]:
        """Build service arguments for an operation.

        Args:
            operation: The operation to build arguments for
            user_request: The original user request
            request_context: Contextual information for the request

        Returns:
            Dict[str, Any]: Arguments to pass to the service method
        """
        # Start with the operation's arguments
        service_args = dict(operation.arguments)

        # Add context-based arguments based on the operation's context requirements
        for context_req in operation.context_requirements:
            context_value = self._extract_context_value(context_req, user_request, request_context)
            if context_value is not None:
                # For simplicity, we're adding context values directly
                # In a real implementation, we might need to map context keys to specific argument names
                service_args[context_req] = context_value

        return service_args

    def _extract_context_value(self, context_key: str,
                             user_request: UserRequest,
                             request_context: RequestContext) -> Any:
        """Extract a value from the context based on the context key.

        Args:
            context_key: The context key to extract
            user_request: The original user request
            request_context: Contextual information for the request

        Returns:
            Any: The extracted value, or None if not found
        """
        # Map context keys to where they might be found
        if context_key == "image":
            return request_context.image
        elif context_key == "video":
            return request_context.video
        elif context_key == "user":
            return request_context.user
        elif context_key == "plant":
            return request_context.plant
        elif context_key == "scan":
            return request_context.scan
        elif context_key == "location":
            return request_context.location
        elif context_key == "conversation":
            return request_context.conversation
        elif context_key == "previous_results":
            return request_context.previous_results
        else:
            # For unknown context keys, return None
            # In a real implementation, we might want to log this or handle it differently
            return None
