"""Shared pytest fixtures for commitguard tests."""
from __future__ import annotations

import pytest

from src.config import Config, AIConfig, RulesConfig, CommitMessageConfig


@pytest.fixture()
def default_config() -> Config:
    """Return a default Config instance with no user overrides."""
    return Config()


@pytest.fixture()
def config_no_ai() -> Config:
    """Return a Config instance with AI layer disabled."""
    cfg = Config()
    cfg.ai = AIConfig(enabled=False)
    return cfg


@pytest.fixture()
def config_with_extras() -> Config:
    """Return a Config with additional user-defined blocked names and prefixes."""
    cfg = Config()
    cfg.rules = RulesConfig(
        blocked_filenames=["MY_AGENT.md"],
        blocked_path_prefixes=["experiments/"],
        allowed_path_prefixes=["docs/internal/"],
    )
    return cfg
