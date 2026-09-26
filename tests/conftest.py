"""Shared fixtures.

Scoring needs Gemini for claim extraction and the borderline judge. Responses are
cached in data/cache/gemini.json, so a populated cache makes the suite replayable
without network access, but a GEMINI_API_KEY must still be set. Tests that need
the scorer are skipped when it is not.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from novelty.config import Settings  # noqa: E402
from novelty.data import load_golden  # noqa: E402
from novelty.scorer import build_default_scorer  # noqa: E402


@pytest.fixture(scope="session")
def settings() -> Settings:
    s = Settings()
    if not s.gemini_api_key:
        pytest.skip("GEMINI_API_KEY not set; scorer tests need Gemini")
    return s


@pytest.fixture(scope="session")
def scorer(settings):
    """Scorer seeded with all 50 corpus reviews. Shared across tests; tests must not ingest into it."""
    return build_default_scorer(settings)


@pytest.fixture(scope="session")
def golden():
    """(bands, {id: item})."""
    bands, items = load_golden()
    return bands, {it["id"]: it for it in items}
