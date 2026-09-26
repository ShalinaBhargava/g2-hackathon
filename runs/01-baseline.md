# Run 01 — baseline (2026-09-26 ~13:00 IST)

First end-to-end run of the golden set with the initial thresholds from SPEC.md
section 4. Extractor and judge: gemini-3.6-flash. Embedder: all-MiniLM-L6-v2.
Gemini cache after this run: 47 responses (19 extractions, 28 judge calls).

**Result: 12/21 in band.**

| Config | Value |
|---|---|
| duplicate_jaccard | 0.70 |
| claim_relevance_min | 0.20 |
| gate_low / gate_high | 0.15 / 0.35 |
| known_low / known_high | 0.50 / 0.80 |
| substance_claims (K) | 2 |
| Listing known claims | sentence split of the listing (7 sentences) |
| Judge candidates | top-1 by cosine |

## Summary table

```
id   category               final  gate   nov   sub  band
g01  duplicate              0.000  0.00  0.00  0.00  {'final_max': 0.0, 'duplicate': True}
g02  duplicate              0.000  0.00  0.00  0.00  {'final_max': 0.0, 'duplicate': True}
g03  rehash                 0.400  1.00  0.40  1.00  {'final_max': 0.25}  <-- OUT OF BAND
g04  rehash                 0.800  1.00  0.80  1.00  {'final_max': 0.25}  <-- OUT OF BAND
g05  rehash                 0.000  0.00  0.00  0.00  {'final_max': 0.25}
g06  rehash                 0.000  0.12  0.00  0.00  {'final_max': 0.25}
g07  listing_restatement    0.688  1.00  0.69  1.00  {'final_max': 0.25}  <-- OUT OF BAND
g08  novel_relevant         0.243  0.36  0.67  1.00  {'final_min': 0.6}  <-- OUT OF BAND
g09  novel_relevant         0.165  0.33  0.50  1.00  {'final_min': 0.6}  <-- OUT OF BAND
g10  novel_relevant         0.000  0.00  0.00  0.00  {'final_min': 0.6}  <-- OUT OF BAND
g11  novel_relevant         1.000  1.00  1.00  1.00  {'final_min': 0.6}
g12  mixed                  0.833  1.00  0.83  1.00  {'final_min': 0.2, 'final_max': 0.8}  <-- OUT OF BAND
g13  mixed                  0.000  0.00  0.00  0.00  {'final_min': 0.2, 'final_max': 0.8}  <-- OUT OF BAND
g14  novel_irrelevant       0.000  0.00  0.00  0.00  {'final_max': 0.1}
g15  novel_irrelevant       0.000  0.00  0.00  0.00  {'final_max': 0.1}
g16  novel_irrelevant       0.000  0.00  0.00  0.00  {'final_max': 0.1}
g17  novel_irrelevant       0.000  0.00  0.00  0.00  {'final_max': 0.1}
g18  padded_irrelevant      0.273  0.82  0.33  1.00  {'final_max': 0.25}  <-- OUT OF BAND
g19  padded_irrelevant      0.000  0.00  0.00  0.00  {'final_max': 0.25}
g20  trivial                0.000  0.00  0.00  0.00  {'final_max': 0.0}
g21  trivial                0.000  0.00  0.00  0.00  {'final_max': 0.0}

12/21 in band  (extractor=gemini)
```

## What works

- Near-copy detection: both duplicates caught (Jaccard 1.00 and 0.91), zero Gemini calls.
- Novel-irrelevant: all four at 0.0. Relevance vs the listing is reliably below 0.2 for
  off-topic text (espresso, hiking, sourdough, stadium: per-claim cosines from -0.14 to 0.19).
- Trivial: both at 0.0.
- Judge behaviour where it was asked the right question: e.g. "Boho is super easy to use"
  vs "Boho is easy to use" (0.98) known by cosine; "Support took days to reply" vs
  "Support takes a long time to respond" (0.80) known by cosine.

## Failure 1: cosine-to-listing does not measure relevance to the product

Per-claim cosine against the full listing embedding rewards *sounding like the listing*
and punishes specific complaints and features the listing does not mention.

| Claim | cos(listing) | Truth |
|---|---|---|
| "Boho features Kanban boards." (g07) | 0.60 | restates listing |
| "Boho costs twelve dollars per user." (g04) | 0.71 | restates listing |
| "Support is email-only." (g13) | 0.14 | on topic |
| "The mobile app crashes constantly." (g05) | 0.06 | on topic |
| "Two-factor authentication is mandatory for workspace admins." (g10) | 0.09 | on topic, novel |
| "Dragging a task with dependencies ... creates a silent scheduling conflict." (g10) | 0.15 | on topic, novel |
| "The drip tray fills up quickly." (g14) | 0.16 | off topic |
| "Descaling takes ten minutes." (g14) | 0.06 | off topic |

On-topic complaints sit in 0.06-0.15 and off-topic sentences sit in -0.14-0.19. No
threshold separates them. g05, g06, g13 and g19 only "pass" because they were zeroed
by this bug, not because novelty was judged.

Also tried on paper: relevance = max(cos to listing, cos to nearest known claim). Novel
relevant claims are, by definition, far from everything (EU data residency 0.31,
audit log 0.33) while off-topic claims reach 0.36-0.37 by chance (stadium parking vs
"Team seats are reasonably priced"). Still no separation.

Conclusion: no config change fixes relevance. The relevance question ("is this about
the product in the listing?") needs the LLM, which already sees the listing during
extraction.

## Failure 2: known-claim matching misses the right candidate

- Listing sentences are compound ("Integrates with Slack, Google Workspace, and
  Microsoft Teams, with apps for web, iOS, and Android"). Atomic claims like
  "Boho integrates with Slack" match them poorly (best match was a corpus claim at 0.67,
  judged new). Same for "$12 per user per month" and "14-day trial". The listing must
  be turned into atomic claims the same way reviews are.
- Only the top-1 cosine candidate is judged. "Nobody on the team needed training"
  (g03) was compared against r040 "Boho works well for small teams" (0.61) and judged
  new, while r007 "No training is needed to use the boards" existed in the pool.
  "The Boho interface is clean" (g12) was compared against "Boho is easy to use" while
  r001 "The interface is clean and easy to learn" existed.
- Hand-authored corpus claims dropped specifics the reviews contain (r002 says "$12 a
  seat" but its claim says "affordable"). Atomic listing claims cover this case.

## Failure 3: minor

- `substance` is 1.0 on every non-zero item (K=2 is easy to hit); it is not
  discriminating anything yet. Leave as is.
- Judge calls: 28 for 21 items. Acceptable, all cached.

## Verbose output (verbatim)

See `01-baseline.verbose.txt`.
