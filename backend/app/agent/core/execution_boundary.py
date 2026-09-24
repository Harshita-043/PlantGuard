"""
Execution Boundary Component
Defines the boundary between the orchestrator and registered capability handlers.
"""
from typing import List, Optional, Dict, Any, Callable
import logging

from ..contracts.user_request import UserRequest
from ..contracts.request_context import RequestContext
from ..contracts.execution_command import ExecutionCommand
from ..contracts.operation_result import OperationResult


class ExecutionBoundaryComponent:
    """
    Execution boundary component responsible for executing commands via registered handlers.

    This component does not know how to execute specific capabilities - it only knows
    how to route execution commands to registered handlers. The actual capability
    implementations will be registered separately (in Phase 6 with the Capability Registry).
    """

    def __init__(self):
        self.logger = logging.getLogger("agent.execution_boundary")
        self.logger.info("Initializing ExecutionBoundaryComponent")
        self._ready = False
        # Registry of capability handlers
        # In a real implementation, this would be populated by the Capability Registry
        self._capability_handlers: Dict[str, Callable] = {}

    def initialize(self) -> None:
        """Initialize the execution boundary component."""
        self.logger.info("ExecutionBoundaryComponent initialized")
        self._ready = True

    def is_ready(self) -> bool:
        """Check if the execution boundary component is ready.

        Returns:
            bool: True if component is ready, False otherwise
        """
        return self._ready

    def get_component_name(self) -> str:
        """Get the component name.

        Returns:
            str: Component name
        """
        return "ExecutionBoundaryComponent"

    def register_capability_handler(self, capability: str, handler: Callable) -> None:
        """Register a handler for a specific capability.

        Args:
            capability: The capability name (e.g., "leaf_segmentation")
            handler: A callable that can execute the capability
        """
        self.logger.info(f"Registering handler for capability: {capability}")
        self._capability_handlers[capability] = handler

    def unregister_capability_handler(self, capability: str) -> None:
        """Unregister a handler for a specific capability.

        Args:
            capability: The capability name to unregister
        """
        if capability in self._capability_handlers:
            self.logger.info(f"Unregistering handler for capability: {capability}")
            del self._capability_handlers[capability]

    def execute_command(self, command: ExecutionCommand) -> OperationResult:
        """Execute a command using the registered handler.

        Args:
            command: The execution command to execute

        Returns:
            OperationResult: The result of the execution
        """
        self.logger.info(f"Executing command {command.command_id} for capability {command.capability}")

        # Check if we have a handler for this capability
        if command.capability not in self._capability_handlers:
            error_msg = f"No handler registered for capability: {command.capability}"
            self.logger.error(error_msg)
            return OperationResult(
                operation_id=command.operation_id,
                success=False,
                error_message=error_msg,
                execution_time_ms=0
            )

        # Get the handler and execute it
        handler = self._capability_handlers[command.capability]

        try:
            import time
            start_time = time.time()

            # Execute the handler with the service arguments
            # The handler should accept the service_args and return the result data
            result_data = handler(command.service_args)

            end_time = time.time()
            execution_time_ms = int((end_time - start_time) * 1000)

            self.logger.info(f"Command {command.command_id} executed successfully in {execution_time_ms}ms")

            return OperationResult(
                operation_id=command.operation_id,
                success=True,
                result_data=result_data,
                execution_time_ms=execution_time_ms
            )

        except Exception as e:
            self.logger.error(f"Error executing command {command.command_id}: {str(e)}")
            return OperationResult(
                operation_id=command.operation_id,
                success=False,
                error_message=str(e),
                execution_time_ms=0
            )

    def is_capability_available(self, capability: str) -> bool:
        """Check if a capability is available (has a registered handler).

        Args:
            capability: The capability name to check

        Returns:
            bool: True if the capability has a registered handler, False otherwise
        """
        return capability in self._capability_handlers

    def get_available_capabilities(self) -> List[str]:
        """Get a list of available capabilities.

        Returns:
            List[str]: List of capability names that have registered handlers
        """
        return list(self._capability_handlers.keys())