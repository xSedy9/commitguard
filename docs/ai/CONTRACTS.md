# AI Validation Contracts

## 1. Overview

This document specifies the semantic contracts enforced by Layer 2 AI providers. All providers conforming to the `AIProvider` interface must adhere to these five rules.

---

## 2. Rule Specifications

### 2.1 Rule 1: `documentation_language`
- **Scope**: Staged human-readable documentation prose (`.md`, `.rst`, `.txt`).
- **Exemptions**: Inline code, fenced code blocks, URLs, file paths, variable names, proper nouns.
- **Pass Threshold**: >= 90% English prose.
- **Fail Condition**: More than 10% non-English sentences in prose content.

### 2.2 Rule 2: `documentation_emoji`
- **Scope**: Staged documentation prose (`.md`, `.rst`, `.txt`).
- **Exemptions**: Characters enclosed in fenced code blocks.
- **Pass Threshold**: 0 emoji characters in headings, paragraphs, lists, and tables.
- **Fail Condition**: Any emoji detected in documentation prose outside code blocks.

### 2.3 Rule 3: `debug_and_garbage_code`
- **Scope**: Added lines (`+`) in the unified diff across all files.
- **Fail Conditions**:
  1. Diagnostic output statements (`print("DEBUG...")`, `console.log(...)`, `fmt.Println(...)`).
  2. Hardcoded local or sensitive values (`http://localhost:3000`, `TOKEN = "..."`).
  3. 3 or more consecutive lines of commented-out executable code.
  4. Temporary annotations (`# TODO: remove`, `# FIXME: hack`, `// TEMP:`).
  5. Diagnostic conditionals without production alternatives (`if DEBUG:` without else).

### 2.4 Rule 4: `commit_atomicity`
- **Scope**: Unified diff.
- **Fail Condition**: The diff mixes two or more unrelated domains or concerns (e.g. business logic + dependency upgrade, UI overhaul + database schema change).
- **Pass Condition**: Changes that logically belong together in a single unit of work (e.g. function + unit test + documentation).

### 2.5 Rule 5: `message_diff_match`
- **Scope**: Commit message subject line in relation to the diff.
- **Fail Conditions**:
  1. Subject references agent task/ticket numbers (e.g. `do task 11`, `task 3`, `step 2`).
  2. Commit type does not match diff (e.g. `feat` when only refactoring existing logic).
  3. Scope does not match files changed.
  4. Generic or vague subject (`wip`, `updates`, `fixes`).
  5. Subject claims one change but diff executes another.

---

## 3. Provider Implementations
Detailed integration contracts for specific providers:
- [Google Gemini Provider](GEMINI_PROVIDER.md)
- [OpenAI Provider](OPENAI_PROVIDER.md)
- [Anthropic Claude Provider](ANTHROPIC_PROVIDER.md)
- [Local Ollama Provider](OLLAMA_PROVIDER.md)
