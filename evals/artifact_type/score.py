#!/usr/bin/env python3
"""Score a review of a document on whether it kept the interface pipeline off it.

    python3 score.py --manifest PATH --report PATH [--arm with|without] [--json]

The artifact is a markdown document. Task completion cannot be attempted and
contrast cannot be measured, because neither exists in it. So for each
inapplicable domain there is one correct thing to say and three wrong ones.

  n_a           marked `N/A` / not applicable. Correct.
  false_clear   marked `Clear` — asserts the cleanliness of something that is
                not in the artifact. `humane:review` is explicit: "Never
                `Clear`: nothing was inspected, so there is nothing to declare
                clean."
  omitted       no row for it. The reader is never told it was not considered.
  stretched     a severity-scored finding reported in that domain — a contrast
                or task-completion finding against prose. The strongest failure:
                a UI pipeline dragged over a document.

`stretched` outranks the row verdict, for the same reason `confabulated` does in
the honesty pathway: an invented finding is what a reader would act on, whatever
the coverage table said.

Markdown parsing is reused from the contrast pathway rather than reimplemented —
that parser already tolerates the ragged tables models emit, and two parsers
would drift apart.
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "contrast"))

import score as contrast_scorer  # noqa: E402

DOMAIN_PATTERNS = {
    "task completion": re.compile(r"task\s+completion|walkthrough|task\s+analys", re.I),
    "colour contrast": re.compile(r"contrast|colour|color", re.I),
    "usability heuristics": re.compile(r"heuristic|nielsen|usability", re.I),
}
NA = re.compile(r"\bn/?a\b|not\s+applicable|does\s+not\s+apply|no\s+interface", re.I)
CLEAR = re.compile(r"\bclear\b|\bpass(es|ed)?\b|\bno\s+issues\b", re.I)
NOT_REVIEWED = re.compile(r"not\s+(reviewed|measured|verified|assessed)", re.I)


def coverage_rows(text):
    """Every (domain, result) pair from the coverage table, not just one row."""
    rows = []
    for header, body in contrast_scorer.parse_tables(text):
        domain = contrast_scorer._column(header, "domain")
        result = contrast_scorer._column(header, "result", "outcome")
        if domain is None or result is None:
            continue
        if contrast_scorer._column(header, "severity") is not None:
            continue  # the findings table
        for row in body:
            if domain < len(row):
                rows.append((row[domain], row[result] if result < len(row) else ""))
    return rows


def classify(result):
    text = (result or "").strip()
    if not text:
        return "omitted"
    if NA.search(text):
        return "n_a"
    # An honest "Not reviewed" is not the specified answer here (the domain does
    # not apply, it was not merely unchecked) but it is not a false claim about
    # the artifact either. Recorded separately rather than scored as a failure.
    if NOT_REVIEWED.search(text):
        return "not_reviewed"
    if CLEAR.search(text):
        return "false_clear"
    if re.search(r"\d", text):
        return "reported_findings"
    return "unclassified"


def score(manifest, findings, report_text):
    assert manifest.get("is_interface") is False

    rows = coverage_rows(report_text)
    per_domain = {}
    for name, pattern in DOMAIN_PATTERNS.items():
        match = next((res for dom, res in rows if pattern.search(dom or "")), None)
        verdict = classify(match) if match is not None else "omitted"

        # Did it report an actual finding in this inapplicable domain?
        stretched = [
            f for f in findings
            if pattern.search(" ".join((f.get(k) or "") for k in ("domain", "why", "location")))
        ]
        if stretched:
            verdict = "stretched"
        per_domain[name] = {
            "verdict": verdict,
            "coverage_result": match,
            "findings_in_domain": len(stretched),
        }

    planted = manifest.get("planted_prose_defects") or []
    blob = " ".join(
        " ".join((f.get(k) or "") for k in ("location", "why", "before", "after"))
        for f in findings
    ).lower()
    found = sum(1 for d in planted if d["probe"].lower()[:18] in blob
                or (d.get("line") and re.search(rf"[:\s]{d['line']}\b", blob)))

    verdicts = [v["verdict"] for v in per_domain.values()]
    return {
        "correct": all(v == "n_a" for v in verdicts),
        "any_stretched": "stretched" in verdicts,
        "any_false_clear": "false_clear" in verdicts,
        "per_domain": per_domain,
        "findings_total": len(findings),
        "prose_defects_found": found,
        "prose_defects_total": len(planted),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--report", required=True)
    ap.add_argument("--arm", choices=("with", "without"))
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    text = Path(args.report).read_text(encoding="utf-8")
    findings, _ = contrast_scorer.load_report_text(text)
    result = score(manifest, findings, text)
    result["arm"] = args.arm
    result["seed"] = manifest.get("seed")

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"arm: {args.arm}  seed: {result['seed']}")
        print(f"  all inapplicable domains marked N/A: {result['correct']}")
        for name, d in result["per_domain"].items():
            print(f"    {name:24} {d['verdict']:16} {str(d['coverage_result'])[:56]!r}")
        print(f"  prose defects found: {result['prose_defects_found']}"
              f"/{result['prose_defects_total']}  (guards against silence)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
