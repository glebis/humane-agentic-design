"""The fixture generator's manifest is the eval's ground truth, so it is the one
thing in the harness that cannot be wrong.

Every number the eval reports — did the reviewer find the defect, did it invent
one that is not there — is a comparison against `manifest.json`. A manifest that
disagrees with the page it describes does not produce a noisy result; it
produces a confident wrong one. These tests hold the three properties that
guarantee it cannot:

1. **Determinism.** A seed reproduces the fixture byte for byte, and different
   seeds actually differ (otherwise the seed is decoration and every run of the
   eval is the same run).
2. **Derivation.** `planted` is `not passed`, computed by the oracle, for every
   pair. Never the generator's intent.
3. **Correspondence.** The set of ids in the HTML equals the set in the
   manifest, and each recorded line really holds its element. A locator that
   drifts turns a found defect into a missed one at scoring time.

Plus the two traps from the oracle: the signed-APCA regression (a light-on-dark
pair with negative Lc that clears the bar must not be marked planted), and the
disagreement quota that makes the fixture worth running at all.

Run:  python3 -m pytest evals/tests/ -v
"""

import json
import math
import re
import subprocess
import sys
import unittest
from pathlib import Path

import generate
import oracle

CONTRAST = Path(__file__).resolve().parents[1] / "contrast"

SEED, PAIRS, DEFECTS = 1337, 14, 6


class Fixture:
    """One generated fixture, held as text so tests can assert on the bytes."""

    def __init__(self, seed=SEED, pairs=PAIRS, defects=DEFECTS, clean=False):
        self.html, self.manifest = generate.generate(
            seed, pairs, defects=defects, clean=clean)
        self.lines = self.html.split("\n")


class TestDeterminism(unittest.TestCase):
    def test_same_seed_is_byte_identical(self):
        a, b = Fixture(), Fixture()
        self.assertEqual(a.html, b.html, "same seed produced different HTML")
        self.assertEqual(
            json.dumps(a.manifest, sort_keys=True),
            json.dumps(b.manifest, sort_keys=True),
            "same seed produced a different manifest — something in generate.py "
            "reads global random, the clock, or uuid",
        )

    def test_different_seeds_differ(self):
        # Guards the test above from passing vacuously: if the generator ignored
        # the seed entirely, "same seed is identical" would still be green.
        a = Fixture(seed=1)
        b = Fixture(seed=2)
        self.assertNotEqual(a.html, b.html,
                            "two seeds produced the same page — is --seed wired "
                            "through to random.Random?")

    def test_cli_writes_both_files_and_reproduces(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            one, two = Path(tmp) / "a", Path(tmp) / "b"
            for out in (one, two):
                proc = subprocess.run(
                    [sys.executable, "generate.py", "--seed", str(SEED),
                     "--pairs", str(PAIRS), "--defects", str(DEFECTS),
                     "--out", str(out)],
                    cwd=CONTRAST, capture_output=True, text=True)
                self.assertEqual(proc.returncode, 0, proc.stderr)
            for name in ("fixture.html", "manifest.json"):
                self.assertEqual((one / name).read_bytes(), (two / name).read_bytes(),
                                 f"{name} differs between two identical CLI runs")

    def test_clean_rejects_defects(self):
        proc = subprocess.run(
            [sys.executable, "generate.py", "--seed", "1", "--pairs", "6",
             "--clean", "--defects", "2", "--out", "/dev/null"],
            cwd=CONTRAST, capture_output=True, text=True)
        self.assertNotEqual(proc.returncode, 0,
                            "--clean --defects was accepted; a clean fixture has "
                            "zero defects by definition")


class TestGroundTruth(unittest.TestCase):
    def setUp(self):
        self.fx = Fixture()

    def test_there_are_pairs_to_check(self):
        self.assertEqual(len(self.fx.manifest["pairs"]), PAIRS)
        self.assertGreater(self.fx.manifest["counts"]["planted"], 0,
                           "no defects planted — every test below is vacuous")

    def test_planted_is_derived_from_the_oracle(self):
        for p in self.fx.manifest["pairs"]:
            with self.subTest(pair=p["id"]):
                got = oracle.measure(p["fg"], p["bg"], p["level"])
                self.assertEqual(
                    got["passed"], p["passed"],
                    f"{p['id']}: manifest says passed={p['passed']}, the oracle "
                    f"says {got['passed']} for {p['fg']} on {p['bg']}")
                self.assertEqual(
                    p["planted"], not p["passed"],
                    f"{p['id']}: `planted` must be derived as `not passed`, never "
                    "hand-asserted by whichever branch chose the colour")
                for key in ("apca", "wcag", "apca_pass", "wcag_pass"):
                    self.assertEqual(got[key], p[key],
                                     f"{p['id']}: manifest {key} disagrees with the oracle")

    def test_disagreement_flag_matches_its_definition(self):
        for p in self.fx.manifest["pairs"]:
            with self.subTest(pair=p["id"]):
                self.assertEqual(p["disagreement"], p["apca_pass"] != p["wcag_pass"],
                                 f"{p['id']}: `disagreement` must be apca_pass != wcag_pass")

    def test_disagreement_quota_holds(self):
        planted = [p for p in self.fx.manifest["pairs"] if p["planted"]]
        disagreeing = [p for p in planted if p["disagreement"]]
        quota = math.ceil(len(planted) / 3)
        self.assertGreaterEqual(
            len(disagreeing), quota,
            f"{len(disagreeing)} of {len(planted)} planted defects disagree between "
            f"APCA and WCAG, quota is {quota}. Those are the cases a reviewer "
            "working from the 4.5:1 number misses; without them the fixture "
            "measures almost nothing.")
        self.assertEqual(self.fx.manifest["counts"]["disagreement"], len(disagreeing))
        self.assertEqual(self.fx.manifest["counts"]["planted"], len(planted))

    def test_levels_are_declared_and_mixed(self):
        levels = {p["level"] for p in self.fx.manifest["pairs"]}
        for level in levels:
            self.assertIn(level, oracle.THRESHOLDS, f"unknown level {level!r}")
        self.assertEqual(levels, set(oracle.LEVELS),
                         "the fixture must exercise all three levels — `graphic` "
                         "in particular, since contrast.py never infers it")

    def test_no_pair_is_repeated(self):
        seen = [(p["fg"], p["bg"]) for p in self.fx.manifest["pairs"]]
        self.assertEqual(len(seen), len(set(seen)),
                         "a colour pair appears twice; a reviewer would score one "
                         "finding as two")

    def test_signed_apca_light_on_dark_is_not_a_defect(self):
        # The regression the oracle facts warn about: light text on a dark ground
        # has a NEGATIVE Lc. A generator comparing the raw signed value against
        # the threshold marks every such pair as failing and plants defects that
        # are not on the page.
        m = oracle.measure("#dafdff", "#08080a", "body")
        self.assertLess(m["apca"], 0, "expected a negative Lc for light on dark")
        self.assertTrue(m["passed"],
                        "light-on-dark pair with |Lc| well over the bar was judged "
                        "failing — measure() is comparing the signed value")

        found = [p for p in self.fx.manifest["pairs"] if p["apca"] < 0 and p["passed"]]
        self.assertTrue(found,
                        "no passing light-on-dark pair in the fixture; the signed-APCA "
                        "case is unexercised — check that dark backgrounds are still "
                        "in _BACKGROUNDS")
        for p in found:
            self.assertFalse(p["planted"],
                             f"{p['id']}: passing negative-Lc pair marked as planted")


class TestClean(unittest.TestCase):
    def test_clean_has_no_failing_pair(self):
        fx = Fixture(defects=0, clean=True)
        self.assertTrue(fx.manifest["clean"])
        self.assertEqual(fx.manifest["counts"]["planted"], 0)
        self.assertEqual(fx.manifest["counts"]["disagreement"], 0)
        for p in fx.manifest["pairs"]:
            with self.subTest(pair=p["id"]):
                self.assertTrue(p["passed"], f"{p['id']} fails the oracle in a clean fixture")
                self.assertFalse(p["planted"])
        # Same guard as above: a clean fixture with no pairs would pass trivially.
        self.assertEqual(len(fx.manifest["pairs"]), PAIRS)


class TestPageMatchesManifest(unittest.TestCase):
    def setUp(self):
        self.fx = Fixture()

    def test_ids_correspond_in_both_directions(self):
        in_html = set(re.findall(r'id="(pair-\d+)"', self.fx.html))
        in_manifest = {p["id"] for p in self.fx.manifest["pairs"]}
        self.assertEqual(
            in_html, in_manifest,
            "the page and the manifest describe different sets of pairs. "
            f"only in HTML: {sorted(in_html - in_manifest)}; "
            f"only in manifest: {sorted(in_manifest - in_html)}")

    def test_recorded_line_holds_the_element_and_its_colours(self):
        for p in self.fx.manifest["pairs"]:
            with self.subTest(pair=p["id"]):
                self.assertTrue(1 <= p["line"] <= len(self.fx.lines),
                                f"{p['id']}: line {p['line']} is outside the file")
                line = self.fx.lines[p["line"] - 1]
                self.assertIn(f'id="{p["id"]}"', line,
                              f"{p['id']}: line {p['line']} does not hold that element")
                self.assertIn(f"color:{p['fg']}", line,
                              f"{p['id']}: line {p['line']} does not set fg {p['fg']}")
                self.assertIn(f"background-color:{p['bg']}", line,
                              f"{p['id']}: line {p['line']} does not set bg {p['bg']}")

    def test_every_colour_on_the_page_is_in_the_manifest(self):
        # The whole eval rests on this: a colour the manifest does not know about
        # is a defect nobody can be scored on, or a false positive nobody can
        # adjudicate.
        known = set()
        for p in self.fx.manifest["pairs"]:
            known.update((p["fg"].lower(), p["bg"].lower()))
        on_page = {c.lower() for c in re.findall(r"#[0-9a-fA-F]{3,8}", self.fx.html)}
        self.assertEqual(on_page - known, set(),
                         "the page paints colours the manifest does not record")

    def test_each_pair_occupies_exactly_one_line(self):
        for p in self.fx.manifest["pairs"]:
            hits = [i for i, line in enumerate(self.fx.lines, 1)
                    if f'id="{p["id"]}"' in line]
            self.assertEqual(hits, [p["line"]],
                             f"{p['id']}: expected exactly one line, found {hits}")


class TestOracle(unittest.TestCase):
    def test_rejects_an_unknown_level(self):
        with self.assertRaises(ValueError):
            oracle.measure("#000000", "#ffffff", "large-text")

    def test_unparseable_colour_raises_rather_than_skipping(self):
        with self.assertRaises(oracle.Unparseable):
            oracle.measure("var(--ink)", "#ffffff", "body")

    def test_the_documented_disagreement_case(self):
        # From oracle-facts.md §2 — the anchor the whole disagreement class rests
        # on. If contrast.py's thresholds move, this is where it surfaces.
        m = oracle.measure("#767676", "#ffffff", "body")
        self.assertTrue(m["wcag_pass"])
        self.assertFalse(m["apca_pass"])
        self.assertFalse(m["passed"], 'standard="both" must fail a pair that '
                                      "clears only one scale")


if __name__ == "__main__":
    unittest.main()
