"""Security tests verifying boundary enforcement and injection prevention."""

import pytest
from programsaathi.security.guardrails import SecurityGuard
from programsaathi.exceptions import SecurityViolationError


def test_benign_inputs_pass_inspection():
    SecurityGuard.inspect_text_input("Please summarize the project risks.")
    SecurityGuard.inspect_payload({"title": "Fix OAuth Token expiration", "details": "Token lasts 60m"})


@pytest.mark.parametrize(
    "malicious_input",
    [
        "DROP TABLE projects;",
        "'; TRUNCATE TABLE tasks; --",
        "UNION SELECT * FROM stakeholders",
        "EXEC(cmd)",
        "UPDATE tasks SET status='DONE' WHERE 1=1",
        "DELETE FROM requirements",
    ],
)
def test_sql_injection_patterns_detected_and_blocked(malicious_input: str):
    with pytest.raises(SecurityViolationError):
        SecurityGuard.inspect_text_input(malicious_input)


def test_nested_payload_injection_caught():
    malicious_dict = {
        "metadata": {
            "tags": ["prod", "critical"],
            "comment": "Nice project; DROP TABLE users; --",
        }
    }
    with pytest.raises(SecurityViolationError):
        SecurityGuard.inspect_payload(malicious_dict)
