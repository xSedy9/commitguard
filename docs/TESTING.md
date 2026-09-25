# Testing Strategy and Test Suite Specification

## 1. Testing Philosophy

commitguard enforces strict quality standards through a multi-tier test suite:
1. **Zero External Dependencies in Tests**: All git subprocess calls, filesystem boundaries, network sockets, and LLM SDK clients are completely mocked using `unittest.mock` and `pytest-mock`.
2. **Determinism and Speed**: The full suite of 200+ tests executes in under 0.5 seconds, allowing instant feedback during local development and pre-commit checks.
3. **Comprehensive Coverage**: Every module maintains greater than 90% statement and branch coverage.

---

## 2. Test Suite Organization

```
tests/
├── conftest.py               # Shared fixtures (default_config, mock configs)
├── test_config.py            # YAML parsing, default merges, .env reading, winreg fallback
├── test_git_guard.py         # Entry point, CLI routing, flag stripping, git passthrough
├── test_layer1_files.py      # Filename blocklists, patterns, path prefixes, allowlists
├── test_layer1_message.py    # Conventional commits, emoji, subject length, task reference filters
├── test_layer2_analyzer.py   # AI prompt builder, diff clipping, skip-path logic, output formatting
└── test_providers.py         # Gemini, OpenAI, Anthropic, Ollama providers and get_provider factory
```

---

## 3. Mocking Harness

### 3.1 Subprocess Mocking for Real Git
Subprocess calls to real git are intercepted in `tests/test_git_guard.py` using a dynamic mock dispatcher:

```python
def _mock_git(staged_files=None, diff=""):
    staged_files = staged_files or []
    def _side_effect(cmd, **kwargs):
        result = MagicMock()
        result.returncode = 0
        args_str = " ".join(str(a) for a in cmd)
        if "--name-only" in args_str:
            result.stdout = "\n".join(staged_files) + ("\n" if staged_files else "")
        elif "--cached" in args_str and "--name-only" not in args_str:
            result.stdout = diff
        else:
            result.stdout = ""
        return result
    return MagicMock(side_effect=_side_effect)
```

### 3.2 AI Provider Mocking
AI provider calls are validated without network activity by mocking `AIProvider.analyze` to return deterministic `AIResult` instances:
- **Clean Pass**: `AIResult(passed=True, issues=[])`
- **Rejection**: `AIResult(passed=False, issues=[AIIssue(category=..., message=..., detail=...)])`
- **Exception Simulation**: Raising `TimeoutError`, `ConnectionError`, or HTTP status errors to verify fail-open behavior.

---

## 4. Test Execution

### 4.1 Running the Full Test Suite
```bash
python -m pytest -v
```

### 4.2 Running Specific Test Categories
```bash
# Test Layer 1 message rules (Conventional Commits, task references)
python -m pytest tests/test_layer1_message.py -v

# Test Layer 1 file rules (forbidden names, debug patterns)
python -m pytest tests/test_layer1_files.py -v

# Test AI providers and response parsing
python -m pytest tests/test_providers.py -v

# Test core CLI interception engine
python -m pytest tests/test_git_guard.py -v
```

### 4.3 Measuring Test Coverage
```bash
python -m pytest --cov=src --cov=git_guard --cov-report=term-missing
```
Minimum required statement coverage for pull requests or branch merges is 90%.
