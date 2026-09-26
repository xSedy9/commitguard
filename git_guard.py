#!/usr/bin/env python3
"""
git_guard.py — commitguard validation engine.

This script is the entry point called by the git shim (git.cmd / git).
It intercepts 'git commit' calls, runs two-layer validation, and either
forwards to the real git executable or rejects with a structured report.

All other git commands (push, log, status, …) are passed through with
zero processing overhead.

Usage (invoked by the shim, not directly):
    python git_guard.py commit -m "feat(ui): add button"
    python git_guard.py push origin main   # ← transparent passthrough
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

# Ensure the repo root is on sys.path so 'src.*' imports work
# regardless of the current working directory.
sys.path.insert(0, str(Path(__file__).parent))

from src.config import load_config
from src.layer1.files import check_staged_files
from src.layer1.message import validate_message
from src.layer2.analyzer import run_analysis, should_skip_ai
from src.output import rejection, success, warn
from src.providers import get_provider

# ---------------------------------------------------------------------------
# Real git discovery
# ---------------------------------------------------------------------------
# The installer sets COMMITGUARD_REAL_GIT or patches this sentinel.
# If neither is available, we auto-discover by scanning PATH entries that
# do NOT contain our own directory.

_SENTINEL = "__REAL_GIT_PLACEHOLDER__"


def _find_real_git() -> str:
    """
    Locate the real git executable, excluding the commitguard shim directory.

    Search order:
    1. COMMITGUARD_REAL_GIT environment variable.
    2. Auto-discovery: scan PATH entries, skip the one containing this script,
       return the first 'git' (or 'git.exe' on Windows) found.

    Returns:
        Absolute path string to the real git executable.

    Raises:
        SystemExit: If the real git cannot be found.
    """
    env_override = os.environ.get("COMMITGUARD_REAL_GIT")
    if env_override and Path(env_override).exists():
        return env_override

    own_dir = str(Path(__file__).parent.resolve())
    path_dirs = os.environ.get("PATH", "").split(os.pathsep)

    for directory in path_dirs:
        if not directory or Path(directory).resolve() == Path(own_dir):
            continue
        for name in ("git.exe", "git"):
            candidate = Path(directory) / name
            if candidate.is_file():
                return str(candidate)

    sys.stderr.write(
        "[commitguard] FATAL: Could not locate the real git executable.\n"
        "  Set COMMITGUARD_REAL_GIT=<path> or re-run the installer.\n"
    )
    sys.exit(2)


# Resolved once at import time (or overridden in tests via monkeypatching).
REAL_GIT: str = _find_real_git()


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------


def _run_git(*args: str) -> subprocess.CompletedProcess:
    """Run REAL_GIT with the given arguments, capturing output."""
    return subprocess.run(
        [REAL_GIT, *args],
        capture_output=True,
        text=True,
    )


def get_staged_files() -> list[str]:
    """
    Retrieve the list of files staged for the next commit.

    Excludes deleted files (only ACMR filter) so that removing a bad
    file is always permitted.

    Returns:
        List of relative file paths from the repo root.
    """
    result = _run_git("diff", "--cached", "--name-only", "--diff-filter=ACMR")
    return [f for f in result.stdout.splitlines() if f.strip()]


def get_staged_diff() -> str:
    """
    Retrieve the full unified diff of staged changes.

    Returns:
        Output of 'git diff --cached' as a string.
    """
    return _run_git("diff", "--cached").stdout


# ---------------------------------------------------------------------------
# Argument parsing helpers
# ---------------------------------------------------------------------------


def strip_no_verify(args: list[str]) -> tuple[list[str], bool]:
    """
    Remove --no-verify and -n from the argument list.

    Args:
        args: Raw commit sub-arguments (everything after 'git commit').

    Returns:
        Tuple of (cleaned_args, was_stripped).
    """
    stripped = False
    cleaned = [a for a in args if a not in ("--no-verify", "-n") or (stripped := True) and False]
    # The walrus trick above is tricky; use explicit loop for clarity:
    cleaned = []
    was_stripped = False
    for arg in args:
        if arg in ("--no-verify", "-n"):
            was_stripped = True
        else:
            cleaned.append(arg)
    return cleaned, was_stripped


def strip_commitguard_flags(args: list[str]) -> tuple[list[str], bool]:
    """
    Remove --commitguard-no-ai from the argument list.

    Args:
        args: Commit sub-arguments.

    Returns:
        Tuple of (cleaned_args, no_ai_requested).
    """
    no_ai = "--commitguard-no-ai" in args
    cleaned = [a for a in args if a != "--commitguard-no-ai"]
    return cleaned, no_ai


def extract_message(args: list[str]) -> str | None:
    """
    Extract the commit message from -m / --message flags.

    Args:
        args: Commit sub-arguments.

    Returns:
        The message string, or None if no -m flag was present.
    """
    for i, arg in enumerate(args):
        if arg in ("-m", "--message") and i + 1 < len(args):
            return args[i + 1]
        if arg.startswith("-m") and len(arg) > 2:
            return arg[2:]
    return None


# ---------------------------------------------------------------------------
# Core flow
# ---------------------------------------------------------------------------


def passthrough(git_args: list[str]) -> int:
    """
    Forward any git command to the real git executable unchanged.

    Args:
        git_args: Full list of arguments to pass (e.g. ['push', 'origin']).

    Returns:
        The real git process exit code.
    """
    result = subprocess.run([REAL_GIT, *git_args])
    return result.returncode


def run(argv: list[str]) -> int:
    """
    Main validation flow.

    Args:
        argv: sys.argv[1:] as passed by the shim.

    Returns:
        Exit code: 0 on success / passthrough, 1 on rejection.
    """
    args = list(argv)

    # Intercept credential management subcommands
    if args and args[0] in ("auth", "credentials"):
        from src.credentials import handle_auth_command

        return handle_auth_command(args[1:])

    # All non-commit commands pass through immediately.
    if not args or args[0] != "commit":
        return passthrough(args)

    commit_args = args[1:]

    # ── Pre-flight: strip bypass and custom flags ─────────────────────────
    commit_args, was_no_verify = strip_no_verify(commit_args)
    if was_no_verify:
        warn("--no-verify was stripped. Bypass is not permitted.")

    commit_args, no_ai = strip_commitguard_flags(commit_args)

    # ── Load config ───────────────────────────────────────────────────────
    config = load_config()

    # ── Gather staged context ─────────────────────────────────────────────
    staged_files = get_staged_files()
    message = extract_message(commit_args)

    all_issues: list[dict] = []

    # ── Layer 1: Heuristics ───────────────────────────────────────────────
    file_issues = check_staged_files(staged_files, config)
    all_issues.extend(file_issues)

    if message:
        msg_issues = validate_message(message, config)
        all_issues.extend(msg_issues)

    # Reject immediately on any Layer 1 failure (skip Layer 2).
    if all_issues:
        rejection(all_issues)
        return 1

    # ── Layer 2: AI ───────────────────────────────────────────────────────
    if not config.ai.enabled:
        success("heuristics only — AI disabled in config")
        return passthrough(["commit", *commit_args])

    provider = None
    if not no_ai:
        provider = get_provider(
            provider_name=config.ai.provider,
            model=config.ai.model,
            timeout=config.ai.timeout_seconds,
        )

    if provider is None:
        if not no_ai:
            warn("No AI provider available — AI checks skipped (heuristics only).")
        success("heuristics only")
        return passthrough(["commit", *commit_args])

    diff = get_staged_diff()

    if should_skip_ai(staged_files, diff, config=config, skip_ai_flag=no_ai):
        success("heuristics only — fast-path (no docs, small diff)")
        return passthrough(["commit", *commit_args])

    ai_result = run_analysis(
        provider=provider,
        commit_message=message or "",
        staged_files=staged_files,
        diff=diff,
        config=config,
    )

    if not ai_result.passed:
        ai_issues = [
            {
                "kind": "ai",
                "title": f"{issue.message}  (category: {issue.category})",
                "detail": issue.detail,
            }
            for issue in ai_result.issues
        ]
        rejection(ai_issues)
        return 1

    success("heuristics + AI")
    return passthrough(["commit", *commit_args])


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
