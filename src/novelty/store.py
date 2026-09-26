"""The pool of known claims: atomic listing claims plus claims from earlier reviews (SPEC.md section 3)."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from novelty.embed import Embedder, cosine_matrix


@dataclass
class KnownClaim:
    text: str
    source: str  # review id or "listing"


Candidate = tuple[KnownClaim, float]  # (known claim, cosine to the query claim)


@dataclass
class KnownClaimStore:
    embedder: Embedder
    claims: list[KnownClaim] = field(default_factory=list)
    _matrix: np.ndarray | None = field(default=None, repr=False)
    _review_texts: dict[str, str] = field(default_factory=dict, repr=False)

    def add(self, claims: list[str], source: str) -> None:
        new = [KnownClaim(text=c, source=source) for c in claims if c and c.strip()]
        if not new:
            return
        vecs = self.embedder.embed([c.text for c in new])
        self.claims.extend(new)
        self._matrix = vecs if self._matrix is None else np.vstack([self._matrix, vecs])

    def add_review_text(self, review_id: str, full_text: str) -> None:
        """Remember raw review text for near-copy detection."""
        self._review_texts[review_id] = full_text

    @property
    def review_texts(self) -> dict[str, str]:
        return self._review_texts

    def __len__(self) -> int:
        return len(self.claims)

    def candidates(self, claim_vectors: np.ndarray, k: int) -> list[list[Candidate]]:
        """For each query vector, the k closest known claims with their cosines, nearest first.

        Empty list for a query when the pool is empty.
        """
        n = claim_vectors.shape[0]
        if self._matrix is None or n == 0:
            return [[] for _ in range(n)]
        sims = cosine_matrix(claim_vectors, self._matrix)
        k = max(1, min(k, sims.shape[1]))
        out: list[list[Candidate]] = []
        for row in sims:
            top = np.argsort(-row)[:k]
            out.append([(self.claims[int(j)], float(row[j])) for j in top])
        return out
