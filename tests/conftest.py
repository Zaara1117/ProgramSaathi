"""Shared pytest fixtures for ProgramSaathi tests."""

import pytest
from programsaathi.config import Settings
from programsaathi.models.project import Project, ProjectStatus, Priority
from programsaathi.repositories.project import InMemoryProjectRepository
from programsaathi.repositories.governance import (
    InMemoryApprovalRequestRepository,
    InMemoryProjectEventRepository,
    InMemoryScopeChangeRepository,
)
from programsaathi.repositories.work_item import InMemoryTaskRepository
from programsaathi.services.llm import MockLLMService
from programsaathi.services.storage import MockBlobStorageService
from programsaathi.services.search import MockSearchService
from programsaathi.services.database import MockDatabaseService
from programsaathi.tools.registry import ToolRegistry


@pytest.fixture
def test_settings() -> Settings:
    """Provides isolated test settings."""
    return Settings(
        environment="test",
        log_level="DEBUG",
        app_name="ProgramSaathi-Test",
        foundry_model="gpt-4o",
    )


@pytest.fixture
def sample_project() -> Project:
    """Provides a valid test Project entity."""
    return Project(
        key="TEST01",
        name="Automated Platform Migration",
        description="Migrating legacy services to cloud architecture.",
        status=ProjectStatus.PLANNING,
        priority=Priority.HIGH,
    )


@pytest.fixture
def mock_services() -> dict:
    """Provides initialized mock service suite."""
    return {
        "llm": MockLLMService(),
        "storage": MockBlobStorageService(),
        "search": MockSearchService(),
        "database": MockDatabaseService(),
    }


@pytest.fixture
def in_memory_repos() -> dict:
    """Provides in-memory repositories."""
    return {
        "project": InMemoryProjectRepository(),
        "approval": InMemoryApprovalRequestRepository(),
        "event": InMemoryProjectEventRepository(),
        "scope": InMemoryScopeChangeRepository(),
        "task": InMemoryTaskRepository(),
    }
