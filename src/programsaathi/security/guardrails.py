"""Security guardrails, SQL injection detection, and mutation authorization checks."""

import re
from typing import Any
from programsaathi.exceptions import SecurityViolationError
from programsaathi.logging import get_logger

logger = get_logger(__name__)

# Patterns indicative of raw SQL manipulation attempts
SQL_INJECTION_PATTERNS = [
    re.compile(r"(\bDROP\b\s+\bTABLE\b)", re.IGNORECASE),
    re.compile(r"(\bTRUNCATE\b\s+\bTABLE\b)", re.IGNORECASE),
    re.compile(r"(\bALTER\b\s+\bTABLE\b)", re.IGNORECASE),
    re.compile(r"(\bEXEC\b|\bEXECUTE\b)\s*\(", re.IGNORECASE),
    re.compile(r"(--|;|\/\*|\*\/)", re.IGNORECASE),
    re.compile(r"(\bUNION\b\s+\bSELECT\b)", re.IGNORECASE),
    re.compile(r"(\bSELECT\b\s+.*\s+\bFROM\b)", re.IGNORECASE),
    re.compile(r"(\bUPDATE\b\s+.*\s+\bSET\b)", re.IGNORECASE),
    re.compile(r"(\bDELETE\b\s+\bFROM\b)", re.IGNORECASE),
]


class SecurityGuard:
    """Enforces non-negotiable architectural boundaries and sanitization rules."""

    @staticmethod
    def inspect_text_input(text: str, context_label: str = "input") -> None:
        """Inspects arbitrary string inputs to prevent raw SQL injection or prompt exploitation."""
        for pattern in SQL_INJECTION_PATTERNS:
            if pattern.search(text):
                logger.error(
                    f"Security violation detected in {context_label}: matched SQL injection pattern",
                    extra={"pattern": pattern.pattern},
                )
                raise SecurityViolationError(
                    f"Input in {context_label} violated security policy: direct SQL or dangerous patterns forbidden.",
                    details={"matched_pattern": pattern.pattern},
                )

    @classmethod
    def inspect_payload(cls, data: Any, context_label: str = "payload") -> None:
        """Recursively inspects dictionary, list, or string payloads."""
        if isinstance(data, str):
            cls.inspect_text_input(data, context_label)
        elif isinstance(data, dict):
            for k, v in data.items():
                cls.inspect_payload(v, f"{context_label}.{k}")
        elif isinstance(data, list):
            for i, item in enumerate(data):
                cls.inspect_payload(item, f"{context_label}[{i}]")
