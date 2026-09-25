# ADR-0003: Two-Layer Validation Architecture (Heuristics + AI)

## Status
Accepted

## Date
2026-09-25

## Context
Invoking an external LLM API on every git commit introduces network latency (1-3 seconds), incurs API costs, and fails when disconnected from the internet. However, many critical quality gates (such as blocking agent prompt files, preventing debug file extensions, and validating Conventional Commit syntax) are completely deterministic and can be evaluated instantly using string matching and regular expressions.

## Decision
Partition the validation engine into two sequential layers:
1. **Layer 1 (Heuristics)**: Zero-network, sub-15ms Python checks covering file blocklists, regex patterns, path prefixes, Conventional Commit format, and anti-task reference filters.
2. **Layer 2 (Semantic AI)**: Asynchronous LLM evaluation covering documentation prose quality, debug code leakage, commit atomicity, and message-diff alignment.

Layer 2 only runs if Layer 1 passes without any issues.

## Consequences

### Positive
- Over 80% of invalid commits are rejected instantly at Layer 1 without consuming API tokens or network latency.
- Fast-path skips Layer 2 completely for small commits (<50 lines of diff) that do not alter documentation files.
- Layer 1 provides a hard, immutable boundary that works 100% offline.

### Negative
- Requires maintaining validation logic across two distinct sub-packages (`src/layer1` and `src/layer2`).
