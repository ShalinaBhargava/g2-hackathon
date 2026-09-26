"""Command line entry points.

python -m novelty.cli score --headline "..." --body "..." --recommend yes
python -m novelty.cli golden [-v]     # score every golden item, check bands
python -m novelty.cli replay          # score the corpus in order, each against its predecessors
"""

from __future__ import annotations

import argparse
import json
import sys

from novelty.data import load_corpus, load_golden
from novelty.models import Submission
from novelty.scorer import build_default_scorer


def _score(args: argparse.Namespace) -> int:
    scorer = build_default_scorer()
    result = scorer.score(Submission(headline=args.headline, body=args.body, recommend=args.recommend))
    print(json.dumps(result.model_dump(), indent=2) if args.json else result.explain())
    return 0


def _golden(args: argparse.Namespace) -> int:
    scorer = build_default_scorer()
    bands, items = load_golden()
    failures, gaps = 0, 0
    print(f"{'id':<5}{'category':<21}{'final':>7}{'gate':>6}{'nov':>6}{'sub':>6}  band")
    for it in items:
        r = scorer.score(Submission(id=it["id"], headline=it["headline"], body=it["body"], recommend=it["recommend"]))
        band = bands[it["category"]]
        ok = band.get("final_min", 0.0) - 1e-9 <= r.final <= band.get("final_max", 1.0) + 1e-9
        if "duplicate" in band:
            ok = ok and r.duplicate == band["duplicate"]
        if ok:
            flag = ""
        elif it.get("known_gap"):
            gaps += 1
            flag = "  <-- KNOWN GAP (expected failure)"
        else:
            failures += 1
            flag = "  <-- OUT OF BAND"
        print(
            f"{it['id']:<5}{it['category']:<21}{r.final:>7.3f}{r.gate:>6.2f}{r.novelty:>6.2f}{r.substance:>6.2f}  {band}{flag}"
        )
        if args.verbose:
            print("      " + r.explain().replace("\n", "\n      "))
    gap_note = f", {gaps} known gap{'s' if gaps != 1 else ''}" if gaps else ""
    print(f"\n{len(items) - failures - gaps}/{len(items)} in band{gap_note}  (extractor={scorer.extractor.name})")
    return 1 if failures else 0


def _replay(args: argparse.Namespace) -> int:
    scorer = build_default_scorer(with_corpus=False)
    print(f"{'id':<6}{'final':>7}{'gate':>6}{'nov':>6}  headline")
    for review in load_corpus():
        sub = Submission(
            id=review["id"], headline=review["headline"], body=review["body"], recommend=review["recommend"]
        )
        r = scorer.score(sub)
        scorer.ingest(sub, claims=review["claims"])
        print(f"{review['id']:<6}{r.final:>7.3f}{r.gate:>6.2f}{r.novelty:>6.2f}  {review['headline']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="novelty")
    sp = p.add_subparsers(dest="cmd", required=True)

    s = sp.add_parser("score", help="score one submission against the corpus")
    s.add_argument("--headline", default="")
    s.add_argument("--body", required=True)
    s.add_argument("--recommend", choices=["yes", "no", "mixed"], default="mixed")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=_score)

    g = sp.add_parser("golden", help="score the golden set and check bands")
    g.add_argument("-v", "--verbose", action="store_true")
    g.set_defaults(fn=_golden)

    sp.add_parser("replay", help="score the corpus in submission order").set_defaults(fn=_replay)

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
