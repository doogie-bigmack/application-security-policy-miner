"""Tests for SQL Server stored procedure analysis."""
import json
from unittest.mock import Mock, patch

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.models.repository import DatabaseType, Repository, RepositoryType
from app.services.database_scanner_service import DatabaseScannerService


class TestSQLServerDatabaseScanner:
    """Test SQL Server stored procedure analysis."""

    @pytest.fixture
    def mock_repository(self):
        """Create a mock SQL Server repository."""
        repo = Mock(spec=Repository)
        repo.id = 1
        repo.name = "Test SQL Server DB"
        repo.repository_type = RepositoryType.DATABASE
        repo.connection_config = {
            "database_type": DatabaseType.SQLSERVER.value,
            "host": "sqlserver.example.com",
            "port": 1433,
            "database": "testdb",
            "username": "testuser",
            "password": "testpass",
        }
        repo.tenant_id = "test-tenant"
        return repo

    @pytest.fixture
    def scanner_service(self):
        """Create database scanner service instance."""
        with patch("app.services.database_scanner_service.get_llm_provider"):
            service = DatabaseScannerService()
            service.llm_provider = Mock()
            service.llm_provider.create_message.return_value = json.dumps([
                {
                    "subject": "manager role",
                    "resource": "Expenses table",
                    "action": "UPDATE",
                    "conditions": "Only for approved expenses",
                    "description": "Managers can approve expenses",
                }
            ])
            return service

    def test_build_sqlserver_connection_string(self, scanner_service, mock_repository):
        """Test building SQL Server connection string with ODBC driver."""
        conn_str = scanner_service._build_connection_string(mock_repository)

        assert "mssql+pyodbc" in conn_str
        assert "sqlserver.example.com:1433" in conn_str
        assert "testdb" in conn_str
        assert "testuser" in conn_str
        assert "ODBC+Driver+17+for+SQL+Server" in conn_str

    def test_contains_authorization_logic_with_is_rolemember(self, scanner_service):
        """Test detection of IS_ROLEMEMBER authorization pattern."""
        definition = """
        CREATE PROCEDURE dbo.check_user_permission()
        AS
        BEGIN
            IF IS_ROLEMEMBER('admin') = 1
                SELECT 'Authorized'
        END
        """
        assert scanner_service._contains_authorization_logic(definition)

    def test_contains_authorization_logic_with_has_perms_by_name(self, scanner_service):
        """Test detection of HAS_PERMS_BY_NAME check."""
        definition = """
        CREATE FUNCTION dbo.can_access_table()
        RETURNS BIT
        AS
        BEGIN
            RETURN HAS_PERMS_BY_NAME('Employees', 'OBJECT', 'SELECT')
        END
        """
        assert scanner_service._contains_authorization_logic(definition)

    def test_contains_authorization_logic_with_current_user(self, scanner_service):
        """Test detection of CURRENT_USER pattern."""
        definition = """
        CREATE PROCEDURE dbo.get_user_data
        AS
        BEGIN
            SELECT * FROM Users WHERE Username = CURRENT_USER
        END
        """
        assert scanner_service._contains_authorization_logic(definition)

    def test_contains_authorization_logic_with_grant(self, scanner_service):
        """Test detection of GRANT statement."""
        definition = """
        CREATE PROCEDURE dbo.manage_permissions
        AS
        BEGIN
            GRANT SELECT ON Employees TO hr_role
        END
        """
        assert scanner_service._contains_authorization_logic(definition)

    def test_contains_authorization_logic_with_revoke(self, scanner_service):
        """Test detection of REVOKE statement."""
        definition = """
        CREATE PROCEDURE dbo.revoke_access
        AS
        BEGIN
            REVOKE UPDATE ON Salaries FROM general_users
        END
        """
        assert scanner_service._contains_authorization_logic(definition)

    def test_no_authorization_logic(self, scanner_service):
        """Test that regular procedures without auth logic are not detected."""
        definition = """
        CREATE PROCEDURE dbo.calculate_total
            @Price DECIMAL,
            @Quantity INT
        AS
        BEGIN
            SELECT @Price * @Quantity AS Total
        END
        """
        assert not scanner_service._contains_authorization_logic(definition)

    @patch("app.services.database_scanner_service.create_engine")
    def test_get_stored_procedures_sqlserver(self, mock_create_engine, scanner_service):
        """Test retrieving SQL Server stored procedures."""
        # Mock engine and connection
        mock_engine = Mock()
        mock_conn = Mock()
        mock_result = Mock()

        # Mock procedure data
        mock_row1 = Mock()
        mock_row1.schema = "dbo"
        mock_row1.name = "sp_CheckUserPermission"
        mock_row1.definition = """
        CREATE PROCEDURE dbo.sp_CheckUserPermission
            @UserId INT
        AS
        BEGIN
            IF IS_ROLEMEMBER('db_admin', USER_NAME(@UserId)) = 1
                SELECT 1 AS HasPermission
        END
        """

        mock_row2 = Mock()
        mock_row2.schema = "dbo"
        mock_row2.name = "fn_GetUserRoles"
        mock_row2.definition = """
        CREATE FUNCTION dbo.fn_GetUserRoles(@UserId INT)
        RETURNS TABLE
        AS
        RETURN (
            SELECT r.RoleName FROM Roles r
            WHERE HAS_PERMS_BY_NAME('Employees', 'OBJECT', 'SELECT') = 1
        )
        """

        mock_result.__iter__ = Mock(return_value=iter([mock_row1, mock_row2]))
        mock_conn.execute.return_value = mock_result
        mock_engine.connect.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = Mock(return_value=False)
        mock_create_engine.return_value = mock_engine

        procedures = scanner_service._get_stored_procedures(
            mock_engine,
            DatabaseType.SQLSERVER.value
        )

        assert len(procedures) == 2
        assert procedures[0]["schema"] == "dbo"
        assert procedures[0]["name"] == "sp_CheckUserPermission"
        assert "IS_ROLEMEMBER" in procedures[0]["definition"]
        assert procedures[1]["name"] == "fn_GetUserRoles"
        assert "HAS_PERMS_BY_NAME" in procedures[1]["definition"]

    @pytest.mark.asyncio
    async def test_scan_database_connection_error(self, scanner_service, mock_repository):
        """Test handling of database connection errors."""
        with patch("app.services.database_scanner_service.create_engine") as mock_create:
            mock_create.side_effect = SQLAlchemyError("Connection failed")

            with pytest.raises(SQLAlchemyError):
                await scanner_service.scan_database(
                    repository=mock_repository,
                    tenant_id=mock_repository.tenant_id,
                )

    def test_build_connection_string_missing_config(self, scanner_service):
        """Test error when connection config is missing."""
        repo = Mock(spec=Repository)
        repo.id = 1
        repo.name = "Test"
        repo.repository_type = RepositoryType.DATABASE
        repo.connection_config = {}

        with pytest.raises(ValueError, match="Missing required database connection parameters"):
            scanner_service._build_connection_string(repo)

    def test_sqlserver_specific_authorization_patterns(self, scanner_service):
        """Test SQL Server-specific authorization patterns."""
        # IS_ROLEMEMBER
        assert scanner_service._contains_authorization_logic(
            "IF IS_ROLEMEMBER('db_datareader') = 1"
        )

        # HAS_PERMS_BY_NAME
        assert scanner_service._contains_authorization_logic(
            "HAS_PERMS_BY_NAME('MyTable', 'OBJECT', 'UPDATE')"
        )

        # SESSION_USER
        assert scanner_service._contains_authorization_logic(
            "SELECT * FROM Users WHERE UserName = SESSION_USER"
        )

        # SECURITY DEFINER
        assert scanner_service._contains_authorization_logic(
            "CREATE PROCEDURE dbo.sp_test WITH SECURITY DEFINER"
        )

    @patch("app.services.database_scanner_service.create_engine")
    def test_sqlserver_query_structure(self, mock_create_engine, scanner_service):
        """Test that SQL Server uses correct system catalog queries."""
        mock_engine = Mock()
        mock_conn = Mock()
        mock_result = Mock()
        mock_result.__iter__ = Mock(return_value=iter([]))

        mock_conn.execute.return_value = mock_result
        mock_engine.connect.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = Mock(return_value=False)
        mock_create_engine.return_value = mock_engine

        # Get procedures using SQL Server catalog
        scanner_service._get_stored_procedures(mock_engine, DatabaseType.SQLSERVER.value)

        # Verify SQL Server-specific query was executed
        call_args = mock_conn.execute.call_args[0][0]
        query_text = str(call_args)

        # SQL Server uses sys.sql_modules and sys.objects
        assert "sys.sql_modules" in query_text or "sql_modules" in query_text.lower()
        assert "sys.objects" in query_text or "objects" in query_text.lower()
