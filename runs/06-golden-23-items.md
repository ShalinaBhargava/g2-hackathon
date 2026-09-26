# Run 06 — golden set with the two author-written items (2026-09-26 15:35 IST)

Same configuration as run 04. Two items added by the human after calibration:
g23 (relabelled `mixed` after a first label of `novel_irrelevant`) and g24
(`trivial`, flagged `known_gap`). No thresholds or prompts changed between run 04
and this run. Verbatim output: `06-golden-23-items.verbose.txt`.

**Result: 22/23 in band, 1 known gap.** All 21 run-04 items unchanged.

| id | category | final | band | |
|---|---|---|---|---|
| g23 | mixed | 0.600 | 0.2 to 0.8 | in band |
| g24 | trivial | 0.500 | 0.0 | known gap, expected failure |

## g23

Five claims: four on topic, one off ("wants to watch reels"). One known
(phone notifications, matched to r013 by the judge), three new: "micromanagement
increased", "the client keeps track of every story", "the client repeatedly asks
to add tasks". Novelty 0.6, gate 1.0, final 0.600. The scorer credits the
micromanagement angle as new information about the client portal, which no
corpus review makes.

## g24

One claim, "The Boho logo is cute", tagged on topic. Nearest known claim is r006
"The client portal can be branded with your own logo" at 0.51; the judge correctly
says it is a different point. One new claim: novelty 1.0, substance 0.5, final
0.500 against a band of 0.0. Recorded as a limitation (SOLUTION.md section 8).

## CLI change

`python -m novelty.cli golden` now reads the `known_gap` flag from `golden.json`,
prints such items as `KNOWN GAP (expected failure)` and excludes them from the
failure count, matching what the pytest suite does with `xfail(strict=True)`.
