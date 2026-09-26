# Run 03 — judge prompt v2, LOW 0.40, "name the product" extraction rule (2026-09-26 ~13:40 IST)

**Result: 16/21 in band** (run 02: 18/21). Regression.

| Config | Value |
|---|---|
| known_low / known_high | 0.40 / 0.80 |
| judge prompt | v2 (generalisation = same; new specific/polarity = different) |
| extraction prompt | v3: "refer to the product by its name from the listing" |
| everything else | as run 02 |

## Summary table

```
g01  duplicate              0.000   ok
g02  duplicate              0.000   ok
g03  rehash                 0.500   OUT (0.125 in run 02)
g04  rehash                 0.125   ok
g05  rehash                 0.500   OUT (0.500 in run 02)
g06  rehash                 1.000   OUT (0.000 in run 02)
g07  listing_restatement    0.000   ok
g08  novel_relevant         1.000   ok
g09  novel_relevant         0.750   ok
g10  novel_relevant         1.000   ok
g11  novel_relevant         1.000   ok
g12  mixed                  0.800   ok (edge)
g13  mixed                  0.800   ok (edge)
g14-g17 novel_irrelevant    0.000   ok
g18  padded_irrelevant      0.278   OUT (0.398 in run 02)
g19  padded_irrelevant      0.278   OUT (0.278 in run 02)
g20-g21 trivial             0.000   ok
```

## Cause: the product name dominates the cosine

With every claim rewritten to start with "Boho", MiniLM's nearest neighbours are
decided by the shared token rather than the content. The top-3 candidates became the
listing's own "Boho allows users to ..." claims, and the corpus claims that carry the
actual match (most of which do not say "Boho") fell out of the candidate set:

| Query claim | Nearest under v3 | cos | Correct match (run 02) | cos then |
|---|---|---|---|---|
| "Boho customer support took days to reply." | [listing] "Boho allows users to set due dates and milestones." | 0.56 | r017 "Support takes a long time to respond" | 0.80 |
| "Boho support is slow." | r007 "Migration onto Boho is fast" | 0.72 | r017 | 0.76 |
| "No one on the reviewer's team needed training to use Boho." | r050 "Boho is easy to use" | 0.55 | r007 "No training is needed to use the boards" | 0.49 |
| "Boho's interface is clean." | r050 "Boho is easy to use" | 0.72 | r035 "The interface is fast and clean" | 0.86 |
| "Boho task updates show up in Slack right away." | r004 "Slack integration posts task updates to channels" | 0.69 | r021 "Slack updates arrive instantly" | 0.74 |

Even off-topic claims picked up the bias: "Boho is the best espresso machine under
$500" now sits at 0.68 from "Boho is inexpensive" (0.34 in run 02). Harmless there,
because the on-topic flag zeroes it, but it shows the token is doing the work.

## What did work

- Judge v2 gets the generalisation cases right when it sees the right pair:
  "Boho's mobile app crashes constantly" vs "crashes on large boards" -> same (was
  different under v1). Keep v2.
- LOW = 0.40 did send the 0.45-0.50 paraphrases to the judge. Keep.
- Listing atomic claims now match by cosine alone in 13/14 restatement cases.

## Fix for run 04

Revert the v3 extraction rule (cache key back to `extract_v2`, so run 02's
extractions are reused with no new calls). Instead, neutralise the product name in
the text that is embedded, on both the pool and the query side: "Boho" and "Boho's"
become "the product" / "the product's" before MiniLM sees them. Symmetric, applied
to listing claims, corpus claims and submission claims alike, and invisible in the
breakdown, which still shows the original claim text.
