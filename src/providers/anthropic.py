"""
Anthropic Claude provider for commitguard Layer 2.

Uses the anthropic SDK. Requires the ANTHROPIC_API_KEY environment variable.
Install: pip install anthropic
"""
from __future__ import annotations

import json
import os
import re

from src.providers.base import AIIssue, AIProvider, AIResult

_DEFAULT_MODEL = "claude-haiku-4-5"

_FENCED_JSON_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)
_BARE_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


class AnthropicProvider(AIProvider):
    """
    AI provider backed by Anthropic Claude via the anthropic SDK.

    Attributes:
        model: Claude model identifier (e.g. 'claude-haiku-4-5').
        timeout: HTTP request timeout in seconds.
    """

    def __init__(
        self,
        model: str = _DEFAULT_MODEL,
        timeout: int = 10,
    ) -> None:
        self.model = model
        self.timeout = timeout
        self._client = None

    def is_available(self) -> bool:
        """Return True if ANTHROPIC_API_KEY is present in the environment."""
        return bool(os.environ.get("ANTHROPIC_API_KEY"))

    def _get_client(self):
        """Lazily initialize and cache the Anthropic client."""
        if self._client is None:
            try:
                import anthropic  # type: ignore[import-untyped]
            except ImportError as exc:
                raise RuntimeError(
                    "anthropic is not installed. Run: pip install anthropic"
                ) from exc
            self._client = anthropic.Anthropic(
                api_key=os.environ["ANTHROPIC_API_KEY"],
                timeout=float(self.timeout),
            )
        return self._client

    def analyze(self, prompt: str) -> AIResult:
        """
        Send prompt to Claude and return a structured AIResult.

        Args:
            prompt: Formatted commit analysis prompt.

        Returns:
            AIResult parsed from the messages API response.
            Falls back to AIResult(passed=True) on any parse failure.
        """
        client = self._get_client()
        message = client.messages.create(
            model=self.model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        text = message.content[0].text if message.content else ""
        return _parse_response(text)


def _parse_response(text: str) -> AIResult:
    """
    Extract and parse the JSON result block from an Anthropic response.

    Falls back to AIResult(passed=True) on any parse failure (fail-open).

    Args:
        text: Raw model response text.

    Returns:
        Parsed AIResult.
    """
    raw: str | None = None

    m = _FENCED_JSON_RE.search(text)
    if m:
        raw = m.group(1)
    else:
        m2 = _BARE_JSON_RE.search(text)
        if m2:
            raw = m2.group(0)

    if raw:
        try:
            data = json.loads(raw)
            passed = bool(data.get("passed", True))
            issues = [
                AIIssue(
                    category=i.get("category", "unknown"),
                    message=i.get("message", ""),
                    detail=i.get("detail", ""),
                )
                for i in data.get("issues", [])
                if isinstance(i, dict)
            ]
            return AIResult(passed=passed, issues=issues)
        except (json.JSONDecodeError, TypeError, AttributeError):
            pass

    return AIResult(passed=True, issues=[])
