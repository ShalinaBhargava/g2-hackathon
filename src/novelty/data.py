"""Loaders for the dataset files in data/."""

from __future__ import annotations

import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def _read(name: str, data_dir: Path = DATA_DIR) -> dict:
    return json.loads((data_dir / name).read_text(encoding="utf-8"))


def load_fixed_content(data_dir: Path = DATA_DIR) -> dict:
    """The listing: id, title, text, word_count."""
    return _read("fixed_content.json", data_dir)


def load_corpus(data_dir: Path = DATA_DIR) -> list[dict]:
    """Reviews in submission order, each with id/headline/body/recommend/claims."""
    return _read("corpus.json", data_dir)["reviews"]


def load_golden(data_dir: Path = DATA_DIR) -> tuple[dict, list[dict]]:
    """(bands, items) from golden.json."""
    d = _read("golden.json", data_dir)
    return d["bands"], d["items"]
