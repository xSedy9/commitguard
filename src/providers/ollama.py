"""
Ollama local LLM provider for commitguard Layer 2.

Communicates with a locally running Ollama instance via its REST API.
No SDK or API key required — uses stdlib urllib only.

Default endpoint: http://localhost:11434
Default model:    llama3.2
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request

from src.providers.base import AIIssue, AIProvider, AIResult

_DEFAULT_ENDPOINT = "http://localhost:11434"
_DEFAULT_MODEL = "llama3.2"

_FENCED_JSON_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)
_BARE_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


class OllamaProvider(AIProvider):
    """
    AI provider backed by a locally running Ollama instance.

    Uses plain HTTP via stdlib urllib — no external SDK required.
    Local models may be slower; the default timeout is 30 s.

    Attributes:
        model: Ollama model name (e.g. 'llama3.2', 'mistral', 'codellama').
        endpoint: Base URL of the Ollama REST API.
        timeout: HTTP request timeout in seconds.
    """

    def __init__(
        self,
        model: str = _DEFAULT_MODEL,
        endpoint: str = _DEFAULT_ENDPOINT,
        timeout: int = 30,
    ) -> None:
        self.model = model
        self.endpoint = endpoint.rstrip("/")
        self.timeout = timeout

    def is_available(self) -> bool:
        """
        Return True if the Ollama server is reachable at the configured endpoint.

        Makes a lightweight GET request to /api/tags (Ollama health endpoint).
        No authentication required.
        """
        try:
            req = urllib.request.Request(f"{self.endpoint}/api/tags")
            with urllib.request.urlopen(req, timeout=3):
                return True
        except Exception:  # noqa: BLE001 — any connectivity failure means unavailable
            return False

    def analyze(self, prompt: str) -> AIResult:
        """
        Send prompt to the local Ollama server and return a structured AIResult.

        Args:
            prompt: Formatted commit analysis prompt.

        Returns:
            AIResult parsed from the generate API response.
            Falls back to AIResult(passed=True) on any failure.
        """
        payload = json.dumps(
            {"model": self.model, "prompt": prompt, "stream": False}
        ).encode()

        req = urllib.request.Request(
            f"{self.endpoint}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            data = json.loads(resp.read())

        text = data.get("response", "")
        return _parse_response(text)


def _parse_response(text: str) -> AIResult:
    """
    Extract and parse the JSON result block from an Ollama response.

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
