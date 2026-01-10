"""Tests for risk scoring service."""


from app.services.risk_scoring_service import RiskScoringService


class TestRiskScoringService:
    """Test RiskScoringService."""

    def test_calculate_complexity_score_simple(self):
        """Test complexity score for simple policy."""
        score = RiskScoringService.calculate_complexity_score(
            subject="Admin",
            resource="User Account",
            action="delete",
            conditions="user.isActive",
            code_snippet="if (user.role === 'ADMIN') { delete(); }",
        )
        assert 0 <= score <= 100

    def test_calculate_complexity_score_complex(self):
        """Test complexity score for complex policy."""
        complex_conditions = (
            "user.role === 'MANAGER' AND "
            "(expense.amount < 5000 OR (expense.amount < 10000 AND expense.department === user.department)) AND "
            "user.status === 'ACTIVE' AND NOT user.isSuspended"
        )
        complex_code = """
        if (user.role === 'MANAGER') {
            if (expense.amount < 5000) {
                return approve();
            } else if (expense.amount < 10000) {
                if (expense.department === user.department) {
                    return approve();
                }
            }
        }
        """
        score = RiskScoringService.calculate_complexity_score(
            subject="Manager",
            resource="Expense Report",
            action="approve",
            conditions=complex_conditions,
            code_snippet=complex_code,
        )
        # Complex policy should have higher score
        assert score > 30

    def test_calculate_impact_score_low_risk(self):
        """Test impact score for low-risk action."""
        score = RiskScoringService.calculate_impact_score(
            subject="User", resource="Profile", action="read", conditions=None
        )
        # Read on non-sensitive resource = low impact
        assert score < 50

    def test_calculate_impact_score_high_risk(self):
        """Test impact score for high-risk action."""
        score = RiskScoringService.calculate_impact_score(
            subject="Admin",
            resource="Financial Data with PII",
            action="delete",
            conditions=None,
        )
        # Delete on sensitive resource = high impact
        assert score > 50

    def test_calculate_confidence_score_with_evidence(self):
        """Test confidence score with strong evidence."""
        code_snippet = """
        @PreAuthorize("hasRole('ADMIN')")
        public void deleteUser(User user) {
            if (!hasPermission(user)) {
                throw new UnauthorizedException();
            }
            userRepository.delete(user);
        }
        """
        score = RiskScoringService.calculate_confidence_score(
            evidence_count=3,
            code_snippet=code_snippet,
            subject="Admin",
            resource="User Account",
            action="delete",
        )
        # Strong evidence = high confidence
        assert score > 50

    def test_calculate_confidence_score_weak_evidence(self):
        """Test confidence score with weak evidence."""
        score = RiskScoringService.calculate_confidence_score(
            evidence_count=1,
            code_snippet="delete(user);",
            subject="Unknown",
            resource="Unknown",
            action="Unknown",
        )
        # Weak evidence = low confidence
        assert score < 50

    def test_calculate_historical_score(self):
        """Test historical score calculation."""
        score = RiskScoringService.calculate_historical_score()
        # Should return 0 for now (not implemented)
        assert score == 0.0

    def test_calculate_overall_risk_score(self):
        """Test overall risk score calculation."""
        # High impact, high complexity, low confidence
        overall = RiskScoringService.calculate_overall_risk_score(
            complexity=80.0, impact=90.0, confidence=30.0, historical=0.0
        )
        # Should be high risk (impact=40%, complexity=30%, inverted_confidence=20%, historical=10%)
        # = 90*0.4 + 80*0.3 + 70*0.2 + 0*0.1 = 36 + 24 + 14 + 0 = 74
        assert 70 <= overall <= 80

    def test_calculate_overall_risk_score_low_risk(self):
        """Test overall risk score for low-risk policy."""
        # Low impact, low complexity, high confidence
        overall = RiskScoringService.calculate_overall_risk_score(
            complexity=10.0, impact=10.0, confidence=90.0, historical=0.0
        )
        # Should be low risk
        # = 10*0.4 + 10*0.3 + 10*0.2 + 0*0.1 = 4 + 3 + 2 + 0 = 9
        assert overall < 20
