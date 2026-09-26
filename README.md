# Novelty scoring for product reviews

Hackathon entry for "Rewarding novelty in submissions" (theme: user generated
content). A review platform shows one fixed product listing and users submit
reviews of it. This project scores each new review in [0.0, 1.0] for the **new,
relevant information it adds** over the reviews before it, and never rewards
content that is novel but off-topic.

Solution write-up (design, rationale, results, limitations): [SOLUTION.md](SOLUTION.md).
Design spec, thresholds and success criteria: [SPEC.md](SPEC.md). Calibration runs: [runs/](runs/).
How the coding agent was used: [WORKLOG.md](WORKLOG.md).

## Layout

```
data/
  fixed_content.json   the 97-word Boho listing (the fixed content) and the product name
  corpus.json          50 synthetic reviews in submission order, with hand-authored claims
  golden.json          24 labeled submissions with expected score bands (two flagged known_gap)
  cache/gemini.json    every Gemini response, committed, so results replay with no new calls
runs/                  one file per calibration run: config, table, diagnosis
src/novelty/
  config.py            thresholds and runtime settings
  models.py            Submission, ExtractedClaim, ClaimVerdict, ScoreBreakdown
  text.py              tokenizing, Jaccard, sentence splitting, product-name neutralisation
  embed.py             MiniLM sentence embeddings + cosine, product-neutral wrapper
  llm.py               Gemini claim extractor (with on-topic verdict) and "same point?" judge, disk-cached
  store.py             known-claim pool: atomic listing claims + earlier reviews' claims, top-k lookup
  scoring.py           the scoring math (relevance, gate, classify, novelty, substance, final)
  scorer.py            pipeline orchestration, build_default_scorer()
  cli.py               score / golden / replay commands
  data.py              loaders for data/
tests/
  helpers.py           shared test helper
  test_text.py         text utilities
  test_scoring.py      unit contract for scoring.py, with a fake judge
  test_golden.py       golden bands, the ordering properties, the padded-pair property
  test_ordering.py     submission-order properties
```

## Setup

Python 3.11+ (developed on 3.13 and 3.14).

```
python -m pip install -e ".[dev]"
```

The first run downloads the MiniLM embedding model (~90 MB) once. On WSL, use
a virtualenv on the Linux filesystem and CPU-only torch:
`pip install torch --index-url https://download.pytorch.org/whl/cpu`.

Gemini is required for claim extraction, the on-topic verdict and the borderline
"same point?" judge. Copy `.env.example` to `.env` and set `GEMINI_API_KEY`.
Every response is cached in `data/cache/gemini.json`, which is committed, so the
golden set, the replay and the test suite make no new calls on a clean checkout.

## Run

```
# score one submission against the 50-review corpus
python -m novelty.cli score --headline "Workload view is great" \
    --body "The workload view shows over-allocation per person." --recommend yes

# score every golden item and check its band (22/24 in band, 2 known gaps)
python -m novelty.cli golden -v

# replay the corpus in submission order, each review against its predecessors
python -m novelty.cli replay

# tests: 50, of which 2 are strict expected failures (the known gaps)
python -m pytest

# lint and format
python -m ruff check src tests --fix && python -m ruff format src tests
```

Scorer-backed tests are skipped when `GEMINI_API_KEY` is not set; unit tests
always run.

## How a score is produced

```
[1] near-copy of an earlier review (Jaccard >= 0.70)            ->  0.0
[2] Gemini extracts atomic claims, each tagged on_topic (it sees the listing)
[3] relevance = share of on-topic claims;  gate = ramp(relevance, 0.25, 0.75)
[4] per on-topic claim, against the pool of listing claims + earlier reviews' claims:
      cosine to the nearest known claim >= 0.80  -> known
      cosine < 0.40                              -> new
      between: Gemini judge on up to 3 nearest  -> known if any is the same point
final = gate * (n_new / n_claims) * min(1, n_new / 2)
```

Every result is a `ScoreBreakdown` with a per-claim table: the claim, whether it
was on topic, its status, how that was decided, and the closest known claim with
its source review. `ScoreBreakdown.explain()` prints it.

## Results

| Golden set | 22/24 in band, 2 known gaps |
|---|---|
| Ordering | novel relevant min 1.000 > non-novel max 0.125; novel irrelevant max 0.000 |
| Padded pairs | both 0.000 <= their unpadded twins |
| Replay | mean 0.840 over the first 25 corpus reviews, 0.662 over the last 25 |

See [SOLUTION.md](SOLUTION.md) for the rationale, the run-by-run history, and
the limitations.
