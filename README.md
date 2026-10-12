# claude-plugins

Personal Claude plugins, published as the `ghostofgoes` marketplace.

## robot-ghosts

The `robot-ghosts-setup` skill plus the four agents it dispatches:

| Agent | Model | Role |
|---|---|---|
| `robot-ghosts:explorer` | Sonnet | reads the code and answers factual questions |
| `robot-ghosts:implementer` | Opus | implements a brief, three verification runs at most |
| `robot-ghosts:runner` | Haiku | runs commands and returns the exit code, failure lines, and a short tail |
| `robot-ghosts:reviewer` | Sonnet | reviews the confirmed change against its brief |

A PreToolUse hook, `hooks/runner-guard.sh`, keeps `robot-ghosts:runner` to
its log template. It also refuses the runner's git writes, `gh` writes,
deletes, and deploys; `hooks/runner_guard.py` holds the full list. The hook
needs `python3` 3.9 or later; without it, the runner refuses every command. It covers the
runner only: the implementer's and reviewer's read-only Bash rules live in
their prompts. A setup that copies the agents without installing the plugin
has no hook. Test it with `bash scripts/test-runner-guard.sh`.

### Install

**Claude Code (CLI, desktop Code tab):**

```bash
claude plugin marketplace add GhostofGoes/claude-plugins   # or a local path to this repo
claude plugin install robot-ghosts@ghostofgoes
```

**claude.ai account (Cowork, Chat, and Claude Code via sync):** Customize →
Plugins → Add → **Add marketplace** with `GhostofGoes/claude-plugins`, or
**Upload plugin** with a zip built by:

```bash
mkdir -p dist && (cd plugins && zip -r -X ../dist/robot-ghosts.zip robot-ghosts -x '*.DS_Store')
```

Account plugins reach Claude Code as `robot-ghosts@synced`.

### Where it works

| Surface | Skill | Agents |
|---|---|---|
| Claude Code (CLI, desktop Code tab) | yes | yes |
| Cowork | yes | yes |
| Chat | yes | no: Chat never loads plugin agents |
| Cloud sessions | no | no: cloud sessions load no plugins |

For cloud sessions in a given repo, commit the skill to `.claude/skills/` and
the agents to `.claude/agents/` there; inside a repo the agents lose the
`robot-ghosts:` prefix, so the skill's agent names need it removed.

### Credits

Thanks to Matthew Stroble at Sandia National Laboratories for the original
inspiration and guidance that formed this skill.

## Checks

`.github/workflows/checks.yml` runs on pushes to `main` and on pull requests:

| Job | Runs |
|---|---|
| plugin validate | `claude plugin validate --strict` on the marketplace and each plugin, with the latest Claude Code |
| lint | `scripts/check-plugin-refs.py`, shellcheck, ruff, actionlint |
| runner guard | `scripts/test-runner-guard.sh` on Linux with Python 3.9 and the latest Python, and on macOS, again under `/bin/bash` 3.2 |

`scripts/check-plugin-refs.py` fails when a marketplace entry, manifest, or
frontmatter name disagrees, or when a `<plugin>:<name>` reference names no
agent or skill. A rename that misses the hook's agent name would otherwise
turn the runner guard off without an error.

Run them locally:

```bash
python3 scripts/check-plugin-refs.py
bash scripts/test-runner-guard.sh
shellcheck plugins/*/hooks/*.sh scripts/*.sh
ruff check .
claude plugin validate --strict . && claude plugin validate --strict plugins/robot-ghosts
```
