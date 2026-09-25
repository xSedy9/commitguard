# Technical Roadmap

## 1. Short-Term Milestones (v0.2.x)

### 1.1 Python AST Heuristic Analyzer
- **Goal**: Move obvious debug print and `localhost` URL detections into Layer 1 using Python's native `ast` module.
- **Benefit**: Catch syntax-level debug statements in Python files in under 2ms without consuming LLM API tokens.

### 1.2 Validation Hash Cache
- **Goal**: Compute SHA-256 digests over `(commit_message, staged_diff)`.
- **Benefit**: Cache positive AI validation verdicts locally in `.commitguard/cache.db` to avoid duplicate API calls when amending or re-running commits.

### 1.3 Pre-Push Verification Support
- **Goal**: Provide an optional `git push` interceptor that validates entire branch histories prior to pushing upstream.

---

## 2. Medium-Term Milestones (v0.3.x)

### 2.1 Compiled Single-Binary Distribution
- **Goal**: Compile `git_guard.py` into a standalone native binary using PyInstaller or Nuitka (`commitguard.exe` for Windows, `commitguard` ELF for Linux/macOS).
- **Benefit**: Removes Python 3.11 runtime prerequisite on target workstations.

### 2.2 GitHub Action and CI Gate
- **Goal**: Publish a standard GitHub Action (`commitguard/action`) that runs the same Layer 1 and Layer 2 validation gates on incoming Pull Requests.
- **Benefit**: Enforces organizational quality policies on commits submitted from web interfaces or external contributors.

### 2.3 Local Model Optimization
- **Goal**: Native integration with small quantized models (e.g. Qwen 2.5 Coder 1.5B / Llama 3.2 1B) via Ollama and vLLM with structured output constraints.

---

## 3. Long-Term Vision (v1.0)

### 3.1 Multi-VCS Adaptor Interface
- Abstract version control operations to support emerging tools such as Jujutsu (`jj`) and Mercurial (`hg`) alongside Git.

### 3.2 Team Policy Sync
- Allow teams to publish centralized validation rules via HTTPS or git submodule configurations with cryptographic signature verification.
