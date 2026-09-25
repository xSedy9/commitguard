"""
Output formatting for commitguard.

All output is written to stderr to avoid interfering with git's own stdout.
The format follows the specification in docs/SPECIFICATION.md § 4.
"""
from __future__ import annotations

import sys
from typing import TextIO


def _write(message: str, file: TextIO | None = None) -> None:
    """Write a single line to the output stream (default: sys.stderr)."""
    print(message, file=file if file is not None else sys.stderr)


def warn(message: str) -> None:
    """
    Print a non-blocking warning to stderr.

    Args:
        message: Warning text (without the [commitguard] prefix).
    """
    _write(f"[commitguard] \u26a0 {message}")


def success(detail: str = "heuristics + AI") -> None:
    """
    Print the success message to stderr.

    Args:
        detail: Short description of which checks ran (shown in parentheses).
    """
    _write(f"[commitguard] \u2713 All checks passed ({detail})")


def rejection(issues: list[dict]) -> None:
    """
    Print a structured rejection report to stderr.

    Groups issues by kind and formats them per the specification.

    Args:
        issues: List of dicts with keys:
                  'kind'  — one of 'blocked_file', 'message_format', 'ai'
                  'title' — short label shown after the ✗ marker
                  'detail'— explanation shown indented below the label
    """
    count = len(issues)
    _write(f"[commitguard] Commit rejected \u2014 {count} issue(s) found\n")

    _print_group(
        issues,
        kind="blocked_file",
        header="[BLOCKED FILES]",
    )
    _print_group(
        issues,
        kind="message_format",
        header="[COMMIT MESSAGE]",
    )
    _print_group(
        issues,
        kind="ai",
        header="[AI ANALYSIS]",
    )

    _write("[commitguard] Fix the issues above and retry.")


def _print_group(issues: list[dict], kind: str, header: str) -> None:
    """
    Print one section of the rejection report if there are issues of that kind.

    Args:
        issues: Full issue list.
        kind: Issue kind to filter by.
        header: Section header string (e.g. '[BLOCKED FILES]').
    """
    group = [i for i in issues if i.get("kind") == kind]
    if not group:
        return
    _write(f"  {header}")
    for issue in group:
        _write(f"  \u2717 {issue['title']}")
        _write(f"    \u2192 {issue['detail']}")
        _write("")
