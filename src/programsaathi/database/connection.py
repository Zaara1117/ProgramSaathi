"""Database engine and session management for Azure SQL and local development."""

from contextlib import contextmanager
import struct
from typing import Any, Generator, Optional
import urllib.parse

from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool

from programsaathi.config import Settings, get_settings
from programsaathi.exceptions import DatabaseServiceError
from programsaathi.logging import get_logger

logger = get_logger(__name__)


def build_azure_sql_connection_url(settings: Settings) -> str:
    """Builds standard SQLAlchemy connection URL for Azure SQL via pyodbc."""
    server = settings.azure_sql_server
    database = settings.azure_sql_database
    driver = settings.azure_sql_driver

    if not server or not database:
        raise DatabaseServiceError("Azure SQL server or database name is not configured in settings.")

    # SQL Authentication mode
    if settings.azure_sql_user and settings.azure_sql_password:
        encoded_pwd = urllib.parse.quote_plus(settings.azure_sql_password)
        encoded_user = urllib.parse.quote_plus(settings.azure_sql_user)
        encoded_driver = urllib.parse.quote_plus(driver)
        return (
            f"mssql+pyodbc://{encoded_user}:{encoded_pwd}@{server}/{database}"
            f"?driver={encoded_driver}&Encrypt=yes&TrustServerCertificate=no&Connection+Timeout=30"
        )

    # Entra ID / Token Authentication URL skeleton
    encoded_driver = urllib.parse.quote_plus(driver)
    return (
        f"mssql+pyodbc://@{server}/{database}"
        f"?driver={encoded_driver}&Encrypt=yes&TrustServerCertificate=no&Connection+Timeout=30"
    )


def create_db_engine(
    settings: Optional[Settings] = None,
    custom_url: Optional[str] = None,
    echo: bool = False,
) -> Engine:
    """Creates a SQLAlchemy engine configured for Azure SQL or custom database."""
    cfg = settings or get_settings()

    if custom_url:
        return create_engine(custom_url, echo=echo)

    # If SQLite or local testing database specified in env
    if not cfg.is_sql_configured:
        # Default in-memory engine for unconfigured local fallback
        return create_engine("sqlite:///:memory:", echo=echo)

    # Production Azure SQL engine
    url = build_azure_sql_connection_url(cfg)

    # Check if Entra ID token auth is needed (no SQL user/pass provided)
    if not cfg.azure_sql_user or not cfg.azure_sql_password:
        try:
            from azure.identity import DefaultAzureCredential

            credential = DefaultAzureCredential()

            def get_token_connect_args():
                token_bytes = credential.get_token("https://database.windows.net/.default").token.encode("utf-16-le")
                token_struct = struct.pack(f"<I{len(token_bytes)}s", len(token_bytes), token_bytes)
                SQL_COPT_SS_ACCESS_TOKEN = 1256
                return {"attrs_before": {SQL_COPT_SS_ACCESS_TOKEN: token_struct}}

            return create_engine(
                url,
                connect_args=get_token_connect_args(),
                pool_pre_ping=True,
                echo=echo,
            )
        except Exception as exc:
            logger.warning(f"Could not configure Entra ID token for Azure SQL: {exc}")

    return create_engine(url, pool_pre_ping=True, echo=echo)


class DatabaseSessionManager:
    """Manages SQLAlchemy session lifecycle and transactional guarantees."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine
        self._session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """Transactional session context manager: auto-commits on success, rolls back on error."""
        sess: Session = self._session_factory()
        try:
            yield sess
            sess.commit()
        except Exception as exc:
            sess.rollback()
            logger.error(f"Transaction rolled back due to error: {exc}")
            raise
        finally:
            sess.close()
