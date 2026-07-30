"""Tests for the brandkit adapter + confirm-then-write handoff. Stdlib unittest."""

import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
import brandkit  # noqa: E402

FIXTURE = pathlib.Path(__file__).resolve().parent / "fixtures" / "set.tokens.json"
DIRECTION = {
    "imageryStyle": "textured risograph, 2-3 spot colors, warm paper ground",
    "mood": ["editorial", "calm", "precise"],
    "avoid": ["stock-photo people", "neon glow"],
    "note": "ignored — not a brand-contract key",
}


class FakeProc:
    def __init__(self, rc=0):
        self.returncode = rc


class DirectionTests(unittest.TestCase):
    def test_normalize_keeps_only_contract_keys(self):
        norm = brandkit.normalize_direction(DIRECTION)
        self.assertEqual(set(norm), {"imageryStyle", "mood", "avoid"})
        self.assertNotIn("note", norm)

    def test_normalize_drops_empty_values(self):
        norm = brandkit.normalize_direction({"imageryStyle": "flat", "mood": [], "avoid": ""})
        self.assertEqual(norm, {"imageryStyle": "flat"})


class HandoffWriteTests(unittest.TestCase):
    def _tmp_tokens(self, d):
        p = pathlib.Path(d) / "set.tokens.json"
        p.write_text(FIXTURE.read_text())
        return p

    def test_writes_block_and_preserves_everything_else(self):
        with tempfile.TemporaryDirectory() as d:
            p = self._tmp_tokens(d)
            res = brandkit.write_brand_block(str(p), DIRECTION)
            self.assertEqual(res["action"], "updated")  # fixture already had a brand block (voice)
            tree = json.loads(p.read_text())
            block = tree["$extensions"]["community.design-tokens.brand"]
            # chosen direction written
            self.assertEqual(block["imageryStyle"], DIRECTION["imageryStyle"])
            self.assertEqual(block["mood"], DIRECTION["mood"])
            self.assertEqual(block["avoid"], DIRECTION["avoid"])
            # pre-existing brand key preserved
            self.assertEqual(block["voice"], "editorial, not salesy")
            # unrelated $extensions preserved
            self.assertEqual(tree["$extensions"]["com.example.other"], {"keep": "me"})
            # tokens untouched
            self.assertEqual(tree["color"]["primary"]["$value"], "#0E7C7B")
            # non-contract key not leaked
            self.assertNotIn("note", block)

    def test_created_block_when_absent(self):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "bare.tokens.json"
            p.write_text(json.dumps({"color": {"$type": "color", "primary": {"$value": "#000"}}}))
            res = brandkit.write_brand_block(str(p), DIRECTION)
            self.assertEqual(res["action"], "created-block")
            block = json.loads(p.read_text())["$extensions"]["community.design-tokens.brand"]
            self.assertEqual(block["mood"], DIRECTION["mood"])

    def test_draft_when_no_token_set(self):
        with tempfile.TemporaryDirectory() as d:
            res = brandkit.write_brand_block(None, DIRECTION, out_dir=d)
            self.assertEqual(res["action"], "draft")
            draft = pathlib.Path(res["path"])
            self.assertEqual(draft.name, "brand-block.draft.json")
            body = json.loads(draft.read_text())
            self.assertEqual(
                body["$extensions"]["community.design-tokens.brand"]["imageryStyle"],
                DIRECTION["imageryStyle"])

    def test_merge_does_not_mutate_caller_tree(self):
        tree = json.loads(FIXTURE.read_text())
        brandkit.merge_brand_block(tree, DIRECTION)
        # original still only has 'voice'
        self.assertEqual(
            tree["$extensions"]["community.design-tokens.brand"], {"voice": "editorial, not salesy"})


class RegenTests(unittest.TestCase):
    def test_regenerate_invokes_design_md_with_sibling_output(self):
        calls = []

        def runner(cmd):
            calls.append(cmd)
            return FakeProc(0)

        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "set.tokens.json"
            p.write_text("{}")
            cmd, rc = brandkit.regenerate_design_md(str(p), runner=runner, cli="/fake/tokens")
            self.assertEqual(rc, 0)
            self.assertEqual(cmd[0], "/fake/tokens")
            self.assertEqual(cmd[1], "design-md")
            self.assertIn("-o", cmd)
            # DESIGN.md written next to the token file
            self.assertTrue(cmd[-1].endswith("DESIGN.md"))
            self.assertEqual(str(pathlib.Path(cmd[-1]).parent), d)

    def test_regenerate_noops_without_cli(self):
        ran = []
        original = brandkit._dtokens_cli
        brandkit._dtokens_cli = lambda: None  # simulate design-tokens not installed
        try:
            cmd, rc = brandkit.regenerate_design_md(
                "/x/set.tokens.json", runner=lambda c: ran.append(c))
        finally:
            brandkit._dtokens_cli = original
        self.assertIsNone(cmd)
        self.assertIsNone(rc)
        self.assertEqual(ran, [])  # runner never called


class BackendTests(unittest.TestCase):
    def test_no_backend_message_mentions_both_and_channels(self):
        self.assertIn("gpt-image-2", brandkit.NO_BACKEND_MESSAGE)
        self.assertIn("nano-banana", brandkit.NO_BACKEND_MESSAGE)
        self.assertIn("npx skills add", brandkit.NO_BACKEND_MESSAGE)

    def test_pick_backend_prefers_gpt(self):
        found = {"nano-banana": "/n", "gpt-image-2": "/g"}
        self.assertEqual(brandkit.pick_backend("auto", found), "gpt-image-2")
        self.assertEqual(brandkit.pick_backend("nano-banana", found), "nano-banana")
        self.assertIsNone(brandkit.pick_backend("missing", found))

    def test_board_command_landscape(self):
        cmd = brandkit.build_board_command("gpt-image-2", "/g", "prompt", "/out.png")
        self.assertIn("--size", cmd)
        self.assertIn("1536x1024", cmd)


if __name__ == "__main__":
    unittest.main()
