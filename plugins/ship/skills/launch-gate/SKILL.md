---
name: launch-gate
description: "Walks a project through a phased launch checklist as a gated, resumable run covering domain, email, analytics, hosting, cross-sell, docs, and verification. Most phases need a human at a keyboard for third-party dashboard clicks; this skill sequences and verifies, it does not click through those UIs for you."
allowed-tools: Read, Edit, Write, Bash, AskUserQuestion
---

**What it does:** Walks one project through a 10-phase launch checklist (domain, email, analytics, hosting, distribution, docs, verification), tracking progress in a resumable file so the checklist isn't re-read from scratch every session.
**When it fires:** `/launch-gate <project>` or `/launch-gate <project> --resume`.
**Config:** `CHECKLIST_PATH` (default: none) — a project checklist that overrides the bundled default. When unset, the skill walks `checklist.md` in this skill's own directory, and uses the project's `docs/LAUNCH-CHECKLIST.md` instead when that file exists. `TECH_STACK_PATH` (default: `docs/TECH-STACK.md`, optional) — hosting decision guide. `PROJECTS_DIR` (default: `projects/`) — where project folders live. Progress file (default: `docs/LAUNCH-PROGRESS.md` inside the project folder) — this skill's own resumability record.

# Launch Gate

Drives a project's launch checklist phase-by-phase, so the checklist doesn't get re-read cold on every launch.

**Which checklist:** resolve it once, in this order. Use `CHECKLIST_PATH` if set. Otherwise use `{PROJECT-ROOT}/docs/LAUNCH-CHECKLIST.md` if that file exists. Otherwise use `checklist.md` in this skill's own directory, which ships with the skill and is always present.

**What this skill does and does not do:** most of the checklist's 10 phases involve manual clicks in a domain registrar, DNS provider, hosting platform, or email dashboard — no scriptable access exists for several of them (domain purchase, nameserver assignment, SMTP "Send As" setup). This skill does NOT attempt those clicks. It sequences the work, tells you exactly what to click and where, verifies what CAN be checked programmatically (DNS records via `dig`, site reachability via `curl`, deploy and analytics state via the hosting provider's CLI, API, or dashboard), and keeps a resumable progress record so a launch spanning multiple sessions doesn't restart from Phase 1 every time.

**Ship-gate note:** this skill never invokes a project's deploy script and never sets an env var that would satisfy one. If a phase would otherwise require running the deploy script, it stops and tells you to run it yourself.

**Commit path:** any commit this skill makes (progress file, doc updates) should go through this repo's designated commit wrapper if one exists — never a raw `git add -A`.

## Step 1 — Parse arguments

`/launch-gate [project-name] [--resume]`

- **PROJECT** = the project's folder name under `PROJECTS_DIR` (kebab-case, e.g. `acme-docs`).
- **PROJECT-ROOT** = `{PROJECTS_DIR}/{PROJECT}`. Resolve it once here, then use it for every later file read and write in this skill. Every `{PROJECT}/...` path below means `{PROJECT-ROOT}/...`.
- `--resume` is accepted but not required — Step 3 always checks for existing progress first regardless of the flag; it exists only so the invocation reads naturally.

If PROJECT doesn't match a folder under `PROJECTS_DIR`, list the folders that do exist and ask which one via AskUserQuestion — don't guess a close match.

## Step 2 — Load context

Read, in order:
1. The resolved checklist (see "Which checklist" above) — the 10 phases this skill walks. If a project checklist replaces the default, re-sync this skill's phase list against it rather than forking it.
2. `TECH_STACK_PATH`, if configured (hosting decision guide — e.g. static host vs. managed platform branch)
3. `{PROJECT}/CLAUDE.md` or the project's equivalent status file (current status, domain if already known)
4. `{PROJECT}/docs/DECISIONS.md` if it exists (DNS/email/analytics decisions already locked — don't re-litigate them)
5. `{PROJECT}/STATE.md` or the project's equivalent session-state file, if it exists (last session's context — a launch spans sessions, and this is the standing cross-session memory file for the project)
6. `{PROJECT}/docs/LAUNCH-PROGRESS.md` if it exists — this is this skill's own resumability record, specific to the launch sequence (Step 3)

## Step 3 — Resume or start

If `LAUNCH-PROGRESS.md` exists: report which phases are checked off, which is next, and any `BLOCKED` lines. Ask (AskUserQuestion): continue from the next unchecked phase, jump to a specific phase, or re-verify a phase marked done. Do not silently restart from Phase 1.

If it doesn't exist: create it from this template and start at Phase 1.

```markdown
# Launch Progress — {PROJECT}

Started: {date}. Checklist version this run is against: see the checklist's Changelog date
at time of this run.

## Phases
- [ ] Phase 1: Domain
- [ ] Phase 2: Email Routing
- [ ] Phase 3: Email Authentication
- [ ] Phase 4: Email Send-As Setup
- [ ] Phase 5: Analytics
- [ ] Phase 6: Hosting & Deploy
- [ ] Phase 7: Keep-Alive (if applicable)
- [ ] Phase 8: Cross-Sell & Distribution
- [ ] Phase 9: Documentation
- [ ] Phase 10: Verification

## Blocked
<!-- BLOCKED lines: phase, what's needed, from whom -->

## Session log
<!-- one line per work session: date, phases advanced, what verified -->
```

## Step 4 — Walk each phase

For each unchecked phase, in order (skip Phase 7 if the project uses no free-tier
auto-pausing service — say so and check it off with a one-line reason rather than leaving
it blank):

1. **State the phase's checklist items verbatim** from the resolved checklist —
   don't paraphrase the DNS records or SPF/DMARC strings, copy them exactly (a typo'd TXT
   record is a silent failure, not a cosmetic one).
2. **Classify each item:**
   - **Human-manual** (domain purchase, DNS/registrar/hosting dashboard clicks, email
     Send-As setup, payment-provider dashboard config) — present as a numbered action list,
     then STOP and ask (AskUserQuestion) whether it's done. Do not proceed past an
     unconfirmed manual item in the same phase.
   - **Claude-verifiable** (DNS propagation via `dig +short` or `nslookup -type=TXT`, site
     reachability via `curl -sI`, git repo to hosting project linkage, analytics pageview
     check via the hosting provider's CLI, API, or dashboard, file-based doc updates) — do
     these directly, show the actual command output as evidence, not "should be working
     now." Where only a dashboard can answer, a screenshot or pasted dashboard output is
     accepted evidence; record which one you used.
   - **Claude-writable docs** (status-file status line, DECISIONS.md entries, STATE.md
     launch session, portfolio dashboard row, tech-stack doc additions) — write these
     directly per Phase 9's own checklist items, using the project's existing file
     conventions.
3. **Check off the box in `LAUNCH-PROGRESS.md`** only under this rule, never on "should be
   fine": a human-manual item whose outcome is command-verifiable (DNS/SPF/DMARC records,
   redirects, site reachability, hosting project linkage) is checked off ONLY after you
   confirm the clicks were done AND the verifying command actually passes — confirmation
   alone never closes it, since a typo'd record is exactly the silent failure this skill
   exists to catch (see the anti-rationalization table). Items with no verifiable outcome
   (e.g. email Send-As, which only a real send/reply test proves and that's itself listed
   as a Phase 10 item) close on confirmation alone, since there's nothing else to check.
4. **If an item can't be completed this session** (waiting on DNS propagation, waiting on
   a person), write a `BLOCKED` line in the progress file (what's needed, from whom) and
   stop the walk there — don't skip ahead to a later phase out of order; later phases often
   depend on earlier ones actually being live (e.g., Phase 6 hosting needs Phase 1's DNS to
   have propagated).

## Step 5 — Close the run

When all 10 phases are checked (or explicitly N/A with a reason):
1. Run Phase 10's verification block for real — actually curl the domain, actually check
   the TXT records, actually read analytics from the hosting provider's CLI, API, or
   dashboard. Report each check's real result, and paste the evidence you used.
2. Append a Session log line to `LAUNCH-PROGRESS.md`.
3. Remind: run the project's own verification/consistency check, if one exists — this
   skill does the launch-specific checks; a general check covers cross-file consistency.
4. If this is a first launch (the portfolio dashboard, if one exists, still shows the
   project as pre-launch), flag that the dashboard needs a status update — don't silently
   leave it stale.

## Anti-rationalization

| Excuse | Rebuttal |
|---|---|
| "DNS probably propagated by now, skip the dig check." | `dig +short` takes one call. A stale check-mark on an unpropagated record is exactly the failure this skill exists to prevent — the checklist's own Phase 10 exists because "should be fine" was the old failure mode. |
| "They said they'd do the registrar steps later, mark it done anyway to keep moving." | Mark it BLOCKED, not done. A false checkmark means the NEXT session (possibly weeks later) assumes DNS is live when it isn't. |
| "This project doesn't need Phase 7, skip silently." | Check it off with a one-line reason ("no free-tier auto-pausing service used"). A blank unchecked box and a deliberate skip look identical without the reason. |
| "I can just run the deploy script myself to save a step." | Ship-gate rule: no autonomous agent invokes a deploy script, ever, regardless of how close to done the launch is. |
