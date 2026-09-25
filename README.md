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
| **language** | Non-English prose in `.md`/`.rst`/`.txt` files (>10%) |
| **debug_code** | Debug prints, hardcoded localhost/tokens, TODO/FIXME |
| **atomicity** | Diff mixes two+ unrelated domains |
| **mismatch** | Commit message doesn't describe the diff |

Layer 2 is skipped when no provider is configured, on timeout (fail-open),
or via `--commitguard-no-ai` (CI escape hatch).

---

## Installation

### Windows

```powershell
cd path\to\commitguard
.\install.ps1
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

commitguard auto-detects the first available AI provider:

| Provider | Environment variable | Install |
|---|---|---|
| Google Gemini | `GOOGLE_API_KEY` | `pip install google-genai` |
| OpenAI | `OPENAI_API_KEY` | `pip install openai` |
| Anthropic Claude | `ANTHROPIC_API_KEY` | `pip install anthropic` |
| Ollama (local) | *(none — auto-detected)* | [ollama.ai](https://ollama.ai) |

```bash
export GOOGLE_API_KEY="your-key-here"   # example
```

---

## Configuration

Copy `config.yaml` and edit as needed. All fields are optional.

```yaml
ai:
  provider: gemini          # explicit; omit for autodetect
  timeout_seconds: 10

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
[commitguard] Commit rejected — 2 issue(s) found

  [BLOCKED FILES]
  ✗ GEMINI.md
    → AI agent instruction file must not be committed

  [AI ANALYSIS]
  ✗ Debug code detected  (category: debug_code)
    → Line 47 in auth.py: print("DEBUG token:", token)
       Remove or replace with proper logging

[commitguard] Fix the issues above and retry.
```

**Success:**
```
[commitguard] ✓ All checks passed (heuristics + AI)
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
