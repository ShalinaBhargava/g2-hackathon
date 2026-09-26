"""Order matters: a review scored against an empty pool beats itself scored last (SPEC.md section 8).

Builds its own scorers so it never mutates the shared session fixture.
"""

import pytest

from novelty.data import load_corpus
from novelty.models import Submission
from novelty.scorer import build_default_scorer


def _sub(review: dict) -> Submission:
    return Submission(id=review["id"], headline=review["headline"], body=review["body"], recommend=review["recommend"])


@pytest.fixture(scope="module")
def corpus():
    return load_corpus()


def test_first_reviewer_outscores_same_review_submitted_last(settings, corpus):
    first = corpus[0]
    early = build_default_scorer(settings, with_corpus=False).score(_sub(first)).final

    late_scorer = build_default_scorer(settings, with_corpus=False)
    for review in corpus[1:]:
        late_scorer.ingest(_sub(review), claims=review["claims"])
    # Re-submit the same text as a new user: it is a near-copy of nothing (r001 was never ingested)
    # but every one of its points has been made by someone else since.
    late = late_scorer.score(_sub(first).model_copy(update={"id": "resubmit"})).final

    assert early > late


def test_score_and_ingest_makes_a_resubmission_a_duplicate(settings, corpus):
    scorer = build_default_scorer(settings, with_corpus=False)
    first = scorer.score_and_ingest(_sub(corpus[0]))
    again = scorer.score(_sub(corpus[0]).model_copy(update={"id": "again"}))
    assert not first.duplicate
    assert again.duplicate and again.final == 0.0 and again.duplicate_of == corpus[0]["id"]


def test_replay_is_monotone_on_average(settings, corpus):
    """Later reviews should, on average, be less novel than earlier ones."""
    scorer = build_default_scorer(settings, with_corpus=False)
    finals = []
    for review in corpus:
        finals.append(scorer.score(_sub(review)).final)
        scorer.ingest(_sub(review), claims=review["claims"])
    half = len(finals) // 2
    assert sum(finals[:half]) / half > sum(finals[half:]) / (len(finals) - half)
