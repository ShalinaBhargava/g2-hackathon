"""Pipeline orchestration (SPEC.md section 3). The math lives in scoring.py."""

from __future__ import annotations

from dataclasses import dataclass

from novelty import scoring
from novelty.config import Settings
from novelty.data import load_corpus, load_fixed_content
from novelty.embed import Embedder, ProductNeutralEmbedder, SentenceTransformerEmbedder
from novelty.llm import ClaimExtractor, SamePointJudge, build_llm
from novelty.models import ClaimVerdict, ScoreBreakdown, Submission
from novelty.store import KnownClaimStore
from novelty.text import jaccard


@dataclass
class NoveltyScorer:
    listing_text: str
    embedder: Embedder
    store: KnownClaimStore
    extractor: ClaimExtractor
    judge: SamePointJudge
    settings: Settings

    def __post_init__(self) -> None:
        self._listing_vec = self.embedder.embed([self.listing_text])

    # ------------------------------------------------------------------
    def score(self, sub: Submission) -> ScoreBreakdown:
        s = self.settings

        # [1] near-copy
        dup_id, dup_sim = self.nearest_copy(sub)
        if dup_id is not None and dup_sim >= s.duplicate_jaccard:
            return ScoreBreakdown.zero(
                sub, self.extractor.name, duplicate=True, duplicate_of=dup_id, duplicate_similarity=dup_sim
            )

        # [2] claims, each with the extractor's on-topic verdict
        extracted = self.extractor.extract(sub.headline, sub.body)
        if not extracted:
            return ScoreBreakdown.zero(sub, self.extractor.name, duplicate_of=dup_id, duplicate_similarity=dup_sim)
        texts = [c.text for c in extracted]
        vecs = self.embedder.embed(texts)

        # [3] relevance
        listing_sims = scoring.listing_similarity(vecs, self._listing_vec)
        relevance = scoring.relevance([c.on_topic for c in extracted])
        gate = scoring.gate(relevance, s)

        # [4] novelty
        verdicts: list[ClaimVerdict] = []
        all_candidates = self.store.candidates(vecs, k=s.judge_candidates)
        for claim, sim_to_listing, candidates in zip(extracted, listing_sims, all_candidates, strict=True):
            status, decided_by, match, match_sim = scoring.classify_claim(
                claim.text, claim.on_topic, candidates, self.judge, s
            )
            verdicts.append(
                ClaimVerdict(
                    claim=claim.text,
                    on_topic=claim.on_topic,
                    relevance=float(sim_to_listing),
                    status=status,
                    decided_by=decided_by,
                    best_match=match.text if match else None,
                    best_match_source=match.source if match else None,
                    best_similarity=match_sim,
                )
            )
        statuses = [v.status for v in verdicts]
        n_new = statuses.count("new")
        novelty = scoring.novelty(statuses)
        substance = scoring.substance(n_new, s)
        final = scoring.final_score(gate, novelty, substance)

        return ScoreBreakdown(
            submission_id=sub.id,
            recommend=sub.recommend,
            duplicate=False,
            duplicate_of=dup_id,
            duplicate_similarity=dup_sim,
            relevance=relevance,
            gate=gate,
            novelty=novelty,
            substance=substance,
            final=final,
            per_claim=verdicts,
            extractor=self.extractor.name,
        )

    def ingest(self, sub: Submission, claims: list[str] | None = None) -> None:
        """Make a submission part of the known pool for everything scored after it.

        Without pre-authored claims, only the extractor's on-topic claims are added,
        so off-topic text never pollutes the pool.
        """
        sid = sub.id or f"sub{len(self.store.review_texts) + 1:04d}"
        self.store.add_review_text(sid, sub.full_text)
        if claims is None:
            claims = [c.text for c in self.extractor.extract(sub.headline, sub.body) if c.on_topic]
        self.store.add(claims, source=sid)

    def score_and_ingest(self, sub: Submission) -> ScoreBreakdown:
        """Production path: score, then (unless duplicate) add the on-topic claims to the pool."""
        result = self.score(sub)
        if not result.duplicate:
            self.ingest(sub, [v.claim for v in result.per_claim if v.on_topic])
        return result

    # ------------------------------------------------------------------
    def nearest_copy(self, sub: Submission) -> tuple[str | None, float]:
        """(review id, jaccard) of the most similar earlier review text, or (None, 0.0)."""
        text = sub.full_text
        if not text:
            return None, 0.0
        top_id, top = None, 0.0
        for rid, other in self.store.review_texts.items():
            j = jaccard(text, other)
            if j > top:
                top_id, top = rid, j
        return top_id, top


def build_default_scorer(settings: Settings | None = None, with_corpus: bool = True) -> NoveltyScorer:
    """Scorer over data/fixed_content.json, seeded with data/corpus.json using its pre-authored claims.

    The listing itself goes through the extractor, so the pool starts from atomic
    listing claims rather than compound sentences.
    """
    settings = settings or Settings()
    fixed = load_fixed_content()
    listing = fixed["text"]
    # The product name is neutralised before embedding so that "Boho is easy to use" and
    # "The tool is easy to use" sit together, and "Boho ..." claims do not cluster on the
    # name alone (runs/03-product-name-regression.md).
    embedder = ProductNeutralEmbedder(SentenceTransformerEmbedder(settings.embedding_model), fixed["product_name"])
    extractor, judge = build_llm(settings, listing)
    store = KnownClaimStore(embedder=embedder)
    store.add([c.text for c in extractor.extract(fixed["title"], listing) if c.on_topic], source="listing")
    scorer = NoveltyScorer(
        listing_text=listing, embedder=embedder, store=store, extractor=extractor, judge=judge, settings=settings
    )
    if with_corpus:
        for review in load_corpus():
            sub = Submission(
                id=review["id"], headline=review["headline"], body=review["body"], recommend=review["recommend"]
            )
            scorer.ingest(sub, claims=review["claims"])
    return scorer
