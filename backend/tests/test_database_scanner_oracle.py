"""Tests for Oracle database stored procedure analysis."""
import json
from unittest.mock import Mock, patch

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.models.repository import DatabaseType, Repository, RepositoryType
from app.services.database_scanner_service import DatabaseScannerService


class TestOracleDatabaseScanner:
    """Test Oracle database stored procedure analysis."""

    @pytest.fixture
    def mock_repository(self):
        """Create a mock Oracle repository."""
        repo = Mock(spec=Repository)
        repo.id = 1
        repo.name = "Test Oracle DB"
        repo.repository_type = RepositoryType.DATABASE
        repo.connection_config = {
            "database_type": DatabaseType.ORACLE.value,
            "host": "oracle.example.com",
            "port": 1521,
            "database": "orcl",
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
                    "subject": "hr_role",
                    "resource": "EMPLOYEES table",
                    "action": "SELECT",
                    "conditions": "Only during business hours",
                    "description": "HR role can view employee records",
                }
            ])
            return service

    def test_build_oracle_connection_string(self, scanner_service, mock_repository):
        """Test building Oracle connection string with cx_oracle driver."""
        conn_str = scanner_service._build_connection_string(mock_repository)

        assert "oracle+cx_oracle" in conn_str
        assert "oracle.example.com:1521" in conn_str
        assert "orcl" in conn_str
        assert "testuser" in conn_str

    def test_contains_authorization_logic_with_authid_current_user(self, scanner_service):
        """Test detection of AUTHID CURRENT_USER pattern."""
        definition = """
        CREATE PROCEDURE check_user_permission
        AUTHID CURRENT_USER
        IS
        BEGIN
            IF USER IN ('ADMIN', 'MANAGER') THEN
                DBMS_OUTPUT.PUT_LINE('Authorized');
            END IF;
        END;
        """
        assert scanner_service._contains_authorization_logic(definition)

    def test_contains_authorization_logic_with_authid_definer(self, scanner_service):
        """Test detection of AUTHID DEFINER pattern."""
        definition = """
        CREATE FUNCTION can_access_table
        RETURN BOOLEAN
        AUTHID DEFINER
        IS
        BEGIN
            RETURN TRUE;
        END;
        """
        assert scanner_service._contains_authorization_logic(definition)

    def test_contains_authorization_logic_with_grant(self, scanner_service):
        """Test detection of GRANT statement."""
        definition = """
        CREATE PROCEDURE manage_permissions
        IS
        BEGIN
            EXECUTE IMMEDIATE 'GRANT SELECT ON EMPLOYEES TO hr_role';
        END;
        """
        assert scanner_service._contains_authorization_logic(definition)

    def test_contains_authorization_logic_with_revoke(self, scanner_service):
        """Test detection of REVOKE statement."""
        definition = """
        CREATE PROCEDURE revoke_access
        IS
        BEGIN
            EXECUTE IMMEDIATE 'REVOKE UPDATE ON SALARIES FROM general_users';
        END;
        """
        assert scanner_service._contains_authorization_logic(definition)

    def test_contains_authorization_logic_with_current_user(self, scanner_service):
        """Test detection of CURRENT_USER pattern."""
        definition = """
        CREATE PROCEDURE get_user_data
        IS
            v_user VARCHAR2(100);
        BEGIN
            v_user := USER;
            SELECT * FROM users WHERE username = USER;
        END;
        """
        assert scanner_service._contains_authorization_logic(definition)

    def test_contains_authorization_logic_with_session_user(self, scanner_service):
        """Test detection of SESSION_USER pattern."""
        definition = """
        CREATE FUNCTION get_current_session
        RETURN VARCHAR2
        IS
        BEGIN
            RETURN SESSION_USER;
        END;
        """
        assert scanner_service._contains_authorization_logic(definition)

    def test_contains_authorization_logic_with_role_check(self, scanner_service):
        """Test detection of ROLE-based authorization."""
        definition = """
        CREATE PROCEDURE check_role_membership
        IS
            v_has_role NUMBER;
        BEGIN
            SELECT COUNT(*) INTO v_has_role
            FROM session_roles
            WHERE role = 'DBA';
        END;
        """
        assert scanner_service._contains_authorization_logic(definition)

    def test_no_authorization_logic(self, scanner_service):
        """Test that regular procedures without auth logic are not detected."""
        definition = """
        CREATE PROCEDURE calculate_total(
            p_price IN NUMBER,
            p_quantity IN NUMBER,
            p_total OUT NUMBER
        )
        IS
        BEGIN
            p_total := p_price * p_quantity;
        END;
        """
        assert not scanner_service._contains_authorization_logic(definition)

    @patch("app.services.database_scanner_service.create_engine")
    def test_get_stored_procedures_oracle(self, mock_create_engine, scanner_service):
        """Test retrieving Oracle stored procedures."""
        # Mock engine and connection
        mock_engine = Mock()
        mock_conn = Mock()
        mock_result = Mock()

        # Mock procedure data
        mock_row1 = Mock()
        mock_row1.schema = "HR"
        mock_row1.name = "CHECK_USER_PERMISSION"
        mock_row1.type = "PROCEDURE"
        mock_row1.definition = """
        CREATE OR REPLACE PROCEDURE check_user_permission
        AUTHID CURRENT_USER
        IS
            v_has_role NUMBER;
        BEGIN
            SELECT COUNT(*) INTO v_has_role
            FROM session_roles
            WHERE role = 'HR_MANAGER';

            IF v_has_role > 0 THEN
                DBMS_OUTPUT.PUT_LINE('Access Granted');
            END IF;
        END;
        """

        mock_row2 = Mock()
        mock_row2.schema = "HR"
        mock_row2.name = "GET_USER_ROLES"
        mock_row2.type = "FUNCTION"
        mock_row2.definition = """
        CREATE OR REPLACE FUNCTION get_user_roles
        RETURN SYS_REFCURSOR
        AUTHID DEFINER
        IS
            v_cursor SYS_REFCURSOR;
        BEGIN
            OPEN v_cursor FOR
                SELECT role_name FROM dba_role_privs
                WHERE grantee = USER;
            RETURN v_cursor;
        END;
        """

        mock_row3 = Mock()
        mock_row3.schema = "SECURITY"
        mock_row3.name = "EMPLOYEE_SECURITY_PKG"
        mock_row3.type = "PACKAGE BODY"
        mock_row3.definition = """
        CREATE OR REPLACE PACKAGE BODY employee_security_pkg IS
            FUNCTION check_vpd_policy(
                schema_var IN VARCHAR2,
                table_var IN VARCHAR2
            )
            RETURN VARCHAR2
            IS
            BEGIN
                IF USER IN ('HR_ADMIN', 'HR_MANAGER') THEN
                    RETURN '';
                ELSE
                    RETURN 'department_id = (SELECT department_id FROM employees WHERE employee_id = SYS_CONTEXT(''USERENV'', ''SESSION_USER''))';
                END IF;
            END;
        END;
        """

        mock_result.__iter__ = Mock(return_value=iter([mock_row1, mock_row2, mock_row3]))
        mock_conn.execute.return_value = mock_result
        mock_engine.connect.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = Mock(return_value=False)
        mock_create_engine.return_value = mock_engine

        procedures = scanner_service._get_stored_procedures(
            mock_engine,
            DatabaseType.ORACLE.value
        )

        assert len(procedures) == 3
        assert procedures[0]["schema"] == "HR"
        assert procedures[0]["name"] == "CHECK_USER_PERMISSION"
        assert procedures[0]["type"] == "PROCEDURE"
        assert "AUTHID CURRENT_USER" in procedures[0]["definition"]

        assert procedures[1]["name"] == "GET_USER_ROLES"
        assert procedures[1]["type"] == "FUNCTION"
        assert "AUTHID DEFINER" in procedures[1]["definition"]

        assert procedures[2]["name"] == "EMPLOYEE_SECURITY_PKG"
        assert procedures[2]["type"] == "PACKAGE BODY"
        assert "VPD" in procedures[2]["definition"].upper()

    @pytest.mark.asyncio
    async def test_scan_database_connection_error(self, scanner_service, mock_repository):
        """Test handling of database connection errors."""
        with patch("app.services.database_scanner_service.create_engine") as mock_create:
            mock_create.side_effect = SQLAlchemyError("TNS: could not resolve connect identifier")

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

    def test_oracle_specific_authorization_patterns(self, scanner_service):
        """Test Oracle-specific authorization patterns."""
        # AUTHID CURRENT_USER
        assert scanner_service._contains_authorization_logic(
            "CREATE PROCEDURE test AUTHID CURRENT_USER IS BEGIN NULL; END;"
        )

        # AUTHID DEFINER
        assert scanner_service._contains_authorization_logic(
            "CREATE FUNCTION test RETURN NUMBER AUTHID DEFINER IS BEGIN RETURN 1; END;"
        )

        # GRANT with EXECUTE IMMEDIATE
        assert scanner_service._contains_authorization_logic(
            "EXECUTE IMMEDIATE 'GRANT SELECT ON employees TO hr_role';"
        )

        # session_roles table check
        assert scanner_service._contains_authorization_logic(
            "SELECT * FROM session_roles WHERE role = 'ADMIN'"
        )

        # USER function with comparison
        assert scanner_service._contains_authorization_logic(
            "IF USER = 'ADMIN' THEN GRANT ALL PRIVILEGES; END IF;"
        )

        # USER function in WHERE clause
        assert scanner_service._contains_authorization_logic(
            "SELECT * FROM users WHERE username = USER"
        )

    @patch("app.services.database_scanner_service.create_engine")
    def test_oracle_query_structure(self, mock_create_engine, scanner_service):
        """Test that Oracle uses correct system catalog queries."""
        mock_engine = Mock()
        mock_conn = Mock()
        mock_result = Mock()
        mock_result.__iter__ = Mock(return_value=iter([]))

        mock_conn.execute.return_value = mock_result
        mock_engine.connect.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = Mock(return_value=False)
        mock_create_engine.return_value = mock_engine

        # Get procedures using Oracle catalog
        scanner_service._get_stored_procedures(mock_engine, DatabaseType.ORACLE.value)

        # Verify Oracle-specific query was executed
        call_args = mock_conn.execute.call_args[0][0]
        query_text = str(call_args)

        # Oracle uses ALL_SOURCE catalog view
        assert "all_source" in query_text.lower()
        assert "listagg" in query_text.lower()  # Oracle string aggregation function
        assert "procedure" in query_text.lower() or "function" in query_text.lower()

    def test_oracle_vpd_policy_detection(self, scanner_service):
        """Test detection of Virtual Private Database (VPD) policies."""
        # Test SYS_CONTEXT pattern detection
        sys_context_definition = """
        CREATE OR REPLACE FUNCTION vpd_security_policy(
            schema_var IN VARCHAR2,
            table_var IN VARCHAR2
        )
        RETURN VARCHAR2
        IS
        BEGIN
            RETURN 'department_id = SYS_CONTEXT(''DEPT_CTX'', ''DEPT_ID'')';
        END;
        """
        assert scanner_service._contains_authorization_logic(sys_context_definition)

        # Test DBMS_RLS pattern detection
        dbms_rls_setup = """
        BEGIN
            DBMS_RLS.ADD_POLICY(
                object_schema => 'HR',
                object_name => 'EMPLOYEES',
                policy_name => 'emp_security_policy',
                function_schema => 'SECURITY',
                policy_function => 'vpd_security_policy'
            );
        END;
        """
        assert scanner_service._contains_authorization_logic(dbms_rls_setup)

    def test_oracle_security_definer(self, scanner_service):
        """Test detection of SECURITY DEFINER pattern in Oracle."""
        definition = """
        CREATE PROCEDURE secure_proc
        AUTHID DEFINER  -- SECURITY DEFINER equivalent in Oracle
        IS
        BEGIN
            DELETE FROM audit_log WHERE log_date < SYSDATE - 90;
        END;
        """
        assert scanner_service._contains_authorization_logic(definition)

    def test_oracle_role_based_access(self, scanner_service):
        """Test detection of role-based access control in PL/SQL."""
        definition = """
        CREATE PROCEDURE check_role_access
        IS
            v_count NUMBER;
        BEGIN
            SELECT COUNT(*)
            INTO v_count
            FROM session_roles
            WHERE role IN ('DBA', 'ADMIN', 'MANAGER');

            IF v_count = 0 THEN
                RAISE_APPLICATION_ERROR(-20001, 'Insufficient privileges');
            END IF;
        END;
        """
        assert scanner_service._contains_authorization_logic(definition)

    def test_oracle_package_body_detection(self, scanner_service):
        """Test detection of authorization in Oracle package bodies."""
        definition = """
        CREATE OR REPLACE PACKAGE BODY security_pkg IS
            FUNCTION check_vpd_policy(
                schema_var IN VARCHAR2,
                table_var IN VARCHAR2
            )
            RETURN VARCHAR2
            IS
            BEGIN
                IF USER IN ('HR_ADMIN', 'HR_MANAGER') THEN
                    RETURN '';
                ELSE
                    RETURN 'department_id = SYS_CONTEXT(''USERENV'', ''SESSION_USER'')';
                END IF;
            END;
        END;
        """
        # Should match on USER IN and SYS_CONTEXT patterns
        assert scanner_service._contains_authorization_logic(definition)
