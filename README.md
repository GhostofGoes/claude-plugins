# claude-plugins

Personal Claude plugins, published as the `ghostofgoes` marketplace.

## lead-coder

The `lead-coder-setup` skill plus the three agents it dispatches:

| Agent | Model | Role |
|---|---|---|
| `lead-coder:lead-explorer` | Sonnet | reads the code and answers factual questions |
| `lead-coder:lead-implementer` | Opus | implements a brief, three verification runs at most |
| `lead-coder:lead-runner` | Haiku | runs commands and returns raw output |

### Install

**Claude Code (CLI, desktop Code tab):**

```bash
claude plugin marketplace add GhostofGoes/claude-plugins   # or a local path to this repo
claude plugin install lead-coder@ghostofgoes
```

**claude.ai account (Cowork, Chat, and Claude Code via sync):** Customize →
Plugins → Add → **Add marketplace** with `GhostofGoes/claude-plugins`, or
**Upload plugin** with a zip built by:

```bash
mkdir -p dist && (cd plugins && zip -r -X ../dist/lead-coder.zip lead-coder -x '*.DS_Store')
```

Account plugins reach Claude Code as `lead-coder@synced`.

### Where it works

| Surface | Skill | Agents |
|---|---|---|
| Claude Code (CLI, desktop Code tab) | yes | yes |
| Cowork | yes | yes |
| Chat | yes | no: Chat never loads plugin agents |
| Cloud sessions | no | no: cloud sessions load no plugins |

For cloud sessions in a given repo, commit the skill to `.claude/skills/` and
the agents to `.claude/agents/` there; inside a repo the agents lose the
`lead-coder:` prefix, so the skill's agent names need it removed.
