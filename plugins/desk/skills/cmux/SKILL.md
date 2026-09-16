---
name: cmux
description: Control and report into the cmux terminal from inside it — drive the sidebar (progress bars, status pills, notifications, logs), manage topology (windows, workspaces, panes, surfaces, splits, focus), send input to other panes, and open diff/markdown viewers and the embedded browser, all via the `cmux` CLI over its Unix socket. Use when running inside cmux and you want to surface task progress or completion, need deterministic layout/navigation, drive another pane or agent, or are asked to manage cmux itself or edit its settings.
---

**What it does:** Drives the cmux GUI terminal's sidebar and topology (progress, status, notifications, panes, viewers) via the `cmux` CLI.
**When it fires:** Only when Claude Code is running inside a cmux terminal — otherwise every command in this skill is a no-op. Fires on wanting to surface task progress/completion, navigate or drive panes deterministically, or manage cmux settings.
**Config:** none — targets the current workspace/surface automatically via `$CMUX_WORKSPACE_ID`/`$CMUX_SURFACE_ID`, which cmux sets in the environment.

# cmux control

cmux is a socket-controlled terminal multiplexer (a GUI app, not tmux-in-a-pane). You control it with the `cmux` CLI, which talks to the running app over a Unix socket. This skill applies only when Claude Code is running inside a cmux terminal — when it is, `CMUX_WORKSPACE_ID` and `CMUX_SURFACE_ID` are auto-set in the environment and become the default target for every command, so most commands need no `--workspace`/`--surface` flag.

**First check whether you are inside cmux at all.** If `$CMUX_WORKSPACE_ID` is empty, you are not in a cmux terminal and these commands are no-ops / will fail — do nothing. Quick probe: `cmux ping` returns `PONG` when the app is reachable; `cmux identify --json` reports the caller's window/workspace/pane/surface refs.

## Object model

- **Window** — a top-level macOS cmux window.
- **Workspace** — a tab-like group within a window (this is what the sidebar shows; progress/status/notifications attach here).
- **Pane** — a split container within a workspace.
- **Surface** — a single tab inside a pane (a terminal or a browser panel).

Handles: commands accept short refs (`window:1`, `workspace:2`, `pane:3`, `surface:7`), UUIDs, or indexes. Output defaults to refs; add `--id-format uuids|both` for UUIDs. List topology with `cmux tree`, `cmux list-workspaces`, `cmux list-panes`, `cmux list-pane-surfaces`.

## Progress bars (default behavior — automatic)

A progress bar in the workspace sidebar is driven automatically by a hook in this skill: `hooks/cmux-progress.py`. The desk plugin registers it in `.claude-plugin/plugin.json` on `PostToolUse` (matcher `TodoWrite`) and on `Stop`, so installing the plugin is the whole setup. Whenever the todo list updates, the bar is set to `completed/total` with the in-progress task as its label. When the turn ends, the bar clears. The hook needs `python3` on `PATH`. It no-ops whenever `$CMUX_WORKSPACE_ID` is unset (plain terminal, a remote host, etc.), so it is safe everywhere.

**Implication:** you generally do not need to touch progress manually — just use `TodoWrite` as normal and the bar tracks it. Reach for manual control only for non-todo progress (e.g. a long loop with a known count) or a custom label:

```bash
cmux set-progress 0.65 --label "Downloading 13/20 files"   # value is 0.0–1.0
cmux clear-progress                                         # remove the bar
```

Inspect current sidebar state any time: `cmux sidebar-state` (shows `progress=`, status pills, log count, git branch, cwd, ports).

To disable the automatic bar, remove the `hooks` block from the plugin's `plugin.json`, or disable the plugin. The display side is governed by the `sidebar.showProgress` setting in `cmux.json` (default `true`).

## Status pills, notifications, logs

These also attach to the workspace and render in the sidebar — use them to report state without printing to the terminal.

```bash
# Status pill (key/value, optional SF Symbol icon + hex color). cmux's own
# wrapper sets a `claude_code=Running` pill; add your own keys alongside it.
cmux set-status build passing --icon checkmark.circle.fill --color "#34C759"
cmux clear-status build
cmux list-status

# Desktop/sidebar notification — good for "done" or "needs input" on a long task
cmux notify --title "Deploy finished" --body "3 files shipped"

# Structured log lines into the sidebar log panel
cmux log --level info --source build "Compiled in 4.2s"
cmux list-log --limit 20
```

## Topology & navigation

```bash
cmux identify --json                 # who am I (caller refs)
cmux new-workspace --name "Tests"    # new tab-like workspace
cmux new-split right                 # split the current pane
cmux new-pane --type browser --url https://example.com
cmux focus-pane --pane pane:2
cmux move-surface --surface surface:7 --pane pane:2 --focus true
cmux trigger-flash                   # flash this surface to draw the user's eye
cmux rename-workspace "Release prep"
```

## Drive another pane / agent

Send keystrokes or text into a specific surface (e.g. feed a command to a shell, or a prompt to another agent's pane). Always target an explicit surface — never blast every pane.

```bash
cmux send --surface surface:5 "npm test"
cmux send-key --surface surface:5 Enter
cmux read-screen --surface surface:5 --lines 50     # read a pane's output
cmux capture-pane --surface surface:5 --scrollback  # tmux-style capture
```

## Viewers

```bash
cmux diff --source branch            # open the current git diff in a browser split
cmux diff --last-turn                # diff of changes made this turn
cmux markdown open ./NOTES.md        # formatted markdown viewer with live reload
```

## Browser automation

cmux embeds a controllable browser surface (`cmux browser ...`: `open`, `goto`, `snapshot`, `click`, `type`, `eval`, `screenshot`, `wait`, cookies/storage, tabs). Run `cmux browser` with no args, or `cmux docs browser`, for the full surface. Use it for in-app web automation instead of an external headless browser when the user is working in cmux.

## Editing cmux settings (do this safely)

cmux-owned settings live in `~/.config/cmux/cmux.json`. **Before editing, copy the file to a timestamped `.bak` next to it** so the user can revert, then reload — no app restart needed:

```bash
cmux docs settings        # prints schema URL, paths, reload command
cmux settings path
cmux config doctor        # validate JSONC syntax + report keys
cmux reload-config        # reloads BOTH cmux.json AND ~/.config/ghostty/config
```

Terminal *rendering* (font, cursor, theme, scrollback, `background-opacity`, blur) is **not** a cmux setting — it lives in Ghostty's config at `~/.config/ghostty/config`. Use cmux.json for app behavior: sidebar, notifications, browser, automation, workspace colors, agent hibernation, custom actions/commands.

## Discovering more

cmux is large and evolving. Don't guess flags — ask the CLI:

```bash
cmux help                 # full command list
cmux docs                 # docs index: settings|shortcuts|api|browser|agents|dock|sidebars
cmux docs agents          # agent hooks, Feed approvals, notifications, session restore
cmux capabilities         # machine-readable capability list
```

Official upstream skill (richer topology references, browser/markdown sub-skills):
`curl -fsSL https://raw.githubusercontent.com/manaflow-ai/cmux/main/skills/cmux/SKILL.md`

## Rules

- **No-op outside cmux.** If `$CMUX_WORKSPACE_ID` is unset, do nothing — these commands only make sense inside the app.
- **Bounded, best-effort reporting.** Sidebar reporting (progress/status/notify/log) is cosmetics. `bin/cmux-report` and the progress hook cap each socket call at 3 seconds and swallow errors, so a hung cmux costs seconds, not the task. Never fail real work because a UI call failed.
- **Target explicit surfaces** with `send`/`send-key`; never iterate over all panes.
- **Back up `cmux.json`** to a timestamped `.bak` before editing, then `cmux reload-config`.
- **Don't fight the wrapper.** cmux's Claude wrapper already sets the `claude_code` running/idle pill and the progress hook tracks todos — add to that, don't duplicate it.
