---
name: repeat-offender
description: Weekly sweep across a project's run ledgers for the same root failure recurring in 2+ different systems — writes a root-cause note, proposes ONE system-level fix rather than a point patch, and tracks whether shipped fixes actually stopped the offender. Fires on "repeat offender sweep", "what keeps breaking", "run the failure digest".
---

**What it does:** Sweeps existing logs for a failure mode that shows up in two unrelated systems and proposes one system-level fix for it.
**When it fires:** "repeat offender sweep", "what keeps breaking", "run the failure digest".
**Config:** state file path — default `repeat-offender-STATE.md`, created empty on first run; list of run ledgers/logs to sweep — config value, no default and must be non-empty (point it at whatever logs, ledgers, or state files your project already keeps).

# /repeat-offender — Cross-System Failure Digest

Reads what already failed, elsewhere. Zero new auth, zero new data collection — every input is a
log or ledger that already exists. The find this skill is built to catch: the SAME root cause
showing up in two unrelated systems, which nobody notices because nobody reads both logs in the
same sitting.

**Usage:** `/repeat-offender` — no arguments, sweeps everything configured.

## Reads (all existing, read-only)

- Any run ledger or verify-pass log your project keeps (loop rounds, adversarial check results,
  fix rounds)
- Any BLOCK/QUEUE-style gate ledger
- Pipeline failure records for any recurring job
- Other skills' state files as they accumulate history (e.g. `watchdog`, `killcheck`, `shadow`)

## State file

`repeat-offender-STATE.md`:

```
## Failure catalog (append-only)
<root-cause-id> | first seen <date> <system> | recurred <date> <different system> | fix proposed <date/none> | fix status: shipped/none/failed-twice

## Log
YYYY-MM-DD | no-op | first sweep, catalog created empty | swept 3/3 ledgers, window YYYY-MM-DD..07-05
YYYY-MM-DD | BLOCK | 2 of 5 ledgers unreadable (perms), sweep incomplete, no verdict
YYYY-MM-DD | DONE | matched "unscoped write outside worktree jail" in both a workflow run AND a pipeline log — root-cause note + ONE proposed guard written
```

## Procedure

1. Read the catalog + log from the state file. If the file is absent, create it with an empty
   catalog and log, then continue. An absent catalog is a first run, not a clean sweep.
2. Check the configured ledger list. Empty list → `BLOCK`, say nothing is wired to sweep, stop.
3. Sweep this week's run ledgers (see Reads above) for failures, blocks, and partials. Record
   which sources were read and the time window covered.
4. Any configured ledger missing or unreadable → `BLOCK`. Name each one and why. An incomplete
   sweep never reports "nothing recurring."
5. Match new failures against the catalog. **The find is specifically the same root cause
   appearing in 2+ DIFFERENT systems** — not the same system failing twice (that's the system's
   own retry logic to fix) and not two different root causes that merely look similar.
6. No match found across a complete sweep → `no-op`, log it with the sources and window
   inspected. Do not manufacture a finding.
7. Match found → identify the worst (most-recurring, or highest-cost) repeat offender this week.
   Write:
   - A root-cause note: what the actual shared mechanism is (not "it broke twice," but *why*
     the same mechanism produces the same failure in unrelated code).
   - ONE proposed system-level fix — a shared guard, a config change, a doc correction — that
     would remove the root cause everywhere it appears, not a patch to just the one instance
     that happened to be reviewed this week.
8. Track previously-proposed fixes: did the offender stop reappearing? A fix that shipped but the
   same root cause recurs a second time afterward means the root cause is deeper than the fix
   addressed — escalate that explicitly rather than proposing a third patch.
9. Append everything to the state file, including the sources and window inspected.

No hard cap beyond one proposal per weekly run — "ONE system change per week" is deliberate; a
sweep that finds three real repeat offenders in one week still only proposes the worst one and
queues the rest.
