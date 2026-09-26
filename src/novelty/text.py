"""Plain-text utilities used by step [1] (near-copy) and to split the listing into known sentences."""

from __future__ import annotations

import re

_WORD_RE = re.compile(r"[a-z0-9$%]+")
_SENT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+|;\s+")
_FILLER_RE = re.compile(
    r"^(overall|honestly|also|but|and|plus|on another note|unrelated, but|on the plus side|minor, but|mostly happy, but)[,:]?\s+",
    re.IGNORECASE,
)


def tokens(text: str) -> set[str]:
    """Lower-cased word set; punctuation dropped, '$' and '%' kept."""
    return set(_WORD_RE.findall((text or "").lower()))


def jaccard(a: str, b: str) -> float:
    """Word-set Jaccard similarity in [0, 1]. Empty input -> 0."""
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def split_sentences(text: str, min_words: int = 3) -> list[str]:
    """Split on sentence punctuation, newlines and semicolons; drop leading filler and short fragments."""
    out: list[str] = []
    for raw in _SENT_SPLIT_RE.split(text or ""):
        s = _FILLER_RE.sub("", raw.strip()).strip(" \t\"'")
        if len(s.split()) >= min_words:
            out.append(s)
    return out


def neutralize_product_name(text: str, product_name: str) -> str:
    """Replace the product name with "the product" so embeddings compare content, not the name.

    "Boho's UI is clean" -> "the product's UI is clean"; "Boho is cheap" -> "the product is cheap".
    Case-insensitive, whole word only. Used only for the text that is embedded; the
    original claim text is what the breakdown shows.
    """
    if not product_name:
        return text
    pattern = re.compile(rf"\b{re.escape(product_name)}('s)?\b", re.IGNORECASE)
    return pattern.sub(lambda m: "the product" + (m.group(1) or ""), text)
