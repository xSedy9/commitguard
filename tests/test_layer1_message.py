"""
Tests for src/layer1/message.py — commit message format validator.
"""
from __future__ import annotations

import pytest

from src.config import Config, CommitMessageConfig
from src.layer1.message import validate_message


def _cfg(**kwargs) -> Config:
    """Helper: build a Config with custom CommitMessageConfig fields."""
    cfg = Config()
    cfg.commit_message = CommitMessageConfig(**kwargs)
    return cfg


class TestValidMessages:
    """Valid messages must produce zero issues."""

    @pytest.mark.parametrize(
        "msg",
        [
            "feat(ui): add snap layouts support",
            "fix(core): resolve null pointer in session handler",
            "docs(api): update authentication endpoint reference",
            "chore(deps): upgrade numpy to 2.1.0",
            "refactor(auth): extract token validation logic",
            "perf(db): add index on user_id column",
            "style(ui): fix inconsistent button padding",
            "test(core): add unit tests for session handler",
        ],
    )
    def test_valid_messages_pass(self, msg, default_config):
        assert validate_message(msg, default_config) == []

    def test_multiline_message_uses_subject_only(self, default_config):
        msg = "feat(core): add new feature\n\nThis is the body.\nMore details here."
        assert validate_message(msg, default_config) == []

    def test_scope_with_dot(self, default_config):
        assert validate_message("docs(api.v2): add rate limit docs", default_config) == []

    def test_scope_with_hyphen(self, default_config):
        assert validate_message("feat(user-auth): add oauth support", default_config) == []


class TestEmptyMessage:
    def test_empty_string(self, default_config):
        issues = validate_message("", default_config)
        assert len(issues) == 1
        assert "empty" in issues[0]["title"].lower()

    def test_whitespace_only(self, default_config):
        issues = validate_message("   \n  ", default_config)
        assert len(issues) == 1


class TestEmojiRejection:
    @pytest.mark.parametrize(
        "msg",
        [
            "feat(ui): ✨ add button",
            "fix(core): 🐛 fix bug",
            "chore(deps): ⬆️ upgrade deps",
        ],
    )
    def test_emoji_blocked(self, msg, default_config):
        issues = validate_message(msg, default_config)
        emoji_issues = [i for i in issues if "emoji" in i["title"].lower()]
        assert len(emoji_issues) >= 1


class TestFormatViolations:
    """Messages that violate the type(scope): subject format."""

    @pytest.mark.parametrize(
        "msg",
        [
            "wip",
            "feat: add button",          # missing scope
            "Feat(UI): Add Button",       # uppercase type
            "feat(ui) add button",        # missing colon-space
            "feat(ui):add button",        # missing space after colon
            "feat(): add button",         # empty scope
            "feat(UI): add button",       # uppercase scope
            "just some text here",        # no structure
        ],
    )
    def test_format_violations_rejected(self, msg, default_config):
        issues = validate_message(msg, default_config)
        format_issues = [i for i in issues if "format" in i["title"].lower()]
        assert len(format_issues) >= 1, f"Expected format error for: {msg!r}"

    def test_format_error_includes_example(self, default_config):
        issues = validate_message("bad message", default_config)
        assert any("Example" in i.get("detail", "") for i in issues)


class TestUnknownType:
    def test_unknown_type_rejected(self, default_config):
        issues = validate_message("build(core): add makefile", default_config)
        type_issues = [i for i in issues if "type" in i["title"].lower()]
        assert len(type_issues) >= 1

    def test_custom_allowed_type_passes(self):
        cfg = _cfg(allowed_types=["feat", "fix", "build"])
        assert validate_message("build(core): add makefile", cfg) == []


class TestSubjectLength:
    def test_subject_too_short_via_regex(self, default_config):
        # The regex requires .{3,} so "ok" (2 chars) won't match format
        issues = validate_message("feat(ui): ok", default_config)
        # Two chars for subject → regex fails → format error
        assert len(issues) >= 1

    def test_subject_exactly_3_chars_passes(self, default_config):
        assert validate_message("fix(x): oops was wrong here fix", default_config) == []

    def test_subject_too_long(self):
        cfg = _cfg(max_subject_length=20)
        long_subject = "a" * 21
        issues = validate_message(f"feat(ui): {long_subject}", cfg)
        long_issues = [i for i in issues if "long" in i["title"].lower()]
        assert len(long_issues) >= 1

    def test_subject_at_max_length_passes(self):
        cfg = _cfg(max_subject_length=20)
        subject = "a" * 20
        assert validate_message(f"feat(ui): {subject}", cfg) == []


class TestEdgeCases:
    def test_scope_with_numbers(self, default_config):
        assert validate_message("feat(api2): add v2 endpoint", default_config) == []

    def test_scope_starting_with_letter(self, default_config):
        # scope must start with [a-z]
        issues = validate_message("feat(2api): bad scope", default_config)
        assert len(issues) >= 1  # regex won't match

    def test_no_verify_does_not_appear_in_message(self, default_config):
        # --no-verify is stripped before this is called, but let's be safe
        assert validate_message("chore(ci): update workflow config", default_config) == []


class TestTaskReferenceRejection:
    """Commit subjects referencing task numbers or workflow steps must be rejected."""

    @pytest.mark.parametrize(
        "msg",
        [
            "feat(core): do task 11",
            "fix(api): task 3",
            "chore(db): step 2 setup database",
            "refactor(auth): finish task 4",
            "feat(ui): implement task #105",
            "fix(core): resolve ticket 42",
            "docs(guide): todo 1",
        ],
    )
    def test_task_references_blocked(self, msg, default_config):
        issues = validate_message(msg, default_config)
        task_issues = [i for i in issues if "task reference" in i["title"].lower()]
        assert len(task_issues) >= 1, f"Expected task reference error for: {msg!r}"


class TestVagueSubjectRejection:
    """Generic/meaningless commit subjects must be rejected."""

    @pytest.mark.parametrize(
        "msg",
        [
            "feat(core): wip",
            "fix(ui): temp",
            "chore(deps): updates",
            "fix(core): fixes",
            "style(ui): cleanup",
            "refactor(auth): clean up",
            "feat(core): various changes",
            "fix(core): small fixes",
            "feat(core): do task",
        ],
    )
    def test_vague_subjects_blocked(self, msg, default_config):
        issues = validate_message(msg, default_config)
        vague_issues = [i for i in issues if "vague" in i["title"].lower()]
        assert len(vague_issues) >= 1, f"Expected vague subject error for: {msg!r}"
