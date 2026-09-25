# Data Formats and Configuration Schemas

## 1. `config.yaml` Schema

commitguard supports an optional configuration file placed at the root of the repository or specified via `COMMITGUARD_CONFIG`. All fields are optional and merge cleanly with built-in defaults.

### 1.1 Complete YAML Specification

```yaml
ai:
  enabled: true                      # boolean: enable/disable Layer 2 AI evaluation
  provider: gemini                   # string: "gemini" | "openai" | "anthropic" | "ollama" | omit for autodetect
  model: gemini-3.5-flash-lite       # string: model override (omit to use provider default)
  timeout_seconds: 10                # integer: seconds before fail-open timeout
  max_diff_tokens: 8000              # integer: approximate token ceiling for diffs

rules:
  blocked_filenames:                 # list of strings: case-insensitive exact file names
    - "CUSTOM_AGENT_RULES.md"
  blocked_path_prefixes:             # list of strings: folder prefixes to block
    - "internal_agent/"
  allowed_path_prefixes:             # list of strings: folder prefixes that bypass all block rules
    - "docs/public_spec/"

commit_message:
  max_subject_length: 100            # integer: maximum character count for subject line
  require_scope: true                # boolean: whether (<scope>) is mandatory
  allowed_types:                     # list of strings: accepted conventional commit types
    - feat
    - fix
    - docs
    - style
    - refactor
    - perf
    - test
    - chore
```

---

## 2. Issue Data Structure

Within the validation pipeline, detected infractions are represented as standardized dictionaries before being formatted for output:

### 2.1 Schema Definition

| Key | Type | Description | Allowed Values |
|---|---|---|---|
| `kind` | `str` | High-level classification of the issue for output grouping | `"blocked_file"`, `"message_format"`, `"ai"` |
| `title` | `str` | Short single-line summary of the violation displayed after the rejection indicator | Any string |
| `detail` | `str` | Multiline explanatory guidance or code snippet showing how to resolve the issue | Any string |

### 2.2 Examples

#### Layer 1 Blocked File Issue
```python
{
    "kind": "blocked_file",
    "title": "AGENTS.md",
    "detail": "AI agent instruction file must not be committed"
}
```

#### Layer 1 Commit Message Format Issue
```python
{
    "kind": "message_format",
    "title": "Task reference in subject: 'do task 11'",
    "detail": (
        "Commit message must describe the concrete code change, not agent tasks or ticket numbers.\n"
        "    Forbidden: 'do task 11', 'task 3', 'step 2'\n"
        "    Allowed example: feat(core): implement payment webhook signature verification"
    )
}
```

#### Layer 2 AI Issue
```python
{
    "kind": "ai",
    "title": "Debug code detected  (category: debug_and_garbage_code)",
    "detail": "auth.py line 47: print('DEBUG token:', token) - remove or replace with proper logging."
}
```

---

## 3. Diff Token Budget and Clipping

To prevent exceeding LLM context windows or incurring excessive latency on massive commits, the unified diff undergoes token budgeting:

- **Approximation Ratio**: 1 token is approximated as 4 characters of diff text.
- **Budget Calculation**: `max_chars = max_diff_tokens * 4` (default: 32,000 characters).
- **Clipping Mechanism**: If `len(diff) > max_chars`, the diff is truncated at `max_chars` and appended with:
  ```
  \n\n[DIFF CLIPPED - token limit reached]\n
  ```
- The prompt explicitly instructs the LLM that diff clipping occurred, allowing it to validate the available portion without error.
