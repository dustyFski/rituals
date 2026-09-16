---
name: local-infer
description: "Route a task to on-device local inference via Ollama instead of Claude. Fires on /local-infer, 'run this locally', 'use the local model', or private/high-volume/low-judgment work (extraction, classification, dedup, tagging, reformatting, first drafts) kept off cloud APIs. Refuses judgment-heavy, legal, money-facing, published, or one-way-door work — that stays on Claude."
user-invocable: true
---

**What it does:** Gates a task for local-inference eligibility, picks a local model, runs it via Ollama, and reports which model ran and why.
**When it fires:** `/local-infer`, "run this locally", "use the local model", "send this to the local model", or any private/high-volume/low-judgment task (extraction, classification, dedup, tagging, reformatting, first drafts).
**Config:** `OLLAMA_HOST` (default `127.0.0.1:11434`, with or without a scheme); `LOCAL_MODEL` (no default — set it to a generation-capable model you have pulled); `LOCAL_MODEL_FAST` (optional second, faster/smaller model for high-volume low-latency triage — default: none, fall back to `LOCAL_MODEL`).
**Prerequisites:** Ollama installed and serving, the model pulled, and cloud inference disabled (see Step 0).

# /local-infer — On-device model router (Ollama)

This skill talks to a local Ollama instance at `OLLAMA_HOST` (`127.0.0.1:11434` by default). It is an EXECUTOR, never a verifier of Claude's own judgment: a weaker local model second-guessing a stronger one's verdict is noise, not signal. Its job is to (1) decide if the task is even eligible for local inference, (2) pick which model fits, (3) run it, (4) hand the result back with a one-line note on what ran and why.

## Step 0 — Privacy precondition (checked before any input is sent)

The whole point of this skill is that the input never leaves the machine. Two things can break that.
`OLLAMA_HOST` can point at another machine, and Ollama can route to Ollama's cloud models. So
"it went to Ollama" does not by itself mean "it stayed local", and cloud-disable alone is not
locality. Run all three checks BEFORE sending anything:

1. **The endpoint is loopback.** Resolve `OLLAMA_HOST` to a bare host and refuse unless it is
   `127.0.0.1`, `localhost`, or `::1`. A remote host passes the other two checks and still ships
   private input off-device. This gate is what makes checks 2 and 3 meaningful: once the endpoint is
   loopback, the server you are querying is this machine.
2. **Cloud inference is disabled on that server.** The setting is `OLLAMA_NO_CLOUD=1` in the
   server's environment, or `"disable_ollama_cloud": true` in `~/.ollama/server.json`. Confirmed
   against the Ollama FAQ (docs.ollama.com/faq); the server log then reports
   `Ollama cloud disabled: true`. Names drift between versions, so check
   `ollama serve --help` if the log line is absent.
3. **The selected model is present on that endpoint.** Ask the endpoint itself, with
   `GET /api/tags`. Do not use a bare `ollama list`: that reads whatever server the CLI defaults to,
   which is not always the one you are about to send to.

If any check fails or cannot be run, REFUSE and say which one. Do not send private input to an
unverified server, and never substitute a different model.

```bash
set -euo pipefail

# 0. Pick the model ONCE, here, before any preflight, per the Step 2 routing rule.
#    Everything after this uses $model, so the tags check and the request body
#    can never disagree.
model="${LOCAL_MODEL:?set LOCAL_MODEL to a generation-capable tag}"
# Simple, high-volume, low-latency triage only:
#   model="${LOCAL_MODEL_FAST:-$LOCAL_MODEL}"

# 1. Loopback gate. A hand-rolled shell parser is bypassable
#    (http://remote.example?x=@localhost:11434 "resolves" to localhost), so parse
#    properly and rebuild a canonical URL that both requests then use.
url=$(OLLAMA_HOST="${OLLAMA_HOST:-127.0.0.1:11434}" python3 -c '
import os, sys
from urllib.parse import urlsplit
raw = os.environ["OLLAMA_HOST"]
u = urlsplit(raw if "://" in raw else "http://" + raw)
try:
    port = u.port or 11434
except ValueError:
    sys.exit(1)
if (u.scheme not in ("http", "https") or u.username or u.password
        or u.query or u.fragment or u.path not in ("", "/")):
    sys.exit(1)
host = u.hostname
if host not in ("127.0.0.1", "localhost", "::1"):
    sys.exit(1)
print("http://%s:%d" % ("[" + host + "]" if ":" in host else host, port))
') || {
  echo "not-loopback: ${OLLAMA_HOST:-127.0.0.1:11434} (refusing to send private input off-device)" >&2
  exit 17
}

# 2. Cloud-disable is a property of that same server. Verify it out of band
#    (server log line, OLLAMA_NO_CLOUD, or ~/.ollama/server.json) before continuing.

# 3. Model presence, asked of the endpoint itself. Same rc/HTTP classification as
#    the generate call: a proxy, a 500, or a hang is not "backend down".
#    -q ignores ~/.curlrc; --noproxy "*" keeps a proxy env var off the loopback path.
TAGS="$(mktemp)"; trap 'rm -f "$TAGS"' EXIT
code=$(curl -q -sS --noproxy '*' -m 5 -o "$TAGS" -w '%{http_code}' "$url/api/tags") && rc=0 || rc=$?
if [ "$rc" -ne 0 ] || [ "$code" = "000" ]; then
  case "$rc" in
    7)  echo "backend-down: connection refused at $url" >&2; exit 10 ;;
    28) echo "timeout: no answer from $url/api/tags within 5s" >&2; exit 12 ;;
    *)  echo "transport-failure: curl rc=$rc code=$code" >&2; exit 13 ;;
  esac
fi
[ "$code" = "200" ] || { echo "http-$code from $url/api/tags" >&2; exit 11; }
jq -e --arg m "$model" '[.models[].name] | index($m) // index($m + ":latest")' "$TAGS" >/dev/null \
  || { echo "model-not-on-endpoint: $model at $url" >&2; exit 11; }
```

## Step 1 — Eligibility gate (deterministic, not a judgment call)

Route to LOCAL only if the task is low-to-moderate judgment AND at least one of privacy /
volume / offline / zero-marginal-cost-exploration applies. Task classes:

**Eligible:** structured extraction, classification/tagging, dedup/clustering, rubric-scoring
against a fixed rubric, reformatting, first-draft generation for a downstream Claude/human
review pass, JSON-schema-strict extraction, cheap pre-filter/sanity-gate before an expensive
Claude call (schema validity, frontmatter presence, obvious-malformation rejects).

**NEVER eligible — refuse and say so, don't attempt it:** final-verdict/ship-fix-kill calls,
editorial or brand-voice work, legal or money-facing published copy, any assessment of legal,
regulatory, or compliance exposure (published or not, and including fixed-rubric screening of
unpublished drafts), any one-way-door decision, multi-turn agentic tool-calling loops, or acting as
a second-opinion reviewer of Claude's own judgment output — this is a hard architectural rule, not a
per-task guess.

If the ask is ambiguous, say so and ask rather than guessing either direction.

**Hard exclusion, checked FIRST, before the eligibility classes above: does this task run as
part of an unattended automated pipeline** (a cron job, a scheduled agent, anything meant to run
without a human at the keyboard)? If yes, refuse regardless of how eligible the task shape looks
(extraction/dedup/classification included) — such pipelines exist to run independent of any one
machine being on, and routing a step to local inference would silently make an unattended
pipeline depend on this machine being awake and reachable. This is a standing exclusion, not a
per-task call.

## Step 2 — Model choice

| Signal in the task | Model | Why |
|---|---|---|
| Structurally complex, multi-step, needs careful verification (e.g. "check these N constraints are each actually necessary", catching a subtle logical error) | **`LOCAL_MODEL`** (default seat) | Reserve the default, larger/more-capable model for anything needing real reasoning or verification. |
| Simple, high-volume, low-latency classification/triage (ticket-shaped, tag-shaped, one-line-per-item) | **`LOCAL_MODEL_FAST`**, if configured | A smaller/faster model trades some quality for throughput on volume work — only worth it when the task is simple enough that the trade is safe. |
| Structured extraction, dedup/clustering, schema-strict output (categorization, idea clustering, structured JSON with a correct-empty case) | **either** | Both should handle this cleanly; default to `LOCAL_MODEL` unless the task is also high-volume/latency-sensitive. |
| Unsure / doesn't fit the above | **`LOCAL_MODEL`** (default) | |

Pick ONE explicit model per call and name it at the top of the Step 0 block, before the tags
preflight. That single `$model` value is what gets checked and what gets sent, so the fast-model
row can never pick a model the request body then fails to use. If `LOCAL_MODEL` is unset the run
refuses: set it to a generation-capable tag you have pulled (skip embedding-only models such as
`nomic-embed-text`). Never send an empty model name.

## Step 3 — Run it (one checked path, every check mandatory)

Prerequisites, once per machine: install Ollama, start the server with cloud inference disabled
(Step 0), and `ollama pull` the model. Then normalize the config, preflight the prompt, and send.
Step 0 must already have passed in the same shell.

```bash
set -euo pipefail

prompt='<self-contained prompt — the model has no conversation history>'
num_ctx=32768          # must match what the model is served with
deadline=300           # seconds; a bounded request, never an open-ended wait
labels=''              # space-separated fixed label set, when the task asked for one
want_json=0            # 1 when the task asked for JSON

OUT="$(mktemp)"; trap 'rm -f "$OUT" "${TAGS:-}"' EXIT

# 1. Preflight: Ollama silently truncates an over-length prompt (keeps the tail).
#    Bound by UTF-8 byte length. A token needs at least one byte, so bytes >= tokens
#    for any byte-level tokenizer. This is a conservative bound, not a guarantee:
#    added tokens and control sequences can break it. Where the model's real
#    tokenizer is available, count with that instead.
bytes=$(printf %s "$prompt" | LC_ALL=C wc -c | tr -d ' ')
[ "$bytes" -le $(( num_ctx - 1024 )) ] || { echo "prompt-too-long: $bytes bytes" >&2; exit 15; }

# 2. Send with a JSON-serialized body and a bounded deadline. `jq -n` does the
#    escaping; hand-built JSON breaks on the first quote or newline in the prompt.
body=$(jq -n --arg m "$model" --arg p "$prompt" --argjson c "$num_ctx" \
  '{model:$m, prompt:$p, stream:false, options:{num_ctx:$c}}')
code=$(curl -q -sS --noproxy '*' -m "$deadline" -o "$OUT" -w '%{http_code}' \
  "$url/api/generate" -H 'Content-Type: application/json' -d "$body") && rc=0 || rc=$?

# 3. Transport status first: curl's exit code, not the HTTP code, which is 000 here.
if [ "$rc" -ne 0 ] || [ "$code" = "000" ]; then
  case "$rc" in
    7)  echo "backend-down: connection refused at $url" >&2; exit 10 ;;
    28) echo "timeout: no answer within ${deadline}s" >&2; exit 12 ;;
    *)  echo "transport-failure: curl rc=$rc code=$code" >&2; exit 13 ;;
  esac
fi
if [ "$code" != "200" ]; then
  [ "$code" = "404" ] && echo "model-not-pulled: $model" >&2 || echo "http-$code" >&2
  exit 11
fi

# 4. Validate the envelope.
jq -e '.response != null and .done == true' "$OUT" >/dev/null \
  || { echo "no-signal: bad envelope" >&2; exit 13; }
answer=$(jq -r '.response' "$OUT")

# 5. Truncated answer: the model hit the output cap. Never pass a half-answer on.
[ "$(jq -r '.done_reason // ""' "$OUT")" != "length" ] \
  || { echo "truncated-answer: done_reason=length" >&2; exit 16; }

# 6. Shape check against what was actually asked for. A word count is not a
#    proxy for either: it rejects a correct `{"items": []}` and accepts `n o`
#    for the label `no`.
trimmed=$(printf %s "$answer" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
if [ -z "$trimmed" ]; then
  echo "empty-answer" >&2; exit 16
elif [ -n "$labels" ]; then
  # A label set was requested: the whole trimmed answer must BE one of the labels.
  case " $labels " in
    *" $trimmed "*) ;;
    *) echo "not-in-label-set: $trimmed" >&2; exit 16 ;;
  esac
elif [ "$want_json" -eq 1 ]; then
  printf %s "$answer" | jq -e . >/dev/null || { echo "not-json" >&2; exit 14; }
fi

# 7. Success: the validated answer goes to stdout.
printf '%s\n' "$answer"
```

**Stable failure statuses — branch on these, never guess from stdout shape:**
- `0` — success, validated answer on stdout.
- `10` — backend down (Ollama not running, connection refused). Start it; don't retry blind.
- `11` — HTTP non-200, or the model is not on the endpoint. A `404` means the model is not pulled.
  Report which and stop; never silently substitute.
- `12` — request exceeded the deadline. For a large prompt, one retry with a longer deadline is
  reasonable; for a small prompt, treat it as a real failure.
- `13` — other transport failure, or no signal: empty body, error envelope, or missing `.response`.
  Not the same as a correct empty answer (`{"items": []}` is success). Never treat as a pass.
- `14` — response was not valid JSON, when JSON was requested.
- `15` — prompt too long for the window; refused before sending.
- `16` — empty answer, an answer outside the requested label set, or a truncated answer. Never a
  pass; report it. A correct empty structure (`{"items": []}`) is success, not a 16.
- `17` — endpoint is not loopback; refused before sending.

## Step 4 — Hand back the result

Always report which model ran and the one-line reason (from the Step 2 table), then the
result. If Step 1 refused, say plainly why and do the task on Claude instead — don't silently
fall through.
