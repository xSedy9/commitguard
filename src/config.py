"""
Configuration loader for commitguard.

Loads settings from config.yaml (optional) and merges them with
built-in defaults. If the file is absent or pyyaml is not installed,
built-in defaults are used silently.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# ── Built-in defaults ────────────────────────────────────────────────────────

#: Exact filenames (lowercase) that are always blocked.
BUILTIN_BLOCKED_FILENAMES: frozenset[str] = frozenset(
    {
        "agents.md",
        "gemini.md",
        "claude.md",
        "cursor.md",
        "copilot.md",
        "tasks.md",
        "todo.md",
        ".cursorrules",
        "aider.md",
        "codeium.md",
    }
)

#: Basename regex patterns (case-insensitive) that are always blocked.
BUILTIN_BLOCKED_PATTERNS: tuple[str, ...] = (
    r"^tasks[._-]",
    r"^todo[._-]",
    r"\.tmp$",
    r"\.bak$",
    r"[._-]debug\.",
    r"^debug[._-]",
    r"^test_output",
    r"^scratch[._-]",
    r"~$",
)

#: Path prefixes (relative to repo root, POSIX) that are always blocked.
BUILTIN_BLOCKED_PATH_PREFIXES: tuple[str, ...] = (
    ".gemini/",
    ".antigravity/",
    "scratch/",
    "__pycache__/",
    ".aider/",
)

#: Conventional Commits types allowed by default.
DEFAULT_ALLOWED_TYPES: tuple[str, ...] = (
    "feat",
    "fix",
    "docs",
    "style",
    "refactor",
    "perf",
    "test",
    "chore",
)

# ── Dataclasses ──────────────────────────────────────────────────────────────


@dataclass
class AIConfig:
    """AI layer (Layer 2) settings."""

    enabled: bool = True
    """Set False to disable AI analysis entirely."""

    provider: Optional[str] = None
    """Explicit provider name ('gemini', 'openai', 'anthropic', 'ollama').
    None = autodetect from environment."""

    model: Optional[str] = None
    """Override the provider's default model identifier. None = provider default."""

    timeout_seconds: int = 10
    """Seconds before the AI request is abandoned (fail-open)."""

    max_diff_tokens: int = 8000
    """Approximate token budget for the diff sent to the AI."""


@dataclass
class RulesConfig:
    """User-defined rule overrides (appended to built-in lists)."""

    blocked_filenames: list[str] = field(default_factory=list)
    """Extra exact filenames (case-insensitive) to block."""

    blocked_path_prefixes: list[str] = field(default_factory=list)
    """Extra path prefixes to block."""

    allowed_path_prefixes: list[str] = field(default_factory=list)
    """Path prefixes that override all block rules (whitelist)."""


@dataclass
class CommitMessageConfig:
    """Commit message format settings."""

    max_subject_length: int = 100
    """Maximum number of characters in the subject line."""

    require_scope: bool = True
    """Whether the scope (parenthesised field) is mandatory."""

    allowed_types: list[str] = field(
        default_factory=lambda: list(DEFAULT_ALLOWED_TYPES)
    )
    """Conventional Commits types accepted by Layer 1."""


@dataclass
class Config:
    """
    Merged configuration: built-in defaults + optional config.yaml overrides.

    All three sub-configs are always present and fully populated with defaults.
    """

    ai: AIConfig = field(default_factory=AIConfig)
    rules: RulesConfig = field(default_factory=RulesConfig)
    commit_message: CommitMessageConfig = field(default_factory=CommitMessageConfig)


# ── Loader ────────────────────────────────────────────────────────────────────


def _find_config_file() -> Optional[Path]:
    """
    Locate config.yaml.

    Search order:
    1. COMMITGUARD_CONFIG environment variable (explicit path).
    2. config.yaml next to git_guard.py (repo root).

    Returns:
        Path to the config file, or None if not found.
    """
    env_path = os.environ.get("COMMITGUARD_CONFIG")
    if env_path:
        p = Path(env_path)
        return p if p.exists() else None

    # src/../ resolves to repo root regardless of CWD
    repo_root = Path(__file__).parent.parent
    candidate = repo_root / "config.yaml"
    return candidate if candidate.exists() else None


def load_config(config_path: Optional[Path] = None) -> Config:
    """
    Load and return a fully-populated Config object.

    Reads config.yaml if found; silently falls back to defaults when
    the file is missing, malformed, or pyyaml is not installed.

    Args:
        config_path: Explicit path to a config file. Overrides autodetect.

    Returns:
        Config populated from the file merged with built-in defaults.
    """
    cfg = Config()

    path = config_path or _find_config_file()
    if path is None:
        return cfg

    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError:
        return cfg  # pyyaml not installed — silent fallback

    try:
        with path.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
    except Exception:  # noqa: BLE001
        return cfg  # malformed YAML — silent fallback

    ai_raw = data.get("ai", {}) or {}
    cfg.ai = AIConfig(
        enabled=ai_raw.get("enabled", True),
        provider=ai_raw.get("provider", None),
        model=ai_raw.get("model", None),
        timeout_seconds=int(ai_raw.get("timeout_seconds", 10)),
        max_diff_tokens=int(ai_raw.get("max_diff_tokens", 8000)),
    )

    rules_raw = data.get("rules", {}) or {}
    cfg.rules = RulesConfig(
        blocked_filenames=list(rules_raw.get("blocked_filenames", [])),
        blocked_path_prefixes=list(rules_raw.get("blocked_path_prefixes", [])),
        allowed_path_prefixes=list(rules_raw.get("allowed_path_prefixes", [])),
    )

    msg_raw = data.get("commit_message", {}) or {}
    cfg.commit_message = CommitMessageConfig(
        max_subject_length=int(msg_raw.get("max_subject_length", 100)),
        require_scope=bool(msg_raw.get("require_scope", True)),
        allowed_types=list(
            msg_raw.get("allowed_types", list(DEFAULT_ALLOWED_TYPES))
        ),
    )

    return cfg
