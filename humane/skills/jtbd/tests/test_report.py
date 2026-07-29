"""Tests for report.py — executive summary generation (single + corpus)."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import report  # noqa: E402


RICH = {
    "name": "widget-flow",
    "hook": "Cuts approval prep from an hour to ten minutes.",
    "jtbd": {
        "situation": "When a producer collects edits scattered across email [E1]...",
        "motivation": "I want every comment in one place tied to a timecode",
        "outcome": "So I stop transcribing notes by hand [E1, E2]. Target not measured — unknown.",
    },
    "switch_forces": {
        "push": "Chaos of edits in the status quo [E1]. Second clause here.",
        "pull": "Progress they buy: the edit lands in the timeline [E3].",
        "habit": "partial — already paying for the old stack [E4].",
        "anxiety": "partial — few pre-switch fears surface in the reviews.",
    },
    "evidence": {
        "source": "Capterra reviews, 2026-07-24. Extra sentence.",
        "ledger": [
            {"id": "E1", "quote": "Emails with unclear timecodes and confusion.", "who": "Travis G."},
            {"id": "E2", "quote": "I funnel clients to one place for feedback.", "who": "Chris F."},
            {"id": "E3", "quote": "Comments show up on my Premiere timeline.", "who": "Adri L."},
        ],
        "weaknesses": ["Small sample", "No decision-timeline", "Buyer vs user unsplit"],
    },
    "open_questions": ["Who is the buyer?", "Real pre-switch fears?", "Frequencies across corpus?"],
    "macro": "m-video-approval",
    "odi": {
        "note": "creator-estimate (Claude, 2026-07-29) — fix when data arrives",
        "outcomes": [
            {"statement": "Minimize the effort to leave frame-accurate feedback",
             "stage": "monitor", "importance": 8.5, "satisfaction": 3,
             "evidence": ["E2", "E3"], "basis": "E7 — a dozen clients struggled. Second sentence."},
            {"statement": "Minimize the time from final cut to sign-off",
             "stage": "conclude", "importance": 9.5, "satisfaction": 6, "evidence": []},
            {"statement": "Minimize the cost when only some clients use it",
             "stage": "conclude", "importance": 7, "satisfaction": 3, "evidence": ["E1"]},
        ],
    },
}

NO_ODI = {
    "name": "no-scores",
    "hook": "A project with no ODI block yet.",
    "jtbd": {"situation": "When X happens", "motivation": "I want Y", "outcome": "So that Z"},
    "switch_forces": {"push": "push text", "pull": "pull text"},
    "evidence": {"source": "interview", "quotes": ["A quote here."], "weaknesses": []},
    "open_questions": [],
}


class SingleProjectHappyPath(unittest.TestCase):
    def setUp(self):
        self.md = report.render_exec_summary(RICH, lang="en")

    def test_has_core_sections(self):
        for heading in ("# Executive summary — widget-flow", "## The job",
                        "## Top opportunities", "## Switch forces",
                        "## Evidence health", "## Load-bearing quote",
                        "## Open questions", "## Recommended next move"):
            self.assertIn(heading, self.md)

    def test_top_opportunity_ranked_first_with_evidence_ids(self):
        # opp = 8.5 + (8.5-3) = 14 is the worst-served → first, ids inline
        self.assertRegex(self.md, r"1\. \*\*Minimize the effort to leave frame-accurate feedback\*\*.*opp 14\.0")
        self.assertIn("[E2, E3]", self.md)

    def test_job_triple_is_one_paragraph(self):
        self.assertIn("When a producer collects edits scattered across email [E1]. "
                      "I want every comment in one place tied to a timecode.", self.md)

    def test_next_move_is_worst_served_stage(self):
        self.assertIn("attack the **monitor** stage: Minimize the effort to leave "
                      "frame-accurate feedback", self.md)

    def test_forces_flag_partial(self):
        self.assertIn("forces flagged partial/unknown", self.md)

    def test_evidence_count(self):
        self.assertIn("3 verbatim quote(s)", self.md)


class CreatorEstimateCaveat(unittest.TestCase):
    def test_caveat_present_when_creator_estimate(self):
        md = report.render_exec_summary(RICH, lang="en")
        self.assertIn("Scores are a creator estimate", md)

    def test_caveat_absent_otherwise(self):
        data = json.loads(json.dumps(RICH))
        data["odi"]["note"] = "scored from a 40-person survey, 2026-07"
        md = report.render_exec_summary(data, lang="en")
        self.assertNotIn("Scores are a creator estimate", md)

    def test_caveat_localized_ru(self):
        md = report.render_exec_summary(RICH, lang="ru")
        self.assertIn("прикидка автора", md)


class MissingOdiGraceful(unittest.TestCase):
    def test_no_crash_and_message(self):
        md = report.render_exec_summary(NO_ODI, lang="en")
        self.assertIn("No ODI scoring yet", md)
        # still renders the parts that don't need scores
        self.assertIn("## The job", md)
        self.assertIn("A quote here.", md)

    def test_next_move_falls_back(self):
        md = report.render_exec_summary(NO_ODI, lang="en")
        self.assertIn("## Recommended next move", md)


class CorpusMode(unittest.TestCase):
    def _write_corpus(self, root):
        corpus = {
            "macros": [
                {"id": "m-video-approval", "name": "Get video approved by clients"},
                {"id": "m-knowledge", "name": "Capture and reuse session knowledge"},
            ]
        }
        (root / "corpus.json").write_text(json.dumps(corpus))
        (root / "widget-flow").mkdir()
        (root / "widget-flow" / "jtbd.json").write_text(json.dumps(RICH))
        thin = json.loads(json.dumps(RICH))
        thin["name"] = "thin-one"
        thin["macro"] = "m-knowledge"
        thin["evidence"] = {"source": "one review", "ledger": [
            {"id": "E1", "quote": "single quote", "who": "someone"}]}
        (root / "thin-one").mkdir()
        (root / "thin-one" / "jtbd.json").write_text(json.dumps(thin))

    def test_corpus_render(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self._write_corpus(root)
            from report import find_bundles, load_corpus, shape_project
            bundles = find_bundles(root)
            projects = [shape_project(b) for b in bundles]
            md = report.render_corpus_summary(projects, load_corpus(root), lang="en")
        self.assertIn("# Corpus executive summary", md)
        self.assertIn("2 projects.", md)
        # macro names resolved from corpus.json
        self.assertIn("Get video approved by clients", md)
        self.assertIn("Capture and reuse session knowledge", md)
        # top-5 table header + a worst-served row
        self.assertIn("| Project | Outcome | imp | sat | opp | tier |", md)
        # worst-served outcome (opp 14.0) ranks into the top-5 table
        self.assertIn("| 14.0 | prioritize |", md)
        # evidence-thin project called out (1 quote < 3)
        self.assertIn("thin-one — 1 quote(s)", md)

    def test_main_writes_file(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self._write_corpus(root)
            out = root / "out.md"
            rc = report.main(["exec-summary", "--all", "--root", str(root), "--out", str(out)])
            self.assertEqual(rc, 0)
            self.assertTrue(out.is_file())
            self.assertIn("Corpus executive summary", out.read_text())

    def test_main_single_writes_default_path(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self._write_corpus(root)
            rc = report.main(["exec-summary", "widget-flow", "--root", str(root)])
            self.assertEqual(rc, 0)
            self.assertTrue((root / "widget-flow" / "exec-summary.md").is_file())


if __name__ == "__main__":
    unittest.main()
