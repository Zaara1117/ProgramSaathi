"""Phase 4 smoke test: Live Azure Blob Storage connectivity.

Skips automatically when Azure Blob Storage environment variables are not configured.
"""

import uuid
import pytest

from programsaathi.config import get_settings
from programsaathi.services.storage import (
    AzureBlobStorageService,
    upload_document_version,
    compute_sha256,
)
from programsaathi.exceptions import StorageServiceError


@pytest.fixture(scope="module")
def blob_settings():
    settings = get_settings()
    if not settings.is_storage_configured:
        pytest.skip(
            "Azure Blob Storage not configured in environment "
            "(AZURE_STORAGE_ACCOUNT_URL or AZURE_STORAGE_CONNECTION_STRING missing)."
        )
    return settings


class TestAzureBlobStorageSmoke:
    def test_live_blob_storage_upload_and_download(self, blob_settings):
        """Upload a small test document and download it back — must match exactly."""
        svc = AzureBlobStorageService(settings=blob_settings)

        test_data = b"ProgramSaathi Phase 4 smoke test blob content."
        blob_name = f"smoke-tests/{uuid.uuid4()}.txt"

        try:
            svc.upload_file(blob_name, test_data, "text/plain")
            assert svc.file_exists(blob_name)

            downloaded = svc.download_file(blob_name)
            assert downloaded == test_data

        finally:
            # Clean up smoke test blob
            svc.delete_file(blob_name)

    def test_live_upload_document_version_helper(self, blob_settings):
        """upload_document_version orchestration must produce correct metadata."""
        svc = AzureBlobStorageService(settings=blob_settings)
        project_id = "smoke-project"
        document_id = str(uuid.uuid4())
        data = b"# PRD Smoke Test\n\nThis is a test document."

        blob_name = None
        try:
            result = upload_document_version(
                storage=svc,
                project_id=project_id,
                document_id=document_id,
                version=1,
                file_name="smoke_prd.md",
                data=data,
            )
            blob_name = result.blob_path
            assert result.sha256_hash == compute_sha256(data)
            assert result.file_size_bytes == len(data)
            assert svc.file_exists(blob_name)
        finally:
            if blob_name:
                svc.delete_file(blob_name)

    def test_live_immutability_reupload_raises(self, blob_settings):
        """Re-uploading to the same blob path must raise StorageServiceError."""
        svc = AzureBlobStorageService(settings=blob_settings)
        blob_name = f"smoke-tests/immutable-{uuid.uuid4()}.txt"

        try:
            svc.upload_file(blob_name, b"original", "text/plain")
            with pytest.raises(StorageServiceError, match="immutable"):
                svc.upload_file(blob_name, b"overwrite attempt", "text/plain")
        finally:
            svc.delete_file(blob_name)
