# Run 04 — product name neutralised for embedding (2026-09-26 ~13:50 IST)

**Result: 21/21 in band.**

| Config | Value |
|---|---|
| duplicate_jaccard | 0.70 |
| relevance | share of extractor `on_topic` claims |
| gate_low / gate_high | 0.25 / 0.75 |
| known_low / known_high | 0.40 / 0.80 |
| judge_candidates | 3 |
| substance_claims (K) | 2 |
| judge prompt | v2 (generalisation = same; new specific / polarity = different) |
| extraction prompt | v2 (claims + on_topic; no naming rule) |
| embedding text | product name replaced by "the product" on both sides |
| Listing known claims | atomic claims from the extractor (cached from run 02) |

## Summary table

```
id   category               final  gate   nov   sub  band
g01  duplicate              0.000  0.00  0.00  0.00  {'final_max': 0.0, 'duplicate': True}
g02  duplicate              0.000  0.00  0.00  0.00  {'final_max': 0.0, 'duplicate': True}
g03  rehash                 0.000  1.00  0.00  0.00  {'final_max': 0.25}
g04  rehash                 0.125  1.00  0.25  0.50  {'final_max': 0.25}
g05  rehash                 0.000  1.00  0.00  0.00  {'final_max': 0.25}
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
g18  padded_irrelevant      0.000  0.93  0.00  0.00  {'final_max': 0.25}
g19  padded_irrelevant      0.000  0.83  0.00  0.00  {'final_max': 0.25}
g20  trivial                0.000  0.00  0.00  0.00  {'final_max': 0.0}
g21  trivial                0.000  0.00  0.00  0.00  {'final_max': 0.0}

21/21 in band  (extractor=gemini)
```

## Progression

| Run | Change | In band |
|---|---|---|
| 01 | initial thresholds, cosine-to-listing relevance | 12/21 |
| 02 | extractor on-topic flag, atomic listing claims, top-3 judge | 18/21 |
| 03 | judge v2, LOW 0.40, "name the product" extraction rule | 16/21 |
| 04 | naming rule reverted, product name neutralised for embedding | 21/21 |

## Ordering properties (SPEC section 7)

- min(novel_relevant) = 1.000 > max(rehash, restatement, duplicate) = 0.125
- max(novel_irrelevant) = 0.000 < min(novel_relevant) = 1.000
- g18 (0.000) <= g03 (0.000); g19 (0.000) <= g05 (0.000)

## What the neutraliser did

With "Boho" mapped to "the product" before embedding, the nearest neighbours are
decided by content again and the matches are the ones a human would pick:

| Query claim | Match | cos |
|---|---|---|
| "Nobody on the team needed training to use the software." | r007 "No training is needed to use the boards" | 0.49 -> judge: same |
| "Customer support took days to reply." | r034 "Support response time is around two days" | 0.72 -> judge: same |
| "The interface is clean." | r035 "The interface is fast and clean" | 0.86 -> cosine |
| "All task updates show up in Slack right away." | r021 "Slack updates arrive instantly" | 0.74 -> judge: same |
| "Boho is super easy to use." | r050 "Boho is easy to use" | 0.93 -> cosine |

## Notes for the write-up

- g04 is the only rehash above 0.0: "Boho is very affordable for a small shop" was
  judged different from "Boho is inexpensive" (0.74). Debatable, and it only reaches
  0.125 because `substance` halves a single new claim. Acceptable.
- g12 and g13 sit at 0.40 and 0.60: exactly the "half repeated, half new" shape the
  mixed category was written for.
- The two novel-irrelevant reviews that mention a price or "the product" (espresso,
  g14) are still zeroed by the on-topic flag, not by cosine.
- Decisions this run, 84 claims: 19 flagged off-topic by the extractor, 14 known by
  cosine alone (>= 0.80), 12 new by cosine alone (< 0.40), 39 sent to the judge.
  Every judge answer is cached in `data/cache/gemini.json` (284 entries after run 04).
