# Anthropic Claude Provider Specification

## 1. Overview
- **Class**: `AnthropicProvider` (`src/providers/anthropic.py`)
- **Default Model**: `claude-haiku-4-5`
- **SDK**: `anthropic` (PyPI)
- **Credential Variable**: `ANTHROPIC_API_KEY`

---

## 2. API Integration
The client is initialized lazily using the `anthropic` SDK:
```python
import anthropic
client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"], timeout=self.timeout)
```

Extracts content from `response.content[0].text` and applies fenced or bare JSON parsing with fail-open fallback.
