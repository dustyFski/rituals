---
name: wrap
description: "Session close ritual. Reconstructs what the session touched, walks a checklist item by item, runs an adversarial review gate on the code, updates STATE.md, saves durable memory, and prints a report that names everything it skipped."
user-invocable: true
---

# wrap — session close ritual

**What it does:** closes a work session with evidence. Every step writes down what it
checked, and the final report names what it could not do.

**When it fires:** `/wrap`, "wrap up", "close the session", "end of session".

**Config** (environment variables, all optional):

| Name | Default | Meaning |
|---|---|---|
| `REVIEWER_CMD` | unset | Adversarial review command. Contract in the repo README. |
| `NOTIFY_CMD` | unset | Command that receives the final report on stdin. |

Run the six steps in order. Do not reorder them. Do not skip silently.

---

## Step 1 — Reconstruct the session

Record the session's starting commit as the baseline. Use the commit the session opened on,
or `git rev-parse HEAD` when nothing was committed yet.

Define ONE session change set and reuse it in every later step:

- unstaged changes (`git diff`)
- staged changes (`git diff --cached`)
- untracked files (`git status --short`, ignore rules respected)
- commits made this session, as both an endpoint diff and a per-commit history:
  `git diff <baseline>..HEAD` for the endpoint, and `git log -p -m <baseline>..HEAD` for every
  commit's own patch (`-m` so merge commits show their changes too)

Both components are needed: the endpoint diff is the compact payload a reviewer reads, while the
per-commit patches are the only place a secret committed and then reverted inside this session
still appears.

Read the conversation too. List every file touched and every decision taken. Name any file
whose contents could not be included, for example a binary blob or an unreadable path.

**Done when:** the baseline commit is written down, the change set is listed, and the
decision list exists. A file in `git status` that you cannot explain is a finding, not noise.

## Step 2 — Checklist

Read `checklists/default.md` in this skill directory. If `.claude/wrap-checklist.md`
exists in the project, read that instead. The project file overrides; it does not merge.

Walk every item. Mark each PASS, FAIL, or N-A with one line of evidence. Evidence is a
command output, a file path, or a quoted line. "Looks fine" is not evidence.

Severity tiers, applied to every FAIL:

| Tier | Meaning |
|---|---|
| BLOCKER | Stop. Fix before the session closes. |
| WARNING | Fix this session. Do not carry it forward. |
| HOUSEKEEPING | Next session is fine. Record it in STATE.md. |

**Done when:** every item has a mark and a line of evidence.

## Step 3 — Adversarial gate

Run `REVIEWER_CMD` on the session change set from step 1, not on `git diff` alone. Transport
is stdin only: pipe that payload to its stdin and read the verdict from stdout. List any file
left out of the payload.

The reviewer's first stdout line is exactly `PASS` or `BLOCK`, and the verdict applies to the
work under review. Each following line is one finding, formatted
`<severity> | <owner or n/a> | <one-line finding>`.

A non-zero exit, empty output, or a first line that is neither `PASS` nor `BLOCK` means no
review happened. Never read any of them as a pass. If `REVIEWER_CMD` is unset, the gate is
skipped and the report says `REVIEWER SKIPPED` in capitals. A native fresh-subagent review
counts only when `REVIEWER_CMD` is unset AND the skill documents that fallback; wrap and cascade
do not, they SKIP.

On `BLOCK`: fix the valid findings, re-run the reviewer once. If it blocks again, stop
and report both verdicts. Do not run a third pass.

Any edit made in this step invalidates earlier evidence. Rerun the checklist items the edit
affects, then record the tree identity both the checklist evidence and the final reviewer
verdict were taken against. Build it from a temporary index, so untracked files are included.
`git stash create` skips untracked files, so it can hash a tree that omits reviewed code.

```bash
TMPIDX=$(mktemp)
GIT_INDEX_FILE="$TMPIDX" git read-tree HEAD
GIT_INDEX_FILE="$TMPIDX" git add -A       # honours .gitignore; picks up untracked files
TREE=$(GIT_INDEX_FILE="$TMPIDX" git write-tree)
rm -f "$TMPIDX"
echo "$TREE"
```

`GIT_INDEX_FILE` is set per command, so the real index is untouched. Record `TREE` in the
report. The report must show one identity, not two.

**Done when:** the report holds a verdict plus the tree identity, or the capitalised skip line.

## Step 4 — STATE.md

Update `<project>/STATE.md`. Create it if it is missing. Four headings:

- **Current state** — what works right now.
- **Open items** — each with what unblocks it.
- **Decisions this session** — what was decided and why.
- **Next step** — specific enough to start cold.

Append one row to the history table: date, what changed, verified how.

**Done when:** the four headings hold this session's content and the table has a new row.

## Step 5 — Memory

On Claude Code, save durable facts to the auto-memory directory for this project and add
each new file to the memory index. Check the index first and update an existing file rather
than creating a duplicate. On an agent without a memory directory, skip this step and put
the line `memory: unsupported here, skipped` in the report.

Save only what the repo cannot tell you: a preference, an external constraint, a decision
and its reason. Do not save code patterns, bug fixes, or session state.

**Done when:** each saved fact has a file, or the report says no memory was written.

## Step 6 — Report

Print to the terminal and write `.wrap/last-report.md`:

- Baseline commit and the tree identity the evidence was taken against.
- Files touched, plus any file the reviewer payload could not include.
- Checklist path used, then every item: ID, status, one line of evidence, and the reason for
  each N-A or skip. Counts come first; FAIL lines appear in full.
- Reviewer verdict, or `REVIEWER SKIPPED`.
- STATE.md diff summary.
- Memory saved, or `memory: unsupported here, skipped`.
- `Skipped:` — a final line, never empty. Write "nothing" only if truly nothing.

If the ritual stops early, write the report with the evidence already collected. Never
discard completed items.

If `NOTIFY_CMD` is set, pipe the report to it. A non-zero exit or an error is recorded in the
report as a delivery failure. It does not block the session from closing.

---

## Rules

- Steps 2, 3 and 6 cannot be skipped silently. Skipping one puts a line in the report.
- A FAIL in step 2 or a BLOCK in step 3 is reported. Never hide either.
- The ritual never commits and never pushes unless the user asks.
- `NOTIFY_CMD` is the only report-delivery hook. `REVIEWER_CMD` may send source to its
  configured provider. Use a local reviewer when source must not leave the machine.

## Anti-rationalization

| The thought | The answer |
|---|---|
| "Small change, skip the checklist." | Small changes are where the checklist earns its keep. |
| "The reviewer is slow, I read the diff myself." | The agent that wrote the change cannot be its only judge. |
| "Reviewer errored, close enough to a pass." | An error is no review. Report it as skipped. |
| "STATE.md is stale anyway." | Then this session fixes it. A stale file starts the next session blind. |
| "Nothing worth reporting." | Then the report is short. It is still written. |
