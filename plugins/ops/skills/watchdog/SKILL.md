---
name: watchdog
description: Silent-until-broken metric band monitor for a project — reads fixed bands from a state file, pulls current numbers, stays silent inside the band, and writes one pre-investigated note when a metric breaks it. Fires on "watchdog [target]", "check the bands", "run the KPI watch", "anomaly check on [target]".
---

**What it does:** Checks a project's metrics against pre-set normal ranges and only speaks up when one breaks its band.
**When it fires:** "watchdog [target]", "check the bands", "run the KPI watch", "anomaly check on [target]".
**Config:** state file path — default `watchdog/<target>-STATE.md` next to wherever you keep run state; per metric, the state file names the source, the max reading age, and an optional direct fallback. No defaults. This skill will not invent a fetch path.

# /watchdog — Metric Band Watcher

Dashboards show everything, which is why nobody looks at them. This skill looks, says nothing on
a normal day, and only speaks when a metric is actually outside the range you already decided is
normal.

**Usage:** `/watchdog <target>` — e.g. `/watchdog signups`, `/watchdog api-latency`.

## Data sources (use what's configured, never invent a fetch path)

Each metric's state-file entry names three things:

- `source`: the query, API call, or file this run reads.
- `max age`: how old a reading may be and still count. A cached source past this age is stale.
- `fallback`: optional. A second source to pull directly when the first reads stale.

Rules:

- Never reuse another job's output unless the config names it as that metric's `source`. Cache
  reuse is explicit config, not something this run discovers.
- A stale reading with a configured `fallback` → pull the fallback and say the run bypassed the
  stale source.
- A stale reading with no configured `fallback` → `BLOCK`. Name the metric and the stale source.
  Do not pick a substitute source yourself.
- If no source is configured for a target, say so and stop. This skill reads existing data
  sources; it does not build new ones. That's a separate task.

## State file

`watchdog/<target>-STATE.md` (or wherever your project's run-state convention puts it). First run
for a target: set the initial bands explicitly — do not invent thresholds from one data point. A
band needs either a stated reason ("conversion below 1% means the funnel is broken") or at least
2-3 weeks of readings to set a normal range from.

```
# watchdog-<target>-STATE.md

## Bands (set once, revised only with a stated reason)
- <metric>: normal range <low>-<high>, source <api/query>, max age <duration>, fallback <api/query or none>

## Log (append-only)
YYYY-MM-DD | PASS | all N metrics inside band
YYYY-MM-DD | BLOCK | pull failed (500) — no reading taken, band NOT updated
YYYY-MM-DD | BLOCK | signups reading 9d old (max age 2d), no fallback configured
YYYY-MM-DD | PAGED | signup_rate 0.4% (band 1.2-2.0%) | checked: traffic source mix, form errors, page load p95 | likely cause: checkout form validation regression
```

## Procedure

1. Read the target's state file (bands + log). If it doesn't exist, this is a first run — help
   set initial bands (ask, don't assume) and create the file, then stop (nothing to check yet).
2. Pull today's numbers via the configured data source.
3. **Pull failed** → `BLOCK`. Name the failed source. Do not fill the gap with an estimate.
   **Reading older than its `max age`** → use the configured `fallback`; if none is configured,
   `BLOCK`. A stale reading is never treated as current.
4. **All inside band** → `PASS`, append the log line, say nothing further. Silence is the
   designed success state — do not narrate a clean run as if it were news.
5. **A metric outside its band** → `PAGED`. Write one short investigation note: what moved, by
   how much, 2-3 likely causes — each one naming the specific data actually checked to support
   it (never "probably X" with nothing behind it). Append to the log.
6. Never claim causation the data doesn't support — "likely cause," not "caused by," unless a
   checked fact directly confirms it.

No hard cap needed beyond one run per invocation — this is a check, not a fan-out.
