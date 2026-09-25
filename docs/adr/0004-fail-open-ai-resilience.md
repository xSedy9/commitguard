# ADR-0004: Fail-Open Strategy for AI Layer Resilience

## Status
Accepted

## Date
2026-09-25

## Context
External cloud services experience outages, network timeouts, rate limit throttling (e.g. HTTP 429 / 503), and quota exhaustion. If commitguard blocked local git commits whenever an AI provider is unreachable or times out, developers and autonomous agents would be unable to save progress locally, completely halting software development.

## Decision
Adopt a strict fail-open policy for Layer 2:
- Any network timeout, connection error, HTTP error, or unparseable JSON response logs a warning to `stderr` and allows the commit to proceed.
- Layer 1 (Heuristics) remains strictly fail-closed: syntax, agent files, and forbidden patterns are never bypassed.

## Consequences

### Positive
- Developers and agents are never blocked from committing code due to external network latency or cloud provider downtime.
- Hard security boundaries (file blocklists, secret protection, bypass stripping) are preserved because Layer 1 never fails open.

### Negative
- Subtle issues (such as non-English prose in documentation or subtle debug prints) could pass into history during an active cloud provider outage.
