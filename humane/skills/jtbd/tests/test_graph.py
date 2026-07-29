"""Tests for graph.py — bundle discovery, schema shaping, evidence shapes,
tier assignment and language plumbing."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from graph import _list, build, find_bundles, read_quotes, score, shape, tier


class TestScoring(unittest.TestCase):
    def test_matches_odi_score(self):
        # same formula as scripts/odi_score.py — importance plus unmet gap
        self.assertAlmostEqual(score(9.2, 2.4), 16.0, places=6)
        self.assertEqual(score(5, 8), 5)          # satisfied: no gap added

    def test_tiers(self):
        self.assertEqual(tier(16.0), "prioritize")
        self.assertEqual(tier(12), "prioritize")
        self.assertEqual(tier(9), "marginal")
        self.assertEqual(tier(8), "skip")


class TestListCoercion(unittest.TestCase):
    def test_accepts_string_where_list_expected(self):
        self.assertEqual(_list("one"), ["one"])
        self.assertEqual(_list(["a", "b"]), ["a", "b"])
        self.assertEqual(_list(None), [])
        self.assertEqual(_list(""), [])
        self.assertEqual(_list([None, "a"]), ["a"])


class TestEvidenceShapes(unittest.TestCase):
    """Real bundles carry evidence two ways; reading one shape loses the other."""

    def test_flat_quotes(self):
        q = read_quotes({"quotes": ["a said thing"]})
        self.assertEqual(q[0]["text"], "a said thing")
        self.assertIsNone(q[0]["id"])

    def test_ledger_entries(self):
        q = read_quotes({"ledger": [
            {"id": "E1", "quote": "unclear timecode stamps", "who": "Travis G., Capterra"},
        ]})
        self.assertEqual(q[0]["id"], "E1")
        self.assertEqual(q[0]["text"], "unclear timecode stamps")
        self.assertIn("Travis", q[0]["who"])

    def test_both_shapes_combine(self):
        q = read_quotes({"quotes": ["flat"], "ledger": [{"id": "E1", "quote": "ledger"}]})
        self.assertEqual(len(q), 2)

    def test_ledger_entries_without_text_are_dropped(self):
        self.assertEqual(read_quotes({"ledger": [{"id": "E1"}, {}]}), [])


class TestShape(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, slug, payload):
        d = self.root / slug
        d.mkdir(parents=True, exist_ok=True)
        (d / "jtbd.json").write_text(json.dumps(payload), encoding="utf-8")
        return d / "jtbd.json"

    def test_minimal_bundle_survives(self):
        """A core-schema-only file must shape without an odi/extended block."""
        p = self._write("minimal", {
            "name": "minimal",
            "jtbd": {"situation": "when X", "motivation": "I want Y", "outcome": "so Z"},
        })
        out = shape(p)
        self.assertEqual(out["slug"], "minimal")
        self.assertEqual(out["outcomes"], [])
        self.assertEqual(out["needs"]["functional"], [])
        self.assertEqual(out["quotes"], [])

    def test_opportunity_computed_when_absent(self):
        p = self._write("scored", {"name": "scored", "odi": {"outcomes": [
            {"statement": "Minimize the time to X", "importance": 9.2, "satisfaction": 2.4},
        ]}})
        o = shape(p)["outcomes"][0]
        self.assertEqual(o["opp"], 16.0)
        self.assertEqual(o["tier"], "prioritize")

    def test_stored_opportunity_is_respected(self):
        """If the skill already wrote opportunity_score, don't recompute it."""
        p = self._write("stored", {"name": "stored", "odi": {"outcomes": [
            {"statement": "X", "importance": 8.5, "satisfaction": 3.2, "opportunity_score": 13.8},
        ]}})
        self.assertEqual(shape(p)["outcomes"][0]["opp"], 13.8)

    def test_unscored_outcome_is_kept_not_dropped(self):
        p = self._write("partial", {"name": "partial", "odi": {"outcomes": [
            {"statement": "no numbers yet"},
        ]}})
        o = shape(p)["outcomes"][0]
        self.assertIsNone(o["opp"])
        self.assertEqual(o["tier"], "unscored")

    def test_extended_blocks_are_carried(self):
        """before_after / scenarios / target_users / trigger exist in real bundles."""
        p = self._write("ext", {"name": "ext",
                                "target_users": ["editors"],
                                "before_after": {"before": "b", "after": "a"},
                                "scenarios": [{"title": "t", "vignette": "v"}, "not a dict"],
                                "trigger": {"type": "event", "detail": "after each call"}})
        out = shape(p)
        self.assertEqual(out["target_users"], ["editors"])
        self.assertEqual(out["before_after"]["after"], "a")
        self.assertEqual(len(out["scenarios"]), 1)      # the bare string is dropped
        self.assertEqual(out["trigger"]["type"], "event")

    def test_evidence_limitation_and_pages_read(self):
        p = self._write("lim", {"name": "lim", "evidence": {
            "limitation": "small sample", "pages_read": ["p1", "p2"]}})
        out = shape(p)
        self.assertEqual(out["evidence_limitation"], "small sample")
        self.assertEqual(len(out["pages_read"]), 2)

    def test_malformed_json_is_skipped_not_fatal(self):
        d = self.root / "broken"
        d.mkdir()
        (d / "jtbd.json").write_text("{not json", encoding="utf-8")
        self.assertIsNone(shape(d / "jtbd.json"))

    def test_find_bundles_accepts_file_dir_and_root(self):
        f = self._write("a", {"name": "a"})
        self._write("b", {"name": "b"})
        self.assertEqual(find_bundles(f), [f])
        self.assertEqual(find_bundles(f.parent), [f])
        self.assertEqual(len(find_bundles(self.root)), 2)

    def test_build_writes_viewer_and_data(self):
        self._write("a", {"name": "a", "odi": {"outcomes": [
            {"statement": "X", "importance": 9, "satisfaction": 2},
        ]}})
        out = self.root / ".graph"
        data = build(self.root, out)
        self.assertTrue((out / "data.json").is_file())
        self.assertTrue((out / "index.html").is_file())
        self.assertEqual(len(data["projects"]), 1)
        self.assertEqual(data["projects"][0]["outcomes"][0]["tier"], "prioritize")

    def test_lang_is_written_and_validated(self):
        self._write("a", {"name": "a"})
        out = self.root / ".graph"
        self.assertEqual(build(self.root, out, "ru")["lang"], "ru")
        self.assertEqual(build(self.root, out)["lang"], "auto")
        self.assertEqual(build(self.root, out, "klingon")["lang"], "auto")

    def test_build_refuses_empty_root(self):
        with self.assertRaises(SystemExit):
            build(self.root, self.root / ".graph")


if __name__ == "__main__":
    unittest.main()
