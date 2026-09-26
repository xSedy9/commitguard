"""
Tests for src/layer2/analyzer.py and src/output.py.
"""
from __future__ import annotations

import io
import sys
import warnings
from unittest.mock import MagicMock

import pytest

from src.config import Config, AIConfig
from src.layer2.analyzer import build_prompt, should_skip_ai, run_analysis
from src.output import warn, success, rejection
from src.providers.base import AIIssue, AIResult


# ── build_prompt ──────────────────────────────────────────────────────────────

class TestBuildPrompt:
    def test_includes_commit_message(self):
        prompt = build_prompt("feat(ui): add button", [], "")
        assert "feat(ui): add button" in prompt

    def test_includes_staged_files(self):
        prompt = build_prompt("feat(x): y", ["src/a.py", "src/b.py"], "")
        assert "src/a.py" in prompt
        assert "src/b.py" in prompt

    def test_includes_diff(self):
        prompt = build_prompt("feat(x): y", [], "+new line\n-old line")
        assert "+new line" in prompt

    def test_diff_truncated_at_token_limit(self):
        big_diff = "x" * 100_000
        prompt = build_prompt("feat(x): y", [], big_diff, max_diff_tokens=100)
        assert "CLIPPED" in prompt

    def test_diff_not_truncated_within_limit(self):
        small_diff = "x" * 100
        prompt = build_prompt("feat(x): y", [], small_diff, max_diff_tokens=8000)
        assert "CLIPPED" not in prompt

    def test_empty_message_placeholder(self):
        prompt = build_prompt("", [], "")
        assert "no message" in prompt.lower()

    def test_no_staged_files_placeholder(self):
        prompt = build_prompt("feat(x): y", [], "")
        assert "(none)" in prompt

    def test_empty_diff_placeholder(self):
        prompt = build_prompt("feat(x): y", ["a.py"], "")
        assert "(empty diff)" in prompt

    def test_prompt_contains_all_standard_categories(self):
        prompt = build_prompt("feat(x): y", [], "")
        for category in ("documentation_language", "documentation_emoji",
                         "debug_and_garbage_code", "commit_atomicity", "message_diff_match",
                         "file_restrictions"):
            assert category in prompt

    def test_prompt_with_custom_rules(self):
        cfg = Config()
        cfg.ai.custom_rules = [
            "All public APIs must have type signatures",
            "No raw SQL queries without parameterized inputs",
        ]
        prompt = build_prompt("feat(api): add endpoint", ["src/api.py"], "+code", config=cfg)
        assert "custom_rule" in prompt
        assert "All public APIs must have type signatures" in prompt
        assert "No raw SQL queries without parameterized inputs" in prompt

    def test_prompt_with_disabled_checks(self):
        cfg = Config()
        cfg.ai.checks.documentation_emoji = False
        cfg.ai.checks.debug_and_garbage_code = False
        prompt = build_prompt("feat(x): y", [], "", config=cfg)
        assert "documentation_emoji" not in prompt
        assert "debug_and_garbage_code" not in prompt
        assert "documentation_language" in prompt
        assert "commit_atomicity" in prompt
        assert "message_diff_match" in prompt

    def test_prompt_custom_commit_conventions(self):
        cfg = Config()
        cfg.commit_message.allowed_types = ["feat", "fix"]
        cfg.commit_message.require_scope = False
        cfg.commit_message.max_subject_length = 50
        prompt = build_prompt("feat: test", [], "", config=cfg)
        assert "feat, fix" in prompt
        assert "Scope is optional" in prompt
        assert "50 characters" in prompt

    def test_prompt_with_allowed_path_prefixes(self):
        cfg = Config()
        cfg.rules.allowed_path_prefixes = ["src/", "tests/"]
        prompt = build_prompt("feat(core): update", [], "", config=cfg)
        assert "Allowed path prefixes" in prompt
        assert "src/, tests/" in prompt


# ── should_skip_ai ────────────────────────────────────────────────────────────

class TestShouldSkipAI:
    def test_skip_if_flag_set(self):
        assert should_skip_ai([], "", skip_ai_flag=True) is True

    def test_no_skip_if_md_file_present(self):
        assert should_skip_ai(["README.md"], "x\n" * 10, skip_ai_flag=False) is False

    def test_no_skip_if_rst_file_present(self):
        assert should_skip_ai(["docs/guide.rst"], "x\n" * 10) is False

    def test_no_skip_if_txt_file_present(self):
        assert should_skip_ai(["notes.txt"], "x\n" * 5) is False

    def test_skip_if_no_docs_and_small_diff(self):
        assert should_skip_ai(["src/main.py"], "x\n" * 10) is True

    def test_no_skip_if_no_docs_but_large_diff(self):
        big_diff = "x\n" * 100
        assert should_skip_ai(["src/main.py"], big_diff) is False

    def test_no_skip_if_no_docs_and_diff_exactly_50_lines(self):
        diff = "x\n" * 50  # 50 newlines → 50 lines
        assert should_skip_ai(["src/main.py"], diff) is False

    def test_skip_if_no_docs_and_diff_49_lines(self):
        diff = "x\n" * 49
        assert should_skip_ai(["src/main.py"], diff) is True

    def test_empty_staged_files_and_empty_diff_skip(self):
        assert should_skip_ai([], "") is True

    def test_case_insensitive_extension_check(self):
        assert should_skip_ai(["README.MD"], "x\n" * 5) is False

    def test_no_skip_when_custom_rules_present(self):
        cfg = Config()
        cfg.ai.custom_rules = ["Enforce type annotations"]
        # Even with no docs and 5-line diff, custom rules require AI evaluation
        assert should_skip_ai(["src/main.py"], "x\n" * 5, config=cfg) is False

    def test_skip_when_all_checks_disabled_and_no_custom_rules(self):
        cfg = Config()
        cfg.ai.checks.documentation_language = False
        cfg.ai.checks.documentation_emoji = False
        cfg.ai.checks.debug_and_garbage_code = False
        cfg.ai.checks.commit_atomicity = False
        cfg.ai.checks.message_diff_match = False
        cfg.ai.custom_rules = []
        # When all AI checks are disabled and no custom rules, skip AI
        assert should_skip_ai(["README.md"], "x\n" * 100, config=cfg) is True

    def test_skip_when_docs_staged_but_doc_checks_disabled_and_small_diff(self):
        cfg = Config()
        cfg.ai.checks.documentation_language = False
        cfg.ai.checks.documentation_emoji = False
        # Docs staged, but doc checks are disabled and diff is small (<50)
        assert should_skip_ai(["README.md"], "x\n" * 10, config=cfg) is True

    def test_positional_bool_backward_compat(self):
        # should_skip_ai(staged_files, diff, True)
        assert should_skip_ai(["README.md"], "x\n" * 10, True) is True


# ── run_analysis ──────────────────────────────────────────────────────────────

class TestRunAnalysis:
    def _make_provider(self, result: AIResult) -> MagicMock:
        provider = MagicMock()
        provider.analyze.return_value = result
        return provider

    def test_returns_passed_result(self):
        provider = self._make_provider(AIResult(passed=True))
        cfg = Config()
        result = run_analysis(provider, "feat(x): y", [], "diff", cfg)
        assert result.passed is True

    def test_returns_failed_result_with_issues(self):
        issues = [AIIssue(category="debug_code", message="Debug", detail="line 1")]
        provider = self._make_provider(AIResult(passed=False, issues=issues))
        cfg = Config()
        result = run_analysis(provider, "feat(x): y", [], "diff", cfg)
        assert result.passed is False
        assert len(result.issues) == 1

    def test_fail_open_on_provider_exception(self):
        provider = MagicMock()
        provider.analyze.side_effect = RuntimeError("network error")
        cfg = Config()

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = run_analysis(provider, "feat(x): y", [], "diff", cfg)

        assert result.passed is True
        assert len(w) == 1
        assert "fail-open" in str(w[0].message).lower()

    def test_provider_receives_built_prompt(self):
        provider = self._make_provider(AIResult(passed=True))
        cfg = Config()
        run_analysis(provider, "feat(ui): add button", ["src/a.py"], "+line", cfg)

        call_args = provider.analyze.call_args
        prompt_sent = call_args[0][0]
        assert "feat(ui): add button" in prompt_sent
        assert "src/a.py" in prompt_sent

    def test_diff_truncated_per_config(self):
        provider = self._make_provider(AIResult(passed=True))
        cfg = Config()
        cfg.ai = AIConfig(max_diff_tokens=10)
        big_diff = "x" * 10_000

        run_analysis(provider, "feat(x): y", [], big_diff, cfg)
        prompt_sent = provider.analyze.call_args[0][0]
        assert "CLIPPED" in prompt_sent


# ── output formatting ─────────────────────────────────────────────────────────

class TestOutput:
    """Tests for src/output.py — all output captured from stderr."""

    def test_warn_format(self, capsys):
        warn("test warning message")
        out = capsys.readouterr().err
        assert "[commitguard]" in out
        assert "test warning message" in out

    def test_success_contains_detail(self, capsys):
        success("heuristics + AI")
        out = capsys.readouterr().err
        assert "heuristics + AI" in out
        assert "passed" in out.lower()

    def test_rejection_shows_count(self, capsys):
        issues = [
            {"kind": "blocked_file", "title": "AGENTS.md", "detail": "AI file"},
            {"kind": "message_format", "title": "Bad format", "detail": "Use type(scope)"},
        ]
        rejection(issues)
        out = capsys.readouterr().err
        assert "2 issue(s)" in out

    def test_rejection_groups_by_kind(self, capsys):
        issues = [
            {"kind": "blocked_file", "title": "AGENTS.md", "detail": "reason"},
            {"kind": "ai", "title": "Debug code", "detail": "line 1"},
        ]
        rejection(issues)
        out = capsys.readouterr().err
        assert "[BLOCKED FILES]" in out
        assert "[AI ANALYSIS]" in out
        assert "[COMMIT MESSAGE]" not in out

    def test_rejection_footer(self, capsys):
        rejection([{"kind": "ai", "title": "X", "detail": "Y"}])
        out = capsys.readouterr().err
        assert "Fix the issues" in out

    def test_rejection_empty_kind_not_shown(self, capsys):
        issues = [{"kind": "blocked_file", "title": "X", "detail": "Y"}]
        rejection(issues)
        out = capsys.readouterr().err
        assert "[AI ANALYSIS]" not in out
        assert "[COMMIT MESSAGE]" not in out
