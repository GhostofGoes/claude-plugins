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
| Cloud sessions | with the setup below | with the setup below |

### Cloud sessions

Cloud sessions load no installed or synced plugins. To load lead-coder there
without adding anything to the project repository, configure a **personal**
cloud environment (cloud icon above the message box at claude.ai/code → add or
edit an environment):

1. **Setup script:** paste [`scripts/cloud-setup.sh`](scripts/cloud-setup.sh).
   It clones this repository to `/opt/claude-plugins` and always exits 0.
2. **Environment variables:**
   `CLAUDE_CODE_PLUGIN_DIRS=/opt/claude-plugins/plugins/lead-coder`
3. Start a session in that environment and run `/lead-coder:lead-coder-setup`.
   It dispatches `lead-coder:lead-runner` with `echo lead-runner-ok`; that
   output means the agents loaded.

The environment snapshot keeps the checkout, so plugin updates arrive when the
setup script reruns: after you edit the script, or about every seven days.
