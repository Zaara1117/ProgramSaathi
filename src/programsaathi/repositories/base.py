"""Generic repository interface and in-memory base implementation."""

from abc import ABC, abstractmethod
from typing import Generic, Optional, TypeVar
from programsaathi.models.base import BaseEntity

T = TypeVar("T", bound=BaseEntity)


class BaseRepository(ABC, Generic[T]):
    """Generic repository interface defining standard CRUD contracts."""

    @abstractmethod
    def get_by_id(self, entity_id: str) -> Optional[T]:
        """Retrieves an entity by its UUID."""
        pass

    @abstractmethod
    def list_by_project(self, project_id: str, limit: int = 100, offset: int = 0) -> list[T]:
        """Lists entities associated with a specific project."""
        pass

    @abstractmethod
    def create(self, entity: T) -> T:
        """Persists a new entity."""
        pass

    @abstractmethod
    def update(self, entity: T) -> T:
        """Updates an existing entity."""
        pass

    @abstractmethod
    def delete(self, entity_id: str) -> bool:
        """Deletes an entity by UUID; returns True if removed."""
        pass


class InMemoryRepository(BaseRepository[T]):
    """Thread-safe in-memory repository implementation for unit testing and local development."""

    def __init__(self) -> None:
        self._store: dict[str, T] = {}

    def get_by_id(self, entity_id: str) -> Optional[T]:
        return self._store.get(entity_id)

    def list_by_project(self, project_id: str, limit: int = 100, offset: int = 0) -> list[T]:
        results = [
            item for item in self._store.values()
            if getattr(item, "project_id", None) == project_id
        ]
        return results[offset : offset + limit]

    def create(self, entity: T) -> T:
        self._store[entity.id] = entity
        return entity

    def update(self, entity: T) -> T:
        self._store[entity.id] = entity
        return entity

    def delete(self, entity_id: str) -> bool:
        if entity_id in self._store:
            del self._store[entity_id]
            return True
        return False
