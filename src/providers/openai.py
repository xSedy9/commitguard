"""
OpenAI / Azure OpenAI provider for commitguard Layer 2.

Uses the openai SDK. Requires the OPENAI_API_KEY environment variable.
For Azure OpenAI also set AZURE_OPENAI_ENDPOINT.
Install: pip install openai
"""
from __future__ import annotations

import json
import os
import re

from src.providers.base import AIIssue, AIProvider, AIResult

_DEFAULT_MODEL = "gpt-4o-mini"

_FENCED_JSON_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)
_BARE_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


class OpenAIProvider(AIProvider):
    """
    AI provider backed by OpenAI (or Azure OpenAI) via the openai SDK.

    Attributes:
        model: OpenAI model identifier (e.g. 'gpt-4o-mini', 'gpt-4o').
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
        """Return True if OPENAI_API_KEY is present in the environment."""
        return bool(os.environ.get("OPENAI_API_KEY"))

    def _get_client(self):
        """Lazily initialize and cache the OpenAI client."""
        if self._client is None:
            try:
                import openai  # type: ignore[import-untyped]
            except ImportError as exc:
                raise RuntimeError(
                    "openai is not installed. Run: pip install openai"
                ) from exc
            self._client = openai.OpenAI(
                api_key=os.environ["OPENAI_API_KEY"],
                timeout=float(self.timeout),
            )
        return self._client

    def analyze(self, prompt: str) -> AIResult:
        """
        Send prompt to OpenAI and return a structured AIResult.

        Args:
            prompt: Formatted commit analysis prompt.

        Returns:
            AIResult parsed from the chat completion response.
            Falls back to AIResult(passed=True) on any parse failure.
        """
        client = self._get_client()
        response = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            timeout=self.timeout,
        )
        text = response.choices[0].message.content or ""
        return _parse_response(text)


def _parse_response(text: str) -> AIResult:
    """
    Extract and parse the JSON result block from an OpenAI response.

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
