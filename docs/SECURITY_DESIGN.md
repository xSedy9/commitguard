# Security Design and Threat Model

## 1. Threat Landscape

In automated and semi-automated coding environments, AI agents frequently invoke git commands directly. Common agent failure modes include:
1. Adding `--no-verify` or `-n` flags to `git commit` to bypass pre-commit hook failures and suppress linter or type-check rejections.
2. Committing temporary context files, agent scratchpads, prompt rules (`AGENTS.md`, `GEMINI.md`, `CLAUDE.md`, `TASKS.md`), or diagnostic test scripts into long-term version history.
3. Committing non-English documentation or emoji in commit headers contrary to organizational policies.

Standard git hooks (`.git/hooks/pre-commit`, `.husky`, etc.) fail in these scenarios because `git commit --no-verify` explicitly disables hook execution by design.

---

## 2. Threat Matrix and Mitigations

| Threat ID | Attack / Failure Vector | Impact | commitguard Mitigation |
|---|---|---|---|
| **T-01** | Agent executes `git commit --no-verify` | Bypasses local quality gates | Pre-flight parser strips `--no-verify` and `-n` before git receives arguments. |
| **T-02** | Agent attempts to commit agent rule files | Pollutes history with private instructions | Layer 1 exact filename blocklist rejects commit immediately (~0ms). |
| **T-03** | Agent leaves debug print or localhost URL | Leaks diagnostic code to production | Layer 2 AI audit analyzes diff lines and rejects non-production patterns. |
| **T-04** | Agent uses task ticket instead of message | Degrades git history readability | Layer 1 regex filter rejects task number references (`do task 11`, `task 3`). |
| **T-05** | API key leak via committed `.env` | Credential compromise | Built-in `.gitignore` rules prevent staging `.env` or `*.env` files. |
| **T-06** | PATH shadow bypass on Windows | Native `git.exe` executed directly | Installer detects Machine-scoped git and elevates to place shim in System PATH. |

---

## 3. Path Precedence and Interception Architecture

### 3.1 Windows PATH Precedence Vulnerability
On Windows systems, environment variable expansion processes `Machine PATH` (system-wide) before `User PATH`:
```
Effective PATH = [Machine PATH entries] + ";" + [User PATH entries]
```
If Git for Windows was installed with system privileges (e.g. into `C:\Program Files\Git\cmd`), any shim added only to `User PATH` will be shadowed by `C:\Program Files\Git\cmd\git.exe`.

**Mitigation**:
`install.ps1` explicitly checks if `git.exe` exists in `Machine PATH`. If present, it requests User Account Control (UAC) elevation via:
```powershell
Start-Process powershell -Verb RunAs -ArgumentList "-ExecutionPolicy Bypass -File `"$PSCommandPath`""
```
When elevated, the commitguard directory is prepended to `Machine PATH`, ensuring `git.cmd` is evaluated prior to any other git installation system-wide.

### 3.2 Dynamic Real Git Resolution
To prevent infinite recursion, `git_guard.py` resolves the true git binary dynamically:
1. It iterates through all directories in `PATH`.
2. It excludes its own directory to prevent calling `git.cmd` recursively.
3. It selects the first matching executable (`git.exe` / `git`) found in subsequent PATH directories.

---

## 4. Credential Management

AI provider API keys (`GOOGLE_API_KEY`, `GEMINI_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`) are handled with the following security boundaries:
1. **Never Staged or Committed**: Credentials must reside in environment variables or an uncommitted `.env` file ignored by `.gitignore`.
2. **Read-Only In-Memory**: Keys are read dynamically at request time and are never written to disk or included in log outputs.
3. **Registry Fallback on Windows**: When running in unrefreshed processes, `load_config` inspects `HKCU\Environment` in memory without modifying persistent storage.
