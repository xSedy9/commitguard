"""
Abstract AI provider interface for commitguard Layer 2.

All LLM backends must implement AIProvider. The validation engine
interacts exclusively with this interface and has no knowledge of the
underlying model, SDK, or transport layer.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class AIIssue:
    """A single issue detected by the AI analysis."""

    category: str
    """Short identifier: 'language', 'debug_code', 'atomicity', 'mismatch'."""

    message: str
    """Brief human-readable label shown in the rejection report."""

    detail: str
    """Full explanation and remediation hint shown below the label."""


@dataclass
class AIResult:
    """
    Structured result returned by any AIProvider.analyze() call.

    Attributes:
        passed: True if the commit passed all AI checks.
        issues: List of detected issues (empty when passed=True).
    """

    passed: bool
    issues: list[AIIssue] = field(default_factory=list)


class AIProvider(ABC):
    """
    Universal interface for all AI backends.

    Implement this abstract class to add a new LLM provider.
    The validation engine calls only analyze() and is_available().

    Contract:
    - analyze() must always return an AIResult (never raise).
      Handle internal errors by returning AIResult(passed=True) (fail-open).
    - is_available() must be cheap and side-effect-free (no network calls).
    """

    @abstractmethod
    def analyze(self, prompt: str) -> AIResult:
        """
        Send the prompt to the underlying LLM and return a structured result.

        Args:
            prompt: Fully-formatted analysis prompt including the commit
                    message, staged file list, and diff.

        Returns:
            AIResult(passed=True, issues=[]) on success,
            AIResult(passed=False, issues=[...]) on detected problems.
        """
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check whether this provider can be used in the current environment.

        Returns True only if all required credentials and/or dependencies
        are present. Must NOT make any network calls.
        """
        ...
