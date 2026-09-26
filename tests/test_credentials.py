"""
Tests for src/credentials.py — secure file-based credential storage.
"""
from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import patch

import pytest

from src.credentials import (
    get_credential,
    get_credentials_path,
    handle_auth_command,
    list_credentials,
    load_credentials,
    mask_key,
    remove_credential,
    set_credential,
)
import git_guard


@pytest.fixture
def temp_creds(tmp_path, monkeypatch):
    """Fixture that redirects credentials to an isolated temporary file."""
    creds_file = tmp_path / "credentials"
    monkeypatch.setenv("COMMITGUARD_CREDENTIALS_FILE", str(creds_file))
    return creds_file


class TestCredentialsPath:
    def test_default_path_ends_with_commitguard_credentials(self, monkeypatch):
        monkeypatch.delenv("COMMITGUARD_CREDENTIALS_FILE", raising=False)
        p = get_credentials_path()
        assert p.name == "credentials"
        assert p.parent.name == ".commitguard"

    def test_override_path(self, monkeypatch, tmp_path):
        target = tmp_path / "custom_creds"
        monkeypatch.setenv("COMMITGUARD_CREDENTIALS_FILE", str(target))
        assert get_credentials_path() == target


class TestCredentialOperations:
    def test_load_empty_when_missing(self, temp_creds):
        assert load_credentials() == {}

    def test_set_and_get_credential(self, temp_creds):
        set_credential("gemini", "AIzaSyTestKey123")
        assert get_credential("gemini") == "AIzaSyTestKey123"

    def test_case_insensitivity(self, temp_creds):
        set_credential("OpenAI", "sk-TestKey456")
        assert get_credential("openai") == "sk-TestKey456"
        assert get_credential("OPENAI") == "sk-TestKey456"

    def test_gemini_aliases(self, temp_creds):
        temp_creds.write_text("google_api_key = test-key-alias\n", encoding="utf-8")
        assert get_credential("gemini") == "test-key-alias"

    def test_anthropic_aliases(self, temp_creds):
        temp_creds.write_text("claude = test-claude-key\n", encoding="utf-8")
        assert get_credential("anthropic") == "test-claude-key"

    def test_get_nonexistent_returns_none(self, temp_creds):
        assert get_credential("nonexistent") is None

    def test_remove_credential(self, temp_creds):
        set_credential("gemini", "AIzaSyTestKey123")
        assert get_credential("gemini") == "AIzaSyTestKey123"
        removed = remove_credential("gemini")
        assert removed is True
        assert get_credential("gemini") is None

    def test_remove_nonexistent_returns_false(self, temp_creds):
        assert remove_credential("nonexistent") is False

    def test_mask_key(self):
        assert mask_key("") == ""
        assert mask_key("short") == "****"
        assert mask_key("AIzaSy123456789") == "AIza...6789"

    def test_list_credentials(self, temp_creds):
        set_credential("gemini", "AIzaSy123456789")
        set_credential("openai", "sk-1234567890abcdef")
        listing = list_credentials()
        assert "gemini" in listing
        assert listing["gemini"] == "AIza...6789"
        assert "openai" in listing
        assert listing["openai"] == "sk-1...cdef"


class TestAuthCLI:
    def test_auth_path(self, temp_creds, capsys):
        ret = handle_auth_command(["path"])
        assert ret == 0
        out = capsys.readouterr().out
        assert str(temp_creds) in out

    def test_auth_set_and_get(self, temp_creds, capsys):
        ret_set = handle_auth_command(["set", "gemini", "AIzaSyTest123456"])
        assert ret_set == 0
        assert get_credential("gemini") == "AIzaSyTest123456"

        ret_get = handle_auth_command(["get", "gemini"])
        assert ret_get == 0
        out_get = capsys.readouterr().out
        assert "AIza...3456" in out_get

    def test_auth_get_missing(self, temp_creds, capsys):
        ret = handle_auth_command(["get", "nonexistent"])
        assert ret == 1
        err = capsys.readouterr().err
        assert "No credential configured" in err

    def test_auth_list(self, temp_creds, capsys):
        handle_auth_command(["set", "gemini", "AIzaSyTest123456"])
        ret = handle_auth_command(["list"])
        assert ret == 0
        out = capsys.readouterr().out
        assert "gemini" in out
        assert "AIza...3456" in out

    def test_auth_list_empty(self, temp_creds, capsys):
        ret = handle_auth_command(["list"])
        assert ret == 0
        out = capsys.readouterr().out
        assert "No credentials configured" in out

    def test_auth_remove(self, temp_creds, capsys):
        handle_auth_command(["set", "openai", "sk-1234567890"])
        ret = handle_auth_command(["remove", "openai"])
        assert ret == 0
        assert get_credential("openai") is None

    def test_auth_help(self, capsys):
        ret = handle_auth_command(["--help"])
        assert ret == 0
        err = capsys.readouterr().err
        assert "commitguard auth" in err

    def test_auth_no_args_shows_help(self, capsys):
        ret = handle_auth_command([])
        assert ret == 0
        err = capsys.readouterr().err
        assert "git auth set" in err

    def test_auth_set_missing_args(self, capsys):
        ret = handle_auth_command(["set", "gemini"])
        assert ret == 1
        err = capsys.readouterr().err
        assert "Usage: git auth set" in err

    def test_auth_get_missing_args(self, capsys):
        ret = handle_auth_command(["get"])
        assert ret == 1
        err = capsys.readouterr().err
        assert "Usage: git auth get" in err

    def test_auth_remove_missing_args(self, capsys):
        ret = handle_auth_command(["remove"])
        assert ret == 1
        err = capsys.readouterr().err
        assert "Usage: git auth remove" in err

    def test_auth_unknown_subcommand(self, capsys):
        ret = handle_auth_command(["foobar"])
        assert ret == 1
        err = capsys.readouterr().err
        assert "Unknown auth command" in err


class TestGitGuardAuthRouting:
    def test_git_guard_intercepts_auth(self, temp_creds, capsys):
        ret = git_guard.run(["auth", "path"])
        assert ret == 0
        out = capsys.readouterr().out
        assert str(temp_creds) in out

    def test_git_guard_intercepts_credentials(self, temp_creds, capsys):
        ret = git_guard.run(["credentials", "list"])
        assert ret == 0
        out = capsys.readouterr().out
        assert "No credentials configured" in out
