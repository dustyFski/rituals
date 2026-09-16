# /hard — loop contract (pre-flight)

Fill this in at Step 0 and persist it to `HARD_STATE_FILE` (default `.hard/state.md`). It is the
rollup of fields `/hard` already gathers, made explicit so the **Plan Gate (Step 1.5)**, the
**closing gate (Step 3)**, and the **stop logic** all read one source of truth. Maps looper's
"healthy loop checklist" onto `/hard`.

```
GOAL      — the one-sentence task + a testable done-state (met/not-met), not a topic
CONTEXT   — the exact files / dirs / URLs / sample inputs the loop may read
ACTIONS   — execution mode: ONE writer (sequential), worktree-isolated writers (parallel),
            or read-only dimension reviewers (review mode);
            judge = REVIEWER_CMD (adversarial), fallback a fresh subagent refuter
FEEDBACK  — the programmatic check command (tests / build / compile / lint) + the refuter
BASE      — the starting HEAD, recorded at Step 0 (`git rev-parse HEAD`); the closing gate
            diffs against it, so committed and staged work still counts as evidence
STATE     — HARD_STATE_FILE (contract on top, one block appended per check pass)
STOP      — done-state met (PASS) · 3-pass cap · no-progress ×2 (two passes that don't move
            evidence) · review mode: two clean rounds, MAX_ROUNDS, or two stalled rounds
BOUNDARY  — sequential vs worktree; git repo (diff is evidence) or non-git (artifact is evidence)
```

Notes:
- The human checkpoint — ask ONE clarifying question when the done-state is ambiguous — is part
  of GOAL. Resolve it before the Plan Gate.
- CONTEXT scopes every helper: a helper gets only the files its slice needs, never the whole
  repo "for context."
- BASE is non-git tasks' one blank field: there the artifact itself is the evidence.
- In review mode, GOAL is the north star from `NORTH_STAR_FILES` plus one atomic goal per
  dimension, and CONTEXT includes `LOCKED_DECISIONS_FILE`.
