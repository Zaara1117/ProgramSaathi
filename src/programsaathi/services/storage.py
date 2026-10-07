"""Azure Blob Storage service interface and implementations."""

from abc import abstractmethod
from typing import Optional
from programsaathi.config import Settings, get_settings
from programsaathi.exceptions import StorageServiceError
from programsaathi.logging import get_logger
from programsaathi.services.base import BaseService

logger = get_logger(__name__)


class BlobStorageServiceInterface(BaseService):
    """Interface for object storage managing raw project documents."""

    @abstractmethod
    def upload_file(self, blob_name: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        """Uploads raw binary bytes to the specified blob path and returns reference URI."""
        pass

    @abstractmethod
    def download_file(self, blob_name: str) -> bytes:
        """Downloads raw bytes from the specified blob path."""
        pass

    @abstractmethod
    def delete_file(self, blob_name: str) -> bool:
        """Deletes a blob if it exists; returns True if deleted."""
        pass

    @abstractmethod
    def file_exists(self, blob_name: str) -> bool:
        """Checks if a blob exists in storage."""
        pass


class AzureBlobStorageService(BlobStorageServiceInterface):
    """Production client for Azure Blob Storage."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()

    def is_available(self) -> bool:
        return self.settings.is_storage_configured

    def upload_file(self, blob_name: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        if not self.is_available():
            raise StorageServiceError(
                "Azure Blob Storage is not configured in settings.",
                details={"blob_name": blob_name, "container": self.settings.azure_storage_container},
            )
        raise NotImplementedError("Live Azure Blob client calls will be integrated in Phase 8.")

    def download_file(self, blob_name: str) -> bytes:
        if not self.is_available():
            raise StorageServiceError("Azure Blob Storage is not configured.")
        raise NotImplementedError("Live Azure Blob client calls will be integrated in Phase 8.")

    def delete_file(self, blob_name: str) -> bool:
        if not self.is_available():
            raise StorageServiceError("Azure Blob Storage is not configured.")
        raise NotImplementedError("Live Azure Blob client calls will be integrated in Phase 8.")

    def file_exists(self, blob_name: str) -> bool:
        if not self.is_available():
            return False
        raise NotImplementedError("Live Azure Blob client calls will be integrated in Phase 8.")


class MockBlobStorageService(BlobStorageServiceInterface):
    """In-memory mock blob storage for unit and offline testing."""

    def __init__(self) -> None:
        self._blobs: dict[str, bytes] = {}

    def is_available(self) -> bool:
        return True

    def upload_file(self, blob_name: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        self._blobs[blob_name] = data
        return f"mock://blobs/{blob_name}"

    def download_file(self, blob_name: str) -> bytes:
        if blob_name not in self._blobs:
            raise StorageServiceError(f"Blob '{blob_name}' does not exist.")
        return self._blobs[blob_name]

    def delete_file(self, blob_name: str) -> bool:
        if blob_name in self._blobs:
            del self._blobs[blob_name]
            return True
        return False

    def file_exists(self, blob_name: str) -> bool:
        return blob_name in self._blobs
