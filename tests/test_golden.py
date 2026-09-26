"""
This is the headline requirement from the problem statement: reward truly novel
content, do not reward non-novel content, and never reward novel-but-irrelevant
content. Requires the embedding model and a Gemini key (responses are cached).
"""

import pytest

from novelty.data import load_golden
from tests.helpers import as_submission

_BANDS, _ITEMS = load_golden()


def _by_category(scores: dict[str, float], *categories: str) -> list[float]:
    return [scores[i["id"]] for i in _ITEMS if i["category"] in categories]


@pytest.fixture(scope="module")
def scores(scorer) -> dict[str, float]:
    return {it["id"]: scorer.score(as_submission(it)).final for it in _ITEMS}


def _param(item: dict):
    """Items flagged known_gap encode a requirement the scorer does not yet meet.

    They are strict expected failures: the requirement stays in the golden set, and the
    test turns red the moment the behaviour changes so the flag gets removed.
    """
    marks = [pytest.mark.xfail(strict=True, reason=item.get("note", "known gap"))] if item.get("known_gap") else []
    return pytest.param(item, id=f"{item['id']}-{item['category']}", marks=marks)


@pytest.mark.parametrize("item", [_param(i) for i in _ITEMS])
def test_golden_item_in_band(scorer, item):
    band = _BANDS[item["category"]]
    r = scorer.score(as_submission(item))
    msg = f"\n{item['note']}\n{r.explain()}"
    if "final_max" in band:
        assert r.final <= band["final_max"], msg
    if "final_min" in band:
        assert r.final >= band["final_min"], msg
    if "duplicate" in band:
        assert r.duplicate is band["duplicate"], msg


def test_novel_relevant_outscores_every_non_novel(scores):
    assert min(_by_category(scores, "novel_relevant")) > max(
        _by_category(scores, "rehash", "listing_restatement", "duplicate")
    )


def test_novel_irrelevant_never_beats_novel_relevant(scores):
    assert max(_by_category(scores, "novel_irrelevant")) < min(_by_category(scores, "novel_relevant"))


def test_padding_with_irrelevant_novelty_does_not_help(scores):
    for it in _ITEMS:
        if it["category"] == "padded_irrelevant":
            assert scores[it["id"]] <= scores[it["pair_of"]] + 1e-9, f"{it['id']} > {it['pair_of']}"


def test_breakdown_is_self_explaining(scorer):
    r = scorer.score(as_submission(next(i for i in _ITEMS if i["category"] == "mixed")))
    assert r.per_claim, "a mixed review must produce claims"
    assert {c.status for c in r.per_claim} >= {"new", "known"}
    assert all(c.best_match for c in r.per_claim if c.status == "known")
