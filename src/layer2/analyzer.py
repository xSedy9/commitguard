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
    You are a strict code-review assistant validating a git commit.
    Analyze the following commit and return ONLY a valid JSON object.
    Do NOT include any prose, markdown formatting, or explanation outside the JSON.

    ## Commit Message
    {commit_message}

    ## Staged Files
    {staged_files}

    ## Diff (may be truncated)
    ```
    {diff}
    ```

    ## Your Task
    Check all four categories. For each failed check add one entry to "issues".

    1. **language** — All human-readable prose in staged .md/.rst/.txt files must
       be in English. Ignore code snippets, URLs, variable names, technical terms.
       Block if more than 10% of prose content is non-English.

    2. **debug_code** — Look for signs of temporary or diagnostic code:
       - Debug print statements (print("DEBUG:…"), console.log, fmt.Println("test"))
       - Hardcoded temporary values (url = "http://localhost:3000", TOKEN = "abc123")
       - Commented-out code blocks (3+ consecutive commented-out lines of real code)
       - Developer annotations (# TODO: remove, # FIXME: hack, # TEMP)
       - Diagnostic-only conditionals (if DEBUG:, if os.environ.get("DEV")) with no
         production fallback

    3. **atomicity** — The diff must represent exactly one logical change.
       Block if it mixes two or more unrelated domains, e.g.:
       - Business logic changes + dependency upgrades
       - UI changes + database schema changes
       - New feature + unrelated bug fix
       Allow: related changes that logically belong together (new function + its test).

    4. **mismatch** — The commit message must accurately describe the diff.
       Block if:
       - The message describes something different from what the diff actually does
       - The message is generic (chore(misc): updates, fix(core): fix things)
       - The message scope doesn't match the changed files

    ## Response Format (strict JSON only, nothing else outside)
    {{
      "passed": true,
      "issues": []
    }}

    Or if problems are found:
    {{
      "passed": false,
      "issues": [
        {{
          "category": "debug_code",
          "message": "Debug code detected",
          "detail": "Line 47 in auth.py: print(\\"DEBUG token:\\", token)\\nRemove or replace with proper logging"
        }}
      ]
    }}
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
