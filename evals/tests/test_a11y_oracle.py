"""Oracle #2 end to end: planting, confirming, collapsing, and scoring.

WHY. Until this pathway existed every planted defect had exactly one possible
owner, so `routing_accuracy` was close to given. Two oracles over two domains is
what makes routing a real measurement — and what makes the one-root-cause rule
load-bearing, because `region` fires once per element outside a landmark and
would otherwise turn one missing `<main>` into a dozen defects a reviewer is
scored against individually.

Run:  python3 -m pytest evals/tests/test_a11y_oracle.py -v
"""

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

EVALS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EVALS / "contrast"))
sys.path.insert(0, str(EVALS / "axe"))

import generate  # noqa: E402
import score_a11y  # noqa: E402

NODE = shutil.which("node") and (EVALS / "node_modules").exists()


class TestPlanting(unittest.TestCase):
    def test_the_catalogue_is_inside_the_allow_list(self):
        owners = json.loads((EVALS / "axe" / "owners.json").read_text(encoding="utf-8"))
        allowed = set(owners["rules"])
        # `no-main` plants the condition that fires region/landmark-one-main.
        for defect in generate.A11Y_DEFECTS:
            if defect == "no-main":
                continue
            with self.subTest(defect=defect):
                self.assertIn(defect, allowed,
                              f"{defect} is planted but not in the vetted allow-list")

    def test_default_fixture_plants_no_accessibility_defect(self):
        html, _ = generate.generate(1, 6, defects=2)
        self.assertIn("<main>", html,
                      "without a landmark axe reports `region` once per element — "
                      "a fixture must not carry an unplanted accessibility defect")
        self.assertIn('<html lang="en">', html)

    def test_each_planted_defect_changes_the_markup(self):
        base, _ = generate.generate(1, 6, defects=2)
        for defect in generate.A11Y_DEFECTS:
            with self.subTest(defect=defect):
                html, _ = generate.generate(1, 6, defects=2, a11y=[defect])
                self.assertNotEqual(html, base, f"{defect} planted nothing")


class TestCollapse(unittest.TestCase):
    OWNERS = {"rules": {"region": {"one_root_cause": True},
                        "heading-order": {}}}

    def test_one_root_cause_becomes_one_defect(self):
        raw = [{"rule": "region", "selector": f"#pair-{i:02d}"} for i in range(1, 13)]
        out = generate.collapse(raw, self.OWNERS)
        self.assertEqual(len(out), 1, "twelve nodes, one missing <main>, one defect")
        self.assertEqual(len(out[0]["selectors"]), 12,
                         "every affected node is still listed")

    def test_ordinary_rules_stay_separate(self):
        raw = [{"rule": "heading-order", "selector": "#a"},
               {"rule": "heading-order", "selector": "#b"}]
        self.assertEqual(len(generate.collapse(raw, self.OWNERS)), 2)


class TestScoring(unittest.TestCase):
    MANIFEST = {
        "seed": 1, "axe": {"available": True},
        "violations": [
            {"rule": "heading-order", "selectors": ["#ax-heading-order"],
             "accepted_owners": ["layout-rules"]},
            {"rule": "empty-heading", "selectors": ["#ax-empty-heading"],
             "accepted_owners": ["ux-writing", "layout-rules"]},
        ],
    }

    def test_a_report_naming_both_scores_full_recall(self):
        findings = [{"domain": "layout-rules", "location": "#ax-heading-order",
                     "why": "heading level skips"},
                    {"domain": "ux-writing", "location": "#ax-empty-heading",
                     "why": "this heading is empty"}]
        out = score_a11y.score(self.MANIFEST, findings)
        self.assertEqual(out["recall"], 1.0)
        self.assertEqual(out["routing"], 1.0)

    def test_either_accepted_owner_counts(self):
        # An empty heading is defensibly ux-writing OR layout-rules. Marking a
        # defensible choice wrong would measure the mapping, not the review.
        for owner in ("ux-writing", "layout-rules"):
            with self.subTest(owner=owner):
                out = score_a11y.score(self.MANIFEST, [
                    {"domain": owner, "location": "#ax-empty-heading",
                     "why": "empty heading"}])
                self.assertEqual(out["routing"], 1.0)

    def test_ordinary_words_count_not_just_rule_ids(self):
        out = score_a11y.score(self.MANIFEST, [
            {"domain": "layout-rules", "location": "line 14",
             "why": "the heading hierarchy jumps from h1 straight to h4"}])
        self.assertEqual(out["found"], ["heading-order"],
                         "a reviewer is not obliged to speak axe's rule ids")

    def test_wrong_owner_keeps_recall_and_loses_routing(self):
        out = score_a11y.score(self.MANIFEST, [
            {"domain": "design-tokens", "location": "#ax-heading-order",
             "why": "heading level skips"}])
        self.assertEqual(out["recall"], 0.5)
        self.assertEqual(out["routing"], 0.0)

    def test_empty_report_gives_null_routing_not_one(self):
        out = score_a11y.score(self.MANIFEST, [])
        self.assertEqual(out["recall"], 0.0)
        self.assertIsNone(out["routing"],
                          "nothing was found, so routing is undefined, not perfect")

    def test_absent_oracle_is_not_reviewed_with_every_metric_null(self):
        manifest = dict(self.MANIFEST, axe={"available": False, "reason": "no node"})
        out = score_a11y.score(manifest, [])
        self.assertEqual(out["result"], "Not reviewed")
        for key in ("recall", "routing", "violations"):
            self.assertIsNone(out[key], f"{key} must be null when the oracle did not run")


@unittest.skipUnless(NODE, "node or evals/node_modules unavailable")
class TestEndToEnd(unittest.TestCase):
    def test_planted_defects_are_confirmed_by_the_oracle(self):
        tmp = tempfile.mkdtemp()
        try:
            generate.main(["--seed", "5", "--pairs", "8", "--defects", "3",
                           "--a11y", "--out", tmp])
            manifest = json.loads((Path(tmp) / "manifest.json").read_text(encoding="utf-8"))
            self.assertTrue(manifest["axe"]["available"])
            rules = {v["rule"] for v in manifest["violations"]}
            for expected in ("heading-order", "empty-heading", "html-has-lang"):
                self.assertIn(expected, rules,
                              f"{expected} was planted but axe did not confirm it")
            region = [v for v in manifest["violations"] if v["rule"] == "region"]
            if region:
                self.assertEqual(len(region), 1, "region must collapse to one defect")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_a_default_fixture_has_no_violations(self):
        tmp = tempfile.mkdtemp()
        try:
            generate.main(["--seed", "5", "--pairs", "8", "--defects", "3", "--out", tmp])
            manifest = json.loads((Path(tmp) / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["counts"]["violations"], 0,
                             "a fixture must not carry accessibility defects nobody planted")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
