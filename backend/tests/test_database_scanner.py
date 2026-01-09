"""Tests for database scanner service."""
import json
from unittest.mock import MagicMock, Mock, patch

import pytest

from app.models.repository import DatabaseType, Repository
from app.services.database_scanner_service import DatabaseScannerService


@pytest.fixture
def mock_repository():
    """Create a mock PostgreSQL repository."""
    repo = Mock(spec=Repository)
    repo.id = 1
    repo.name = "Test Database"
    repo.connection_config = {
        "database_type": "postgresql",
        "host": "localhost",
        "port": 5432,
        "database": "testdb",
        "username": "testuser",
        "password": "testpass",
    }
    return repo


@pytest.fixture
def database_scanner():
    """Create database scanner service instance."""
    return DatabaseScannerService()


def test_build_connection_string_postgresql(database_scanner, mock_repository):
    """Test building PostgreSQL connection string."""
    conn_string = database_scanner._build_connection_string(mock_repository)
    assert "postgresql+psycopg2://" in conn_string
    assert "testuser:testpass@localhost:5432/testdb" in conn_string


def test_build_connection_string_mysql(database_scanner):
    """Test building MySQL connection string."""
    repo = Mock(spec=Repository)
    repo.connection_config = {
        "database_type": "mysql",
        "host": "localhost",
        "port": 3306,
        "database": "testdb",
        "username": "testuser",
        "password": "testpass",
    }
    conn_string = database_scanner._build_connection_string(repo)
    assert "mysql+pymysql://" in conn_string
    assert "testuser:testpass@localhost:3306/testdb" in conn_string


def test_build_connection_string_sqlserver(database_scanner):
    """Test building SQL Server connection string."""
    repo = Mock(spec=Repository)
    repo.connection_config = {
        "database_type": "sqlserver",
        "host": "localhost",
        "port": 1433,
        "database": "testdb",
        "username": "testuser",
        "password": "testpass",
    }
    conn_string = database_scanner._build_connection_string(repo)
    assert "mssql+pyodbc://" in conn_string
    assert "ODBC+Driver+17+for+SQL+Server" in conn_string


def test_build_connection_string_oracle(database_scanner):
    """Test building Oracle connection string."""
    repo = Mock(spec=Repository)
    repo.connection_config = {
        "database_type": "oracle",
        "host": "localhost",
        "port": 1521,
        "database": "testdb",
        "username": "testuser",
        "password": "testpass",
    }
    conn_string = database_scanner._build_connection_string(repo)
    assert "oracle+cx_oracle://" in conn_string
    assert "testuser:testpass@localhost:1521/testdb" in conn_string


def test_build_connection_string_missing_config(database_scanner):
    """Test building connection string with missing config raises error."""
    repo = Mock(spec=Repository)
    repo.connection_config = {}

    with pytest.raises(ValueError, match="Missing required database connection parameters"):
        database_scanner._build_connection_string(repo)


def test_contains_authorization_logic_with_grant(database_scanner):
    """Test detecting GRANT statement."""
    definition = "GRANT SELECT ON users TO public;"
    assert database_scanner._contains_authorization_logic(definition) is True


def test_contains_authorization_logic_with_policy(database_scanner):
    """Test detecting CREATE POLICY statement."""
    definition = """
        CREATE POLICY user_isolation ON users
        USING (user_id = current_user_id());
    """
    assert database_scanner._contains_authorization_logic(definition) is True


def test_contains_authorization_logic_with_role_check(database_scanner):
    """Test detecting role check in IF statement."""
    definition = """
        IF current_role = 'admin' THEN
            RETURN true;
        END IF;
    """
    assert database_scanner._contains_authorization_logic(definition) is True


def test_contains_authorization_logic_no_auth(database_scanner):
    """Test no authorization logic detected."""
    definition = """
        SELECT * FROM products
        WHERE category = 'electronics';
    """
    assert database_scanner._contains_authorization_logic(definition) is False


@patch.object(DatabaseScannerService, "_extract_policies_from_procedure")
@patch.object(DatabaseScannerService, "_get_stored_procedures")
@patch("app.services.database_scanner_service.create_engine")
@pytest.mark.asyncio
async def test_scan_database_postgresql(
    mock_create_engine,
    mock_get_procedures,
    mock_extract_policies,
    database_scanner,
    mock_repository,
):
    """Test scanning PostgreSQL database."""
    # Mock engine
    mock_engine = Mock()
    mock_create_engine.return_value = mock_engine

    # Mock stored procedures
    mock_get_procedures.return_value = [
        {
            "schema": "public",
            "name": "check_user_access",
            "definition": "IF current_user IN (SELECT user_id FROM admins) THEN RETURN true; END IF;",
            "type": "FUNCTION",
        }
    ]

    # Mock policy extraction to return a mock policy
    mock_policy = Mock()
    mock_policy.subject = "Admin users"
    mock_policy.resource = "Database access"
    mock_policy.action = "Full access"
    mock_policy.conditions = "User must be in admins table"
    mock_extract_policies.return_value = [mock_policy]

    result = await database_scanner.scan_database(
        repository=mock_repository,
        tenant_id="test-tenant",
    )

    assert result["procedures_scanned"] == 1
    assert result["total_procedures"] == 1
    assert result["policies_extracted"] == 1
    assert len(result["policies"]) == 1

    policy = result["policies"][0]
    assert policy.subject == "Admin users"
    assert policy.resource == "Database access"
    assert policy.action == "Full access"
    assert policy.conditions == "User must be in admins table"


@patch("app.services.database_scanner_service.create_engine")
@pytest.mark.asyncio
async def test_scan_database_connection_error(
    mock_create_engine,
    database_scanner,
    mock_repository,
):
    """Test handling database connection errors."""
    mock_create_engine.side_effect = Exception("Connection failed")

    with pytest.raises(Exception, match="Connection failed"):
        await database_scanner.scan_database(
            repository=mock_repository,
            tenant_id="test-tenant",
        )


def test_extract_policies_empty_response(database_scanner, mock_repository):
    """Test handling empty LLM response."""
    procedure = {
        "schema": "public",
        "name": "test_proc",
        "definition": "SELECT 1;",
        "type": "FUNCTION",
    }

    llm_response = "[]"

    with patch.object(database_scanner.llm_provider, "create_message", return_value=llm_response):
        policies = database_scanner._extract_policies_from_procedure(
            procedure=procedure,
            repository_id=1,
            tenant_id="test-tenant",
            db_type="postgresql",
        )

    assert len(policies) == 0


def test_extract_policies_invalid_json(database_scanner, mock_repository):
    """Test handling invalid JSON from LLM."""
    procedure = {
        "schema": "public",
        "name": "test_proc",
        "definition": "IF current_user = 'admin' THEN RETURN true; END IF;",
        "type": "FUNCTION",
    }

    llm_response = "This is not valid JSON"

    with patch.object(database_scanner.llm_provider, "create_message", return_value=llm_response):
        policies = database_scanner._extract_policies_from_procedure(
            procedure=procedure,
            repository_id=1,
            tenant_id="test-tenant",
            db_type="postgresql",
        )

    assert len(policies) == 0
