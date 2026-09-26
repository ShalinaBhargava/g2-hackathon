"""
Every number that shapes a score lives here so the SPEC can cite it and the
calibration output can print it.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
CACHE_DIR = DATA_DIR / "cache"


@dataclass(frozen=True)
class Settings:
    # --- [1] near-copy detection --------------------------------------------
    duplicate_jaccard: float = 0.70

    # --- [3] relevance gate ---------------------------------------------------
    # Review relevance = share of claims the extractor marked on topic.
    gate_low: float = 0.25  # GATE_LO: ramp starts (1 in 4 claims on topic -> gate 0)
    gate_high: float = 0.75  # GATE_HI: ramp saturates at 1.0 (3 in 4 on topic -> gate 1)

    # --- [4] novelty against known claims ------------------------------------
    known_high: float = 0.80  # HIGH: cosine >= this -> known
    known_low: float = 0.40  # LOW:  cosine <  this -> new (0.50 missed paraphrases at 0.45-0.50, run 02)
    judge_candidates: int = 3  # K_JUDGE: how many nearest known claims the judge may be asked about
    substance_claims: int = 2  # K: substance = min(1, n_new / K)

    # --- models ----------------------------------------------------------------
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    gemini_model: str = field(default_factory=lambda: os.getenv("NOVELTY_GEMINI_MODEL", "gemini-3.6-flash"))
    gemini_api_key: str | None = field(default_factory=lambda: os.getenv("GEMINI_API_KEY") or None, repr=False)
    cache_dir: Path = CACHE_DIR
