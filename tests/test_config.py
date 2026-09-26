"""
Tests for src/config.py — configuration loader.
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from src.config import (
    BUILTIN_BLOCKED_FILENAMES,
    BUILTIN_BLOCKED_PATTERNS,
    BUILTIN_BLOCKED_PATH_PREFIXES,
    DEFAULT_ALLOWED_TYPES,
    Config,
    AIConfig,
    RulesConfig,
    CommitMessageConfig,
    load_config,
)


class TestDefaults:
    """load_config() with no file returns fully-populated defaults."""

    def test_returns_config_instance(self):
        cfg = load_config(config_path=Path("/nonexistent/path/config.yaml"))
        assert isinstance(cfg, Config)

    def test_ai_defaults(self):
        cfg = load_config(config_path=Path("/nonexistent"))
        assert cfg.ai.enabled is True
        assert cfg.ai.provider is None
        assert cfg.ai.model is None
        assert cfg.ai.timeout_seconds == 10
        assert cfg.ai.max_diff_tokens == 8000
        assert cfg.ai.checks.documentation_language is True
        assert cfg.ai.checks.documentation_emoji is True
        assert cfg.ai.checks.debug_and_garbage_code is True
        assert cfg.ai.checks.commit_atomicity is True
        assert cfg.ai.checks.message_diff_match is True
        assert cfg.ai.custom_rules == []

    def test_rules_defaults(self):
        cfg = load_config(config_path=Path("/nonexistent"))
        assert cfg.rules.blocked_filenames == []
        assert cfg.rules.blocked_path_prefixes == []
        assert cfg.rules.allowed_path_prefixes == []

    def test_commit_message_defaults(self):
        cfg = load_config(config_path=Path("/nonexistent"))
        assert cfg.commit_message.max_subject_length == 100
        assert cfg.commit_message.require_scope is True
        assert set(cfg.commit_message.allowed_types) == set(DEFAULT_ALLOWED_TYPES)


class TestYamlLoading:
    """load_config() reads valid YAML and merges overrides."""

    def test_full_override(self, tmp_path: Path):
        yaml_content = textwrap.dedent("""\
            ai:
              enabled: false
              provider: openai
              model: gpt-4o
              timeout_seconds: 5
              max_diff_tokens: 4000
            rules:
              blocked_filenames:
                - CUSTOM.md
              blocked_path_prefixes:
                - experiments/
              allowed_path_prefixes:
                - docs/internal/
            commit_message:
              max_subject_length: 72
              require_scope: false
              allowed_types:
                - feat
                - fix
        """)
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(yaml_content)
        cfg = load_config(config_path=cfg_file)

        assert cfg.ai.enabled is False
        assert cfg.ai.provider == "openai"
        assert cfg.ai.model == "gpt-4o"
        assert cfg.ai.timeout_seconds == 5
        assert cfg.ai.max_diff_tokens == 4000
        assert cfg.rules.blocked_filenames == ["CUSTOM.md"]
        assert cfg.rules.blocked_path_prefixes == ["experiments/"]
        assert cfg.rules.allowed_path_prefixes == ["docs/internal/"]
        assert cfg.commit_message.max_subject_length == 72
        assert cfg.commit_message.require_scope is False
        assert cfg.commit_message.allowed_types == ["feat", "fix"]

    def test_partial_override_keeps_defaults(self, tmp_path: Path):
        yaml_content = "ai:\n  timeout_seconds: 20\n"
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(yaml_content)
        cfg = load_config(config_path=cfg_file)

        assert cfg.ai.timeout_seconds == 20
        assert cfg.ai.enabled is True  # default unchanged
        assert cfg.commit_message.max_subject_length == 100  # default unchanged

    def test_empty_yaml_file_returns_defaults(self, tmp_path: Path):
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text("")
        cfg = load_config(config_path=cfg_file)
        assert cfg.ai.enabled is True

    def test_malformed_yaml_returns_defaults(self, tmp_path: Path):
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(": : broken yaml {{{\n")
        cfg = load_config(config_path=cfg_file)
        assert isinstance(cfg, Config)
        assert cfg.ai.enabled is True

    def test_yaml_checks_override(self, tmp_path: Path):
        yaml_content = textwrap.dedent("""\
            ai:
              checks:
                documentation_emoji: false
                debug_and_garbage_code: false
        """)
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(yaml_content)
        cfg = load_config(config_path=cfg_file)

        assert cfg.ai.checks.documentation_emoji is False
        assert cfg.ai.checks.debug_and_garbage_code is False
        assert cfg.ai.checks.documentation_language is True
        assert cfg.ai.checks.commit_atomicity is True
        assert cfg.ai.checks.message_diff_match is True

    def test_yaml_custom_rules_ai_section(self, tmp_path: Path):
        yaml_content = textwrap.dedent("""\
            ai:
              custom_rules:
                - "Public functions must have type hints"
                - "No raw SQL queries without parameters"
        """)
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(yaml_content)
        cfg = load_config(config_path=cfg_file)

        assert cfg.ai.custom_rules == [
            "Public functions must have type hints",
            "No raw SQL queries without parameters",
        ]

    def test_yaml_custom_rules_fallback_from_rules_section(self, tmp_path: Path):
        yaml_content = textwrap.dedent("""\
            rules:
              custom_rules:
                - "Fallback rule under rules section"
        """)
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(yaml_content)
        cfg = load_config(config_path=cfg_file)

        assert cfg.ai.custom_rules == [
            "Fallback rule under rules section",
        ]


class TestBuiltinConstants:
    """Built-in blocklists contain expected entries."""

    def test_agents_md_blocked(self):
        assert "agents.md" in BUILTIN_BLOCKED_FILENAMES

    def test_gemini_md_blocked(self):
        assert "gemini.md" in BUILTIN_BLOCKED_FILENAMES

    def test_tmp_pattern_present(self):
        assert any("tmp" in p for p in BUILTIN_BLOCKED_PATTERNS)

    def test_gemini_dir_blocked(self):
        assert ".gemini/" in BUILTIN_BLOCKED_PATH_PREFIXES

    def test_default_types_complete(self):
        expected = {"feat", "fix", "docs", "style", "refactor", "perf", "test", "chore"}
        assert expected == set(DEFAULT_ALLOWED_TYPES)
