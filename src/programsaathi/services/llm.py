"""Foundry and Azure OpenAI reasoning service interface and implementation."""

from abc import abstractmethod
from typing import Any, Optional, Type, TypeVar
from pydantic import BaseModel

from programsaathi.config import Settings, get_settings
from programsaathi.exceptions import LLMServiceError
from programsaathi.logging import get_logger
from programsaathi.services.base import BaseService

logger = get_logger(__name__)
T = TypeVar("T", bound=BaseModel)


class LLMServiceInterface(BaseService):
    """Interface for reasoning, interpretation, and structured output generation."""

    @abstractmethod
    def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        **kwargs: Any,
    ) -> str:
        """Generates raw text response given prompt and system instructions."""
        pass

    @abstractmethod
    def generate_structured(
        self,
        prompt: str,
        schema: Type[T],
        system_prompt: Optional[str] = None,
        temperature: float = 0.0,
        **kwargs: Any,
    ) -> T:
        """Generates a response validated against a target Pydantic schema."""
        pass


class FoundryLLMService(LLMServiceInterface):
    """Production service for Azure AI Foundry / Azure OpenAI.

    Enforces structured output parsing and clean error boundaries.
    """

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()

    def is_available(self) -> bool:
        return self.settings.is_llm_configured

    def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        **kwargs: Any,
    ) -> str:
        if not self.is_available():
            raise LLMServiceError(
                "Foundry / Azure OpenAI endpoint or key not configured in environment.",
                details={"model": self.settings.foundry_model},
            )
        logger.info(
            "Dispatched reasoning request to Foundry",
            extra={"model": self.settings.foundry_model},
        )
        # Concrete Azure OpenAI client SDK calls will be linked in Azure integration phase
        raise NotImplementedError("Live Azure Foundry client invocation will be integrated in Phase 4.")

    def generate_structured(
        self,
        prompt: str,
        schema: Type[T],
        system_prompt: Optional[str] = None,
        temperature: float = 0.0,
        **kwargs: Any,
    ) -> T:
        if not self.is_available():
            raise LLMServiceError(
                "Foundry / Azure OpenAI endpoint or key not configured in environment.",
                details={"model": self.settings.foundry_model, "schema": schema.__name__},
            )
        logger.info(
            "Dispatched structured reasoning request to Foundry",
            extra={"model": self.settings.foundry_model, "schema": schema.__name__},
        )
        raise NotImplementedError("Live Azure Foundry client invocation will be integrated in Phase 4.")


class MockLLMService(LLMServiceInterface):
    """Test-double service for local deterministic testing without cloud round-trips."""

    def __init__(self, fixed_text_response: str = "Test LLM output") -> None:
        self.fixed_text_response = fixed_text_response
        self.recorded_calls: list[dict[str, Any]] = []

    def is_available(self) -> bool:
        return True

    def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        **kwargs: Any,
    ) -> str:
        self.recorded_calls.append({"prompt": prompt, "system_prompt": system_prompt})
        return self.fixed_text_response

    def generate_structured(
        self,
        prompt: str,
        schema: Type[T],
        system_prompt: Optional[str] = None,
        temperature: float = 0.0,
        **kwargs: Any,
    ) -> T:
        self.recorded_calls.append({"prompt": prompt, "schema": schema.__name__})
        # Attempt to construct default or empty instance if possible
        try:
            return schema.model_validate({})
        except Exception:
            raise LLMServiceError(f"MockLLMService cannot construct default instance for schema {schema.__name__}")
