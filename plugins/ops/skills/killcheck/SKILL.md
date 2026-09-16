---
name: killcheck
description: Generic kill-criteria decision loop for any open either/or call with 2+ live options. First run writes a concrete kill condition per option BEFORE evidence-gathering; later runs hunt ONLY disconfirming evidence — a triggered kill condition is final, and a lone survivor's record IS the recommendation. Fires on "killcheck [decision]", "write kill conditions for", "what would kill this option", "run the kill-criteria loop on".
---

**What it does:** Forces a falsifiable disqualifying condition for each option before gathering evidence, then only hunts for evidence that would kill an option.
**When it fires:** "killcheck [decision]", "write kill conditions for", "what would kill this option", "run the kill-criteria loop on".
**Config:** state file path — default `<decision-folder>/killcheck-STATE.md`, alongside wherever that decision's docs live; no other config.

# /killcheck — Kill-Criteria Decision Loop

Most decisions get made by accumulating reasons FOR an option until one feels heaviest. This
skill inverts that: it forces a concrete, falsifiable reason each option would be DISQUALIFIED
before anyone looks for evidence, then spends every subsequent pass hunting only for that
disqualifying evidence. An option that survives repeated, genuine attempts to kill it earns the
recommendation — not because it scored well, but because nobody could find the fact that would
rule it out.

**Usage:** `/killcheck <decision name> — <option 1>, <option 2>, ...`

## Why this exists

A positive-evidence score (however it's computed) says nothing about what fact would mean "don't
choose this even at a high score." Decisions that get advanced by score alone, with no written
pre-commit kill condition, tend to accumulate quiet regret later. This skill is a generalizable
fix: write the disqualifying condition first, for any decision — not just scored ones.

## State file

`<decision-folder>/killcheck-STATE.md`:

```
## Roster (recorded on the FIRST run, never edited afterwards)
<option A>, <option B>, <option C>

## Options and kill conditions (written FIRST, before any evidence pass)
- <option A>: KILL IF <concrete disqualifying fact — a number, a date, a missing dependency>
- <option B>: KILL IF <...>
- <option C>: UNRESOLVED, no testable kill condition articulated

## Log (append-only)
YYYY-MM-DD | BLOCK | roster recorded; option C UNRESOLVED, no testable kill condition — first run incomplete
YYYY-MM-DD | BLOCK | option C still UNRESOLVED — no recommendation this run
YYYY-MM-DD | WITHDRAWN | option C withdrawn by <who>, reason: <why it is off the table>
YYYY-MM-DD | DONE | kill conditions written for every roster option still in play, no evidence pass yet (first run)
YYYY-MM-DD | PASS | hunted disconfirming evidence for both — neither kill condition triggered
YYYY-MM-DD | DONE | option B's kill condition triggered (<cited fact>) — option B is dead, no resurrection without new facts
```

## Procedure

**First run for a decision:**
1. List every live option and record that list as the roster. Completeness is measured against
   the roster forever after, so an option can never be quietly dropped to make the gate pass.
2. For EACH roster option, write one explicit kill condition — a concrete fact that, if true, means
   "don't build/choose this," not a vague risk. Good: "conversion below 5% in season." Bad:
   "if it doesn't work out."
3. If a kill condition can't be articulated for an option, mark that option `UNRESOLVED` and say
   so explicitly. Do not force a weak condition to fill the field. An `UNRESOLVED` option is
   never a tested survivor. It clears only two ways: someone writes a testable condition for it,
   or someone withdraws it and logs a `WITHDRAWN` line naming who withdrew it and why. Calling it
   "not live" without that line does not clear it.
4. Do NOT gather evidence yet. Every roster option has a committed kill condition or a logged
   withdrawal → log `DONE`, first run complete. Any roster option still `UNRESOLVED` → `BLOCK`,
   not `DONE`.

**Every later run (weekly, or on demand):**
1. Read the state file — the roster and the kill conditions already committed to. Re-check the
   completeness invariant first: any roster option that is `UNRESOLVED` and not withdrawn blocks
   any recommendation this run. Log `BLOCK` and say which option is holding it.
2. For each surviving option, hunt ONLY for evidence that the kill condition has triggered.
   Supporting/positive evidence is not the job here and doesn't get logged as progress.
3. An option whose kill condition is confirmed true → dead. Log it, cite the confirming fact.
   **No resurrection without a new fact** — a re-read of the same data doesn't count.
4. If exactly one option survives after a real hunt, and no roster option is `UNRESOLVED` →
   recommend it. The case FOR it is that it survived a genuine attempt to kill it, not a score.
   An `UNRESOLVED` option never counts as a survivor; if it is the only one left, say the decision
   is unresolved and recommend nothing.
5. If multiple options survive → `PASS`, log it, continue next cycle. Multiple survivors is a
   valid, expected outcome — it means "not disqualified yet," not "tied, pick one."
6. If all options die → say so plainly and propose a reframe (the decision as posed was wrong).
   Do not force a pick among dead options.

## Relation to a scoring pipeline

If your project also runs a numeric scoring process for the same kind of decision, that score and
this skill's kill condition answer different questions — score is "how good is this," kill
condition is "what would mean not this, regardless of score." Both are useful; neither replaces
the other. This skill does not touch a scoring pipeline — it's an added pre-commit check, not a
modification to it.
