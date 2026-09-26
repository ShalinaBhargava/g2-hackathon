"""Data shapes: what comes in, what goes out"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Recommend = Literal["yes", "no", "mixed"]
ClaimStatus = Literal["new", "known", "irrelevant"]
DecidedBy = Literal["relevance", "cosine_high", "cosine_low", "judge"]


class Submission(BaseModel):
    """The user-generated content: three user-provided properties."""

    headline: str = ""
    body: str = ""
    recommend: Recommend = "mixed"
    id: str | None = None

    @property
    def full_text(self) -> str:
        return f"{self.headline.strip()}\n{self.body.strip()}".strip()


class ExtractedClaim(BaseModel):
    """One atomic claim from the extractor, with its relevance verdict."""

    text: str
    on_topic: bool = Field(description="extractor's verdict: is this claim about the product in the listing?")


class ClaimVerdict(BaseModel):
    """One row of the per-claim explanation."""

    claim: str
    on_topic: bool = Field(description="extractor's relevance verdict; False -> status is 'irrelevant'")
    relevance: float = Field(description="cos(claim, listing); diagnostic only, not used in the score")
    status: ClaimStatus
    decided_by: DecidedBy
    best_match: str | None = Field(default=None, description="closest known claim, if any")
    best_match_source: str | None = Field(default=None, description="review id or 'listing'")
    best_similarity: float = Field(default=0.0, description="cos(claim, best_match)")


class ScoreBreakdown(BaseModel):
    """Every score explains itself."""

    submission_id: str | None = None
    recommend: Recommend
    duplicate: bool
    duplicate_of: str | None = None
    duplicate_similarity: float = 0.0
    relevance: float = Field(description="share of claims the extractor marked on topic")
    gate: float = Field(description="ramp(relevance) in [0, 1]")
    novelty: float = Field(description="n_new / n_claims")
    substance: float = Field(description="min(1, n_new / K)")
    final: float = Field(ge=0.0, le=1.0)
    per_claim: list[ClaimVerdict] = Field(default_factory=list)
    extractor: str = Field(description="which claim extractor produced per_claim")

    @property
    def n_new(self) -> int:
        return sum(1 for c in self.per_claim if c.status == "new")

    @classmethod
    def zero(
        cls,
        sub: Submission,
        extractor: str,
        *,
        duplicate: bool = False,
        duplicate_of: str | None = None,
        duplicate_similarity: float = 0.0,
    ) -> ScoreBreakdown:
        """A 0.0 result for duplicates and submissions with no claims."""
        return cls(
            submission_id=sub.id,
            recommend=sub.recommend,
            duplicate=duplicate,
            duplicate_of=duplicate_of,
            duplicate_similarity=duplicate_similarity,
            relevance=0.0,
            gate=0.0,
            novelty=0.0,
            substance=0.0,
            final=0.0,
            per_claim=[],
            extractor=extractor,
        )

    def explain(self) -> str:
        lines = [
            f"final={self.final:.3f}  (gate {self.gate:.2f} x novelty {self.novelty:.2f} x substance {self.substance:.2f})",
            f"duplicate={self.duplicate}"
            + (f" of {self.duplicate_of} (jaccard {self.duplicate_similarity:.2f})" if self.duplicate else ""),
            f"relevance={self.relevance:.3f}  recommend={self.recommend}  extractor={self.extractor}",
        ]
        for c in self.per_claim:
            tail = f"  ~ [{c.best_match_source}] {c.best_match!r} ({c.best_similarity:.2f})" if c.best_match else ""
            topic = "on " if c.on_topic else "off"
            lines.append(f"  - {c.status:<10} {topic} cos={c.relevance:.2f} via {c.decided_by:<11} {c.claim!r}{tail}")
        return "\n".join(lines)
