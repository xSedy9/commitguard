# Developer Guide

## 1. Development Environment Setup

### 1.1 Prerequisites
- Python >= 3.11
- Git (system installation)
- Visual Studio Code, Cursor, or any text editor

### 1.2 Installation from Source
Clone the repository and install testing dependencies:
```bash
git clone <repository_url>
cd commitguard

# Install development dependencies
pip install -r requirements.txt
pip install pyyaml pytest pytest-mock
```

---

## 2. Git Workflow Standards

All contributors and AI agents must adhere to the following branch and commit rules:

### 2.1 Branching Strategy
- Direct commits to `master` are strictly prohibited.
- Work must occur in isolated feature branches: `<type>/<description>`.
- Examples:
  - `feat/anthropic-provider`
  - `fix/windows-path-order`
  - `docs/api-specification`

### 2.2 Conventional Commits Format
Every commit message must follow:
```
<type>(<scope>): <subject>
```
- **Type**: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`.
- **Scope**: Mandatory lowercase identifier (`core`, `layer1`, `layer2`, `providers`, `install`).
- **Subject**: 3 to 100 characters, no emoji, descriptive summary of the change.
- **Atomicity**: Exactly one logical change per commit.

---

## 3. Extending commitguard: Adding an AI Provider

New LLM providers must implement the `AIProvider` interface defined in `src/providers/base.py`:

### Step 1: Create Provider Module
Create `src/providers/<name>.py`:
```python
from __future__ import annotations
import os
from src.providers.base import AIProvider, AIResult

class CustomProvider(AIProvider):
    def __init__(self, model: str = "default-model", timeout: int = 10) -> None:
        self.model = model
        self.timeout = timeout

    def is_available(self) -> bool:
        """Verify API key is present in environment."""
        return bool(os.environ.get("CUSTOM_API_KEY"))

    def analyze(self, prompt: str) -> AIResult:
        """Invoke API, parse JSON, and return AIResult."""
        ...
```

### Step 2: Register in Provider Factory
Update `src/providers/__init__.py`:
1. Add `<name>` to `_PROVIDER_ORDER`.
2. Add lazy import mapping in `_load_provider_class`.

### Step 3: Add Unit Tests
Create tests in `tests/test_providers.py` asserting:
1. `is_available()` returns `False` when the environment variable is missing.
2. `is_available()` returns `True` when credentials are set.
3. Response parsing extracts `AIResult(passed=True)` and `AIResult(passed=False, issues=...)` correctly.
4. Parsing errors fail open to `AIResult(passed=True)`.

---

## 4. Quality Verification
Before submitting a branch for merge into `master`:
```bash
# Run the complete test suite
python -m pytest tests/ -v

# Verify code formatting and linting
python -m pytest --cov=src --cov-report=term
```
All 200+ unit tests must pass with zero errors.
