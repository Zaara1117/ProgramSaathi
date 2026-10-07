"""Work item repositories: Requirement, UserStory, Task, and Dependency."""

from programsaathi.models.work_items import Requirement, UserStory, Task, Dependency
from programsaathi.repositories.base import BaseRepository, InMemoryRepository


class RequirementRepository(BaseRepository[Requirement]):
    """Repository interface for Requirements."""
    pass


class InMemoryRequirementRepository(InMemoryRepository[Requirement], RequirementRepository):
    """In-memory Requirement repository."""
    pass


class UserStoryRepository(BaseRepository[UserStory]):
    """Repository interface for UserStories."""
    pass


class InMemoryUserStoryRepository(InMemoryRepository[UserStory], UserStoryRepository):
    """In-memory UserStory repository."""
    pass


class TaskRepository(BaseRepository[Task]):
    """Repository interface for Tasks."""
    pass


class InMemoryTaskRepository(InMemoryRepository[Task], TaskRepository):
    """In-memory Task repository."""
    pass


class DependencyRepository(BaseRepository[Dependency]):
    """Repository interface for Dependencies."""
    pass


class InMemoryDependencyRepository(InMemoryRepository[Dependency], DependencyRepository):
    """In-memory Dependency repository."""
    pass
