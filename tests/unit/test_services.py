"""Unit tests for service interfaces and error boundaries."""

import pytest
from programsaathi.config import Settings
from programsaathi.exceptions import (
    LLMServiceError,
    StorageServiceError,
    SearchServiceError,
    DatabaseServiceError,
)
from programsaathi.services.llm import FoundryLLMService, MockLLMService
from programsaathi.services.storage import AzureBlobStorageService, MockBlobStorageService
from programsaathi.services.search import AzureAISearchService, MockSearchService
from programsaathi.services.database import AzureSQLService, MockDatabaseService


def test_unconfigured_azure_services_raise_explicit_errors():
    empty_settings = Settings()

    llm = FoundryLLMService(settings=empty_settings)
    assert llm.is_available() is False
    with pytest.raises(LLMServiceError):
        llm.generate_text("Prompt")

    storage = AzureBlobStorageService(settings=empty_settings)
    assert storage.is_available() is False
    with pytest.raises(StorageServiceError):
        storage.upload_file("test.pdf", b"data")

    search = AzureAISearchService(settings=empty_settings)
    assert search.is_available() is False
    with pytest.raises(SearchServiceError):
        search.search("query")

    db = AzureSQLService(settings=empty_settings)
    assert db.is_available() is False
    with pytest.raises(DatabaseServiceError):
        db.execute_query("SELECT 1")


def test_mock_services_behavior():
    mock_llm = MockLLMService("AI response")
    assert mock_llm.generate_text("Hello") == "AI response"
    assert len(mock_llm.recorded_calls) == 1

    mock_storage = MockBlobStorageService()
    uri = mock_storage.upload_file("doc.txt", b"content")
    assert mock_storage.file_exists("doc.txt") is True
    assert mock_storage.download_file("doc.txt") == b"content"
    mock_storage.delete_file("doc.txt")
    assert mock_storage.file_exists("doc.txt") is False

    mock_search = MockSearchService()
    mock_search.index_documents([
        {"id": "1", "title": "Architecture Doc", "content": "Microservices design"},
        {"id": "2", "title": "Roadmap", "content": "Deliver MVP in Q3"},
    ])
    hits = mock_search.search("Microservices")
    assert len(hits) == 1
    assert hits[0]["id"] == "1"

    mock_db = MockDatabaseService()
    assert mock_db.is_healthy() is True
    res = mock_db.execute_statement("UPDATE table SET x = 1")
    assert res == 1
