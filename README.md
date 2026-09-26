# commitguard

> Git wrapper with two-layer commit validation for agentic development environments.

commitguard transparently intercepts every `git commit` call, enforces quality rules,
and prevents bypass — even when an AI agent passes `--no-verify`.

---

## How it works

```
agent: git commit --no-verify -m "wip"
              ↓
   git.cmd / git (PATH shim)
              ↓
   git_guard.py  ← validation engine
              ↓
   FAIL → stderr + exit 1
   PASS → real git.exe / git binary
```

### Layer 1 — Heuristics (~0 ms, no network)

- Blocks AI agent files (`AGENTS.md`, `GEMINI.md`, `CLAUDE.md`, …)
- Blocks temp/debug files (`.tmp`, `.bak`, `debug_*`, `scratch_*`, …)
- Blocks path prefixes (`.gemini/`, `.aider/`, `scratch/`, …)
- Enforces Conventional Commits format: `type(scope): subject`
- Strips `--no-verify` / `-n` silently (bypass is not permitted)

### Layer 2 — AI analysis (~1–3 s)

Powered by any supported LLM (pluggable provider interface):

| Check | What is flagged |
|---|---|
| **documentation_language** | Non-English prose in `.md`/`.rst`/`.txt` files (>10%) |
| **documentation_emoji** | Emoji in documentation headings, paragraphs, bullet points, tables |
| **debug_and_garbage_code** | Debug prints, hardcoded localhost/tokens, commented-out blocks, TODO/FIXME/TEMP |
| **commit_atomicity** | Diff mixes two+ unrelated domains/changes |
| **message_diff_match** | Commit message doesn't describe the diff or scope/type mismatch |

Layer 2 is skipped when no provider is configured, on timeout (fail-open),
or via `--commitguard-no-ai` (CI escape hatch).

---

## Installation

### Windows

Run from PowerShell (use `-ExecutionPolicy Bypass` if unsigned scripts are restricted on your system):

```powershell
cd path\to\commitguard
powershell -ExecutionPolicy Bypass -File .\install.ps1
# Restart your terminal
```

### macOS / Linux

```bash
cd path/to/commitguard
chmod +x install.sh git
./install.sh
source ~/.zshrc   # or ~/.bashrc
```

### Set your API key

API keys are stored securely in `~/.commitguard/credentials` with owner-only permissions, isolated from environment variables and child processes:

```bash
# Save an API key (cross-platform)
git auth set gemini "your-gemini-key"
git auth set openai "your-openai-key"
git auth set anthropic "your-anthropic-key"

# View configured credentials (keys are automatically masked)
git auth list
```

commitguard auto-detects the first available AI provider:

| Provider | Setup Command | Install SDK |
|---|---|---|
| Google Gemini | `git auth set gemini <key>` | `pip install google-genai` |
| OpenAI | `git auth set openai <key>` | `pip install openai` |
| Anthropic Claude | `git auth set anthropic <key>` | `pip install anthropic` |
| Ollama (local) | *(none — zero credentials needed)* | [ollama.ai](https://ollama.ai) |

---

## Configuration

Copy `config.yaml` and edit as needed. All fields are optional.

```yaml
ai:
  provider: gemini          # explicit; omit for autodetect
  timeout_seconds: 10

  # Toggle individual semantic checks
  checks:
    documentation_emoji: true
    debug_and_garbage_code: true

  # Project-specific custom rules in natural language
  custom_rules:
    - "All public functions must have docstrings"
    - "No raw SQL queries without parameter binding"

rules:
  blocked_filenames:
    - MY_CUSTOM_AGENT.md
  allowed_path_prefixes:
    - docs/internal/        # whitelist overrides all block rules
```

Point to a custom config file:

```bash
export COMMITGUARD_CONFIG=/path/to/my-config.yaml
```

---

## Commit message format

```
<type>(<scope>): <subject>
```

| Field | Rules |
|---|---|
| `type` | `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore` |
| `scope` | Mandatory. Lowercase alphanumeric + hyphens/dots. |
| `subject` | 3–100 chars. No emoji. |

**Valid examples:**
```
feat(ui): add snap layouts support
fix(core): resolve null pointer in session handler
docs(api): update authentication endpoint reference
chore(deps): upgrade numpy to 2.1.0
```

---

## Output examples

**Rejection:**
```
[commitguard] Commit rejected -- 2 issue(s) found

  [BLOCKED FILES]
  [X] GEMINI.md
    -> AI agent instruction file must not be committed

  [AI ANALYSIS]
  [X] Debug code detected  (category: debug_code)
    -> Line 47 in auth.py: print("DEBUG token:", token)
       Remove or replace with proper logging

[commitguard] Fix the issues above and retry.
```

**Success:**
```
[commitguard] [OK] All checks passed (heuristics + AI)
```

---

## Uninstall

```powershell
# Windows
.\uninstall.ps1
```

```bash
# Unix/macOS
./uninstall.sh
```

---

## Project structure

```
commitguard/
├── git_guard.py          ← validation engine (entry point)
├── git.cmd               ← Windows PATH shim
├── git                   ← Unix PATH shim
├── install.ps1 / .sh     ← installers
├── uninstall.ps1 / .sh   ← uninstallers
├── config.yaml           ← optional user configuration
├── src/
│   ├── config.py         ← config loader
│   ├── credentials.py    ← secure credential storage & auth CLI
│   ├── output.py         ← stderr formatter
│   ├── layer1/           ← heuristic validators
│   ├── layer2/           ← AI analysis orchestrator
│   └── providers/        ← AI provider implementations
│       ├── base.py       ← abstract AIProvider interface
│       ├── gemini.py
│       ├── openai.py
│       ├── anthropic.py
│       └── ollama.py
└── tests/                ← pytest test suite (90%+ coverage target)
```

---

## Requirements

- Python ≥ 3.11
- Git (any version)
- `pyyaml` (optional, for `config.yaml` support)
- One AI provider SDK (optional — heuristics-only mode works without any)
