# ADR-0001: Selection of PATH Shim Over Standard Git Hooks

## Status
Accepted

## Date
2026-09-25

## Context
Standard git hooks (such as `.git/hooks/pre-commit`, Husky, or the pre-commit framework) are the traditional mechanism for intercepting commits. However, modern autonomous AI agents frequently invoke `git commit --no-verify` or `-n` when executing repetitive tasks or attempting to bypass linter failures. When `--no-verify` is passed, Git deliberately bypasses all pre-commit hooks, rendering them completely ineffective in agentic development environments.

Furthermore, git hooks must be initialized individually inside every repository clone, which is prone to omission and does not provide system-wide protection across arbitrary repositories.

## Decision
Implement commitguard as a PATH shim (`git.cmd` on Windows, `git` POSIX shell script on Unix) that shadows the native git executable.

The shim intercepts all `git` invocations, inspects the subcommand, and if the command is `commit`, strips any `--no-verify` or `-n` flags before delegating validation to `git_guard.py`.

## Consequences

### Positive
- Bypasses via `--no-verify` or `-n` are stripped before git ever executes.
- Operates globally across all repositories on the machine with zero per-repo setup.
- Non-commit commands (`push`, `log`, `status`, etc.) pass through with sub-5ms overhead.

### Negative
- Requires modifying the system `PATH` environment variable during installation.
- On Windows, requires Administrator elevation if the native Git installation is located in the machine-scoped PATH (`C:\Program Files\Git\cmd`).
