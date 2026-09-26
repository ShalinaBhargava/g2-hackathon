"""
The scoring math (SPEC.md section 3). Everything else in the package is plumbing:
embeddings, claim extraction, the known-claim pool, the CLI. The scorer in
scorer.py calls these in order and assembles the ScoreBreakdown.

All functions are pure: numpy / plain values in, plain floats / statuses out.
Keep them that way so they stay trivially unit-testable.
"""

from __future__ import annotations

import numpy as np

from novelty.config import Settings
from novelty.llm import SamePointJudge
from novelty.models import ClaimStatus, DecidedBy
from novelty.store import Candidate, KnownClaim

# ---------------------------------------------------------------------------
# [3] relevance
# ---------------------------------------------------------------------------


def listing_similarity(claim_vectors: np.ndarray, listing_vector: np.ndarray) -> np.ndarray:
    """cos(claim_i, listing) for every row of claim_vectors. Diagnostic only.

    Recorded in each ClaimVerdict so a human can see how far a claim sits from the
    listing text; it does not feed the score (see runs/01-baseline.md, failure 1).
    Returns an (n,) array, empty when there are no claims.
    """
    if claim_vectors.shape[0] == 0:
        return np.zeros(0, dtype=np.float32)
    return (claim_vectors @ listing_vector.T)[:, 0]


def relevance(on_topic: list[bool]) -> float:
    """Review-level relevance = share of claims the extractor marked on topic. 0.0 when empty."""
    if not on_topic:
        return 0.0
    return sum(1 for x in on_topic if x) / len(on_topic)


def gate(relevance_value: float, settings: Settings) -> float:
    """Linear ramp: 0 at settings.gate_low, 1 at settings.gate_high, clamped to [0, 1]."""
    lo, hi = settings.gate_low, settings.gate_high
    if hi <= lo:  # degenerate config: behave as a hard threshold
        return 1.0 if relevance_value >= hi else 0.0
    return float(min(1.0, max(0.0, (relevance_value - lo) / (hi - lo))))


# ---------------------------------------------------------------------------
# [4] novelty
# ---------------------------------------------------------------------------


def classify_claim(
    claim: str,
    on_topic: bool,
    candidates: list[Candidate],
    judge: SamePointJudge,
    settings: Settings,
) -> tuple[ClaimStatus, DecidedBy, KnownClaim | None, float]:
    """Decide whether one claim is new, known, or irrelevant.

    candidates: the k closest known claims with their cosines, best first.

    Order of checks:
      1. not on_topic                              -> irrelevant, "relevance"
      2. no candidates, or nearest cosine < known_low -> new, "cosine_low"
      3. nearest cosine >= known_high                 -> known, "cosine_high"
      4. borderline band: ask the judge about each candidate with cosine >= known_low,
         best first; the first "same point" makes the claim known, "judge".
         None agree                                -> new, "judge"

    Returns (status, decided_by, the known claim the judge matched or else the nearest one, its cosine).
    """
    best, best_sim = candidates[0] if candidates else (None, 0.0)

    if not on_topic:
        return "irrelevant", "relevance", best, best_sim
    if best is None or best_sim < settings.known_low:
        return "new", "cosine_low", best, best_sim
    if best_sim >= settings.known_high:
        return "known", "cosine_high", best, best_sim

    for known, sim in candidates:
        if sim < settings.known_low:
            break
        if judge.same_point(claim, known.text):
            return "known", "judge", known, sim
    return "new", "judge", best, best_sim


def novelty(statuses: list[ClaimStatus]) -> float:
    """Share of claims that are 'new': n_new / n_claims. Irrelevant claims stay in the denominator."""
    if not statuses:
        return 0.0
    return sum(1 for s in statuses if s == "new") / len(statuses)


def substance(n_new: int, settings: Settings) -> float:
    """min(1, n_new / settings.substance_claims)."""
    return min(1.0, n_new / settings.substance_claims)


# ---------------------------------------------------------------------------
# final
# ---------------------------------------------------------------------------


def final_score(gate_value: float, novelty_value: float, substance_value: float) -> float:
    """gate * novelty * substance, rounded to 4 decimals, guaranteed in [0, 1]."""
    result = round(gate_value * novelty_value * substance_value, 4)
    return float(min(1.0, max(0.0, result)))
