# ADR-0002: Pluggable AIProvider Interface Over Single-Vendor SDK

## Status
Accepted

## Date
2026-09-25

## Context
Initial specifications coupled validation logic directly to the Google Gemini SDK. However, enterprise and developer environments often require private, on-premise, or alternative hosted LLMs (such as OpenAI, Anthropic Claude, or local Ollama instances) due to compliance policies, API cost management, or offline connectivity constraints.

Directly importing a single vendor SDK into the validation engine would lock the architecture into a single provider and force every user to install unused third-party dependencies.

## Decision
Introduce an abstract base class `AIProvider` in `src/providers/base.py` with concrete implementations in `src/providers/` and an autodetecting factory in `src/providers/__init__.py`.

The core validation engine (`src/layer2/analyzer.py`) interacts exclusively with the `AIProvider` interface and has zero knowledge of vendor-specific SDKs.

## Consequences

### Positive
- Loose coupling: Adding a new model or provider requires implementing only two methods: `analyze()` and `is_available()`.
- Zero-config runtime autodetection: Automatically selects the first available provider based on environment variables (`GOOGLE_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, or local Ollama ping).
- Optional dependencies: Users only install the SDK for the provider they actually intend to use.

### Negative
- Requires maintaining prompt specifications and JSON parsing across different LLM instruction-following capabilities.
