#!/usr/bin/env python3
"""Generate a document fixture — an artifact that is deliberately NOT an interface.

    python3 generate.py --seed 1337 --out DIR

WHY. `humane:review` §1 specifies a reduced pipeline for a document: run
`ux-writing` for the prose and `layout-rules` for structure only, and "Skip
`walkthrough`, `nielsen-heuristics`, and contrast — mark them `N/A (not an
interface)`, not `Clear`". Its Output section draws the distinction that makes
this testable: `N/A` means nothing was inspected because nothing applies, while
`Clear` is an assertion about the artifact.

So this fixture is a README. There is no markup, no colour, no control, nothing
to operate — a review cannot walk a task or measure a contrast ratio here
because neither exists. Ground truth is a property of construction, not a
measurement, so no oracle is involved.

Real prose defects are planted (an install step that names no command, a summary
line that adds no conclusion, a named entity that is never linked, a version
inconsistency) so that a review returning nothing cannot score well by default.
Those belong to `ux-writing` and `layout-rules` under the reduced pipeline and
are the guard, not the measurement.
"""

import argparse
import json
import random
from pathlib import Path

# Each defect is checkable by a distinctive string a reviewer would have to
# quote or locate. Keyed to the skill that owns it under CLAUDE.md.
DEFECTS = [
    {"key": "install_no_command",
     "what": "the install section tells the reader to install but names no command",
     "owner": "ux-writing", "probe": "Install it the usual way"},
    {"key": "summary_no_conclusion",
     "what": "a summary line that restates the topic instead of stating a conclusion",
     "owner": "ux-writing", "probe": "This section covers configuration"},
    {"key": "unlinked_entity",
     "what": "a named tool is referenced repeatedly and never linked",
     "owner": "ux-writing", "probe": "Ledgerline"},
    {"key": "version_inconsistency",
     "what": "the version in the badge and the version in the install text disagree",
     "owner": "ux-writing", "probe": "2.4.0"},
    {"key": "no_heading_hierarchy",
     "what": "every heading is the same level, so the document has no structure",
     "owner": "layout-rules", "probe": "## "},
]

BODY = """# Ledgerline

![version](https://img.shields.io/badge/version-2.4.0-blue)

Ledgerline reconciles multi-entity ledgers.

## Install

Install it the usual way, then run the setup step. Version 2.7.1 is
the current release and is recommended for all users.

## Configuration

This section covers configuration. Ledgerline reads its configuration from a
file in the working directory. Ledgerline will fall back to defaults when that
file is absent, and Ledgerline logs which layer won.

## Reconciling

Point Ledgerline at a directory of statements. Entities are matched on account
number first and on normalised name second.

## Troubleshooting

If reconciliation stalls, check that every statement carries a settlement date.
Statements without one are held back and reported at the end of the run.
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    # Vary the ordering of the two middle sections by seed so the three runs are
    # not byte-identical documents, while keeping every planted defect present.
    parts = BODY.split("\n## ")
    head, sections = parts[0], parts[1:]
    middle = sections[1:3]
    rng.shuffle(middle)
    body = head + "\n## " + "\n## ".join([sections[0]] + middle + sections[3:])
    (out / "README.md").write_text(body, encoding="utf-8")

    lines = body.splitlines()
    located = []
    for d in DEFECTS:
        line = next((i + 1 for i, l in enumerate(lines) if d["probe"] in l), None)
        located.append({**d, "line": line})

    manifest = {
        "seed": args.seed,
        "pathway": "artifact_type",
        "fixture": "README.md",
        "is_interface": False,
        "why_not_an_interface": (
            "A markdown document. No markup, no colour declarations, no controls, "
            "nothing to operate. Task completion cannot be attempted and contrast "
            "cannot be measured because neither exists in the artifact."
        ),
        "inapplicable_domains": ["task completion", "colour contrast", "usability heuristics"],
        "applicable_domains": ["interface copy / prose (ux-writing)",
                               "structure and hierarchy (layout-rules)"],
        "correct_results": ["n/a", "not applicable"],
        "incorrect_results": ["clear"],
        "planted_prose_defects": located,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n",
                                       encoding="utf-8")
    print(f"{out}: README.md, {len(located)} prose defects, not an interface")


if __name__ == "__main__":
    main()
