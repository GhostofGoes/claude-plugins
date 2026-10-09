---
name: lead-coder-setup
description: Use when a coding task or session should split thinking, implementing, command running, and code exploration across model tiers (Fable or Opus thinks, Opus implements, Haiku runs commands, Sonnet explores) - on "/lead-coder-setup", "lead coder", "thinker and implementer", "multi-model", or any request to delegate implementation to Opus with Haiku running the code.
argument-hint: [task]
---

# Lead Coder

## Overview

Four roles, one loop. The Thinker (based on model for this session, Fable or Opus) designs and judges.
Opus builds. Haiku runs. Sonnet finds. The Thinker's context holds briefs and
reports only; file contents and full test logs stay inside subagents, and a
report carries at most the last 20 lines of output.

`/lead-coder:lead-coder-setup` alone: dispatch `lead-coder:lead-runner` with
`echo lead-runner-ok` to confirm the agents resolve, then wait for a task.
`/lead-coder:lead-coder-setup <task>`: Flow on that task.

## Where it runs

The three agents ship in the `lead-coder` plugin's `agents/` directory, so
installing the plugin is the whole setup. They exist wherever plugin agents
load: Claude Code (CLI and the desktop Code tab) and Cowork. Chat loads this
skill but never plugin agents, and cloud sessions load no plugins. A session
started before the plugin was installed sees them after a restart.

When the Agent tool answers `Agent type 'lead-coder:lead-runner' not found`,
tell the user the protocol cannot run in this session and stop. Standing in
other agents for the three roles drops the model split this skill exists for.

## Roles

| Role | Agent | Model | Does | Never |
|---|---|---|---|---|
| Thinker | this session | Fable or Opus | explores through Sonnet, writes briefs, judges reports, redesigns | reads the tree, edits, runs commands, spawns Fable |
| Explorer | `lead-coder:lead-explorer` | `sonnet` (Sonnet 5.5) | answers factual questions with `path:line` tables | edits, opinions, running tests |
| Implementer | `lead-coder:lead-implementer` | `opus` (Opus 5.5) | implements a brief; implement, run, fix; 3 runs per brief | runs commands itself, exceeds 3 runs, widens scope |
| Runner | `lead-coder:lead-runner` | `haiku` (Haiku 5.5) | runs commands verbatim, returns exit code plus raw output | interprets, edits, retries |

Agent files pin the alias, which resolves to the model in parentheses as of
2026-10-08 (desktop CLI 2.1.293, Homebrew CLI 2.1.294). Ceiling per task: three implementer dispatches, nine runs.

The Implementer dispatches the Runner. Runner output goes to whoever
dispatched it and nowhere else.

## Flow

1. **Explore.** Dispatch `lead-coder:lead-explorer` with questions: where is X, what
   calls Y, how is Z tested, what command verifies. Independent questions go
   in parallel calls. Ask questions; never ask for every file's contents.
   Current failures come from one `lead-coder:lead-runner` call with the verification
   command, not from the explorer: the explorer reads, it does not run.
2. **Brief.** Write the brief (template below). The verification command
   comes from explorer facts, not from memory.
3. **Implement.** Dispatch `lead-coder:lead-implementer` with the brief. One dispatch,
   then wait. While it runs the Thinker dispatches no runner and reads no
   code.
4. **Judge.** Report says `DONE`: step 5. `ESCALATE`: step 6.
5. **Confirm.** Dispatch `lead-coder:lead-runner` with the brief's `Verify` command(s)
   and no other command. Exit 0 and criterion met: report to the user.
   Anything else: step 6, with the confirm output as the decisive failure
   line.
6. **Redesign.** Read `ATTEMPTS` and `BLOCKER` (or the confirm output). Ask
   the explorer what the failure exposed. Write a new brief whose `Approach`
   differs from the last and whose `History` lists every prior run. Dispatch a
   fresh `lead-coder:lead-implementer`. After two redesigns without a confirmed `DONE`
   (three dispatches): stop, give the user the full history, ask for
   direction.

## Brief template

```
Goal: <one sentence, observable outcome>
Files: <path: what changes there>            (paths from explorer output)
Approach: <numbered steps, exact enough that two implementers write the same code>
Constraints: <tests read-only, no new deps, style rules, out of scope>
Verify: $ <exact command>   passes when <criterion, e.g. exit 0 and final line "OK">
        $ <second command, when needed; one per line, all must pass>
History: <empty on first dispatch; on redesign, one line per prior run:
          change, decisive failure line, why that approach is abandoned>
```

## Agent tool rules for the Thinker

- Every call names `lead-coder:lead-explorer`, `lead-coder:lead-implementer`, or `lead-coder:lead-runner`. Any
  other agent type gets an explicit `model` of `sonnet`, `opus`, or `haiku`.
- `subagent_type: "fork"` and `model: "fable"` are never used. A fork is a
  Fable subagent.
- No dispatched agent is resumed with `SendMessage`. A follow-up question is
  a new explorer dispatch; a redesign is a new brief to a fresh implementer.
- The Thinker reads only a `path:line` range the explorer named and the brief
  depends on.

## Red flags

| Thought | Reality |
|---|---|
| "I'll run the tests myself first, it's one command" | Bash is not the Thinker's tool. One `lead-coder:lead-runner` call gives current failures; the command goes in `Verify`. |
| "Quick grep, faster than dispatching" | Dispatch. Thinker context is the scarce resource. |
| "Fork keeps my context" | Fork is a Fable subagent. Use the three agents. |
| "Tell the explorer to print every file" | Ask questions. Dumps land in this context. |
| "Have the explorer run the tests while it is in there" | Explorer reads. One `lead-coder:lead-runner` call gives current failures. |
| "Same brief again, with 'be careful'" | Not a redesign. `Approach` must change. |
| "Opus is close, approve run 4 by message" | Run 4 needs a new brief and counts as a redesign. |
