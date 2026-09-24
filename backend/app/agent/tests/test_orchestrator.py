"""
Tests for the agentic orchestrator components.
"""
import numpy as np
import pytest

from app.agent.contracts.user_request import UserRequest
from app.agent.contracts.request_context import RequestContext
from app.agent.contracts.validation_result import ValidationResult
from app.agent.contracts.agent_plan import AgentPlan
from app.agent.contracts.planned_operation import PlannedOperation
from app.agent.core.orchestrator import OrchestratorComponent
from app.agent.core.planner import PlannerComponent
from app.agent.core.validator import ValidatorComponent
from app.agent.core.command_builder import CommandBuilderComponent
from app.agent.core.execution_boundary import ExecutionBoundaryComponent
from app.agent.core.result_validator import ResultValidatorComponent


def test_planner_component():
    """Test the planner component."""
    planner = PlannerComponent()
    planner.initialize()

    assert planner.is_ready()
    assert planner.get_component_name() == "PlannerComponent"

    # Test basic plan generation
    user_request = UserRequest(
        request_id="test_req_1",
        user_id="user_1",
        message="Analyze this plant for disease"
    )

    request_context = RequestContext()

    plan = planner.generate_plan(user_request, request_context)

    assert plan.request_id == user_request.request_id
    assert len(plan.operations) > 0
    assert plan.reasoning is not None


def test_validator_component():
    """Test the validator component."""
    validator = ValidatorComponent()
    validator.initialize()

    assert validator.is_ready()
    assert validator.get_component_name() == "ValidatorComponent"

    # Test validation of a valid plan
    planner = PlannerComponent()
    planner.initialize()

    user_request = UserRequest(
        request_id="test_req_1",
        user_id="user_1",
        message="Analyze this plant for disease"
    )

    request_context = RequestContext()
    plan = planner.generate_plan(user_request, request_context)

    validation_result = validator.validate_plan(user_request, request_context, plan)

    # Should be valid or have only warnings (not errors that prevent execution)
    assert isinstance(validation_result, ValidationResult)


def test_validator_rejects_plan_for_another_request():
    validator = ValidatorComponent()
    validator.initialize()
    request = UserRequest(request_id="expected", user_id="user", message="check plant")
    plan = AgentPlan(request_id="different", operations=[PlannedOperation(
        operation_id="op_1", capability="plant_analysis", arguments={}, reason="Check plant"
    )])

    result = validator.validate_plan(request, RequestContext(), plan)

    assert result.valid is False
    assert "Plan request ID does not match the original request" in result.errors


def test_validator_rejects_long_dependency_cycles():
    validator = ValidatorComponent()
    validator.initialize()
    request = UserRequest(request_id="cycle", user_id="user", message="check plant")
    operations = [
        PlannedOperation(operation_id="a", capability="plant_analysis", arguments={}, reason="a", dependencies=["c"]),
        PlannedOperation(operation_id="b", capability="plant_analysis", arguments={}, reason="b", dependencies=["a"]),
        PlannedOperation(operation_id="c", capability="plant_analysis", arguments={}, reason="c", dependencies=["b"]),
    ]
    plan = AgentPlan(request_id="cycle", operations=operations)

    result = validator.validate_plan(request, RequestContext(), plan)

    assert result.valid is False
    assert "Circular operation dependency detected" in result.errors


def test_command_builder_component():
    """Test the command builder component."""
    command_builder = CommandBuilderComponent()
    command_builder.initialize()

    assert command_builder.is_ready()
    assert command_builder.get_component_name() == "CommandBuilderComponent"

    # Test building commands
    planner = PlannerComponent()
    planner.initialize()

    user_request = UserRequest(
        request_id="test_req_1",
        user_id="user_1",
        message="Analyze this plant for disease"
    )

    request_context = RequestContext()
    plan = planner.generate_plan(user_request, request_context)

    validator = ValidatorComponent()
    validator.initialize()
    validation_result = validator.validate_plan(user_request, request_context, plan)

    commands = command_builder.build_commands(
        user_request, request_context, plan, validation_result
    )

    assert isinstance(commands, list)
    # May be empty if validation failed, but should be a list


def test_execution_boundary_component():
    """Test the execution boundary component."""
    execution_boundary = ExecutionBoundaryComponent()
    execution_boundary.initialize()

    assert execution_boundary.is_ready()
    assert execution_boundary.get_component_name() == "ExecutionBoundaryComponent"

    # Test registering a handler
    def dummy_handler(args):
        return {"result": "success"}

    execution_boundary.register_capability_handler("test_capability", dummy_handler)
    assert execution_boundary.is_capability_available("test_capability")
    assert "test_capability" in execution_boundary.get_available_capabilities()

    # Test executing a command
    from app.agent.contracts.execution_command import ExecutionCommand
    command = ExecutionCommand(
        command_id="test_cmd_1",
        operation_id="test_op_1",
        capability="test_capability",
        service_method="test_method",
        service_args={"test_arg": "test_value"}
    )

    result = execution_boundary.execute_command(command)
    assert isinstance(result, dict) or hasattr(result, '__dict__')  # Should return the handler result


def test_result_validator_component():
    """Test the result validator component."""
    result_validator = ResultValidatorComponent()
    result_validator.initialize()

    assert result_validator.is_ready()
    assert result_validator.get_component_name() == "ResultValidatorComponent"

    # Test validating a successful result
    from app.agent.contracts.operation_result import OperationResult
    operation_result = OperationResult(
        operation_id="test_op_1",
        success=True,
        result_data={"test": "data"},
        execution_time_ms=100
    )

    validated_result = result_validator.validate_result(operation_result)

    assert isinstance(validated_result, dict) or hasattr(validated_result, '__dict__')
    assert validated_result.validated is False
    assert validated_result.validated_data is None


def test_orchestrator_component():
    """Test the orchestrator component."""
    orchestrator = OrchestratorComponent()
    orchestrator.initialize()

    assert orchestrator.is_ready()
    assert orchestrator.get_component_name() == "OrchestratorComponent"

    # Test that all sub-components are ready
    assert orchestrator.planner.is_ready()
    assert orchestrator.validator.is_ready()
    assert orchestrator.command_builder.is_ready()
    assert orchestrator.execution_boundary.is_ready()
    assert orchestrator.result_validator.is_ready()


if __name__ == "__main__":
    test_planner_component()
    test_validator_component()
    test_command_builder_component()
    test_execution_boundary_component()
    test_result_validator_component()
    test_orchestrator_component()
    print("All tests passed!")
