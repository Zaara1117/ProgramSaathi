"""Document and DocumentVersion domain entities for ingestion and RAG tracking."""

from enum import Enum
from typing import Optional
from pydantic import Field
from programsaathi.models.base import BaseEntity


class DocumentType(str, Enum):
    """Classification of project documentation."""
    PRD = "PRD"
    ARCHITECTURE = "ARCHITECTURE"
    MEETING_NOTES = "MEETING_NOTES"
    STATUS_REPORT = "STATUS_REPORT"
    SPECIFICATION = "SPECIFICATION"
    CONTRACT = "CONTRACT"
    OTHER = "OTHER"


class Document(BaseEntity):
    """Root document descriptor stored within project catalog."""

    project_id: str = Field(..., description="Parent Project UUID")
    title: str = Field(..., description="Document display name")
    document_type: DocumentType = Field(default=DocumentType.OTHER, description="Category of document")
    latest_version: int = Field(default=1, ge=1, description="Latest revision number")
    primary_blob_url: Optional[str] = Field(default=None, description="Azure Blob URL of canonical copy")
    summary: Optional[str] = Field(default=None, description="Synthesized executive summary")
    is_active: bool = Field(default=True, description="Whether document is actively referenced in RAG")


class DocumentVersion(BaseEntity):
    """Specific revision of an uploaded project document."""

    document_id: str = Field(..., description="Parent Document UUID")
    version_number: int = Field(default=1, ge=1, description="Revision sequence number")
    file_name: str = Field(..., description="Original uploaded filename")
    content_type: str = Field(..., description="MIME content type (e.g., application/pdf)")
    file_size_bytes: int = Field(default=0, ge=0, description="Size in bytes")
    blob_path: str = Field(..., description="Azure Blob Storage relative path")
    sha256_hash: str = Field(..., description="SHA-256 cryptographic digest of document content")
    uploaded_by: Optional[str] = Field(default=None, description="Stakeholder UUID who uploaded the file")
    is_indexed: bool = Field(default=False, description="Whether chunks are indexed into Azure AI Search")
    chunk_count: int = Field(default=0, ge=0, description="Number of text chunks generated for search")
