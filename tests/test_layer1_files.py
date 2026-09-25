"""
Tests for src/layer1/files.py — staged file blocklist checker.
"""
from __future__ import annotations

import pytest

from src.config import Config, RulesConfig
from src.layer1.files import check_staged_files


def _cfg(**kwargs) -> Config:
    """Helper: build a Config with custom RulesConfig fields."""
    cfg = Config()
    cfg.rules = RulesConfig(**kwargs)
    return cfg


class TestExactFilenames:
    """Built-in exact filename blocks."""

    @pytest.mark.parametrize(
        "filename",
        [
            "AGENTS.md",
            "agents.md",
            "GEMINI.md",
            "CLAUDE.md",
            "CURSOR.md",
            "COPILOT.md",
            "TASKS.md",
            "TODO.md",
            ".cursorrules",
            "AIDER.md",
            "CODEIUM.md",
        ],
    )
    def test_blocks_builtin_exact_names(self, filename, default_config):
        issues = check_staged_files([filename], default_config)
        assert len(issues) == 1
        assert issues[0]["kind"] == "blocked_file"
        assert issues[0]["title"] == filename

    def test_case_insensitive_match(self, default_config):
        issues = check_staged_files(["AgEnTs.Md"], default_config)
        assert len(issues) == 1

    def test_exact_name_in_subdirectory(self, default_config):
        issues = check_staged_files(["src/AGENTS.md"], default_config)
        assert len(issues) == 1

    def test_user_blocked_filename(self):
        cfg = _cfg(blocked_filenames=["MY_AGENT.md"])
        issues = check_staged_files(["MY_AGENT.md"], cfg)
        assert len(issues) == 1
        assert "user-defined" in issues[0]["detail"]

    def test_user_blocked_filename_case_insensitive(self):
        cfg = _cfg(blocked_filenames=["MY_AGENT.md"])
        issues = check_staged_files(["my_agent.md"], cfg)
        assert len(issues) == 1


class TestPatternBlocks:
    """Built-in filename pattern blocks."""

    @pytest.mark.parametrize(
        "filename",
        [
            "TASKS-2024.md",
            "TASKS_v2.md",
            "TODO-feature.md",
            "output.tmp",
            "build.tmp",
            "config.bak",
            "app.debug.log",
            "debug_run.py",
            "debug-output.txt",
            "test_output_2024.json",
            "scratch_idea.py",
            "scratch-notes.txt",
            "file.py~",
        ],
    )
    def test_blocks_builtin_patterns(self, filename, default_config):
        issues = check_staged_files([filename], default_config)
        assert len(issues) == 1, f"Expected {filename!r} to be blocked"
        assert "pattern" in issues[0]["detail"].lower()

    def test_pattern_match_case_insensitive(self, default_config):
        issues = check_staged_files(["OUTPUT.TMP"], default_config)
        assert len(issues) == 1


class TestPathPrefixBlocks:
    """Built-in path prefix blocks."""

    @pytest.mark.parametrize(
        "path",
        [
            ".gemini/config.json",
            ".antigravity/session.log",
            "scratch/idea.py",
            "__pycache__/module.pyc",
            ".aider/history",
        ],
    )
    def test_blocks_builtin_prefixes(self, path, default_config):
        issues = check_staged_files([path], default_config)
        assert len(issues) == 1
        assert "blocked directory" in issues[0]["detail"].lower()

    def test_user_blocked_prefix(self):
        cfg = _cfg(blocked_path_prefixes=["experiments/"])
        issues = check_staged_files(["experiments/run1.py"], cfg)
        assert len(issues) == 1

    def test_windows_backslash_path(self, default_config):
        issues = check_staged_files([".gemini\\config.json"], default_config)
        assert len(issues) == 1


class TestWhitelist:
    """allowed_path_prefixes override all block rules."""

    def test_allowed_prefix_overrides_exact_name_block(self):
        cfg = _cfg(allowed_path_prefixes=["docs/internal/"])
        # AGENTS.md is normally blocked — but whitelisted here
        issues = check_staged_files(["docs/internal/AGENTS.md"], cfg)
        assert issues == []

    def test_allowed_prefix_overrides_pattern_block(self):
        cfg = _cfg(allowed_path_prefixes=["archive/"])
        issues = check_staged_files(["archive/output.tmp"], cfg)
        assert issues == []

    def test_allowed_prefix_overrides_path_block(self):
        cfg = _cfg(allowed_path_prefixes=["scratch/"])
        issues = check_staged_files(["scratch/allowed.py"], cfg)
        assert issues == []


class TestCleanFiles:
    """Normal source files should never be blocked."""

    @pytest.mark.parametrize(
        "path",
        [
            "src/main.py",
            "tests/test_app.py",
            "README.md",
            "docs/guide.md",
            "pyproject.toml",
            "src/utils/helpers.py",
        ],
    )
    def test_clean_files_pass(self, path, default_config):
        issues = check_staged_files([path], default_config)
        assert issues == [], f"Unexpected block on {path!r}"


class TestMultipleFiles:
    """Multiple files — mixed blocked and clean."""

    def test_only_blocked_reported(self, default_config):
        files = ["src/main.py", "AGENTS.md", "tests/test_app.py", "debug_run.py"]
        issues = check_staged_files(files, default_config)
        blocked_titles = {i["title"] for i in issues}
        assert "AGENTS.md" in blocked_titles
        assert "debug_run.py" in blocked_titles
        assert "src/main.py" not in blocked_titles
        assert "tests/test_app.py" not in blocked_titles

    def test_empty_list_returns_no_issues(self, default_config):
        assert check_staged_files([], default_config) == []
