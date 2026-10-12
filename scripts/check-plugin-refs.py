#!/usr/bin/env python3
"""Checks that the marketplace, its plugins, and every <plugin>:<name> reference agree.

Each marketplace entry must point at a plugin manifest with the same name. Each
agent's and skill's frontmatter name must match its file or directory name.
Every <plugin>:<name> in the repository must name one of that plugin's agents or
skills. A stale name in a skill or agent fails at dispatch, and a stale name in
a hook silently turns the hook off.
Run: python3 scripts/check-plugin-refs.py
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {".git", "dist", "node_modules"}


def frontmatter_name(path):
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for line in lines[1:]:
        if line.strip() == "---":
            break
        match = re.match(r"name:\s*(\S+)\s*$", line)
        if match:
            return match.group(1).strip("'\"")
    return None


def text_files():
    for path in sorted(ROOT.rglob("*")):
        rel = path.relative_to(ROOT)
        if any(part in SKIP_DIRS for part in rel.parts) or not path.is_file():
            continue
        try:
            yield rel, path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue


def plugin_names(plugin_dir, errors):
    names = set()
    for agent in sorted((plugin_dir / "agents").glob("*.md")):
        got = frontmatter_name(agent)
        if got != agent.stem:
            errors.append(f"{agent.relative_to(ROOT)}: frontmatter name {got!r}, file name {agent.stem!r}")
        names.add(agent.stem)
    for skill in sorted((plugin_dir / "skills").glob("*/SKILL.md")):
        got = frontmatter_name(skill)
        if got != skill.parent.name:
            errors.append(f"{skill.relative_to(ROOT)}: frontmatter name {got!r}, directory name {skill.parent.name!r}")
        names.add(skill.parent.name)
    return names


def main():
    errors = []
    marketplace = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    known = {}
    for entry in marketplace.get("plugins", []):
        name, source = entry.get("name"), entry.get("source")
        if not isinstance(source, str):
            continue  # a remote source has no files here to check
        plugin_dir = (ROOT / source).resolve()
        manifest = plugin_dir / ".claude-plugin" / "plugin.json"
        if not manifest.is_file():
            errors.append(f".claude-plugin/marketplace.json: {name!r} source {source!r} has no .claude-plugin/plugin.json")
            continue
        manifest_name = json.loads(manifest.read_text(encoding="utf-8")).get("name")
        if manifest_name != name:
            errors.append(f"{manifest.relative_to(ROOT)}: name {manifest_name!r}, marketplace entry {name!r}")
        known[name] = plugin_names(plugin_dir, errors)

    refs = 0
    if known:
        pattern = re.compile(r"(?<![\w-])(" + "|".join(map(re.escape, known)) + r"):([a-z0-9][a-z0-9-]*)")
        for rel, text in text_files():
            for lineno, line in enumerate(text.splitlines(), 1):
                for match in pattern.finditer(line):
                    refs += 1
                    plugin, target = match.groups()
                    if target not in known[plugin]:
                        errors.append(f"{rel}:{lineno}: {match.group(0)} names no agent or skill of {plugin}")

    for error in errors:
        print(error)
    if errors:
        return 1
    print(f"plugin references OK: {len(known)} plugin(s), {refs} reference(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
