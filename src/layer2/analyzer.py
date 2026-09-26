"""
Layer 2 — AI-powered commit analysis orchestrator.

Builds the analysis prompt, dispatches it to the configured AIProvider,
handles timeouts and exceptions (always fail-open), and provides
the fast-path skip logic.
"""
from __future__ import annotations

import textwrap
import warnings

from typing import Optional

from src.config import (
    BUILTIN_BLOCKED_FILENAMES,
    BUILTIN_BLOCKED_PATH_PREFIXES,
    Config,
)
from src.providers.base import AIProvider, AIResult

# ── Prompt Template ───────────────────────────────────────────────────────────

_PROMPT_TEMPLATE = textwrap.dedent("""\
    You are a strict automated gate that validates git commits before they enter history.
    Your job is to enforce the project rules exactly as written below.
    Return ONLY a JSON object — no prose, no markdown, no explanation outside the JSON.

    ═══════════════════════════════════════════════════════
    COMMIT UNDER REVIEW
    ═══════════════════════════════════════════════════════

    Commit message:
    {commit_message}

    Staged files:
    {staged_files}

    Diff (may be clipped at token limit):
    ```
    {diff}
    ```

    ═══════════════════════════════════════════════════════
    RULES — check every one, reject on ANY violation
    ═══════════════════════════════════════════════════════

{rules}

    ═══════════════════════════════════════════════════════
    OUTPUT FORMAT
    ═══════════════════════════════════════════════════════

    If ALL rules pass:
    {{
      "passed": true,
      "issues": []
    }}

    If ANY rule fails (include one entry per violated rule):
    {{
      "passed": false,
      "issues": [
        {{
          "category": "<one of valid categories>",
          "message": "<brief summary of violation>",
          "detail": "<specific file, line, or reason>"
        }}
      ]
    }}

    Valid category values: {valid_categories}
""")


def _generate_dynamic_rules(config: Config) -> tuple[str, list[str]]:
    """
    Generate dynamic rule descriptions and valid issue categories from config.

    Combines:
    - File and path restrictions (built-ins + config.rules)
    - Active semantic AI checks (config.ai.checks)
    - Commit message format conventions (config.commit_message)
    - Custom project-specific natural language rules (config.ai.custom_rules)

    Returns:
        Tuple of (formatted_rules_text, list_of_valid_categories).
    """
    rule_sections: list[str] = []
    categories: list[str] = []
    rule_number = 1

    # 1. File placement & exclusion rules
    all_blocked_files = sorted(
        set(BUILTIN_BLOCKED_FILENAMES) | {f.lower() for f in config.rules.blocked_filenames}
    )
    all_blocked_prefixes = sorted(
        set(BUILTIN_BLOCKED_PATH_PREFIXES) | set(config.rules.blocked_path_prefixes)
    )
    file_rule_lines = [
        f"RULE {rule_number} \u00b7 file_restrictions",
        "─────────────────────────────────",
        "Staged files MUST NOT contain prohibited files or prohibited directory paths.",
        "Prohibited filenames:",
        f"  {', '.join(all_blocked_files)}",
        "Prohibited path prefixes:",
        f"  {', '.join(all_blocked_prefixes)}",
    ]
    if config.rules.allowed_path_prefixes:
        file_rule_lines.append("Allowed path prefixes (strict whitelist):")
        file_rule_lines.append(f"  {', '.join(config.rules.allowed_path_prefixes)}")
    file_rule_lines.extend([
        "BLOCK if: any staged file matches a prohibited filename, prohibited path prefix,",
        "or falls outside allowed path prefixes.",
    ])
    rule_sections.append("\n".join(file_rule_lines))
    categories.append("file_restrictions")
    rule_number += 1

    # 2. Semantic Checks
    checks = config.ai.checks

    if checks.documentation_language:
        rule_sections.append(textwrap.dedent(f"""\
            RULE {rule_number} \u00b7 documentation_language
            ─────────────────────────────────
            All human-readable prose inside staged .md, .rst, and .txt files MUST be in English.
            Exclusions (do NOT flag these): code blocks, inline code, URLs, file paths,
            variable/function names, technical identifiers, proper nouns.
            BLOCK if: more than 10 % of the prose sentences are in a non-English language.
            Examples of violations:
              • A Russian paragraph in a README.md
              • French instructions in a CONTRIBUTING.md
              • Mixed-language changelog entries"""))
        categories.append("documentation_language")
        rule_number += 1

    if checks.documentation_emoji:
        rule_sections.append(textwrap.dedent(f"""\
            RULE {rule_number} \u00b7 documentation_emoji
            ─────────────────────────────────
            Staged .md, .rst, and .txt files MUST NOT contain emoji characters anywhere
            in their prose content (section headings, paragraphs, bullet points, table cells).
            Emoji in code blocks are allowed.
            BLOCK if: any emoji character appears outside a code block in a documentation file.
            Examples of violations:
              • "## ✨ Features" heading
              • "- 🐛 Fixed login bug" bullet point
              • Table cell containing 🚀"""))
        categories.append("documentation_emoji")
        rule_number += 1

    if checks.debug_and_garbage_code:
        rule_sections.append(textwrap.dedent(f"""\
            RULE {rule_number} \u00b7 debug_and_garbage_code
            ─────────────────────────────────
            The staged diff MUST NOT introduce temporary, diagnostic, or intermediate code.
            BLOCK if any of the following appear in the added lines (+):
              a) Debug output statements:
                   print("DEBUG: …"), console.log("here"), fmt.Println("test"), log.debug("…")
              b) Hardcoded local/temporary values:
                   url = "http://localhost:3000", TOKEN = "hardcoded_secret", API_KEY = "abc123"
              c) Commented-out code blocks:
                   3 or more consecutive commented-out lines that look like real code (not docs)
              d) Explicit temporary annotations:
                   # TODO: remove, # FIXME: remove this, # TEMP, # HACK, // TEMP:
                   (annotations marking code as "remove before commit")
              e) Diagnostic-only conditionals without a production path:
                   if DEBUG:, if os.environ.get("DEV_MODE"):  — with no else branch"""))
        categories.append("debug_and_garbage_code")
        rule_number += 1

    if checks.commit_atomicity:
        rule_sections.append(textwrap.dedent(f"""\
            RULE {rule_number} \u00b7 commit_atomicity
            ─────────────────────────────────
            The diff MUST represent exactly ONE logical change.
            BLOCK if the diff mixes two or more unrelated concerns, for example:
              • Business logic change + dependency version bump
              • UI layout change + database schema migration
              • New feature code + unrelated bug fix in another module
              • Refactoring in one module + new functionality in another
            ALLOW: changes that logically belong to the same unit of work:
              • A new function + its unit test
              • A bug fix + the regression test for it
              • A feature + its documentation update"""))
        categories.append("commit_atomicity")
        rule_number += 1

    if checks.message_diff_match:
        scope_str = (
            "Scope is required, e.g. 'type(scope): subject'"
            if config.commit_message.require_scope
            else "Scope is optional, e.g. 'type(scope): subject' or 'type: subject'"
        )
        allowed_types_str = ", ".join(config.commit_message.allowed_types)
        max_len = config.commit_message.max_subject_length

        rule_sections.append(textwrap.dedent(f"""\
            RULE {rule_number} \u00b7 message_diff_match
            ─────────────────────────────────
            The commit message MUST accurately and specifically describe what the diff does.
            Project commit conventions:
              • Allowed types: {allowed_types_str}
              • Format requirement: {scope_str}
              • Maximum subject length: {max_len} characters
            BLOCK if:
              • The message refers to internal task numbers, ticket IDs, or agent workflow steps
                (e.g. 'do task 11', 'task 3 completed', 'implement step 2', 'ticket #42')
                instead of describing the actual functional code modification.
              • The message type is wrong (e.g. "feat" but the diff only modifies existing logic or fixes a bug)
              • The scope does not match the files changed (e.g. scope "ui" but only backend files)
              • The subject is vague, generic, or non-descriptive:
                  chore(misc): updates
                  fix(core): fix things
                  feat(ui): changes
                  feat(core): do task 11
              • The message claims one thing but the diff does another"""))
        categories.append("message_diff_match")
        rule_number += 1

    # 3. Project-specific custom rules (natural language)
    if config.ai.custom_rules:
        custom_lines = [
            f"RULE {rule_number} \u00b7 custom_rule",
            "─────────────────────────────────",
            "The commit MUST satisfy all project-specific custom rules:",
        ]
        for r in config.ai.custom_rules:
            custom_lines.append(f"  • {r}")
        custom_lines.extend([
            "BLOCK if: any of the above custom project rules are violated.",
            'Report any violation using category "custom_rule".',
        ])
        rule_sections.append("\n".join(custom_lines))
        categories.append("custom_rule")
        rule_number += 1

    if not rule_sections:
        return "    (No active rules configured)", []

    formatted_text = "\n\n".join(textwrap.indent(section, "    ") for section in rule_sections)
    return formatted_text, categories


def build_prompt(
    commit_message: str,
    staged_files: list[str],
    diff: str,
    max_diff_tokens: int = 8000,
    config: Optional[Config] = None,
) -> str:
    """
    Construct the analysis prompt to send to the AI provider.

    Dynamically incorporates rules from configuration, including
    file restrictions, commit conventions, active semantic checks,
    and project-specific custom rules.

    Truncates the diff if it exceeds the token budget (approx 4 chars/token).

    Args:
        commit_message: Full raw commit message (subject + optional body).
        staged_files: List of relative file paths that are staged.
        diff: Output of `git diff --cached`.
        max_diff_tokens: Maximum number of tokens to allocate for the diff.
        config: Loaded commitguard configuration (defaults to default Config).

    Returns:
        Formatted prompt string ready to pass to AIProvider.analyze().
    """
    if config is None:
        config = Config()

    rules_text, categories = _generate_dynamic_rules(config)
    valid_categories = ", ".join(categories) if categories else "none"

    char_limit = max_diff_tokens * 4
    truncated_diff = diff[:char_limit]
    if len(diff) > char_limit:
        truncated_diff += "\n\n[DIFF CLIPPED — token limit reached]"

    return _PROMPT_TEMPLATE.format(
        commit_message=commit_message or "(no message provided)",
        staged_files="\n".join(staged_files) if staged_files else "(none)",
        diff=truncated_diff or "(empty diff)",
        rules=rules_text,
        valid_categories=valid_categories,
    )


# ── Skip logic ────────────────────────────────────────────────────────────────

_DOC_EXTENSIONS = frozenset({".md", ".rst", ".txt"})
_FAST_PATH_LINE_LIMIT = 50


def should_skip_ai(
    staged_files: list[str],
    diff: str,
    config: Optional[Config] = None,
    skip_ai_flag: bool = False,
) -> bool:
    """
    Determine whether the AI layer (Layer 2) can be skipped.

    Skips when:
    - The --commitguard-no-ai flag was passed explicitly.
    - Or all AI checks are disabled and no custom rules are defined.
    - Or no custom rules are defined, no staged documentation files require
      checking, and the diff is fewer than 50 lines.

    Args:
        staged_files: Relative paths of all staged files.
        diff: Output of `git diff --cached`.
        config: Loaded commitguard configuration (optional).
        skip_ai_flag: True if --commitguard-no-ai was present.

    Returns:
        True if Layer 2 should be skipped.
    """
    if isinstance(config, bool):
        skip_ai_flag = config
        config = None

    if skip_ai_flag:
        return True

    if config is not None:
        # If custom rules are defined, never fast-path skip:
        # custom rules may apply to any small code diff or file.
        if config.ai.custom_rules:
            return False

        checks = config.ai.checks
        any_checks_enabled = any((
            checks.documentation_language,
            checks.documentation_emoji,
            checks.debug_and_garbage_code,
            checks.commit_atomicity,
            checks.message_diff_match,
        ))
        if not any_checks_enabled:
            return True

        doc_checks_enabled = checks.documentation_language or checks.documentation_emoji
    else:
        doc_checks_enabled = True

    has_docs = any(
        any(f.lower().endswith(ext) for ext in _DOC_EXTENSIONS)
        for f in staged_files
    )
    diff_lines = diff.count("\n")

    if doc_checks_enabled and has_docs:
        return False

    return diff_lines < _FAST_PATH_LINE_LIMIT


# ── Analysis runner ───────────────────────────────────────────────────────────


def run_analysis(
    provider: AIProvider,
    commit_message: str,
    staged_files: list[str],
    diff: str,
    config: Config,
) -> AIResult:
    """
    Run Layer 2 AI analysis using the given provider.

    Builds the prompt, calls the provider, and handles any exception
    with fail-open behaviour (warns + allows the commit).

    Args:
        provider: A ready-to-use AIProvider instance.
        commit_message: Full commit message text.
        staged_files: Relative paths of staged files.
        diff: Output of `git diff --cached`.
        config: Loaded commitguard configuration.

    Returns:
        AIResult. On network timeout or any other error, returns
        AIResult(passed=True) and emits a warning to stderr.
    """
    prompt = build_prompt(
        commit_message=commit_message,
        staged_files=staged_files,
        diff=diff,
        max_diff_tokens=config.ai.max_diff_tokens,
        config=config,
    )

    try:
        return provider.analyze(prompt)
    except Exception as exc:  # noqa: BLE001 — intentional fail-open
        warnings.warn(
            f"[commitguard] \u26a0 AI analysis failed "
            f"({type(exc).__name__}: {exc}) \u2014 skipped (fail-open).",
            stacklevel=2,
        )
        return AIResult(passed=True, issues=[])
