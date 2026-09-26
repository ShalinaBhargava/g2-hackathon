# How the coding agent was used

Tool: Claude Code, model Claude Fable 5.1, one session on 2026-09-26 (10:00 to
15:00 IST). This is the disclosure required by the problem statement. The
calibration evidence it refers to is in `runs/`.

## Division of work

| Human | Agent |
|---|---|
| Wrote the one-page SPEC first: content shape, pipeline sketch, output shape | Read the problem statement PDF, refined the SPEC into sections with rationale, thresholds, data design, success criteria |
| Set the scope at each step ("just the data and setup", "give me a boilerplate, I will write the scoring logic") | Project scaffold, dependencies, linter, tests, CLI, data loaders |
| Wrote the first versions of the scoring functions; merged two of them | Authored the synthetic data: 97-word listing, 50-review corpus with 105 hand-written claims, 21 labelled golden items with bands |
| Removed the offline judge after asking why it existed | Implemented the plumbing: embeddings, Gemini extractor and judge with disk cache, known-claim store, orchestration |
| Questioned the LLM judge versus Jaccard; questioned splitting relevance into two functions | Diagnosed each calibration run from the per-claim breakdown and proposed the next change |
| Ran every calibration run, pasted the output back, approved or rejected each proposal | Drafted SOLUTION.md, README, this file |
| Wrote two golden items independently; called the first fix proposal for one of them overfitting | Recorded the runs, kept the known gap as an expected failure |

## How the agent was directed

The agent was steered by specification and by review rather than by open-ended
prompts:

1. **A written spec came first.** The human's SPEC.md defined the content shape,
   the four pipeline steps, and the self-explaining output. The agent's job was to
   refine it, not invent it. Its two additions (per-claim relevance tagging so
   padding cannot help; a substance term so one fact does not tie four) were
   proposed with reasons and accepted.
2. **Scope was narrowed explicitly.** When the agent began writing the pipeline
   unasked, the human stopped it. The agent removed the draft and delivered a
   skeleton with the scoring math left as documented stubs, which the human
   implemented.
3. **Design changes needed a go.** The one change that replaced something the
   human had authored (relevance moving from embedding distance to the
   extractor's verdict) was presented with the numbers that showed the original
   could not work, and made only after "ok do it".
4. **Every calibration step was reviewed by the human.** Four golden runs, each
   pasted back. Run 03 was a regression caused by an agent proposal (name the
   product in every claim); it was diagnosed from the breakdown and reverted.
5. **Pushback went both ways.** The human asked why an offline judge existed and
   had it removed; asked why not Jaccard for claim matching and accepted the
   argument for embeddings plus a judge; called a proposed test relabel
   overfitting, and the agent agreed for one item and disagreed, with reasons,
   for the other.

## The architectural requirements supplied, and the prompts

The requirements document given to the agent was the human's own SPEC.md as it
stood before the agent touched it: commit `25af738` in this repository. It fixed
the content shape, the four pipeline steps (near-copy, extract, relevance gate,
per-claim novelty with an LLM judge for the borderline band), and the requirement
that every score explain itself. Everything the agent built traces back to it.

The prompts that steered the session, verbatim, in order:

1. "this is a hackathon folder and the problem statement is in the pdf named as
   such, setup the project for me, I have created spec.md help me refine it and
   generate the data needed for this"
2. "i just need the data and setup"  (interrupting the agent mid-build)
3. "increase the size of the fixed content it is only 52 words make it about
   95-100 words, adjust the golden and corpus accordingly"
4. "give me a skeleton of the structure on the basis of the spec.md i will write
   the actual relevance novelty final novelty score. Also please keep a summary of
   this conversation in a worklog file, and create a readme document"
5. "add a linter and check the unknown resources"
6. "why are we going with judge offline?"  then  "no, lets get rid of it, where are
   we using minilm apart from this wouldnt creating embedding for known and new
   claims with it be better?"
7. "why are we not using jaccard for checking if the known and new claim is the
   same, will it not be a more deterministic approach than that of using a judge"
8. "why are claim_relevance and review_relevance two different functions"  then
   "ok then clean up the test_scoring ive merged the two functions"
9. "fix gate and claim_relevance for me"
10. "ok so 12/21 pass lets store this first run as the base and start fixing our
    configs"  then, after the agent's diagnosis and proposal,  "ok do it"
11. Runs 02, 03 and 04 pasted back with no instruction beyond the output; the
    agent diagnosed and proposed, the human ran the next command.
12. "i want to add a few test cases of my own and test them as well ill add them
    to corpus.json?"  then  "the case of g23 and g24 feels like overfitting to me"
    then  "do it"
13. "this should not be best it makes no sense"  (on a line of the SPEC)
14. "trim off the worklog as they mostly only want to know a summary of where and
    how ai was utilised and are not keen on a line by line log"

Not listed: routine requests for commands and a few environment fixes (a WSL
virtualenv, a wrong Gemini model name).

## Key decisions and who made them

| Decision | By | Basis |
|---|---|---|
| Claims, not text, as the unit of novelty | human (spec) | paraphrase and polarity |
| No offline fallback for the judge; determinism via committed cache | human | cosine midpoint cannot tell paraphrase from opposite polarity |
| Relevance = extractor's on-topic verdict, not cosine to listing | agent, approved | run 01 numbers: on-topic complaints 0.06-0.15, off-topic 0.16-0.19 |
| Judge sees top-3 candidates, not top-1 | agent, approved | correct match was often second or third |
| Product name neutralised before embedding | agent, approved | run 03 regression |
| g24 kept as a strict expected failure rather than relabelled | human's call, agent's mechanism | a real requirement the scorer fails |

## What the agent got wrong

- Started building the pipeline before being asked; removed on request.
- Proposed naming the product in every claim (run 03), which regressed 18/21 to
  16/21 by letting the shared token dominate nearest-neighbour search.
- Offered a "relabel to a new band" option for g24 that would have been fitting
  the test to the model; withdrawn when challenged.
- A test failure printed the settings object including the API key; fixed by
  excluding the key from the repr.

## Data provenance

All 50 corpus reviews, the listing text, and the 21 original golden items were
written by the agent during setup, with the human's constraints (listing length,
three user-provided fields, recurring themes plus one-off points, novel items
must not overlap the corpus). The human wrote g23 and g24.
