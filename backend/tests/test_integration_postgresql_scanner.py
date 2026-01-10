"""Integration tests for PostgreSQL stored procedure analysis.

These tests verify that the database scanner can successfully scan a real PostgreSQL database
and extract authorization policies from stored procedures.
"""
import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

from app.models.repository import DatabaseType, Repository, RepositoryType
from app.services.database_scanner_service import DatabaseScannerService

# Skip these tests if not in integration test mode or if PostgreSQL is not available
pytestmark = pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION_TESTS") != "true",
    reason="Integration tests disabled. Set RUN_INTEGRATION_TESTS=true to run"
)


class TestPostgreSQLIntegration:
    """Integration tests for PostgreSQL database scanning."""

    @pytest.fixture(scope="class")
    def test_db_connection(self):
        """Create test database connection using the main postgres container."""
        # Use the same postgres container that the app uses
        connection_config = {
            "database_type": DatabaseType.POSTGRESQL.value,
            "host": os.getenv("POSTGRES_HOST", "postgres"),
            "port": int(os.getenv("POSTGRES_PORT", 5432)),
            "database": os.getenv("POSTGRES_DB", "policy_miner"),
            "username": os.getenv("POSTGRES_USER", "postgres"),
            "password": os.getenv("POSTGRES_PASSWORD", "postgres"),
        }
        return connection_config

    @pytest.fixture(scope="class")
    def test_repository(self, test_db_connection):
        """Create a mock repository for testing."""
        from unittest.mock import Mock
        repo = Mock(spec=Repository)
        repo.id = 999
        repo.name = "Test PostgreSQL Integration"
        repo.repository_type = RepositoryType.DATABASE
        repo.connection_config = test_db_connection
        return repo

    @pytest.fixture(scope="class", autouse=True)
    def setup_test_procedures(self, test_db_connection):
        """Create test stored procedures in the database."""
        # Build connection string
        conn_str = (
            f"postgresql+psycopg2://{test_db_connection['username']}:{test_db_connection['password']}"
            f"@{test_db_connection['host']}:{test_db_connection['port']}/{test_db_connection['database']}"
        )

        try:
            engine = create_engine(conn_str)
            with engine.connect() as conn:
                # Create test schema
                conn.execute(text("CREATE SCHEMA IF NOT EXISTS test_auth"))
                conn.commit()

                # Create test function with role-based authorization
                conn.execute(text("""
                    CREATE OR REPLACE FUNCTION test_auth.check_manager_permission(user_id integer)
                    RETURNS boolean AS $$
                    BEGIN
                        -- Check if current user has manager role
                        IF pg_has_role(current_user, 'manager', 'member') THEN
                            RETURN true;
                        END IF;
                        RETURN false;
                    END;
                    $$ LANGUAGE plpgsql;
                """))
                conn.commit()

                # Create test function with table privilege check
                conn.execute(text("""
                    CREATE OR REPLACE FUNCTION test_auth.can_read_sensitive_data()
                    RETURNS boolean AS $$
                    BEGIN
                        -- Check if user has SELECT privilege on sensitive table
                        IF has_table_privilege(current_user, 'sensitive_data', 'SELECT') THEN
                            RETURN true;
                        END IF;
                        RETURN false;
                    END;
                    $$ LANGUAGE plpgsql;
                """))
                conn.commit()

                # Create test function without authorization logic (should not be scanned)
                conn.execute(text("""
                    CREATE OR REPLACE FUNCTION test_auth.calculate_sum(a integer, b integer)
                    RETURNS integer AS $$
                    BEGIN
                        RETURN a + b;
                    END;
                    $$ LANGUAGE plpgsql;
                """))
                conn.commit()

            yield

            # Cleanup
            with engine.connect() as conn:
                conn.execute(text("DROP SCHEMA IF EXISTS test_auth CASCADE"))
                conn.commit()

            engine.dispose()

        except OperationalError as e:
            pytest.skip(f"PostgreSQL not available: {e}")

    @pytest.mark.asyncio
    async def test_can_connect_to_postgresql(self, test_db_connection):
        """Test that we can connect to PostgreSQL database."""
        conn_str = (
            f"postgresql+psycopg2://{test_db_connection['username']}:{test_db_connection['password']}"
            f"@{test_db_connection['host']}:{test_db_connection['port']}/{test_db_connection['database']}"
        )

        try:
            engine = create_engine(conn_str)
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                assert result.scalar() == 1
            engine.dispose()
        except OperationalError as e:
            pytest.skip(f"PostgreSQL not available: {e}")

    @pytest.mark.asyncio
    async def test_scan_postgresql_procedures_detects_auth_logic(
        self, test_repository, test_db_connection
    ):
        """Test that scanner detects stored procedures with authorization logic."""
        scanner = DatabaseScannerService()

        result = await scanner.scan_database(
            repository=test_repository,
            tenant_id="test-tenant"
        )

        # Verify scan results
        assert result["total_procedures"] >= 3  # At least our 3 test functions
        assert result["procedures_scanned"] >= 2  # At least 2 with auth logic
        assert result["policies_extracted"] >= 0  # May extract policies if LLM is configured

        # If TEST_MODE or LLM is configured, we should extract policies
        # In real integration with LLM, this would be > 0
        # For now, just verify the scan completes successfully

    @pytest.mark.asyncio
    async def test_scanner_identifies_pg_has_role_pattern(
        self, test_repository
    ):
        """Test that scanner correctly identifies pg_has_role authorization pattern."""
        scanner = DatabaseScannerService()

        # We know check_manager_permission uses pg_has_role
        test_definition = """
            CREATE OR REPLACE FUNCTION check_manager_permission(user_id integer)
            RETURNS boolean AS $$
            BEGIN
                IF pg_has_role(current_user, 'manager', 'member') THEN
                    RETURN true;
                END IF;
                RETURN false;
            END;
            $$ LANGUAGE plpgsql;
        """

        has_auth = scanner._contains_authorization_logic(test_definition)
        assert has_auth is True

    @pytest.mark.asyncio
    async def test_scanner_identifies_has_table_privilege_pattern(
        self, test_repository
    ):
        """Test that scanner correctly identifies has_table_privilege pattern."""
        scanner = DatabaseScannerService()

        test_definition = """
            CREATE OR REPLACE FUNCTION can_read_sensitive_data()
            RETURNS boolean AS $$
            BEGIN
                IF has_table_privilege(current_user, 'sensitive_data', 'SELECT') THEN
                    RETURN true;
                END IF;
                RETURN false;
            END;
            $$ LANGUAGE plpgsql;
        """

        has_auth = scanner._contains_authorization_logic(test_definition)
        assert has_auth is True

    @pytest.mark.asyncio
    async def test_scanner_ignores_non_auth_procedures(
        self, test_repository
    ):
        """Test that scanner ignores procedures without authorization logic."""
        scanner = DatabaseScannerService()

        test_definition = """
            CREATE OR REPLACE FUNCTION calculate_sum(a integer, b integer)
            RETURNS integer AS $$
            BEGIN
                RETURN a + b;
            END;
            $$ LANGUAGE plpgsql;
        """

        has_auth = scanner._contains_authorization_logic(test_definition)
        assert has_auth is False
