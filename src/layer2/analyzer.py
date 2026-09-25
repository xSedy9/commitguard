"""
Layer 2 — AI-powered commit analysis orchestrator.

Builds the analysis prompt, dispatches it to the configured AIProvider,
handles timeouts and exceptions (always fail-open), and provides
the fast-path skip logic.
"""
from __future__ import annotations

import textwrap
import warnings

from src.config import Config
from src.providers.base import AIProvider, AIResult

# ── Prompt ────────────────────────────────────────────────────────────────────

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

    RULE 1 · documentation_language
    ─────────────────────────────────
    All human-readable prose inside staged .md, .rst, and .txt files MUST be in English.
    Exclusions (do NOT flag these): code blocks, inline code, URLs, file paths,
    variable/function names, technical identifiers, proper nouns.
    BLOCK if: more than 10 % of the prose sentences are in a non-English language.
    Examples of violations:
      • A Russian paragraph in a README.md
      • French instructions in a CONTRIBUTING.md
      • Mixed-language changelog entries

    RULE 2 · documentation_emoji
    ─────────────────────────────────
    Staged .md, .rst, and .txt files MUST NOT contain emoji characters anywhere
    in their prose content (section headings, paragraphs, bullet points, table cells).
    Emoji in code blocks are allowed.
    BLOCK if: any emoji character appears outside a code block in a documentation file.
    Examples of violations:
      • "## ✨ Features" heading
      • "- 🐛 Fixed login bug" bullet point
      • Table cell containing 🚀

    RULE 3 · debug_and_garbage_code
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
           if DEBUG:, if os.environ.get("DEV_MODE"):  — with no else branch

    RULE 4 · commit_atomicity
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
      • A feature + its documentation update

    RULE 5 · message_diff_match
    ─────────────────────────────────
    The commit message MUST accurately and specifically describe what the diff does.
    BLOCK if:
      • The message type is wrong (e.g. "feat" but the diff only modifies existing logic)
      • The scope does not match the files changed (e.g. scope "ui" but only backend files)
      • The subject is vague or generic:
          chore(misc): updates
          fix(core): fix things
          feat(ui): changes
      • The message claims one thing but the diff does another

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
          "category": "documentation_language",
          "message": "Non-English prose detected in README.md",
          "detail": "Found Russian text in lines 12-18. All documentation prose must be in English."
        }},
        {{
          "category": "debug_and_garbage_code",
          "message": "Debug print statement detected",
          "detail": "auth.py line 47: print(\\"DEBUG token:\\", token) — remove or replace with proper logging."
        }}
      ]
    }}

    Valid category values: documentation_language, documentation_emoji,
                           debug_and_garbage_code, commit_atomicity, message_diff_match
""")


def build_prompt(
    commit_message: str,
    staged_files: list[str],
    diff: str,
    max_diff_tokens: int = 8000,
) -> str:
    """
    Construct the analysis prompt to send to the AI provider.

    Truncates the diff if it exceeds the token budget (approx 4 chars/token).

    Args:
        commit_message: Full raw commit message (subject + optional body).
        staged_files: List of relative file paths that are staged.
        diff: Output of `git diff --cached`.
        max_diff_tokens: Maximum number of tokens to allocate for the diff.

    Returns:
        Formatted prompt string ready to pass to AIProvider.analyze().
    """
    char_limit = max_diff_tokens * 4
    truncated_diff = diff[:char_limit]
    if len(diff) > char_limit:
        truncated_diff += "\n\n[DIFF CLIPPED — token limit reached]"

    return _PROMPT_TEMPLATE.format(
        commit_message=commit_message or "(no message provided)",
        staged_files="\n".join(staged_files) if staged_files else "(none)",
        diff=truncated_diff or "(empty diff)",
    )


# ── Skip logic ────────────────────────────────────────────────────────────────

_DOC_EXTENSIONS = frozenset({".md", ".rst", ".txt"})
_FAST_PATH_LINE_LIMIT = 50


def should_skip_ai(
    staged_files: list[str],
    diff: str,
    skip_ai_flag: bool = False,
) -> bool:
    """
    Determine whether the AI layer (Layer 2) can be skipped.

    Skips when:
    - The --commitguard-no-ai flag was passed explicitly.
    - No documentation files (.md, .rst, .txt) are staged AND
      the diff is fewer than 50 lines.

    Args:
        staged_files: Relative paths of all staged files.
        diff: Output of `git diff --cached`.
        skip_ai_flag: True if --commitguard-no-ai was present.

    Returns:
        True if Layer 2 should be skipped.
    """
    if skip_ai_flag:
        return True

    has_docs = any(
        any(f.lower().endswith(ext) for ext in _DOC_EXTENSIONS)
        for f in staged_files
    )
    diff_lines = diff.count("\n")

    return not has_docs and diff_lines < _FAST_PATH_LINE_LIMIT


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
