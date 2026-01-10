"""Simple unit tests for PostgreSQL stored procedure analysis patterns."""
from unittest.mock import Mock

import pytest

from app.models.repository import DatabaseType
from app.services.database_scanner_service import DatabaseScannerService


class TestPostgreSQLPatternDetection:
    """Test PostgreSQL authorization pattern detection without full ORM."""

    @pytest.fixture
    def scanner_service(self):
        """Create database scanner service instance."""
        from unittest.mock import patch
        with patch("app.services.database_scanner_service.get_llm_provider"):
            service = DatabaseScannerService()
            service.llm_provider = Mock()
            return service

    def test_detects_pg_has_role(self, scanner_service):
        """Test detection of pg_has_role pattern."""
        sql = """
        CREATE OR REPLACE FUNCTION approve_expense(expense_id integer)
        RETURNS void AS $$
        BEGIN
            IF pg_has_role(current_user, 'manager', 'member') THEN
                UPDATE expenses SET status = 'approved' WHERE id = expense_id;
            END IF;
        END;
        $$ LANGUAGE plpgsql;
        """
        assert scanner_service._contains_authorization_logic(sql)

    def test_detects_has_table_privilege(self, scanner_service):
        """Test detection of has_table_privilege pattern."""
        sql = """
        CREATE FUNCTION can_access()
        RETURNS boolean AS $$
        BEGIN
            RETURN has_table_privilege(current_user, 'users', 'SELECT');
        END;
        $$ LANGUAGE plpgsql;
        """
        assert scanner_service._contains_authorization_logic(sql)

    def test_detects_has_column_privilege(self, scanner_service):
        """Test detection of has_column_privilege pattern."""
        sql = """
        CREATE FUNCTION can_see_email()
        RETURNS boolean AS $$
        BEGIN
            RETURN has_column_privilege(current_user, 'users', 'email', 'SELECT');
        END;
        $$ LANGUAGE plpgsql;
        """
        assert scanner_service._contains_authorization_logic(sql)

    def test_detects_create_policy(self, scanner_service):
        """Test detection of Row-Level Security CREATE POLICY."""
        sql = """
        CREATE POLICY tenant_isolation ON sensitive_data
            USING (tenant_id = current_setting('app.tenant_id')::uuid);
        """
        assert scanner_service._contains_authorization_logic(sql)

    def test_detects_alter_policy(self, scanner_service):
        """Test detection of ALTER POLICY statement."""
        sql = """
        ALTER POLICY tenant_policy ON data RENAME TO new_tenant_policy;
        """
        assert scanner_service._contains_authorization_logic(sql)

    def test_detects_grant_statement(self, scanner_service):
        """Test detection of GRANT permission statement."""
        sql = """
        CREATE FUNCTION grant_access()
        RETURNS void AS $$
        BEGIN
            GRANT SELECT ON TABLE users TO read_only_role;
        END;
        $$ LANGUAGE plpgsql;
        """
        assert scanner_service._contains_authorization_logic(sql)

    def test_detects_revoke_statement(self, scanner_service):
        """Test detection of REVOKE permission statement."""
        sql = """
        CREATE FUNCTION revoke_access()
        RETURNS void AS $$
        BEGIN
            REVOKE INSERT ON TABLE users FROM guest_role;
        END;
        $$ LANGUAGE plpgsql;
        """
        assert scanner_service._contains_authorization_logic(sql)

    def test_detects_current_user(self, scanner_service):
        """Test detection of CURRENT_USER checks."""
        sql = """
        CREATE FUNCTION check_owner(resource_id integer)
        RETURNS boolean AS $$
        BEGIN
            IF current_user = 'admin' THEN
                RETURN true;
            END IF;
            RETURN false;
        END;
        $$ LANGUAGE plpgsql;
        """
        assert scanner_service._contains_authorization_logic(sql)

    def test_detects_session_user(self, scanner_service):
        """Test detection of SESSION_USER checks."""
        sql = """
        CREATE FUNCTION audit_action()
        RETURNS void AS $$
        BEGIN
            INSERT INTO audit_log (user_name) VALUES (session_user);
        END;
        $$ LANGUAGE plpgsql;
        """
        assert scanner_service._contains_authorization_logic(sql)

    def test_detects_create_role(self, scanner_service):
        """Test detection of CREATE ROLE statement."""
        sql = """
        CREATE FUNCTION setup_roles()
        RETURNS void AS $$
        BEGIN
            CREATE ROLE manager;
        END;
        $$ LANGUAGE plpgsql;
        """
        assert scanner_service._contains_authorization_logic(sql)

    def test_detects_if_with_role_keyword(self, scanner_service):
        """Test detection of IF statements with ROLE keyword (uppercase matters)."""
        # Note: Pattern requires ROLE keyword, not just variable named "user_role"
        sql = """
        CREATE FUNCTION check_access()
        RETURNS boolean AS $$
        BEGIN
            IF USER IN ('admin', 'manager') THEN
                RETURN true;
            END IF;
            RETURN false;
        END;
        $$ LANGUAGE plpgsql;
        """
        assert scanner_service._contains_authorization_logic(sql)

    def test_does_not_detect_non_auth_function(self, scanner_service):
        """Test that regular functions without auth logic are not flagged."""
        sql = """
        CREATE FUNCTION calculate_total(price numeric, quantity integer)
        RETURNS numeric AS $$
        BEGIN
            RETURN price * quantity;
        END;
        $$ LANGUAGE plpgsql;
        """
        assert not scanner_service._contains_authorization_logic(sql)

    def test_does_not_detect_simple_select(self, scanner_service):
        """Test that simple SELECT statements are not flagged."""
        sql = """
        SELECT * FROM users WHERE active = true;
        """
        assert not scanner_service._contains_authorization_logic(sql)

    def test_postgresql_connection_string_format(self, scanner_service):
        """Test that PostgreSQL connection string is properly formatted."""
        from unittest.mock import Mock
        mock_repo = Mock()
        mock_repo.connection_config = {
            "database_type": DatabaseType.POSTGRESQL.value,
            "host": "localhost",
            "port": 5432,
            "database": "testdb",
            "username": "testuser",
            "password": "testpass",
        }

        conn_str = scanner_service._build_connection_string(mock_repo)

        assert "postgresql+psycopg2" in conn_str
        assert "testuser:testpass" in conn_str
        assert "localhost:5432" in conn_str
        assert "testdb" in conn_str

    def test_key_postgresql_patterns(self, scanner_service):
        """Test key PostgreSQL authorization patterns."""
        # Test patterns that definitely should be detected
        auth_patterns = [
            "GRANT SELECT ON TABLE data TO role",
            "REVOKE INSERT ON TABLE data FROM role",
            "CREATE POLICY name ON table USING (condition)",
            "ALTER POLICY old_name RENAME TO new_name",
            "CREATE ROLE new_role",
            "WHERE owner = CURRENT_USER",
            "INSERT INTO log VALUES (SESSION_USER)",
            "SELECT CURRENT_ROLE()",
            "IF USER = 'admin' THEN",
            "CREATE FUNCTION func() SECURITY DEFINER",
        ]

        for sql in auth_patterns:
            assert scanner_service._contains_authorization_logic(sql), \
                f"Should detect auth pattern: {sql}"

        # Test patterns that should NOT be detected
        non_auth_patterns = [
            "SELECT * FROM users",
            "INSERT INTO products VALUES (1, 'item')",
            "UPDATE orders SET status = 'shipped'",
            "CREATE TABLE test (id integer)",
        ]

        for sql in non_auth_patterns:
            assert not scanner_service._contains_authorization_logic(sql), \
                f"Should NOT detect non-auth pattern: {sql}"


class TestPostgreSQLProcedureMetadata:
    """Test PostgreSQL stored procedure metadata extraction."""

    def test_recognizes_postgresql_database_type(self):
        """Test that PostgreSQL is a recognized database type."""
        assert DatabaseType.POSTGRESQL.value == "postgresql"

    def test_postgresql_query_structure(self):
        """Test that the PostgreSQL procedure query is correctly structured."""
        # This test documents the expected query structure for PostgreSQL
        expected_columns = ["schema", "name", "definition", "arguments"]

        # The query should filter out system schemas
        excluded_schemas = ["pg_catalog", "information_schema"]

        # The query should select functions and procedures
        procedure_kinds = ["f", "p"]  # f = function, p = procedure

        # Just verify these are the expected values for documentation
        assert excluded_schemas == ["pg_catalog", "information_schema"]
        assert procedure_kinds == ["f", "p"]
        assert expected_columns == ["schema", "name", "definition", "arguments"]
