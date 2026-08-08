#!/usr/bin/env python3
"""Aggregate scored arms across seeds into one comparison table.

    python3 aggregate.py runs/            # every seed under runs/
    python3 aggregate.py runs/ --json

One trial is noise. The point of this script is to make the number of trials
behind a claim impossible to lose sight of: every row prints its n, and a
per-seed breakdown sits under the summary so a mean that hides a split decision
is visible rather than averaged away.

It reports means and does not compute a p-value. With n in the low single digits
a significance test would dress up a result the sample cannot support — the
honest output is the numbers, the n, and the spread.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

METRICS = ("recall", "recall_disagreement", "precision", "padding",
           "routing_accuracy")
HERE = Path(__file__).resolve().parent


def score(manifest, report, arm):
    """Shell out to score.py so there is exactly one scoring implementation."""
    out = subprocess.run(
        [sys.executable, str(HERE / "score.py"), "--manifest", str(manifest),
         "--report", str(report), "--arm", arm, "--json"],
        capture_output=True, text=True,
    )
    if out.returncode != 0:
        raise RuntimeError(f"score.py failed on {report}:\n{out.stderr}")
    return json.loads(out.stdout)


def collect(runs_dir):
    rows = []
    for seed_dir in sorted(Path(runs_dir).glob("seed-*")):
        manifest = seed_dir / "manifest.json"
        if not manifest.exists():
            continue
        for arm in ("with", "without"):
            for report in sorted((seed_dir / "arms" / arm).glob("trial-*.md")):
                result = score(manifest, report, arm)
                rows.append({
                    "seed": seed_dir.name, "arm": arm, "trial": report.stem,
                    "metrics": result["metrics"],
                })
    return rows


def mean(values):
    """Mean of the non-null values, or None when every value was null.

    A null metric means its denominator was zero — the reviewer reported
    nothing, so precision is undefined rather than perfect. Averaging those in
    as 0.0, or skipping the row silently, both misreport. They are excluded and
    the surviving count is printed alongside.
    """
    present = [v for v in values if v is not None]
    if not present:
        return None, 0
    return round(sum(present) / len(present), 4), len(present)


def summarize(rows):
    out = {}
    for arm in ("with", "without"):
        arm_rows = [r for r in rows if r["arm"] == arm]
        summary = {"n": len(arm_rows)}
        for metric in METRICS:
            value, count = mean([r["metrics"].get(metric) for r in arm_rows])
            summary[metric] = value
            summary[f"{metric}_n"] = count
        summary["false_clear"] = sum(
            1 for r in arm_rows if r["metrics"].get("false_clear"))
        out[arm] = summary
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("runs", help="directory holding seed-* subdirectories")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    rows = collect(args.runs)
    if not rows:
        print(f"no scored reports found under {args.runs}", file=sys.stderr)
        return 1
    summary = summarize(rows)

    if args.json:
        print(json.dumps({"summary": summary, "trials": rows}, indent=2))
        return 0

    w, o = summary["with"], summary["without"]
    print(f"{'metric':<24}{'with humane':>14}{'without':>12}")
    print("-" * 50)
    for metric in METRICS:
        fmt = (lambda v: "  —  " if v is None else f"{v:.3f}")
        print(f"{metric:<24}{fmt(w[metric]):>14}{fmt(o[metric]):>12}")
    print(f"{'false_clear (count)':<24}{w['false_clear']:>14}{o['false_clear']:>12}")
    print(f"{'n (trials)':<24}{w['n']:>14}{o['n']:>12}")

    print("\nper seed:")
    for row in rows:
        m = row["metrics"]
        rec = "  — " if m.get("recall") is None else f"{m['recall']:.2f}"
        dis = "  — " if m.get("recall_disagreement") is None else f"{m['recall_disagreement']:.2f}"
        print(f"  {row['seed']:<12} {row['arm']:<8} recall {rec}  "
              f"disagreement {dis}  false_clear {m.get('false_clear')}")

    if min(w["n"], o["n"]) < 5:
        print(f"\nn is {min(w['n'], o['n'])} per arm. Treat this as a smoke "
              "test, not a result — single-digit trials on model output are noise.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
