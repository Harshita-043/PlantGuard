"""
Result Validator Component
Responsible for validating operation results before they become trusted final responses.
"""
from typing import List, Optional, Dict, Any
import logging

from ..contracts.operation_result import OperationResult
from ..contracts.validated_result import ValidatedResult


class ResultValidatorComponent:
    """
    Result validator component responsible for validating operation results.

    No capability-specific schemas are currently registered, so successful handler
    output is rejected instead of being treated as trusted result data.
    """

    def __init__(self):
        self.logger = logging.getLogger("agent.result_validator")
        self.logger.info("Initializing ResultValidatorComponent")
        self._ready = False

    def initialize(self) -> None:
        """Initialize the result validator component."""
        self.logger.info("ResultValidatorComponent initialized")
        self._ready = True

    def is_ready(self) -> bool:
        """Check if the result validator component is ready.

        Returns:
            bool: True if component is ready, False otherwise
        """
        return self._ready

    def get_component_name(self) -> str:
        """Get the component name.

        Returns:
            str: Component name
        """
        return "ResultValidatorComponent"

    def validate_result(self, operation_result: OperationResult) -> ValidatedResult:
        """
        Validate an operation result.

        Args:
            operation_result: The operation result to validate

        Returns:
            ValidatedResult: The validated result
        """
        self.logger.debug(f"Validating result for operation {operation_result.operation_id}")

        validation_errors = []
        validation_warnings = []
        validated_data = None

        # Check if the operation was successful
        if not operation_result.success:
            validation_errors.append(f"Operation failed: {operation_result.error_message}")
            return ValidatedResult(
                operation_id=operation_result.operation_id,
                validated=False,
                validated_data=None,
                validation_errors=validation_errors,
                validation_warnings=validation_warnings,
                original_result=operation_result
            )

        if operation_result.result_data is None:
            validation_errors.append("Operation returned no result data")
        else:
            validation_errors.append("No result schema is registered; result data is not trusted")

        # Determine if the result is valid overall
        validated = False

        self.logger.debug(f"Result validation completed for operation {operation_result.operation_id}: validated={validated}")

        return ValidatedResult(
            operation_id=operation_result.operation_id,
            validated=validated,
            validated_data=validated_data,
            validation_errors=validation_errors,
            validation_warnings=validation_warnings,
            original_result=operation_result
        )
