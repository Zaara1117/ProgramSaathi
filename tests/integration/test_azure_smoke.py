"""Smoke test for live Azure AI Foundry / Azure OpenAI integration.

Only runs when live credentials (AZURE_OPENAI_ENDPOINT / FOUNDRY_PROJECT_ENDPOINT)
and authentication (AZURE_OPENAI_API_KEY or DefaultAzureCredential) are actually configured.
"""

import os
import pytest
from programsaathi.config import get_settings
from programsaathi.services.llm import FoundryLLMService


def test_live_azure_foundry_connection_smoke():
    settings = get_settings()

    # Determine if live Azure OpenAI endpoint is configured
    has_endpoint = bool(settings.effective_llm_endpoint)
    has_key = bool(settings.azure_openai_api_key)
    has_azure_auth = bool(os.environ.get("AZURE_CLIENT_ID") or os.environ.get("AZURE_TENANT_ID"))

    if not has_endpoint or not (has_key or has_azure_auth or settings.use_azure_ad):
        pytest.skip(
            "Live Azure credentials are not configured in environment (.env). "
            "Skipping live Azure Foundry smoke test (expected in offline local development)."
        )

    service = FoundryLLMService(settings=settings)
    try:
        response = service.generate_text("Reply with 'READY' to verify ProgramSaathi reasoning link.")
        assert len(response.strip()) > 0
    except Exception as exc:
        pytest.fail(f"Live Azure Foundry smoke test failed with error: {exc}")
