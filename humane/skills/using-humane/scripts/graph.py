#!/usr/bin/env python3
"""Read the handoff graph declared in every skill's frontmatter and print routes.

Claude Code's loader ignores the `handoffs:` / `accepts:` / `orchestrates:` keys
— they exist so the cycle's shape is data rather than prose spread across
fourteen files. This script is what turns that data back into an answer to the
only question that matters mid-cycle: *I just finished X, what now?*

    python3 graph.py --from layout-rules   # what layout-rules hands to, and when
    python3 graph.py --to ux-writing       # who hands into ux-writing, and when
    python3 graph.py                       # the whole graph
    python3 graph.py --mermaid             # the whole graph as a mermaid diagram

Standard library only, deliberately: PyYAML is not stdlib, and this must run on
a machine that has nothing installed. The blocks are a fixed shape written by
this repo's own tests, so they are parsed directly rather than as general YAML.
"""

import argparse
import re
import sys
from pathlib import Path

# scripts/ -> using-humane/ -> skills/
SKILLS_DIR = Path(__file__).resolve().parent.parent.parent


def parse_skill(path):
    """Return {name, handoffs: [(to, when)], accepts: [from], orchestrates: [name]}.

    Only the graph keys are read. Anything else in the frontmatter is ignored,
    including the description, which is long and irrelevant here.
    """
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        return None

    skill = {
        "name": path.parent.name,
        "handoffs": [],
        "accepts": [],
        "orchestrates": [],
    }
    section = None
    for line in match.group(1).splitlines():
        top = re.match(r"^([a-z]+):\s*$", line)
        if top:
            section = top.group(1) if top.group(1) in skill else None
            continue
        if re.match(r"^[a-zA-Z_-]+:", line):  # any other top-level key ends the section
            section = None
            continue
        if section is None:
            continue

        if section == "handoffs":
            to = re.match(r"^\s*-\s*to:\s*(.+?)\s*$", line)
            if to:
                skill["handoffs"].append([to.group(1), ""])
                continue
            when = re.match(r"^\s*when:\s*(.+?)\s*$", line)
            if when and skill["handoffs"]:
                skill["handoffs"][-1][1] = when.group(1).strip('"')
        elif section == "accepts":
            src = re.match(r"^\s*-\s*from:\s*(.+?)\s*$", line)
            if src:
                skill["accepts"].append(src.group(1))
        elif section == "orchestrates":
            item = re.match(r"^\s*-\s*(.+?)\s*$", line)
            if item:
                skill["orchestrates"].append(item.group(1))

    return skill


def load():
    skills = {}
    for path in sorted(SKILLS_DIR.glob("*/SKILL.md")):
        parsed = parse_skill(path)
        if parsed:
            skills[parsed["name"]] = parsed
    return skills


def unknown(name, skills):
    print(f"no skill named `{name}`. Known: {', '.join(sorted(skills))}", file=sys.stderr)
    return 2


def show_from(name, skills):
    if name not in skills:
        return unknown(name, skills)
    skill = skills[name]
    if skill["orchestrates"]:
        print(f"`humane:{name}` orchestrates (calls, and consolidates the findings of):")
        for target in skill["orchestrates"]:
            print(f"  humane:{target}")
        print()
    if not skill["handoffs"]:
        print(f"`humane:{name}` declares no handoffs — it is a terminal step.")
        return 0
    print(f"After `humane:{name}`, hand off to:")
    for target, when in skill["handoffs"]:
        print(f"  humane:{target}")
        print(f"      when {when}")
    return 0


def show_to(name, skills):
    if name not in skills:
        return unknown(name, skills)
    inbound = [
        (other, when)
        for other, skill in skills.items()
        for target, when in skill["handoffs"]
        if target == name
    ]
    callers = [other for other, s in skills.items() if name in s["orchestrates"]]
    if callers:
        print(f"`humane:{name}` is orchestrated by: {', '.join('humane:' + c for c in callers)}")
        print()
    if not inbound:
        print(f"Nothing hands into `humane:{name}` — it is an entry point.")
        return 0
    print(f"Hands into `humane:{name}`:")
    for other, when in sorted(inbound):
        print(f"  humane:{other}")
        print(f"      when {when}")
    return 0


def show_all(skills):
    for name in sorted(skills):
        skill = skills[name]
        if not (skill["handoffs"] or skill["orchestrates"]):
            continue
        print(f"humane:{name}")
        for target in skill["orchestrates"]:
            print(f"  calls    humane:{target}")
        for target, when in skill["handoffs"]:
            print(f"  hands to humane:{target} — when {when}")
        print()
    # The router reads the graph; it is not a step in it, so it is not a
    # skill anyone is missing a route to.
    isolated = sorted(
        n
        for n, s in skills.items()
        if n != "using-humane" and not (s["handoffs"] or s["accepts"] or s["orchestrates"])
    )
    if isolated:
        print(f"standalone (no declared route): {', '.join(isolated)}")
    return 0


def show_mermaid(skills):
    print("flowchart LR")
    for name in sorted(skills):
        for target, _ in skills[name]["handoffs"]:
            print(f"    {name} --> {target}")
        for target in skills[name]["orchestrates"]:
            print(f"    {name} -.calls.-> {target}")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--from", dest="source", metavar="SKILL", help="what this skill hands to")
    parser.add_argument("--to", dest="target", metavar="SKILL", help="who hands into this skill")
    parser.add_argument("--mermaid", action="store_true", help="print the whole graph as mermaid")
    args = parser.parse_args()

    skills = load()
    if not skills:
        print(f"no skills found under {SKILLS_DIR}", file=sys.stderr)
        return 1
    if args.source:
        return show_from(args.source, skills)
    if args.target:
        return show_to(args.target, skills)
    if args.mermaid:
        return show_mermaid(skills)
    return show_all(skills)


if __name__ == "__main__":
    sys.exit(main())
