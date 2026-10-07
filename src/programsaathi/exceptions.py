"""Explicit domain and infrastructure exceptions for ProgramSaathi."""

from typing import Any, Optional


class ProgramSaathiError(Exception):
    """Base exception for all ProgramSaathi system and domain errors."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(message={self.message!r}, details={self.details!r})"


class ConfigurationError(ProgramSaathiError):
    """Raised when configuration values are missing, invalid, or malformed."""


class ValidationError(ProgramSaathiError):
    """Raised when domain entity or input validation rules fail."""


class SecurityViolationError(ProgramSaathiError):
    """Raised when an action violates security policies (e.g., unauthorized access, forbidden SQL generation)."""


class HumanApprovalRequiredError(ProgramSaathiError):
    """Raised when a consequential project state mutation is attempted without verified human approval."""

    def __init__(self, message: str, change_proposal_id: Optional[str] = None, details: Optional[dict[str, Any]] = None) -> None:
        details = details or {}
        if change_proposal_id:
            details["change_proposal_id"] = change_proposal_id
        super().__init__(message, details=details)
        self.change_proposal_id = change_proposal_id


class StateTransitionError(ProgramSaathiError):
    """Raised when an invalid project or item lifecycle transition is attempted."""


class EntityNotFoundError(ProgramSaathiError):
    """Raised when a requested entity does not exist in the authoritative store."""


class DuplicateEntityError(ProgramSaathiError):
    """Raised when attempting to insert an entity that already exists."""


class ServiceUnavailableError(ProgramSaathiError):
    """Base exception for third-party or Azure cloud service failures."""


class LLMServiceError(ServiceUnavailableError):
    """Raised when Azure OpenAI / Foundry reasoning calls fail or produce unparseable responses."""


class StorageServiceError(ServiceUnavailableError):
    """Raised when Azure Blob Storage operations fail."""


class SearchServiceError(ServiceUnavailableError):
    """Raised when Azure AI Search indexing or retrieval operations fail."""


class DatabaseServiceError(ServiceUnavailableError):
    """Raised when Azure SQL transactions, connections, or queries fail."""
