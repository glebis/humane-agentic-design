#!/usr/bin/env python3
"""Score one saved `humane:review` report against one contrast manifest.

WHY THIS EXISTS. The first pathway of an eval harness asking whether running
`humane:review` beats not running it. Ground truth is deliberately narrow —
colour contrast only — because it is the one design domain with a machine
checkable answer: a foreground/background pair either clears the bar or it does
not. Everything else a review says is judgement; this is arithmetic.

WHY IT PARSES MARKDOWN. The thing under evaluation is the report a model
actually emits, in the format `humane/skills/review/SKILL.md` specifies: a
"Scope and coverage" table (Domain | Evidence inspected | Result) and a
"Findings" table (# | Severity | Domain | Location | Before | After | Why).
Inventing an eval-only output format would measure a thing no user ever
receives. So the parser is tolerant of whitespace, alignment rows, ragged pipes,
missing columns, and prose wrapped around the tables — models vary in all of
those and none of that variation is a defect worth scoring.

WHY THE NULLS MATTER. Every metric here has a denominator that can legitimately
be zero, and each of them reads as a *perfect score* if you divide anyway:
precision 1.0 for a review that reported nothing, recall 1.0 for a manifest with
nothing planted. A harness built to catch a reviewer overstating its coverage
must not overstate its own. Zero denominator emits `null` plus a stated reason,
never a number.

Usage:
    python3 score.py --manifest PATH --report PATH [--report-json PATH]
                     [--arm with|without] [--json]
"""

import argparse
import json
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Markdown table ingestion
# ---------------------------------------------------------------------------

# An alignment row: | --- | :---: | ---: |  (and any spacing thereof)
_ALIGNMENT_ROW = re.compile(r"^[\s|:\-]+$")


def _split_row(line):
    """Split one markdown table row into stripped cells.

    Tolerates leading and trailing pipes being present, absent, or one of each,
    which is the most common way a hand-written table differs from a generated
    one.
    """
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [cell.strip() for cell in line.split("|")]


def parse_tables(text):
    """Yield every markdown table in `text` as (header_cells, [row_cells, ...]).

    A table is any run of consecutive pipe-bearing lines. Alignment rows are
    dropped wherever they appear rather than assumed to be line two, because a
    model that omits one still produced a readable table and a model that
    indents one has not produced a defect.
    """
    tables = []
    block = []
    for line in text.splitlines() + [""]:
        if "|" in line and line.strip():
            block.append(line)
            continue
        if block:
            rows = [_split_row(l) for l in block if not _ALIGNMENT_ROW.match(l.strip())]
            if len(rows) >= 1:
                tables.append((rows[0], rows[1:]))
            block = []
    return tables


def _norm(cell):
    """Lowercase a cell and strip the decoration models wrap words in."""
    return re.sub(r"[`*_~]", "", (cell or "")).strip().lower()


def _column(header, *names):
    """Index of the first header cell equal to one of `names`, else None."""
    normalized = [_norm(h) for h in header]
    for name in names:
        if name in normalized:
            return normalized.index(name)
    return None


def find_findings_table(text):
    """Return the findings table as a list of dicts, or [] if there is none.

    A report with no parseable findings table is a VALID input meaning zero
    findings — a reviewer that found nothing writes "No actionable findings."
    and omits the table, exactly as the skill instructs. Crashing on it would
    score honest emptiness as a harness error.
    """
    for header, rows in parse_tables(text):
        severity = _column(header, "severity")
        location = _column(header, "location", "locator", "where")
        if severity is None or location is None:
            continue
        domain = _column(header, "domain", "owner", "skill")
        why = _column(header, "why", "reason", "rationale")
        before = _column(header, "before")
        after = _column(header, "after")

        findings = []
        for row in rows:
            def cell(idx):
                return row[idx] if idx is not None and idx < len(row) else ""

            if not any(cell(i) for i in (severity, location, domain, why)):
                continue  # a blank spacer row, not a finding
            findings.append(
                {
                    "severity": cell(severity),
                    "domain": cell(domain),
                    "location": cell(location),
                    "before": cell(before),
                    "after": cell(after),
                    "why": cell(why),
                }
            )
        return findings
    return []


CONTRAST_ROW = re.compile(r"contrast|colour|color", re.IGNORECASE)


def find_coverage_result(text):
    """Return the Result cell of the contrast/colour coverage row, or None.

    None means the row is absent entirely, which is a distinct and worse thing
    than `Not reviewed`: the reader is never told the domain went unexamined.
    """
    for header, rows in parse_tables(text):
        domain = _column(header, "domain")
        result = _column(header, "result", "outcome")
        if domain is None or result is None:
            continue
        if _column(header, "severity") is not None:
            continue  # that is the findings table, not coverage
        for row in rows:
            if domain < len(row) and CONTRAST_ROW.search(row[domain] or ""):
                return row[result] if result < len(row) else ""
    return None


def load_report_text(text):
    """Findings and the contrast coverage result from a markdown report."""
    return find_findings_table(text), find_coverage_result(text)


def load_report_data(data):
    """Findings and the contrast coverage result from a structured report.

    Secondary to markdown on purpose: evaluating the real deliverable beats
    inventing an eval-only format. Kept for harnesses that already hold the
    review as data.
    """
    if isinstance(data, list):
        data = {"findings": data}
    findings = [
        {k: str(raw.get(k, "") or "") for k in
         ("severity", "domain", "location", "before", "after", "why")}
        for raw in (data.get("findings") or [])
    ]
    coverage = data.get("coverage")
    result = None
    if isinstance(coverage, dict):
        for key, value in coverage.items():
            if CONTRAST_ROW.search(str(key)):
                result = str(value)
                break
    elif coverage:
        result = str(coverage)
    return findings, result


def load_report(markdown_path=None, json_path=None):
    """Load findings and the coverage result from whichever source was given."""
    if json_path:
        return load_report_data(json.loads(Path(json_path).read_text(encoding="utf-8")))
    return load_report_text(Path(markdown_path).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Matching a finding to a pair
# ---------------------------------------------------------------------------

PAIR_ID = re.compile(r"pair-\d+", re.IGNORECASE)
HEX = re.compile(r"#[0-9a-fA-F]{3,8}")


def _hexes(text):
    """Normalized hex colours in `text`, expanding #abc to #aabbcc."""
    out = set()
    for raw in HEX.findall(text or ""):
        value = raw.lower()
        if len(value) == 4:
            value = "#" + "".join(c * 2 for c in value[1:])
        out.add(value)
    return out


def match_finding(finding, pairs, fixture):
    """Match one finding to EVERY pair it locates.

    Returns (pairs_list, strategy_or_None, multi_bool). The list is empty when
    nothing matched.

    One finding legitimately covers many pairs. `humane:review` §8 requires it:
    "One root cause is one finding, listing every confirmed location — not a row
    per occurrence." An earlier version of this scorer attributed a finding to a
    single best match and counted the rest as ambiguous, which scored a review
    that obeyed the consolidation rule as though it had missed the defects it
    had actually found and listed. On the first real comparison that inverted
    the result — the arm that found 6 of 6 scored 0.33 against an arm that found
    4 of 6. A scorer that punishes the skill for following its own rules
    measures the scorer, not the skill.

    Priority is fixed and resolves across tiers: element id, then
    `fixture.html:LINE`, then both hex colours. The first tier that hits wins,
    and every pair it names is returned.
    """
    location = finding.get("location", "") or ""
    why = finding.get("why", "") or ""
    by_id = {p["id"].lower(): p for p in pairs if p.get("id")}
    hits = [by_id[m.lower()] for m in PAIR_ID.findall(location) if m.lower() in by_id]
    if hits:
        unique = _dedupe(hits)
        return unique, "id", len(unique) > 1

    stem = re.escape(Path(fixture).name) if fixture else r"[\w.\-/]+"
    lines = {int(m) for m in re.findall(rf"{stem}\s*:\s*(\d+)", location)}
    if lines:
        hits = [p for p in pairs if p.get("line") in lines]
        if hits:
            unique = _dedupe(hits)
            return unique, "line", len(unique) > 1

    found = _hexes(location) | _hexes(why)
    if found:
        hits = [
            p
            for p in pairs
            if _hexes(p.get("fg", "")) <= found and _hexes(p.get("bg", "")) <= found
            and p.get("fg") and p.get("bg")
        ]
        if hits:
            unique = _dedupe(hits)
            return unique, "hex", len(unique) > 1

    return [], None, False


def _dedupe(pairs):
    """Preserve order, drop repeats of the same pair id."""
    seen, out = set(), []
    for p in pairs:
        key = p.get("id") or id(p)
        if key not in seen:
            seen.add(key)
            out.append(p)
    return out


# Explicit contrast vocabulary, or a quoted measurement. Deliberately NOT bare
# "colour" and NOT the owning skill's name: a `layout-rules` finding that the
# same status badge is painted in two unrelated palettes is about consistency,
# not contrast, and a `ux-writing` finding about duplicate labels is about
# neither. Both quote hex values, and both were being counted as contrast
# findings — which inflated `padding` for exactly the reviews that cover more
# than one domain. The harness was penalising breadth again, in a second place.
CONTRAST_KEYWORDS = re.compile(
    r"contrast|wcag|apca|luminance|legib|readab"
    r"|\d+(\.\d+)?\s*:\s*1|\bLc\s*-?\d",
    re.IGNORECASE,
)


def is_contrast_finding(finding, matched):
    """Whether a finding is about contrast at all.

    A locator match is NOT sufficient, though an earlier version treated it as
    conclusive. Every element in the fixture is a `pair-NN`, so a finding about
    heading order or a dead link matches a pair and was being counted as a
    contrast finding. That penalised precisely the reviews that cover more than
    one domain: an arm reporting layout, copy and usability findings against
    those same elements had every one of them scored as contrast padding, while
    an arm that only ever discussed colour was barely touched. The harness was
    rewarding narrowness.

    So the test is evidence that the finding is *about* colour: contrast
    vocabulary anywhere in its cells, or the pair's colours quoted in it.

    The Domain cell alone is deliberately not the test — `routing_accuracy`
    measures whether that cell names the right owner, and defining the
    population by it would make the metric read 1.0 by construction and hide the
    double-review bug the ownership table in CLAUDE.md exists to prevent.
    """
    blob = " ".join(
        finding.get(k, "") or ""
        for k in ("domain", "why", "location", "before", "after")
    )
    return bool(CONTRAST_KEYWORDS.search(blob))


OWNER = re.compile(r"design[-_ ]?tokens", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


def score(manifest, findings, coverage_result, arm=None):
    """Compute every metric, with a stated reason wherever one is null."""
    pairs = manifest.get("pairs") or []
    fixture = manifest.get("fixture") or ""
    planted = [p for p in pairs if p.get("planted")]
    disagreeing = [p for p in planted if p.get("disagreement")]

    matched_ids = set()
    ambiguous = 0
    contrast_findings = []
    strategies = {"id": 0, "line": 0, "hex": 0}

    for finding in findings:
        matches, strategy, is_multi = match_finding(finding, pairs, fixture)
        primary = matches[0] if matches else None
        if not is_contrast_finding(finding, primary):
            continue
        contrast_findings.append((finding, primary, matches))
        for pair in matches:
            matched_ids.add(pair["id"])
        if strategy:
            strategies[strategy] += 1
        if is_multi:
            ambiguous += 1

    nulls = {}

    def ratio(numerator, denominator, name, reason):
        if denominator == 0:
            nulls[name] = reason
            return None
        return round(numerator / denominator, 4)

    recall = ratio(
        sum(1 for p in planted if p["id"] in matched_ids),
        len(planted),
        "recall",
        "no planted defects in this manifest — nothing to recall",
    )
    recall_disagreement = ratio(
        sum(1 for p in disagreeing if p["id"] in matched_ids),
        len(disagreeing),
        "recall_disagreement",
        "no planted defect where WCAG and APCA disagree",
    )
    # A consolidated finding is correct if any pair it names is a real defect.
    hits = sum(1 for _, _, ms in contrast_findings if any(m.get("planted") for m in ms))
    precision = ratio(
        hits,
        len(contrast_findings),
        "precision",
        "the report contains no contrast findings — nothing to be precise about",
    )
    routed = sum(1 for f, _, _ms in contrast_findings if OWNER.search(f.get("domain") or ""))
    routing_accuracy = ratio(
        routed,
        len(contrast_findings),
        "routing_accuracy",
        "the report contains no contrast findings — nothing to route",
    )

    padding = sum(
        1
        for _, pair, _ms in contrast_findings
        if pair is None or pair.get("passed") is True
    )

    normalized_result = _norm(coverage_result) if coverage_result is not None else None
    false_clear = bool(planted) and (
        coverage_result is None or normalized_result in {"clear", "clean"}
    )

    return {
        "arm": arm,
        "manifest": {
            "seed": manifest.get("seed"),
            "clean": bool(manifest.get("clean")),
            "fixture": fixture,
            "pairs": len(pairs),
            "planted": len(planted),
            "disagreement": len(disagreeing),
        },
        "report": {
            "findings_total": len(findings),
            "contrast_findings": len(contrast_findings),
            "matched_pairs": sorted(matched_ids),
            "coverage_result": coverage_result,
            "coverage_row_present": coverage_result is not None,
            "matched_by": strategies,
        },
        "metrics": {
            "recall": recall,
            "recall_disagreement": recall_disagreement,
            "precision": precision,
            "false_clear": false_clear,
            "padding": padding,
            "routing_accuracy": routing_accuracy,
            "ambiguous": ambiguous,
        },
        "nulls": nulls,
    }


def format_summary(result):
    """Human-readable rendering. Nulls print as `null` plus their reason."""
    metrics, nulls = result["metrics"], result["nulls"]
    report, mani = result["report"], result["manifest"]

    def show(name):
        value = metrics[name]
        if value is None:
            return f"null  ({nulls.get(name, 'denominator is zero')})"
        return f"{value}"

    lines = [
        f"arm:        {result['arm'] or '(unlabelled)'}",
        f"manifest:   seed={mani['seed']} clean={mani['clean']} "
        f"pairs={mani['pairs']} planted={mani['planted']} "
        f"disagreement={mani['disagreement']}",
        f"report:     {report['findings_total']} finding(s), "
        f"{report['contrast_findings']} about contrast; "
        f"contrast coverage result = "
        f"{report['coverage_result'] if report['coverage_row_present'] else 'ROW ABSENT'}",
        "",
        f"  recall                 {show('recall')}",
        f"  recall_disagreement    {show('recall_disagreement')}   <- headline",
        f"  precision              {show('precision')}",
        f"  routing_accuracy       {show('routing_accuracy')}",
        f"  padding                {metrics['padding']}",
        f"  ambiguous              {metrics['ambiguous']}",
        f"  false_clear            {str(metrics['false_clear']).upper()}",
    ]
    if metrics["false_clear"]:
        lines.append(
            "\n  false_clear is TRUE: the review asserted this domain was clean "
            "(or omitted its row) over a fixture holding real defects."
        )
    matched = report["matched_pairs"]
    lines.append("\n  matched pairs: " + (", ".join(matched) if matched else "none"))
    if metrics["ambiguous"]:
        lines.append(
            f"  {metrics['ambiguous']} finding(s) name more than one pair — every pair "
            "named is credited, per the skill's one-root-cause-one-row rule."
        )
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--report", help="markdown review report (primary path)")
    parser.add_argument("--report-json", dest="report_json",
                        help="structured report, used instead of --report when given")
    parser.add_argument("--arm", choices=["with", "without"])
    parser.add_argument("--json", action="store_true", help="strict JSON output")
    args = parser.parse_args(argv)

    if not args.report and not args.report_json:
        parser.error("one of --report or --report-json is required")

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    findings, coverage = load_report(args.report, args.report_json)
    result = score(manifest, findings, coverage, arm=args.arm)

    print(json.dumps(result, indent=2) if args.json else format_summary(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
