"""Tests for PolicyFixingService."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from app.models.policy import Policy
from app.models.policy_fix import FixSeverity, FixStatus, PolicyFix
from app.services.policy_fixing_service import PolicyFixingService


@pytest.fixture
def mock_db():
    """Mock database session."""
    return MagicMock(spec=Session)


@pytest.fixture
def mock_policy():
    """Mock policy for testing."""
    policy = MagicMock(spec=Policy)
    policy.id = 1
    policy.subject = "Manager"
    policy.resource = "Expense Report"
    policy.action = "approve"
    policy.conditions = "None"
    policy.description = "Managers can approve expense reports"
    policy.evidence = []
    return policy


@pytest.fixture
def mock_llm_provider():
    """Mock LLM provider."""
    provider = AsyncMock()
    return provider


class TestPolicyFixingService:
    """Tests for PolicyFixingService."""

    @pytest.mark.asyncio
    async def test_analyze_policy_no_gaps(self, mock_db, mock_policy):
        """Test analyzing policy with no security gaps."""
        # Setup
        mock_db.query.return_value.filter.return_value.first.return_value = mock_policy

        service = PolicyFixingService(mock_db, "test-tenant")

        # Mock LLM response - no gaps
        with patch.object(service, "_analyze_policy_with_ai") as mock_analyze:
            mock_analyze.return_value = {"has_gaps": False}

            # Execute
            result = await service.analyze_policy(1)

            # Assert
            assert result is None
            mock_analyze.assert_called_once_with(mock_policy)

    @pytest.mark.asyncio
    async def test_analyze_policy_with_gaps(self, mock_db, mock_policy):
        """Test analyzing policy with security gaps."""
        # Setup
        mock_db.query.return_value.filter.return_value.first.return_value = mock_policy

        service = PolicyFixingService(mock_db, "test-tenant")

        # Mock LLM response - gaps found
        analysis_result = {
            "has_gaps": True,
            "gap_type": "incomplete_logic",
            "severity": "high",
            "gap_description": "Missing user suspension check",
            "missing_checks": ["Check user suspension status", "Verify approval limits"],
            "fixed_policy": {
                "subject": "Manager (active, not suspended)",
                "resource": "Expense Report",
                "action": "approve",
                "conditions": "amount < manager.approvalLimit AND user.status == 'active'",
            },
            "fix_explanation": "Added suspension check and approval limits",
        }

        with patch.object(service, "_analyze_policy_with_ai") as mock_analyze:
            mock_analyze.return_value = analysis_result

            # Execute
            result = await service.analyze_policy(1)

            # Assert
            assert result is not None
            assert isinstance(result, PolicyFix)
            assert result.security_gap_type == "incomplete_logic"
            assert result.severity == FixSeverity.HIGH
            assert result.status == FixStatus.PENDING
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_policy_not_found(self, mock_db):
        """Test analyzing non-existent policy."""
        # Setup
        mock_db.query.return_value.filter.return_value.first.return_value = None

        service = PolicyFixingService(mock_db, "test-tenant")

        # Execute & Assert
        with pytest.raises(ValueError, match="Policy 999 not found"):
            await service.analyze_policy(999)

    @pytest.mark.asyncio
    async def test_analyze_policy_with_ai_parses_json(self, mock_db, mock_policy):
        """Test that AI analysis correctly parses JSON response."""
        # Setup
        service = PolicyFixingService(mock_db, "test-tenant")

        llm_response = """
        Here is the analysis:
        {
          "has_gaps": true,
          "gap_type": "privilege_escalation",
          "severity": "critical",
          "gap_description": "Missing role check allows any user to approve",
          "missing_checks": ["Verify user has manager role"],
          "fixed_policy": {
            "subject": "Manager with manager role",
            "resource": "Expense Report",
            "action": "approve",
            "conditions": "user.role == 'manager' AND user.status == 'active'"
          },
          "fix_explanation": "Added role verification to prevent privilege escalation"
        }
        Some additional text
        """

        with patch.object(service, "llm_provider") as mock_llm:
            mock_llm.create_message = AsyncMock(return_value=llm_response)

            # Execute
            result = await service._analyze_policy_with_ai(mock_policy)

            # Assert
            assert result["has_gaps"] is True
            assert result["gap_type"] == "privilege_escalation"
            assert result["severity"] == "critical"
            assert "Missing role check" in result["gap_description"]
            assert len(result["missing_checks"]) == 1

    @pytest.mark.asyncio
    async def test_analyze_policy_with_ai_invalid_json(self, mock_db, mock_policy):
        """Test that invalid JSON returns has_gaps=false."""
        # Setup
        service = PolicyFixingService(mock_db, "test-tenant")

        llm_response = "This is not valid JSON at all"

        with patch.object(service, "llm_provider") as mock_llm:
            mock_llm.create_message = AsyncMock(return_value=llm_response)

            # Execute
            result = await service._analyze_policy_with_ai(mock_policy)

            # Assert
            assert result["has_gaps"] is False

    @pytest.mark.asyncio
    async def test_generate_test_cases(self, mock_db):
        """Test generating test cases for a fix."""
        # Setup
        policy_fix = PolicyFix(
            id=1,
            policy_id=1,
            tenant_id="test-tenant",
            security_gap_type="incomplete_logic",
            severity=FixSeverity.HIGH,
            gap_description="Missing checks",
            missing_checks='["Check 1", "Check 2"]',
            original_policy='{"subject": "Manager", "action": "approve"}',
            fixed_policy='{"subject": "Manager (active)", "action": "approve"}',
            fix_explanation="Added checks",
            status=FixStatus.PENDING,
        )

        mock_db.query.return_value.filter.return_value.first.return_value = policy_fix

        service = PolicyFixingService(mock_db, "test-tenant")

        test_cases_json = json.dumps(
            [
                {
                    "name": "Allow authorized manager",
                    "scenario": "Active manager approving expense",
                    "input": {"user": {"role": "manager", "status": "active"}},
                    "expected_original": "ALLOWED",
                    "expected_fixed": "ALLOWED",
                    "reasoning": "Legitimate case",
                },
                {
                    "name": "Block suspended manager",
                    "scenario": "Suspended manager attempting approval",
                    "input": {"user": {"role": "manager", "status": "suspended"}},
                    "expected_original": "ALLOWED",
                    "expected_fixed": "DENIED",
                    "reasoning": "Fix prevents suspended users",
                },
            ]
        )

        with patch.object(service, "_generate_test_cases_ai") as mock_generate:
            mock_generate.return_value = test_cases_json

            # Execute
            result = await service.generate_test_cases(1)

            # Assert
            assert result == policy_fix
            assert result.test_cases == test_cases_json
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_test_cases_fix_not_found(self, mock_db):
        """Test generating test cases for non-existent fix."""
        # Setup
        mock_db.query.return_value.filter.return_value.first.return_value = None

        service = PolicyFixingService(mock_db, "test-tenant")

        # Execute & Assert
        with pytest.raises(ValueError, match="PolicyFix 999 not found"):
            await service.generate_test_cases(999)

    def test_get_fix(self, mock_db):
        """Test getting a fix by ID."""
        # Setup
        policy_fix = PolicyFix(
            id=1,
            policy_id=1,
            tenant_id="test-tenant",
            security_gap_type="incomplete_logic",
            severity=FixSeverity.MEDIUM,
            gap_description="Test",
            missing_checks="[]",
            original_policy="{}",
            fixed_policy="{}",
            fix_explanation="Test",
            status=FixStatus.PENDING,
        )

        mock_db.query.return_value.filter.return_value.filter.return_value.first.return_value = policy_fix

        service = PolicyFixingService(mock_db, "test-tenant")

        # Execute
        result = service.get_fix(1)

        # Assert
        assert result == policy_fix

    def test_list_fixes_with_filters(self, mock_db):
        """Test listing fixes with filters."""
        # Setup
        fixes = [
            PolicyFix(
                id=1,
                policy_id=1,
                tenant_id="test-tenant",
                security_gap_type="incomplete_logic",
                severity=FixSeverity.HIGH,
                gap_description="Test 1",
                missing_checks="[]",
                original_policy="{}",
                fixed_policy="{}",
                fix_explanation="Test",
                status=FixStatus.PENDING,
            ),
            PolicyFix(
                id=2,
                policy_id=2,
                tenant_id="test-tenant",
                security_gap_type="privilege_escalation",
                severity=FixSeverity.CRITICAL,
                gap_description="Test 2",
                missing_checks="[]",
                original_policy="{}",
                fixed_policy="{}",
                fix_explanation="Test",
                status=FixStatus.REVIEWED,
            ),
        ]

        mock_query = mock_db.query.return_value
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value.all.return_value = fixes

        service = PolicyFixingService(mock_db, "test-tenant")

        # Execute
        result = service.list_fixes(policy_id=1, status=FixStatus.PENDING, severity=FixSeverity.HIGH)

        # Assert
        assert len(result) == 2
        mock_db.query.assert_called_once()

    def test_update_fix_status(self, mock_db):
        """Test updating fix status."""
        # Setup
        policy_fix = PolicyFix(
            id=1,
            policy_id=1,
            tenant_id="test-tenant",
            security_gap_type="incomplete_logic",
            severity=FixSeverity.MEDIUM,
            gap_description="Test",
            missing_checks="[]",
            original_policy="{}",
            fixed_policy="{}",
            fix_explanation="Test",
            status=FixStatus.PENDING,
        )

        mock_db.query.return_value.filter.return_value.filter.return_value.first.return_value = policy_fix

        service = PolicyFixingService(mock_db, "test-tenant")

        # Execute
        result = service.update_fix_status(1, FixStatus.REVIEWED, "admin@example.com", "Looks good")

        # Assert
        assert result.status == FixStatus.REVIEWED
        assert result.reviewed_by == "admin@example.com"
        assert result.review_comment == "Looks good"
        assert result.reviewed_at is not None
        mock_db.commit.assert_called_once()

    def test_delete_fix(self, mock_db):
        """Test deleting a fix."""
        # Setup
        policy_fix = PolicyFix(
            id=1,
            policy_id=1,
            tenant_id="test-tenant",
            security_gap_type="incomplete_logic",
            severity=FixSeverity.MEDIUM,
            gap_description="Test",
            missing_checks="[]",
            original_policy="{}",
            fixed_policy="{}",
            fix_explanation="Test",
            status=FixStatus.PENDING,
        )

        mock_db.query.return_value.filter.return_value.filter.return_value.first.return_value = policy_fix

        service = PolicyFixingService(mock_db, "test-tenant")

        # Execute
        result = service.delete_fix(1)

        # Assert
        assert result is True
        mock_db.delete.assert_called_once_with(policy_fix)
        mock_db.commit.assert_called_once()

    def test_delete_fix_not_found(self, mock_db):
        """Test deleting non-existent fix."""
        # Setup
        mock_db.query.return_value.filter.return_value.filter.return_value.first.return_value = None

        service = PolicyFixingService(mock_db, "test-tenant")

        # Execute
        result = service.delete_fix(999)

        # Assert
        assert result is False
        mock_db.delete.assert_not_called()

    def test_parse_severity(self, mock_db):
        """Test parsing severity strings."""
        service = PolicyFixingService(mock_db, "test-tenant")

        assert service._parse_severity("low") == FixSeverity.LOW
        assert service._parse_severity("medium") == FixSeverity.MEDIUM
        assert service._parse_severity("high") == FixSeverity.HIGH
        assert service._parse_severity("critical") == FixSeverity.CRITICAL
        assert service._parse_severity("unknown") == FixSeverity.MEDIUM  # Default
