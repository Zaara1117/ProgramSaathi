"""Unit tests for Azure AI Foundry / Azure OpenAI service integration and safety boundaries."""

from unittest.mock import MagicMock
import pytest
from pydantic import BaseModel, Field

from programsaathi.config import Settings
from programsaathi.exceptions import LLMServiceError, ValidationError
from programsaathi.services.llm import FoundryLLMService, MockLLMService
from programsaathi.prompts.templates import (
    ProjectUnderstandingResult,
    RequirementExtractionResult,
    format_grounded_prompt,
)


class DummyOutputSchema(BaseModel):
    title: str = Field(..., description="Title of the output")
    priority_level: int = Field(..., ge=1, le=5, description="Priority rating 1 to 5")


# ------------------------------------------------------------------------------
# 1. Configuration & Unconfigured Service Tests
# ------------------------------------------------------------------------------

def test_foundry_unconfigured_availability():
    unconfigured_settings = Settings(
        foundry_project_endpoint=None,
        azure_openai_endpoint=None,
        azure_openai_api_key=None,
    )
    service = FoundryLLMService(settings=unconfigured_settings)
    assert service.is_available() is False

    with pytest.raises(LLMServiceError) as exc_info:
        service.generate_text("Ping")
    assert "not configured" in str(exc_info.value).lower()

    with pytest.raises(LLMServiceError):
        service.generate_structured("Ping", DummyOutputSchema)

    with pytest.raises(LLMServiceError):
        service.generate_grounded("Ping", schema=DummyOutputSchema)


def test_foundry_configured_with_endpoint_or_key():
    settings_endpoint = Settings(azure_openai_endpoint="https://myresource.openai.azure.com")
    service1 = FoundryLLMService(settings=settings_endpoint)
    assert service1.is_available() is True

    settings_key = Settings(azure_openai_api_key="sk-fake-test-key")
    service2 = FoundryLLMService(settings=settings_key)
    assert service2.is_available() is True


# ------------------------------------------------------------------------------
# 2. Successful Structured LLM Responses (Mocked AzureOpenAI Client)
# ------------------------------------------------------------------------------

def test_successful_structured_output_via_parse():
    # Setup mock AzureOpenAI client and parsed message
    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.refusal = None
    mock_choice.message.parsed = DummyOutputSchema(title="MVP Delivery", priority_level=1)

    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]
    mock_client.beta.chat.completions.parse.return_value = mock_completion

    settings = Settings(
        azure_openai_endpoint="https://myresource.openai.azure.com",
        azure_openai_api_key="fake-key",
    )
    service = FoundryLLMService(settings=settings, client=mock_client)

    result = service.generate_structured(
        prompt="Extract delivery details",
        schema=DummyOutputSchema,
        system_prompt="Custom PM prompt",
    )

    assert isinstance(result, DummyOutputSchema)
    assert result.title == "MVP Delivery"
    assert result.priority_level == 1
    mock_client.beta.chat.completions.parse.assert_called_once()


def test_successful_structured_output_fallback_raw_json():
    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.refusal = None
    mock_choice.message.parsed = None
    mock_choice.message.content = '{"title": "Architecture Signoff", "priority_level": 2}'

    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]
    mock_client.beta.chat.completions.parse.return_value = mock_completion

    settings = Settings(azure_openai_endpoint="https://myresource.openai.azure.com", azure_openai_api_key="fake-key")
    service = FoundryLLMService(settings=settings, client=mock_client)

    result = service.generate_structured(prompt="Parse JSON", schema=DummyOutputSchema)
    assert isinstance(result, DummyOutputSchema)
    assert result.title == "Architecture Signoff"
    assert result.priority_level == 2


# ------------------------------------------------------------------------------
# 3. Invalid LLM Responses Handling & Boundary Checks
# ------------------------------------------------------------------------------

def test_invalid_structured_output_raises_validation_error():
    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.refusal = None
    mock_choice.message.parsed = None
    # Invalid: priority_level is string instead of int or missing required fields
    mock_choice.message.content = '{"title": "Invalid Story", "priority_level": 99}'

    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]
    mock_client.beta.chat.completions.parse.return_value = mock_completion

    settings = Settings(azure_openai_endpoint="https://myresource.openai.azure.com", azure_openai_api_key="fake-key")
    service = FoundryLLMService(settings=settings, client=mock_client)

    with pytest.raises(ValidationError) as exc_info:
        service.generate_structured(prompt="Extract", schema=DummyOutputSchema)

    assert "schema validation" in str(exc_info.value).lower()
    assert exc_info.value.details.get("schema") == "DummyOutputSchema"


def test_model_refusal_raises_llm_service_error():
    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.refusal = "I cannot fulfill this request due to policy."

    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]
    mock_client.beta.chat.completions.parse.return_value = mock_completion

    settings = Settings(azure_openai_endpoint="https://myresource.openai.azure.com", azure_openai_api_key="fake-key")
    service = FoundryLLMService(settings=settings, client=mock_client)

    with pytest.raises(LLMServiceError) as exc_info:
        service.generate_structured(prompt="Forbidden task", schema=DummyOutputSchema)

    assert "refused" in str(exc_info.value).lower()


def test_llm_call_failure_raises_explicit_service_error():
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = RuntimeError("Connection timeout to Azure endpoint")

    settings = Settings(azure_openai_endpoint="https://myresource.openai.azure.com", azure_openai_api_key="fake-key")
    service = FoundryLLMService(settings=settings, client=mock_client)

    with pytest.raises(LLMServiceError) as exc_info:
        service.generate_text("Hello")

    assert "generation failed" in str(exc_info.value).lower()


# ------------------------------------------------------------------------------
# 4. Grounded Prompt Pipeline
# ------------------------------------------------------------------------------

def test_generate_grounded_calls_structured():
    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.refusal = None
    mock_choice.message.parsed = DummyOutputSchema(title="Grounded Milestone", priority_level=3)

    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]
    mock_client.beta.chat.completions.parse.return_value = mock_completion

    settings = Settings(azure_openai_endpoint="https://myresource.openai.azure.com", azure_openai_api_key="fake-key")
    service = FoundryLLMService(settings=settings, client=mock_client)

    result = service.generate_grounded(
        user_request="What is the next milestone?",
        project_context={"project_id": "p-1", "name": "Cloud Portal"},
        retrieved_evidence=[{"title": "PRD section 3", "content": "Launch in Q4"}],
        schema=DummyOutputSchema,
    )

    assert isinstance(result, DummyOutputSchema)
    assert result.title == "Grounded Milestone"


# ------------------------------------------------------------------------------
# 5. MockLLMService Functionality & Error Simulation
# ------------------------------------------------------------------------------

def test_mock_llm_service_structured_and_error_simulation():
    mock_service = MockLLMService()
    canned = DummyOutputSchema(title="Mocked Item", priority_level=1)
    mock_service.register_structured_response(DummyOutputSchema, canned)

    res = mock_service.generate_structured("Prompt", DummyOutputSchema)
    assert res.title == "Mocked Item"
    assert len(mock_service.recorded_calls) == 1

    # Test error simulation
    error_mock = MockLLMService(simulate_error=ValidationError("Simulated parsing failure"))
    with pytest.raises(ValidationError):
        error_mock.generate_text("Prompt")
    with pytest.raises(ValidationError):
        error_mock.generate_structured("Prompt", DummyOutputSchema)
