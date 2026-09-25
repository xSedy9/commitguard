"""
Layer 1 — commit message format validation.

Enforces Conventional Commits format with mandatory scope and emoji-free messages.
Only the subject line (first line) is validated here;
multi-line body is allowed but not checked.
"""
from __future__ import annotations

import re

from src.config import Config

# Conventional Commits pattern: type(scope): subject
_MSG_RE = re.compile(
    r"^(?P<type>[a-z]+)\((?P<scope>[a-z][a-z0-9._-]*)\): (?P<subject>.{3,})$"
)

# Broad emoji detection via Unicode ranges
_EMOJI_RE = re.compile(
    "["
    "\U0001f600-\U0001f64f"  # emoticons
    "\U0001f300-\U0001f5ff"  # misc symbols & pictographs
    "\U0001f680-\U0001f6ff"  # transport & map
    "\U0001f1e0-\U0001f1ff"  # flags (enclosed letters)
    "\U00002700-\U000027bf"  # dingbats
    "\U0001f900-\U0001f9ff"  # supplemental symbols & pictographs
    "\U00002600-\U000026ff"  # misc symbols
    "\U0001fa00-\U0001fa9f"  # chess, medical symbols
    "\U00002b00-\U00002bff"  # misc symbols & arrows (⬆ is U+2B06)
    "\U000025a0-\U000025ff"  # geometric shapes
    "\U0000fe00-\U0000fe0f"  # variation selectors (️ is U+FE0F)
    "]+",
    flags=re.UNICODE,
)


def _has_emoji(text: str) -> bool:
    """Return True if text contains at least one emoji character."""
    return bool(_EMOJI_RE.search(text))


def _subject_line(message: str) -> str:
    """Extract and strip the first line of a commit message."""
    return (message.strip().splitlines() or [""])[0].strip()


def validate_message(message: str, config: Config) -> list[dict]:
    """
    Validate the commit message subject line against Layer 1 format rules.

    Checks applied in order:
    1. Non-empty message.
    2. No emoji in the subject line.
    3. Regex format: type(scope): subject.
    4. Known type from the allowed list.
    5. Subject length (3 ≤ len ≤ max_subject_length).

    Args:
        message: Full raw commit message (multi-line allowed).
        config: Loaded commitguard configuration.

    Returns:
        List of issue dicts with keys 'kind', 'title', 'detail'.
        Empty list means the message passed all checks.
    """
    issues: list[dict] = []
    subject = _subject_line(message)

    # 1. Empty check
    if not subject:
        issues.append(
            {
                "kind": "message_format",
                "title": "Empty commit message",
                "detail": "Commit message must not be empty.",
            }
        )
        return issues

    # 2. Emoji check
    if _has_emoji(subject):
        issues.append(
            {
                "kind": "message_format",
                "title": "Emoji in commit message",
                "detail": "Emoji characters are not allowed in commit messages.",
            }
        )

    # 3. Format check — returns early so we don't pile on with confusing errors
    match = _MSG_RE.match(subject)
    if not match:
        issues.append(
            {
                "kind": "message_format",
                "title": "Invalid commit message format",
                "detail": (
                    "Required format: <type>(<scope>): <subject>\n"
                    f"    Allowed types: {', '.join(config.commit_message.allowed_types)}\n"
                    "    Example: feat(ui): add snap layouts support"
                ),
            }
        )
        return issues

    commit_type = match.group("type")
    subject_text = match.group("subject")

    # 4. Type check
    if commit_type not in config.commit_message.allowed_types:
        issues.append(
            {
                "kind": "message_format",
                "title": f"Unknown commit type: '{commit_type}'",
                "detail": (
                    f"Allowed types: {', '.join(config.commit_message.allowed_types)}"
                ),
            }
        )

    # 5. Subject length check (regex already enforces min=3 via .{3,})
    max_len = config.commit_message.max_subject_length
    if len(subject_text) > max_len:
        issues.append(
            {
                "kind": "message_format",
                "title": f"Subject too long ({len(subject_text)} chars, max {max_len})",
                "detail": f"Shorten the subject to at most {max_len} characters.",
            }
        )

    return issues
