"""
Google Gemini AI provider for commitguard Layer 2.

Uses the google-genai SDK. Requires the GOOGLE_API_KEY environment variable.
Install: pip install google-genai
"""
from __future__ import annotations

import json
import logging
import os
import re
import warnings

from src.credentials import get_credential
from src.providers.base import AIIssue, AIProvider, AIResult

_DEFAULT_MODEL = "gemini-3.5-flash-lite"

# Matches a JSON object inside a fenced code block (```json ... ```)
_FENCED_JSON_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)
# Matches a bare JSON object anywhere in the text
_BARE_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


class GeminiProvider(AIProvider):
    """
    AI provider backed by Google Gemini via the google-genai SDK.

    Attributes:
        model: Gemini model identifier string.
        timeout: Maximum seconds to wait for a Gemini response.
    """

    def __init__(
        self,
        model: str = _DEFAULT_MODEL,
        timeout: int = 10,
        api_key: str | None = None,
    ) -> None:
        self.model = model
        self.timeout = timeout
        self.api_key = api_key
        self._client = None

    def _resolve_api_key(self) -> str | None:
        """Resolve API key from constructor argument or credentials file."""
        return self.api_key or get_credential("gemini")

    def is_available(self) -> bool:
        """Return True if an API key is present in credentials."""
        return bool(self._resolve_api_key())

    def _get_client(self):
        """Lazily initialize and cache the Gemini API client."""
        if self._client is None:
            try:
                import google.genai as genai  # type: ignore[import-untyped]
            except ImportError as exc:
                raise RuntimeError(
                    "google-genai is not installed. Run: pip install google-genai"
                ) from exc
            key = self._resolve_api_key()
            if not key:
                raise RuntimeError(
                    "Gemini API key is not configured. Run: git auth set gemini <your_key>"
                )
            logging.getLogger("google_genai").setLevel(logging.ERROR)
            logging.getLogger("google").setLevel(logging.ERROR)
            self._client = genai.Client(api_key=key)
        return self._client

    def analyze(self, prompt: str) -> AIResult:
        """
        Send prompt to Gemini and return a structured AIResult.

        Args:
            prompt: Formatted commit analysis prompt.

        Returns:
            AIResult parsed from the model's JSON response.
            Falls back to AIResult(passed=True) on any parse failure (fail-open).
        """
        client = self._get_client()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            response = client.models.generate_content(
                model=self.model,
                contents=prompt,
            )
        return _parse_response(response.text)


def _parse_response(text: str) -> AIResult:
    """
    Extract and parse the JSON result block from a Gemini text response.

    Tries a fenced code block first, then a bare JSON object.
    Returns AIResult(passed=True) on any parse failure (fail-open).

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
            return _build_result(data)
        except (json.JSONDecodeError, TypeError, AttributeError):
            pass

    return AIResult(passed=True, issues=[])


def _build_result(data: dict) -> AIResult:
    """Convert a parsed JSON dict into an AIResult."""
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
