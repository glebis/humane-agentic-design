"""The accessibility oracle, and the boundary that keeps it dev-only.

WHY. `evals/` gained Node dependencies for oracle #2. Two things must stay true
and neither is self-enforcing:

  * **Nothing shipped may reach for them.** The plugin's scripts are Python
    stdlib only and install nowhere near a `node_modules`. A stray import under
    `humane/` would turn a dev-only eval dependency into a runtime requirement
    for every user of the plugin, and would be found by them rather than by us.
  * **The rule set is the oracle.** It is an allow-list on purpose. If a rule
    with no owner under CLAUDE.md's table were planted, the harness would be
    testing the method on a domain the method openly disclaims — and
    `routing_accuracy` would punish a review for correctly routing it away.

Run:  python3 -m pytest evals/tests/test_axe_oracle.py -v
"""

import json
import shutil
import subprocess
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
AXE = REPO / "evals" / "axe"
OWNERS = json.loads((AXE / "owners.json").read_text(encoding="utf-8"))

# Owners the mapping may name. Anything else is a typo or a skill that does not
# exist, and would silently make routing_accuracy unsatisfiable.
SKILLS = {p.name for p in (REPO / "humane" / "skills").iterdir() if p.is_dir()}


def node_available():
    return shutil.which("node") is not None and (REPO / "evals" / "node_modules").exists()


class TestOwnerMapping(unittest.TestCase):
    def test_there_are_rules_to_check(self):
        self.assertGreater(len(OWNERS["rules"]), 0, "the allow-list is empty")

    def test_every_rule_names_real_skills_as_accepted_owners(self):
        for rule, spec in OWNERS["rules"].items():
            with self.subTest(rule=rule):
                accepted = spec.get("accepted_owners") or []
                self.assertTrue(accepted, f"{rule}: no accepted_owners")
                for owner in accepted:
                    self.assertIn(
                        owner, SKILLS,
                        f"{rule}: `{owner}` is not a skill in this plugin — "
                        "routing_accuracy could never be satisfied",
                    )

    def test_every_rule_states_why_it_has_that_owner(self):
        for rule, spec in OWNERS["rules"].items():
            with self.subTest(rule=rule):
                self.assertTrue(
                    spec.get("why"),
                    f"{rule}: no `why`. An owner assignment without a reason "
                    "cannot be argued with when it turns out to be wrong.",
                )

    def test_contrast_is_never_delegated_to_axe(self):
        # design-tokens owns all colour measurement. Two oracles on one domain
        # produce contradictory ground truth, and axe's WCAG-only view would
        # pass the WCAG-passes/APCA-fails pairs the fixture plants deliberately.
        self.assertNotIn("color-contrast", OWNERS["rules"])
        self.assertIn("color-contrast", OWNERS["excluded"])

    def test_out_of_scope_rules_are_excluded_with_a_reason(self):
        # CLAUDE.md defers accessibility engineering depth to `interfaces`.
        for rule in ("image-alt", "label", "button-name", "link-name"):
            with self.subTest(rule=rule):
                self.assertNotIn(rule, OWNERS["rules"])
                self.assertTrue(
                    OWNERS["excluded"].get(rule),
                    f"{rule} must be excluded *with a stated reason*",
                )


class TestShippedSkillsStayPython(unittest.TestCase):
    def test_nothing_under_humane_references_the_eval_node_dependencies(self):
        offenders = []
        for path in (REPO / "humane").rglob("*"):
            if not path.is_file() or path.suffix in {".png", ".jpg", ".woff2"}:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            if "axe-core" in text or "node_modules" in text:
                offenders.append(str(path.relative_to(REPO)))
        self.assertEqual(
            offenders, [],
            "shipped skills must not reference the eval harness's Node "
            f"dependencies: {offenders}. evals/ is dev-only; a reference here "
            "makes it a runtime requirement for every plugin user.",
        )


@unittest.skipUnless(node_available(), "node or evals/node_modules unavailable")
class TestRunner(unittest.TestCase):
    def _run(self, html):
        fixture = Path(self.tmp) / "fixture.html"
        fixture.write_text(html, encoding="utf-8")
        out = subprocess.run(
            ["node", str(AXE / "run_axe.js"), str(fixture)],
            capture_output=True, text=True,
        )
        return json.loads(out.stdout)

    def setUp(self):
        import tempfile
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_a_missing_fixture_degrades_rather_than_crashing(self):
        out = subprocess.run(
            ["node", str(AXE / "run_axe.js"), "/nonexistent/fixture.html"],
            capture_output=True, text=True,
        )
        self.assertEqual(out.returncode, 0, "a missing pathway is not a crash")
        payload = json.loads(out.stdout)
        self.assertFalse(payload["available"])
        self.assertTrue(payload.get("reason"), "unavailability must say why")

    def test_it_finds_a_planted_heading_order_break(self):
        out = self._run(
            '<!doctype html><html lang="en"><head><title>t</title></head>'
            '<body><main><h1 id="ax-01">A</h1><h4 id="ax-02">B</h4></main></body></html>'
        )
        self.assertTrue(out["available"])
        rules = {v["rule"] for v in out["violations"]}
        self.assertIn("heading-order", rules)

    def test_it_runs_only_the_allow_listed_rules(self):
        out = self._run(
            '<!doctype html><html lang="en"><head><title>t</title></head>'
            '<body><main><img id="ax-01" src="a.png"><h1>A</h1></main></body></html>'
        )
        self.assertEqual(set(out["rules_run"]), set(OWNERS["rules"]))
        self.assertNotIn(
            "image-alt", {v["rule"] for v in out["violations"]},
            "an excluded, out-of-scope rule must not reach the manifest even "
            "when the page would violate it",
        )

    def test_violations_carry_a_selector_and_accepted_owners(self):
        out = self._run(
            '<!doctype html><html lang="en"><head><title>t</title></head>'
            '<body><main><h1 id="ax-01">A</h1><h4 id="ax-02">B</h4></main></body></html>'
        )
        for violation in out["violations"]:
            with self.subTest(rule=violation["rule"]):
                self.assertTrue(violation["selector"], "no locator to match on")
                self.assertTrue(violation["accepted_owners"])


if __name__ == "__main__":
    unittest.main()
