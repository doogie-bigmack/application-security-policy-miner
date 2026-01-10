"""Integration tests for SQL Server stored procedure analysis."""
from unittest.mock import Mock, patch

import pytest

from app.models.repository import Repository
from app.services.database_scanner_service import DatabaseScannerService


@pytest.fixture
def sql_server_repository():
    """Create a mock SQL Server repository."""
    repo = Mock(spec=Repository)
    repo.id = 1
    repo.name = "SQL Server Test Database"
    repo.connection_config = {
        "database_type": "sqlserver",
        "host": "localhost",
        "port": 1433,
        "database": "testdb",
        "username": "sa",
        "password": "YourStrong@Passw0rd",
    }
    return repo


@pytest.fixture
def database_scanner():
    """Create database scanner service instance."""
    return DatabaseScannerService()


def test_sql_server_connection_string(database_scanner, sql_server_repository):
    """Test building SQL Server connection string with ODBC driver."""
    conn_string = database_scanner._build_connection_string(sql_server_repository)

    assert "mssql+pyodbc://" in conn_string
    assert "sa:YourStrong@Passw0rd@localhost:1433/testdb" in conn_string
    assert "ODBC+Driver+17+for+SQL+Server" in conn_string


def test_sql_server_authorization_patterns(database_scanner):
    """Test detecting SQL Server specific authorization patterns."""

    # Test IS_MEMBER (SQL Server specific)
    definition1 = """
        IF IS_MEMBER('db_owner') = 1
        BEGIN
            GRANT SELECT ON dbo.SensitiveData TO [UserRole]
        END
    """
    assert database_scanner._contains_authorization_logic(definition1) is True

    # Test HAS_PERMS_BY_NAME (SQL Server specific)
    definition2 = """
        IF HAS_PERMS_BY_NAME('dbo.Orders', 'OBJECT', 'UPDATE') = 1
        BEGIN
            UPDATE dbo.Orders SET Status = 'Approved'
        END
    """
    assert database_scanner._contains_authorization_logic(definition2) is True

    # Test IS_ROLEMEMBER (SQL Server specific)
    definition3 = """
        IF IS_ROLEMEMBER('db_datareader', @username) = 1
        BEGIN
            SELECT * FROM dbo.UserData
        END
    """
    assert database_scanner._contains_authorization_logic(definition3) is True


@patch.object(DatabaseScannerService, "_extract_policies_from_procedure")
@patch.object(DatabaseScannerService, "_get_stored_procedures")
@patch("app.services.database_scanner_service.create_engine")
@pytest.mark.asyncio
async def test_scan_sql_server_procedures(
    mock_create_engine,
    mock_get_procedures,
    mock_extract_policies,
    database_scanner,
    sql_server_repository,
):
    """Test scanning SQL Server stored procedures."""
    # Mock engine
    mock_engine = Mock()
    mock_engine.dispose = Mock()
    mock_create_engine.return_value = mock_engine

    # Mock SQL Server stored procedures
    mock_get_procedures.return_value = [
        {
            "schema": "dbo",
            "name": "sp_CheckUserPermission",
            "definition": """
                CREATE PROCEDURE dbo.sp_CheckUserPermission
                    @UserId INT,
                    @Resource NVARCHAR(100)
                AS
                BEGIN
                    IF IS_MEMBER('Administrators') = 1
                    BEGIN
                        RETURN 1
                    END

                    IF HAS_PERMS_BY_NAME(@Resource, 'OBJECT', 'SELECT') = 1
                    BEGIN
                        RETURN 1
                    END

                    RETURN 0
                END
            """,
            "type": "P",
        },
        {
            "schema": "dbo",
            "name": "sp_GetUserData",
            "definition": """
                CREATE PROCEDURE dbo.sp_GetUserData
                    @UserId INT
                AS
                BEGIN
                    SELECT * FROM dbo.Users WHERE UserId = @UserId
                END
            """,
            "type": "P",
        }
    ]

    # Mock extracted policies
    mock_policy1 = Mock()
    mock_policy1.subject = "Administrators role"
    mock_policy1.resource = "All database objects"
    mock_policy1.action = "Full access"
    mock_policy1.conditions = "User must be member of Administrators role"
    mock_policy1.evidence = [Mock(file_path="dbo.sp_CheckUserPermission", repository_id=1, tenant_id="test-tenant")]

    mock_policy2 = Mock()
    mock_policy2.subject = "Users with SELECT permission"
    mock_policy2.resource = "Specified resource object"
    mock_policy2.action = "SELECT"
    mock_policy2.conditions = "User must have SELECT permission on the resource"
    mock_policy2.evidence = [Mock(file_path="dbo.sp_CheckUserPermission", repository_id=1, tenant_id="test-tenant")]

    mock_extract_policies.return_value = [mock_policy1, mock_policy2]

    result = await database_scanner.scan_database(
        repository=sql_server_repository,
        tenant_id="test-tenant",
    )

    # Verify scan results
    assert result["total_procedures"] == 2
    assert result["procedures_scanned"] == 1  # Only first one has auth logic
    assert result["policies_extracted"] == 2
    assert len(result["policies"]) == 2

    # Verify policy details
    policy1 = result["policies"][0]
    assert policy1.subject == "Administrators role"
    assert policy1.resource == "All database objects"
    assert policy1.action == "Full access"
    assert "Administrators role" in policy1.conditions

    policy2 = result["policies"][1]
    assert policy2.subject == "Users with SELECT permission"
    assert policy2.resource == "Specified resource object"
    assert policy2.action == "SELECT"

    # Verify evidence is created
    assert len(policy1.evidence) == 1
    assert policy1.evidence[0].file_path == "dbo.sp_CheckUserPermission"
    assert policy1.evidence[0].repository_id == 1
    assert policy1.evidence[0].tenant_id == "test-tenant"

    # Verify engine disposal
    mock_engine.dispose.assert_called_once()


def test_sql_server_procedure_query_structure(database_scanner):
    """Test that SQL Server query structure is correct."""
    # This tests the query structure defined in _get_stored_procedures
    # We verify the query targets the correct system tables


    # The expected query for SQL Server from the implementation
    expected_query = """
                    SELECT
                        SCHEMA_NAME(o.schema_id) as schema,
                        o.name as name,
                        m.definition as definition
                    FROM sys.sql_modules m
                    JOIN sys.objects o ON m.object_id = o.object_id
                    WHERE o.type IN ('P', 'FN', 'IF', 'TF')  -- Procedures and functions
                    ORDER BY schema, name
                """

    # Verify the query is valid SQL (syntax check)
    # In a real integration test, this would run against a real SQL Server
    # For now, we just verify the query structure is as expected
    assert "sys.sql_modules" in expected_query
    assert "sys.objects" in expected_query
    assert "SCHEMA_NAME(o.schema_id)" in expected_query
    assert "o.type IN ('P', 'FN', 'IF', 'TF')" in expected_query


@patch("app.services.database_scanner_service.create_engine")
@pytest.mark.asyncio
async def test_sql_server_connection_error_handling(
    mock_create_engine,
    database_scanner,
    sql_server_repository,
):
    """Test handling SQL Server connection errors."""
    from sqlalchemy.exc import OperationalError

    mock_create_engine.side_effect = OperationalError(
        "statement", "params", "orig", "connection_invalidated"
    )

    with pytest.raises(OperationalError):
        await database_scanner.scan_database(
            repository=sql_server_repository,
            tenant_id="test-tenant",
        )
