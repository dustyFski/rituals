#!/usr/bin/env python3
"""cmux progress-bar hook.

Drives the cmux sidebar progress bar from Claude Code's TodoWrite list and
clears it when a turn ends. The desk plugin registers it in plugin.json as:

  PostToolUse  matcher "TodoWrite"  -> this script   (set/update the bar)
  Stop         matcher ""           -> this script   (clear the bar)

It is a NO-OP whenever Claude is not running inside a cmux terminal (the
`cmux` binary is missing, or CMUX_WORKSPACE_ID is unset), so it is safe to
keep enabled globally — on a remote host, in a plain terminal, anywhere.

Bounded, not async: each cmux call is capped at 3 seconds. Worst case the hook
delays the event by that much. It always exits 0 and never prints to stdout.
"""
import json
import os
import shutil
import subprocess
import sys

APP_FALLBACK = "/Applications/cmux.app/Contents/Resources/bin/cmux"
MAX_LABEL = 60


def find_cmux():
    path = shutil.which("cmux")
    if path:
        return path
    if os.path.exists(APP_FALLBACK):
        return APP_FALLBACK
    return None


def run(cmux, args):
    # Bounded call; a hung socket costs 3 seconds, not the turn.
    try:
        subprocess.run(
            [cmux, *args],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=3,
        )
    except Exception:
        pass


def truncate(text):
    text = " ".join(str(text).split())  # collapse newlines/whitespace
    return text if len(text) <= MAX_LABEL else text[: MAX_LABEL - 1] + "…"


def main():
    workspace = os.environ.get("CMUX_WORKSPACE_ID")
    if not workspace:
        return  # not inside a cmux terminal -> nothing to drive

    cmux = find_cmux()
    if not cmux:
        return

    try:
        data = json.load(sys.stdin)
    except Exception:
        data = {}

    event = data.get("hook_event_name", "")
    ws = ["--workspace", workspace]

    if event in ("Stop", "SubagentStop"):
        run(cmux, ["clear-progress", *ws])
        return

    # PostToolUse / TodoWrite: derive a completion ratio from the todo list.
    todos = (data.get("tool_input") or {}).get("todos") or []
    total = len(todos)
    if total == 0:
        run(cmux, ["clear-progress", *ws])
        return

    completed = sum(1 for t in todos if t.get("status") == "completed")
    ratio = round(completed / total, 3)

    active = next((t for t in todos if t.get("status") == "in_progress"), None)
    if active:
        label = active.get("activeForm") or active.get("content") or ""
        label = f"{truncate(label)} ({completed}/{total})"
    else:
        label = f"{completed}/{total} tasks done"

    run(cmux, ["set-progress", str(ratio), "--label", label, *ws])


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
