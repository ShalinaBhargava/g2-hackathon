"""Unit tests for the pure scoring functions in novelty/scoring.py (SPEC.md section 3).

Tiny hand-made vectors and a fake judge: no embedding model, no Gemini.
"""

import numpy as np
import pytest

from novelty import scoring
from novelty.config import Settings
from novelty.store import KnownClaim

S = Settings(gemini_api_key="unused-in-unit-tests")


def _unit(*xs):
    v = np.asarray(xs, dtype=np.float32)
    return v / np.linalg.norm(v)


# [3] relevance --------------------------------------------------------------


def test_listing_similarity_is_cosine_per_row():
    listing = _unit(1, 0)[None, :]
    claims = np.stack([_unit(1, 0), _unit(0, 1), _unit(1, 1)])
    sims = scoring.listing_similarity(claims, listing)
    assert sims.shape == (3,)
    assert sims == pytest.approx([1.0, 0.0, 0.7071], abs=1e-3)
    assert scoring.listing_similarity(np.zeros((0, 2), dtype=np.float32), listing).shape == (0,)


def test_relevance_is_share_of_on_topic_claims():
    assert scoring.relevance([True, True, False, False]) == 0.5
    assert scoring.relevance([True]) == 1.0
    assert scoring.relevance([False, False]) == 0.0
    assert scoring.relevance([]) == 0.0


def test_gate_is_clamped_linear_ramp():
    assert scoring.gate(S.gate_low - 0.1, S) == 0.0
    assert scoring.gate(S.gate_low, S) == 0.0
    assert scoring.gate((S.gate_low + S.gate_high) / 2, S) == pytest.approx(0.5)
    assert scoring.gate(S.gate_high, S) == 1.0
    assert scoring.gate(0.99, S) == 1.0


# [4] novelty ----------------------------------------------------------------

_K1 = KnownClaim(text="Support is slow", source="r005")
_K2 = KnownClaim(text="No training is needed", source="r007")
_K3 = KnownClaim(text="Boards are intuitive", source="r024")
_MID = (S.known_low + S.known_high) / 2


class _FakeJudge:
    """Answers True only for known texts in `same`; records every call."""

    name = "fake"

    def __init__(self, same: set[str] = frozenset()):
        self.same = set(same)
        self.calls: list[tuple[str, str]] = []

    def same_point(self, claim, known):
        self.calls.append((claim, known))
        return known in self.same


def test_classify_off_topic_is_irrelevant_regardless_of_similarity():
    j = _FakeJudge()
    status, by, match, sim = scoring.classify_claim("x", False, [(_K1, 0.99)], j, S)
    assert (status, by, match, sim) == ("irrelevant", "relevance", _K1, 0.99)
    assert j.calls == []


def test_classify_new_when_pool_empty_or_best_below_low():
    j = _FakeJudge()
    assert scoring.classify_claim("x", True, [], j, S) == ("new", "cosine_low", None, 0.0)
    assert scoring.classify_claim("x", True, [(_K1, S.known_low - 0.01)], j, S) == (
        "new",
        "cosine_low",
        _K1,
        S.known_low - 0.01,
    )
    assert j.calls == []


def test_classify_known_by_cosine_alone_above_high():
    j = _FakeJudge()
    assert scoring.classify_claim("x", True, [(_K1, S.known_high), (_K2, _MID)], j, S) == (
        "known",
        "cosine_high",
        _K1,
        S.known_high,
    )
    assert j.calls == []


def test_classify_borderline_asks_judge_about_candidates_in_order():
    # Top candidate is not the same point, second one is: the judge must be asked about both,
    # and the verdict must name the candidate that matched.
    j = _FakeJudge(same={_K2.text})
    status, by, match, sim = scoring.classify_claim("x", True, [(_K1, 0.7), (_K2, 0.6), (_K3, 0.55)], j, S)
    assert (status, by, match, sim) == ("known", "judge", _K2, 0.6)
    assert j.calls == [("x", _K1.text), ("x", _K2.text)]


def test_classify_borderline_new_when_no_candidate_agrees():
    j = _FakeJudge()
    status, by, match, sim = scoring.classify_claim("x", True, [(_K1, 0.7), (_K2, 0.6)], j, S)
    assert (status, by, match, sim) == ("new", "judge", _K1, 0.7)
    assert j.calls == [("x", _K1.text), ("x", _K2.text)]


def test_classify_judge_skips_candidates_below_low():
    j = _FakeJudge()
    scoring.classify_claim("x", True, [(_K1, 0.7), (_K2, S.known_low - 0.05)], j, S)
    assert j.calls == [("x", _K1.text)]


def test_novelty_share_counts_irrelevant_in_denominator():
    assert scoring.novelty(["new", "known"]) == 0.5
    assert scoring.novelty(["new", "irrelevant", "irrelevant", "irrelevant"]) == 0.25
    assert scoring.novelty(["known", "known"]) == 0.0
    assert scoring.novelty([]) == 0.0


def test_substance_saturates_at_k():
    assert scoring.substance(0, S) == 0.0
    assert scoring.substance(1, S) == pytest.approx(1 / S.substance_claims)
    assert scoring.substance(S.substance_claims, S) == 1.0
    assert scoring.substance(S.substance_claims + 5, S) == 1.0


# final ------------------------------------------------------------------------


def test_final_is_product_in_unit_interval():
    assert scoring.final_score(1.0, 1.0, 1.0) == 1.0
    assert scoring.final_score(0.5, 0.5, 1.0) == 0.25
    assert scoring.final_score(0.0, 1.0, 1.0) == 0.0
    assert scoring.final_score(0.3333, 0.6667, 0.5) == pytest.approx(0.1111, abs=1e-4)
