"""Azure SQL service interface and implementations."""

from abc import abstractmethod
from typing import Any, Optional
from programsaathi.config import Settings, get_settings
from programsaathi.exceptions import DatabaseServiceError
from programsaathi.logging import get_logger
from programsaathi.services.base import BaseService

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

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()

    def is_available(self) -> bool:
        return self.settings.is_sql_configured

    def is_healthy(self) -> bool:
        if not self.is_available():
            return False
        # Phase 6 will implement live connection check
        return False

    def execute_query(self, query: str, params: tuple = ()) -> list[dict[str, Any]]:
        if not self.is_available():
            raise DatabaseServiceError(
                "Azure SQL server/database is not configured in settings.",
                details={"server": self.settings.azure_sql_server},
            )
        raise NotImplementedError("Live Azure SQL queries will be integrated in Phase 6.")

    def execute_statement(self, statement: str, params: tuple = ()) -> int:
        if not self.is_available():
            raise DatabaseServiceError("Azure SQL server/database is not configured.")
        raise NotImplementedError("Live Azure SQL statement execution will be integrated in Phase 6.")


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
