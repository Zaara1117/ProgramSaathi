"""Unit tests for exception hierarchy."""

from programsaathi.exceptions import (
    ProgramSaathiError,
    HumanApprovalRequiredError,
    SecurityViolationError,
    ConfigurationError,
    LLMServiceError,
    ServiceUnavailableError,
)


def test_base_exception():
    err = ProgramSaathiError("Base error occurred", details={"code": 500})
    assert err.message == "Base error occurred"
    assert err.details["code"] == 500
    assert "ProgramSaathiError" in repr(err)


def test_human_approval_required_error():
    err = HumanApprovalRequiredError(
        "Human signoff needed",
        change_proposal_id="prop-789",
        details={"impact": "HIGH"},
    )
    assert err.change_proposal_id == "prop-789"
    assert err.details["change_proposal_id"] == "prop-789"
    assert err.details["impact"] == "HIGH"
    assert isinstance(err, ProgramSaathiError)


def test_service_error_inheritance():
    llm_err = LLMServiceError("Model quota exceeded")
    assert isinstance(llm_err, ServiceUnavailableError)
    assert isinstance(llm_err, ProgramSaathiError)
