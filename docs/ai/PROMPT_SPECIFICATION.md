# AI Prompt Template and Context Specification

## 1. System Prompt Architecture

The prompt delivered to the LLM orchestrator is constructed dynamically from repository configuration (`config.yaml`). It combines a system instruction defining the gatekeeper role, commit context, dynamic rules compilation, and a strict JSON output schema:

```
You are a strict automated gate that validates git commits before they enter history.
Your job is to enforce the project rules exactly as written below.
Return ONLY a JSON object — no prose, no markdown, no explanation outside the JSON.

═══════════════════════════════════════════════════════
COMMIT UNDER REVIEW
═══════════════════════════════════════════════════════

Commit message:
{commit_message}

Staged files:
{staged_files}

Diff (may be clipped at token limit):
```
{diff}
```

═══════════════════════════════════════════════════════
RULES — check every one, reject on ANY violation
═══════════════════════════════════════════════════════

{rules}

═══════════════════════════════════════════════════════
OUTPUT FORMAT (EXAMPLES)
═══════════════════════════════════════════════════════

Example if ALL rules pass:
{
  "passed": true,
  "issues": []
}

Example if ANY rule fails (include one entry per violated rule):
{
  "passed": false,
  "issues": [
    {
      "category": "<one of valid categories>",
      "message": "<brief summary of violation>",
      "detail": "<specific file, line, or reason>"
    }
  ]
}

Valid category values: {valid_categories}
```

---

## 2. Dynamic Rules Compilation

Rules are parsed from `config.yaml` and compiled into the `{rules}` prompt section:

1. **File Placement & Restrictions (`file_restrictions`)**:
   - Compiles built-in blocked filenames (`AGENTS.md`, `GEMINI.md`, etc.), blocked prefixes (`.gemini/`), and any extra rules from `rules.blocked_filenames`, `rules.blocked_path_prefixes`, and `rules.allowed_path_prefixes`.
2. **Standard Semantic Checks (`ai.checks`)**:
   - `documentation_language`: English-only prose in documentation (`.md`, `.rst`, `.txt`).
   - `documentation_emoji`: Prohibits emoji in documentation prose.
   - `debug_and_garbage_code`: Detects debug prints, hardcoded secrets/localhost, commented-out code, and temporary markers.
   - `commit_atomicity`: Enforces single-responsibility commits.
   - `message_diff_match`: Enforces Conventional Commit types (`commit_message.allowed_types`), scope requirements (`commit_message.require_scope`), subject length, and accuracy against the staged diff.
3. **Custom Project Rules (`custom_rule`)**:
   - Repository-specific rules specified in natural language under `ai.custom_rules` (or `rules.custom_rules`).
   - AI evaluates each natural language constraint and reports violations under category `"custom_rule"`.

---

## 3. Token Budgeting Strategy
- **Budget**: Configured via `ai.max_diff_tokens` (default 8,000 tokens / ~32,000 characters).
- **Clipping**: When diff exceeds the character limit, the diff is sliced and appended with `[DIFF CLIPPED — token limit reached]`.
- **Parsing**: Responses are parsed using fenced JSON regex first, falling back to bare JSON extraction.

