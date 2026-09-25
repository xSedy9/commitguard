# Google Gemini Provider Specification

## 1. Overview
- **Class**: `GeminiProvider` (`src/providers/gemini.py`)
- **Default Model**: `gemini-3.5-flash-lite`
- **SDK**: `google-genai` (PyPI)
- **Credential Variables**: `GOOGLE_API_KEY` or `GEMINI_API_KEY`

---

## 2. API Integration
The provider initializes the client lazily on first analysis:
```python
from google import genai
client = genai.Client(api_key=api_key)
```

### 2.1 Warning Suppression
The `google-genai` SDK emits advisory notices regarding Automatic Function Calling (AFC) when calling `generate_content` directly. The provider catches and suppresses these warnings to ensure `stderr` remains clean.

### 2.2 Response Parsing
1. Extracts text from `response.text`.
2. Inspects for fenced markdown block: ````json ... ````.
3. Fallback extracts outermost `{ ... }` curly braces.
4. On JSON syntax error, fails open by returning `AIResult(passed=True)` and logging a non-blocking warning.
