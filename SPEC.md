# SPEC: Novelty Scoring for Product Reviews

## 1. Problem

A review platform shows one fixed piece of content (a product listing), and users
submit reviews of it. Most reviews repeat each other. The goal is to **reward a
review for the new, relevant information it adds**, with a score in [0.0, 1.0], and
to **never reward novel but irrelevant content**.

## 2. Content shape

**Fixed content (≤100 words):** a listing blurb for a fictional SaaS product,
*"Boho: project management for small agencies. Boards, timelines, client
portals, time tracking, Slack/Google/Microsoft eams integrations. From $12/user/month."*

**Submission, with 3 user-provided properties:**

| Field | Type | Role in scoring |
|---|---|---|
| `headline` | str | text, extracted for claims with the body |
| `body` | str | main source of claims |
| `recommend` | enum: `yes` / `no` / `mixed` | **not** a novelty signal; shown in the breakdown only |


## 3. Pipeline

```
review->[1] near-copy?  Jaccard ≥ threshold
        -> yes reward: 0.0
        -> no:
            [2] extract claims (Gemini, JSON, cached)
            [3] relevance = mean cos(claim, listing) ─► gate()
            [4] per claim, best cos vs known claims:             
                       ≥ HIGH → already said                             
                       < LOW  → new                                
                    between → Gemini judge "same point?" (cached)     
                    novelty = share of claims that are new 
            final = gate*novelty
        
```

- **Known claims** = claims from **earlier** reviews + sentences of the listing itself.
- **Output** = `ScoreBreakdown(duplicate, relevance, gate, novelty, final, per_claim)`,
  so every score explains itself.

