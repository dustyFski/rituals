---
name: hard
description: "Goal-anchored execute-and-verify loop for a hard, ambiguous, or parallelizable task — code or not. Pins a task-specific testable goal, decides sequential vs parallelizable (one writer straight through for sequential; an inline Workflow fan-out with worktree-isolated writers for parallelizable — hard is not the same as parallel), then runs an adversarial cross-model check that refutes-by-default against the goal before declaring done. Loops fix→recheck, max 3 check passes. An optional review mode reviews a live product against a quantified north star instead. USER-INVOKED ONLY, deliberately — fires on '/hard', 'run hard on this', 'run the hard loop', 'tackle this with the full loop'. Do NOT auto-fire on routine requests. For session close use wrap."
---

**What it does:** Pins a testable done-state for one hard task, picks sequential or parallel execution, does the work under one writer per tree, then blocks on an adversarial cross-model gate that must see real evidence before the task can be called done.
**When it fires:** Deliberate invocation only, on a task worth the full loop: a gnarly debug, a multi-module migration, a subtle refactor, a broad audit, a review of a live product against its goal. Never on routine one-line work.
**Config:** `REVIEWER_CMD` (default none) — see README reviewer contract. `HARD_STATE_FILE` (default `.hard/state.md`) — the loop contract plus one block per check pass. `NORTH_STAR_FILES` (default none) — one or more files stating the quantified goal, review mode only. `LOCKED_DECISIONS_FILE` (default none) — deliberate decisions reviewers must not re-litigate, review mode only. `MAX_ROUNDS` (default 5) — review mode round backstop.

# /hard — Goal-Anchored Hard-Task Loop

You point it at any task (build, debug, refactor, research, write) and it pins what "done"
means, decides how much firepower the task deserves, does the work with one safe writer, then
hands the result to a reviewer that did not do the work, as a skeptic, before it is allowed to
call the task done.

Sequential mode runs on any agent that reads this file, including Claude Code and Codex CLI.
Parallel mode and review mode use Claude Code's Workflow script API (`agent()`, `pipeline()`,
`phase()`, `isolation:'worktree'`), available on paid plans and via the `/config` "Dynamic
workflows" toggle on Pro.

**Usage:** `/hard <the task, and what done looks like>`
Deliberate invocation only. This is you declaring "this one is worth the full loop." Do not
auto-fire it — a one-line fix needs neither a swarm nor a second model.

---

## Why this shape works (preserve when editing)

1. **A testable end-state beats a vague intent.** "The importer handles the 3 malformed CSV
   shapes in `/tmp/samples` without throwing, and existing tests still pass" — an agent can
   answer met/not-met. "Make the importer better" — it cannot.
2. **Hard constraints stated early and explicitly.** What must NOT change, what must stay
   backward-compatible, what's out of scope. Up front, not as an afterthought.
3. **One writer.** Helper agents are READ-ONLY — OR each parallel writer gets its own git
   worktree. The difference between "agents are told to be careful" and "agents cannot
   clobber each other."
4. **Adversarial check, refute-by-default, by a different model.** The end check's job is to
   prove the work WRONG, not bless it. A same-model self-review is not a check.
5. **The check must see real evidence.** An empty diff fed to the reviewer is a silent pass.
   The gate must receive the actual artifacts produced, or it has not run.
6. **Caps force prioritization.** Max 3 check passes. A loop that can't converge in 3 has a
   scoping problem, not a persistence problem.
7. **Scope each helper.** A helper gets only the files/context its slice needs, never the
   whole repo "for context."
8. **In a fan-out, the orchestrator writes the goals.** The main loop (the orchestrating
   session) authors each worker's goal prompt — a met/not-met sub-goal plus an explicit charge to
   pursue only that goal, refuse scope drift, and report honestly. A worker handed a blank brief
   self-scopes, and a self-scoped worker drifts off the parent goal.

## When NOT to use

- Small, linear tasks — just do them. The loop is overhead.
- Pure questions / research you can answer in one pass.
- A goal cascade across many subagents with its own validator tier → use **cascade**.

---

## Procedure

### Step 0 — Pin the loop contract (goal + 7 fields), and persist it

Write the **loop contract** — the goal block plus the six other fields the loop needs (full
template in `loop-contract.md`, this skill's dir). The core is still the goal:

- **What the task is** — one sentence.
- **Done looks like** — a testable end-state, not a topic.
- **Constraints** — what must not change, what's out of scope, what must stay working.

Then name the rest, so the Plan Gate, the closing gate, and the stop logic share ONE source of
truth: **Context** (files/URLs the loop may read), **Actions** (mode + reviewer), **Feedback**
(the programmatic check command + the refuter), **Base** (the starting HEAD, so the closing gate
can diff against it), **State** (this file), **Stop** (done-state · 3-pass cap · no-progress ×2),
**Boundary** (sequential vs worktree).

**If the invocation has no testable done-state**, do not guess silently: propose a falsifiable
one (or ask ONE clarifying question) before starting work. Show the contract back to the user
and proceed — but if the goal is genuinely ambiguous, wait for the answer.

Persist it as ONE state file for the whole run, so the Plan Gate and the Step 3 check read it.
The state file is `HARD_STATE_FILE`, default `.hard/state.md` in the project:

```bash
STATE="${HARD_STATE_FILE:-.hard/state.md}"
mkdir -p "$(dirname "$STATE")"          # a custom HARD_STATE_FILE may point at a new directory
BASE="$(git rev-parse HEAD 2>/dev/null)"   # record BEFORE any writing; empty on a non-git task
printf 'BASE %s\n' "$BASE" > "$STATE"
# quoted delimiter: contract text is written literally, so backticks and $VARS in it never run
cat >> "$STATE" <<'STATE_EOF'
<loop contract: goal / done / constraints + context / actions / feedback / stop / boundary>

## Pass log
STATE_EOF
```

The contract is prose you did not write as code. An unquoted heredoc would run any backticked
command in it and expand any `$VAR`. Write `BASE` with `printf` first, then append the contract
under the quoted `<<'STATE_EOF'` delimiter.

If the user corrects the goal mid-run, rewrite the contract atop the state file and re-enter
Step 1.

### Step 1 — Sketch the split, THEN decide the execution mode (the judgment gate)

Every `/hard` task is hard — but **hard is not the same as parallel.** Don't pick the mode from a
prior; pick it from a one-pass decomposition sketch (no writing, no agents):

**Sketch first.** Try to cut the task into slices that (a) touch disjoint files/surfaces and
(b) meet only at interfaces that already exist or can be fixed up front. Then read what the sketch
shows:

- Slices come apart cleanly and keep to their own files → **parallelizable.**
- Slices keep referring to each other, share types/state, or you can't name the seam without
  designing it first → **coupled → sequential.** Settle the shared interface in one sequential
  pass; only then can anything else fan out.

Then state the mode in one line:

- **Sequential** (a gnarly debug, a subtle refactor, a proof, deep single-surface work, or any
  build whose pieces meet at a seam you haven't designed yet) → ONE writer, straight through.
  Coherence comes from one mind holding all the constraints; splitting coupled work just relocates
  the coupling into a merge. Helpers may still investigate read-only, and **verification still fans
  out** (Step 3).
- **Parallelizable** (independent slices: a multi-module migration, an audit across N files, N
  independent components/endpoints behind stable interfaces, a broad research sweep, or a feature
  that genuinely decomposes) → decompose in Step 2 via a Workflow. This is where fan-out earns its
  keep: N writers each holding one slice beat one writer holding all N.
- **Review mode** (a live product to be reviewed against its stated goal, rather than a task to
  execute) → skip Steps 2 and 3 and go to the Review mode section below. Review mode runs its own
  blocking close check, so skipping Step 3 never means closing unreviewed.

The cost runs **both ways.** Wrong-parallel adds coordination cost and a merge to un-pick;
wrong-sequential wastes wall-clock and forces one writer to hold unrelated slices in one context,
which degrades the output. Default to sequential when the sketch shows coupling — not as a reward
for every hard task. When the sketch splits cleanly, fan out.

### Step 1.5 — Plan gate (review the approach before any writing)

Before any file changes, gate the *plan*, not the output — a cheap front gate that catches scope
and decomposition errors before expensive work:

- **Sequential** → one-line self-check: state the approach and confirm it can reach the
  done-state in the state file. If it can't, re-scope now.
- **Parallelizable** → check the decomposition: every slice has a testable sub-goal that
  *provably advances the parent goal* (Step 2 derives these). A slice you can't tie to the
  parent goal is the wrong slice — fix the split here, before the worktree fan-out is spent.
- **High blast radius** (broad migration, many writers, hard-to-reverse) → run the plan past
  `REVIEWER_CMD` before launching. Cheap insurance.

The Plan Gate is a same-model self-check by default — a sanity gate, not the adversarial one
(that's Step 3). Failing it loops back to Step 0/1, never forward into execution.

### Step 2 — Decompose with a Workflow (parallelizable mode only)

This is the engine for genuinely parallel work. **Author the Workflow script inline** — the
Workflow tool takes the script directly; there is no fixed template, because `/hard`'s structure
is per-task. Invoking `/hard` on parallel work IS the Workflow opt-in. The canonical shape is
**fan-out workers → verify each result as it completes → synthesize.**

**The orchestrating session authors every worker's goal prompt.** Workers are handed a goal,
never a blank brief: a met/not-met sub-goal plus an explicit charge to pursue ONLY that goal,
refuse scope drift, flag (not silently fix) anything outside its files, and report honestly
against the end-state. A self-scoped worker drifts; the main loop owns each slice's goal and
threads it into BOTH the worker and that slice's refuter. Copyable skeleton (adapt per task —
there is no fixed template, `/hard`'s structure is per-task):

```js
export const meta = {
  name: 'hard-fanout',
  description: '<task> — independent-slice fan-out: per-slice goal + adversarial verify',
  phases: [{ title: 'Build' }, { title: 'Verify' }],
}
// SLICES derived in Step 2 BEFORE launch. Each: { files:[...], subGoal:'<met/not-met, advances parent>' }
const SLICES = args.slices, PARENT = args.parentGoal
const WORK = { type:'object', required:['summary','metGoal'], properties:{
  summary:{type:'string'}, metGoal:{type:'boolean'}, files:{type:'array',items:{type:'string'}} } }
const VERDICT = { type:'object', required:['refuted','reasons'], properties:{
  refuted:{type:'boolean'}, reasons:{type:'string'} } }

// The orchestrating session writes the goal each worker gets — stay-on-track + stay-honest live in the prompt.
const goalPrompt = s =>
  `GOAL — do ONLY this, stay honest to it: ${s.subGoal}\n` +
  `Parent goal it must advance: ${PARENT}\n` +
  `Files in scope: ${s.files.join(', ')} — touch nothing else.\n` +
  `If the goal needs anything outside your files, STOP and report it; do not edit it. ` +
  `Do not claim done unless the met/not-met end-state is actually met.`
const refutePrompt = (s, r) =>
  `Adversarial reviewer. Default: this slice is NOT done.\n` +
  `Slice goal: ${s.subGoal}\nParent goal: ${PARENT}\nWorker claim: ${JSON.stringify(r)}\n` +
  `Refute against the slice goal AND whether it advances the parent goal. If uncertain, refute.`

const results = await pipeline(SLICES,
  s => agent(goalPrompt(s), { phase:'Build', isolation:'worktree', schema: WORK }),
  (r, s) => agent(refutePrompt(s, r), { phase:'Verify', schema: VERDICT }).then(v => ({ s, r, v })),
)
return results.filter(Boolean)
// Main loop then merges each worktree branch ONE AT A TIME, inspects for conflict, and runs the
// Step 3 whole-task gate on the FINAL merged state (don't run that gate twice).
```

**Before any worker prompt: derive a testable sub-goal per slice.** Splitting the work is not
splitting the goal. For each slice write a one-line met/not-met end-state that (a) can be judged
on that slice alone and (b) provably advances the parent goal in the state file — if you
can't say how a slice moves the parent goal, it's the wrong slice. Thread that sub-goal through
BOTH pipeline stages: into the worker's `workPrompt` (so the worker knows what "done" means for
its slice) AND into that slice's refuter (so it refutes against the slice's own end-state, not a
generic "is this output ok"). The refuter stage receives the original slice as its second
argument — use it:
`pipeline(slices, s => agent(s.workPrompt, {isolation:'worktree', schema}), (r, s) => agent(refutePrompt(s.subGoal, r), {schema}))`
A slice that passes its own refuter but doesn't move the parent goal is a scoping error — catch
it here, not at the Step 3 whole-task gate after the fan-out is already spent.

- **Investigation / research / review slices (no writes)** → workers are read-only; their prompt
  must EXPLICITLY forbid editing, writing, creating, deleting, moving, committing. They return
  structured findings; only the main loop writes.
- **Independent build slices that each write files** → each worker runs in its own worktree
  (`isolation: "worktree"`). The main loop merges each branch **one at a time** and inspects for
  conflict. A conflict means the slices weren't independent → abort that merge, fall back to one
  sequential writer for the overlap. Re-verify after each merge; the check on the FINAL merged
  state IS the Step 3 closing gate — don't run it twice.
- **Make verification a pipeline stage, not an afterthought:** each worker's result is checked by
  an INDEPENDENT refuter **against that slice's sub-goal** as it completes (the
  `pipeline(items, do, verify)` pattern) — so
  worker A's output is being verified while worker B is still running. This per-slice verify does
  NOT replace Step 3 — the final whole-task gate still runs once, on the merged result.

For a tiny fan-out (2–3 read-only helpers) the Agent tool directly is fine; a Workflow earns its
keep once there are enough slices, or enough verify structure, to justify the script.

### Step 3 — The adversarial end check (the closing gate — never skip, never no-op)

Gather the REAL evidence first — the gate is worthless if it sees nothing. Handle code and
non-code, tracked and untracked:

```bash
STATE="${HARD_STATE_FILE:-.hard/state.md}"
BASE="$(awk '$1=="BASE"{print $2; exit}' "$STATE")"   # the HEAD recorded at Step 0
EVIDENCE="$(mktemp)"   # outside the repo, so the scan can never ingest its own output
{
  echo "GOAL:"; cat "$STATE"
  echo; echo "CHANGES + EVIDENCE:"
  if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    git status --short
    # diff against BASE, not the index: merged worker branches, commits and staged work all count
    git --no-pager diff "$BASE"
    # new untracked files: NUL-safe (spaces/newlines), skip binaries, cap size, skip loop state
    git ls-files -z --others --exclude-standard -- . ':(exclude).hard/*' |
      while IFS= read -r -d '' f; do
        case "$(file -b --mime "$f")" in *charset=binary*) continue;; esac
        sz=$(wc -c < "$f" | tr -d ' ')   # BSD wc pads; strip so the message reads clean
        if [ "$sz" -gt 20000 ]; then
          echo "BLOCK: artifact too large for one payload: $f ($sz bytes)"; continue
        fi
        echo "--- new file: $f ---"; cat "$f"; echo
      done
  else
    echo "(non-git task: paste the produced artifact contents + any test/verification output)"
  fi
} > "$EVIDENCE"
```

Headers alone make the file non-empty, so size proves nothing. A non-empty diff proves nothing
either: it can be one unrelated file while the artifact the contract named is still missing.

Check per artifact instead. List every artifact the contract asked for, then grep `"$EVIDENCE"` for
each one by name and confirm it is present with its content. Untracked-only deliverables count, so
a new file that was never committed must appear under its `--- new file:` header. If any artifact is
missing, STOP. That is itself a finding (you changed nothing, or the gate cannot see your output).
Fix before reviewing.

Never truncate an artifact to fit the payload, because the cut half is where the defect hides. When
an artifact exceeds the size cap, the collector emits a `BLOCK:` line naming the file and its byte
count. Stop on that line and shrink the payload at the source: review that artifact in its own
reviewer call, or split the run. Splitting the payload across calls also works, but one artifact per
call is simpler, so prefer it.

**Programmatic check first (deterministic before judge).** If the task has a
deterministic pass/fail — tests, build, compile, lint — run it now and append the result to
`"$EVIDENCE"`. A programmatic FAIL is a fix in the main loop; do NOT spend a judge
pass on known-broken work. Only a programmatic PASS (or a task with no programmatic check)
proceeds to the refuter.

Then run the refuter against goal + evidence, through `REVIEWER_CMD`:

```bash
"$REVIEWER_CMD" < "$EVIDENCE"
```

`REVIEWER_CMD` takes the payload on **stdin only**; there is no `--evidence` flag. Its first line is
`PASS` or `BLOCK`. Each later line is one finding, formatted
`<severity> | <owner or n/a> | <one-line finding>`. **A first line that is neither `PASS` nor `BLOCK`
is malformed, and malformed means no review happened. So does a non-zero exit or empty stdout.**
Never read any of those as a pass. Say so and fall back.

**Fallback when `REVIEWER_CMD` is unset or produced nothing:** spawn a FRESH subagent with the
same refute-by-default prompt, hand it the same payload on stdin, and require the same
`PASS`/`BLOCK` first line and finding format. The fallback is weaker, because it shares a model family with the writer. **The final
summary must name that the fallback was used**, so the second-model claim stays auditable rather
than assumed.

**The reviewer MUST be a different model than the one that did the work** — that is the whole
point. **Name the reviewer(s) you actually used in the final summary.**

**Verification fans out regardless of write mode.** For high-stakes or coupled feature work, run
the refuter as a small panel — 2–3 reviewers with distinct lenses (correctness · drift-from-goal ·
does-it-actually-run), each refute-by-default and decorrelated from the writer; majority-refute =
BLOCK. A sequential *write* does not force a sequential *check*; the panel counts as one check pass.

- **BLOCK** → append the findings to the `## Pass log` in the state file, fix the real
  ones in the main loop, then re-run the check.
- **PASS** → done.
- **Round counter:** a round = one check pass. After the **3rd BLOCK, STOP and report
  regardless** — do not run a 4th. Non-convergence in 3 is a scoping signal, not a persistence one.
- **No-progress stop:** before re-running, compare this pass's BLOCK findings +
  evidence diff against the previous pass's in the state file. If a fix attempt left the
  same finding standing (the evidence didn't move), that's a no-progress pass. **Two no-progress
  passes → STOP and escalate**, even with a pass left — spinning is not persistence.

### Step 4 — Summarize, then hand off (don't duplicate)

Summarize to the user: what got done, which reviewer ran, what it flagged, how each flag was
resolved or why it was dropped. Then: **if the session is being closed, invoke `wrap`**. Otherwise
stop after the summary. Either way, do not repeat wrap's steps here.

---

## Review mode

Use review mode when the subject is a **live product to be reviewed against its goal**, not a
task to execute. The question is "is this thing serving the goal it exists for", not "is this
change correct". Sequential and parallel mode judge a diff; review mode judges the live artifact.

**Inputs.** `NORTH_STAR_FILES` names one or more files stating the quantified goal: what the
product is and for whom, the success metric WITH its current value and trend, and the hard
constraints. A quantified north star beats an abstract mission, because it gives every reviewer a
tiebreaker for every judgment call. `LOCKED_DECISIONS_FILE` names the deliberate decisions
reviewers, verifiers and the Guardian must not re-litigate. Flagging a locked decision is the
number one false-positive class, so every verifier prompt carries the list.

Assemble both into the loop contract at Step 0 and show it in the kickoff message. **Showing the
contract IS the human plan gate**: the one cheap chance to catch a wrong north star or a misfit
dimension before N reviewers spawn. Add a one-line dimension-fit check and drop any dimension with
no live surface to review.

**Safety boundaries (a live product is the subject, so these are hard).**

- Only explicitly approved change classes may auto-apply. An unknown or unspecified scope is
  `proposeOnly`.
- Protected surfaces are never auto-applied: forms, navigation, CTAs, templates, new pages,
  removals, deployment config.
- Remote or production inputs are staged locally as read-only snapshots first. Subagents get no
  remote access, and never ssh.
- At most two code fixes auto-apply per round. The cap forces prioritization; log what it deferred.
- Every proposal goes to `.hard/pending.md` for the owner.
- Deploy only with the owner's explicit approval.

**Per round, one Workflow:** `pipeline(DIMENSIONS, review, verify)` → barrier → Guardian.

- **Review phase.** N read-only dimension reviewers in parallel. Each gets the north star, the
  constraints block, ONE atomic goal as a testable end-state, and only its own file paths and
  URLs. No reviewer gets the whole repo "for context". An atomic goal reads "every factual claim
  published in the last 7 days matches its cited source", not "review content quality".
- **Findings schema, capped.** Structured output, never free text, with evidence fields: quoted
  text, fetched value, file:line, never assumption. Cap 8 findings per reviewer, keeping the ones
  that matter most to the north star; log what the cap dropped. Enforce the cap in the schema
  (`maxItems`) plus post-call truncation, because a cap stated only in a prompt is a suggestion.
  Each finding carries a `fix_scope` from `FIX_SCOPES` (below) and a severity **anchored to
  business impact**, defined inline in the prompt: CRITICAL = user-visible error or legal exposure
  live now; HIGH = materially blocks trust or growth; MEDIUM = real, not urgent; LOW = polish.
  Without the rubric every reviewer inflates.
- **Verify phase.** A refute-by-default pass on CRITICAL and HIGH findings only, cap 6 per
  dimension, run through `REVIEWER_CMD` on stdin as pipeline stage 2, not behind a barrier. This
  pass is **advisory**: it prunes findings, it does not close the loop. Verification of
  dimension A starts while dimension B still reviews. The prompt says: your default position is
  that the finding is WRONG, try to refute it, and if uncertain, refute. Include the
  locked-decisions list. A non-zero exit, empty stdout, or a first line that is neither `PASS` nor
  `BLOCK` is no review, never a pass; fall back to a fresh subagent and name the fallback in the
  summary. The reviewer verdicts the batch; the **Guardian**, not the reviewer, sets each finding's
  disposition.
- **Guardian phase.** ONE synthesis agent receives all surviving findings, the per-dimension goal
  assessments, and the fix scopes. It outputs: `north_star_assessment`; `safe_fix_plan` (each item
  naming files, an `exact_change` precise enough to apply without re-deriving, and a test);
  `proposals_for_owner` (consolidated); `dropped` (aggressive, with reasons, this is the
  course-correction); `verdict: continue|done`; `progress: advancing|stalled`; and
  `course_corrections` for the next round's reviewers. Making scope-kill a required output field
  turns it into a deliverable rather than a hope.

**Fix scopes.** `FIX_SCOPES` maps each scope name to one of two behaviors. Its default is
`auto: []`, everything else `proposeOnly` — so a scope nobody approved cannot write.

- `auto` — the main loop may apply it, taking a timestamped backup first, then running the
  Guardian's `test` field. Subagents never write. One writer, no exception for size.
- `proposeOnly` — never applied by the loop. Written to `.hard/pending.md` for the owner to decide.

Put anything that changes first paint, removes content, or touches deploy machinery in a
`proposeOnly` scope. Apply the programmatic gate before the model judge on any code fix: compile
and the regression test must pass FIRST, and only then does a fix earn a review pass.

**Between rounds,** feed the Guardian's `course_corrections` into the next round's reviewer
prompts and mark prior findings as known, so reviewers hunt NEW issues instead of re-reporting old
ones.

**Final CRITICAL check (blocking, once, before `done`).** The per-round verify pass is advisory: it
prunes findings on their way to the Guardian. This one is different. Before the loop may return
`done`, run `REVIEWER_CMD` once over **every surviving CRITICAL finding** with its evidence. If
`REVIEWER_CMD` is unset or produced nothing, use the named fallback refuter and say so in the
summary. A `BLOCK` here reopens the loop for another round. No round closes on advisory checks alone.

**Stop.** Two consecutive clean rounds (zero new CRITICAL or HIGH, every prior CRITICAL and HIGH
either fixed or formally proposed) **plus a passing final CRITICAL check** = done. `MAX_ROUNDS` (default 5) is the backstop: stop and
report regardless. Two consecutive `stalled` rounds also stop and escalate, rather than re-running
identical reviewers. Stagnation is a scoping signal, not an effort one.

---

## Anti-rationalization

| Excuse | Rebuttal |
|---|---|
| "It's a hard task, so fan it out into a Workflow." | Hard ≠ parallel. Sequential hard work (debug, proof, subtle refactor) gets worse when split. Default sequential; Workflow only for independent slices. |
| "It's coupled-ish, I'll keep it sequential to be safe." | Sequential-by-fear wastes the fan-out engine. If the sketch splits into disjoint files behind stable interfaces, fan out — serializing genuinely independent slices is its own failure mode, not the safe choice. |
| "Let each worker infer its own goal from the task." | Workers get a goal the orchestrating session wrote, not a blank brief. A self-scoped worker drifts; the main loop owns each slice's met/not-met end-state and the charge to stay honest to it. |
| "Each worker has a prompt, that's enough." | A workPrompt is a task, not a goal. Without a met/not-met sub-goal the refuter has nothing slice-specific to refute against, and a slice can be 'done' while moving the parent goal nowhere. Derive the sub-goal first, thread it into worker and refuter. |
| "A helper can just make this small edit itself." | Helpers are read-only, or worktree-isolated. One writer per tree. No size exception. |
| "The diff is empty but I did the work, ship it." | Empty evidence = the gate is blind. That's a finding, not a pass. |
| "I'll let the same model self-review, close enough." | A same-model self-review is not an adversarial check. Use `REVIEWER_CMD`, or a fresh refuter, and name it. |
| "The reviewer is slow, skip the check this once." | Run the fresh-subagent fallback and say you used it. Skipping the gate turns `/hard` into ordinary work with a fancier name. |
| "Two writers in one tree, I'll sort the merge out." | Worktrees, or one writer. A merge conflict means the slices weren't independent — fall back to sequential. |
| "It didn't pass in 3 rounds, one more will do it." | 3-pass cap. Non-convergence means the goal or scope is wrong — report it. |
| "Same finding came back — one more fix will get it." | A fix that left the finding standing is no-progress, not under-effort. Two no-progress passes → stop and escalate. |
| "Skip the plan gate, I'll just start writing." | The plan gate is cheap; a bad decomposition found after the fan-out is not. Gate the approach before any writes. |
| "This review finding is obviously real, skip verification." | Obvious findings are exactly the plausible-but-wrong class. CRITICAL and HIGH always get a refuter. |
| "Polish improves the product, keep the finding." | The Guardian drops polish against a stalled metric. That is its job, not a bug. |
| "The verifier refuted it, but I still think it's real." | Gather NEW evidence in the main loop and re-submit next round. Don't overrule the gate silently. |
| "The review loop should keep running until perfect." | `MAX_ROUNDS` backstop. Convergence failure is a scoping signal, report it, don't grind it. |

## Cross-references

- Goal cascade across many subagents, with its own validator tier: `cascade` skill
- Reviewer contract and a worked `REVIEWER_CMD`: repo README plus `examples/`
- Scope each helper to only the files its slice needs (subagent-context discipline)
- Loop contract (pre-flight 7 fields): `loop-contract.md` in this skill dir
- Session close: `wrap` skill

## Credits

A ralph-style execute-and-verify loop. Plan gate, no-progress stop, programmatic-before-judge
ordering and the loop contract are adapted from github.com/ksimback/looper (MIT). What this adds:
the sequential-versus-parallel mode decision, a cross-model refute-by-default gate,
empty-evidence-is-a-finding, and the optional review mode.
