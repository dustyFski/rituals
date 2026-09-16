---
name: handoff
description: Write a self-contained mid-task handoff file so work can resume in a fresh context window or a different agent with zero conversation access. Fires on "/handoff", "prepare a handoff", "write a handoff", "we need to clear context", "hand this to another agent", or when context is nearly full mid-task. NOT for session close — that is a separate wrap/close ritual. Handoff transfers live work; a session-close skill closes finished work.
---

**What it does:** Writes a template-driven handoff file capturing state, decisions, gotchas, blockers, and next actions so a fresh reader can resume with zero conversation access.
**When it fires:** "/handoff", "prepare a handoff", "write a handoff", "we need to clear context", "hand this to another agent", or when context is nearly full mid-task.
**Config:** handoff file location — see "Where the file goes" below; no other config.

# Handoff — Mid-Task Context Transfer

A handoff is written for a reader with ZERO access to this conversation. The test: could a fresh agent resume in under 5 minutes without asking a single question? Everything it would have to ask for goes in the file.

## When this fires vs a session-close ritual

- Work is UNFINISHED and continues immediately (fresh context, another agent, another machine) → this skill.
- Session is CLOSING and work is done or parked → your project's session-close skill instead, if it has one. If both apply (closing a session mid-task), write the handoff first, then run session close; the close step references the handoff file.

## Where the file goes

- Project or tool work → `<project-or-tool>/tasks/HANDOFF-YYYY-MM-DD-<slug>.md`
- Cross-cutting or ops work → `<repo-root>/ops/handoffs/HANDOFF-YYYY-MM-DD-<slug>.md`
- Non-repo work → the working directory root, same filename.
- When a HANDOFF file for the same task already exists, update it in place — never fork a second one for the same task.

## Procedure

1. **Verify before you claim.** When you are about to write "done" next to any item, verify it first (run the test, check the file, `git status`) — never transcribe your own optimism.
2. **Capture uncommitted state explicitly.** Run `git status` in every repo touched; list dirty/untracked files by path in the file. An uncommitted edit that isn't named in the handoff is lost work.
   For a handoff to another machine, dirty work must travel, not just be named. Produce a transfer artifact and record where the successor can fetch it:
   - `git diff --binary HEAD > transfer.patch` for the tracked working state. `HEAD` is required: a plain `git diff` shows unstaged changes only and silently drops everything already staged.
   - `git ls-files --others --exclude-standard | tar -czf untracked.tgz -T -` for the untracked files, which no diff carries.

   Record the base commit the patch applies to. Before you mark cross-machine readiness READY, verify the reconstruction: check out that base commit in a scratch clone, apply the patch, unpack the tarball, and confirm the result matches. If the successor must use this same worktree, say so and mark cross-machine readiness BLOCKED until the transfer is verified.
3. **Write the file** with the template below. Use complete sentences and full paths — no conversation shorthand, no labels invented mid-session, no "as discussed".
4. **Scrub secrets.** Record locations, never values.
5. **Point the successor at it.** End your reply with the file path and the one-line resume instruction (e.g. "start by reading tasks/HANDOFF-....md, then do Next-action 1").

## Template

```markdown
# HANDOFF — <task> — <date>
**Audience:** <fresh Claude context / another agent or a fresh session / subagent>
**Goal & done-when:** <the pinned goal and its testable completion criteria>

## Repository
- Repo: <name and remote URL> — branch: <branch> — base commit: <sha>
- Source root here: <absolute path> — maps to: <path on the successor's machine, or "same worktree required">
- Transfer artifact: <path or URL of the diff/tarball, and how to apply it — or "none needed, tree is clean">
- Cross-machine ready: <yes / BLOCKED until transfer verified>

## State
- DONE + verified: <item — how it was verified>
- DONE, unverified: <item — what would verify it>
- IN FLIGHT: <item — exactly where it stopped, mid-file if needed>
- NOT STARTED: <item>
- Uncommitted: <repo: files>

## Key files
<full path — one line on what/why it matters>

## Decisions made (and why)
<decision — rationale — recorded where>

## Gotchas / tacit context
<anything true that is NOT discoverable from the files: quirks hit, env facts, which approach already failed and why it must not be retried>

## Blockers
<blocker — what unblocks it, or "none">

## Next actions (ordered, start-ready)
1. <specific enough to begin immediately>

## Verify
<commands or checks that prove the resumed work still holds>
```

## Rules

- When an item's status is uncertain, write it as uncertain — a wrong "done" in a handoff poisons the successor's whole run.
- When an approach was tried and rejected, record it under Gotchas with the reason; the successor must not re-derive the dead end.
- When handing to a different agent, scope the file list to only what it needs and state its write boundaries explicitly.
- When the task has a governing doc (plan, spec, gate register), link it under Key files rather than restating it.

- When writing a handoff, never include secret values — only their locations.
- Never trust a background agent's self-reported status. Check its job ID via an accessible status mechanism or its artifact; otherwise mark the completion unverified.
- When the handoff covers content mid a publishing pipeline, state which safety/compliance gates have and have not run — a successor publishing ungated content is a risk event.
