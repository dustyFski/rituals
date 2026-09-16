# Reviewer options for the gate

The gate needs a judge that did not write the code. Two options follow.

## Option 1: a native fresh subagent (hard's documented fallback only)

This option applies only to a skill that documents the fresh-subagent fallback, which today
means `hard`. In `wrap` and `cascade` an unset `REVIEWER_CMD` means the gate is SKIPPED, and a
subagent review does not substitute for it there.

Inside Claude Code, run the review with the Agent tool instead of a reviewer command. A
nested `claude -p` subprocess is often rejected from inside a running session, so prefer
this. Leave `REVIEWER_CMD` unset and record in the report that the gate ran as a subagent.

Spawn a general-purpose subagent with a refute-by-default prompt:

```
Review the payload below adversarially. Assume it is wrong until you fail to break it.
Flag correctness, reliability, and security defects only. Ignore style.
Your first line must be exactly PASS or BLOCK, and the verdict applies to the work
under review. Each following line is one finding, formatted:
<severity> | <owner or n/a> | <one-line finding>

<payload>
```

Paste the session change set as the payload. Read the subagent's first line as the verdict.
A first line that is neither PASS nor BLOCK is malformed, and counts as no review.

## Option 2 — an external CLI reviewer

Prerequisites: a CLI installed and authenticated on this machine, from a different vendor
than the author. A model from the author's own family misses the same defects.

Save this as `review.sh`, make it executable, and set `REVIEWER_CMD=./review.sh`.

```bash
#!/usr/bin/env bash
# Reads the payload on stdin. Prints the verdict and findings on stdout.
set -euo pipefail
payload=$(cat)
[ -z "$payload" ] && { echo "BLOCK: empty payload"; exit 1; }
printf '%s\n\n%s\n' "Review this payload adversarially. Try to break it.
Flag correctness, reliability, and security defects only.
Your first line must be exactly PASS or BLOCK, and the verdict applies to the work
under review. Each following line is one finding, formatted:
<severity> | <owner or n/a> | <one-line finding>" "$payload" \
  | your-reviewer-cli
```

Transport is stdin only. The skill treats a non-zero exit, empty stdout, or a first line
that is neither PASS nor BLOCK as no review, never a pass. Keep the exit code honest.
