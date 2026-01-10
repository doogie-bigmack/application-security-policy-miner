"""Database stored procedure scanner service."""
import re
from typing import Any

import structlog
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from app.models.policy import Evidence, Policy, PolicyStatus, SourceType
from app.models.repository import DatabaseType, Repository
from app.services.llm_provider import get_llm_provider
from app.services.risk_scoring_service import RiskScoringService

logger = structlog.get_logger()

# Authorization patterns in SQL
SQL_AUTH_PATTERNS = [
    r"GRANT\s+",
    r"REVOKE\s+",
    r"CREATE\s+POLICY",
    r"ALTER\s+POLICY",
    r"CREATE\s+ROLE",
    r"IF\s+.*\bROLE\b",
    r"IF\s+.*\bUSER\b",
    r"IF\s+.*\bPERMISSION\b",
    r"CURRENT_ROLE",
    r"CURRENT_USER",
    r"SESSION_USER",
    r"SECURITY\s+DEFINER",
    r"AUTHID\s+CURRENT_USER",
    r"AUTHID\s+DEFINER",
    r"HAS_PERMS_BY_NAME",
    r"IS_MEMBER",
    r"IS_ROLEMEMBER",
    r"pg_has_role",
    r"has_table_privilege",
    r"has_column_privilege",
    # Oracle-specific patterns (matched against uppercase text)
    r"\bUSER\s*=",  # Oracle USER function comparison
    r"\bUSER\s+IN\s*\(",  # Oracle USER IN clause
    r":=\s*USER",  # Oracle USER assignment
    r"WHERE\s+.*\bUSER\b",  # USER in WHERE clause
    r"SESSION_ROLES",  # Oracle session_roles table
    r"DBA_ROLE_PRIVS",  # Oracle DBA role privileges view
    r"DBMS_RLS",  # Oracle Row-Level Security package
    r"SYS_CONTEXT",  # Oracle system context function
    # MySQL/MariaDB-specific patterns
    r"\bUSER\s*\(\)",  # MySQL USER() function
    r"CURRENT_USER\s*\(\)",  # MySQL CURRENT_USER() function
    r"SQL\s+SECURITY\s+DEFINER",  # MySQL security context
    r"SQL\s+SECURITY\s+INVOKER",  # MySQL security context
]


class DatabaseScannerService:
    """Service for scanning database stored procedures and extracting authorization policies."""

    def __init__(self):
        """Initialize database scanner service."""
        self.llm_provider = get_llm_provider()
        self.risk_scorer = RiskScoringService()

    def _build_connection_string(self, repository: Repository) -> str:
        """Build database connection string from repository config.

        Args:
            repository: Repository object with database connection config

        Returns:
            Connection string for SQLAlchemy

        Raises:
            ValueError: If required connection config is missing
        """
        config = repository.connection_config or {}
        db_type = config.get("database_type")
        host = config.get("host")
        port = config.get("port")
        database = config.get("database")
        username = config.get("username")
        password = config.get("password")

        if not all([db_type, host, database, username, password]):
            raise ValueError("Missing required database connection parameters")

        # Map database types to SQLAlchemy drivers
        driver_map = {
            DatabaseType.POSTGRESQL.value: "postgresql+psycopg2",
            DatabaseType.MYSQL.value: "mysql+pymysql",
            DatabaseType.SQLSERVER.value: "mssql+pyodbc",
            DatabaseType.ORACLE.value: "oracle+cx_oracle",
        }

        driver = driver_map.get(db_type)
        if not driver:
            raise ValueError(f"Unsupported database type: {db_type}")

        # Build connection string based on database type
        if db_type == DatabaseType.SQLSERVER.value:
            # SQL Server requires special ODBC driver specification
            return f"{driver}://{username}:{password}@{host}:{port}/{database}?driver=ODBC+Driver+17+for+SQL+Server"
        else:
            return f"{driver}://{username}:{password}@{host}:{port}/{database}"

    def _get_stored_procedures(self, engine: Any, db_type: str) -> list[dict[str, Any]]:
        """Retrieve list of stored procedures from database.

        Args:
            engine: SQLAlchemy engine
            db_type: Database type

        Returns:
            List of stored procedures with metadata
        """
        procedures: list[dict[str, Any]] = []

        with engine.connect() as conn:
            if db_type == DatabaseType.POSTGRESQL.value:
                # PostgreSQL: Query pg_catalog for functions
                query = text("""
                    SELECT
                        n.nspname as schema,
                        p.proname as name,
                        pg_get_functiondef(p.oid) as definition,
                        pg_get_function_arguments(p.oid) as arguments
                    FROM pg_proc p
                    JOIN pg_namespace n ON p.pronamespace = n.oid
                    WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
                    AND p.prokind IN ('f', 'p')  -- Functions and procedures
                    ORDER BY n.nspname, p.proname
                """)

            elif db_type == DatabaseType.MYSQL.value:
                # MySQL: Query information_schema for routines
                query = text("""
                    SELECT
                        ROUTINE_SCHEMA as schema,
                        ROUTINE_NAME as name,
                        ROUTINE_DEFINITION as definition,
                        ROUTINE_TYPE as type
                    FROM information_schema.ROUTINES
                    WHERE ROUTINE_SCHEMA NOT IN ('mysql', 'information_schema', 'performance_schema', 'sys')
                    ORDER BY ROUTINE_SCHEMA, ROUTINE_NAME
                """)

            elif db_type == DatabaseType.SQLSERVER.value:
                # SQL Server: Query sys.sql_modules for procedures
                query = text("""
                    SELECT
                        SCHEMA_NAME(o.schema_id) as schema,
                        o.name as name,
                        m.definition as definition
                    FROM sys.sql_modules m
                    JOIN sys.objects o ON m.object_id = o.object_id
                    WHERE o.type IN ('P', 'FN', 'IF', 'TF')  -- Procedures and functions
                    ORDER BY schema, name
                """)

            elif db_type == DatabaseType.ORACLE.value:
                # Oracle: Query ALL_SOURCE for procedures
                query = text("""
                    SELECT
                        owner as schema,
                        name as name,
                        type as type,
                        LISTAGG(text, '') WITHIN GROUP (ORDER BY line) as definition
                    FROM all_source
                    WHERE owner NOT IN ('SYS', 'SYSTEM', 'DBSNMP', 'SYSMAN')
                    AND type IN ('PROCEDURE', 'FUNCTION', 'PACKAGE BODY')
                    GROUP BY owner, name, type
                    ORDER BY owner, name
                """)
            else:
                return procedures

            result = conn.execute(query)
            for row in result:
                procedures.append({
                    "schema": row.schema,
                    "name": row.name,
                    "definition": row.definition or "",
                    "type": getattr(row, "type", "PROCEDURE"),
                })

        return procedures

    def _contains_authorization_logic(self, definition: str) -> bool:
        """Check if stored procedure contains authorization logic.

        Args:
            definition: Stored procedure definition

        Returns:
            True if authorization patterns found
        """
        if not definition:
            return False

        definition_upper = definition.upper()

        for pattern in SQL_AUTH_PATTERNS:
            if re.search(pattern, definition_upper):
                return True

        return False

    def _extract_policies_from_procedure(
        self,
        procedure: dict[str, Any],
        repository_id: int,
        tenant_id: str | None,
        db_type: str,
    ) -> list[Policy]:
        """Extract authorization policies from stored procedure using LLM.

        Args:
            procedure: Stored procedure metadata and definition
            repository_id: Repository ID
            tenant_id: Tenant ID
            db_type: Database type

        Returns:
            List of extracted Policy objects
        """
        schema = procedure["schema"]
        name = procedure["name"]
        definition = procedure["definition"]
        proc_type = procedure.get("type", "PROCEDURE")

        logger.info(
            "extracting_policies_from_procedure",
            schema=schema,
            name=name,
            type=proc_type,
            db_type=db_type,
        )

        # Build prompt for LLM
        prompt = f"""You are analyzing a {db_type} {proc_type} for authorization and access control logic.

Database Type: {db_type}
Schema: {schema}
Name: {name}
Type: {proc_type}

Stored Procedure Definition:
```sql
{definition[:10000]}  # Limit to first 10K chars
```

Extract ALL authorization and access control policies from this stored procedure.
For EACH policy, identify:

1. WHO (Subject): Which user, role, or group has access?
2. WHAT (Resource): What database object, table, or data is being protected?
3. HOW (Action): What operation is allowed/denied (SELECT, INSERT, UPDATE, DELETE, EXECUTE, etc.)?
4. WHEN (Conditions): Under what conditions does this policy apply?

Return a JSON array of policies in this exact format:
```json
[
  {{
    "subject": "WHO can access (role, user, group)",
    "resource": "WHAT is being protected (table, view, column, procedure)",
    "action": "HOW they can access it (SELECT, INSERT, UPDATE, DELETE, EXECUTE, etc.)",
    "conditions": "WHEN this applies (time, data filters, other conditions)",
    "description": "Clear description of this authorization policy"
  }}
]
```

If no authorization logic is found, return an empty array: []

IMPORTANT: Only extract policies where authorization/access control logic exists. Do not invent policies.
"""

        try:
            # Call LLM
            response = self.llm_provider.create_message(
                prompt=prompt,
                max_tokens=4000,
            )

            # Parse JSON response
            response_text = response.strip()

            # Extract JSON from markdown code blocks if present
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()

            import json
            policy_data_list = json.loads(response_text)

            if not isinstance(policy_data_list, list):
                logger.warning("llm_response_not_list", response=response_text[:200])
                return []

            # Create Policy objects
            policies = []
            for policy_data in policy_data_list:
                # Create evidence
                evidence = Evidence(
                    file_path=f"{schema}.{name}",
                    line_start=1,
                    line_end=len(definition.splitlines()),
                    code_snippet=definition[:500],  # First 500 chars as preview
                    repository_id=repository_id,
                    tenant_id=tenant_id,
                )

                # Calculate risk scores
                risk_scores = self.risk_scorer.calculate_risk_scores(
                    subject=policy_data.get("subject", ""),
                    resource=policy_data.get("resource", ""),
                    action=policy_data.get("action", ""),
                    conditions=policy_data.get("conditions", ""),
                    code_snippet=definition[:1000],
                    evidence_count=1,
                )

                # Create policy
                policy = Policy(
                    subject=policy_data.get("subject", "Unknown"),
                    resource=policy_data.get("resource", "Unknown"),
                    action=policy_data.get("action", "Unknown"),
                    conditions=policy_data.get("conditions", ""),
                    description=policy_data.get("description", ""),
                    source_type=SourceType.DATABASE,
                    status=PolicyStatus.PENDING,
                    risk_level=risk_scores["risk_level"],
                    overall_risk_score=risk_scores["overall_risk_score"],
                    complexity_score=risk_scores["complexity_score"],
                    impact_score=risk_scores["impact_score"],
                    confidence_score=risk_scores["confidence_score"],
                    historical_score=risk_scores["historical_score"],
                    repository_id=repository_id,
                    tenant_id=tenant_id,
                    evidence=[evidence],
                )

                # Generate embedding for similarity (only if not in test mode)
                try:
                    # Import here to avoid circular dependencies in tests
                    from app.services.similarity_service import SimilarityService
                    similarity_service = SimilarityService()
                    policy.embedding = similarity_service.generate_embedding(policy)
                except (ImportError, Exception) as e:
                    # It's okay if embedding fails (e.g., in tests or if pgvector not configured)
                    logger.debug("embedding_generation_skipped", error=str(e))

                policies.append(policy)

            logger.info(
                "policies_extracted_from_procedure",
                schema=schema,
                name=name,
                count=len(policies),
            )

            return policies

        except json.JSONDecodeError as e:
            logger.error(
                "failed_to_parse_llm_response",
                error=str(e),
                response=response_text[:500],
            )
            return []
        except Exception as e:
            logger.error(
                "failed_to_extract_policies",
                error=str(e),
                schema=schema,
                name=name,
            )
            return []

    async def scan_database(
        self,
        repository: Repository,
        tenant_id: str | None = None,
    ) -> dict[str, Any]:
        """Scan database stored procedures and extract policies.

        Args:
            repository: Repository object with database connection info
            tenant_id: Tenant ID for multi-tenancy

        Returns:
            Scan results dictionary
        """
        logger.info(
            "starting_database_scan",
            repository_id=repository.id,
            repository_name=repository.name,
            tenant_id=tenant_id,
        )

        if not repository.connection_config:
            raise ValueError("Repository missing connection_config")

        db_type = repository.connection_config.get("database_type")
        if not db_type:
            raise ValueError("Repository connection_config missing database_type")

        # Build connection string
        connection_string = self._build_connection_string(repository)

        try:
            # Create engine
            engine = create_engine(connection_string, echo=False)

            # Get stored procedures
            logger.info("fetching_stored_procedures", db_type=db_type)
            procedures = self._get_stored_procedures(engine, db_type)

            logger.info("found_procedures", count=len(procedures))

            # Filter procedures with authorization logic
            auth_procedures = [
                proc for proc in procedures
                if self._contains_authorization_logic(proc["definition"])
            ]

            logger.info(
                "filtered_authorization_procedures",
                total=len(procedures),
                with_auth=len(auth_procedures),
            )

            # Extract policies from each procedure
            all_policies = []
            for procedure in auth_procedures:
                policies = self._extract_policies_from_procedure(
                    procedure=procedure,
                    repository_id=repository.id,
                    tenant_id=tenant_id,
                    db_type=db_type,
                )
                all_policies.extend(policies)

            logger.info(
                "database_scan_complete",
                repository_id=repository.id,
                procedures_scanned=len(auth_procedures),
                policies_extracted=len(all_policies),
            )

            return {
                "procedures_scanned": len(auth_procedures),
                "total_procedures": len(procedures),
                "policies_extracted": len(all_policies),
                "policies": all_policies,
            }

        except SQLAlchemyError as e:
            logger.error(
                "database_connection_failed",
                error=str(e),
                repository_id=repository.id,
            )
            raise
        finally:
            if 'engine' in locals():
                engine.dispose()
