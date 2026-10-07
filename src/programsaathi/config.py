"""Configuration management for ProgramSaathi using Pydantic Settings and environment variables."""

from typing import Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration class loaded from environment variables and .env files."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # General App Settings
    environment: str = Field(default="development", description="Environment: development, test, staging, production")
    log_level: str = Field(default="INFO", description="Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL")
    app_name: str = Field(default="ProgramSaathi", description="Application name")

    # Microsoft Foundry / Azure OpenAI
    foundry_project_endpoint: Optional[str] = Field(default=None, description="Azure AI Foundry Project Endpoint")
    azure_openai_endpoint: Optional[str] = Field(default=None, description="Azure OpenAI Endpoint URL")
    foundry_model: str = Field(default="gpt-4o", description="Model deployment name")
    azure_openai_deployment_name: Optional[str] = Field(default=None, description="Azure OpenAI Deployment name override")
    azure_openai_api_key: Optional[str] = Field(default=None, description="Azure OpenAI API Key (optional if using DefaultAzureCredential)")
    azure_openai_api_version: str = Field(default="2024-06-01", description="API Version")
    use_azure_ad: bool = Field(default=False, description="Explicitly use Azure AD / DefaultAzureCredential instead of API key")

    # Azure Blob Storage
    azure_storage_account_url: Optional[str] = Field(default=None, description="Azure Storage Account Blob URL")
    azure_storage_container: str = Field(default="programsaathi-documents", description="Blob container name")
    azure_storage_connection_string: Optional[str] = Field(default=None, description="Blob connection string")

    # Azure AI Search
    azure_search_endpoint: Optional[str] = Field(default=None, description="Azure AI Search Endpoint URL")
    azure_search_index: str = Field(default="programsaathi-index", description="Target search index name")
    azure_search_api_key: Optional[str] = Field(default=None, description="Search API key")

    # Azure SQL
    azure_sql_server: Optional[str] = Field(default=None, description="Azure SQL Server hostname")
    azure_sql_database: Optional[str] = Field(default=None, description="Azure SQL Database name")
    azure_sql_user: Optional[str] = Field(default=None, description="SQL Login username")
    azure_sql_password: Optional[str] = Field(default=None, description="SQL Login password")
    azure_sql_driver: str = Field(default="ODBC Driver 18 for SQL Server", description="ODBC Driver")

    # Observability
    applicationinsights_connection_string: Optional[str] = Field(
        default=None, description="Application Insights connection string"
    )

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in valid_levels:
            raise ValueError(f"Invalid log_level: {v}. Must be one of {sorted(valid_levels)}")
        return upper

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @property
    def effective_llm_endpoint(self) -> Optional[str]:
        return self.azure_openai_endpoint or self.foundry_project_endpoint

    @property
    def effective_llm_model(self) -> str:
        return self.azure_openai_deployment_name or self.foundry_model

    @property
    def is_llm_configured(self) -> bool:
        return bool(self.foundry_project_endpoint or self.azure_openai_endpoint or self.azure_openai_api_key)

    @property
    def is_storage_configured(self) -> bool:
        return bool(self.azure_storage_account_url or self.azure_storage_connection_string)

    @property
    def is_search_configured(self) -> bool:
        return bool(self.azure_search_endpoint)

    @property
    def is_sql_configured(self) -> bool:
        return bool(self.azure_sql_server and self.azure_sql_database)


# Singleton instance accessor
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Returns the cached global Settings instance or instantiates a new one."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings() -> None:
    """Reset the cached Settings instance (primarily used for unit testing with custom env)."""
    global _settings
    _settings = None
