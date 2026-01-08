"""Repository service for managing repository operations."""
import shutil
import tempfile

import structlog
from git import GitCommandError, Repo
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app.models.repository import DatabaseType, Repository, RepositoryStatus
from app.schemas.repository import RepositoryCreate, RepositoryUpdate

logger = structlog.get_logger()


class RepositoryService:
    """Service for repository operations."""

    def __init__(self, db: Session):
        """Initialize service with database session."""
        self.db = db

    def create_repository(self, repository_data: RepositoryCreate, tenant_id: str | None = None) -> Repository:
        """Create a new repository."""
        logger.info("creating_repository", name=repository_data.name, type=repository_data.repository_type, tenant_id=tenant_id)

        repository = Repository(
            name=repository_data.name,
            description=repository_data.description,
            repository_type=repository_data.repository_type,
            source_url=repository_data.source_url,
            connection_config=repository_data.connection_config,
            tenant_id=tenant_id or repository_data.tenant_id,
            status=RepositoryStatus.PENDING,
        )

        self.db.add(repository)
        self.db.commit()
        self.db.refresh(repository)

        logger.info("repository_created", repository_id=repository.id, name=repository.name, tenant_id=repository.tenant_id)
        return repository

    def get_repository(self, repository_id: int, tenant_id: str | None = None) -> Repository | None:
        """Get a repository by ID, optionally filtered by tenant."""
        stmt = select(Repository).where(Repository.id == repository_id)
        if tenant_id:
            stmt = stmt.where(Repository.tenant_id == tenant_id)
        return self.db.scalars(stmt).first()

    def list_repositories(
        self, skip: int = 0, limit: int = 100, tenant_id: str | None = None
    ) -> tuple[list[Repository], int]:
        """List repositories with pagination."""
        stmt = select(Repository)

        if tenant_id:
            stmt = stmt.where(Repository.tenant_id == tenant_id)

        # Get total count
        total_stmt = select(Repository.id)
        if tenant_id:
            total_stmt = total_stmt.where(Repository.tenant_id == tenant_id)
        total = len(self.db.scalars(total_stmt).all())

        # Get paginated results
        stmt = stmt.offset(skip).limit(limit).order_by(Repository.created_at.desc())
        repositories = self.db.scalars(stmt).all()

        return list(repositories), total

    def update_repository(
        self, repository_id: int, repository_data: RepositoryUpdate, tenant_id: str | None = None
    ) -> Repository | None:
        """Update a repository."""
        repository = self.get_repository(repository_id, tenant_id=tenant_id)
        if not repository:
            return None

        logger.info("updating_repository", repository_id=repository_id, tenant_id=tenant_id)

        update_data = repository_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(repository, field, value)

        self.db.commit()
        self.db.refresh(repository)

        logger.info("repository_updated", repository_id=repository.id)
        return repository

    def delete_repository(self, repository_id: int, tenant_id: str | None = None) -> bool:
        """Delete a repository."""
        repository = self.get_repository(repository_id, tenant_id=tenant_id)
        if not repository:
            return False

        logger.info("deleting_repository", repository_id=repository_id, tenant_id=tenant_id)
        self.db.delete(repository)
        self.db.commit()

        logger.info("repository_deleted", repository_id=repository_id)
        return True

    def verify_git_connection(self, repository: Repository) -> bool:
        """Verify Git repository connection by attempting to clone/fetch."""
        logger.info("verifying_git_connection", repository_id=repository.id, url=repository.source_url)

        if not repository.source_url:
            logger.error("no_source_url", repository_id=repository.id)
            repository.status = RepositoryStatus.FAILED
            self.db.commit()
            return False

        temp_dir = None
        try:
            # Create temporary directory for git operations
            temp_dir = tempfile.mkdtemp(prefix="policy_miner_git_")
            logger.debug("created_temp_dir", temp_dir=temp_dir)

            # Prepare auth credentials if provided
            clone_url = repository.source_url
            if repository.connection_config:
                username = repository.connection_config.get("username")
                password = repository.connection_config.get("password")
                token = repository.connection_config.get("token")

                # If token is provided, use it in the URL
                if token:
                    # Replace https:// with https://token@
                    if clone_url.startswith("https://"):
                        clone_url = clone_url.replace("https://", f"https://{token}@")
                    elif clone_url.startswith("http://"):
                        clone_url = clone_url.replace("http://", f"http://{token}@")
                elif username and password:
                    # Replace https:// with https://username:password@
                    if clone_url.startswith("https://"):
                        clone_url = clone_url.replace("https://", f"https://{username}:{password}@")
                    elif clone_url.startswith("http://"):
                        clone_url = clone_url.replace("http://", f"http://{username}:{password}@")

            # Try to list remote refs (lightweight operation)
            # This verifies the URL is accessible without cloning
            try:
                repo = Repo.init(temp_dir)
                remote = repo.create_remote("origin", clone_url)
                remote.fetch(depth=1)  # Shallow fetch just to verify connection

                logger.info("git_connection_verified", repository_id=repository.id)
                repository.status = RepositoryStatus.CONNECTED
                self.db.commit()
                return True
            except GitCommandError as git_err:
                logger.error(
                    "git_connection_failed",
                    repository_id=repository.id,
                    error=str(git_err),
                )
                repository.status = RepositoryStatus.FAILED
                self.db.commit()
                return False

        except Exception as e:
            logger.error(
                "git_verification_exception",
                repository_id=repository.id,
                error=str(e),
            )
            repository.status = RepositoryStatus.FAILED
            self.db.commit()
            return False
        finally:
            # Clean up temporary directory
            if temp_dir:
                try:
                    shutil.rmtree(temp_dir)
                    logger.debug("cleaned_temp_dir", temp_dir=temp_dir)
                except Exception as cleanup_err:
                    logger.warning("temp_dir_cleanup_failed", temp_dir=temp_dir, error=str(cleanup_err))

    def verify_database_connection(self, repository: Repository) -> bool:
        """Verify database connection by attempting to connect and execute a simple query."""
        logger.info("verifying_database_connection", repository_id=repository.id)

        if not repository.connection_config:
            logger.error("no_connection_config", repository_id=repository.id)
            repository.status = RepositoryStatus.FAILED
            self.db.commit()
            return False

        try:
            # Extract connection details
            config = repository.connection_config
            db_type = config.get("database_type")
            host = config.get("host")
            port = config.get("port")
            database = config.get("database")
            username = config.get("username")
            password = config.get("password")

            if not all([db_type, host, database, username, password]):
                logger.error(
                    "missing_connection_details",
                    repository_id=repository.id,
                    has_db_type=bool(db_type),
                    has_host=bool(host),
                    has_database=bool(database),
                    has_username=bool(username),
                    has_password=bool(password),
                )
                repository.status = RepositoryStatus.FAILED
                self.db.commit()
                return False

            # Build connection string based on database type
            connection_string = self._build_database_connection_string(
                db_type, host, port, database, username, password
            )

            logger.debug("attempting_database_connection", repository_id=repository.id, db_type=db_type)

            # Attempt to connect and execute a simple query
            engine = create_engine(connection_string, pool_pre_ping=True, connect_args={"connect_timeout": 10})

            # Test the connection with a simple query
            with engine.connect() as connection:
                result = connection.execute(text("SELECT 1"))
                result.fetchone()

            logger.info("database_connection_verified", repository_id=repository.id)
            repository.status = RepositoryStatus.CONNECTED
            self.db.commit()
            engine.dispose()
            return True

        except Exception as e:
            logger.error(
                "database_connection_failed",
                repository_id=repository.id,
                error=str(e),
                error_type=type(e).__name__,
            )
            repository.status = RepositoryStatus.FAILED
            self.db.commit()
            return False

    def _build_database_connection_string(
        self, db_type: str, host: str, port: int | None, database: str, username: str, password: str
    ) -> str:
        """Build database connection string based on database type."""
        # Set default ports if not provided
        if not port:
            default_ports = {
                DatabaseType.POSTGRESQL.value: 5432,
                DatabaseType.MYSQL.value: 3306,
                DatabaseType.SQLSERVER.value: 1433,
                DatabaseType.ORACLE.value: 1521,
            }
            port = default_ports.get(db_type, 5432)

        # Build connection string based on database type
        if db_type == DatabaseType.POSTGRESQL.value:
            return f"postgresql://{username}:{password}@{host}:{port}/{database}"
        elif db_type == DatabaseType.MYSQL.value:
            return f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}"
        elif db_type == DatabaseType.SQLSERVER.value:
            # SQL Server uses different connection string format
            return f"mssql+pyodbc://{username}:{password}@{host}:{port}/{database}?driver=ODBC+Driver+17+for+SQL+Server"
        elif db_type == DatabaseType.ORACLE.value:
            return f"oracle+cx_oracle://{username}:{password}@{host}:{port}/?service_name={database}"
        else:
            msg = f"Unsupported database type: {db_type}"
            raise ValueError(msg)
