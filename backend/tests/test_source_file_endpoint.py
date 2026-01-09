"""Tests for source file endpoint."""
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import get_db
from app.main import app
from app.models.policy import Evidence, Policy, PolicyStatus, RiskLevel, SourceType
from app.models.repository import Base, Repository, RepositoryStatus, RepositoryType

# Setup test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_source_file.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db_session():
    """Create test database session."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db_session):
    """Create test client."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


@pytest.fixture
def test_repository(db_session):
    """Create test repository."""
    repo = Repository(
        name="Test Repo",
        description="Test repository",
        repository_type=RepositoryType.GIT,
        source_url="https://github.com/test/repo.git",
        status=RepositoryStatus.CONNECTED,
        tenant_id="test-tenant",
    )
    db_session.add(repo)
    db_session.commit()
    db_session.refresh(repo)
    return repo


@pytest.fixture
def test_policy(db_session, test_repository):
    """Create test policy."""
    policy = Policy(
        repository_id=test_repository.id,
        subject="Manager",
        resource="Expense Report",
        action="approve",
        conditions="amount < 5000",
        status=PolicyStatus.PENDING,
        risk_level=RiskLevel.LOW,
        source_type=SourceType.BACKEND,
        tenant_id="test-tenant",
    )
    db_session.add(policy)
    db_session.commit()
    db_session.refresh(policy)
    return policy


@pytest.fixture
def test_evidence_with_file(db_session, test_policy, test_repository):
    """Create test evidence with actual source file."""
    # Create temporary source file
    repo_dir = Path("/tmp/policy_miner_repos") / str(test_repository.id)
    repo_dir.mkdir(parents=True, exist_ok=True)

    test_file = repo_dir / "test.py"
    test_content = """def approve_expense(user, expense):
    if user.role == "Manager" and expense.amount < 5000:
        return True
    return False
"""
    test_file.write_text(test_content)

    # Create evidence
    evidence = Evidence(
        policy_id=test_policy.id,
        file_path="test.py",
        line_start=2,
        line_end=3,
        code_snippet='    if user.role == "Manager" and expense.amount < 5000:\n        return True',
    )
    db_session.add(evidence)
    db_session.commit()
    db_session.refresh(evidence)

    yield evidence

    # Cleanup
    import shutil

    if repo_dir.exists():
        shutil.rmtree(repo_dir)


def test_get_source_file_success(client, test_evidence_with_file):
    """Test successful source file retrieval."""
    response = client.get(f"/api/v1/policies/evidence/{test_evidence_with_file.id}/source")

    assert response.status_code == 200
    data = response.json()

    assert data["file_path"] == "test.py"
    assert "def approve_expense" in data["content"]
    assert data["line_start"] == 2
    assert data["line_end"] == 3
    assert data["total_lines"] > 0


def test_get_source_file_evidence_not_found(client):
    """Test source file endpoint with non-existent evidence."""
    response = client.get("/api/v1/policies/evidence/99999/source")

    assert response.status_code == 404
    assert "Evidence not found" in response.json()["detail"]


def test_get_source_file_file_not_found(client, db_session, test_policy):
    """Test source file endpoint when source file doesn't exist."""
    # Create evidence without creating actual file
    evidence = Evidence(
        policy_id=test_policy.id,
        file_path="nonexistent.py",
        line_start=1,
        line_end=2,
        code_snippet="some code",
    )
    db_session.add(evidence)
    db_session.commit()
    db_session.refresh(evidence)

    response = client.get(f"/api/v1/policies/evidence/{evidence.id}/source")

    assert response.status_code == 404
    assert "Source file not found" in response.json()["detail"]


def test_source_file_content_matches_evidence(client, test_evidence_with_file):
    """Test that source file content matches the evidence snippet."""
    response = client.get(f"/api/v1/policies/evidence/{test_evidence_with_file.id}/source")

    assert response.status_code == 200
    data = response.json()

    # Extract the relevant lines from content
    lines = data["content"].split("\n")
    evidence_lines = "\n".join(lines[data["line_start"] - 1 : data["line_end"]])

    # Verify the evidence snippet is in the extracted lines
    assert 'user.role == "Manager"' in evidence_lines
    assert "expense.amount < 5000" in evidence_lines


def test_source_file_line_numbers_accurate(client, test_evidence_with_file):
    """Test that line numbers are accurate."""
    response = client.get(f"/api/v1/policies/evidence/{test_evidence_with_file.id}/source")

    assert response.status_code == 200
    data = response.json()

    assert data["line_start"] == 2
    assert data["line_end"] == 3
    assert data["total_lines"] == 4  # 4 lines in the test file
