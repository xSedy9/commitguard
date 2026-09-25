# Requirements Specification

## 1. Functional Requirements

### 1.1 Command Interception
- **FR-01 (Transparent Passthrough)**: Any git command other than `commit` (`status`, `push`, `pull`, `log`, `diff`, `checkout`, `branch`, etc.) must pass directly to the real git binary without overhead or modification.
- **FR-02 (Flag Stripping)**: When `commit` is invoked, the validator must strip bypass flags (`--no-verify`, `-n`) and the custom escape hatch (`--commitguard-no-ai`) before evaluation.
- **FR-03 (Bypass Notification)**: If `--no-verify` or `-n` is stripped, a warning message must be written to `stderr` indicating bypass attempts are prohibited.

### 1.2 Layer 1 Validation (Heuristics)
- **FR-04 (Forbidden File Blocking)**: The system must block staged files matching forbidden filenames (case-insensitive exact match: `AGENTS.md`, `GEMINI.md`, `CLAUDE.md`, `CURSOR.md`, `COPILOT.md`, `TASKS.md`, `TODO.md`, `.cursorrules`, `AIDER.md`, `CODEIUM.md`).
- **FR-05 (Pattern and Path Blocking)**: The system must block files matching temporary and debug patterns (e.g. `*.tmp`, `*.bak`, `debug_*`, `scratch_*`, `*~`) and path prefixes (e.g. `.gemini/`, `.aider/`, `scratch/`).
- **FR-06 (Allowlist Override)**: Paths matching configured `allowed_path_prefixes` must bypass all blocklist rules.
- **FR-07 (Deleted Files Exemption)**: Files marked as deleted (`--diff-filter=D`) must never trigger file blocklist rejections.
- **FR-08 (Conventional Commit Format)**: The first line of the commit message must conform to `<type>(<scope>): <subject>` where:
  - `type` belongs to allowed types (`feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`).
  - `scope` is mandatory and matches `^[a-z][a-z0-9._-]*$`.
  - `subject` length is between 3 and 100 characters.
  - No unicode emoji characters are present anywhere in the subject line.
- **FR-09 (Task Reference and Vague Subject Blocking)**: The validator must reject subjects containing agent task numbers (`do task 11`, `task 3`, `step 2`, `ticket #42`, `todo 5`) or generic phrases (`wip`, `temp`, `updates`, `fixes`, `cleanup`).

### 1.3 Layer 2 Validation (AI Semantic Review)
- **FR-10 (Documentation Quality Checks)**: Staged `.md`, `.rst`, and `.txt` files must have prose written in English (>90% threshold) and must not contain emoji characters outside code blocks.
- **FR-11 (Code Hygiene and Atomicity)**: The diff must not introduce temporary debug statements, hardcoded localhost URLs, or combine multiple unrelated logical changes.
- **FR-12 (Message-Diff Synchronization)**: The commit message type, scope, and subject must accurately reflect the staged diff.

---

## 2. Non-Functional Requirements

### 2.1 Performance and Latency Budgets
- **NFR-01 (Passthrough Overhead)**: For non-commit commands, the shim execution overhead must not exceed 10 milliseconds.
- **NFR-02 (Layer 1 Latency)**: Layer 1 validation must execute in under 15 milliseconds on a repository with up to 1,000 staged files.
- **NFR-03 (Layer 2 Timeout)**: AI provider analysis must complete within a configurable timeout (default: 10 seconds).
- **NFR-04 (Fast-Path Optimization)**: If staged changes contain no documentation files and the unified diff is under 50 lines, Layer 2 must be bypassed automatically.

### 2.2 Reliability and Availability
- **NFR-05 (Fail-Open Resilience)**: If the AI provider is unavailable, times out, or returns invalid JSON, the validator must issue a warning and allow the commit to proceed.
- **NFR-06 (Self-Healing Git Discovery)**: Real git must be discovered dynamically across all operating system paths without hardcoded binary paths.

### 2.3 Portability and Platform Support
- **NFR-07 (Operating System Compatibility)**: The system must operate identically on Windows 10/11, macOS (12+), and Linux (kernel 4.x+).
- **NFR-08 (Console Encoding Safety)**: Output formatting must automatically adapt to legacy or non-UTF-8 console code pages without raising unhandled encoding exceptions.
