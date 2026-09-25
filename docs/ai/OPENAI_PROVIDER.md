# OpenAI Provider Specification

## 1. Overview
- **Class**: `OpenAIProvider` (`src/providers/openai.py`)
- **Default Model**: `gpt-4o-mini`
- **SDK**: `openai` (PyPI)
- **Credential Variable**: `OPENAI_API_KEY`

---

## 2. API Integration
The client is initialized lazily using the `openai` SDK:
```python
import openai
client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"], timeout=self.timeout)
```

The call enforces structured JSON responses via `response_format={"type": "json_object"}` where supported, and falls back to regex-based JSON extraction.
