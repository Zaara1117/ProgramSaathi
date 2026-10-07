"""Azure SQL service interface and production implementation."""

from abc import abstractmethod
from typing import Any, Optional
from sqlalchemy import text, Engine
from sqlalchemy.orm import Session

from programsaathi.config import Settings, get_settings
from programsaathi.exceptions import DatabaseServiceError
from programsaathi.logging import get_logger
from programsaathi.services.base import BaseService
from programsaathi.database.connection import create_db_engine, DatabaseSessionManager

logger = get_logger(__name__)


class DatabaseServiceInterface(BaseService):
    """Interface for relational database execution maintaining authoritative state."""

    @abstractmethod
    def execute_query(self, query: str, params: tuple = ()) -> list[dict[str, Any]]:
        """Executes a parameterized read-only query and returns rows as dictionaries."""
        pass

    @abstractmethod
    def execute_statement(self, statement: str, params: tuple = ()) -> int:
        """Executes a parameterized DML statement and returns affected rows count."""
        pass

    @abstractmethod
    def is_healthy(self) -> bool:
        """Verifies database connectivity."""
        pass


class AzureSQLService(DatabaseServiceInterface):
    """Production client for Azure SQL Database."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        engine: Optional[Engine] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._engine = engine
        self._session_manager: Optional[DatabaseSessionManager] = None

    def is_available(self) -> bool:
        return bool(self._engine or self.settings.is_sql_configured)

    def _get_engine(self) -> Engine:
        if self._engine is None:
            if not self.is_available():
                raise DatabaseServiceError(
                    "Azure SQL server/database is not configured in settings.",
                    details={"server": self.settings.azure_sql_server},
                )
            self._engine = create_db_engine(self.settings)
        return self._engine

    def get_session_manager(self) -> DatabaseSessionManager:
        if self._session_manager is None:
            self._session_manager = DatabaseSessionManager(self._get_engine())
        return self._session_manager

    def is_healthy(self) -> bool:
        if not self.is_available():
            return False
        try:
            with self._get_engine().connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as exc:
            logger.warning(f"Database health check failed: {exc}")
            return False

    def execute_query(self, query: str, params: tuple = ()) -> list[dict[str, Any]]:
        if not self.is_available():
            raise DatabaseServiceError(
                "Azure SQL server/database is not configured in settings.",
                details={"server": self.settings.azure_sql_server},
            )
        try:
            with self._get_engine().connect() as conn:
                result = conn.execute(text(query), params if isinstance(params, dict) else {})
                return [dict(row._mapping) for row in result]
        except Exception as exc:
            raise DatabaseServiceError(f"Database query execution failed: {exc}") from exc

    def execute_statement(self, statement: str, params: tuple = ()) -> int:
        if not self.is_available():
            raise DatabaseServiceError("Azure SQL server/database is not configured.")
        try:
            with self._get_engine().begin() as conn:
                result = conn.execute(text(statement), params if isinstance(params, dict) else {})
                return result.rowcount
        except Exception as exc:
            raise DatabaseServiceError(f"Database statement execution failed: {exc}") from exc


class MockDatabaseService(DatabaseServiceInterface):
    """In-memory mock database for unit and repository testing."""

    def __init__(self) -> None:
        self.tables: dict[str, list[dict[str, Any]]] = {}
        self.query_log: list[tuple[str, tuple]] = []

    def is_available(self) -> bool:
        return True

    def is_healthy(self) -> bool:
        return True

    def execute_query(self, query: str, params: tuple = ()) -> list[dict[str, Any]]:
        self.query_log.append((query, params))
        return []

    def execute_statement(self, statement: str, params: tuple = ()) -> int:
        self.query_log.append((statement, params))
        return 1
