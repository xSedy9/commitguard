"""
Layer 1 — blocked file detection.

Checks staged files against built-in and user-configured blocklists.
Deleted files (excluded from the staged list by --diff-filter=ACMR)
are never checked — removing a bad file is always allowed.
"""
from __future__ import annotations

import re
from pathlib import PurePosixPath

from src.config import (
    BUILTIN_BLOCKED_FILENAMES,
    BUILTIN_BLOCKED_PATTERNS,
    BUILTIN_BLOCKED_PATH_PREFIXES,
    Config,
)


def _normalize(path: str) -> str:
    """Convert backslashes to forward slashes for uniform matching."""
    return path.replace("\\", "/")


def _is_allowed(normalized_path: str, allowed_prefixes: list[str]) -> bool:
    """
    Return True if the path starts with any user-defined allowed prefix.

    Allowed prefixes act as a whitelist that overrides all block rules.

    Args:
        normalized_path: POSIX-style relative path from repo root.
        allowed_prefixes: User-configured whitelist prefixes.

    Returns:
        True if the path is explicitly whitelisted.
    """
    return any(normalized_path.startswith(prefix) for prefix in allowed_prefixes)


def _check_exact_name(basename: str, extra_names: list[str]) -> str | None:
    """
    Return a rejection reason if the basename matches a built-in or user blocklist.

    Args:
        basename: Filename component of the path.
        extra_names: User-configured additional blocked filenames.

    Returns:
        Rejection reason string, or None if not blocked.
    """
    lower = basename.lower()
    if lower in BUILTIN_BLOCKED_FILENAMES:
        return "AI agent instruction file must not be committed"
    if lower in {n.lower() for n in extra_names}:
        return "File is in the user-defined blocked filename list"
    return None


def _check_pattern(basename: str) -> str | None:
    """
    Return a rejection reason if the basename matches any built-in pattern.

    Args:
        basename: Filename component of the path.

    Returns:
        Rejection reason string, or None if no pattern matches.
    """
    lower = basename.lower()
    for pattern in BUILTIN_BLOCKED_PATTERNS:
        if re.search(pattern, lower):
            return f"Matches blocked filename pattern: {pattern}"
    return None


def _check_path_prefix(normalized_path: str, extra_prefixes: list[str]) -> str | None:
    """
    Return a rejection reason if the path starts with a blocked prefix.

    Checks both built-in prefixes and user-configured additions.

    Args:
        normalized_path: POSIX-style relative path from repo root.
        extra_prefixes: User-configured additional blocked path prefixes.

    Returns:
        Rejection reason string, or None if not blocked.
    """
    all_prefixes = list(BUILTIN_BLOCKED_PATH_PREFIXES) + extra_prefixes
    for prefix in all_prefixes:
        if normalized_path.startswith(prefix):
            return f"Path is under blocked directory: {prefix}"
    return None


def check_staged_files(staged_files: list[str], config: Config) -> list[dict]:
    """
    Validate staged files against Layer 1 file blocklists.

    Checks are applied in order:
    1. Whitelist (allowed_path_prefixes) — skip if matched.
    2. Exact filename match (built-in + user list).
    3. Basename pattern match (built-in regexes).
    4. Path prefix match (built-in + user list).

    Args:
        staged_files: Relative paths from repo root. Deleted files must
                      already be excluded (via --diff-filter=ACMR).
        config: Loaded commitguard configuration.

    Returns:
        List of issue dicts with keys 'kind', 'title', 'detail'.
        Empty list means all files passed.
    """
    issues: list[dict] = []

    for path in staged_files:
        normalized = _normalize(path)

        # 1. Whitelist check — skip if explicitly allowed
        if _is_allowed(normalized, config.rules.allowed_path_prefixes):
            continue

        basename = PurePosixPath(normalized).name

        # 2. Exact filename
        reason = _check_exact_name(basename, config.rules.blocked_filenames)
        if reason:
            issues.append({"kind": "blocked_file", "title": path, "detail": reason})
            continue

        # 3. Filename pattern
        reason = _check_pattern(basename)
        if reason:
            issues.append({"kind": "blocked_file", "title": path, "detail": reason})
            continue

        # 4. Path prefix
        reason = _check_path_prefix(normalized, config.rules.blocked_path_prefixes)
        if reason:
            issues.append({"kind": "blocked_file", "title": path, "detail": reason})

    return issues
