# SPEC: Novelty Scoring for Product Reviews

## 1. Problem

A review platform shows one fixed piece of content (a product listing), and users
submit reviews of it. Most reviews repeat each other. The goal is to **reward a
review for the new, relevant information it adds**, with a score in [0.0, 1.0], and
to **never reward novel but irrelevant content**.

Non-goals: judging writing quality, sentiment, or whether a claim is *true*.

## 2. Content shape

**Fixed content (97 words, `data/fixed_content.json`):**

> Boho is project management built for small agencies. Plan work on Kanban boards
> and Gantt timelines, share progress through branded client portals, and log hours
> with built-in time tracking. Assign tasks, set due dates and milestones, attach
> files, and keep comments next to the work. Clients get free logins to review and
> approve deliverables without buying a seat. Weekly timesheets roll up
> automatically for billing. Integrates with Slack, Google Workspace, and Microsoft
> Teams, with apps for web, iOS, and Android. Plans start at $12 per user per
> month, with a 14-day free trial and no credit card.

**Submission, with 3 user-provided properties:**

| Field | Type | Role in scoring |
|---|---|---|
| `headline` | str | extracted for claims together with the body |
| `body` | str | main source of claims |
| `recommend` | enum: `yes` / `no` / `mixed` | **not** a novelty signal; echoed in the breakdown only |

`recommend` is deliberately excluded from the score: a verdict is not information,
and rewarding it would let "no" reviews game novelty on a corpus of "yes" reviews.

## 3. Pipeline

```
submission
  [1] near-copy?   Jaccard(word set of headline+body, any earlier review) >= 0.70
        yes -> final = 0.0, duplicate_of = <id>
        no  ->
  [2] extract claims          LLM (Gemini) sees the listing; returns {claim, on_topic}
                              per atomic claim; JSON output, disk-cached
  [3] per claim: on_topic == false -> status = irrelevant (can never be "new")
      relevance = share of claims with on_topic == true
      gate      = ramp(relevance, GATE_LO, GATE_HI)
      (cos(claim, listing) is recorded per claim as a diagnostic; it is not scored)
  [4] per on-topic claim:
        candidates = the K_JUDGE known claims with the highest cosine to this claim
        sim        = cosine of the nearest one
        sim >= HIGH        -> known   (decided by cosine alone)
        sim <  LOW         -> new     (nothing in the pool is close)
        LOW <= sim < HIGH  -> Gemini judge "same point?", asked for each candidate
                              with cosine >= LOW, nearest first (cached, required)
                                any candidate judged same -> known
                                none                      -> new
      novelty   = n_new / n_claims           (irrelevant claims dilute, never count)
      substance = min(1, n_new / K)          (one new fact should not equal four)
  final = gate * novelty * substance
```

- **Known claims** = claims from **earlier** reviews + the listing's own atomic claims,
  produced by the same extractor. Restating the listing is therefore not novel.
- **Order matters**: a review is scored against what existed when it was submitted.
  After scoring, its claims join the pool (unless it was a duplicate).
- **Output** = `ScoreBreakdown(duplicate, duplicate_of, relevance, gate, novelty,
  substance, final, per_claim[])`. Each `per_claim` entry carries the claim, its
  relevance, its status (`new` / `known` / `irrelevant`), how the status was decided
  (`relevance` / `cosine_high` / `cosine_low` / `judge`), and the nearest known
  claim (or the one the judge matched) with its source id. Every score explains itself.

### Why per-claim relevance and not only a review-level gate

A review-level gate alone can be gamed: three repeated relevant claims plus three
novel irrelevant sentences gets a mid gate and a high novelty share. Tagging each
claim as irrelevant before the novelty step means padding *lowers* the score
(`novelty` denominator grows, numerator does not). The golden set has explicit
padded/unpadded pairs to lock this in.

### Why a substance term

`novelty` is a share, so a one-line review with one unseen fact would score 1.0,
the same as a review with four. `substance = min(1, n_new / K)` with `K = 2`
saturates fast enough that a two-fact review is not penalized but a one-liner is
held to 0.5.

## 4. Thresholds (initial, to calibrate on the golden set)

| Name | Value | Where |
|---|---|---|
| `DUPLICATE_JACCARD` | 0.70 | step 1 |
| `GATE_LO` / `GATE_HI` | 0.25 / 0.75 | step 3, linear ramp on the on-topic share |
| `HIGH` / `LOW` | 0.80 / 0.40 | step 4, cosine bands (LOW was 0.50 until run 02: paraphrases landed at 0.45-0.50 and never reached the judge) |
| `K_JUDGE` | 3 | step 4, candidates the judge may be asked about |
| `K` | 2 | substance |

History: v1 used per-claim `cos(claim, listing)` with a 0.20 floor and a 0.15/0.35
ramp on the mean. `runs/01-baseline.md` shows why that cannot work: on-topic
complaints ("Support is email-only", 0.14) and off-topic sentences ("The drip tray
fills up quickly", 0.16) are indistinguishable by cosine to the listing, while
restating the listing scores highest of all. Relevance moved to the extractor.

Embedder: `sentence-transformers/all-MiniLM-L6-v2` (local, CPU, deterministic).
Cosine values above are for this model and must be re-checked if it changes.

## 5. Models

| Component | Implementation |
|---|---|
| Embeddings (step 4, plus diagnostics) | `all-MiniLM-L6-v2`, local CPU, deterministic. Embeds the listing, every known claim, and every claim of the submission under test. |
| Claim extraction + relevance (steps 2 and 3) | Gemini sees the listing and returns atomic claims each tagged `on_topic`. JSON schema, temperature 0, disk cache in `data/cache/`. The listing itself is run through it once to seed the pool. |
| Borderline judge (step 4) | Gemini "same point?" yes/no, cached. Only called when the cosine to the nearest known claim falls in [`LOW`, `HIGH`), on up to `K_JUDGE` candidates. |

A `GEMINI_API_KEY` is required. There is no offline fallback for the judge: a
cosine midpoint cannot tell a paraphrase from an opposite-polarity claim about
the same feature, and getting that distinction right is the whole point of the
borderline band. Determinism comes from the cache, not from a heuristic.

The corpus ships with **hand-authored claims** per review, so the known-claim pool
never depends on the extractor. Only the *submission under test* goes through it.

## 6. Data (`data/`)

| File | Contents |
|---|---|
| `fixed_content.json` | the 97-word listing |
| `corpus.json` | 50 synthetic reviews in submission order, each with `headline`, `body`, `recommend`, hand-authored `claims` (105 total), and documentation-only `themes` |
| `golden.json` | 24 labeled submissions in 9 categories with expected score bands (21 agent-written, 3 added afterwards; two flagged `known_gap` and run as strict expected failures) |

Corpus design: about ten themes recur (easy UI, client portal, time tracking,
Slack, pricing, mobile app, support, Gantt, reporting, onboarding) so the pool has
real redundancy, plus a dozen one-off points (calendar duplicates, no recurring
tasks, CSV-only export, API rate limit, no dark mode, ...) so "already said" hits
against a single earlier review are testable. A few corpus claims (free client
logins, automatic timesheets, no credit card, approving deliverables, milestones)
are also in the listing; those reviews should score low on replay.

Golden categories and bands:

| Category | Band | What it proves |
|---|---|---|
| `duplicate` (2) | final = 0, duplicate = true | near-copies earn nothing |
| `rehash` (4) | final <= 0.25 | paraphrasing common points earns little |
| `listing_restatement` (1) | final <= 0.25 | the listing itself is known |
| `novel_relevant` (4) | final >= 0.6 | unseen, on-topic facts are rewarded |
| `mixed` (2) | 0.2 <= final <= 0.8 | half-new reviews land in the middle |
| `novel_irrelevant` (4) | final <= 0.1 | novelty without relevance is not rewarded |
| `padded_irrelevant` (2) | final <= 0.25 and <= its unpadded twin | padding cannot help |
| `trivial` (2) | final = 0 | nothing to extract |

Novel-relevant items use facts absent from both the listing and the corpus on
purpose (workload view, retainer budgets, audit-log retention, Okta SSO tiering,
QuickBooks export, EU data residency, Gantt dependency bug, mandatory admin 2FA,
automation rules, baselines, offline sync). Do not add these topics to the listing
or corpus without re-labeling.

## 7. Success criteria

1. All 21 golden items land in their bands.
2. Ordering holds: min(novel_relevant) > max(rehash, listing_restatement, duplicate).
3. max(novel_irrelevant) < min(novel_relevant).
4. Every padded item scores <= its unpadded twin.
5. Every score is explainable from `per_claim` alone, with no hidden state.
6. Scoring one submission against the 50-review pool takes under 1 s with a warm cache.

## 8. Tests to write

- `test_text.py`: normalization, Jaccard, sentence splitting.
- `test_golden.py`: parametrized over `golden.json` bands, plus the three ordering
  properties above.
- `test_ordering.py`: replay the corpus in order; the same review scored at
  position 1 must outscore itself scored at position 50.

## 9. Open questions

- ~~Relevance against the full listing embedding vs. max over listing sentences.~~
  Resolved in run 02: neither works (see section 4 history and
  `runs/01-baseline.md`); relevance is now the extractor's per-claim verdict.
- Whether to bring `recommend` back as a tie-breaker (a "no" on a 95%-"yes"
  product is itself informative). Out of scope for v1.
