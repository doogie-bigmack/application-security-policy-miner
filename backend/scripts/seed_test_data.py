"""Seed test data for E2E testing."""

import asyncio
import logging
import sys
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# flake8: noqa: E402
# Import after sys.path modification
from app.core.database import SessionLocal, engine
from app.models import (
    Application,
    BusinessUnit,
    CriticalityLevel,
    Division,
    Evidence,
    Organization,
    PBACProvider,
    Policy,
    PolicyStatus,
    ProviderType,
    Repository,
    RepositoryStatus,
    RepositoryType,
    RiskLevel,
    SourceType,
    Tenant,
)
from app.models.policy import ValidationStatus
from app.models.repository import GitProvider

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def seed_test_data() -> None:
    """Seed the test database with sample data for E2E testing."""
    # Import Base and all models to resolve relationships
    import app.models  # noqa: F401
    from app.models.repository import Base
    from app.models.secret_detection import SecretDetectionLog  # noqa: F401

    # Create all tables
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")

    db = SessionLocal()

    try:
        logger.info("Starting test data seeding...")

        # Check if data already exists
        existing_org = db.query(Organization).filter(Organization.name == "Test Organization").first()
        if existing_org:
            logger.info("Test data already exists. Skipping seeding.")
            return

        # 1. Create test tenant
        logger.info("Creating test tenant...")
        tenant = Tenant(
            tenant_id="test-tenant-001",
            name="Test Tenant",
            description="Test tenant for E2E testing",
            is_active=True,
        )
        db.add(tenant)
        db.flush()
        logger.info(f"Created tenant: {tenant.tenant_id}")

        # 2. Create test organization
        logger.info("Creating test organization...")
        organization = Organization(
            name="Test Organization",
            description="Test organization for E2E testing",
        )
        db.add(organization)
        db.flush()
        logger.info(f"Created organization: {organization.name}")

        # 3. Create test division
        logger.info("Creating test division...")
        division = Division(
            organization_id=organization.id,
            name="Engineering Division",
            description="Engineering division for test organization",
        )
        db.add(division)
        db.flush()
        logger.info(f"Created division: {division.name}")

        # 4. Create test business unit
        logger.info("Creating test business unit...")
        business_unit = BusinessUnit(
            division_id=division.id,
            name="Security Team",
            description="Security team business unit",
        )
        db.add(business_unit)
        db.flush()
        logger.info(f"Created business unit: {business_unit.name}")

        # 5. Create test application
        logger.info("Creating test application...")
        application = Application(
            name="Test Application",
            business_unit_id=business_unit.id,
            tenant_id=tenant.tenant_id,
            description="Test application for E2E testing",
            criticality=CriticalityLevel.HIGH,
            tech_stack="Python, FastAPI, React, PostgreSQL",
            owner="test-owner@example.com",
        )
        db.add(application)
        db.flush()
        logger.info(f"Created application: {application.name}")

        # 6. Create test repositories
        logger.info("Creating test repositories...")

        # Repository 1: GitHub repository
        repo_github = Repository(
            name="test-auth-patterns",
            description="Test repository with authorization patterns",
            repository_type=RepositoryType.GIT,
            git_provider=GitProvider.GITHUB,
            source_url="https://github.com/doogie-bigmack/test-auth-patterns",
            status=RepositoryStatus.CONNECTED,
            tenant_id=tenant.tenant_id,
            webhook_enabled=0,
        )
        db.add(repo_github)
        db.flush()
        logger.info(f"Created repository: {repo_github.name}")

        # Repository 2: Another GitHub repository
        repo_github_2 = Repository(
            name="application-security-policy-miner",
            description="Policy miner application repository",
            repository_type=RepositoryType.GIT,
            git_provider=GitProvider.GITHUB,
            source_url="https://github.com/doogie-bigmack/application-security-policy-miner",
            status=RepositoryStatus.CONNECTED,
            tenant_id=tenant.tenant_id,
            webhook_enabled=0,
        )
        db.add(repo_github_2)
        db.flush()
        logger.info(f"Created repository: {repo_github_2.name}")

        # Repository 3: GitLab repository
        repo_gitlab = Repository(
            name="test-gitlab-repo",
            description="Test GitLab repository",
            repository_type=RepositoryType.GIT,
            git_provider=GitProvider.GITLAB,
            source_url="https://gitlab.com/test-org/test-repo",
            status=RepositoryStatus.CONNECTED,
            tenant_id=tenant.tenant_id,
            webhook_enabled=0,
        )
        db.add(repo_gitlab)
        db.flush()
        logger.info(f"Created repository: {repo_gitlab.name}")

        # 7. Create sample policies with evidence
        logger.info("Creating sample policies...")

        # Policy 1: Admin role requirement
        policy1 = Policy(
            repository_id=repo_github.id,
            application_id=application.id,
            subject="Admin",
            resource="User Management",
            action="create_user",
            conditions="role == 'admin'",
            risk_score=75.0,
            risk_level=RiskLevel.HIGH,
            complexity_score=60.0,
            impact_score=80.0,
            confidence_score=90.0,
            status=PolicyStatus.APPROVED,
            description="Only administrators can create new users in the system",
            source_type=SourceType.BACKEND,
            tenant_id=tenant.tenant_id,
        )
        db.add(policy1)
        db.flush()

        evidence1 = Evidence(
            policy_id=policy1.id,
            file_path="backend/controllers/user_controller.py",
            line_start=45,
            line_end=50,
            code_snippet='@require_role("admin")\ndef create_user(request):\n    """Create a new user."""\n    user = User(**request.data)\n    db.session.add(user)\n    return {"id": user.id}',
            validation_status=ValidationStatus.VALID,
        )
        db.add(evidence1)
        logger.info(f"Created policy: {policy1.subject} -> {policy1.action} -> {policy1.resource}")

        # Policy 2: Manager approval for expenses
        policy2 = Policy(
            repository_id=repo_github.id,
            application_id=application.id,
            subject="Manager",
            resource="Expense Report",
            action="approve",
            conditions="amount < 5000 AND department == requester.department",
            risk_score=45.0,
            risk_level=RiskLevel.MEDIUM,
            complexity_score=70.0,
            impact_score=50.0,
            confidence_score=85.0,
            status=PolicyStatus.APPROVED,
            description="Managers can approve expense reports under $5000 within their department",
            source_type=SourceType.BACKEND,
            tenant_id=tenant.tenant_id,
        )
        db.add(policy2)
        db.flush()

        evidence2 = Evidence(
            policy_id=policy2.id,
            file_path="backend/services/expense_service.py",
            line_start=120,
            line_end=128,
            code_snippet='def can_approve_expense(user, expense):\n    if user.role != "manager":\n        return False\n    if expense.amount >= 5000:\n        return False\n    if expense.department != user.department:\n        return False\n    return True',
            validation_status=ValidationStatus.VALID,
        )
        db.add(evidence2)
        logger.info(f"Created policy: {policy2.subject} -> {policy2.action} -> {policy2.resource}")

        # Policy 3: Database access control
        policy3 = Policy(
            repository_id=repo_github_2.id,
            application_id=application.id,
            subject="Database Administrator",
            resource="Production Database",
            action="execute_query",
            conditions="environment == 'production' AND requires_approval == true",
            risk_score=90.0,
            risk_level=RiskLevel.HIGH,
            complexity_score=40.0,
            impact_score=95.0,
            confidence_score=95.0,
            status=PolicyStatus.PENDING,
            description="Database administrators need approval to execute queries on production",
            source_type=SourceType.DATABASE,
            tenant_id=tenant.tenant_id,
        )
        db.add(policy3)
        db.flush()

        evidence3 = Evidence(
            policy_id=policy3.id,
            file_path="database/stored_procedures/check_permissions.sql",
            line_start=15,
            line_end=25,
            code_snippet="CREATE OR REPLACE FUNCTION check_query_permission(user_id INT, query TEXT)\nRETURNS BOOLEAN AS $$\nBEGIN\n    IF (SELECT environment FROM system_config) = 'production' THEN\n        RETURN EXISTS(\n            SELECT 1 FROM approvals\n            WHERE user_id = user_id AND approved = true\n        );\n    END IF;\n    RETURN true;\nEND;\n$$ LANGUAGE plpgsql;",
            validation_status=ValidationStatus.VALID,
        )
        db.add(evidence3)
        logger.info(f"Created policy: {policy3.subject} -> {policy3.action} -> {policy3.resource}")

        # Policy 4: Frontend route protection
        policy4 = Policy(
            repository_id=repo_github_2.id,
            application_id=application.id,
            subject="Authenticated User",
            resource="Dashboard",
            action="view",
            conditions="is_authenticated == true",
            risk_score=30.0,
            risk_level=RiskLevel.LOW,
            complexity_score=20.0,
            impact_score=40.0,
            confidence_score=95.0,
            status=PolicyStatus.APPROVED,
            description="Only authenticated users can view the dashboard",
            source_type=SourceType.FRONTEND,
            tenant_id=tenant.tenant_id,
        )
        db.add(policy4)
        db.flush()

        evidence4 = Evidence(
            policy_id=policy4.id,
            file_path="frontend/src/routes/ProtectedRoute.tsx",
            line_start=8,
            line_end=15,
            code_snippet='export const ProtectedRoute = ({ children }: Props) => {\n  const { isAuthenticated } = useAuth();\n\n  if (!isAuthenticated) {\n    return <Navigate to="/login" />;\n  }\n\n  return <>{children}</>;\n};',
            validation_status=ValidationStatus.VALID,
        )
        db.add(evidence4)
        logger.info(f"Created policy: {policy4.subject} -> {policy4.action} -> {policy4.resource}")

        # Policy 5: API rate limiting
        policy5 = Policy(
            repository_id=repo_github_2.id,
            application_id=application.id,
            subject="API Client",
            resource="API Endpoint",
            action="call",
            conditions="requests_per_minute <= 100",
            risk_score=50.0,
            risk_level=RiskLevel.MEDIUM,
            complexity_score=30.0,
            impact_score=60.0,
            confidence_score=90.0,
            status=PolicyStatus.APPROVED,
            description="API clients are rate-limited to 100 requests per minute",
            source_type=SourceType.BACKEND,
            tenant_id=tenant.tenant_id,
        )
        db.add(policy5)
        db.flush()

        evidence5 = Evidence(
            policy_id=policy5.id,
            file_path="backend/middleware/rate_limit.py",
            line_start=30,
            line_end=38,
            code_snippet='class RateLimitMiddleware:\n    def __init__(self, max_requests=100):\n        self.max_requests = max_requests\n\n    async def dispatch(self, request):\n        client_id = get_client_id(request)\n        count = await redis.get(f"rate:{client_id}")\n        if count and int(count) >= self.max_requests:\n            raise RateLimitExceeded()',
            validation_status=ValidationStatus.VALID,
        )
        db.add(evidence5)
        logger.info(f"Created policy: {policy5.subject} -> {policy5.action} -> {policy5.resource}")

        # 8. Create test PBAC provider
        logger.info("Creating test PBAC provider...")
        pbac_provider = PBACProvider(
            tenant_id=tenant.tenant_id,
            provider_type=ProviderType.OPA,
            name="Test OPA Provider",
            endpoint_url="http://localhost:8181",
            api_key=None,  # OPA typically doesn't require API key for local testing
            configuration='{"bundle_path": "/v1/data"}',
        )
        db.add(pbac_provider)
        db.flush()
        logger.info(f"Created PBAC provider: {pbac_provider.name}")

        # Commit all changes
        logger.info("Committing changes to database...")
        db.commit()
        logger.info("✅ Test data seeding completed successfully!")

        # Print summary
        logger.info("\n" + "=" * 60)
        logger.info("SEED SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Tenant: {tenant.tenant_id}")
        logger.info(f"Organization: {organization.name}")
        logger.info(f"Division: {division.name}")
        logger.info(f"Business Unit: {business_unit.name}")
        logger.info(f"Application: {application.name}")
        logger.info("Repositories: 3 (GitHub: 2, GitLab: 1)")
        logger.info("Policies: 5 (with evidence)")
        logger.info(f"PBAC Provider: {pbac_provider.name} (OPA)")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Error seeding test data: {e}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    """Main entry point for CLI execution."""
    logger.info("Test Data Seeder")
    logger.info("=" * 60)

    # Run the async seed function
    asyncio.run(seed_test_data())


if __name__ == "__main__":
    main()
