"""
Provider registry and autodetect factory for commitguard AI layer.

Autodetects an available provider when none is explicitly configured,
following the priority order:
  1. Google Gemini  (configured in ~/.commitguard/credentials)
  2. OpenAI         (configured in ~/.commitguard/credentials)
  3. Anthropic      (configured in ~/.commitguard/credentials)
  4. Ollama         (always available if running locally)
"""
from __future__ import annotations

from typing import Optional

from src.providers.base import AIProvider

_PROVIDER_ORDER = ("gemini", "openai", "anthropic", "ollama")


def _load_provider_class(name: str) -> type[AIProvider]:
    """
    Lazily import and return the concrete provider class for *name*.

    Args:
        name: Provider identifier string.

    Returns:
        Subclass of AIProvider.

    Raises:
        ValueError: If the provider name is unknown.
        ImportError: If the provider's SDK is not installed.
    """
    if name == "gemini":
        from src.providers.gemini import GeminiProvider

        return GeminiProvider
    if name == "openai":
        from src.providers.openai import OpenAIProvider

        return OpenAIProvider
    if name == "anthropic":
        from src.providers.anthropic import AnthropicProvider

        return AnthropicProvider
    if name == "ollama":
        from src.providers.ollama import OllamaProvider

        return OllamaProvider
    raise ValueError(f"Unknown AI provider: '{name}'")


def get_provider(
    provider_name: Optional[str] = None,
    model: Optional[str] = None,
    timeout: int = 10,
) -> Optional[AIProvider]:
    """
    Return an instantiated, available AIProvider.

    Iterates over candidates in priority order and returns the first one
    whose is_available() returns True. Returns None if none are available.

    Args:
        provider_name: Explicit provider name. If None, autodetect.
        model: Override the provider's default model name.
        timeout: Request timeout in seconds passed to the provider.

    Returns:
        A ready-to-use AIProvider instance, or None.
    """
    candidates = [provider_name] if provider_name else list(_PROVIDER_ORDER)

    for name in candidates:
        try:
            cls = _load_provider_class(name)
        except (ImportError, ValueError):
            continue

        kwargs: dict = {"timeout": timeout}
        if model:
            kwargs["model"] = model

        try:
            instance = cls(**kwargs)
        except TypeError:
            instance = cls()

        if instance.is_available():
            return instance

    return None
