# rituals

Agent Skills ([agentskills.io](https://agentskills.io)) for Claude Code and Codex CLI.
Verification loops, session rituals, and launch gates. The loops, rituals and gates block until evidence exists and report what they checked and what they skipped. The desk utilities do not.

Fifteen skills in five bundles. Twelve run identically on both agents. `hard`'s parallel and review modes and `cascade` use Claude Code's Workflow script API; sequential `hard` runs anywhere. `cmux` needs the cmux terminal. `ss` and `local-infer` need local software (a vision-capable agent and Ollama) but no Claude-only feature.

## Install

Claude Code:

```
/plugin marketplace add dustyFski/rituals
/plugin install loops@rituals
/plugin install session@rituals
/plugin install ops@rituals
/plugin install ship@rituals
/plugin install desk@rituals
```

Install only the bundles you want; each line is independent.

Codex CLI (skills are mirrored at `skills/<name>`):

```
git clone https://github.com/dustyFski/rituals && cp -RL rituals/skills/* ~/.codex/skills/
```

`npx skills add dustyFski/rituals` also works; that command is a community convention, not an Anthropic or OpenAI one.

## Skills

| Bundle | Skill | What it does | Portable |
|---|---|---|---|
| loops | hard | Execute-and-verify loop: loop contract, plan gate, cross-model refute gate, optional review mode against a north star | Claude Code (parallel), any (sequential) |
| loops | cascade | One planner authors goal, criteria and worker briefs; workers in worktrees; cross-model validators and auditor; judge routes defects to owners | Claude Code |
| session | wrap | Six-step session close: reconstruct, checklist, reviewer gate, STATE.md, memory, report that lists what was skipped | any |
| session | handoff | Self-contained mid-task handoff file so a fresh session or another agent can resume with zero conversation access | any |
| ops | watchdog | Silent-until-broken metric band monitor; one pre-investigated note when a band breaks | any |
| ops | repeat-offender | Sweep run ledgers for the same root failure across 2+ systems; propose one system-level fix and track it | any |
| ops | shadow | Blind candidate-vs-production test; queue only disagreements; promotion needs a clear week and zero gate misses | any |
| ops | killcheck | Write kill conditions per option before gathering evidence; then hunt only disconfirming evidence | any |
| ship | build-loop | Discuss-plan-build-verify loop that enforces discuss-before-build | any |
| ship | launch-gate | Phased, resumable launch checklist: domain, email, analytics, payments, legal, monitoring | any |
| ship | seo-content | Research, write, optimize and score long-form SEO articles through a four-phase pipeline with a scorer script | any |
| ship | proof-toolkit | Five prove-it-do-not-eyeball recipes for claiming a change is correct | any |
| desk | cmux | Drive the cmux terminal sidebar, panes and viewers from inside it | Claude Code in cmux |
| desk | ss | Grab recent screenshots from a configured folder and analyze them | any |
| desk | local-infer | Route private or high-volume, low-judgment work to local Ollama; refuse judgment-heavy work | any |

## Reviewer contract

Skills with a review gate take one config line, `REVIEWER_CMD`. One contract covers every role.

- The command reads the review payload on **stdin**. There is no file flag.
- Its first line is `PASS` or `BLOCK`, and it applies to the work under review.
- Each later line is one finding: `<severity> | <owner or n/a> | <one-line finding>`.
- A first line that is neither `PASS` nor `BLOCK` is malformed, and malformed means no review happened.
- So does a non-zero exit or empty stdout. No review is never a pass, and the skill says so.
- In `hard`'s review mode the Guardian sets each finding's disposition, not the reviewer.

See `examples/`.

MIT.
