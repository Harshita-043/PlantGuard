"""
Orchestrator Component
Central component that coordinates the agentic workflow.
"""
from typing import List, Optional, Dict, Any
import logging
import time

from ..contracts.user_request import UserRequest
from ..contracts.request_context import RequestContext
from ..contracts.agent_plan import AgentPlan
from ..contracts.planned_operation import PlannedOperation
from ..contracts.validation_result import ValidationResult
from ..contracts.execution_command import ExecutionCommand
from ..contracts.operation_result import OperationResult
from ..contracts.validated_result import ValidatedResult
from ..contracts.final_response import FinalResponse
from .planner import PlannerComponent
from .validator import ValidatorComponent
from .command_builder import CommandBuilderComponent
from .execution_boundary import ExecutionBoundaryComponent
from .result_validator import ResultValidatorComponent


class OrchestratorComponent:
    """
    Central orchestrator component that coordinates the agentic workflow.

    The orchestrator takes a user request and context, generates a plan,
    validates the plan, builds execution commands, executes them via registered
    handlers, validates the results, and produces a final response.
    """

    def __init__(self):
        self.logger = logging.getLogger("agent.orchestrator")
        self.logger.info("Initializing OrchestratorComponent")

        # Initialize sub-components
        self.planner = PlannerComponent()
        self.validator = ValidatorComponent()
        self.command_builder = CommandBuilderComponent()
        self.execution_boundary = ExecutionBoundaryComponent()
        self.result_validator = ResultValidatorComponent()

        self._ready = False

    def initialize(self) -> None:
        """Initialize the orchestrator and all sub-components."""
        self.logger.info("OrchestratorComponent initializing sub-components")

        self.planner.initialize()
        self.validator.initialize()
        self.command_builder.initialize()
        self.execution_boundary.initialize()
        self.result_validator.initialize()

        self.logger.info("OrchestratorComponent initialized")
        self._ready = True

    def is_ready(self) -> bool:
        """Check if the orchestrator and all sub-components are ready.

        Returns:
            bool: True if all components are ready, False otherwise
        """
        return (
            self._ready and
            self.planner.is_ready() and
            self.validator.is_ready() and
            self.command_builder.is_ready() and
            self.execution_boundary.is_ready() and
            self.result_validator.is_ready()
        )

    def get_component_name(self) -> str:
        """Get the component name.

        Returns:
            str: Component name
        """
        return "OrchestratorComponent"

    def process_request(self, user_request: UserRequest, request_context: RequestContext) -> FinalResponse:
        """
        Process a user request through the complete agentic workflow.

        Args:
            user_request: The user request to process
            request_context: Contextual information for the request

        Returns:
            FinalResponse: The final response to the user
        """
        start_time = time.time()
        self.logger.info(f"Processing request {user_request.request_id}")

        # Check if we're ready
        if not self.is_ready():
            self.logger.error("Orchestrator is not ready to process requests")
            return FinalResponse(
                request_id=user_request.request_id,
                response_id=f"resp_{int(time.time())}",
                status="failure",
                message="System is not ready to process requests",
                processing_time_ms=0,
                ml_mode="unknown"
            )

        try:
            # Step 1: Generate a plan
            self.logger.debug("Step 1: Generating plan")
            plan = self.planner.generate_plan(user_request, request_context)

            # Step 2: Validate the plan
            self.logger.debug("Step 2: Validating plan")
            validation_result = self.validator.validate_plan(user_request, request_context, plan)

            if not validation_result.valid:
                self.logger.warning(f"Plan validation failed for request {user_request.request_id}: {validation_result.errors}")
                return FinalResponse(
                    request_id=user_request.request_id,
                    response_id=f"resp_{int(time.time())}",
                    status="failure",
                    message="Request validation failed: " + "; ".join(validation_result.errors),
                    processing_time_ms=int((time.time() - start_time) * 1000),
                    ml_mode="unknown"
                )

            # Step 3: Build execution commands
            self.logger.debug("Step 3: Building execution commands")
            commands = self.command_builder.build_commands(
                user_request, request_context, plan, validation_result
            )

            if not commands:
                self.logger.warning(f"No commands built for request {user_request.request_id}")
                return FinalResponse(
                    request_id=user_request.request_id,
                    response_id=f"resp_{int(time.time())}",
                    status="failure",
                    message="Unable to build execution commands from plan",
                    processing_time_ms=int((time.time() - start_time) * 1000),
                    ml_mode="unknown"
                )

            # Step 4: Execute commands
            self.logger.debug("Step 4: Executing commands")
            operation_results: List[OperationResult] = []
            validated_results: List[ValidatedResult] = []

            for command in commands:
                # Execute the command
                operation_result = self.execution_boundary.execute_command(command)
                operation_results.append(operation_result)

                # Validate the result
                validated_result = self.result_validator.validate_result(operation_result)
                validated_results.append(validated_result)

                # If a critical operation fails, we might want to stop early
                # For now, we'll continue to execute all commands

            # Step 5: Build final response
            self.logger.debug("Step 5: Building final response")
            final_response = self._build_final_response(
                user_request, request_context, plan, operation_results, validated_results, start_time
            )

            end_time = time.time()
            processing_time_ms = int((end_time - start_time) * 1000)
            final_response.processing_time_ms = processing_time_ms

            self.logger.info(f"Request {user_request.request_id} processed successfully in {processing_time_ms}ms")
            return final_response

        except Exception as e:
            self.logger.error(f"Error processing request {user_request.request_id}: {str(e)}")
            end_time = time.time()
            processing_time_ms = int((end_time - start_time) * 1000)
            return FinalResponse(
                request_id=user_request.request_id,
                response_id=f"resp_{int(time.time())}",
                status="failure",
                message=f"Internal processing error: {str(e)}",
                processing_time_ms=processing_time_ms,
                ml_mode="unknown"
            )

    def _build_final_response(self, user_request: UserRequest, request_context: RequestContext,
                            plan: AgentPlan, operation_results: List[OperationResult],
                            validated_results: List[ValidatedResult], start_time: float) -> FinalResponse:
        """Build the final response from the processing results.

        Args:
            user_request: The original user request
            request_context: Contextual information for the request
            plan: The plan that was executed
            operation_results: List of operation results
            validated_results: List of validated operation results
            start_time: The start time of processing

        Returns:
            FinalResponse: The final response to the user
        """
        # Count successful and failed operations
        validated_operations = [r for r in validated_results if r.validated]
        successful_operations = [
            result
            for result, validated in zip(operation_results, validated_results)
            if result.success and validated.validated
        ]
        failed_operations = [
            result
            for result, validated in zip(operation_results, validated_results)
            if not result.success or not validated.validated
        ]

        # Determine overall status
        if len(failed_operations) == 0:
            status = "success"
        elif len(successful_operations) == 0:
            status = "failure"
        else:
            status = "partial_success"

        # Build a human-readable message
        if status == "success":
            message = "Analysis completed successfully"
        elif status == "partial_success":
            message = f"Analysis partially completed: {len(successful_operations)} succeeded, {len(failed_operations)} failed"
        else:
            message = "Analysis failed"

        # Build the data section from validated results
        data = {}
        if validated_results:
            # For now, we'll just include the validated results
            # In a real implementation, we would synthesize these into a coherent response
            data["validated_results"] = [vr.dict() for vr in validated_results]

            # Try to extract meaningful information for a better response
            # This would be enhanced in later phases with domain-specific synthesis
            if any(vr.validated and vr.validated_data for vr in validated_results):
                data["analysis_completed"] = True
                data["operations_processed"] = len(validated_results)

        # Build suggestions
        suggestions = []
        if status == "success":
            suggestions = [
                "Would you like to save this analysis to your plant's history?",
                "Should I set a reminder to check progress in a week?"
            ]
        elif status == "partial_success":
            suggestions = [
                "Would you like to retry the failed operations?",
                "Can I help you with anything else regarding your plant's health?"
            ]
        else:
            suggestions = [
                "Please try again with a clearer description of the issue",
                "Would you like to upload a different image?"
            ]

        # Determine ML mode (this would come from configuration in a real implementation)
        ml_mode = "not_integrated"

        return FinalResponse(
            request_id=user_request.request_id,
            response_id=f"resp_{int(time.time())}",
            status=status,
            message=message,
            data=data if data else None,
            suggestions=suggestions if suggestions else None,
            processing_time_ms=0,  # Will be set by the caller
            ml_mode=ml_mode
        )
