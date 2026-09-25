# API and Interface Specification

## 1. Command-Line Interface (CLI)

commitguard is invoked transparently by the PATH shim whenever `git` is executed.

### 1.1 Invocation Syntax
```bash
python git_guard.py <subcommand> [options...]
```

### 1.2 Subcommand Routing
- If `<subcommand>` != `"commit"`:
  Executes `passthrough()` immediately. All arguments are forwarded to the real git binary without inspection.
- If `<subcommand>` == `"commit"`:
  Executes the two-layer validation engine.

### 1.3 Exit Codes
| Exit Code | Meaning | Source |
|---|---|---|
| `0` | Success: Commit passed validation and was committed by real git, or non-commit command succeeded. | `git_guard.py` / real git |
| `1` | Validation Rejection: One or more Layer 1 or Layer 2 checks failed. Commit aborted. | `git_guard.py` |
| `2` | Fatal Error: Could not locate real git executable on system PATH. | `git_guard.py` |
| `128+` | Real git error code propagated from a passthrough command (e.g. fatal repository error). | real git |

### 1.4 Custom CLI Flags
- `--commitguard-no-ai`: Stripped from arguments before real git execution. Instructs commitguard to skip Layer 2 AI evaluation while enforcing all Layer 1 rules (intended for CI runners without API keys).

---

## 2. Python Core API

### 2.1 `git_guard` Module
```python
def run(argv: list[str]) -> int:
    """Main validation and passthrough coordinator."""

def passthrough(git_args: list[str]) -> int:
    """Forward command to real git and return its process exit code."""

def strip_no_verify(args: list[str]) -> tuple[list[str], bool]:
    """Remove --no-verify and -n flags from commit arguments."""

def strip_commitguard_flags(args: list[str]) -> tuple[list[str], bool]:
    """Extract and remove --commitguard-no-ai flag."""

def extract_message(args: list[str]) -> str | None:
    """Extract commit message text from -m or --message options."""

def get_staged_files() -> list[str]:
    """Return relative paths of staged files with filter ACMR."""

def get_staged_diff() -> str:
    """Return unified diff output from 'git diff --cached'."""
```

### 2.2 `src.config` Module
```python
@dataclass
class AIConfig:
    enabled: bool = True
    provider: Optional[str] = None
    model: Optional[str] = None
    timeout_seconds: int = 10
    max_diff_tokens: int = 8000

@dataclass
class RulesConfig:
    blocked_filenames: list[str] = field(default_factory=list)
    blocked_path_prefixes: list[str] = field(default_factory=list)
    allowed_path_prefixes: list[str] = field(default_factory=list)

@dataclass
class CommitMessageConfig:
    max_subject_length: int = 100
    require_scope: bool = True
    allowed_types: list[str] = field(default_factory=lambda: list(DEFAULT_ALLOWED_TYPES))

@dataclass
class Config:
    ai: AIConfig = field(default_factory=AIConfig)
    rules: RulesConfig = field(default_factory=RulesConfig)
    commit_message: CommitMessageConfig = field(default_factory=CommitMessageConfig)

def load_config(config_path: Optional[Path] = None) -> Config:
    """Load config.yaml with fallback to defaults and .env loading."""
```

### 2.3 `src.providers.base` Module
```python
@dataclass
class AIIssue:
    category: str  # Rule identifier (e.g. 'documentation_language')
    message: str   # High-level issue description
    detail: str    # Detailed context or line reference

@dataclass
class AIResult:
    passed: bool
    issues: list[AIIssue] = field(default_factory=list)

class AIProvider(ABC):
    @abstractmethod
    def analyze(self, prompt: str) -> AIResult:
        """Send prompt to LLM and return structured AIResult."""

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if credentials and dependencies are satisfied."""
```

### 2.4 `src.providers` Factory
```python
def get_provider(
    provider_name: Optional[str] = None,
    model: Optional[str] = None,
    timeout: int = 10,
) -> Optional[AIProvider]:
    """
    Return instantiated AIProvider based on explicit name or autodetect order:
    1. Gemini (GOOGLE_API_KEY / GEMINI_API_KEY)
    2. OpenAI (OPENAI_API_KEY)
    3. Anthropic (ANTHROPIC_API_KEY)
    4. Ollama (local server at http://localhost:11434)
    """
```

### 2.5 `src.output` Module
```python
def warn(message: str) -> None:
    """Write non-blocking warning to stderr with safe encoding fallback."""

def success(detail: str = "heuristics + AI") -> None:
    """Write confirmation to stderr when all checks succeed."""

def rejection(issues: list[dict]) -> None:
    """Write structured rejection report grouped by issue category to stderr."""
```
