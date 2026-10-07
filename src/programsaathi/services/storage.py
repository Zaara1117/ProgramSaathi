"""Azure Blob Storage service interface and implementations.

Phase 4 — Production implementation using azure-storage-blob SDK.

Responsibilities:
- Upload original project documents as immutable blobs
- Never overwrite existing blob versions
- Return stable blob paths for SQL metadata recording
- Support PDF, DOCX, XLSX, TXT, Markdown and other project-document formats
- SHA-256 integrity verification on every upload
- Mock implementation for offline unit testing
"""

import hashlib
import io
import mimetypes
import uuid
from abc import abstractmethod
from typing import Optional

from programsaathi.config import Settings, get_settings
from programsaathi.exceptions import StorageServiceError
from programsaathi.logging import get_logger
from programsaathi.services.base import BaseService

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Supported project-document MIME types
# ---------------------------------------------------------------------------

SUPPORTED_CONTENT_TYPES: set[str] = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",         # .xlsx
    "application/vnd.ms-excel",                                                   # .xls
    "text/plain",
    "text/markdown",
    "text/x-markdown",
    "application/octet-stream",  # fallback for unrecognised types
}


def detect_content_type(file_name: str, data: bytes) -> str:
    """Heuristically detect MIME type from filename, falling back to octet-stream."""
    guessed, _ = mimetypes.guess_type(file_name)
    if guessed and guessed in SUPPORTED_CONTENT_TYPES:
        return guessed
    # Check Markdown by extension only (not in stdlib mime DB by default)
    ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
    if ext in {"md", "markdown"}:
        return "text/markdown"
    if guessed:
        return guessed
    return "application/octet-stream"


def compute_sha256(data: bytes) -> str:
    """Return SHA-256 hex digest of the given byte sequence."""
    return hashlib.sha256(data).hexdigest()


def build_blob_path(project_id: str, document_id: str, version: int, file_name: str) -> str:
    """Build a deterministic, collision-free blob storage path.

    Pattern: ``projects/<project_id>/documents/<document_id>/v<version>/<filename>``
    """
    safe_name = file_name.replace(" ", "_")
    return f"projects/{project_id}/documents/{document_id}/v{version}/{safe_name}"


# ---------------------------------------------------------------------------
# Service Interface
# ---------------------------------------------------------------------------

class BlobStorageServiceInterface(BaseService):
    """Interface for object storage managing raw project documents."""

    @abstractmethod
    def upload_file(self, blob_name: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        """Uploads raw binary bytes to the specified blob path.

        Returns the canonical blob URI or path reference.
        Raises StorageServiceError if unavailable or upload fails.
        """

    @abstractmethod
    def download_file(self, blob_name: str) -> bytes:
        """Downloads raw bytes from the specified blob path.

        Raises StorageServiceError if blob does not exist or service unavailable.
        """

    @abstractmethod
    def delete_file(self, blob_name: str) -> bool:
        """Deletes a blob if it exists.

        Returns True if deleted, False if not found.
        NOTE: Originals are treated as immutable; callers must enforce this policy.
        """

    @abstractmethod
    def file_exists(self, blob_name: str) -> bool:
        """Returns True if the blob exists in storage."""

    @abstractmethod
    def get_blob_url(self, blob_name: str) -> str:
        """Returns a stable public-or-SAS URL for the blob (or mock equivalent)."""


# ---------------------------------------------------------------------------
# Production: Azure Blob Storage
# ---------------------------------------------------------------------------

class AzureBlobStorageService(BlobStorageServiceInterface):
    """Production client for Azure Blob Storage using DefaultAzureCredential or connection string."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        self._client = None   # BlobServiceClient — lazy-initialised

    def is_available(self) -> bool:
        return self.settings.is_storage_configured

    def _get_container_client(self):
        """Lazy-initialise and return the Azure ContainerClient."""
        if not self.is_available():
            raise StorageServiceError(
                "Azure Blob Storage is not configured.",
                details={
                    "account_url": self.settings.azure_storage_account_url,
                    "container": self.settings.azure_storage_container,
                },
            )
        if self._client is not None:
            return self._client

        try:
            from azure.storage.blob import BlobServiceClient  # type: ignore

            if self.settings.azure_storage_connection_string:
                service = BlobServiceClient.from_connection_string(
                    self.settings.azure_storage_connection_string
                )
            else:
                from azure.identity import DefaultAzureCredential  # type: ignore
                credential = DefaultAzureCredential()
                service = BlobServiceClient(
                    account_url=self.settings.azure_storage_account_url,
                    credential=credential,
                )

            self._client = service.get_container_client(self.settings.azure_storage_container)

            # Ensure container exists
            try:
                self._client.get_container_properties()
            except Exception:
                logger.info(f"Container '{self.settings.azure_storage_container}' not found — creating.")
                self._client.create_container()

            return self._client

        except ImportError as exc:
            raise StorageServiceError(
                "azure-storage-blob package is not installed. Install it with: pip install azure-storage-blob"
            ) from exc
        except Exception as exc:
            raise StorageServiceError(f"Failed to initialise Azure Blob Storage client: {exc}") from exc

    def upload_file(self, blob_name: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        """Upload bytes to blob storage.

        The blob_name is treated as immutable — if it already exists this method
        raises StorageServiceError to prevent silent overwrites of original documents.
        """
        container = self._get_container_client()
        try:
            blob_client = container.get_blob_client(blob_name)
            # Guard: never silently overwrite existing blobs
            try:
                blob_client.get_blob_properties()
                raise StorageServiceError(
                    f"Blob '{blob_name}' already exists. Original documents are immutable. Use a new version path.",
                    details={"blob_name": blob_name},
                )
            except StorageServiceError:
                raise
            except Exception:
                pass  # Blob doesn't exist — safe to upload

            blob_client.upload_blob(
                data=io.BytesIO(data),
                content_settings=self._make_content_settings(content_type),
                overwrite=False,
            )
            logger.info(f"Uploaded blob: {blob_name} ({len(data)} bytes, {content_type})")
            return blob_name
        except StorageServiceError:
            raise
        except Exception as exc:
            raise StorageServiceError(f"Failed to upload blob '{blob_name}': {exc}") from exc

    def download_file(self, blob_name: str) -> bytes:
        container = self._get_container_client()
        try:
            return container.download_blob(blob_name).readall()
        except Exception as exc:
            raise StorageServiceError(f"Failed to download blob '{blob_name}': {exc}") from exc

    def delete_file(self, blob_name: str) -> bool:
        container = self._get_container_client()
        try:
            blob_client = container.get_blob_client(blob_name)
            blob_client.delete_blob()
            return True
        except Exception as exc:
            logger.warning(f"Could not delete blob '{blob_name}': {exc}")
            return False

    def file_exists(self, blob_name: str) -> bool:
        try:
            container = self._get_container_client()
            blob_client = container.get_blob_client(blob_name)
            blob_client.get_blob_properties()
            return True
        except Exception:
            return False

    def get_blob_url(self, blob_name: str) -> str:
        """Returns the canonical HTTPS URL for the blob."""
        account_url = (self.settings.azure_storage_account_url or "").rstrip("/")
        container = self.settings.azure_storage_container
        return f"{account_url}/{container}/{blob_name}"

    @staticmethod
    def _make_content_settings(content_type: str):
        try:
            from azure.storage.blob import ContentSettings  # type: ignore
            return ContentSettings(content_type=content_type)
        except ImportError:
            return None


# ---------------------------------------------------------------------------
# Document Upload Orchestration Helper
# ---------------------------------------------------------------------------

class DocumentUploadResult:
    """Value object returned after a document upload completes."""

    def __init__(
        self,
        blob_path: str,
        blob_url: str,
        sha256_hash: str,
        file_size_bytes: int,
        content_type: str,
    ) -> None:
        self.blob_path = blob_path
        self.blob_url = blob_url
        self.sha256_hash = sha256_hash
        self.file_size_bytes = file_size_bytes
        self.content_type = content_type

    def __repr__(self) -> str:
        return (
            f"DocumentUploadResult(path={self.blob_path!r}, "
            f"size={self.file_size_bytes}, hash={self.sha256_hash[:16]}...)"
        )


def upload_document_version(
    storage: BlobStorageServiceInterface,
    project_id: str,
    document_id: str,
    version: int,
    file_name: str,
    data: bytes,
    content_type: Optional[str] = None,
) -> DocumentUploadResult:
    """Upload one immutable document version to blob storage.

    This function:
    1. Detects content type if not provided
    2. Computes SHA-256 digest
    3. Builds a versioned blob path (never overwrites)
    4. Uploads the bytes
    5. Returns a DocumentUploadResult for recording in SQL

    Raises:
        StorageServiceError: if the blob already exists or upload fails.
    """
    detected_type = content_type or detect_content_type(file_name, data)
    sha256 = compute_sha256(data)
    blob_path = build_blob_path(project_id, document_id, version, file_name)

    storage.upload_file(blob_path, data, detected_type)
    blob_url = storage.get_blob_url(blob_path)

    logger.info(
        f"Document version v{version} uploaded: {blob_path} "
        f"(sha256={sha256[:16]}..., size={len(data)})"
    )

    return DocumentUploadResult(
        blob_path=blob_path,
        blob_url=blob_url,
        sha256_hash=sha256,
        file_size_bytes=len(data),
        content_type=detected_type,
    )


# ---------------------------------------------------------------------------
# Mock: In-Memory Blob Storage
# ---------------------------------------------------------------------------

class MockBlobStorageService(BlobStorageServiceInterface):
    """In-memory mock blob storage for unit and offline testing.

    Enforces the same immutability rules as the production service.
    """

    def __init__(self) -> None:
        self._blobs: dict[str, bytes] = {}
        self._content_types: dict[str, str] = {}

    def is_available(self) -> bool:
        return True

    def upload_file(self, blob_name: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        if blob_name in self._blobs:
            raise StorageServiceError(
                f"Blob '{blob_name}' already exists. Original documents are immutable.",
                details={"blob_name": blob_name},
            )
        self._blobs[blob_name] = data
        self._content_types[blob_name] = content_type
        return f"mock://blobs/{blob_name}"

    def download_file(self, blob_name: str) -> bytes:
        if blob_name not in self._blobs:
            raise StorageServiceError(f"Blob '{blob_name}' does not exist.")
        return self._blobs[blob_name]

    def delete_file(self, blob_name: str) -> bool:
        if blob_name in self._blobs:
            del self._blobs[blob_name]
            self._content_types.pop(blob_name, None)
            return True
        return False

    def file_exists(self, blob_name: str) -> bool:
        return blob_name in self._blobs

    def get_blob_url(self, blob_name: str) -> str:
        return f"mock://blobs/{blob_name}"

    @property
    def stored_count(self) -> int:
        """Number of blobs currently in mock storage (useful for assertions)."""
        return len(self._blobs)
