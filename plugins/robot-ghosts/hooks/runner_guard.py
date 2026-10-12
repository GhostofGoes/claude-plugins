"""PreToolUse guard for Bash calls made by robot-ghosts:runner.

runner-guard.sh calls this only for the runner's Bash calls. It denies a call
whose commands change git state, write through gh, delete files, or deploy, and
a call that is neither a log-template run nor a read of a runner log.
Standard library only; Python 3.9 or later.
"""

import json
import os
import re
import shlex
import sys

REFUSED = (
    "The runner never runs commands that change git state, write through gh, "
    "delete files, or deploy. Do not retry it in another form. Report this "
    "command as: exit: refused (side effects)"
)
NOT_TEMPLATE = (
    "The runner runs a caller command only inside the log template from its "
    "instructions (mktemp .../robot-ghosts-runner.XXXXXX), and reads output "
    "only from that log. Rerun this step with the template."
)
NO_CD = (
    "Denied: the braces in this run call do not start with cd. Resend it as "
    "{ cd <dir> && <command>; }, where <dir> is the Dir: path your caller gave, "
    "or . when none was given. Do not ask your caller to run the command instead."
)

RUN_PREFIX = re.compile(
    r'^\s*log=\$\(mktemp\s+"\$\{TMPDIR:-/tmp\}/robot-ghosts-runner\.XXXXXX"\)\s*&&\s*'
    r'echo\s+"log: \$log"\s*&&\s*\{'
)
RUN_CD = re.compile(r'&&\s*\{\s*cd\s')
RUN_REDIRECT = re.compile(r'\}\s*>\s*"\$log"\s+2>&1')
LOG_READERS = {
    "grep", "egrep", "fgrep", "rg", "tail", "head", "cat", "sed", "awk", "wc",
    "echo", "printf", "cut", "sort", "uniq", "nl", "tr", "test", "[", "ls",
    "true", "false", ":",
}

KEYWORDS = {"{", "}", "(", ")", "!", "if", "then", "else", "elif", "fi", "do",
            "done", "while", "until", "time", "case", "esac", "in"}
ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
SHELLS = {"bash", "sh", "zsh", "dash", "ksh"}

GIT_GLOBAL_ARG = {"-C", "-c", "--git-dir", "--work-tree", "--namespace",
                  "--exec-path", "--super-prefix", "--config-env"}
GIT_WRITE = {"commit", "push", "pull", "reset", "checkout", "switch", "restore",
             "rebase", "merge", "cherry-pick", "revert", "am", "add", "rm", "mv",
             "clean", "update-ref", "update-index", "filter-branch",
             "filter-repo", "replace", "gc", "prune", "commit-tree", "init"}
GIT_WRITE_SUBS = {
    "worktree": {"add", "remove", "move", "prune", "lock", "unlock", "repair"},
    "submodule": {"add", "update", "deinit", "sync", "set-branch", "set-url",
                  "absorbgitdirs", "init", "foreach"},
    "notes": {"add", "append", "copy", "edit", "merge", "remove", "prune"},
    "remote": {"add", "remove", "rm", "rename", "set-url", "set-head",
               "set-branches", "prune", "update"},
}
BRANCH_WRITE_FLAGS = {"-d", "-D", "--delete", "-m", "-M", "--move", "-c", "-C",
                      "--copy", "-f", "--force", "-u", "--set-upstream-to",
                      "--unset-upstream", "--edit-description", "-t", "--track",
                      "--no-track"}
BRANCH_LIST_FLAGS = {"-l", "--list", "-a", "--all", "-r", "--remotes",
                     "--contains", "--no-contains", "--merged", "--no-merged",
                     "--points-at", "--show-current", "-v", "-vv", "--verbose",
                     "--format", "--sort"}
TAG_WRITE_FLAGS = {"-d", "--delete", "-a", "--annotate", "-s", "--sign", "-u",
                   "--local-user", "-m", "--message", "-F", "--file", "-f",
                   "--force", "-e", "--edit"}
TAG_LIST_FLAGS = {"-l", "--list", "-v", "--verify", "-n", "--contains",
                  "--no-contains", "--points-at", "--merged", "--no-merged",
                  "--sort", "--format"}
CONFIG_READ = {"--get", "--get-all", "--get-regexp", "--get-urlmatch", "-l",
               "--list", "get", "list"}
CONFIG_WRITE = {"--unset", "--unset-all", "--add", "--replace-all",
                "--rename-section", "--remove-section", "-e", "--edit", "set",
                "unset", "rename-section", "remove-section", "edit"}

GH_READ_VERBS = {"view", "list", "ls", "status", "diff", "checks", "watch",
                 "download", "get", "check", "verify"}
GH_READ_TOP = {"status", "search", "help", "version", "browse", "completion"}

DELETERS = {"rm", "rmdir", "unlink", "shred", "srm"}
DEPLOY_WORDS = {"deploy", "publish"}
CLOUD_CLIS = {"firebase", "fly", "flyctl", "netlify", "heroku", "gcloud", "aws",
              "az", "serverless", "sls", "sam", "cdk", "wrangler", "eb",
              "amplify", "railway", "cf", "doctl", "vercel"}
CLOUD_EXTRA = {"cf": {"push"}, "railway": {"up"}, "vercel": {"--prod"}}
KUBECTL_GLOBAL_ARG = {"-n", "--namespace", "--context", "--cluster",
                      "--kubeconfig", "-s", "--server", "--user", "--token"}
KUBECTL_WRITE = {"apply", "create", "delete", "replace", "patch", "scale", "set",
                 "edit", "annotate", "label", "drain", "cordon", "uncordon",
                 "taint", "expose", "run", "autoscale", "cp"}
HELM_WRITE = {"install", "upgrade", "uninstall", "delete", "rollback", "push"}
TERRAFORM_WRITE = {"apply", "destroy", "import", "taint", "untaint",
                   "force-unlock"}
PUBLISHERS = {
    "npm": {"publish", "unpublish", "deprecate"}, "pnpm": {"publish"},
    "yarn": {"publish"}, "bun": {"publish"}, "cargo": {"publish", "yank"},
    "twine": {"upload"}, "gem": {"push", "yank"}, "poetry": {"publish"},
    "uv": {"publish"}, "hatch": {"publish"}, "flit": {"publish"},
    "goreleaser": {"release"}, "docker": {"push"}, "podman": {"push"},
    "buildah": {"push"}, "pulumi": {"up", "update", "destroy", "import"},
}
MAKE_ARG = {"-C", "-f", "--file", "--makefile", "-I", "--include-dir", "-o",
            "--old-file", "-W", "--what-if", "--directory"}
DEPLOY_TARGET = re.compile(r"(^|[-_:/.])(deploy|publish)($|[-_:/.])")


def positionals(args):
    return [a for a in args if not a.startswith("-")]


def git_writes(args):
    i = 0
    while i < len(args):
        a = args[i]
        if a in GIT_GLOBAL_ARG:
            i += 2
        elif a.startswith("-"):
            i += 1
        else:
            break
    if i >= len(args):
        return False
    sub, rest = args[i], args[i + 1:]
    flags, pos = set(rest), positionals(rest)
    if sub in GIT_WRITE:
        return True
    if sub in GIT_WRITE_SUBS:
        return bool(pos) and pos[0] in GIT_WRITE_SUBS[sub]
    if sub == "stash":
        return not (pos and pos[0] in {"list", "show"})
    if sub == "branch":
        if flags & BRANCH_WRITE_FLAGS or any(f.startswith("--set-upstream-to=") for f in flags):
            return True
        return bool(pos) and not flags & BRANCH_LIST_FLAGS
    if sub == "tag":
        if flags & TAG_WRITE_FLAGS:
            return True
        return bool(pos) and not flags & TAG_LIST_FLAGS
    if sub == "config":
        if flags & CONFIG_WRITE:
            return True
        if flags & CONFIG_READ:
            return False
        return len(pos) >= 2
    if sub == "apply":
        return not flags & {"--check", "--stat", "--numstat", "--summary"}
    if sub == "symbolic-ref":
        return len(pos) >= 2
    if sub == "bisect":
        return not (pos and pos[0] in {"log", "visualize", "view"})
    return False


def gh_api_writes(args):
    method, fields = None, []
    i = 0
    while i < len(args):
        a = args[i]
        nxt = args[i + 1] if i + 1 < len(args) else ""
        if a in {"-X", "--method"}:
            method, i = nxt.upper(), i + 2
            continue
        if a.startswith("--method="):
            method = a.split("=", 1)[1].upper()
        elif a.startswith("-X") and len(a) > 2:
            method = a[2:].lstrip("=").upper()
        elif a in {"-f", "-F", "--field", "--raw-field", "--input"}:
            fields.append(nxt)
            i += 2
            continue
        elif a.startswith(("--field=", "--raw-field=", "--input=")):
            fields.append(a.split("=", 1)[1])
        elif a.startswith(("-f", "-F")) and len(a) > 2:
            fields.append(a[2:])
        i += 1
    if method in {"GET", "HEAD"}:
        return False
    if method:
        return True
    if "graphql" in positionals(args):
        return any(re.search(r"\bmutation\b", f, re.I) for f in fields)
    return bool(fields)


def gh_writes(args):
    i = 0
    while i < len(args) and args[i].startswith("-"):
        i += 2 if args[i] in {"-R", "--repo"} else 1
    if i >= len(args):
        return False
    top, rest = args[i], args[i + 1:]
    if top == "api":
        return gh_api_writes(rest)
    if top in GH_READ_TOP:
        return False
    if top == "auth":
        return not (rest and rest[0] in {"status", "token"})
    pos = positionals(rest)
    return not (pos and pos[0] in GH_READ_VERBS)


def skip_opts(args, with_value):
    i = 0
    while i < len(args) and args[i].startswith("-"):
        i += 2 if args[i] in with_value else 1
    return args[i:]


def deploys(name, args):
    pos = positionals(args)
    if name in {"kubectl", "oc"}:
        rest = skip_opts(args, KUBECTL_GLOBAL_ARG)
        if not rest:
            return False
        if rest[0] == "rollout":
            return bool(rest[1:]) and rest[1] in {"restart", "undo", "pause", "resume"}
        return rest[0] in KUBECTL_WRITE
    if name == "helm":
        rest = skip_opts(args, {"-n", "--namespace", "--kube-context", "--kubeconfig"})
        return bool(rest) and rest[0] in HELM_WRITE
    if name in {"terraform", "tofu", "terragrunt"}:
        if not pos:
            return False
        if pos[0] == "state":
            return len(pos) > 1 and pos[1] in {"mv", "rm", "push", "replace-provider"}
        return pos[0] in TERRAFORM_WRITE
    if name in PUBLISHERS and pos and pos[0] in PUBLISHERS[name]:
        return True
    if name in {"docker", "podman"} and len(pos) >= 2:
        if pos[0] == "stack" and pos[1] in {"deploy", "rm"}:
            return True
        if pos[0] == "service" and pos[1] in {"create", "update", "rm", "scale"}:
            return True
    if name in {"npm", "pnpm", "yarn", "bun"}:
        if pos and pos[0] in {"run", "run-script"} and len(pos) > 1:
            return bool(DEPLOY_TARGET.search(pos[1]))
        if name in {"yarn", "pnpm"} and pos and pos[0] == "npm" and pos[1:2] == ["publish"]:
            return True
        return name in {"yarn", "pnpm"} and bool(pos) and bool(DEPLOY_TARGET.search(pos[0]))
    if name in {"make", "gmake", "just"}:
        targets, i = [], 0
        while i < len(args):
            a = args[i]
            if a in MAKE_ARG:
                i += 2
                continue
            if not a.startswith("-") and not ASSIGNMENT.match(a):
                targets.append(a)
            i += 1
        return any(DEPLOY_TARGET.search(t) for t in targets)
    if name in {"mvn", "mvnw", "./mvnw"}:
        return "deploy" in pos
    if name in {"gradle", "gradlew", "./gradlew"}:
        return any(DEPLOY_TARGET.search(t) for t in pos)
    if name in CLOUD_CLIS:
        words = DEPLOY_WORDS | CLOUD_EXTRA.get(name, set())
        if name == "vercel" and not args:
            return True
        return any(a in words for a in args)
    return False


def unwrap(argv):
    """Strip assignments, keywords, and wrapper commands from the front."""
    while argv:
        head = argv[0]
        if head in KEYWORDS or ASSIGNMENT.match(head):
            argv = argv[1:]
        elif head in {"sudo", "doas"}:
            argv = skip_opts(argv[1:], {"-u", "-g", "-C", "-D", "-h", "-p", "-r", "-t", "-U"})
        elif head == "env":
            rest = skip_opts(argv[1:], {"-u", "-C", "-S"})
            while rest and ASSIGNMENT.match(rest[0]):
                rest = rest[1:]
            argv = rest
        elif head in {"command", "builtin", "exec", "nohup", "stdbuf", "caffeinate"}:
            argv = skip_opts(argv[1:], {"-o", "-e", "-i", "-w", "-t"})
        elif head == "nice":
            argv = skip_opts(argv[1:], {"-n"})
        elif head == "timeout":
            rest = skip_opts(argv[1:], {"-s", "--signal", "-k", "--kill-after"})
            argv = rest[1:]
        elif head == "xargs":
            argv = skip_opts(argv[1:], {"-I", "-n", "-P", "-L", "-d", "-s", "-E", "-a"})
        else:
            return argv
    return argv


def writes(argv, depth):
    argv = unwrap(argv)
    if not argv:
        return False
    name, args = os.path.basename(argv[0]), argv[1:]
    if name in SHELLS:
        for idx, a in enumerate(args):
            if a.startswith("-") and not a.startswith("--") and "c" in a[1:]:
                return idx + 1 < len(args) and command_writes(args[idx + 1], depth + 1)
        return False
    if name == "eval":
        return command_writes(" ".join(args), depth + 1)
    if name == "git":
        return git_writes(args)
    if name == "gh":
        return gh_writes(args)
    if name in DELETERS:
        return True
    if name == "find":
        if "-delete" in args:
            return True
        for flag in ("-exec", "-execdir", "-ok", "-okdir"):
            if flag in args:
                start = args.index(flag) + 1
                end = next((j for j in range(start, len(args)) if args[j] in {";", "+", "\\;"}), len(args))
                if writes(args[start:end], depth + 1):
                    return True
        return False
    return deploys(name, args)


def substitutions(s):
    out, i = [], 0
    while i < len(s):
        if s.startswith("$(", i) and not s.startswith("$((", i):
            depth, j = 0, i + 1
            while j < len(s):
                if s[j] == "(":
                    depth += 1
                elif s[j] == ")":
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            out.append(s[i + 2:j])
            i = j + 1
        elif s[i] == "`":
            j = s.find("`", i + 1)
            if j < 0:
                break
            out.append(s[i + 1:j])
            i = j + 1
        else:
            i += 1
    return out


def tokens(text):
    try:
        lex = shlex.shlex(text, posix=True, punctuation_chars=True)
        lex.whitespace_split = True
        lex.commenters = ""
        return list(lex)
    except ValueError:
        # Unparseable quoting: split on whitespace and operators, quotes dropped.
        return re.findall(r"[;&|()<>]+|[^\s;&|()<>'\"]+", text)


def simple_commands(command):
    text = command.replace("\\\n", " ").replace("\n", " ; ")
    current, skip_next = [], False
    for tok in tokens(text):
        if skip_next:
            skip_next = False
            continue
        if tok and set(tok) <= set("();<>|&"):
            if "<" in tok or ">" in tok:
                skip_next = True
                continue
            if current:
                yield current
            current = []
            continue
        current.append(tok)
    if current:
        yield current


def command_writes(command, depth=0):
    if depth > 4:
        return False
    for argv in simple_commands(command):
        if writes(argv, depth):
            return True
    return any(command_writes(sub, depth + 1) for sub in substitutions(command))


def decide(command):
    if command_writes(command):
        return REFUSED
    if "mktemp" in command:
        if not RUN_PREFIX.search(command) or not RUN_REDIRECT.search(command):
            return NOT_TEMPLATE
        if not RUN_CD.search(command):
            return NO_CD
        return None
    if "robot-ghosts-runner." not in command:
        return NOT_TEMPLATE
    for argv in simple_commands(command):
        argv = unwrap(argv)
        if argv and os.path.basename(argv[0]) not in LOG_READERS:
            return NOT_TEMPLATE
    return None


def main():
    try:
        data = json.load(sys.stdin)
        if data.get("agent_type") != "robot-ghosts:runner":
            return
        command = (data.get("tool_input") or {}).get("command") or ""
        reason = decide(command)
    except Exception as exc:  # fail closed: a guard error never lets a call through
        reason = "runner guard error ({}). Report this command as: exit: refused (guard error)".format(exc)
    if reason:
        json.dump({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                          "permissionDecision": "deny",
                                          "permissionDecisionReason": reason}}, sys.stdout)
        sys.stdout.write("\n")


if __name__ == "__main__":
    main()
