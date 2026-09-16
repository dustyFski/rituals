---
name: proof-toolkit
description: "Five prove-it-don't-eyeball recipes for claiming a change is correct — refute-by-default review, rederive-from-source, phantom-claim detection, blind A/B, held-out validation. Load before asserting \"this works / this is fixed / safe to ship\" when you need the evidence method."
allowed-tools: Read, Bash
---

**What it does:** Gives five falsification recipes for turning "I think this works" into "here is
what would have proven it wrong, and it didn't."
**When it fires:** Before asserting a fix, verdict, or change is safe to ship — trigger phrases like
"this works," "this is fixed," "safe to ship," or any request to prove a claim rather than assert it.
**Config:** `REVIEWER_CMD` — the adversarial-review command this project uses for recipe 1 (default:
none; must be set per project). It reads the evidence on stdin, and its first line is exactly `PASS`
or `BLOCK`; recipe 1 carries the full contract. `RERUN_SELFTEST_CMD` — the
project's rederive/self-test entry point for recipe 2 (default: none; use the pipeline's own
`--selftest` flag or equivalent). `PHANTOM_CHECK_CMD` — the phantom-claim / reality-check script for
recipe 3 (default: none). `SHADOW_STATE_FILE` — path to the blind-A/B run log for recipe 4 (default:
none; see the `shadow` skill). `HELD_OUT_SPEC_FILE` — path to the held-out validation contract for
recipe 5 (default: none).

# proof-toolkit

Five recipes for turning "I think this works" into "here is what would have proven it wrong, and
it didn't." Pick by what you're trying to falsify. Full command flags, decorrelation rationale, and
a worked example per recipe: `references/recipes.md`.

## The one rule above all five

**Empty evidence is a FINDING, not a PASS.** A reviewer that returns nothing, a script that finds
zero of anything, a check that silently no-ops — treat as "this check did not run," not as
"everything is fine." This is the skill's imposed posture. An adversarial review command may say so
in its own output, or refuse to run on empty input with a neutral message and a non-zero exit code.
Same effect, different wording. Apply the posture to every recipe below whichever convention a given
tool uses.

## The five recipes

| Recipe | Proves | Reach for it when | Tool |
|---|---|---|---|
| Refute-by-default adversarial | A verdict/fix survives someone actively trying to kill it | Before shipping anything high-stakes (money, production, security) or reversing a prior verdict | `REVIEWER_CMD` — a decorrelated adversarial review command, evidence on stdin, first line `PASS` or `BLOCK` |
| Rederive-from-source self-test | A pipeline's output is actually derived from its stated inputs, not stale/cached/hand-edited | Before trusting a derived-data file that a live surface reads | The pipeline's own `--selftest` (or equivalent) entry point |
| Phantom-claim detection | An agent's "I did X" claim is real, not a silent no-op or a rewritten result file | After any unattended agent run, before trusting its result markdown | `PHANTOM_CHECK_CMD` — a deterministic file/git-based verifier |
| Blind A/B | A candidate is actually better, not just different, with human judgment uncontaminated by labels | Comparing a candidate model/prompt against a pinned production one | `shadow` skill + a per-target state log |
| Held-out validation | An edit is a strict improvement on data the optimizer never saw, not overfit to what it was scored on | Any loop that edits based on a score (gated-edit / optimizer loops) | A written held-out acceptance spec (`HELD_OUT_SPEC_FILE`) |

A clean result is only as strong as what it tried to falsify — state what would have shown up if
the thing were actually broken. A PASS with no falsification story is not proof, it's a shrug.

## Decorrelation rule (adversarial review only)

Use a **decorrelated, cross-family** second opinion — a reviewer built on a different model family
than the one that produced the work under review. A same-family check (a model reviewing its own
family's work) is not independent and doesn't count as adversarial verification. Same-family review
is a fallback of last resort, never the default.

This rule governs recipe 1 only. It does not apply to blind A/B, where candidate and production may
share a lab; what a blind A/B decorrelates is the grader's expectation, not the model lineage.

## When candidate and production agree in a blind A/B

Discard it as noise — it carries no signal. Only disagreements get queued for a human blind grade.
See the `shadow` skill for the full procedure; this toolkit only covers the proof logic.

<!-- PROTECTED — do not edit. Incident-derived + standing hard rules. -->
- When an adversarial check returns empty evidence, treat it as a FINDING, not a PASS.
- Use a decorrelated, cross-family reviewer for a second opinion — a same-family check is not independent.
- When candidate and production agree in a blind A/B, discard it as noise; only disagreements carry signal.
- A phantom-claim verifier only asserts CONTRADICTED when the evidence definitively refutes the claim; when it can't prove a claim false it returns UNVERIFIED, never a false phantom.
<!-- END PROTECTED -->

## Maintenance

Re-verify each recipe's tooling is still present and runnable before trusting this skill's command
examples in a new project — full worked examples, exact CLI flags, and decorrelation rationale per
recipe live in `references/recipes.md`.
