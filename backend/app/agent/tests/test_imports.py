"""
Test that all agentic components can be imported correctly.
"""
def test_imports():
    """Test that all components can be imported."""
    from app.agent.service import AgentService
    from app.agent.core.orchestrator import OrchestratorComponent
    from app.agent.core.planner import PlannerComponent
    from app.agent.core.validator import ValidatorComponent
    from app.agent.core.command_builder import CommandBuilderComponent
    from app.agent.core.execution_boundary import ExecutionBoundaryComponent
    from app.agent.core.result_validator import ResultValidatorComponent
    from app.agent.contracts.user_request import UserRequest
    from app.agent.contracts.request_context import RequestContext
    from app.agent.contracts.agent_plan import AgentPlan
    from app.agent.contracts.planned_operation import PlannedOperation
    from app.agent.contracts.validation_result import ValidationResult
    from app.agent.contracts.execution_command import ExecutionCommand
    from app.agent.contracts.operation_result import OperationResult
    from app.agent.contracts.validated_result import ValidatedResult
    from app.agent.contracts.final_response import FinalResponse

    assert True  # If we got here, all imports worked

if __name__ == "__main__":
    test_imports()
    print("All imports successful!")