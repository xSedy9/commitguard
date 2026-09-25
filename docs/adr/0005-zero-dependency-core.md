# ADR-0005: Zero-Dependency Core with Optional Provider SDKs

## Status
Accepted

## Date
2026-09-25

## Context
Requiring users to install multiple heavy vendor SDKs (`google-genai`, `openai`, `anthropic`, `pyyaml`) to run a local git interceptor creates high friction and dependency conflicts in existing development environments.

## Decision
The core engine (`git_guard.py`, `src/config.py`, `src/layer1/`, `src/output.py`) relies exclusively on the Python standard library. External SDKs are treated as optional dependencies and imported lazily only when their respective provider or YAML parsing is actively triggered.

## Consequences

### Positive
- Zero initial external dependency requirements: Layer 1 validation works out of the box with standard Python 3.11+.
- Local Ollama provider requires no external dependencies (uses standard library `urllib.request`).
- Fast cold startup time.

### Negative
- Lazy import blocks must catch `ImportError` and provide actionable pip installation instructions.
