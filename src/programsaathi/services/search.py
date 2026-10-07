"""Azure AI Search service interface and implementations."""

from abc import abstractmethod
from typing import Any, Optional
from programsaathi.config import Settings, get_settings
from programsaathi.exceptions import SearchServiceError
from programsaathi.logging import get_logger
from programsaathi.services.base import BaseService

logger = get_logger(__name__)


class SearchServiceInterface(BaseService):
    """Interface for indexing document chunks and retrieving grounded evidence."""

    @abstractmethod
    def index_documents(self, documents: list[dict[str, Any]]) -> int:
        """Indexes parsed document chunks into Azure AI Search; returns count indexed."""
        pass

    @abstractmethod
    def search(
        self,
        query: str,
        top_k: int = 5,
        filter_expression: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Executes hybrid keyword + vector search; returns list of scored chunks."""
        pass


class AzureAISearchService(SearchServiceInterface):
    """Production client for Azure AI Search hybrid retrieval."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()

    def is_available(self) -> bool:
        return self.settings.is_search_configured

    def index_documents(self, documents: list[dict[str, Any]]) -> int:
        if not self.is_available():
            raise SearchServiceError(
                "Azure AI Search endpoint is not configured in environment.",
                details={"index": self.settings.azure_search_index},
            )
        raise NotImplementedError("Live Azure AI Search indexing will be integrated in Phase 11.")

    def search(
        self,
        query: str,
        top_k: int = 5,
        filter_expression: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        if not self.is_available():
            raise SearchServiceError("Azure AI Search endpoint is not configured.")
        raise NotImplementedError("Live Azure AI Search hybrid retrieval will be integrated in Phase 12.")


class MockSearchService(SearchServiceInterface):
    """In-memory mock search service for deterministic retrieval testing."""

    def __init__(self) -> None:
        self._documents: list[dict[str, Any]] = []

    def is_available(self) -> bool:
        return True

    def index_documents(self, documents: list[dict[str, Any]]) -> int:
        self._documents.extend(documents)
        return len(documents)

    def search(
        self,
        query: str,
        top_k: int = 5,
        filter_expression: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        query_lower = query.lower()
        matched = [
            doc for doc in self._documents
            if query_lower in str(doc.get("content", "")).lower() or query_lower in str(doc.get("title", "")).lower()
        ]
        return matched[:top_k]
