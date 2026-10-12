---
name: robot-ghosts-setup
description: Use when a coding task or session should split thinking, implementing, command running, code exploration, and review across model tiers (Fable or Opus thinks, Opus implements, Haiku runs commands, Sonnet explores and reviews) - on "/robot-ghosts-setup", "robot ghosts", "thinker and implementer", "multi-model", or any request to delegate implementation to Opus with Haiku running the code.
argument-hint: [task]
---

# Robot Ghosts

## Overview

Five roles, one loop. The Thinker (based on model for this session, Fable or Opus) designs and judges.
Opus builds. Haiku runs. Sonnet finds and reviews. The Thinker's context holds
briefs and reports only; file contents and full test logs stay inside
subagents. Runner output arrives condensed: exit code, failure lines, and a
15-line tail.

`/robot-ghosts:robot-ghosts-setup` alone: dispatch `robot-ghosts:runner` with
`echo runner-ok` to confirm the agents resolve, then wait for a task.
`/robot-ghosts:robot-ghosts-setup <task>`: Flow on that task.

## Where it runs

The four agents ship in the `robot-ghosts` plugin's `agents/` directory, so
installing the plugin is the whole setup. They exist wherever plugin agents
load: Claude Code (CLI and the desktop Code tab) and Cowork. Chat loads this
skill but never plugin agents, and cloud sessions load no plugins. A session
started before the plugin was installed sees them after a restart. The plugin
also ships a PreToolUse hook that holds `robot-ghosts:runner` to its log
template and refuses its git writes, `gh` writes, deletes, and deploys. The
hook needs `python3`; without it, the runner refuses every command.

When the Agent tool answers `Agent type 'robot-ghosts:runner' not found`,
tell the user the protocol cannot run in this session and stop. Standing in
other agents for the four roles drops the model split this skill exists for.

## Roles

| Role | Agent | Model | Does | Never |
|---|---|---|---|---|
| Thinker | this session | Fable or Opus | explores through Sonnet, writes briefs, judges reports and findings, redesigns | reads the tree, edits, runs commands, spawns Fable |
| Explorer | `robot-ghosts:explorer` | `sonnet` (Sonnet 5.5) | answers factual questions with `path:line` tables | edits, opinions, running tests |
| Implementer | `robot-ghosts:implementer` | `opus` (Opus 5.5) | implements a brief; implement, run, fix; 3 runs per brief; runs read-only git inspection itself | runs builds or tests itself, exceeds 3 runs, widens scope |
| Runner | `robot-ghosts:runner` | `haiku` (Haiku 5.5) | runs commands into a log, returns exit code, failure lines, and tail (raw on request) | interprets, edits, retries, commits, deletes, deploys |
| Reviewer | `robot-ghosts:reviewer` | `sonnet` (Sonnet 5.5) | reviews the confirmed change against the brief; findings with `path:line` and a failing input | edits, runs builds or tests, style notes |

Agent files pin the alias, which resolves to the model in parentheses as of
2026-10-08 (desktop CLI 2.1.293, Homebrew CLI 2.1.294). Ceiling per task: three
implementer dispatches with nine runs, plus one review round with three runs.

The Implementer dispatches the Runner. Runner output goes to whoever
dispatched it and nowhere else.

## Flow

1. **Explore.** Dispatch `robot-ghosts:explorer` with questions: where is X, what
   calls Y, how is Z tested, what command verifies. Independent questions go
   in parallel calls. Ask questions; never ask for every file's contents.
   Current failures come from one `robot-ghosts:runner` call with the verification
   command, not from the explorer: the explorer reads, it does not run.
2. **Brief.** Write the brief (template below). The verification command
   comes from explorer facts, not from memory.
3. **Implement.** Dispatch `robot-ghosts:implementer` with the brief. One dispatch,
   then wait. While it runs the Thinker dispatches no runner and reads no
   code.
4. **Judge.** Report says `DONE`: step 5. `ESCALATE`: step 7. A fix round's
   `DISPUTED` lines: read the evidence; a finding it shows wrong is dropped,
   and the rest go to the user as unresolved.
5. **Confirm.** Dispatch `robot-ghosts:runner` with a `Dir:` line and the
   brief's `Verify` command(s), and no other command. Exit 0 and criterion
   met: step 6 when the task has had no review yet, otherwise report to the
   user. Anything else: step 7, with the confirm output as the decisive
   failure line.
6. **Review.** Runs once per task. Dispatch `robot-ghosts:reviewer` with the
   brief, the diff base (`HEAD` while the implementer's changes are
   uncommitted), and the confirm block. `VERDICT: PASS`: report to the user.
   `VERDICT: FINDINGS`: read each cited `path:line` range, and run a finding's
   `check:` command through one `robot-ghosts:runner` call with the brief's
   `Dir`. Keep a finding only when the code or the check shows the defect. No
   finding kept: report to the user. Otherwise send the kept findings,
   numbered, to the implementer that wrote the change with `SendMessage`,
   wait for its report, and go to step 4. Dropped findings and the reason for
   each go into the report to the user.
7. **Redesign.** Read `ATTEMPTS` and `BLOCKER` (or the confirm output). Ask
   the explorer what the failure exposed. Write a new brief whose `Approach`
   differs from the last and whose `History` lists every prior run. Dispatch a
   fresh `robot-ghosts:implementer`. After two redesigns without a confirmed `DONE`
   (three dispatches): stop, give the user the full history, ask for
   direction.

## Brief template

```
Goal: <one sentence, observable outcome>
Dir: <absolute path the implementer works in: the repo or its worktree>
Files: <path: what changes there>            (paths from explorer output)
Approach: <numbered steps, exact enough that two implementers write the same code>
Constraints: <tests read-only, no new deps, style rules, out of scope>
Verify: $ <exact command>   passes when <criterion, e.g. exit 0 and final line "OK">
        $ <second command, when needed; one per line, all must pass>
History: <empty on first dispatch; on redesign, one line per prior run:
          change, decisive failure line, why that approach is abandoned>
```

## Agent tool rules for the Thinker

- Every call names `robot-ghosts:explorer`, `robot-ghosts:implementer`,
  `robot-ghosts:runner`, or `robot-ghosts:reviewer`. Any other agent
  type gets an explicit `model` of `sonnet`, `opus`, or `haiku`.
- `subagent_type: "fork"` and `model: "fable"` are never used. A fork is a
  Fable subagent.
- `SendMessage` resumes one agent only: the implementer whose change was
  reviewed, carrying the kept findings. A follow-up question is a new explorer
  dispatch; a redesign is a new brief to a fresh implementer.
- The Thinker reads only a `path:line` range that the explorer or the reviewer
  named and that a brief or a finding depends on.

## Red flags

| Thought | Reality |
|---|---|
| "I'll run the tests myself first, it's one command" | Bash is not the Thinker's tool. One `robot-ghosts:runner` call gives current failures; the command goes in `Verify`. |
| "Quick grep, faster than dispatching" | Dispatch. Thinker context is the scarce resource. |
| "Fork keeps my context" | Fork is a Fable subagent. Use the four agents. |
| "Tell the explorer to print every file" | Ask questions. Dumps land in this context. |
| "Have the explorer run the tests while it is in there" | Explorer reads. One `robot-ghosts:runner` call gives current failures. |
| "Same brief again, with 'be careful'" | Not a redesign. `Approach` must change. |
| "Opus is close, approve run 4 by message" | Run 4 of a brief or a fix round needs a new brief and counts as a redesign. |
| "The reviewer flagged it, so it is real" | Read the cited lines or run the check first. Unshown findings are dropped and listed. |
| "Fixes are in, review again" | One review round per task. Confirm the fixes and report. |
| "A fresh implementer for the review fixes" | Resume the one that wrote the change; its context already holds the files. |
| "Ask the runner for raw output to be safe" | `raw: ` only when exact bytes matter, such as a snapshot diff. The extract keeps the failure lines. |

## Credits

Matthew Stroble at Sandia National Laboratories gave the original inspiration
and guidance that formed this skill.
