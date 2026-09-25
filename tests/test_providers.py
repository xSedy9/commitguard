"""
Tests for all AI provider implementations.

All tests use mocking — no real API calls are made.
"""
from __future__ import annotations

import json
import os
from unittest.mock import MagicMock, patch

import pytest

from src.providers.base import AIIssue, AIProvider, AIResult
from src.providers.gemini import GeminiProvider, _parse_response as gemini_parse
from src.providers.openai import OpenAIProvider, _parse_response as openai_parse
from src.providers.anthropic import AnthropicProvider, _parse_response as anthropic_parse
from src.providers.ollama import OllamaProvider, _parse_response as ollama_parse
from src.providers import get_provider


# ── Helpers ──────────────────────────────────────────────────────────────────

def _ok_json() -> str:
    return json.dumps({"passed": True, "issues": []})


def _fail_json(category: str = "debug_code") -> str:
    return json.dumps(
        {
            "passed": False,
            "issues": [
                {
                    "category": category,
                    "message": "Test issue",
                    "detail": "Some detail",
                }
            ],
        }
    )


def _fenced(content: str) -> str:
    return f"```json\n{content}\n```"


# ── AIProvider interface ──────────────────────────────────────────────────────

class TestAIProviderInterface:
    """AIProvider is abstract and cannot be instantiated directly."""

    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            AIProvider()  # type: ignore[abstract]

    def test_concrete_must_implement_analyze(self):
        class Incomplete(AIProvider):
            def is_available(self) -> bool:
                return True

        with pytest.raises(TypeError):
            Incomplete()  # type: ignore[abstract]

    def test_concrete_must_implement_is_available(self):
        class Incomplete(AIProvider):
            def analyze(self, prompt: str) -> AIResult:
                return AIResult(passed=True)

        with pytest.raises(TypeError):
            Incomplete()  # type: ignore[abstract]


# ── _parse_response helpers ───────────────────────────────────────────────────

class TestParseResponse:
    """All four providers share the same parsing logic — test it centrally."""

    @pytest.mark.parametrize("parse_fn", [gemini_parse, openai_parse, anthropic_parse, ollama_parse])
    def test_passes_on_bare_json(self, parse_fn):
        result = parse_fn(_ok_json())
        assert result.passed is True
        assert result.issues == []

    @pytest.mark.parametrize("parse_fn", [gemini_parse, openai_parse, anthropic_parse, ollama_parse])
    def test_passes_on_fenced_json(self, parse_fn):
        result = parse_fn(_fenced(_ok_json()))
        assert result.passed is True

    @pytest.mark.parametrize("parse_fn", [gemini_parse, openai_parse, anthropic_parse, ollama_parse])
    def test_fail_result_populates_issues(self, parse_fn):
        result = parse_fn(_fail_json())
        assert result.passed is False
        assert len(result.issues) == 1
        assert result.issues[0].category == "debug_code"
        assert result.issues[0].message == "Test issue"

    @pytest.mark.parametrize("parse_fn", [gemini_parse, openai_parse, anthropic_parse, ollama_parse])
    def test_fail_open_on_empty_response(self, parse_fn):
        result = parse_fn("")
        assert result.passed is True
        assert result.issues == []

    @pytest.mark.parametrize("parse_fn", [gemini_parse, openai_parse, anthropic_parse, ollama_parse])
    def test_fail_open_on_invalid_json(self, parse_fn):
        result = parse_fn("not json at all")
        assert result.passed is True

    @pytest.mark.parametrize("parse_fn", [gemini_parse, openai_parse, anthropic_parse, ollama_parse])
    def test_fenced_takes_priority_over_bare(self, parse_fn):
        # Fenced block contains "passed: false", bare would contain "passed: true"
        text = f"some preamble {_fenced(_fail_json())} {{\"passed\": true}}"
        result = parse_fn(text)
        assert result.passed is False


# ── GeminiProvider ────────────────────────────────────────────────────────────

class TestGeminiProvider:
    def test_is_available_false_without_key(self, monkeypatch):
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        assert GeminiProvider().is_available() is False

    def test_is_available_true_with_google_key(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        assert GeminiProvider().is_available() is True

    def test_is_available_true_with_gemini_key(self, monkeypatch):
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        assert GeminiProvider().is_available() is True

    def test_analyze_calls_sdk_and_parses(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
        provider = GeminiProvider()

        mock_response = MagicMock()
        mock_response.text = _ok_json()
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        provider._client = mock_client

        result = provider.analyze("test prompt")
        assert result.passed is True
        mock_client.models.generate_content.assert_called_once()

    def test_get_client_raises_on_missing_sdk(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
        provider = GeminiProvider()
        with patch.dict("sys.modules", {"google.genai": None}):
            with pytest.raises(RuntimeError, match="google-genai"):
                provider._get_client()

    def test_default_model(self):
        assert "gemini" in GeminiProvider().model.lower()


# ── OpenAIProvider ────────────────────────────────────────────────────────────

class TestOpenAIProvider:
    def test_is_available_false_without_key(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        assert OpenAIProvider().is_available() is False

    def test_is_available_true_with_key(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        assert OpenAIProvider().is_available() is True

    def test_analyze_calls_sdk_and_parses(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        provider = OpenAIProvider()

        mock_msg = MagicMock()
        mock_msg.content = _ok_json()
        mock_choice = MagicMock()
        mock_choice.message = mock_msg
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        provider._client = mock_client

        result = provider.analyze("test prompt")
        assert result.passed is True

    def test_default_model(self):
        assert OpenAIProvider().model == "gpt-4o-mini"


# ── AnthropicProvider ─────────────────────────────────────────────────────────

class TestAnthropicProvider:
    def test_is_available_false_without_key(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        assert AnthropicProvider().is_available() is False

    def test_is_available_true_with_key(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "ant-test")
        assert AnthropicProvider().is_available() is True

    def test_analyze_calls_sdk_and_parses(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "ant-test")
        provider = AnthropicProvider()

        mock_content_block = MagicMock()
        mock_content_block.text = _ok_json()
        mock_message = MagicMock()
        mock_message.content = [mock_content_block]
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_message
        provider._client = mock_client

        result = provider.analyze("test prompt")
        assert result.passed is True

    def test_default_model(self):
        assert "claude" in AnthropicProvider().model.lower()


# ── OllamaProvider ────────────────────────────────────────────────────────────

class TestOllamaProvider:
    def test_is_available_true_when_server_reachable(self):
        provider = OllamaProvider()
        with patch("urllib.request.urlopen") as mock_open:
            mock_open.return_value.__enter__ = lambda s: s
            mock_open.return_value.__exit__ = MagicMock(return_value=False)
            assert provider.is_available() is True

    def test_is_available_false_when_server_unreachable(self):
        import urllib.error

        provider = OllamaProvider()
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("refused")):
            assert provider.is_available() is False

    def test_analyze_calls_api_and_parses(self):
        provider = OllamaProvider()
        response_data = json.dumps({"response": _ok_json()}).encode()

        mock_resp = MagicMock()
        mock_resp.read.return_value = response_data
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = provider.analyze("test prompt")

        assert result.passed is True

    def test_default_model(self):
        assert OllamaProvider().model == "llama3.2"

    def test_endpoint_trailing_slash_stripped(self):
        p = OllamaProvider(endpoint="http://localhost:11434/")
        assert not p.endpoint.endswith("/")


# ── get_provider factory ──────────────────────────────────────────────────────

class TestGetProvider:
    def test_returns_none_when_no_provider_available(self, monkeypatch):
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with patch("urllib.request.urlopen", side_effect=Exception("no ollama")):
            result = get_provider()
        assert result is None

    def test_returns_gemini_when_key_set(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        provider = get_provider()
        assert isinstance(provider, GeminiProvider)

    def test_explicit_name_overrides_autodetect(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        provider = get_provider(provider_name="openai")
        assert isinstance(provider, OpenAIProvider)

    def test_unknown_provider_name_returns_none(self):
        result = get_provider(provider_name="nonexistent_provider")
        assert result is None
