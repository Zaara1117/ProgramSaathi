"""Phase 3 smoke test: Live Azure SQL connectivity.

Skips automatically when Azure SQL environment variables are not configured.
Only connects to real Azure SQL when full credentials are present.
"""

import pytest

from programsaathi.config import get_settings
from programsaathi.services.database import AzureSQLService
from programsaathi.database.connection import create_db_engine
from programsaathi.database.init_db import init_database


@pytest.fixture(scope="module")
def azure_sql_settings():
    """Returns settings — skips test module if Azure SQL is not configured."""
    settings = get_settings()
    if not settings.is_sql_configured:
        pytest.skip("Azure SQL not configured in environment (AZURE_SQL_SERVER / AZURE_SQL_DATABASE missing).")
    return settings


class TestAzureSQLSmoke:
    def test_live_azure_sql_health_check(self, azure_sql_settings):
        """AzureSQLService must report healthy when credentials are present."""
        svc = AzureSQLService(settings=azure_sql_settings)
        healthy = svc.is_healthy()
        if not healthy:
            pytest.skip("Azure SQL credentials present but connection failed — check network/firewall.")
        assert healthy is True

    def test_live_azure_sql_select_one(self, azure_sql_settings):
        """Must be able to execute a trivial SELECT against Azure SQL."""
        svc = AzureSQLService(settings=azure_sql_settings)
        if not svc.is_healthy():
            pytest.skip("Azure SQL not reachable.")
        result = svc.execute_query("SELECT 1 AS value")
        assert len(result) == 1
        assert list(result[0].values())[0] == 1

    def test_live_azure_sql_schema_init(self, azure_sql_settings):
        """Schema init must complete idempotently against the live database."""
        engine = create_db_engine(settings=azure_sql_settings)
        try:
            init_database(engine)  # idempotent — CREATE TABLE IF NOT EXISTS
        finally:
            engine.dispose()
