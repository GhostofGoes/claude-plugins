#!/usr/bin/env bash
# shellcheck disable=SC2016
# SC2016 is off because the commands under test are single-quoted on purpose.
# Tests plugins/robot-ghosts/hooks/runner-guard.sh and runner_guard.py.
# Run: bash scripts/test-runner-guard.sh
# Set GUARD_BASH to test under another bash (for example /bin/bash 3.2 on macOS).

guard="$(cd "$(dirname "$0")/.." && pwd)/plugins/robot-ghosts/hooks/runner-guard.sh"
shell=${GUARD_BASH:-bash}
fails=0

# hook_input <command> <agent_type>: the compact JSON Claude Code sends the hook.
# Built in Python: bash 3.2's ${s//...} takes minutes on a 60KB command.
hook_input() {
  python3 -c 'import json, sys
print(json.dumps({"session_id": "s", "hook_event_name": "PreToolUse", "tool_name": "Bash",
                  "tool_input": {"command": sys.argv[1], "description": "x"},
                  "agent_id": "a1", "agent_type": sys.argv[2]}, separators=(",", ":")))' "$1" "$2"
}

# check <expect: allow|deny> <agent_type> <command>
check() {
  local json out got
  json=$(hook_input "$3" "$2")
  out=$(printf '%s' "$json" | "$shell" "$guard")
  got=allow
  [[ $out == *'"permissionDecision": "deny"'* || $out == *'"permissionDecision":"deny"'* ]] && got=deny
  if [[ $got != "$1" ]]; then
    fails=$((fails + 1))
    printf 'FAIL want %s got %s: [%s] %s\n' "$1" "$got" "$2" "$3"
  fi
  if [[ -n $out ]] && ! printf '%s' "$out" | python3 -c 'import json,sys; json.load(sys.stdin)' 2>/dev/null; then
    fails=$((fails + 1))
    printf 'FAIL invalid JSON output for: %s\n' "$3"
  fi
}

r=robot-ghosts:runner
tpl() { printf 'log=$(mktemp "${TMPDIR:-/tmp}/robot-ghosts-runner.XXXXXX") && echo "log: $log" && { cd /w && %s; } >"$log" 2>&1; echo "exit: $? lines: $(wc -l <"$log")"' "$1"; }
allow() { check allow $r "$(tpl "$1")"; }
deny() { check deny $r "$(tpl "$1")"; }

# Builds, tests, linters, installs, and read-only inspection run.
allow 'go test -v ./...'
allow 'go test -run '"'"'TestRm|TestPush'"'"' ./...'
allow 'npm ci && npm test'
allow 'npm test -- --grep "git commit"'
allow 'pytest -k "not deploy" tests/'
allow 'make generate'
allow 'make -C deploy test'
allow 'cargo build --release'
allow 'git log --oneline -3'
allow 'git diff --stat'
allow 'git stash list'
allow 'git tag -l'
allow 'git tag'
allow 'git branch'
allow 'git branch --show-current'
allow 'git config --get user.name'
allow 'git fetch origin'
allow 'git worktree list'
allow 'git apply --check fix.patch'
allow 'grep -rn "git push" docs'
allow 'gh pr view 12 --json state'
allow 'gh run view 99 --log-failed'
allow 'gh api repos/o/r/pulls'
allow 'gh api -X GET repos/o/r/pulls -f state=open'
allow 'gh api graphql -f query='"'"'{viewer{login}}'"'"''
allow 'kubectl get pods -n prod'
allow 'terraform plan'
allow 'ls -la /tmp/rm-test'
allow 'command -v git'
check allow $r 'grep -c -E "FAIL|panic:" "/var/folders/x/T/robot-ghosts-runner.Ab12Cd"; grep -E -A 10 "FAIL|panic:" "/var/folders/x/T/robot-ghosts-runner.Ab12Cd" | head -n 200; echo "-- tail --"; tail -n 15 "/var/folders/x/T/robot-ghosts-runner.Ab12Cd"'
check allow $r 'log="/var/folders/x/T/robot-ghosts-runner.Ab12Cd"; sed -n "360,376p" "$log"'
check allow $r 'cat "/var/folders/x/T/robot-ghosts-runner.Ab12Cd"'

# Git writes are refused in every spelling.
deny 'git commit --allow-empty -m probe'
deny 'git --no-pager commit -m x'
deny 'git --git-dir=.git push'
deny 'git -C "/my dir" push'
deny 'git -c user.name=x commit -m y'
deny 'make test && git push'
deny 'go test ./...
git push'
deny 'git \
push'
deny 'git add -A'
deny 'git mv a b'
deny 'git rm old.go'
deny 'git apply fix.patch'
deny 'git pull'
deny 'git reset --hard HEAD~1'
deny 'git checkout -- file.go'
deny 'git switch main'
deny 'git stash'
deny 'git tag v1.0'
deny 'git branch -D old'
deny 'git branch -m old new'
deny 'git branch newbranch'
deny 'git worktree add ../x'
deny 'git config user.name X'
deny 'echo $(git commit -m x)'
deny 'bash -c "git push"'
deny 'sh -lc "git push origin HEAD"'
deny 'env FOO=1 git push'

# gh writes are refused.
deny 'gh pr create --fill'
deny 'gh pr merge 12 --squash'
deny 'gh pr checkout 12'
deny 'gh pr update-branch 12'
deny 'gh workflow run ci.yml'
deny 'gh api -X DELETE repos/o/r/git/refs/heads/x'
deny 'gh api --method=PUT repos/o/r/pulls/1/merge'
deny 'gh api repos/o/r/issues --method POST'
deny 'gh api repos/o/r/issues -f title=x'
deny 'gh api repos/o/r/issues -ftitle=x'
deny 'gh api graphql -f query='"'"'mutation { addStar(input:{}) { clientMutationId } }'"'"''

# Deletes are refused.
deny 'rm -rf build'
deny '/bin/rm -f out.txt'
deny 'sudo rm -rf /tmp/x'
deny 'find . -name "*.tmp" -delete'
deny 'find . -name "*.tmp" -exec rm {} \;'
deny 'ls *.tmp | xargs rm'

# Deploys and publishes are refused.
deny 'kubectl apply -f deploy.yaml'
deny 'kubectl -n prod apply -f x.yaml'
deny 'helm -n x upgrade r c'
deny 'terraform -chdir=infra apply'
deny 'npm publish'
deny 'npm run deploy'
deny 'make deploy-staging'
deny 'docker push img:tag'
deny 'gcloud run deploy svc'
deny 'firebase deploy'

# A runner call outside the log template, or a template run without cd, is refused.
check deny $r 'go test -v ./...'
check deny $r 'go test ./... # robot-ghosts-runner.x'
check deny $r 'log=$(mktemp "${TMPDIR:-/tmp}/robot-ghosts-runner.XXXXXX") && echo "log: $log" && { git log --oneline -3; } >"$log" 2>&1; echo "exit: $?"'
check deny $r 'cd /w && log=$(mktemp "${TMPDIR:-/tmp}/robot-ghosts-runner.XXXXXX") && echo "log: $log" && { git log --oneline -3; } >"$log" 2>&1; echo "exit: $?"'
check allow $r 'log=$(mktemp "${TMPDIR:-/tmp}/robot-ghosts-runner.XXXXXX") && echo "log: $log" && { cd . && git log --oneline -3; } >"$log" 2>&1; echo "exit: $?"'

# Other agents and the main loop are never touched.
check allow robot-ghosts:implementer 'git commit -m x'
check allow robot-ghosts:implementer 'go test ./...'
check allow cmd-digest 'rm -rf build'
check allow '' 'git push'

# A long command with many quotes is checked in well under a second.
long=$(printf 'echo "x" %.0s' $(seq 1 5000))
start=$(python3 -c 'import time; print(time.time())')
allow "$long"
elapsed=$(python3 -c "import time; print(round(time.time() - $start, 2))")
if python3 -c "import sys; sys.exit(0 if $elapsed < 2 else 1)"; then :; else
  fails=$((fails + 1))
  printf 'FAIL 60KB command took %ss\n' "$elapsed"
fi

if ((fails)); then
  printf '%d failure(s) under bash %s\n' "$fails" "$("$shell" -c 'echo $BASH_VERSION')"
  exit 1
fi
printf 'all runner-guard checks passed under bash %s (60KB command: %ss)\n' "$("$shell" -c 'echo $BASH_VERSION')" "$elapsed"
