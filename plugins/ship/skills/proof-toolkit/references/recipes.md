# Proof recipes — full detail, commands, and worked examples

Companion to `../SKILL.md`. Each recipe below has: what it proves, the command shape, why it's
decorrelated (where that applies), and a worked example illustrating the failure mode it catches.

---

## 1. Refute-by-default adversarial review

**Proves:** a verdict, fix, or plan survives someone actively trying to kill it — not just someone
nodding along.

**Command shape:**
```
$REVIEWER_CMD < evidence.md
```
The evidence goes in on stdin, and nothing else does. Transport is stdin only. Build the evidence
file yourself: the diff, any new files, the test output, and the numbered claims you want falsified.
Number the claims, because the coverage check below counts them.

Ask the reviewer for its strongest effort setting. A review run at a default effort is a weaker
check than the one this recipe calls for, and the difference is invisible in the output.

Give the reviewer time to finish. A high-effort reviewer can think silently for minutes at a
stretch, so a short timeout kills it mid-thought and you get no review at all.

**Decorrelation rationale:** pick reviewers from labs/model families that share no lineage with
each other or with the model that authored the work under review. A same-family check (a model
reviewing its own family's work) is not independent — it shares blind spots with the author, so it
has every incentive and no independent vantage point to just agree.

**A review is usable only if** its first line is exactly `PASS` or `BLOCK`. Following lines are
findings, one per line, formatted `<severity> | <owner or n/a> | <one-line finding>`. After the
findings, the reviewer writes one line per numbered claim it checked, formatted
`claim <n> | PASS|FAIL | <one line>`. A clean review has no findings and still answers every
claim. A first line that is anything else is malformed and counts as no review. A non-zero exit or
empty stdout is also no review, never a pass. `BLOCK` applies to the work under review: fix the
findings and re-run.

**Coverage floor:** coverage is the count of submitted claim IDs the reviewer answered, divided by
the number of claims you submitted. Discard any `claim <n>` line whose ID you did not submit; an
unknown ID never adds coverage. Below 50%, the review is not usable evidence, however confident its
first line sounds. Re-run it, or say the check did not happen. A clean `PASS` requires every
submitted claim answered `PASS`: any unanswered or `FAIL` claim means the check did not pass,
whatever the first line says.

**Worked example — a launch-readiness verdict reversed by the reviewers:** a provisional
"ship after fixes" verdict on a product's launch readiness was reviewed by three decorrelated
adversaries from three different labs, via a shared verdict file. All three independently returned
"verdict does not hold" against it, with substantially overlapping but independently derived reasoning:
- **Conflict 1 (who bears the fraud risk of a forgeable client-side check):** the provisional
  verdict had treated this as a bounded post-launch residual ("the end user is the only plausible
  threat actor, no money rides on the check"). All three reviewers independently rejected this
  framing on different grounds — one pointed out that the product's own selling point depends on
  that check being unforgeable, so a forgeable version fails to be what it's sold as from day one;
  another pointed out the framing inverts who is harmed — a forged check defrauds the paying
  customer, not the operator; the third noted that a "residual closes in N days" window in the
  provisional verdict was invented, defined nowhere in the actual spec. Resolution: accepted in
  full — the verdict author conceded the window was constructed, not derived, and moved the item to
  a money-blocking issue.
- **Conflict 2 (blocker-count honesty):** the provisional verdict counted a small number of
  blockers by bundling several independent failure points under one line item and parking other
  known-open items outside the table entirely. The reviewers each recounted honestly, landing well
  over the brief's own ship/no-ship ceiling even under a generous count. Resolution: accepted — the
  honest recount stayed over ceiling, so the verdict flipped from "ship after fixes" to "do not ship
  yet", with the estimate corrected upward.
- The verdict author also documented what was **not** conceded — one adversary claim stood
  unrefuted by all three, and one did not. A refute-by-default review does not mean rubber-stamping
  every adversary claim; it means engaging each one on the merits and recording the resolution
  either way.

This is the load-bearing example for why reviewers must be decorrelated: a same-family reviewer
grading its own prior verdict would have had every incentive, and no independent vantage point, to
just agree with it. Three separately-trained models, with no shared blind spot, independently found
the same two structural holes.

**Second worked example — a shared bug caught three ways:** within the same round, all three
decorrelated reviewers independently flagged the same concrete defect pattern (a
nullable/boolean-ambiguity bug in payment-adjacent entitlement logic) without being pointed at it —
the kind of convergent, unprompted finding across independent architectures that is much stronger
evidence than one reviewer catching it once.

---

## 2. Rederive-from-source self-test

**Proves:** a pipeline's output is actually and correctly derived from its stated inputs by the
pipeline's own current logic — not a stale file, a hand-edit, or silent drift from a data-format
change upstream.

**Command shape:**
```
$RERUN_SELFTEST_CMD
```
For example: `python3 rederive_pipeline.py --selftest`. A good `--selftest` builds a synthetic
input for one segment with known rows — including a duplicate, a renewal/repeat entry, an outlier
row, and a row that should be filtered out entirely — runs the real derivation function against it,
and asserts the output lands on an **independently hand-computed** correct answer with the right
rows filtered/deduped. It should exercise every filter branch in one pass and print a clear
`SELFTEST PASS`/`FAIL` with the derivation stats.

**Why this recipe, not just "read the output and eyeball it":** when a pipeline writes a derived
data seed that a live surface reads directly to answer a real question, a silent failure mode here
is dangerous by construction. A well-hardened pipeline carries an explicit fatal gate refusing to
write a fresh output if zero inputs matched, and a floor check refusing to write when the match
rate (matched input rows divided by total input rows) falls below 50% of the prior run's match rate. Both guards exist because an upstream format drift (a column rename, a
value-vocabulary change) could otherwise pass every other check yet silently match nothing — a
rederive that looks like it ran clean while actually deriving garbage. `--selftest` is the
deterministic regression check that the derivation math itself (filters, dedup, matching, whatever
aggregation the pipeline does) still lands on a known-correct answer after any change to the
pipeline — independent of whatever the live upstream export currently contains.

**Decorrelation rationale:** N/A — this is a self-test against a hand-computed ground truth, not an
adversarial-panel recipe. Its power comes from the expected value being computed independently (by
hand, in the test) of the code path being tested, so a bug that breaks the derivation logic breaks
the assertion too.

---

## 3. Phantom-claim (reality-check) detection

**Proves:** an unattended agent's "I did X" claim in its result markdown is real — the file exists
and was actually modified in the run window, or a commit actually happened — not a silent no-op, a
crashed process that still logged success, or a rewritten result file.

**Command shape:**
```
$PHANTOM_CHECK_CMD <result_file.md> --repo <path> --hours <window>
```
A good implementation defaults its `--repo` to wherever it normally runs (e.g. a server path) —
always pass `--repo` explicitly when running it somewhere else. Exit code 0 = no phantom claims (all
VERIFIED or UNVERIFIED); exit code 1 = one or more CONTRADICTED (phantom) claims found.

**Deliberately conservative by design:** it should only return CONTRADICTED when the evidence
*definitively* refutes a claim (file missing, file stale outside the run window, zero commits
anywhere in the run window). When it cannot prove a claim false — e.g. a commit exists but can't be
attributed to this specific agent — it returns UNVERIFIED, never a false phantom. The guiding
principle: a verifier that cries wolf is worse than no verifier.

**Worked example — three incident classes that motivate it:**
1. An unattended agent drifted dead for roughly three weeks while the dispatcher's launch call had
   logged "launched" — a silent process-spawn failure that looked like a running job.
2. A file-transfer "shipped" claim in a result file never actually landed. An old modification
   time on the destination is a prompt to check, not proof: `scp -p` preserves the source mtime, so
   a successful transfer can leave an old timestamp. Prove it with a hash of the source and a hash
   of the destination, or with independent transfer evidence such as the transport's own log. On an
   old timestamp alone the claim is UNVERIFIED, never CONTRADICTED.
3. An agent rewrote its own result file *after* a downstream step had already read it — making the
   claim self-consistent on a later read but false at the moment it mattered.

This is the design justification for phantom detection existing as a deterministic, file/git-only
check (no LLM) that runs *before* an agent's result is trusted by whatever consumes it next.

---

## 4. Blind A/B (shadow test)

**Proves:** a candidate model/prompt is actually preferred, not merely different, with the human
grader's judgment uncontaminated by knowing which side is which.

**Mechanism (full procedure lives in the `shadow` skill — this entry covers only the proof logic,
not the operational steps):** run the candidate silently on the same real production inputs the
target actually processed. Candidate output never touches anything live. Per input: **agreement**
(same substantive output, or a difference that doesn't matter) is discarded, not logged — agreement
is noise, not signal. **Disagreement** gets queued, unlabeled which side is which. At the end of the
observation window, the queued disagreements are graded blind by a human — two unlabeled outputs,
pick the better one.

**Worked example — a real production-vs-candidate run:** the target was a pinned production writer
model; the candidate was a newer model on the identical brief. The first real comparison pulled an
actual production input and the actual shipped output, then ran the candidate on the same input.
Both landed on the same facts and the same structure, but they did not read the same: the two
openings and the ordering of the middle section were not interchangeable, and whether that
difference was an improvement is exactly the judgment the agent must not make for itself. So it was
queued as ONE disagreement item for a blind human grade. The verdict was "extend the run": one sample is not a week's worth of evidence, and
single-digit samples on a low-volume system are too few to judge — so the run explicitly deferred a
verdict rather than force one on a thin sample, and queued continuing through the next real
production runs before any promote/keep call.

Note: illustrative example log lines inside a skill's own SKILL.md are template text, not real
state — real state belongs only in the per-target state file this recipe writes to.

**Decorrelation rationale:** the cross-family rule does not apply here. It governs adversarial
review only. In a blind A/B the decorrelation is procedural (blind labeling), not model-family. The
candidate and production model may well share a lab; what's being decorrelated is the grader's
expectation from the output.

---

## 5. Held-out validation (strict-greater acceptance)

**Proves:** a proposed edit is a genuine improvement on data the optimizer never saw during
optimization — not an edit that overfits to exactly the inputs it was scored against.

**Spec:** write the contract in a file (`HELD_OUT_SPEC_FILE`) before building the loop that enforces
it. Treat any claim that this recipe has already caught a real regression as unverified until the
loop that enforces it is actually built and a run log exists.

**The contract, as specified:**
- Write a versioned split manifest (input IDs, split label, manifest hash). The loop pins one
  manifest version per run; a version mismatch is a hard stop.
- The validation split is the gate set. **The optimizer never sees it** — not the inputs, outputs,
  or scores. It sees train rollouts only. Any code path that shows validation data to the optimizer
  is a defect.
- The validation split is **immutable** during a run — not regenerated, reshuffled, or extended
  mid-loop. Growing the held-out set is a new manifest version and a new run.
- Score is an **integer pass-count** over the validation split — never compare fractions or floats;
  integer comparison eliminates float noise entirely.
- **Acceptance rule (exact):** accept a candidate edit iff `candidate_pass_count >
  current_best_pass_count` — strictly greater, integer. A tie (`==`) is REJECT — equal is not
  improvement, and an edit that flips one input to pass and another to fail nets zero and is
  correctly rejected.
- If the thing under test can't be scored deterministically (e.g. non-zero-temperature sampling),
  require the improvement to hold across k=3 seeds independently before accepting — closes the
  "accepted noise" hole.

**Example target:** a content or code writer scored by a deterministic validator, with the model
under test treated as frozen during optimization.

**Cross-reference, don't duplicate:** the acceptance-bar mechanics (what generally counts as
evidence, ship-gate tiers) belong wherever a project keeps its acceptance-bar doc; this entry covers
only the held-out-split proof method that such a doc would reference but not restate.
