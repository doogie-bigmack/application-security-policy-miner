"""Tests for MySQL/MariaDB stored procedure analysis."""
import json
from unittest.mock import Mock, patch

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.models.repository import DatabaseType, Repository, RepositoryType
from app.services.database_scanner_service import DatabaseScannerService


class TestMySQLDatabaseScanner:
    """Test MySQL/MariaDB stored procedure analysis."""

    @pytest.fixture
    def mock_repository(self):
        """Create a mock MySQL repository."""
        repo = Mock(spec=Repository)
        repo.id = 1
        repo.name = "Test MySQL DB"
        repo.repository_type = RepositoryType.DATABASE
        repo.connection_config = {
            "database_type": DatabaseType.MYSQL.value,
            "host": "mysql.example.com",
            "port": 3306,
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
                    "subject": "admin role",
                    "resource": "Employees table",
                    "action": "SELECT",
                    "conditions": "Only for active users",
                    "description": "Admins can view employee data",
                }
            ])
            return service

    def test_build_mysql_connection_string(self, scanner_service, mock_repository):
        """Test building MySQL connection string with pymysql driver."""
        conn_str = scanner_service._build_connection_string(mock_repository)

        assert "mysql+pymysql" in conn_str
        assert "mysql.example.com:3306" in conn_str
        assert "testdb" in conn_str
        assert "testuser" in conn_str
        assert "testpass" in conn_str

    def test_contains_authorization_logic_with_current_user(self, scanner_service):
        """Test detection of CURRENT_USER pattern."""
        definition = """
        CREATE PROCEDURE get_user_data()
        BEGIN
            SELECT * FROM Users WHERE username = CURRENT_USER();
        END
        """
        assert scanner_service._contains_authorization_logic(definition)

    def test_contains_authorization_logic_with_user_function(self, scanner_service):
        """Test detection of USER() function pattern."""
        definition = """
        CREATE PROCEDURE check_access()
        BEGIN
            IF USER() = 'admin@localhost' THEN
                SELECT 'Authorized';
            END IF;
        END
        """
        assert scanner_service._contains_authorization_logic(definition)

    def test_contains_authorization_logic_with_grant(self, scanner_service):
        """Test detection of GRANT statement."""
        definition = """
        CREATE PROCEDURE manage_permissions()
        BEGIN
            GRANT SELECT ON testdb.Employees TO 'hr_role'@'localhost';
        END
        """
        assert scanner_service._contains_authorization_logic(definition)

    def test_contains_authorization_logic_with_revoke(self, scanner_service):
        """Test detection of REVOKE statement."""
        definition = """
        CREATE PROCEDURE revoke_access()
        BEGIN
            REVOKE UPDATE ON testdb.Salaries FROM 'guest'@'%';
        END
        """
        assert scanner_service._contains_authorization_logic(definition)

    def test_contains_authorization_logic_with_role_check(self, scanner_service):
        """Test detection of role-based authorization."""
        definition = """
        CREATE PROCEDURE check_user_role()
        BEGIN
            DECLARE user_role VARCHAR(50);
            SELECT role INTO user_role FROM user_roles WHERE user = CURRENT_USER();
            IF user_role = 'ADMIN' THEN
                -- Allow operation
                SELECT 1;
            END IF;
        END
        """
        assert scanner_service._contains_authorization_logic(definition)

    def test_contains_authorization_logic_with_permission_check(self, scanner_service):
        """Test detection of permission-based checks."""
        definition = """
        CREATE FUNCTION has_permission(resource_name VARCHAR(100))
        RETURNS BOOLEAN
        BEGIN
            DECLARE has_perm BOOLEAN;
            SELECT COUNT(*) > 0 INTO has_perm
            FROM permissions
            WHERE user = CURRENT_USER() AND resource = resource_name;
            RETURN has_perm;
        END
        """
        assert scanner_service._contains_authorization_logic(definition)

    def test_contains_authorization_logic_with_security_definer(self, scanner_service):
        """Test detection of SECURITY DEFINER attribute."""
        definition = """
        CREATE DEFINER=`admin`@`localhost` PROCEDURE secure_operation()
        SQL SECURITY DEFINER
        BEGIN
            -- Privileged operation
            DELETE FROM audit_logs WHERE created_at < NOW() - INTERVAL 90 DAY;
        END
        """
        assert scanner_service._contains_authorization_logic(definition)

    def test_no_authorization_logic(self, scanner_service):
        """Test that regular procedures without auth logic are not detected."""
        definition = """
        CREATE PROCEDURE calculate_total(price DECIMAL(10,2), quantity INT)
        BEGIN
            SELECT price * quantity AS total;
        END
        """
        assert not scanner_service._contains_authorization_logic(definition)

    @patch("app.services.database_scanner_service.create_engine")
    def test_get_stored_procedures_mysql(self, mock_create_engine, scanner_service):
        """Test retrieving MySQL stored procedures."""
        # Mock engine and connection
        mock_engine = Mock()
        mock_conn = Mock()
        mock_result = Mock()

        # Mock procedure data
        mock_row1 = Mock()
        mock_row1.schema = "testdb"
        mock_row1.name = "check_user_permission"
        mock_row1.type = "PROCEDURE"
        mock_row1.definition = """
        BEGIN
            DECLARE user_role VARCHAR(50);
            SELECT role INTO user_role FROM user_roles WHERE user = CURRENT_USER();
            IF user_role = 'ADMIN' THEN
                SELECT 1 AS has_permission;
            END IF;
        END
        """

        mock_row2 = Mock()
        mock_row2.schema = "testdb"
        mock_row2.name = "get_user_data"
        mock_row2.type = "FUNCTION"
        mock_row2.definition = """
        BEGIN
            RETURN (SELECT data FROM user_data WHERE username = USER());
        END
        """

        mock_result.__iter__ = Mock(return_value=iter([mock_row1, mock_row2]))
        mock_conn.execute.return_value = mock_result
        mock_engine.connect.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = Mock(return_value=False)
        mock_create_engine.return_value = mock_engine

        procedures = scanner_service._get_stored_procedures(
            mock_engine,
            DatabaseType.MYSQL.value
        )

        assert len(procedures) == 2
        assert procedures[0]["schema"] == "testdb"
        assert procedures[0]["name"] == "check_user_permission"
        assert "CURRENT_USER" in procedures[0]["definition"]
        assert procedures[1]["name"] == "get_user_data"
        assert "USER()" in procedures[1]["definition"]

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

    def test_mysql_specific_authorization_patterns(self, scanner_service):
        """Test MySQL-specific authorization patterns."""
        # CURRENT_USER()
        assert scanner_service._contains_authorization_logic(
            "SELECT * FROM users WHERE name = CURRENT_USER()"
        )

        # USER() function
        assert scanner_service._contains_authorization_logic(
            "IF USER() LIKE 'admin%' THEN"
        )

        # GRANT statement
        assert scanner_service._contains_authorization_logic(
            "GRANT ALL PRIVILEGES ON mydb.* TO 'user'@'host'"
        )

        # REVOKE statement
        assert scanner_service._contains_authorization_logic(
            "REVOKE INSERT ON table1 FROM 'user'@'host'"
        )

        # SESSION_USER
        assert scanner_service._contains_authorization_logic(
            "SELECT * FROM users WHERE name = SESSION_USER"
        )

        # SECURITY DEFINER
        assert scanner_service._contains_authorization_logic(
            "CREATE PROCEDURE test SQL SECURITY DEFINER"
        )

        # SECURITY INVOKER
        assert scanner_service._contains_authorization_logic(
            "CREATE PROCEDURE test SQL SECURITY INVOKER"
        )

    @patch("app.services.database_scanner_service.create_engine")
    def test_mysql_query_structure(self, mock_create_engine, scanner_service):
        """Test that MySQL uses correct information_schema queries."""
        mock_engine = Mock()
        mock_conn = Mock()
        mock_result = Mock()
        mock_result.__iter__ = Mock(return_value=iter([]))

        mock_conn.execute.return_value = mock_result
        mock_engine.connect.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = Mock(return_value=False)
        mock_create_engine.return_value = mock_engine

        # Get procedures using MySQL catalog
        scanner_service._get_stored_procedures(mock_engine, DatabaseType.MYSQL.value)

        # Verify MySQL-specific query was executed
        call_args = mock_conn.execute.call_args[0][0]
        query_text = str(call_args)

        # MySQL uses information_schema.ROUTINES
        assert "information_schema" in query_text.lower() or "ROUTINES" in query_text

    def test_mariadb_compatibility(self, scanner_service):
        """Test that MariaDB-specific patterns are also detected."""
        # MariaDB uses same patterns as MySQL
        definition = """
        CREATE PROCEDURE check_admin()
        BEGIN
            DECLARE is_admin BOOLEAN;
            SELECT COUNT(*) > 0 INTO is_admin
            FROM mysql.user
            WHERE User = CURRENT_USER() AND Super_priv = 'Y';

            IF is_admin THEN
                SELECT 'Admin access granted';
            END IF;
        END
        """
        assert scanner_service._contains_authorization_logic(definition)
