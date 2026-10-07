"""Unit tests for configuration management."""

import pytest
from programsaathi.config import Settings, get_settings, reset_settings


def test_settings_defaults():
    settings = Settings()
    assert settings.environment == "development"
    assert settings.app_name == "ProgramSaathi"
    assert settings.foundry_model == "gpt-4o"
    assert settings.azure_storage_container == "programsaathi-documents"
    assert settings.azure_search_index == "programsaathi-index"
    assert settings.is_production is False


def test_settings_custom_values():
    settings = Settings(
        environment="production",
        log_level="DEBUG",
        foundry_project_endpoint="https://foundry.example.com",
        azure_storage_account_url="https://mystorage.blob.core.windows.net",
        azure_search_endpoint="https://mysearch.search.windows.net",
        azure_sql_server="myserver.database.windows.net",
        azure_sql_database="ProgramSaathiDB",
    )
    assert settings.is_production is True
    assert settings.log_level == "DEBUG"
    assert settings.is_llm_configured is True
    assert settings.is_storage_configured is True
    assert settings.is_search_configured is True
    assert settings.is_sql_configured is True


def test_settings_invalid_log_level():
    with pytest.raises(ValueError):
        Settings(log_level="SUPER_VERBOSE")


def test_singleton_accessor():
    reset_settings()
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2
    reset_settings()
