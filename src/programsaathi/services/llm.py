"""Foundry and Azure OpenAI reasoning service interface and production implementation."""

from abc import abstractmethod
from typing import Any, Optional, Type, TypeVar, Union
from pydantic import BaseModel

from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

from programsaathi.config import Settings, get_settings
from programsaathi.exceptions import LLMServiceError, ValidationError
from programsaathi.logging import get_logger
from programsaathi.prompts.system import PROGRAMSAATHI_SYSTEM_PROMPT
from programsaathi.prompts.templates import format_grounded_prompt
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

    @abstractmethod
    def generate_grounded(
        self,
        user_request: str,
        project_context: Optional[Union[dict[str, Any], str]] = None,
        retrieved_evidence: Optional[list[Union[dict[str, Any], str]]] = None,
        system_prompt: Optional[str] = None,
        schema: Optional[Type[T]] = None,
        temperature: float = 0.2,
        **kwargs: Any,
    ) -> Union[T, str]:
        """Generates a response grounded in authoritative project context and retrieved evidence."""
        pass


class FoundryLLMService(LLMServiceInterface):
    """Production service for Azure AI Foundry / Azure OpenAI.

    Connects via AzureOpenAI client using either API key or DefaultAzureCredential.
    Guarantees structured outputs via Pydantic parsing and ensures safety boundaries.
    """

    def __init__(
        self,
        settings: Optional[Settings] = None,
        client: Optional[AzureOpenAI] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._client: Optional[AzureOpenAI] = client

    def is_available(self) -> bool:
        """Checks if required configuration is present."""
        return self.settings.is_llm_configured

    def _get_client(self) -> AzureOpenAI:
        """Lazily initializes and caches the AzureOpenAI client with appropriate credentials."""
        if self._client is not None:
            return self._client

        endpoint = self.settings.effective_llm_endpoint
        if not endpoint:
            raise LLMServiceError(
                "Foundry / Azure OpenAI endpoint not configured. Set AZURE_OPENAI_ENDPOINT or FOUNDRY_PROJECT_ENDPOINT.",
                details={"configured": False, "model": self.settings.effective_llm_model},
            )

        api_version = self.settings.azure_openai_api_version

        # Priority 1: API key if explicitly provided and use_azure_ad is not forced
        if self.settings.azure_openai_api_key and not self.settings.use_azure_ad:
            logger.debug("Initializing AzureOpenAI client with API key authentication")
            try:
                self._client = AzureOpenAI(
                    azure_endpoint=endpoint,
                    api_key=self.settings.azure_openai_api_key,
                    api_version=api_version,
                )
            except Exception as exc:
                logger.error(f"Failed to initialize AzureOpenAI client with API key: {exc}")
                raise LLMServiceError(
                    f"Azure OpenAI client initialization failed: {exc}",
                    details={"endpoint": endpoint, "error": str(exc)},
                ) from exc
        # Priority 2: Entra ID via DefaultAzureCredential
        else:
            logger.debug("Initializing AzureOpenAI client with DefaultAzureCredential")
            try:
                token_provider = get_bearer_token_provider(
                    DefaultAzureCredential(),
                    "https://cognitiveservices.azure.com/.default",
                )
                self._client = AzureOpenAI(
                    azure_endpoint=endpoint,
                    azure_ad_token_provider=token_provider,
                    api_version=api_version,
                )
            except Exception as exc:
                logger.error(f"Failed to initialize AzureOpenAI client with DefaultAzureCredential: {exc}")
                raise LLMServiceError(
                    f"Failed to initialize Azure AD authentication via DefaultAzureCredential: {exc}",
                    details={"endpoint": endpoint, "error": str(exc)},
                ) from exc

        return self._client

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
                details={"model": self.settings.effective_llm_model},
            )

        client = self._get_client()
        sys_prompt = system_prompt or PROGRAMSAATHI_SYSTEM_PROMPT
        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": prompt},
        ]
        model = self.settings.effective_llm_model

        try:
            logger.info(f"Dispatching text reasoning request to Azure OpenAI (model={model})")
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                **kwargs,
            )
            content = response.choices[0].message.content
            return content or ""
        except Exception as exc:
            logger.error(f"Azure OpenAI generate_text call failed: {exc}")
            raise LLMServiceError(
                f"Azure OpenAI generation failed: {exc}",
                details={"model": model, "error": str(exc)},
            ) from exc

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
                details={"model": self.settings.effective_llm_model, "schema": schema.__name__},
            )

        client = self._get_client()
        sys_prompt = system_prompt or PROGRAMSAATHI_SYSTEM_PROMPT
        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": prompt},
        ]
        model = self.settings.effective_llm_model

        try:
            logger.info(f"Dispatching structured reasoning request to Azure OpenAI (model={model}, schema={schema.__name__})")
            completion = client.beta.chat.completions.parse(
                model=model,
                messages=messages,
                response_format=schema,
                temperature=temperature,
                **kwargs,
            )
            choice = completion.choices[0]

            # Check if model refused request
            refusal = getattr(choice.message, "refusal", None)
            if refusal:
                raise LLMServiceError(
                    f"Model refused request: {refusal}",
                    details={"refusal": refusal, "schema": schema.__name__},
                )

            parsed = choice.message.parsed
            if parsed is not None:
                return parsed

            # Fallback parsing on raw response content
            raw_content = choice.message.content or ""
            try:
                return schema.model_validate_json(raw_content)
            except Exception as val_exc:
                logger.error(f"Model raw output failed schema validation for {schema.__name__}: {val_exc}")
                raise ValidationError(
                    f"Model output failed schema validation for {schema.__name__}: {val_exc}",
                    details={"raw_content": raw_content, "schema": schema.__name__},
                ) from val_exc

        except ValidationError:
            # Re-raise explicit ValidationError without masking
            raise
        except LLMServiceError:
            raise
        except Exception as exc:
            err_str = str(exc)
            if "validation" in err_str.lower() or "did not match schema" in err_str.lower() or "json" in err_str.lower():
                logger.error(f"Schema validation failure from LLM response: {err_str}")
                raise ValidationError(
                    f"Model output failed schema validation for {schema.__name__}: {err_str}",
                    details={"schema": schema.__name__, "error": err_str},
                ) from exc
            logger.error(f"Azure OpenAI structured reasoning call failed: {exc}")
            raise LLMServiceError(
                f"Azure OpenAI structured generation failed: {exc}",
                details={"model": model, "schema": schema.__name__, "error": err_str},
            ) from exc

    def generate_grounded(
        self,
        user_request: str,
        project_context: Optional[Union[dict[str, Any], str]] = None,
        retrieved_evidence: Optional[list[Union[dict[str, Any], str]]] = None,
        system_prompt: Optional[str] = None,
        schema: Optional[Type[T]] = None,
        temperature: float = 0.2,
        **kwargs: Any,
    ) -> Union[T, str]:
        prompt = format_grounded_prompt(
            user_request=user_request,
            project_context=project_context,
            retrieved_evidence=retrieved_evidence,
        )
        if schema is not None:
            return self.generate_structured(
                prompt=prompt,
                schema=schema,
                system_prompt=system_prompt,
                temperature=temperature,
                **kwargs,
            )
        return self.generate_text(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            **kwargs,
        )


class MockLLMService(LLMServiceInterface):
    """Test-double service for local deterministic testing without cloud round-trips."""

    def __init__(
        self,
        fixed_text_response: str = "Test LLM output",
        canned_structured_responses: Optional[dict[Type[BaseModel], BaseModel]] = None,
        simulate_error: Optional[Exception] = None,
    ) -> None:
        self.fixed_text_response = fixed_text_response
        self.canned_structured_responses: dict[Type[BaseModel], BaseModel] = canned_structured_responses or {}
        self.simulate_error = simulate_error
        self.recorded_calls: list[dict[str, Any]] = []

    def is_available(self) -> bool:
        return True

    def register_structured_response(self, schema: Type[T], instance: T) -> None:
        """Registers a canned Pydantic response for a specific schema."""
        self.canned_structured_responses[schema] = instance

    def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        **kwargs: Any,
    ) -> str:
        if self.simulate_error:
            raise self.simulate_error
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
        if self.simulate_error:
            raise self.simulate_error
        self.recorded_calls.append({"prompt": prompt, "schema": schema.__name__})

        if schema in self.canned_structured_responses:
            return self.canned_structured_responses[schema]  # type: ignore

        try:
            return schema.model_validate({})
        except Exception:
            raise LLMServiceError(f"MockLLMService cannot construct default instance for schema {schema.__name__}")

    def generate_grounded(
        self,
        user_request: str,
        project_context: Optional[Union[dict[str, Any], str]] = None,
        retrieved_evidence: Optional[list[Union[dict[str, Any], str]]] = None,
        system_prompt: Optional[str] = None,
        schema: Optional[Type[T]] = None,
        temperature: float = 0.2,
        **kwargs: Any,
    ) -> Union[T, str]:
        if self.simulate_error:
            raise self.simulate_error

        self.recorded_calls.append({
            "user_request": user_request,
            "project_context": project_context,
            "retrieved_evidence": retrieved_evidence,
            "schema": schema.__name__ if schema else None,
        })

        if schema is not None:
            return self.generate_structured(
                prompt=user_request,
                schema=schema,
                system_prompt=system_prompt,
                temperature=temperature,
                **kwargs,
            )
        return self.generate_text(
            prompt=user_request,
            system_prompt=system_prompt,
            temperature=temperature,
            **kwargs,
        )
