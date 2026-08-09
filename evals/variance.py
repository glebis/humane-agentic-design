#!/usr/bin/env python3
"""How much does an identical run vary? The denominator for every other number.

    python3 variance.py --manifest PATH --arm-dir DIR [--label with] [--json]

WHY. Every result in this harness has been one trial per arm, captioned "smoke
test", with no measurement of run-to-run spread. So a reported gap of 0.87
against 0.80 might be a finding or might be two draws from the same
distribution, and nothing published so far could tell the difference.

This runs the existing scorer over every `trial-*.md` in one arm directory and
reports the range and standard deviation of each metric.

READING IT. Compare a between-arm gap against within-arm spread:

  gap  <  spread   the gap is not distinguishable from noise. Withdraw it.
  gap  ~= spread   suggestive at best; more trials or nothing.
  gap  >  spread   worth reporting, still without a p-value at this n.

That comparison is the whole purpose. A harness that reports differences it
cannot separate from its own noise is generating numbers, not evidence.
"""

import argparse
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "contrast"))

import score as contrast_scorer  # noqa: E402

METRICS = ("recall", "recall_disagreement", "precision", "padding", "routing_accuracy")


def collect(manifest, arm_dir):
    rows = []
    for report in sorted(Path(arm_dir).glob("trial-*.md")):
        findings, coverage = contrast_scorer.load_report_text(
            report.read_text(encoding="utf-8"))
        rows.append((report.name, contrast_scorer.score(manifest, findings, coverage)["metrics"]))
    return rows


def spread(values):
    """Range and sample stdev over the non-null values.

    Nulls are excluded, never coerced. A precision of `null` means the report
    had no contrast findings — undefined, not zero — and averaging it in as 0
    would manufacture variance that did not happen.
    """
    present = [v for v in values if v is not None]
    if not present:
        return {"n": 0, "mean": None, "range": None, "stdev": None,
                "min": None, "max": None}
    return {
        "n": len(present),
        "mean": round(statistics.mean(present), 4),
        "min": round(min(present), 4),
        "max": round(max(present), 4),
        "range": round(max(present) - min(present), 4),
        "stdev": round(statistics.stdev(present), 4) if len(present) > 1 else 0.0,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--arm-dir", required=True)
    ap.add_argument("--label", default="")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    rows = collect(manifest, args.arm_dir)
    if len(rows) < 2:
        print(f"{args.arm_dir}: {len(rows)} trial(s) — need at least 2 to speak "
              "about spread at all", file=sys.stderr)
        return 1

    out = {m: spread([r[1].get(m) for r in rows]) for m in METRICS}
    if args.json:
        print(json.dumps({"arm": args.label, "trials": len(rows), "spread": out}, indent=2))
        return 0

    print(f"arm: {args.label or args.arm_dir}   trials: {len(rows)}")
    print(f"{'metric':<22}{'mean':>8}{'min':>8}{'max':>8}{'range':>9}{'stdev':>9}")
    print("-" * 64)
    for m in METRICS:
        s = out[m]
        f = lambda v: "   —  " if v is None else f"{v:.3f}"
        print(f"{m:<22}{f(s['mean']):>8}{f(s['min']):>8}{f(s['max']):>8}"
              f"{f(s['range']):>9}{f(s['stdev']):>9}  (n={s['n']})")
    print("\nper trial:")
    for name, metrics in rows:
        r = metrics.get("recall")
        p = metrics.get("precision")
        print(f"  {name:<12} recall {('%.2f' % r) if r is not None else '  — '}"
              f"   precision {('%.2f' % p) if p is not None else '  — '}"
              f"   padding {metrics.get('padding')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
