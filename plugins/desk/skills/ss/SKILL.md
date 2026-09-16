---
name: ss
description: "Screenshot vision — grab recent screenshots from a configured folder and analyze them. Use when user says /ss, /ss N, /ss huh, /ss fix, /ss do this, or /ss with any creative instruction. Gives Claude eyes into what the user is looking at."
---

**What it does:** Reads the N most recent screenshots and describes, explains, fixes, or builds from them, per the invocation.
**When it fires:** `/ss`, `/ss N`, `/ss huh`, `/ss fix`, `/ss do this`, or `/ss <creative instruction>`.
**Config:** `SCREENSHOT_DIR` — default `~/Desktop`, the stock macOS screenshot destination.

# /ss — Screenshot Vision

Grab screenshots from `SCREENSHOT_DIR`, sorted newest-first, and act on them.

## Step 1: Parse the arguments

The user invoked `/ss` with optional arguments. Parse them:

| Pattern | Count | Action |
|---------|-------|--------|
| `/ss` | 1 | Describe what's visible |
| `/ss N` (number) | N | Show N most recent, briefly describe each |
| `/ss huh` | 1 | Explain the content in detail — what is this, what does it mean, what's notable |
| `/ss fix` | 1 | Assume it's a code error or UI bug. Read the error, diagnose it, fix it in the current codebase |
| `/ss do this` | 1 | Assume the user screenshotted something smart online. Learn from it and implement the most goal-oriented version for the current project |
| `/ss [creative instruction]` | 1, or 3 if the instruction implies combining multiple inputs | Use screenshot content to produce whatever the instruction asks for |

If the argument is just a number, count = that number, action = describe.
If the argument starts with a number followed by words, count = that number, action = the words.
If the argument is only words (no number), count = 1 (unless the instruction implies multiple — e.g., "make infographic" defaults to 3).

## Step 2: List and grab screenshots

List the screenshots directory sorted by modification time (newest first), filtered to image files. Substitute N from Step 1:

```bash
SCREENSHOT_DIR="${SCREENSHOT_DIR:-$HOME/Desktop}"
ls -tp "$SCREENSHOT_DIR" | grep -Ei '\.(png|jpe?g|webp|gif)$' | head -N
```

`-p` marks directories with a trailing slash, so the extension filter drops them along with non-image files.

If the command returns fewer than N names, say how many you found and name the directory you searched. If it returns none, name the directory and tell the user how to find the real one:

```bash
defaults read com.apple.screencapture location    # empty or an error means ~/Desktop
```

Use the Read tool to view each file returned. Claude's vision capabilities will process the image content automatically.

Read each file using its full path:
```
$SCREENSHOT_DIR/[filename]
```

## Step 3: Act on the content

Based on the action determined in Step 1:

### No action keyword (just `/ss` or `/ss N`)
- Briefly describe what's visible in each screenshot
- Keep it concise — 1-2 sentences per screenshot
- If something looks actionable or relevant to current work, mention it

### `huh` — Explain
- Describe the content in detail
- What is this showing? What app/site/tool is this?
- What's notable, unusual, or important?
- If it's code: what language, what's happening, any issues visible?
- If it's a UI: what product, what state, what's the user flow?

### `fix` — Diagnose and fix
- Read the error message, stack trace, or UI bug carefully
- Identify the file(s) and line(s) involved
- Search the current codebase for the relevant code
- Diagnose the root cause
- Fix it directly — edit the files, don't just explain
- If the fix requires context you don't have, ask one targeted question

### `do this` — Learn and implement
- Identify what's smart about what the user screenshotted (design pattern, feature, workflow, copy, strategy)
- Consider how it applies to the user's current project and priorities
- Build the most goal-oriented version — not a copy, but a remix that fits the project's context
- If it's a design: implement it for the relevant part of the project
- If it's a strategy/idea: write up a brief and propose next steps
- If it's a tool/feature: build a working version

### Creative instruction (anything else)
- Use the screenshot content as input material
- Follow the instruction literally
- Default to 3 screenshots if the instruction implies combining multiple inputs
- Produce the requested output (infographic, summary, comparison, implementation, etc.)

## Notes

- Screenshots folder: `SCREENSHOT_DIR` (default `~/Desktop`, macOS's stock destination; check `defaults read com.apple.screencapture location` for a custom one)
- Supported formats: PNG, JPG, JPEG, WEBP, GIF — Claude vision handles all of these
- If the folder is empty, missing, or holds no images, name the directory you searched and suggest they take a screenshot or set `SCREENSHOT_DIR`
- If a screenshot is too large or unreadable, say so and ask the user to crop or retake
- For `/ss fix`: prioritize speed — the user wants the fix, not a lecture about the error
- For `/ss do this`: think about which part of the user's project benefits most, then act
