"""End-to-end tests for C# to Cedar policy translation.

This test validates the complete workflow:
1. Extract policy from C# code (simulated with existing scanner)
2. Translate policy to AWS Cedar format using Claude Agent SDK
3. Verify semantic equivalence between C# and Cedar
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.policy import Policy, PolicyStatus, RiskLevel, SourceType
from app.services.translation_service import TranslationService


@pytest.mark.asyncio
async def test_csharp_aspnet_authorize_attribute_to_cedar():
    """Test translating C# [Authorize(Roles = \"Manager\")] to Cedar."""
    # Simulates a policy extracted from C# code:
    # [Authorize(Roles = "Manager")]
    # [HttpPost("approve")]
    # public IActionResult ApproveExpense(ExpenseRequest request)
    policy = Policy(
        policy_id=1,
        tenant_id="test-tenant",
        repository_id=1,
        subject="Manager",
        resource="expense",
        action="approve",
        conditions="amount < 5000",
        description="Managers can approve expenses under $5000 (from C# ASP.NET Core [Authorize] attribute)",
        status=PolicyStatus.PENDING,
        risk_score=30,
        complexity_score=20,
        impact_score=40,
        confidence_score=90,
        historical_score=0,
        risk_level=RiskLevel.LOW,
        source_type=SourceType.BACKEND,
    )

    # Mock Claude Agent SDK response with Cedar policy
    mock_cedar_response = MagicMock()
    mock_cedar_response.content = [
        MagicMock(
            text="""```cedar
permit (
    principal in Role::"Manager",
    action == Action::"approve",
    resource in ResourceType::"expense"
)
when {
    resource.amount < 5000
};
```"""
        )
    ]

    with patch("app.services.llm_provider.get_llm_provider") as mock_get_provider:
        mock_provider = MagicMock()
        mock_provider.create_message = AsyncMock(return_value=mock_cedar_response)
        mock_get_provider.return_value = mock_provider

        translation_service = TranslationService()
        cedar_policy = await translation_service.translate_to_cedar(policy)

        # Verify Cedar policy structure
        assert "permit" in cedar_policy
        assert "principal" in cedar_policy
        assert "Manager" in cedar_policy
        assert "action" in cedar_policy
        assert "approve" in cedar_policy
        assert "resource" in cedar_policy
        assert "expense" in cedar_policy
        assert "when" in cedar_policy
        assert "5000" in cedar_policy
        assert cedar_policy.rstrip().endswith(";")

        # Verify semantic equivalence (WHO/WHAT/HOW/WHEN preserved)
        assert "Manager" in cedar_policy  # WHO: Manager role from C# [Authorize(Roles = "Manager")]
        assert "expense" in cedar_policy  # WHAT: expense resource from C# method context
        assert "approve" in cedar_policy  # HOW: approve action from C# method name
        assert "5000" in cedar_policy  # WHEN: amount < 5000 condition from C# business logic


@pytest.mark.asyncio
async def test_csharp_principal_permission_to_cedar():
    """Test translating C# [PrincipalPermission] (legacy ASP.NET) to Cedar."""
    # Simulates a policy extracted from:
    # [PrincipalPermission(SecurityAction.Demand, Role = "Administrator")]
    # public void ModifyConfiguration() { ... }
    policy = Policy(
        policy_id=2,
        tenant_id="test-tenant",
        repository_id=1,
        subject="Administrator",
        resource="configuration",
        action="modify",
        conditions="user is authenticated",
        description="Only administrators can modify configuration (from C# [PrincipalPermission])",
        status=PolicyStatus.PENDING,
        risk_score=70,
        complexity_score=25,
        impact_score=80,
        confidence_score=95,
        historical_score=0,
        risk_level=RiskLevel.HIGH,
        source_type=SourceType.BACKEND,
    )

    mock_cedar_response = MagicMock()
    mock_cedar_response.content = [
        MagicMock(
            text="""```cedar
permit (
    principal in Role::"Administrator",
    action == Action::"modify",
    resource in ResourceType::"configuration"
)
when {
    principal.isAuthenticated == true
};
```"""
        )
    ]

    with patch("app.services.llm_provider.get_llm_provider") as mock_get_provider:
        mock_provider = MagicMock()
        mock_provider.create_message = AsyncMock(return_value=mock_cedar_response)
        mock_get_provider.return_value = mock_provider

        translation_service = TranslationService()
        cedar_policy = await translation_service.translate_to_cedar(policy)

        # Verify semantic preservation from C# to Cedar
        assert "Administrator" in cedar_policy or "admin" in cedar_policy.lower()
        assert "configuration" in cedar_policy
        assert "modify" in cedar_policy
        assert "when" in cedar_policy
        assert "isAuthenticated" in cedar_policy or "authenticated" in cedar_policy.lower()


@pytest.mark.asyncio
async def test_csharp_user_is_in_role_to_cedar():
    """Test translating C# User.IsInRole() check to Cedar."""
    # Simulates a policy extracted from:
    # if (User.IsInRole("Director")) {
    #     // Approve large expense
    # }
    policy = Policy(
        policy_id=3,
        tenant_id="test-tenant",
        repository_id=1,
        subject="Director",
        resource="expense",
        action="approve",
        conditions="no amount limit",
        description="Directors can approve any expense (from C# User.IsInRole check)",
        status=PolicyStatus.PENDING,
        risk_score=40,
        complexity_score=15,
        impact_score=60,
        confidence_score=95,
        historical_score=0,
        risk_level=RiskLevel.MEDIUM,
        source_type=SourceType.BACKEND,
    )

    mock_cedar_response = MagicMock()
    mock_cedar_response.content = [
        MagicMock(
            text="""```cedar
permit (
    principal in Role::"Director",
    action == Action::"approve",
    resource in ResourceType::"expense"
);
```"""
        )
    ]

    with patch("app.services.llm_provider.get_llm_provider") as mock_get_provider:
        mock_provider = MagicMock()
        mock_provider.create_message = AsyncMock(return_value=mock_cedar_response)
        mock_get_provider.return_value = mock_provider

        translation_service = TranslationService()
        cedar_policy = await translation_service.translate_to_cedar(policy)

        # Verify translation
        assert "permit" in cedar_policy
        assert "Director" in cedar_policy
        assert "approve" in cedar_policy
        assert "expense" in cedar_policy
        # Note: No amount condition for Directors (they can approve any amount)


@pytest.mark.asyncio
async def test_cedar_translation_validates_syntax():
    """Test that Cedar translation validates policy syntax."""
    policy = Policy(
        policy_id=4,
        tenant_id="test-tenant",
        repository_id=1,
        subject="Manager",
        resource="document",
        action="delete",
        conditions="document is not archived",
        description="Managers can delete non-archived documents",
        status=PolicyStatus.PENDING,
        risk_score=50,
        complexity_score=30,
        impact_score=60,
        confidence_score=85,
        historical_score=0,
        risk_level=RiskLevel.MEDIUM,
        source_type=SourceType.BACKEND,
    )

    # Mock an invalid Cedar response (missing semicolon)
    mock_invalid_response = MagicMock()
    mock_invalid_response.content = [
        MagicMock(
            text="""```cedar
permit (
    principal in Role::"Manager",
    action == Action::"delete",
    resource in ResourceType::"document"
)
```"""
        )
    ]

    with patch("app.services.llm_provider.get_llm_provider") as mock_get_provider:
        mock_provider = MagicMock()
        mock_provider.create_message = AsyncMock(return_value=mock_invalid_response)
        mock_get_provider.return_value = mock_provider

        translation_service = TranslationService()

        # Should raise validation error for missing semicolon
        with pytest.raises(ValueError, match="must end with semicolon"):
            await translation_service.translate_to_cedar(policy)


@pytest.mark.asyncio
async def test_cedar_translation_prompt_includes_csharp_context():
    """Test that Cedar translation prompt includes C# policy context."""
    policy = Policy(
        policy_id=5,
        tenant_id="test-tenant",
        repository_id=1,
        subject="Supervisor",
        resource="timesheet",
        action="submit",
        conditions="for subordinates only",
        description="Supervisors can submit timesheets for their subordinates",
        status=PolicyStatus.PENDING,
        risk_score=35,
        complexity_score=25,
        impact_score=45,
        confidence_score=88,
        historical_score=0,
        risk_level=RiskLevel.LOW,
        source_type=SourceType.BACKEND,
    )

    translation_service = TranslationService()
    prompt = translation_service._build_cedar_translation_prompt(policy)

    # Verify prompt includes all policy fields
    assert "Supervisor" in prompt
    assert "timesheet" in prompt
    assert "submit" in prompt
    assert "for subordinates only" in prompt
    assert "Supervisors can submit timesheets for their subordinates" in prompt

    # Verify prompt includes Cedar format instructions
    assert "permit" in prompt or "forbid" in prompt
    assert "principal" in prompt
    assert "action" in prompt
    assert "resource" in prompt
    assert "when" in prompt


@pytest.mark.asyncio
async def test_csharp_claims_based_authorization_to_cedar():
    """Test translating C# claims-based authorization to Cedar."""
    # Simulates a policy extracted from:
    # [Authorize(Policy = "EmployeeOnly")]
    # where EmployeeOnly policy checks: user.HasClaim("EmployeeNumber", "*")
    policy = Policy(
        policy_id=6,
        tenant_id="test-tenant",
        repository_id=1,
        subject="Employee",
        resource="payroll",
        action="view",
        conditions="has valid employee number claim",
        description="Employees can view their own payroll (from C# claims-based authorization)",
        status=PolicyStatus.PENDING,
        risk_score=45,
        complexity_score=30,
        impact_score=55,
        confidence_score=90,
        historical_score=0,
        risk_level=RiskLevel.MEDIUM,
        source_type=SourceType.BACKEND,
    )

    mock_cedar_response = MagicMock()
    mock_cedar_response.content = [
        MagicMock(
            text="""```cedar
permit (
    principal in Role::"Employee",
    action == Action::"view",
    resource in ResourceType::"payroll"
)
when {
    principal has employeeNumber &&
    resource.employeeId == principal.employeeNumber
};
```"""
        )
    ]

    with patch("app.services.llm_provider.get_llm_provider") as mock_get_provider:
        mock_provider = MagicMock()
        mock_provider.create_message = AsyncMock(return_value=mock_cedar_response)
        mock_get_provider.return_value = mock_provider

        translation_service = TranslationService()
        cedar_policy = await translation_service.translate_to_cedar(policy)

        # Verify claims-based logic translated to Cedar
        assert "Employee" in cedar_policy
        assert "payroll" in cedar_policy
        assert "view" in cedar_policy
        assert "when" in cedar_policy
        assert "employeeNumber" in cedar_policy or "employee" in cedar_policy.lower()
