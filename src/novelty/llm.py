"""Claim extraction [2] (with the per-claim relevance verdict [3]) and the borderline
"same point?" judge [4]. See SPEC.md section 5.

Both are Gemini (google-genai) calls with a JSON disk cache in data/cache/, so a
given (headline, body) or (claim, known claim) pair is only ever sent once.
"""

from __future__ import annotations

import hashlib
import json
import threading
from pathlib import Path
from typing import Protocol

from novelty.config import Settings
from novelty.models import ExtractedClaim


class ClaimExtractor(Protocol):
    name: str

    def extract(self, headline: str, body: str) -> list[ExtractedClaim]: ...


class SamePointJudge(Protocol):
    name: str

    def same_point(self, claim: str, known: str) -> bool: ...


_EXTRACT_PROMPT = """You extract atomic claims from a product review and decide, for each one,
whether it is about the product.

The review was submitted against this product listing:
<listing>
{listing}
</listing>

Return a JSON array of objects {{"claim": ..., "on_topic": ...}}.

claim rules:
- One idea per claim, written as a short, self-contained declarative sentence.
- Keep the reviewer's specifics (numbers, feature names, plan names, integrations).
- Drop greetings, filler, and pure sentiment with no content ("love it").
- Do NOT drop content that is off-topic; extract it as a claim and mark it.
- Return [] if there is nothing to extract.

on_topic rules:
- true if the claim is about this product or the experience of using it: its
  features, missing features, bugs, performance, pricing, plans, trial, support,
  integrations, apps, security, data handling, usability, onboarding, or how it
  compares to competing tools. Complaints and unlisted features count as on
  topic; the listing does not have to mention the feature.
- false if the claim is about something else entirely (another product, food,
  travel, sport, the weather, the reviewer's life) even if it is written in the
  same review.

Headline: {headline}
Body: {body}
"""

_JUDGE_PROMPT = """Two statements from reviews of the same product. Statement A is already
known. Does statement B add any information for a reader who already knows A?

Answer {{"same": true}} when B adds nothing: B is a paraphrase of A, a vaguer or
more general version of A, or the same complaint or praise about the same feature.
A vaguer restatement is not new information.
  A "The mobile app is slow and crashes on large boards"  B "The mobile app crashes constantly"  -> same: true
  A "Support takes a long time to respond"                 B "Support is slow"                    -> same: true

Answer {{"same": false}} when B contains a specific fact, feature, condition, number,
plan name, or opposite polarity that A does not.
  A "Slack updates arrive instantly"                       B "Slack updates arrive late"         -> same: false
  A "Dragging tasks on the timeline updates dates"         B "Dragging a task across a month boundary breaks its dependencies"  -> same: false
  A "Pricing is affordable"                                B "Contractors cost a full seat for the month"  -> same: false

Statement A (already known): {known}
Statement B (new submission): {claim}
"""

_EXTRACT_SCHEMA = {
    "type": "ARRAY",
    "items": {
        "type": "OBJECT",
        "properties": {"claim": {"type": "STRING"}, "on_topic": {"type": "BOOLEAN"}},
        "required": ["claim", "on_topic"],
    },
}
_JUDGE_SCHEMA = {"type": "OBJECT", "properties": {"same": {"type": "BOOLEAN"}}, "required": ["same"]}


class _DiskCache:
    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.Lock()
        self._data: dict[str, object] = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}

    def get(self, key: str):
        return self._data.get(key)

    def set(self, key: str, value) -> None:
        with self._lock:
            self._data[key] = value
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self._data, indent=1, ensure_ascii=False), encoding="utf-8")


def _key(*parts: str) -> str:
    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()


class GeminiClient:
    """Implements both ClaimExtractor and SamePointJudge."""

    name = "gemini"

    def __init__(self, settings: Settings, listing_text: str):
        from google import genai  # lazy

        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._model = settings.gemini_model
        self._listing = listing_text
        self._cache = _DiskCache(settings.cache_dir / "gemini.json")

    def _json(self, prompt: str, schema: dict):
        from google.genai import types

        resp = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=schema,
                temperature=0.0,
            ),
        )
        return json.loads(resp.text)

    def extract(self, headline: str, body: str) -> list[ExtractedClaim]:
        if not (headline.strip() or body.strip()):
            return []
        k = _key("extract_v2", self._model, self._listing, headline, body)
        cached = self._cache.get(k)
        if cached is None:
            prompt = _EXTRACT_PROMPT.format(listing=self._listing, headline=headline, body=body)
            raw = self._json(prompt, _EXTRACT_SCHEMA)
            cached = [
                {"text": item["claim"].strip(), "on_topic": bool(item["on_topic"])}
                for item in raw
                if isinstance(item, dict) and isinstance(item.get("claim"), str) and item["claim"].strip()
            ]
            self._cache.set(k, cached)
        return [ExtractedClaim(**c) for c in cached]

    def same_point(self, claim: str, known: str) -> bool:
        k = _key("judge_v2", self._model, known, claim)
        if (cached := self._cache.get(k)) is not None:
            return bool(cached)
        same = bool(self._json(_JUDGE_PROMPT.format(known=known, claim=claim), _JUDGE_SCHEMA)["same"])
        self._cache.set(k, same)
        return same


def build_llm(settings: Settings, listing_text: str) -> tuple[ClaimExtractor, SamePointJudge]:
    """Gemini implements both roles. A key is required; there is no offline fallback."""
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is not set. Copy .env.example to .env and add your key.")
    client = GeminiClient(settings, listing_text)
    return client, client
