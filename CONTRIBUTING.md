# Contributing to commitguard

Thank you for your interest in contributing to commitguard!

## Development Guidelines

1. **Language**: Python >= 3.11 only.
2. **Git Flow**:
   - Every feature or fix must be developed in a separate branch: `<type>/<description>`.
   - Examples: `feat/new-provider`, `fix/layer1-regex`, `docs/update-guide`.
3. **Commit Messages**:
   - Must strictly follow Conventional Commits: `<type>(<scope>): <subject>`.
   - Allowed types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`.
   - Scope is mandatory: e.g. `feat(layer1): add filename pattern`.
   - No emoji in commit subjects.
   - Atomic commits: exactly one logical change per commit.
4. **Testing**:
   - All tests must pass before merging.
   - Target minimum 90% test coverage using `pytest`.
5. **Code Style & Documentation**:
   - Write PEP 257 docstrings for all modules, classes, and public functions.
   - Keep documentation prose in English without emoji.
