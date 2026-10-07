"""Document and DocumentVersion repositories."""

from programsaathi.models.document import Document, DocumentVersion
from programsaathi.repositories.base import BaseRepository, InMemoryRepository


class DocumentRepository(BaseRepository[Document]):
    pass


class InMemoryDocumentRepository(InMemoryRepository[Document], DocumentRepository):
    pass


class DocumentVersionRepository(BaseRepository[DocumentVersion]):
    def list_by_document(self, document_id: str) -> list[DocumentVersion]:
        raise NotImplementedError


class InMemoryDocumentVersionRepository(InMemoryRepository[DocumentVersion], DocumentVersionRepository):
    def list_by_document(self, document_id: str) -> list[DocumentVersion]:
        return [
            v for v in self._store.values()
            if v.document_id == document_id
        ]
