# ADR-0006: File-Based Credential Storage Over Environment Variables

## Status
Accepted

## Date
2026-09-26

## Context
Relying on ambient environment variables (`GOOGLE_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`) introduces credential leakage risks in agentic software development environments:
1. Child processes (e.g. `npm postinstall`, build scripts, test suites, third-party CLI tools) inherit the full parent environment and can exfiltrate API keys.
2. Process inspection tools (`/proc/$PID/environ` on Linux, WMI or Task Manager on Windows) expose environment strings.
3. Diagnostic crash dumps, CI logs, or agent terminal transcript logs can inadvertently capture environment variable dumps.

Platform-specific credential managers (such as Windows Credential Manager or macOS Keychain) introduce heavy native dependencies, external C-bindings, or interactive desktop prompts that fail in headless environments, SSH sessions, or lightweight Linux setups.

## Decision
Store provider API keys in a dedicated user-level credentials file at `~/.commitguard/credentials` with restricted file permissions (POSIX `0600` for owner-only read/write and Windows user ACL).

Eliminate loading provider API keys from ambient environment variables.

Provide built-in CLI management subcommands intercepted directly by the shim:
- `git auth set <provider> <key>`
- `git auth get <provider>`
- `git auth remove <provider>`
- `git auth list`
- `git auth path`

## Consequences

### Positive
- API keys are isolated from child processes, package install scripts, and process listings.
- Fully cross-platform across Windows, Linux, and macOS using only Python standard library.
- Zero external dependencies introduced into the core engine.
- Headless and container compatible.

### Negative
- Users must configure their credentials once via `git auth set <provider> <key>` or by editing `~/.commitguard/credentials`.
