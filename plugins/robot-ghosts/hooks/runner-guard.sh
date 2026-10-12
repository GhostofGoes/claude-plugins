#!/usr/bin/env bash
# PreToolUse hook: hands Bash calls made by robot-ghosts:runner to
# runner_guard.py. Every other agent and tool call exits here untouched.

input=$(cat)
case $input in
  *'"agent_type":"robot-ghosts:runner"'* | *'"agent_type": "robot-ghosts:runner"'*) ;;
  *) exit 0 ;;
esac

if command -v python3 >/dev/null 2>&1; then
  printf '%s' "$input" | python3 "$(dirname "$0")/runner_guard.py"
  exit 0
fi
printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"The robot-ghosts runner guard needs python3, which is not installed. Report this command as: exit: refused (guard unavailable)"}}'
