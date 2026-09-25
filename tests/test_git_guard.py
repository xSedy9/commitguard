"""
Tests for git_guard.py — the main validation engine.

All subprocess calls and provider lookups are mocked.
"""
from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch, call

import pytest

import git_guard
from src.providers.base import AIIssue, AIResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(args: list[str]) -> int:
    """Call git_guard.run() with the given argument list."""
    return git_guard.run(args)


def _mock_git(staged_files: list[str] = None, diff: str = "") -> MagicMock:
    """Return a mock for subprocess.run that simulates git output."""
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


# ---------------------------------------------------------------------------
# Passthrough
# ---------------------------------------------------------------------------

class TestPassthrough:
    """Non-commit commands are forwarded without validation."""

    def test_push_is_passthrough(self, monkeypatch):
        mock_run = MagicMock(return_value=MagicMock(returncode=0))
        monkeypatch.setattr(subprocess, "run", mock_run)
        code = _run(["push", "origin", "main"])
        assert code == 0
        # Should have been called once — with real git + push args
        mock_run.assert_called_once()
        called_args = mock_run.call_args[0][0]
        assert "push" in called_args

    def test_status_is_passthrough(self, monkeypatch):
        mock_run = MagicMock(return_value=MagicMock(returncode=0))
        monkeypatch.setattr(subprocess, "run", mock_run)
        _run(["status"])
        called_args = mock_run.call_args[0][0]
        assert "status" in called_args

    def test_empty_args_passthrough(self, monkeypatch):
        mock_run = MagicMock(return_value=MagicMock(returncode=0))
        monkeypatch.setattr(subprocess, "run", mock_run)
        _run([])
        mock_run.assert_called_once()

    def test_log_returns_real_exit_code(self, monkeypatch):
        mock_run = MagicMock(return_value=MagicMock(returncode=128))
        monkeypatch.setattr(subprocess, "run", mock_run)
        code = _run(["log", "--oneline"])
        assert code == 128


# ---------------------------------------------------------------------------
# Argument stripping
# ---------------------------------------------------------------------------

class TestArgStripping:
    def test_strip_no_verify(self):
        cleaned, stripped = git_guard.strip_no_verify(["--no-verify", "-m", "msg"])
        assert "--no-verify" not in cleaned
        assert stripped is True

    def test_strip_n_flag(self):
        cleaned, stripped = git_guard.strip_no_verify(["-n", "-m", "msg"])
        assert "-n" not in cleaned
        assert stripped is True

    def test_no_strip_when_absent(self):
        cleaned, stripped = git_guard.strip_no_verify(["-m", "msg"])
        assert cleaned == ["-m", "msg"]
        assert stripped is False

    def test_strip_commitguard_no_ai(self):
        cleaned, no_ai = git_guard.strip_commitguard_flags(
            ["-m", "msg", "--commitguard-no-ai"]
        )
        assert "--commitguard-no-ai" not in cleaned
        assert no_ai is True

    def test_no_ai_false_when_absent(self):
        _, no_ai = git_guard.strip_commitguard_flags(["-m", "msg"])
        assert no_ai is False


# ---------------------------------------------------------------------------
# Message extraction
# ---------------------------------------------------------------------------

class TestExtractMessage:
    def test_extract_m_flag(self):
        assert git_guard.extract_message(["-m", "feat(x): y"]) == "feat(x): y"

    def test_extract_message_flag(self):
        assert git_guard.extract_message(["--message", "feat(x): y"]) == "feat(x): y"

    def test_extract_m_concatenated(self):
        assert git_guard.extract_message(["-mfeat(x): y"]) == "feat(x): y"

    def test_returns_none_when_absent(self):
        assert git_guard.extract_message(["--amend"]) is None

    def test_returns_none_for_empty(self):
        assert git_guard.extract_message([]) is None


# ---------------------------------------------------------------------------
# Layer 1 rejection
# ---------------------------------------------------------------------------

class TestLayer1Rejection:
    def test_rejects_blocked_file(self, monkeypatch, capsys):
        mock_run = _mock_git(staged_files=["AGENTS.md"], diff="")
        monkeypatch.setattr(subprocess, "run", mock_run)

        code = _run(["commit", "-m", "feat(x): add file"])
        assert code == 1
        err = capsys.readouterr().err
        assert "AGENTS.md" in err

    def test_rejects_bad_message(self, monkeypatch, capsys):
        mock_run = _mock_git(staged_files=["src/main.py"], diff="+line\n" * 10)
        monkeypatch.setattr(subprocess, "run", mock_run)

        code = _run(["commit", "-m", "bad message no format"])
        assert code == 1
        err = capsys.readouterr().err
        assert "format" in err.lower() or "commitguard" in err

    def test_layer1_fail_skips_ai(self, monkeypatch):
        mock_run = _mock_git(staged_files=["AGENTS.md"])
        monkeypatch.setattr(subprocess, "run", mock_run)

        with patch("git_guard.get_provider") as mock_provider:
            _run(["commit", "-m", "feat(x): add file"])
            mock_provider.assert_not_called()


# ---------------------------------------------------------------------------
# Layer 2 and AI flow
# ---------------------------------------------------------------------------

class TestAIFlow:
    def _setup(self, monkeypatch, staged=None, diff="", ai_result=None):
        staged = staged or ["src/main.py"]
        mock_run = _mock_git(staged_files=staged, diff=diff)
        monkeypatch.setattr(subprocess, "run", mock_run)

        if ai_result is None:
            ai_result = AIResult(passed=True)

        mock_provider = MagicMock()
        mock_provider.analyze.return_value = ai_result

        monkeypatch.setattr(git_guard, "get_provider", lambda **kw: mock_provider)
        return mock_provider

    def test_passes_and_calls_real_git(self, monkeypatch, capsys):
        provider = self._setup(monkeypatch, diff="x\n" * 60)
        code = _run(["commit", "-m", "feat(core): add feature"])
        assert code == 0
        err = capsys.readouterr().err
        assert "passed" in err.lower()

    def test_ai_rejection_returns_1(self, monkeypatch, capsys):
        issues = [AIIssue(category="debug_code", message="Debug", detail="line 1")]
        self._setup(monkeypatch, diff="x\n" * 60, ai_result=AIResult(passed=False, issues=issues))
        code = _run(["commit", "-m", "feat(core): add feature"])
        assert code == 1
        err = capsys.readouterr().err
        assert "AI ANALYSIS" in err

    def test_no_ai_flag_skips_provider(self, monkeypatch, capsys):
        mock_run = _mock_git(staged_files=["src/main.py"], diff="x\n" * 10)
        monkeypatch.setattr(subprocess, "run", mock_run)

        with patch("git_guard.get_provider") as mock_gp:
            _run(["commit", "-m", "feat(core): add feature", "--commitguard-no-ai"])
            mock_gp.assert_not_called()

    def test_no_provider_warns_and_passes(self, monkeypatch, capsys):
        mock_run = _mock_git(staged_files=["src/main.py"], diff="x\n" * 60)
        monkeypatch.setattr(subprocess, "run", mock_run)
        monkeypatch.setattr(git_guard, "get_provider", lambda **kw: None)

        code = _run(["commit", "-m", "feat(core): add feature"])
        assert code == 0
        err = capsys.readouterr().err
        assert "provider" in err.lower() or "heuristics" in err.lower()


# ---------------------------------------------------------------------------
# --no-verify warning
# ---------------------------------------------------------------------------

class TestNoVerifyWarning:
    def test_no_verify_stripped_and_warned(self, monkeypatch, capsys):
        mock_run = _mock_git(staged_files=["src/main.py"], diff="x\n" * 60)
        monkeypatch.setattr(subprocess, "run", mock_run)
        monkeypatch.setattr(git_guard, "get_provider", lambda **kw: None)

        _run(["commit", "--no-verify", "-m", "feat(core): add feature"])
        err = capsys.readouterr().err
        assert "stripped" in err.lower() or "no-verify" in err.lower()
