# Architecture Decision Records (ADRs)

## ADR-001: Selection of PATH Shim Over Standard Git Hooks

### Context
Standard git hooks (such as `.git/hooks/pre-commit`, Husky, or pre-commit framework) are the traditional mechanism for intercepting commits. However, modern autonomous AI agents frequently invoke `git commit --no-verify` or `-n` when executing repetitive tasks or attempting to bypass linter failures. When `--no-verify` is passed, Git deliberately bypasses all pre-commit hooks, rendering them ineffective in agentic development environments.

### Decision
Implement commitguard as a PATH shim (`git.cmd` on Windows, `git` POSIX shell script on Unix) that shadows the real git executable.

### Consequences
- **Positive**:
  - The shim inspects and strips `--no-verify` before the real git executable ever receives the command.
  - Operates globally across all repositories on the workstation without requiring repository-level `.git/hooks` initialization.
  - Transparent passthrough ensures non-commit commands incur less than 5ms overhead.
- **Negative**:
  - Requires PATH modification during installation.
  - On Windows, requires Administrator elevation if native Git is installed in system-scoped PATH.

---

## ADR-002: Pluggable AIProvider Interface Over Single-Vendor SDK

### Context
Initial prototypes coupled validation logic directly to the Google Gemini SDK. However, enterprise environments often require private, on-premise, or alternative hosted LLMs (such as OpenAI, Anthropic Claude, or local Ollama instances) due to compliance, cost, or connectivity constraints.

### Decision
Introduce an abstract base class `AIProvider` in `src/providers/base.py` with concrete implementations in `src/providers/` and an autodetecting factory in `src/providers/__init__.py`.

### Consequences
- **Positive**:
  - Validation engine (`src/layer2/analyzer.py`) has zero direct knowledge of specific LLM SDKs.
  - Users can select providers via `config.yaml` or rely on zero-config autodetection based on available environment variables.
  - Providers only require their specific SDK installed when active.
- **Negative**:
  - Requires maintaining uniform prompt specifications and JSON parsing across different LLM instruction-following capabilities.

---

## ADR-003: Two-Layer Architecture (Heuristic Filter + Semantic AI)

### Context
Invoking an LLM API on every git commit introduces network latency (1-3 seconds) and API costs, and would fail if working offline. Many rule violations (forbidden files, invalid commit message syntax, task number references) can be identified deterministically using regular expressions.

### Decision
Partition validation into two distinct layers:
1. **Layer 1 (Heuristics)**: Zero-network, sub-15ms Python checks covering file blocklists, regex patterns, path prefixes, and Conventional Commit structure.
2. **Layer 2 (Semantic AI)**: LLM analysis covering natural language quality, code hygiene, atomicity, and message-diff alignment.

### Consequences
- **Positive**:
  - 80%+ of invalid commits are rejected instantly at Layer 1 without consuming API tokens or network latency.
  - Fast-path skips Layer 2 completely for small commits (<50 lines) that do not alter documentation.
- **Negative**:
  - Requires maintaining logic across two distinct validation pipelines.

---

## ADR-004: Fail-Open Strategy for AI Provider Outages

### Context
Network connections drop, LLM providers experience service degradation or rate limits, and API keys may expire. If commitguard blocked commits during AI service outages, developers and agents would be unable to record progress.

### Decision
Adopt a strict fail-open policy for Layer 2: any network timeout, HTTP error, or JSON parsing exception emits a warning to `stderr` and permits the commit to proceed. Layer 1 heuristic checks remain strictly fail-closed.

### Consequences
- **Positive**:
  - Zero workflow blockage during third-party API outages or offline travel.
  - Security gates (file blocklists, bypass prevention) remain 100% active because Layer 1 never fails open.
- **Negative**:
  - Highly sophisticated debug code or non-English documentation could theoretically slip into a commit during an active API outage.

---

## ADR-005: Zero-Dependency Core with Optional Provider SDKs

### Context
Requiring users to install multiple heavy vendor SDKs (`google-genai`, `openai`, `anthropic`, `pyyaml`) to run a git wrapper creates high installation friction.

### Decision
The core engine (`git_guard.py`, `src/config.py`, `src/layer1/`, `src/output.py`) relies exclusively on the Python standard library. External SDKs are optional dependencies imported lazily only when their respective provider or YAML config is explicitly activated.

### Consequences
- **Positive**:
  - Immediate installation footprint: 0 external PyPI packages required for Layer 1 heuristic validation.
  - Local Ollama provider functions using pure stdlib `urllib.request`.
- **Negative**:
  - Lazy import logic must catch `ImportError` and provide user-friendly installation hints.
