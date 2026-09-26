# Run 02 — relevance moved to the extractor, atomic listing claims, top-3 judge (2026-09-26 ~13:30 IST)

Changes since run 01: see `WORKLOG.md` (13:15-13:45 entry) and SPEC sections 3-5.

**Result: 18/21 in band** (run 01: 12/21).

| Config | Value |
|---|---|
| duplicate_jaccard | 0.70 |
| relevance | share of extractor `on_topic` claims |
| gate_low / gate_high | 0.25 / 0.75 |
| known_low / known_high | 0.50 / 0.80 |
| judge_candidates | 3 |
| substance_claims (K) | 2 |
| Listing known claims | 14 atomic claims from the extractor |

## Summary table

```
id   category               final  gate   nov   sub  band
g01  duplicate              0.000  0.00  0.00  0.00  {'final_max': 0.0, 'duplicate': True}
g02  duplicate              0.000  0.00  0.00  0.00  {'final_max': 0.0, 'duplicate': True}
g03  rehash                 0.125  1.00  0.25  0.50  {'final_max': 0.25}
g04  rehash                 0.000  1.00  0.00  0.00  {'final_max': 0.25}
g05  rehash                 0.500  1.00  0.50  1.00  {'final_max': 0.25}  <-- OUT OF BAND
g06  rehash                 0.000  1.00  0.00  0.00  {'final_max': 0.25}
g07  listing_restatement    0.000  1.00  0.00  0.00  {'final_max': 0.25}
g08  novel_relevant         1.000  1.00  1.00  1.00  {'final_min': 0.6}
g09  novel_relevant         1.000  1.00  1.00  1.00  {'final_min': 0.6}
g10  novel_relevant         1.000  1.00  1.00  1.00  {'final_min': 0.6}
g11  novel_relevant         1.000  1.00  1.00  1.00  {'final_min': 0.6}
g12  mixed                  0.400  1.00  0.40  1.00  {'final_min': 0.2, 'final_max': 0.8}
g13  mixed                  0.600  1.00  0.60  1.00  {'final_min': 0.2, 'final_max': 0.8}
g14  novel_irrelevant       0.000  0.00  0.00  0.00  {'final_max': 0.1}
g15  novel_irrelevant       0.000  0.00  0.00  0.00  {'final_max': 0.1}
g16  novel_irrelevant       0.000  0.00  0.00  0.00  {'final_max': 0.1}
g17  novel_irrelevant       0.000  0.00  0.00  0.00  {'final_max': 0.1}
g18  padded_irrelevant      0.398  0.93  0.43  1.00  {'final_max': 0.25}  <-- OUT OF BAND
g19  padded_irrelevant      0.278  0.83  0.33  1.00  {'final_max': 0.25}  <-- OUT OF BAND
g20  trivial                0.000  0.00  0.00  0.00  {'final_max': 0.0}
g21  trivial                0.000  0.00  0.00  0.00  {'final_max': 0.0}

18/21 in band  (extractor=gemini)
```

## What the redesign fixed

- Relevance: every claim in g14-g17 is `off`; every claim in g03-g13 is `on`. The
  extractor's on-topic flag separates cleanly where cosine could not.
- Restatement (g07): 14/14 claims matched against `[listing]`, 9 by cosine alone
  (0.84-1.00), 5 by the judge. Final 0.0.
- Novel relevant (g08-g11): all 1.0. Novel claims sit at cosine 0.27-0.62 from
  anything known and the judge correctly says "different" for the borderline ones
  (e.g. "Gantt dependencies break across month boundaries" vs "The Gantt timeline is
  simpler than MS Project", 0.62).
- Top-3 candidates: "Nobody on the team needed training" now finds r007
  "No training is needed to use the boards" as its best match.

## Remaining failures

### A. The judge is too strict about generalisations (g05, g19)

| B (new) | A (known) | cos | judge |
|---|---|---|---|
| "The mobile app crashes constantly." | "The mobile app is slow and crashes on large boards" (r003) | 0.77 | different |
| "The mobile app is missing most features." | "The mobile app lacks the Gantt view" (r013) | 0.65 | different |

Read literally, "adds no information after the first" lets the judge treat a vaguer
restatement as new. A vaguer version of a known complaint is not information. The
prompt needs to say so: paraphrase, generalisation, or the same complaint about the
same feature = same; a new specific fact, condition, number, or opposite polarity =
different.

### B. Clear paraphrases fall below LOW and never reach the judge (g03, g18)

| B (new) | A (known) | cos | decided |
|---|---|---|---|
| "The product is super easy to use." | "The tool is simple and fast" (r027) | 0.50 | cosine_low -> new |
| "Nobody on the team needed training to use the software." | "No training is needed to use the boards" (r007) | 0.49 | cosine_low -> new |
| "Nobody on the reviewer's team needed training to use the product." | same | 0.45 | cosine_low -> new |

MiniLM puts obvious paraphrases at 0.45-0.50 when the wording differs ("the product"
vs "Boho", "software" vs "boards"). LOW = 0.50 is too high; 0.40 sends these to the
judge. Cost: more judge calls, all cached.

Related: the extractor wrote "Boho is super easy to use" for g03 but "The product is
super easy to use" for g18 (same sentence, different surrounding text). Against
"Boho is easy to use" those score 0.98 and 0.50. Asking the extractor to name the
product in every claim removes this source of variance.

### C. Padded pair (g18 vs g03)

g18 (0.398) > g03 (0.125) is caused by A and B above: three claims judged new in
g18 that are known in g03 or should be. Expected to resolve with the two fixes.
Note the extractor produced 5 on-topic claims for g18 and 4 for g03 from the same
two sentences; small extraction differences between a text and its padded twin are
inherent to LLM extraction and the pair test may need a small tolerance.

## Judge and extraction calls this run

19 extractions (re-requested under the `extract_v2` key) + 1 for the listing;
judge calls: ~35 (28 reused from run 01 where the pair was identical).
