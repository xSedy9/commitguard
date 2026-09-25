# AI Contracts and Prompt Specification

## 1. Overview

commitguard Layer 2 delegates semantic code and documentation validation to an LLM provider. This document defines the formal contract, prompt structure, evaluation criteria, and output schema expected from any compliant AI provider.

---

## 2. Evaluation Rules Specification

The AI provider evaluates the commit against five mutually distinct categories:

### Rule 1: `documentation_language`
- **Scope**: Human-readable prose inside staged `.md`, `.rst`, and `.txt` files.
- **Exclusions**: Code blocks (fenced and inline), URLs, file paths, variable names, functions, technical identifiers, proper nouns.
- **Condition for Rejection**: More than 10% of prose sentences are written in a non-English language.
- **Category ID**: `documentation_language`

### Rule 2: `documentation_emoji`
- **Scope**: Documentation files (`.md`, `.rst`, `.txt`).
- **Exclusions**: Characters inside fenced code blocks or backtick literals.
- **Condition for Rejection**: Any emoji character appears in document headers, body paragraphs, bullet lists, or tables.
- **Category ID**: `documentation_emoji`

### Rule 3: `debug_and_garbage_code`
- **Scope**: Added lines (`+`) in the unified diff across all staged files.
- **Conditions for Rejection**:
  1. Diagnostic output statements (`print("DEBUG:...")`, `console.log("here")`, `fmt.Println("test")`).
  2. Hardcoded local or sensitive values (`url = "http://localhost:3000"`, `TOKEN = "secret123"`).
  3. Commented-out code blocks consisting of 3 or more consecutive lines of executable syntax.
  4. Explicit temporary developer markers (`# TODO: remove`, `# FIXME: hack`, `// TEMP:`).
  5. Diagnostic conditionals without production execution paths (`if DEBUG:` with no fallback).
- **Category ID**: `debug_and_garbage_code`

### Rule 4: `commit_atomicity`
- **Scope**: Unified diff across all staged files.
- **Condition for Rejection**: The diff mixes two or more unrelated architectural or functional concerns (e.g. backend business logic + UI overhaul, new feature code + unrelated bug fix in another module, database schema + dependency upgrade).
- **Condition for Acceptance**: Logically cohesive changes that belong to the same unit of work (e.g. new function + unit test + docs update).
- **Category ID**: `commit_atomicity`

### Rule 5: `message_diff_match`
- **Scope**: Relation between the commit message subject line and the staged diff.
- **Conditions for Rejection**:
  1. The message references task numbers, ticket identifiers, or workflow steps (e.g. `do task 11`, `task 3 completed`, `implement step 2`) instead of describing the concrete code change.
  2. Commit type mismatch (e.g. `feat` when only refactoring existing code).
  3. Scope mismatch (e.g. `ui` when only altering database models).
  4. Vague or generic descriptions (`updates`, `fixes`, `changes`).
  5. Discrepancy between stated intent and actual modifications.
- **Category ID**: `message_diff_match`

---

## 3. Prompt Template

The prompt is delivered to the LLM as a single system instruction containing the commit metadata:

```
You are a strict automated gate that validates git commits before they enter history.
Your job is to enforce the project rules exactly as written below.
Return ONLY a JSON object - no prose, no markdown, no explanation outside the JSON.

=======================================================
COMMIT UNDER REVIEW
=======================================================

Commit message:
{commit_message}

Staged files:
{staged_files}

Diff (may be clipped at token limit):
```
{diff}
```

=======================================================
RULES - check every one, reject on ANY violation
=======================================================
[Rules 1 through 5 specifications]

=======================================================
OUTPUT FORMAT
=======================================================
```

---

## 4. Response JSON Schema

### 4.1 Success Response
When all five rules pass without violation:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "passed": { "type": "boolean", "const": true },
    "issues": { "type": "array", "maxItems": 0 }
  },
  "required": ["passed", "issues"]
}
```

Example payload:
```json
{
  "passed": true,
  "issues": []
}
```

### 4.2 Failure Response
When one or more rules are violated:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "passed": { "type": "boolean", "const": false },
    "issues": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "properties": {
          "category": {
            "type": "string",
            "enum": [
              "documentation_language",
              "documentation_emoji",
              "debug_and_garbage_code",
              "commit_atomicity",
              "message_diff_match"
            ]
          },
          "message": { "type": "string" },
          "detail": { "type": "string" }
        },
        "required": ["category", "message", "detail"]
      }
    }
  },
  "required": ["passed", "issues"]
}
```

Example payload:
```json
{
  "passed": false,
  "issues": [
    {
      "category": "debug_and_garbage_code",
      "message": "Debug print statement detected",
      "detail": "auth.py line 47 added print('DEBUG: token', token). Remove or replace with logger."
    },
    {
      "category": "message_diff_match",
      "message": "Task reference in commit subject",
      "detail": "Subject 'feat(core): do task 11' refers to task number instead of describing functionality."
    }
  ]
}
```

---

## 5. Parser Resilience

Provider response parsers must tolerate common LLM formatting variations:
1. **Fenced Code Blocks**: Responses enclosed in ` ```json ... ``` ` or ` ``` ... ``` ` are parsed first.
2. **Bare JSON**: If no code fence is present, the parser extracts the outermost curly brace pair `{ ... }`.
3. **Fail-Open on Parse Error**: If the response is unparseable or malformed, the parser returns `AIResult(passed=True)` and logs a warning to ensure development is not blocked by intermittent LLM formatting glitches.
