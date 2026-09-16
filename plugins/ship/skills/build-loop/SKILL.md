---
name: build-loop
description: "Structured discuss-plan-build-verify loop for a software project; enforces the discuss-before-build discipline that prevents rework loops. Fires when starting any build session on a project — 'build', 'work on/fix/ship [project]', 'next on [project]', 'discuss phase', 'gray areas', 'lock decisions', or any development, content, or deployment request on a specific project."
---

**What it does:** Runs every build session through four phases (orient, discuss, build, verify) so decisions get locked before code changes, and state gets written down before the session ends.
**When it fires:** Starting a work session on a project; fixing bugs; creating content; deploying or configuring infrastructure; any request touching a specific project's files.
**Config:** `STATE_FILE` (default `tasks/STATE.md`) — cross-session memory. `DECISIONS_FILE` (default `docs/DECISIONS.md`) — locked decisions + open gray areas. `ROOT_DOC` (default the project's root `CLAUDE.md` or `README.md`) — status, design decisions, folder structure. `BRAND_GUIDE` (default none) — voice/tone file for customer-facing work. `TECH_STACK_DOC` (default none) — portfolio/org standard to check before adding a new tool or service. `CHECKLIST_FILE` (default none) — extra project checks, added to the baseline checklist in the VERIFY phase. `KEY_MAP_DOC` (default none) — where to record which API key belongs to which project, if the Credentials Gate applies. `REVIEWER_CMD` (default none) — the adversarial review command run on the diff in VERIFY. See the reviewer contract below.

# Build Loop Workflow

A structured workflow for building software projects. Adapted from GSD's discuss → plan → execute → verify pattern, simplified for a solo builder using AI-assisted tools.

The core insight: **resolve design decisions before building, build in focused sessions, verify before declaring done, and always update state for the next session.**

---

## When This Skill Triggers

Any time the user wants to do build, content, or deployment work on a specific project. This includes:

- Starting a new work session on a project
- Fixing bugs or issues
- Creating content (articles, emails, social posts)
- Deploying or configuring infrastructure
- Any request that touches the project's own files

---

## Progress reporting (cmux — best-effort, never affects logic)

If running inside cmux, surface phase progress in the workspace sidebar via the self-guarding
helper (`cmux-report`, from the `cmux` skill). It **silently no-ops and exits 0 whenever it is
not inside cmux** (plain terminal, remote host, subagent), so it never changes the workflow.
Fire-and-forget — never wait on it.

Check the helper exists before calling it (`command -v cmux-report`). If it is absent, skip
every line below and carry on; progress reporting is never a gate.

At the start of each phase, bump the bar; on Session Close, finish and notify:

- Phase 1 ORIENT: `cmux-report status project <name>` then `cmux-report progress 0.1 "ORIENT — <project>"`
- Phase 2 DISCUSS: `cmux-report progress 0.35 "DISCUSS — locking decisions"`
- Phase 3 BUILD: `cmux-report progress 0.6 "BUILD — <what's being built>"`
- Phase 4 VERIFY: `cmux-report progress 0.85 "VERIFY"`
- Session Close: `cmux-report progress 1.0 "Session done"` then
  `cmux-report notify "build-loop: <project>" "<one line of what shipped>"`

---

## The Four Phases

### Phase 1: ORIENT (2-3 minutes)

Load context. Every session starts here — no exceptions.

1. Read the project's root doc (`ROOT_DOC`) — status, design decisions, folder structure
2. Read `STATE_FILE` (what happened last session, what's blocked, what's next)
3. Read `DECISIONS_FILE` (locked decisions + unresolved gray areas)
4. Read `BRAND_GUIDE` if set and doing any customer-facing work
5. Record the starting commit as `BASE`: `BASE=$(git rev-parse HEAD)`. Note it in the session
   summary. VERIFY diffs against it, so the evidence survives the commits made in BUILD.

**First run:** if `STATE_FILE` or `DECISIONS_FILE` does not exist, create it before reading on.
Create `STATE_FILE` with the headings `## Last Session`, `### What Got Done`, `### Decisions Made`,
`### What's Blocked`, `### What's Next (Priority Order)`, and a `## Session History` table whose
header row is `| Date | Focus | Outcome |`. Create `DECISIONS_FILE` with the headings
`## Locked Decisions` and `## Open Gray Areas`. Say you created them, then treat this session as
session one rather than reporting an empty history as "nothing happened".

After reading, give the user a 3-line summary:
- **Last session:** [one line from STATE_FILE]
- **Blocked:** [blockers, or "nothing blocked"]
- **Recommended next action:** [top priority from STATE_FILE's "What's Next"]

Then ask: "Does this match what you want to work on, or do you have something else in mind?"

### Phase 2: DISCUSS (5-15 minutes)

Resolve gray areas before building. This is the step most people skip — and where most rework comes from.

1. Check `DECISIONS_FILE` for any OPEN gray areas relevant to today's work
2. If gray areas exist that affect today's build:
   - Present each one with options
   - Ask the user to pick (or suggest a recommendation)
   - Lock the decision in `DECISIONS_FILE` with date and rationale
3. If the user's request involves something NOT yet in `DECISIONS_FILE`:
   - Identify what design questions need answering
   - Present them as gray areas
   - Resolve before building
4. If no gray areas affect today's work → skip to Phase 3

The goal: **every decision is locked before a single file is created or modified.**

Gray areas to always check for:
- Where does this live? (which folder, which file, which platform)
- What does "done" look like? (specific success criteria)
- What existing decisions does this depend on? (check `DECISIONS_FILE`)
- Does this touch anything customer-facing? (if yes, voice/tone/legal checks apply)
- Does this introduce a new tool or service? (if yes, check `TECH_STACK_DOC`, when set, for a portfolio/org standard first — use the standard unless there's a documented reason to deviate)
- Does this project call a paid API (an LLM provider or any other metered service)? (if yes → the **Credentials & API Keys Gate** in Phase 3 applies)

### Phase 3: BUILD (main work session)

Execute the actual work. Keep it focused.

**Before starting:**
- State what you're going to do in 1-2 sentences
- Confirm the user is aligned

**During build:**
- For parallel work, use subagents. Each agent gets only what it needs — see the subagent context budget table below.
- For customer-facing content: read the voice/brand files first
- Web-search validate all facts, prices, and market claims
- Never use advisory language ("you should", "we recommend") if the project is an information tool, not an advice tool
- Commit atomic pieces of work. Don't try to do everything in one giant pass.

**Credentials & API Keys Gate (MANDATORY when the project calls a paid API):**

Decide the auth model BEFORE wiring any key. Default order:

1. **Can the code shell out to an authenticated CLI you already pay a flat rate for?** (CLI tools, cron jobs, batch/bootstrap scripts — anything running on your own machine or server, not in a request handler) → prefer that over a metered key. There is no per-call charge when the CLI is authenticated by subscription; confirm that before relying on it.
2. **Is it a serverless/runtime that CAN'T run the CLI?** (platform route handlers, mid-request processing, a third-party host, or work needing parallelism beyond the flat-rate seat's limits) → a raw **API key is justified**. Then, no exceptions:
   - Give the project its **OWN API key/workspace.** Never reuse a shared personal key or another project's key. One project = one key = one cost line + one spend cap + clean blast radius. This is the whole point — per-project cost attribution and rotation isolation.
   - Set a **monthly spend cap** on the workspace as a runaway backstop.
   - Wire it through the **platform secret store only**: your host's project env vars, a server-side secrets file, or a gitignored `.env.local`. **NEVER hardcode a key in source. NEVER commit one.** (A committed key lives in git history forever — rotation, not deletion, is the only fix.)
   - Record the key → project mapping in `KEY_MAP_DOC`, if set.

**Subagent context budget:**

| Task Type | What the Subagent Gets |
|-----------|----------------------|
| Build (HTML, code, deploy) | Project root doc + `DECISIONS_FILE` + specific build files |
| Content (articles, social, email) | Voice files + brand guide + topic brief |
| Brand/design | Brand guide file(s) |
| Research | Project root doc + web search (nearly stateless) |
| Legal review | Legal reference doc(s) + project root doc |

### Phase 4: VERIFY (5-10 minutes)

Never declare done without checking.

**Baseline verification checklist (never optional, runs on every build session):**

1. The build passes. Discover the project's build command and run it, then show the exit status.
   If the project has no build command, record an evidenced N/A (say where you looked) and run the
   content-specific validation instead, such as a link check, a schema check, or the seo-content scorer.
2. The tests pass. Discover the project's test command and run it, then show the summary line.
   If the project has no test command, record an evidenced N/A the same way and run the
   content-specific validation instead. Checks 3 to 5 stay mandatory in every project.
3. Secret grep on the session's work returns nothing:
   `git diff -U0 "$BASE" | grep -nEi '(api[_-]?key|secret|token|password|bearer|sk-[a-z0-9]{8,})'`
   `git diff "$BASE"` compares the worktree against the ORIENT commit, so it covers staged,
   unstaged, and already-committed work. Grep each intended new untracked file as well.
   Any hit stops the session until it is explained or removed.
4. No server-side secret reached the client. Grep the same diff for the framework's public env
   prefix (for example `NEXT_PUBLIC_`, `VITE_`, `REACT_APP_`) next to any credential name.
5. Manually smoke the path you changed. Open it, click it, run it. Say which path you exercised.

`CHECKLIST_FILE`, when set, adds project checks on top of these five. It never replaces them.

**For build work:**
- Does it render/work correctly? (test in browser if applicable)
- Does it match the locked decisions in `DECISIONS_FILE`?
- Are all paths and references valid?

**For content:**
- Does it match the brand voice? (`BRAND_GUIDE`, if set)
- Would the intended audience find this useful?
- Are facts web-search validated?
- Are disclaimers present on anything customer-facing?
- No advisory language, if this is meant to be an information tool?

**For deployment:**
- Is the deploy URL accessible?
- Does it work on mobile?
- Are there console errors?

**For credentials (if the project calls a paid API):**
- Is it on the project's OWN key, not a shared personal key? (compare the last-4 against the provider console)
- Is the key in the platform secret store, never hardcoded? (a source grep for the key prefix returns nothing in tracked source)
- Is a monthly spend cap set on the workspace?
- Do baseline checks 3 and 4 pass (no key in a client-exposed file or a public-prefixed env var)?

**Billing mode (any session that invokes a provider CLI):**

Confirm which credential the CLI will use before invoking it. If an API key env var is set and a
subscription login also exists, unset the key for that invocation so the flat-rate seat is used.
Record which mode was used. Silence here is how a flat-rate session quietly bills metered.

**Adversarial review (`REVIEWER_CMD`, when set):**

Build the payload from `git diff "$BASE"` plus the intended untracked files, then pipe it on
stdin: `{ git diff "$BASE"; cat <intended-new-files>; } | $REVIEWER_CMD`. Check the payload first.
An empty payload is always an error to investigate, never a pass: fix the base or the file list,
and do not invoke the reviewer until the payload holds the changes under review. Transport is stdin only. The reviewer's
FIRST line is exactly `PASS` or `BLOCK`. Following lines are findings, one per line, formatted
`<severity> | <owner or n/a> | <one-line finding>`. A first line that is neither `PASS` nor `BLOCK`
is malformed and counts as no review. A non-zero exit or empty stdout is also no review, never a
pass. `BLOCK` applies to the work under review: fix the findings and re-run before declaring done.

After verification, tell the user what was checked and what passed/failed.

---

## Session Close (MANDATORY)

At the end of every work session — no matter how small — update `STATE_FILE`:

```markdown
## Last Session

**Date:** [today]
**Duration:** ~[estimate]
**Focus:** [one line]

### What Got Done
- [concrete deliverables]

### Decisions Made
- [any decisions] → recorded in DECISIONS_FILE? Y/N

### What's Blocked
- [blockers] → [what unblocks them]

### What's Next (Priority Order)
1. [most important]
2. [second]
3. [third]
```

Also append to the Session History table at the bottom of `STATE_FILE`.

If any decisions were made during the session, add them to `DECISIONS_FILE` with date, rationale, and impact.

If the project's status changed, update the project's root doc (Current Status section), and any higher-level dashboard doc that tracks it.

---

## Anti-Patterns to Avoid

- **Building before discussing:** If you catch yourself creating files without having checked `DECISIONS_FILE` for gray areas, stop and go back to Phase 2.
- **Skipping session close:** The few-minute `STATE_FILE` update saves far more time at the start of the next session. Always do it.
- **Overloading subagents:** Each subagent gets only its task-specific context. Don't dump the entire project into it.
- **Vague "done":** "Worked on the landing page" is not a state entry. "Fixed iframe height, added responsive CSS, verified on desktop" is.
- **Ignoring blockers:** If something is blocked, say so in `STATE_FILE`. Don't silently skip it.
