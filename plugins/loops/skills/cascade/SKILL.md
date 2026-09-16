---
name: cascade
description: Goal-cascade multi-agent loop — one premium seat authors the top goal and every subagent's brief, a Workflow script orchestrates workers in isolated worktrees, a cross-family reviewer validates and audits, and acceptance criteria run on a merged tree rather than in the main conversation window. Findings are adjudicated by a premium judge and routed back to the worker that caused them. USER-INVOKED — fires on "/cascade", "cascade this", "run the goal cascade", "spawn goals for subagents".
---

This skill uses Claude Code's Workflow script API — `agent()`, `pipeline()`, `phase()`, and `isolation: 'worktree'`. That API is available on paid plans, and on Pro it needs the "Dynamic workflows" toggle in `/config`. It does not run on Codex CLI.

**What it does:** Cascades one authored goal down into verbatim worker briefs with disjoint write scopes, runs the workers in isolated worktrees, then cascades adjudicated findings back up to whichever worker or planner caused them.
**When it fires:** "/cascade", "cascade this", "run the goal cascade", "spawn goals for subagents". Not for anything mechanical or single-seat.
**Config:** `PREMIUM_MODEL` — the model that plans and judges (default: the current session's model). `REVIEWER_CMD` — the cross-family validator/auditor command (default: unset). `REVIEWER_TIMEOUT` — seconds (default: 300).

# /cascade — goal cascade with attributed fix routing

Goals cascade DOWN from one premium seat; fixes cascade back UP to the owner that caused them.

## Config — the swappable pointers (edit this block, nothing else)

- **`PREMIUM_MODEL`** — the model that plans and judges. Defaults to the current session's model. It
  fires twice per pass, PLANNER once and JUDGE once. Prefer a pinned full model ID over a bare tier
  alias, so a new release never silently swaps the seat.
- **`REVIEWER_CMD`** — the cross-family validator and auditor command. Contract: it reads the review
  payload on **stdin**. Its first line is `PASS` or `BLOCK`, applying to the work under review. Each
  later line is one finding, formatted `<severity> | <owner or n/a> | <one-line finding>`, where the
  owner is a worker id or `PLANNER`. A non-zero exit, empty stdout, or a first line that is neither
  `PASS` nor `BLOCK` means no review happened — never a pass. Left unset, validators and the auditor
  are SKIPPED and every report says so in capitals. A native fresh-subagent review counts only when
  `REVIEWER_CMD` is unset AND the skill documents that fallback; wrap and cascade do not, they SKIP.
- **`REVIEWER_TIMEOUT`** — seconds before a reviewer call is abandoned. Default `300`. The host
  agent's own Bash timeout must be at least `REVIEWER_TIMEOUT` plus 60 seconds.

Absence of review is never a pass.

`model:` accepts tier aliases AND full pinned model IDs. `REVIEWER_CMD` is NOT a model alias: passing
a command path as `model:` kills the agent with an invalid-model error and silently costs you the
whole review. Always spawn the reviewer as a subagent running `REVIEWER_CMD` on a cheap tier, whose
brief makes it shell out and relay the verdict verbatim — the host never substitutes its own
judgment, because a same-lab opinion wearing a decorrelated label is the thing this loop is built to
prevent. Every reviewer verdict always carries the literal command line it ran and the first bytes of
raw tool output — a self-reported seat label is not evidence the tool ran, and the run journal does
not record shell invocations. Never hardcode model names; rosters rot in both directions.

## Why this shape works (preserve when editing)

- **One author for all goals.** The premium seat writes the top goal and every worker brief in its
  own words. The briefs ARE the plan; never let a cheaper seat expand a summary of them.
- **The orchestrator is code.** Dispatch, collect, and route-fix-to-owner are routing, so a script
  does them — no context, no hallucination. Judgment it cannot do is escalated, never guessed.
- **Validators stay small; the auditor goes wide.** One validator sees one worker. The auditor sees
  raw output from all of them, because a wrong assumption shared by two workers is invisible to
  every small-context seat and is the defect class this loop would otherwise ship.
- **Acceptance is criteria green on merged code.** Per-worktree green proves nothing.

## When NOT to use

- A single point decision, one review, or no loop → spawn one agent directly.
- Anything mechanical (rename, lookup, format, run a script) → just do it on a cheap tier.

## Procedure

**0. Pin the target (main window, no reading).** Restate the raw ask and the target path. Delegate
repo-scale reading to a cheap seat returning `path:line`-anchored facts. When a compressed claim
will anchor the goal, always spot-check its pointer before it reaches PREMIUM_MODEL.

**1. PLANNER (spawned on PREMIUM_MODEL, `effort: high`).** Never plan in the main window:

```
goal        — one testable sentence; met/not-met must be decidable
criteria[]  — falsifiable checks, runnable against a merged tree
workers[]   — {id, brief, tier, writes:bool, paths[]}
              brief is verbatim-to-the-worker, written by YOU, not a summary
              paths[] declares write scope; PLANNER must keep scopes DISJOINT
```

The script asserts `paths[]` are disjoint before dispatch — overlapping writers mean merge
conflicts resolved by nobody. Veto a runaway fan-out from the main window on `workers.length`.
If the pack is missing something, PLANNER returns NEED and never goes reading on its own.

**Disjoint paths are necessary, never sufficient.** Two workers can own separate files and still be
coupled through a contract — a call signature, a documented precondition, a shared scope
assumption. That seam is invisible to both small-context validators, and each worker looks
internally correct while the pair is broken. So PLANNER always names every contract that would
cross a worker boundary and then either puts both sides inside ONE worker, or gives the contract a
named owner who tests it end to end. Cleaving a surface at its riskiest seam because that made the
file scopes trivially disjoint is the recorded failure mode, not a clean decomposition.

Criteria must be **reachable and honest**: scoped to files this pass actually owns (never a
directory carrying pre-existing debt), graded as no-worse-than-baseline where the goal says so
rather than against a literal zero, type-aware where they assert a type, and any check needing a
capability no agent has — a launch, a screenshot, a human eye — is marked owner-graded up front,
never left to fail as though the code were at fault. A test count is not coverage: require at least
one criterion that pins the seam between workers, or green means nothing.

Three criteria classes are MANDATORY:
- **Render-proof (any UI surface).** At least one machine criterion asserts the surface draws
  non-empty against realistic fixture data. Structural greps cannot catch a view that renders blank.
- **Capability parity (any replacement of an existing thing).** Enumerate the baseline's
  user-visible capabilities before briefs are written; every one defaults KEEP — DROP only by an
  explicit owner ruling in the goal pack, and an unruled DROP is a PLANNER-owned defect. A
  criterion checks every KEEP survives.
- **Coupling, not existence.** "X follows/derives-from Y" is proven by a test pinning the data
  path, never by X and Y merely existing.

**2. Workers, then per-worker validation.** One Workflow per pass; the script is the orchestrator:

```js
const results = await pipeline(
  workers,
  w => agent(w.brief, {label: w.id, phase: 'Work', schema: WORK,
                       isolation: w.writes ? 'worktree' : undefined}),
  (out, w) => out.status === 'BLOCKED' ? out
    : agent(validateHostPrompt(w, out), {label: `validate:${w.id}`, phase: 'Validate',
                                     model: 'haiku', schema: VERDICT})
        // host agent: shells out to REVIEWER_CMD, relays its verdict verbatim
        // (never `model: REVIEWER_CMD` — a command path is not a model; see Config block)
        .then(v => ({w, out, v}))
)
```

`WORK` carries `{status: DONE|BLOCKED, question?, ...}`. A worker that hits an ambiguity its brief
never covered always returns BLOCKED with a question, and the script routes it to PLANNER — it
never guesses, because its validator holds the same incomplete brief and would pass the guess.

**Any stage whose result is read by field MUST pass `schema:`** — without it `agent()` returns raw
text, every field read is `undefined`, and the downstream filter quietly yields an empty list. And
**never let a filter empty a stage in silence**: assert the surviving count against the expected one
and throw. The recorded failure is a full pass whose workers all succeeded on disk while the
integrator was handed an empty list and cheerfully graded the untouched base as though it were the
result. A loud crash costs one minute; a silent empty list costs the whole pass and looks like a
verdict.

**Before launching, always confirm the shell's working directory is inside the target repository**
(`git rev-parse --is-inside-work-tree`). Worktree isolation needs a git repo at the cwd, and the cwd
drifts across a long session — the recorded failure is a pass that died in 35ms because the shell
had wandered to a non-repo home directory.

Worktrees are cut from the repo's current HEAD, **not** from any base you name in a prompt. When a
pass builds on earlier work, the base is established by an explicit hard reset inside the worker's
own worktree and then **verified by the integrator** before its diff is applied — a diff computed
against the wrong base is never applied on trust.

**3. Integrate and run criteria (every pass, before any judging).** One cheap agent merges the
worker diffs into a single integration worktree and runs `criteria[]` there. A merge conflict is a
finding owned by whichever worker breached its `paths[]`. Criteria results are facts the judge and
auditor both receive — this merged run is also what catches cross-worker breakage, so untouched
workers need no re-validation.

**4. AUDITOR (a subagent running REVIEWER_CMD).** Always split the audit — one bounded call per
contract or per small batch, never one giant call carrying every raw output at once. A single
whole-pass audit is both a single point of failure and the shape that times out: the recorded
failure is a pass whose audit died at a 900-second ceiling, took its fallback down with it at 480,
and left every contract unchecked. Reasoning burn scales with payload, so bound the ask and keep a
named fallback seat. Each call receives the **raw** worker outputs in its scope and the criteria
results, refutes by default, and returns findings in the reviewer contract's line format,
`<severity> | <owner> | <finding>`, where the owner is a worker id **or `PLANNER`**. A defect in the goal or a brief is the planner's,
and forcing it onto an innocent worker burns re-fires on a scapegoat.

**5. JUDGE (spawned on PREMIUM_MODEL, LAST in the pass).** The judge runs after the audit, never
before — it adjudicates the auditor's findings too, and a judge that ran first could not. Receives
worker summaries, validator verdicts, criteria results, the audit findings, and one verdict per
contract. Confirms each worker met *its own* brief, scores against the top goal, and assigns a
stable `key` to every finding — the judge is the persistent seat, so keys stay comparable across
passes where a rotating auditor's wording would not. Always adjudicate every verdict and every
finding in the pass it lands: fix, rebut with evidence, or accept with a written disposition.
Nothing reaches a worker unadjudicated. A seat that reported a failed tool, or a contract that came
back unaudited, is absence of review — always an open gap, never a pass.

**6. Route and re-fire.** Deduplicate on the judge's `key` against everything **seen**, never
against what was confirmed — dedup on confirmed makes rejected findings reappear forever. Re-fire
each owning worker with its original brief plus its adjudicated findings, then re-integrate,
re-run criteria, re-audit, re-judge — the judge stays LAST, so it adjudicates the fresh audit. Check the two-re-fire rule **before** the pass cap: when one
`key` survives two re-fires, or is owned by PLANNER, it always returns to PLANNER, which may
rewrite the brief **or the goal itself**. A rewritten goal re-cascades the briefs.

**7. Stop.** No open findings and criteria green on the merged tree, or the pass cap (4) is hit.
Acceptance is never validator consensus. Report the exact failure when it fails; never wrap one
in "completed." **A deferred criterion is not a passed criterion**: while any owner-graded item is
ungraded, the verdict is `AWAITING OWNER GRADE — N machine-PASS, M owner-pending`, never "0 FAIL".

**8. Land it (main window).** Apply the integration worktree's diff — **to a staging branch, never
main, while any owner-graded criterion is pending.** The owner's first look IS the final pass: keep
the fix loop armed, route their findings through step 6, merge to main only after their explicit
pass. The main window applies patches and never authors or reads.

## Anti-rationalization

| Excuse | Answer |
|---|---|
| "I'll write the briefs myself, PREMIUM_MODEL gave me the shape." | The briefs are the plan. Re-spawn PLANNER. |
| "One validator can check all the workers, it's cheaper." | One validator, one worker. Cross-worker defects are the auditor's job, on raw output. |
| "Tests pass in each worktree, that's green." | Green is criteria on the merged tree. Nothing else counts. |
| "Same-lab judge is a decorrelated check." | It isn't. AUDITOR is a different lab or it is not an audit. |
| "The auditor said it, so fix it." | Unadjudicated findings mutate correct code. JUDGE rules first. |
| "No new findings this pass, ship it." | Stop on no OPEN findings. Recurrence is not convergence. |
| "N/M PASS, the rest are owner-graded." | Deferred ≠ passed. AWAITING OWNER GRADE; staging branch; main only after the owner's pass. |
| "The view code exists and tests count up, so it renders." | Only a render-proof on fixture data proves a UI draws. |
| "REVIEWER_CMD is unset, so there was nothing to block." | Unset means SKIPPED, in capitals, in the report. Skipped is not passed. |

## Cross-references

- `hard` — the single-target verification loop; use it when one worker and one reviewer suffice.
