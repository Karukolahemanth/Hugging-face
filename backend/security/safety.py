"""
Safety layer for GAIA Agent.
Validates requests before they reach the planner.
"""

import re
from backend.utils.logger import get_logger

logger = get_logger(__name__)

# ── Patterns that indicate dangerous intent ───────────────────────────────────
DANGEROUS_PATTERNS = [
    r"\bdelete\b.{0,30}\bfile\b",
    r"\bformat\b.{0,30}\bdrive\b",
    r"\brm\s+-rf\b",
    r"\bsudo\b",
    r"\bshutdown\b",
    r"\bexec\s*\(",
    r"__import__\s*\(",
    r"\beval\s*\(",
    r"\bos\.system\b",
    r"\bsubprocess\b",
    r"\bsend\b.{0,30}\bemail\b",
    r"\bsmtp\b",
    r"drop\s+table",
    r"truncate\s+table",
]

_COMPILED = [re.compile(p, re.IGNORECASE) for p in DANGEROUS_PATTERNS]


class SafetyResult:
    def __init__(self, safe: bool, reason: str = "") -> None:
        self.safe = safe
        self.reason = reason


def validate_request(text: str) -> SafetyResult:
    """
    Screen user input for obviously dangerous patterns.
    Returns SafetyResult(safe=True) if the request appears safe.
    """
    for pattern in _COMPILED:
        if pattern.search(text):
            logger.warning("Safety block — pattern matched: %s", pattern.pattern)
            return SafetyResult(
                safe=False,
                reason=(
                    "This request contains potentially dangerous content and "
                    "has been blocked. If this is legitimate, please rephrase your request."
                ),
            )
    return SafetyResult(safe=True)


def validate_code(code: str) -> SafetyResult:
    """Screen Python code for obviously unsafe patterns."""
    dangerous_code_patterns = [
        r"__import__\s*\(",
        r"open\s*\(.{0,200}['\"]w",       # file write
        r"os\.remove\b",
        r"shutil\.rmtree\b",
    ]
    for p in dangerous_code_patterns:
        if re.search(p, code, re.IGNORECASE):
            return SafetyResult(
                safe=False,
                reason=f"Code contains a restricted pattern: '{p}'.",
            )
    return SafetyResult(safe=True)
