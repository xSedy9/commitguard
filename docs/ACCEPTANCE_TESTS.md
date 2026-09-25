# Acceptance Test Criteria and Verification Scenarios

## 1. Overview

Acceptance tests define the expected system behavior from an end-user or agent perspective across both happy and adverse operational paths.

---

## 2. Verification Scenarios

### Scenario 1: Staged Agent Instruction File
- **Given**: A repository with `AGENTS.md` staged for commit.
- **When**: The user runs `git commit -m "feat(core): add rules"`.
- **Then**:
  - The command fails immediately with exit code 1.
  - Stderr contains `[BLOCKED FILES]` and identifies `AGENTS.md`.
  - The real git commit command is never invoked.

### Scenario 2: Staged Temporary or Debug File
- **Given**: A repository with `app.debug.log` or `config.bak` staged.
- **When**: The user runs `git commit -m "fix(core): update config"`.
- **Then**:
  - The command fails with exit code 1.
  - Stderr identifies the file pattern violation.

### Scenario 3: Bypass Attempt via `--no-verify` or `-n`
- **Given**: A repository with invalid files or messages.
- **When**: The user runs `git commit --no-verify -m "fix(core): bypass check"`.
- **Then**:
  - commitguard strips the `--no-verify` flag.
  - Stderr prints `[commitguard] [!] --no-verify was stripped. Bypass is not permitted.`
  - Validation proceeds and rejects the commit if issues are present.

### Scenario 4: Non-Compliant Commit Message Format
- **Given**: Clean files staged.
- **When**: The user runs `git commit -m "fixed the login issue"`.
- **Then**:
  - The command fails with exit code 1.
  - Stderr indicates `Invalid commit message format` and provides the required syntax `<type>(<scope>): <subject>`.

### Scenario 5: Task Reference or Vague Subject
- **Given**: Clean files staged.
- **When**: The user runs `git commit -m "feat(core): do task 11"`.
- **Then**:
  - The command fails with exit code 1.
  - Stderr identifies `Task reference in subject: 'do task 11'` and cites forbidden patterns.
- **When**: The user runs `git commit -m "chore(core): wip"`.
- **Then**:
  - The command fails with exit code 1.
  - Stderr identifies `Vague commit subject: 'wip'`.

### Scenario 6: Non-English Documentation Content
- **Given**: Staged `.md` file containing Russian or other non-English prose paragraphs (>10%).
- **When**: The user runs `git commit -m "docs(api): update user guide"`.
- **Then**:
  - Layer 1 passes.
  - Layer 2 AI analysis flags `documentation_language`.
  - The commit is rejected with exit code 1.

### Scenario 7: Emoji in Documentation Content
- **Given**: Staged `README.md` containing `## Features` with emoji bullet points.
- **When**: The user runs `git commit -m "docs(readme): add feature section"`.
- **Then**:
  - Layer 2 AI flags `documentation_emoji`.
  - The commit is rejected with exit code 1.

### Scenario 8: Diagnostic or Debug Statements in Diff
- **Given**: Staged code introducing `print("DEBUG: token is", token)` or `url = "http://localhost:3000"`.
- **When**: The user runs `git commit -m "feat(auth): add login check"`.
- **Then**:
  - Layer 2 AI flags `debug_and_garbage_code`.
  - The commit is rejected with exit code 1.

### Scenario 9: Fully Compliant Commit
- **Given**: Clean code, English documentation, and a message conforming to `feat(core): implement token validation`.
- **When**: The user runs `git commit -m "feat(core): implement token validation"`.
- **Then**:
  - Stderr prints `[commitguard] [OK] All checks passed (heuristics + AI)`.
  - Real git executes and records the commit.
  - The command exits with code 0.

### Scenario 10: AI Provider Outage (Fail-Open Verification)
- **Given**: Staged changes exceeding 50 lines, but the AI API times out or is unreachable.
- **When**: The user runs a valid commit.
- **Then**:
  - A warning is emitted to stderr indicating AI checks were skipped.
  - The commit succeeds and real git records the change (fail-open).
