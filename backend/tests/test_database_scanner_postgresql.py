"""Tests for PostgreSQL stored procedure analysis."""
import json
from unittest.mock import MagicMock, Mock, patch

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.models.repository import DatabaseType, Repository, RepositoryType
from app.services.database_scanner_service import DatabaseScannerService


class TestPostgreSQLDatabaseScanner:
    """Test PostgreSQL stored procedure analysis."""

    @pytest.fixture
    def mock_repository(self):
        """Create a mock PostgreSQL repository."""
        repo = Mock(spec=Repository)
        repo.id = 1
        repo.name = "Test PostgreSQL DB"
        repo.repository_type = RepositoryType.DATABASE
        repo.connection_config = {
            "database_type": DatabaseType.POSTGRESQL.value,
            "host": "localhost",
            "port": 5432,
            "database": "testdb",
            "username": "testuser",
            "password": "testpass",
        }
        return repo

    @pytest.fixture
    def scanner_service(self):
        """Create database scanner service instance."""
        with patch("app.services.database_scanner_service.get_llm_provider"):
            service = DatabaseScannerService()
            service.llm_provider = Mock()
            return service

    def test_build_postgresql_connection_string(self, scanner_service, mock_repository):
        """Test building PostgreSQL connection string."""
        conn_str = scanner_service._build_connection_string(mock_repository)
        assert "postgresql+psycopg2" in conn_str
        assert "localhost:5432" in conn_str
        assert "testdb" in conn_str
        assert "testuser" in conn_str

    def test_contains_authorization_logic_with_pg_has_role(self, scanner_service):
        """Test detection of pg_has_role authorization pattern."""
        definition = """
        CREATE OR REPLACE FUNCTION check_user_permission()
        RETURNS boolean AS $$
        BEGIN
            IF pg_has_role(current_user, 'admin', 'member') THEN
                RETURN true;
            END IF;
            RETURN false;
        END;
        $$ LANGUAGE plpgsql;
        """
        assert scanner_service._contains_authorization_logic(definition)

    def test_contains_authorization_logic_with_rls_policy(self, scanner_service):
        """Test detection of Row-Level Security policy."""
        definition = """
        CREATE POLICY tenant_isolation ON users
            USING (tenant_id = current_setting('app.tenant_id')::uuid);
        """
        assert scanner_service._contains_authorization_logic(definition)

    def test_contains_authorization_logic_with_grant(self, scanner_service):
        """Test detection of GRANT statement."""
        definition = """
        CREATE OR REPLACE FUNCTION grant_permissions()
        RETURNS void AS $$
        BEGIN
            GRANT SELECT ON TABLE sensitive_data TO read_only_role;
        END;
        $$ LANGUAGE plpgsql;
        """
        assert scanner_service._contains_authorization_logic(definition)

    def test_contains_authorization_logic_with_has_table_privilege(self, scanner_service):
        """Test detection of has_table_privilege check."""
        definition = """
        CREATE OR REPLACE FUNCTION can_access_table(table_name text)
        RETURNS boolean AS $$
        BEGIN
            RETURN has_table_privilege(current_user, table_name, 'SELECT');
        END;
        $$ LANGUAGE plpgsql;
        """
        assert scanner_service._contains_authorization_logic(definition)

    def test_no_authorization_logic(self, scanner_service):
        """Test that regular functions without auth logic are not detected."""
        definition = """
        CREATE OR REPLACE FUNCTION calculate_total(a integer, b integer)
        RETURNS integer AS $$
        BEGIN
            RETURN a + b;
        END;
        $$ LANGUAGE plpgsql;
        """
        assert not scanner_service._contains_authorization_logic(definition)

    @patch("app.services.database_scanner_service.create_engine")
    def test_get_stored_procedures_postgresql(self, mock_create_engine, scanner_service):
        """Test retrieving PostgreSQL stored procedures."""
        # Mock engine and connection
        mock_engine = Mock()
        mock_conn = Mock()
        mock_result = Mock()

        # Mock procedure data
        mock_row = Mock()
        mock_row.schema = "public"
        mock_row.name = "check_user_access"
        mock_row.definition = "CREATE OR REPLACE FUNCTION check_user_access()..."
        mock_row.arguments = "user_id integer"

        mock_result.__iter__ = Mock(return_value=iter([mock_row]))
        mock_conn.execute.return_value = mock_result
        mock_engine.connect.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = Mock(return_value=False)
        mock_create_engine.return_value = mock_engine

        procedures = scanner_service._get_stored_procedures(
            mock_engine,
            DatabaseType.POSTGRESQL.value
        )

        assert len(procedures) == 1
        assert procedures[0]["schema"] == "public"
        assert procedures[0]["name"] == "check_user_access"
        assert "CREATE OR REPLACE FUNCTION" in procedures[0]["definition"]

    @patch("app.services.similarity_service.SimilarityService")
    def test_extract_policies_from_procedure_with_role_check(self, mock_similarity, scanner_service, mock_repository):
        """Test policy extraction from procedure with role-based authorization."""
        procedure = {
            "schema": "public",
            "name": "approve_expense",
            "definition": """
                CREATE OR REPLACE FUNCTION approve_expense(expense_id integer)
                RETURNS void AS $$
                BEGIN
                    IF pg_has_role(current_user, 'manager', 'member') THEN
                        UPDATE expenses SET status = 'approved' WHERE id = expense_id;
                    ELSE
                        RAISE EXCEPTION 'Unauthorized: Only managers can approve expenses';
                    END IF;
                END;
                $$ LANGUAGE plpgsql;
            """,
            "type": "FUNCTION",
        }

        # Mock LLM response
        llm_response = json.dumps([
            {
                "subject": "manager role",
                "resource": "expenses table",
                "action": "UPDATE (approve)",
                "conditions": "User must be member of 'manager' role",
                "description": "Only managers can approve expenses by updating status to approved",
            }
        ])
        scanner_service.llm_provider.create_message.return_value = llm_response

        policies = scanner_service._extract_policies_from_procedure(
            procedure=procedure,
            repository_id=mock_repository.id,
            tenant_id="test-tenant",
            db_type=DatabaseType.POSTGRESQL.value,
        )

        assert len(policies) == 1
        policy = policies[0]
        assert "manager" in policy.subject.lower()
        assert "expenses" in policy.resource.lower()
        assert "UPDATE" in policy.action or "approve" in policy.action.lower()
        assert len(policy.evidence) == 1
        assert policy.evidence[0].file_path == "public.approve_expense"

    @patch("app.services.similarity_service.SimilarityService")
    def test_extract_policies_from_procedure_with_rls(self, mock_similarity, scanner_service, mock_repository):
        """Test policy extraction from Row-Level Security policy."""
        procedure = {
            "schema": "public",
            "name": "tenant_isolation_policy",
            "definition": """
                CREATE POLICY tenant_isolation ON sensitive_data
                    USING (tenant_id = current_setting('app.tenant_id')::uuid);
            """,
            "type": "POLICY",
        }

        # Mock LLM response
        llm_response = json.dumps([
            {
                "subject": "tenant users (filtered by tenant_id)",
                "resource": "sensitive_data table",
                "action": "SELECT, UPDATE, DELETE",
                "conditions": "Row tenant_id must match current session's tenant_id",
                "description": "Row-Level Security policy ensuring users can only access data belonging to their tenant",
            }
        ])
        scanner_service.llm_provider.create_message.return_value = llm_response

        policies = scanner_service._extract_policies_from_procedure(
            procedure=procedure,
            repository_id=mock_repository.id,
            tenant_id="test-tenant",
            db_type=DatabaseType.POSTGRESQL.value,
        )

        assert len(policies) == 1
        policy = policies[0]
        assert "tenant" in policy.subject.lower()
        assert "sensitive_data" in policy.resource.lower()
        assert "tenant_id" in policy.conditions.lower()

    @patch("app.services.similarity_service.SimilarityService")
    def test_extract_policies_handles_llm_json_in_markdown(self, mock_similarity, scanner_service, mock_repository):
        """Test that policy extraction handles JSON in markdown code blocks."""
        procedure = {
            "schema": "public",
            "name": "test_func",
            "definition": "CREATE FUNCTION test_func() RETURNS void AS $$ BEGIN END; $$ LANGUAGE plpgsql;",
            "type": "FUNCTION",
        }

        # Mock LLM response with markdown code block
        llm_response = """Here are the policies I found:

```json
[
    {
        "subject": "admin users",
        "resource": "test table",
        "action": "SELECT",
        "conditions": "always",
        "description": "Test policy"
    }
]
```
"""
        scanner_service.llm_provider.create_message.return_value = llm_response

        policies = scanner_service._extract_policies_from_procedure(
            procedure=procedure,
            repository_id=mock_repository.id,
            tenant_id="test-tenant",
            db_type=DatabaseType.POSTGRESQL.value,
        )

        assert len(policies) == 1
        assert policies[0].subject == "admin users"

    def test_extract_policies_handles_no_policies_found(self, scanner_service, mock_repository):
        """Test that extraction handles empty policy list correctly."""
        procedure = {
            "schema": "public",
            "name": "no_auth_func",
            "definition": "CREATE FUNCTION no_auth_func() RETURNS integer AS $$ BEGIN RETURN 42; END; $$ LANGUAGE plpgsql;",
            "type": "FUNCTION",
        }

        # Mock LLM response with empty array
        llm_response = "[]"
        scanner_service.llm_provider.create_message.return_value = llm_response

        policies = scanner_service._extract_policies_from_procedure(
            procedure=procedure,
            repository_id=mock_repository.id,
            tenant_id="test-tenant",
            db_type=DatabaseType.POSTGRESQL.value,
        )

        assert len(policies) == 0

    @pytest.mark.asyncio
    @patch("app.services.similarity_service.SimilarityService")
    @patch("app.services.database_scanner_service.create_engine")
    async def test_scan_database_end_to_end(
        self, mock_create_engine, mock_similarity, scanner_service, mock_repository
    ):
        """Test complete database scan workflow for PostgreSQL."""
        # Mock engine and connection
        mock_engine = Mock()
        mock_conn = Mock()
        mock_result = Mock()

        # Mock procedure with authorization logic
        mock_row = Mock()
        mock_row.schema = "public"
        mock_row.name = "check_permission"
        mock_row.definition = """
            CREATE OR REPLACE FUNCTION check_permission(user_id integer, resource_id integer)
            RETURNS boolean AS $$
            BEGIN
                IF pg_has_role(current_user, 'admin', 'member') THEN
                    RETURN true;
                END IF;
                RETURN false;
            END;
            $$ LANGUAGE plpgsql;
        """
        mock_row.arguments = "user_id integer, resource_id integer"

        mock_result.__iter__ = Mock(return_value=iter([mock_row]))
        mock_conn.execute.return_value = mock_result
        mock_engine.connect.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = Mock(return_value=False)
        mock_engine.dispose = Mock()
        mock_create_engine.return_value = mock_engine

        # Mock LLM response
        llm_response = json.dumps([
            {
                "subject": "admin role members",
                "resource": "resource access",
                "action": "CHECK PERMISSION",
                "conditions": "User must be member of admin role",
                "description": "Admins can check permissions for any resource",
            }
        ])
        scanner_service.llm_provider.create_message.return_value = llm_response

        # Run scan
        result = await scanner_service.scan_database(
            repository=mock_repository,
            tenant_id="test-tenant",
        )

        # Verify results
        assert result["total_procedures"] == 1
        assert result["procedures_scanned"] == 1  # Has authorization logic
        assert result["policies_extracted"] == 1
        assert len(result["policies"]) == 1

        policy = result["policies"][0]
        assert "admin" in policy.subject.lower()
        assert policy.source_type.value == "database"
        assert policy.repository_id == mock_repository.id
        assert policy.tenant_id == "test-tenant"

        # Verify engine was disposed
        mock_engine.dispose.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.services.database_scanner_service.create_engine")
    async def test_scan_database_handles_connection_error(
        self, mock_create_engine, scanner_service, mock_repository
    ):
        """Test that scan handles database connection errors gracefully."""
        # Mock connection failure
        mock_create_engine.side_effect = SQLAlchemyError("Connection refused")

        with pytest.raises(SQLAlchemyError):
            await scanner_service.scan_database(
                repository=mock_repository,
                tenant_id="test-tenant",
            )

    def test_postgresql_specific_patterns(self, scanner_service):
        """Test PostgreSQL-specific authorization patterns are detected."""
        test_cases = [
            ("has_table_privilege(current_user, 'users', 'SELECT')", True),
            ("has_column_privilege(current_user, 'users', 'email', 'SELECT')", True),
            ("pg_has_role(current_user, 'admin', 'member')", True),
            ("current_user = 'admin'", True),
            ("session_user != 'guest'", True),
            ("CREATE POLICY tenant_policy ON data USING (tenant_id = current_tenant())", True),
            ("ALTER POLICY tenant_policy ON data RENAME TO new_policy", True),
            ("GRANT SELECT ON TABLE users TO read_role", True),
            ("REVOKE INSERT ON TABLE users FROM write_role", True),
            ("regular SQL without auth", False),
            ("SELECT * FROM users WHERE active = true", False),
        ]

        for definition, expected in test_cases:
            result = scanner_service._contains_authorization_logic(definition)
            assert result == expected, f"Failed for: {definition}"
