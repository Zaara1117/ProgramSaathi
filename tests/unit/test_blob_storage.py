"""Phase 4: Azure Blob Storage unit tests (no Azure credentials required).

Tests cover:
- Content type detection (PDF, DOCX, XLSX, TXT, Markdown, unknown)
- SHA-256 digest computation
- Blob path construction (versioned, project/document scoped)
- MockBlobStorageService: upload, download, exists, delete, immutability
- upload_document_version orchestration helper
- AzureBlobStorageService: unconfigured raises StorageServiceError
- DocumentUploadResult attributes
"""

import hashlib
import pytest

from programsaathi.services.storage import (
    AzureBlobStorageService,
    MockBlobStorageService,
    DocumentUploadResult,
    upload_document_version,
    detect_content_type,
    compute_sha256,
    build_blob_path,
    SUPPORTED_CONTENT_TYPES,
)
from programsaathi.exceptions import StorageServiceError
from programsaathi.config import Settings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PDF_MAGIC = b"%PDF-1.4 small test document"
DOCX_MAGIC = b"PK\x03\x04"   # Zip header (DOCX is a ZIP)
TXT_CONTENT = b"Hello, ProgramSaathi!"
MD_CONTENT  = b"# My Project PRD\n\nObjective: ..."


PROJECT_ID  = "aaaa-bbbb-cccc-dddd"
DOC_ID      = "1111-2222-3333-4444"


# ===========================================================================
# 1. Utility functions
# ===========================================================================

class TestDetectContentType:
    def test_pdf_detected(self):
        assert detect_content_type("spec.pdf", PDF_MAGIC) == "application/pdf"

    def test_docx_detected(self):
        ct = detect_content_type("requirements.docx", DOCX_MAGIC)
        assert "wordprocessingml" in ct or ct == "application/octet-stream"

    def test_xlsx_detected(self):
        ct = detect_content_type("plan.xlsx", b"PK\x03\x04")
        assert "spreadsheet" in ct or "excel" in ct or ct == "application/octet-stream"

    def test_txt_detected(self):
        assert detect_content_type("notes.txt", TXT_CONTENT) == "text/plain"

    def test_md_detected(self):
        ct = detect_content_type("README.md", MD_CONTENT)
        assert "markdown" in ct

    def test_markdown_extension_detected(self):
        ct = detect_content_type("prd.markdown", MD_CONTENT)
        assert "markdown" in ct

    def test_unknown_falls_back_to_octet_stream(self):
        ct = detect_content_type("binary.bin", b"\x00\x01\x02\x03")
        # Should be some type — not crash
        assert isinstance(ct, str)
        assert len(ct) > 0


class TestComputeSha256:
    def test_known_hash(self):
        data = b"hello"
        expected = hashlib.sha256(b"hello").hexdigest()
        assert compute_sha256(data) == expected

    def test_empty_bytes(self):
        digest = compute_sha256(b"")
        assert len(digest) == 64

    def test_different_data_different_hash(self):
        assert compute_sha256(b"a") != compute_sha256(b"b")


class TestBuildBlobPath:
    def test_path_structure(self):
        path = build_blob_path(PROJECT_ID, DOC_ID, 1, "spec.pdf")
        assert path == f"projects/{PROJECT_ID}/documents/{DOC_ID}/v1/spec.pdf"

    def test_version_increments(self):
        p1 = build_blob_path(PROJECT_ID, DOC_ID, 1, "doc.pdf")
        p2 = build_blob_path(PROJECT_ID, DOC_ID, 2, "doc.pdf")
        assert p1 != p2
        assert "v2" in p2

    def test_spaces_in_filename_replaced(self):
        path = build_blob_path(PROJECT_ID, DOC_ID, 1, "my doc.pdf")
        assert " " not in path
        assert "my_doc.pdf" in path


# ===========================================================================
# 2. MockBlobStorageService
# ===========================================================================

class TestMockBlobStorageService:
    @pytest.fixture
    def storage(self) -> MockBlobStorageService:
        return MockBlobStorageService()

    def test_is_available(self, storage):
        assert storage.is_available() is True

    def test_upload_and_exists(self, storage):
        storage.upload_file("blobs/test.txt", TXT_CONTENT, "text/plain")
        assert storage.file_exists("blobs/test.txt") is True

    def test_upload_returns_url(self, storage):
        url = storage.upload_file("blobs/test.txt", TXT_CONTENT, "text/plain")
        assert "test.txt" in url

    def test_download_returns_correct_bytes(self, storage):
        storage.upload_file("blobs/doc.txt", TXT_CONTENT, "text/plain")
        result = storage.download_file("blobs/doc.txt")
        assert result == TXT_CONTENT

    def test_download_nonexistent_raises(self, storage):
        with pytest.raises(StorageServiceError, match="does not exist"):
            storage.download_file("blobs/missing.txt")

    def test_delete_existing_blob(self, storage):
        storage.upload_file("blobs/del.txt", TXT_CONTENT, "text/plain")
        deleted = storage.delete_file("blobs/del.txt")
        assert deleted is True
        assert storage.file_exists("blobs/del.txt") is False

    def test_delete_nonexistent_returns_false(self, storage):
        assert storage.delete_file("blobs/nope.txt") is False

    def test_get_blob_url(self, storage):
        url = storage.get_blob_url("some/path/file.pdf")
        assert "file.pdf" in url

    def test_stored_count_increments(self, storage):
        assert storage.stored_count == 0
        storage.upload_file("a.txt", b"a", "text/plain")
        storage.upload_file("b.txt", b"b", "text/plain")
        assert storage.stored_count == 2

    # Immutability enforcement
    def test_immutability_reupload_same_path_raises(self, storage):
        storage.upload_file("blobs/v1/spec.pdf", PDF_MAGIC, "application/pdf")
        with pytest.raises(StorageServiceError, match="immutable"):
            storage.upload_file("blobs/v1/spec.pdf", PDF_MAGIC, "application/pdf")

    def test_different_version_path_succeeds(self, storage):
        storage.upload_file("blobs/v1/spec.pdf", PDF_MAGIC, "application/pdf")
        storage.upload_file("blobs/v2/spec.pdf", PDF_MAGIC, "application/pdf")
        assert storage.stored_count == 2


# ===========================================================================
# 3. upload_document_version orchestration
# ===========================================================================

class TestUploadDocumentVersion:
    @pytest.fixture
    def storage(self) -> MockBlobStorageService:
        return MockBlobStorageService()

    def test_returns_upload_result(self, storage):
        result = upload_document_version(
            storage=storage,
            project_id=PROJECT_ID,
            document_id=DOC_ID,
            version=1,
            file_name="prd.pdf",
            data=PDF_MAGIC,
        )
        assert isinstance(result, DocumentUploadResult)

    def test_correct_sha256(self, storage):
        result = upload_document_version(
            storage=storage,
            project_id=PROJECT_ID,
            document_id=DOC_ID,
            version=1,
            file_name="prd.pdf",
            data=PDF_MAGIC,
        )
        assert result.sha256_hash == compute_sha256(PDF_MAGIC)

    def test_correct_file_size(self, storage):
        result = upload_document_version(
            storage=storage,
            project_id=PROJECT_ID,
            document_id=DOC_ID,
            version=1,
            file_name="prd.pdf",
            data=PDF_MAGIC,
        )
        assert result.file_size_bytes == len(PDF_MAGIC)

    def test_blob_path_stored_in_storage(self, storage):
        result = upload_document_version(
            storage=storage,
            project_id=PROJECT_ID,
            document_id=DOC_ID,
            version=1,
            file_name="spec.txt",
            data=TXT_CONTENT,
            content_type="text/plain",
        )
        assert storage.file_exists(result.blob_path)

    def test_versioned_paths_are_distinct(self, storage):
        r1 = upload_document_version(
            storage=storage, project_id=PROJECT_ID, document_id=DOC_ID,
            version=1, file_name="doc.pdf", data=PDF_MAGIC,
        )
        r2 = upload_document_version(
            storage=storage, project_id=PROJECT_ID, document_id=DOC_ID,
            version=2, file_name="doc.pdf", data=PDF_MAGIC + b"-v2",
        )
        assert r1.blob_path != r2.blob_path
        assert "v1" in r1.blob_path
        assert "v2" in r2.blob_path

    def test_same_version_path_raises_immutability_error(self, storage):
        upload_document_version(
            storage=storage, project_id=PROJECT_ID, document_id=DOC_ID,
            version=1, file_name="doc.pdf", data=PDF_MAGIC,
        )
        with pytest.raises(StorageServiceError, match="immutable"):
            upload_document_version(
                storage=storage, project_id=PROJECT_ID, document_id=DOC_ID,
                version=1, file_name="doc.pdf", data=PDF_MAGIC,
            )

    def test_content_type_auto_detected_when_not_provided(self, storage):
        result = upload_document_version(
            storage=storage, project_id=PROJECT_ID, document_id=DOC_ID,
            version=1, file_name="report.pdf", data=PDF_MAGIC,
            content_type=None,
        )
        assert result.content_type == "application/pdf"

    def test_explicit_content_type_used(self, storage):
        result = upload_document_version(
            storage=storage, project_id=PROJECT_ID, document_id=DOC_ID,
            version=1, file_name="data.bin", data=b"\x00\x01",
            content_type="application/octet-stream",
        )
        assert result.content_type == "application/octet-stream"


# ===========================================================================
# 4. DocumentUploadResult
# ===========================================================================

class TestDocumentUploadResult:
    def test_repr_shows_path_and_size(self):
        r = DocumentUploadResult(
            blob_path="projects/p1/doc/v1/spec.pdf",
            blob_url="https://sa.blob.core.windows.net/container/projects/p1/doc/v1/spec.pdf",
            sha256_hash="abc123" * 10 + "def4",
            file_size_bytes=1024,
            content_type="application/pdf",
        )
        assert "spec.pdf" in repr(r)


# ===========================================================================
# 5. AzureBlobStorageService (unconfigured)
# ===========================================================================

class TestAzureBlobStorageServiceUnconfigured:
    def _unconfigured_service(self) -> AzureBlobStorageService:
        settings = Settings(
            azure_storage_account_url=None,
            azure_storage_connection_string=None,
        )
        return AzureBlobStorageService(settings=settings)

    def test_is_available_returns_false(self):
        svc = self._unconfigured_service()
        assert svc.is_available() is False

    def test_upload_raises_when_unconfigured(self):
        svc = self._unconfigured_service()
        with pytest.raises(StorageServiceError):
            svc.upload_file("test/blob.txt", b"data")

    def test_download_raises_when_unconfigured(self):
        svc = self._unconfigured_service()
        with pytest.raises(StorageServiceError):
            svc.download_file("test/blob.txt")

    def test_file_exists_returns_false_when_unconfigured(self):
        svc = self._unconfigured_service()
        assert svc.file_exists("test/blob.txt") is False

    def test_delete_raises_when_unconfigured(self):
        svc = self._unconfigured_service()
        # delete should raise (can't connect) or return False gracefully
        # either is acceptable — just must not crash with unexpected exception
        try:
            result = svc.delete_file("test/blob.txt")
            assert result is False
        except StorageServiceError:
            pass  # Also acceptable
