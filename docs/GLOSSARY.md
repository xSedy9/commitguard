# Glossary of Terms

## Core Concepts

### PATH Shim
A lightweight executable or script (`git.cmd` on Windows, `git` shell script on Unix) placed in a directory prepended to the system `PATH`. When an agent or user invokes `git`, the operating system resolves the shim rather than the native git executable.

### Layer 1 (Heuristics)
The zero-network, sub-15ms validation stage executed directly by Python. Inspects staged file names, paths, regex patterns, and commit message formatting before any remote or AI calls are initiated.

### Layer 2 (Semantic AI)
The second validation stage powered by large language models (LLMs). Audits unified diffs and documentation prose for language quality, debug code leakage, commit atomicity, and message-diff synchronization.

### Fast-Path
A performance optimization in Layer 2. If staged files contain no documentation extensions (`.md`, `.rst`, `.txt`) and the unified diff is under 50 lines, Layer 2 evaluation is automatically skipped.

### Fail-Open
A design principle ensuring commitguard never permanently blocks developer workflow due to external API outages, rate limits, network timeouts, or unparseable LLM output. If an AI provider error occurs, commitguard emits a warning and allows the commit to proceed.

### Conventional Commits
A standardized commit message specification adopting the format `<type>(<scope>): <subject>`. Enables automated changelog generation and maintains a structured git history.

### ACMR Filter
Git diff argument (`--diff-filter=ACMR`) used by commitguard to query Added, Copied, Modified, or Renamed files while explicitly excluding Deleted (`D`) files. This ensures users can always commit deletions of previously committed forbidden files.

### Agent File
Instruction or coordination files utilized by autonomous coding assistants (such as `AGENTS.md`, `GEMINI.md`, `CLAUDE.md`, `CURSOR.md`, `TASKS.md`). commitguard permanently blocks these files from entering public repository history.

### Token Budgeting
The process of approximating LLM token usage (4 characters per token) and truncating large diffs at a configurable threshold (default: 8,000 tokens) to prevent exceeding provider context limits.

### Passthrough
The transparent execution of non-commit git commands (`git status`, `git push`, `git log`, etc.) directly via the real git binary with zero overhead and unmodified standard streams.
