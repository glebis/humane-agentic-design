#!/usr/bin/env python3
"""Score the fan-out pathway: inline review against four fanned-out domains.

    python3 score.py --manifest PATH --inline PATH --fanout DIR [--json]

WHY. `humane:review` 0.13.0 added a fan-out mode on an argument alone: that a
host which compacts a full context summarizes rather than fails, so evidence
from the first domain can be summarized away while the impression of coverage
survives to the verdict. That is a mechanism, not a measurement. This scores
whether it shows up.

The fan-out arm's report is the four domain tables **concatenated**. Nothing
here judges, ranks, or filters them — a consolidator applying taste would be a
third variable, and the question is what the arms found, not how well I merge.

POSITION BIAS is the interesting number. If evidence really does decay as a
context fills, the pairs an inline review reports should cluster toward the top
of the document. Each planted pair has an index; `position_bias` is the mean
index of the ones a report matched, normalised to 0..1 against the planted set's
own index range. 0.5 is what an unbiased reader scores. Materially below 0.5
means the tail of the page went unreported — which is the mechanism, visible.

It is a weak signal on its own: a reviewer may simply run out of effort rather
than context, and this harness cannot tell those apart. Reported as evidence,
never as proof.
"""

import argparse
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "contrast"))

import score as contrast_scorer  # noqa: E402


def concat_domains(directory):
    """The fan-out arm's report: every domain table, mechanically joined."""
    parts = sorted(Path(directory).glob("domain-*.md"))
    return "\n\n".join(p.read_text(encoding="utf-8") for p in parts), [p.name for p in parts]


def position_bias(manifest, matched_ids):
    """Mean normalised index of the planted pairs a report matched.

    Returns None when fewer than two planted pairs were matched — a mean over
    one point says nothing, and reporting it as 0.0 or 1.0 would invent a
    finding out of a sample of one.
    """
    planted = [p for p in manifest["pairs"] if p.get("planted")]
    if len(planted) < 2:
        return None
    order = {p["id"]: i for i, p in enumerate(planted)}
    hits = [order[i] for i in matched_ids if i in order]
    if len(hits) < 2:
        return None
    return round(statistics.mean(hits) / (len(planted) - 1), 4)


def score_arm(manifest, text):
    findings, coverage = contrast_scorer.load_report_text(text)
    result = contrast_scorer.score(manifest, findings, coverage)
    matched = result["report"]["matched_pairs"]
    result["metrics"]["position_bias"] = position_bias(manifest, matched)
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--inline", required=True, help="the inline arm's report")
    ap.add_argument("--fanout", required=True, help="directory of domain-*.md tables")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    inline = score_arm(manifest, Path(args.inline).read_text(encoding="utf-8"))
    fan_text, domains = concat_domains(args.fanout)
    fan = score_arm(manifest, fan_text)

    out = {
        "planted": manifest["counts"]["planted"],
        "pairs": manifest["counts"]["pairs"],
        "domains_concatenated": domains,
        "inline": inline["metrics"],
        "fanout": fan["metrics"],
        "inline_matched": len(inline["report"]["matched_pairs"]),
        "fanout_matched": len(fan["report"]["matched_pairs"]),
    }
    if args.json:
        print(json.dumps(out, indent=2))
        return 0

    print(f"fixture: {out['pairs']} pairs, {out['planted']} planted")
    print(f"fanout arm = {len(domains)} domain tables concatenated: {', '.join(domains)}\n")
    print(f"{'metric':<22}{'inline':>10}{'fanned out':>13}")
    print("-" * 45)
    for k in ("recall", "recall_disagreement", "precision", "padding",
              "routing_accuracy", "position_bias"):
        f = lambda v: "   —  " if v is None else f"{v:.3f}"
        print(f"{k:<22}{f(inline['metrics'][k]):>10}{f(fan['metrics'][k]):>13}")
    print("\nposition_bias: mean normalised index of matched planted pairs.")
    print("0.5 is unbiased; materially below means the tail of the page went unreported.")
    print("\nn = 1 per arm, one fixture. A smoke test, not a result.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
