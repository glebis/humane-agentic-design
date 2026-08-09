#!/usr/bin/env python3
"""Score a review against oracle #2 — the accessibility violations axe found.

    python3 score_a11y.py --manifest PATH --report PATH [--arm with|without] [--json]

Separate from the contrast scorer on purpose. Two oracles, two domains, two
sets of numbers: averaging them would hide which one a review is good at, and
`design-tokens` owning colour while `layout-rules` owns structure is the whole
reason `routing_accuracy` becomes meaningful here. Until now every planted
defect had exactly one possible owner, so routing was close to given.

WHAT IS SCORED

  recall       violations axe reported that the review also reported
  routing      of those, how many named an owner axe's allow-list accepts
  padding      contrast-free findings matching no violation and no pair

`accepted_owners` is a SET. Some defects are defensibly routed to more than one
skill — an empty heading is both a missing string (`ux-writing`) and a broken
hierarchy (`layout-rules`) — and marking a defensible choice wrong would measure
the mapping's opinion rather than the review's judgement.

WHEN THE ORACLE DID NOT RUN, every metric is `null` and the domain is reported
**Not reviewed**. A machine without node must not produce a smaller-but-complete
looking result.
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "contrast"))

import score as contrast_scorer  # noqa: E402

# `#ax-heading-order` -> ax-heading-order, `html` -> html
SELECTOR = re.compile(r"[#.]?([A-Za-z][\w-]*)")


def _blob(finding):
    return " ".join((finding.get(k) or "") for k in
                    ("domain", "location", "before", "after", "why")).lower()


# How a human writes each rule. Rule ids are not vocabulary a reviewer is
# obliged to use, and requiring the id would score fluency in axe rather than
# whether the defect was found.
PHRASES = {
    "heading-order":        ("heading level", "heading hierarchy", "skips"),
    "empty-heading":        ("empty heading", "heading with no", "blank heading"),
    "html-has-lang":        ("lang attribute", "no language", "language is not"),
    "region":               ("landmark", "outside any region", "no main"),
    "landmark-one-main":    ("main landmark", "<main>", "no main"),
    "page-has-heading-one": ("no h1", "top-level heading", "heading one"),
}


def matches(violation, finding):
    """Does this finding name this violation?

    Three ways, any of which counts: it cites one of the violation's selectors,
    it names the rule id, or it uses the ordinary words for that defect.
    """
    text = _blob(finding)
    for selector in violation.get("selectors", []):
        token = SELECTOR.match(selector.strip())
        if token and token.group(1).lower() in text:
            return True
    rule = violation["rule"]
    if rule in text or rule.replace("-", " ") in text:
        return True
    return any(phrase in text for phrase in PHRASES.get(rule, ()))


def score(manifest, findings):
    axe = manifest.get("axe") or {}
    if not axe.get("available"):
        return {
            "result": "Not reviewed",
            "reason": axe.get("reason") or "oracle #2 did not run",
            "recall": None, "routing": None, "violations": None, "found": None,
        }

    violations = manifest.get("violations") or []
    found, routed = [], 0
    for v in violations:
        hits = [f for f in findings if matches(v, f)]
        if not hits:
            continue
        found.append(v["rule"])
        accepted = {o.lower() for o in v.get("accepted_owners", [])}
        if any(any(o in (f.get("domain") or "").lower() for o in accepted) for f in hits):
            routed += 1

    def ratio(n, d):
        return None if not d else round(n / d, 4)

    return {
        "result": f"{len(found)}/{len(violations)}",
        "violations": len(violations),
        "found": found,
        "recall": ratio(len(found), len(violations)),
        "routing": ratio(routed, len(found)),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--report", required=True)
    ap.add_argument("--arm", choices=("with", "without"))
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    findings, _ = contrast_scorer.load_report_text(
        Path(args.report).read_text(encoding="utf-8"))
    out = score(manifest, findings)
    out["arm"] = args.arm
    out["seed"] = manifest.get("seed")

    if args.json:
        print(json.dumps(out, indent=2))
    else:
        print(f"arm: {args.arm or '—'}  seed: {out['seed']}")
        if out.get("result") == "Not reviewed":
            print(f"  accessibility: Not reviewed — {out['reason']}")
        else:
            f = lambda v: "  — " if v is None else f"{v:.3f}"
            print(f"  violations found  {out['result']}   recall {f(out['recall'])}"
                  f"   routing {f(out['routing'])}")
            print(f"  rules found: {', '.join(out['found']) or 'none'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
