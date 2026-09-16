---
name: shadow
description: Blind candidate-vs-production testing loop — runs a candidate model or prompt silently on the same real inputs as production, queues only disagreements, and a human grades them blind; promotion needs a full week's clear majority plus zero safety/gate misses. Never serves a real user or ships anywhere. Fires on "shadow test [X] against [Y]", "run the shadow loop", "test if [candidate] can replace [pinned model]".
---

**What it does:** Runs a candidate model or prompt silently alongside production, then has a human blind-grade only the cases where they disagree.
**When it fires:** "shadow test [X] against [Y]", "run the shadow loop", "test if [candidate] can replace [pinned model]".
**Config:** state file path — default `shadow/<target>-STATE.md`; `PRODUCTION_LOG`: where real production input/output pairs are read from; `CANDIDATE_CMD`: how the candidate is invoked; `GATES`: the applicable checks, each a command or checklist. All three are required, no defaults.

# /shadow — Blind Candidate-vs-Production Test Loop

For testing whether a cheaper or different model/prompt can safely replace one that's currently
pinned — without ever risking a real user seeing the candidate's output, and without trusting
anyone's gut feeling about which one is "obviously better." The candidate runs in the dark; only
disagreements surface, and they surface unlabeled.

**Usage:** `/shadow <production system/prompt> vs <candidate>` — e.g.
`/shadow "current writer prompt on model A" vs "the same brief on model B"`.

## Why this exists

Model pins in most projects are reliability calls made once and never re-tested. That may still
be correct. This skill is how you find out empirically instead of leaving it as an assumption:
shadow the candidate on the same real production inputs for a week, grade only what differs, and
let the evidence — not the pin's age — decide.

## State file

`shadow/<target>-STATE.md`:

```
## This week's disagreement queue (candidate never serves a real user)
YYYY-MM-DD | input <ref/id> | production output <ref> | candidate output <ref> | UNGRADED
YYYY-MM-DD | input <ref/id> | production output <ref> | candidate output <ref> | GRADED: candidate preferred (blind)

## Log (append-only, one line per week)
YYYY-MM-DD | no-op | no candidate ready this week
YYYY-MM-DD | EXTEND | 2 disagreements this week — too few to judge, extend the shadow week
YYYY-MM-DD | PROMOTE-FLAGGED | 9 disagreements, 7/9 candidate-preferred blind, 0 gate misses — flagged for review before deploy
YYYY-MM-DD | CANDIDATE-LOSES | 1 safety/gate miss this week — candidate loses the week regardless of preference tally
YYYY-MM-DD | BLOCK | gate "compliance-check" failed to execute on 4 outputs — week void, no verdict

## Gate runs (every candidate output, before the agree/disagree split)
YYYY-MM-DD | 14 outputs x 3 gates | 42 run, 42 passed, 0 misses
```

## Procedure

1. Read the state file. If no candidate is configured for this target this week, `no-op` — do
   not invent a candidate run to look busy.
2. Check the bindings before the loop starts: `PRODUCTION_LOG`, `CANDIDATE_CMD`, and a non-empty
   `GATES` set. Any one missing → `BLOCK`. Never run the loop on an unbound target.
3. Run the candidate SILENTLY via `CANDIDATE_CMD` on the real production inputs read from
   `PRODUCTION_LOG`. The candidate's output touches nothing live: no send, no publish, no deploy.
4. Run every gate in `GATES` on EVERY candidate output, before comparing anything. Log the count
   of gates run, passed, and missed. A gate that fails to execute, or that the run cannot prove
   ran, → `BLOCK`. Unrun gates are never counted as zero misses.
5. Compare candidate vs. production output per input:
   - **Agreement** (same substantive output, or differences that don't matter) → discard, not
     logged individually. Agreement is noise, not signal.
   - **Disagreement** → queue it, unlabeled which side is which.
6. At the end of the week (not before — a single day's sample is too small to judge):
   - **Any gate miss this week** → `CANDIDATE-LOSES`, even on a thin sample. A known miss vetoes
     `EXTEND` and every other outcome.
   - **Too few disagreements to judge** (use judgment — single digits on a low-volume system) →
     `EXTEND`, log it, run another week. Don't force a verdict on a thin sample.
   - Otherwise, a human grades each queued disagreement BLIND — two unlabeled outputs, they pick
     the better one. This is the only human step in the loop.
   - **Clear majority blind-preferred AND every gate run on every candidate output with zero
     misses** → `PROMOTE-FLAGGED`: flag for a human before any actual deploy/pin change. This
     skill recommends; it never swaps the pin itself. Zero misses counts only against a logged
     gate-run tally covering all outputs.
   - Otherwise → log the tally, continue shadowing next week.
7. No candidate ready some week → `no-op`, explicitly stated, never fabricated.

Nothing here ever writes to a live system. The only output of a "win" is a flagged recommendation
for a human to action manually.
