"""Tests for the contrast eval scorer.

WHY. This scorer is the instrument, and an instrument that flatters is worse
than no instrument. The tests below are weighted towards the ways a scorer
silently lies rather than the ways it crashes:

  * a metric reading 1.0 because its denominator was zero (precision on an empty
    report, recall on an empty manifest) — the exact dishonesty the harness
    exists to catch, committed by the harness;
  * `false_clear` failing to fire, which would let a review assert a clean
    contrast domain over a fixture full of planted defects and score well;
  * `Not reviewed` being punished as if it were a lie, when the skill defines it
    as the honest admission;
  * `routing_accuracy` reading 1.0 by construction, which it would if the set of
    contrast findings were defined by the same Domain cell the metric grades.

Report fixtures are written inline, deliberately ragged — missing outer pipes,
stray prose, unaligned columns — because that is how models actually emit these
tables and none of it is a defect worth scoring.

Run:  python3 -m pytest evals/tests/test_score.py -v
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "contrast"))

import score as scorer  # noqa: E402


MANIFEST = {
    "seed": 1337,
    "clean": False,
    "fixture": "fixture.html",
    "counts": {"pairs": 4, "planted": 3, "disagreement": 2},
    "pairs": [
        {"id": "pair-01", "line": 12, "fg": "#767676", "bg": "#ffffff",
         "level": "body", "apca": 71.6, "wcag": 4.54, "apca_pass": False,
         "wcag_pass": True, "passed": False, "planted": True, "disagreement": True},
        {"id": "pair-02", "line": 27, "fg": "#8a8a8a", "bg": "#f0f0f0",
         "level": "body", "apca": 55.0, "wcag": 3.10, "apca_pass": False,
         "wcag_pass": False, "passed": False, "planted": True, "disagreement": False},
        {"id": "pair-03", "line": 42, "fg": "#595959", "bg": "#eeeeee",
         "level": "large", "apca": 68.0, "wcag": 6.20, "apca_pass": False,
         "wcag_pass": True, "passed": False, "planted": True, "disagreement": True},
        {"id": "pair-04", "line": 55, "fg": "#000000", "bg": "#ffffff",
         "level": "body", "apca": 106.0, "wcag": 21.0, "apca_pass": True,
         "wcag_pass": True, "passed": True, "planted": False, "disagreement": False},
    ],
}

CLEAN_MANIFEST = {
    "seed": 99, "clean": True, "fixture": "fixture.html",
    "counts": {"pairs": 1, "planted": 0, "disagreement": 0},
    "pairs": [dict(MANIFEST["pairs"][3])],
}


def coverage_table(result):
    """A Scope-and-coverage table whose contrast row carries `result`."""
    return (
        "### Scope and coverage\n\n"
        "Mode: full. Scope: fixture.html. Domains ran inline.\n\n"
        "| Domain | Evidence inspected | Result |\n"
        "| --- | --- | --- |\n"
        "| Task completion | Nothing operable | `N/A` |\n"
        f"| Colour and contrast | fixture.html, all pairs | {result} |\n"
        "| Interface copy | Body strings | `Clear` |\n\n"
    )


def findings_table(rows):
    """A Findings table in the skill's seven-column shape."""
    head = (
        "### Findings\n\n"
        "| # | Severity | Domain | Location | Before | After | Why |\n"
        "| --- | --- | --- | --- | --- | --- | --- |\n"
    )
    return head + "".join("| " + " | ".join(r) + " |\n" for r in rows) + "\n"


def run(manifest, markdown):
    return scorer.score(manifest, *scorer.load_report_text(markdown))


class TestPerfectReport(unittest.TestCase):
    """A report that names every planted defect, routed to its owner."""

    def setUp(self):
        report = coverage_table("3 findings") + findings_table([
            ["1", "HIGH", "`design-tokens`", "fixture.html:12 (`pair-01`)",
             "#767676 on #ffffff", "#595959 on #ffffff", "APCA 71.6 fails body text"],
            ["2", "HIGH", "`design-tokens`", "`pair-02`",
             "#8a8a8a on #f0f0f0", "#4a4a4a on #f0f0f0", "WCAG 3.10 below 4.5:1"],
            ["3", "MEDIUM", "`design-tokens`", "`pair-03`",
             "#595959 on #eeeeee", "#3a3a3a on #eeeeee", "APCA 68 fails large text"],
        ])
        self.result = run(MANIFEST, report)

    def test_finds_every_planted_defect(self):
        self.assertEqual(self.result["metrics"]["recall"], 1.0,
                         "three planted pairs were each cited; recall must be 1.0")

    def test_headline_disagreement_recall_is_one(self):
        self.assertEqual(self.result["metrics"]["recall_disagreement"], 1.0,
                         "both WCAG/APCA-disagreeing pairs were cited")

    def test_no_padding_and_perfect_precision(self):
        self.assertEqual(self.result["metrics"]["precision"], 1.0)
        self.assertEqual(self.result["metrics"]["padding"], 0,
                         "every finding matched a failing pair; nothing was invented")

    def test_routing_is_correct(self):
        self.assertEqual(self.result["metrics"]["routing_accuracy"], 1.0,
                         "all three name `design-tokens`, the owner per CLAUDE.md")

    def test_not_a_false_clear(self):
        self.assertFalse(self.result["metrics"]["false_clear"])

    def test_the_fixture_actually_exercised_the_parser(self):
        # Guards against the whole class passing because nothing parsed and
        # every metric came back null.
        self.assertEqual(self.result["report"]["findings_total"], 3,
                         "the findings table did not parse — the assertions above are vacuous")


class TestFalseClear(unittest.TestCase):
    """The honesty metric: asserting cleanliness over real defects."""

    def test_clear_over_planted_defects_is_a_false_clear(self):
        result = run(MANIFEST, coverage_table("`Clear`") + "No actionable findings.\n")
        self.assertTrue(result["metrics"]["false_clear"],
                        "`Clear` over 3 planted defects must set false_clear TRUE")
        self.assertEqual(result["metrics"]["recall"], 0.0)

    def test_not_reviewed_is_an_honest_admission_not_a_false_clear(self):
        result = run(
            MANIFEST,
            coverage_table("`Not reviewed` — no token set in the project")
            + "No actionable findings.\n",
        )
        self.assertFalse(result["metrics"]["false_clear"],
                         "`Not reviewed` names the gap; it must not be scored as a lie")

    def test_an_absent_contrast_row_is_a_false_clear(self):
        report = (
            "### Scope and coverage\n\n"
            "| Domain | Evidence inspected | Result |\n"
            "| --- | --- | --- |\n"
            "| Interface copy | Body strings | `Clear` |\n\n"
            "No actionable findings.\n"
        )
        result = run(MANIFEST, report)
        self.assertIsNone(result["report"]["coverage_result"])
        self.assertTrue(result["metrics"]["false_clear"],
                        "omitting the row tells the reader nothing at all — worse "
                        "than `Not reviewed`, so it must score as a false clear")

    def test_clean_manifest_can_never_be_a_false_clear(self):
        result = run(CLEAN_MANIFEST, coverage_table("`Clear`") + "No actionable findings.\n")
        self.assertFalse(result["metrics"]["false_clear"],
                         "with nothing planted, `Clear` is simply true")


class TestZeroDenominators(unittest.TestCase):
    """Every metric that can divide by zero must emit null, never 1.0."""

    def test_precision_on_an_empty_report_is_null(self):
        result = run(MANIFEST, coverage_table("`Clear`") + "No actionable findings.\n")
        self.assertIsNone(result["metrics"]["precision"],
                          "a review that reported nothing is not perfectly precise")
        self.assertIn("precision", result["nulls"],
                      "a null metric must carry a stated reason")

    def test_routing_accuracy_on_an_empty_report_is_null(self):
        result = run(MANIFEST, coverage_table("`Clear`") + "No actionable findings.\n")
        self.assertIsNone(result["metrics"]["routing_accuracy"])
        self.assertIn("routing_accuracy", result["nulls"])

    def test_recall_on_a_clean_manifest_is_null(self):
        result = run(CLEAN_MANIFEST, coverage_table("`Clear`") + "No actionable findings.\n")
        self.assertIsNone(result["metrics"]["recall"],
                          "nothing was planted, so nothing was recalled — not 1.0")
        self.assertIsNone(result["metrics"]["recall_disagreement"])
        self.assertIn("recall", result["nulls"])

    def test_summary_prints_null_with_its_reason(self):
        result = run(CLEAN_MANIFEST, coverage_table("`Clear`") + "No actionable findings.\n")
        text = scorer.format_summary(result)
        self.assertIn("null", text)
        self.assertIn("nothing to recall", text,
                      "the human-readable output must say why a metric is null")


class TestLocatorStrategies(unittest.TestCase):
    """Each of the three ways a finding may point at a pair."""

    def _one(self, location, why="contrast too low"):
        report = coverage_table("1 finding") + findings_table([
            ["1", "HIGH", "`design-tokens`", location, "x", "y", why],
        ])
        return run(MANIFEST, report)

    def test_matches_by_element_id(self):
        result = self._one("the byline in `pair-02`")
        self.assertEqual(result["report"]["matched_pairs"], ["pair-02"])
        self.assertEqual(result["report"]["matched_by"]["id"], 1)

    def test_matches_by_file_and_line(self):
        result = self._one("fixture.html:27")
        self.assertEqual(result["report"]["matched_pairs"], ["pair-02"])
        self.assertEqual(result["report"]["matched_by"]["line"], 1)

    def test_matches_by_both_hex_colours(self):
        result = self._one("the muted caption", why="#8a8a8a on #f0f0f0 is 3.10:1")
        self.assertEqual(result["report"]["matched_pairs"], ["pair-02"])
        self.assertEqual(result["report"]["matched_by"]["hex"], 1)

    def test_one_hex_alone_does_not_match(self):
        # Half a pair is not evidence the reviewer found that pair.
        result = self._one("somewhere", why="#8a8a8a looks light")
        self.assertEqual(result["report"]["matched_pairs"], [])
        self.assertEqual(result["metrics"]["padding"], 1)

    def test_id_beats_line_when_they_disagree(self):
        result = self._one("fixture.html:27 — `pair-03`")
        self.assertEqual(result["report"]["matched_pairs"], ["pair-03"],
                         "element id outranks the line number by locator priority")
        self.assertEqual(result["metrics"]["ambiguous"], 0,
                         "cross-tier priority resolves cleanly; nothing is ambiguous")


class TestAmbiguity(unittest.TestCase):
    def test_a_consolidated_finding_gets_credit_for_every_pair_it_names(self):
        # `humane:review` §8 requires one root cause to be one row listing every
        # confirmed location. Crediting only the "best" match scored a review
        # that obeyed that rule as though it had missed the defects it listed —
        # on the first real comparison it turned 6-of-6 into 0.33 and inverted
        # the result against an arm that had found 4 of 6.
        report = coverage_table("1 finding") + findings_table([
            ["1", "HIGH", "`design-tokens`", "`pair-01` and `pair-03`",
             "x", "y", "both are too light"],
        ])
        result = run(MANIFEST, report)
        self.assertEqual(result["report"]["matched_pairs"], ["pair-01", "pair-03"],
                         "every pair the finding locates must be credited")
        self.assertEqual(result["metrics"]["ambiguous"], 1,
                         "the multi-pair count is still surfaced to the reader")
        self.assertIn("ambiguous", scorer.format_summary(result),
                      "the count must reach the reader of the summary")


class TestPaddingAndRouting(unittest.TestCase):
    def test_invented_findings_count_as_padding(self):
        report = coverage_table("2 findings") + findings_table([
            ["1", "HIGH", "`design-tokens`", "`pair-01`", "x", "y", "APCA fails"],
            ["2", "MEDIUM", "`design-tokens`", "the footer", "x", "y",
             "the contrast here feels weak"],
        ])
        result = run(MANIFEST, report)
        self.assertEqual(result["metrics"]["padding"], 1)
        self.assertEqual(result["metrics"]["precision"], 0.5)

    def test_a_finding_against_a_passing_pair_is_padding(self):
        report = coverage_table("1 finding") + findings_table([
            ["1", "LOW", "`design-tokens`", "`pair-04`", "x", "y", "contrast"],
        ])
        result = run(MANIFEST, report)
        self.assertEqual(result["metrics"]["padding"], 1,
                         "pair-04 passes; reporting it is an invented defect")
        self.assertEqual(result["metrics"]["precision"], 0.0)

    def test_wrong_owner_lowers_routing_accuracy(self):
        report = coverage_table("2 findings") + findings_table([
            ["1", "HIGH", "`design-tokens`", "`pair-01`", "x", "y", "APCA fails"],
            ["2", "HIGH", "`layout-rules`", "`pair-02`", "x", "y",
             "text contrast below the bar"],
        ])
        result = run(MANIFEST, report)
        self.assertEqual(result["metrics"]["routing_accuracy"], 0.5,
                         "contrast is owned by `design-tokens`; routing it to "
                         "`layout-rules` is the double-review bug")
        self.assertAlmostEqual(result["metrics"]["recall"], 2 / 3, places=3,
                               msg="a misrouted finding still found the defect")

    def test_routing_accuracy_is_not_one_by_construction(self):
        # If the contrast population were defined by the Domain cell, this
        # report would score 1.0 and the metric would be meaningless.
        report = coverage_table("1 finding") + findings_table([
            ["1", "HIGH", "`layout-rules`", "`pair-01`", "x", "y", "too light"],
        ])
        result = run(MANIFEST, report)
        self.assertEqual(result["report"]["contrast_findings"], 1)
        self.assertEqual(result["metrics"]["routing_accuracy"], 0.0)


class TestTolerantIngestion(unittest.TestCase):
    def test_ragged_tables_still_parse(self):
        report = (
            "Some preamble prose about the review.\n\n"
            "Domain | Evidence inspected | Result\n"
            ":--- | :---: | ---:\n"
            "Colour/contrast | all pairs | 1 finding\n\n"
            "More prose.\n\n"
            "#|Severity|Domain|Location|Before|After|Why\n"
            "---|---|---|---|---|---|---\n"
            "1|HIGH|design-tokens|pair-01|a|b|apca fails\n"
        )
        result = run(MANIFEST, report)
        self.assertEqual(result["report"]["findings_total"], 1,
                         "a table without outer pipes is still a table")
        self.assertEqual(result["report"]["coverage_result"], "1 finding")

    def test_a_report_with_no_tables_at_all_does_not_crash(self):
        result = run(MANIFEST, "I looked at the page. It seemed fine to me.\n")
        self.assertEqual(result["report"]["findings_total"], 0)
        self.assertIsNone(result["report"]["coverage_result"])
        self.assertTrue(result["metrics"]["false_clear"],
                        "no coverage row at all over planted defects is a false clear")

    def test_a_findings_table_missing_columns_still_parses(self):
        report = (
            coverage_table("1 finding")
            + "| Severity | Location | Why |\n| --- | --- | --- |\n"
            + "| HIGH | `pair-01` | APCA 71.6 fails body text |\n"
        )
        result = run(MANIFEST, report)
        self.assertEqual(result["report"]["findings_total"], 1)
        self.assertEqual(result["report"]["matched_pairs"], ["pair-01"])
        self.assertEqual(result["metrics"]["routing_accuracy"], 0.0,
                         "no Domain cell means no owner was named")

    def test_empty_rows_are_not_counted_as_findings(self):
        report = coverage_table("1 finding") + findings_table([
            ["1", "HIGH", "`design-tokens`", "`pair-01`", "x", "y", "apca fails"],
            ["", "", "", "", "", "", ""],
        ])
        self.assertEqual(run(MANIFEST, report)["report"]["findings_total"], 1)


class TestStructuredReport(unittest.TestCase):
    def test_json_report_scores_the_same_as_its_markdown_twin(self):
        structured = {
            "coverage": {"colour and contrast": "1 finding"},
            "findings": [
                {"severity": "HIGH", "domain": "design-tokens",
                 "location": "pair-01", "why": "APCA 71.6 fails body text"},
            ],
        }
        findings, coverage = scorer.load_report_data(structured)
        result = scorer.score(MANIFEST, findings, coverage)
        self.assertEqual(result["report"]["matched_pairs"], ["pair-01"])
        self.assertFalse(result["metrics"]["false_clear"])


class TestCLI(unittest.TestCase):
    def test_end_to_end_json_output(self):
        import json
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / "manifest.json").write_text(json.dumps(MANIFEST), encoding="utf-8")
            (tmp / "report.md").write_text(
                coverage_table("1 finding") + findings_table([
                    ["1", "HIGH", "`design-tokens`", "`pair-01`", "x", "y", "apca fails"],
                ]),
                encoding="utf-8",
            )
            from contextlib import redirect_stdout
            import io

            buffer = io.StringIO()
            with redirect_stdout(buffer):
                code = scorer.main([
                    "--manifest", str(tmp / "manifest.json"),
                    "--report", str(tmp / "report.md"),
                    "--arm", "with", "--json",
                ])
            self.assertEqual(code, 0)
            payload = json.loads(buffer.getvalue())
            self.assertEqual(payload["arm"], "with")
            self.assertEqual(payload["metrics"]["recall"], round(1 / 3, 4))


if __name__ == "__main__":
    unittest.main()
