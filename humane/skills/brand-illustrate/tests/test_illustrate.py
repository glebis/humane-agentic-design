"""Tests for the brand-illustrate adapter. Stdlib unittest, no network, no spend."""

import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
import illustrate  # noqa: E402

FIXTURE = pathlib.Path(__file__).resolve().parent / "fixtures" / "brand.tokens.json"


def _tree():
    return json.loads(FIXTURE.read_text())


class FakeProc:
    def __init__(self, rc=0):
        self.returncode = rc


class ScaffoldTests(unittest.TestCase):
    def test_summarize_resolves_roles_and_aliases(self):
        s = illustrate.summarize_tokens(_tree())
        # role aliases resolved through {color.*} to concrete hexes
        self.assertEqual(s["roles"]["primary"], "#0E7C7B")
        self.assertEqual(s["roles"]["accent"], "#F2714E")
        self.assertEqual(s["roles"]["text"], "#13201F")
        self.assertEqual(s["roles"]["background"], "#FBF7F0")
        self.assertIn("Fraunces", s["fonts"])
        self.assertEqual(s["shape"], "rounded")  # 12px radius
        self.assertEqual(s["brand"]["mood"], ["precise", "editorial", "calm"])

    def test_compose_prompt_has_all_scaffold_parts(self):
        s = illustrate.summarize_tokens(_tree())
        answers = {"subject": "a lighthouse of interlocking grids", "style": "isotype pictograms"}
        prompt = illustrate.compose_prompt(s, answers["subject"], answers)
        self.assertIn("lighthouse of interlocking grids", prompt)
        self.assertIn("precise, editorial, calm", prompt)        # mood lead
        self.assertIn("Shared style across the set", prompt)      # series block
        self.assertIn("isotype pictograms", prompt)              # user style
        self.assertIn("#0E7C7B", prompt)                          # palette hex
        self.assertIn("primary", prompt)                          # palette role
        self.assertIn("Fraunces-style type", prompt)             # font
        self.assertIn("Strictly avoid", prompt)                   # negatives tail

    def test_series_block_absent_when_no_style_info(self):
        s = illustrate.summarize_tokens({"color": {"$type": "color",
                                                    "primary": {"$value": "#123456"}}})
        self.assertIsNone(illustrate.series_block(s, {}))


class NegativeMergeTests(unittest.TestCase):
    def test_merges_deslop_brand_and_user_without_dupes(self):
        brand = {"avoid": ["stock-photo people"], "negativePrompt": "neon glow"}
        negs = illustrate.merge_negatives(brand, user_negatives=["neon glow", "hands"])
        # de-slop entries lead
        self.assertEqual(negs[0], illustrate.DESLOP_NEGATIVES[0])
        # brand + user appended
        self.assertIn("stock-photo people", negs)
        self.assertIn("hands", negs)
        # case-insensitive dedupe: "neon glow" appears once
        self.assertEqual(sum(1 for n in negs if n.lower() == "neon glow"), 1)

    def test_deslop_always_present(self):
        negs = illustrate.merge_negatives({}, None)
        for d in illustrate.DESLOP_NEGATIVES:
            self.assertIn(d, negs)


class PlatformTests(unittest.TestCase):
    def test_preset_resolution(self):
        plats = illustrate.resolve_platforms({"platforms": ["og-image", "spot-ui"]})
        names = [p["name"] for p in plats]
        self.assertEqual(names, ["og-image", "spot-ui"])
        og = next(p for p in plats if p["name"] == "og-image")
        self.assertEqual((og["w"], og["h"], og["flag"]), (1200, 630, "blog"))
        spot = next(p for p in plats if p["name"] == "spot-ui")
        self.assertIsNone(spot["flag"])  # no native backend platform

    def test_unknown_platform_falls_back_to_default(self):
        plats = illustrate.resolve_platforms({"platforms": ["nonsense"]})
        self.assertEqual(plats[0]["name"], illustrate.DEFAULT_PLATFORM)

    def test_purpose_used_when_no_platforms(self):
        plats = illustrate.resolve_platforms({"purpose": "og-image"})
        self.assertEqual(plats[0]["name"], "og-image")


class BackendTests(unittest.TestCase):
    def test_no_backend_message(self):
        scaffold = illustrate.build_scaffold(_tree(), {"subject": "x"})
        with tempfile.TemporaryDirectory() as d:
            res = illustrate.run_batch(scaffold, str(FIXTURE), d, found={})
        self.assertFalse(res["ok"])
        self.assertEqual(res["error"], "no-backend")
        self.assertIn("gpt-image-2", res["message"])
        self.assertIn("nano-banana", res["message"])
        self.assertIn("npx skills add", res["message"])

    def test_pick_backend_auto_prefers_seeded(self):
        found = {"nano-banana": "/n", "gpt-image-2": "/g"}
        self.assertEqual(illustrate.pick_backend("auto", found), "gpt-image-2")
        self.assertEqual(illustrate.pick_backend("nano-banana", found), "nano-banana")
        self.assertIsNone(illustrate.pick_backend("missing", found))

    def test_run_batch_writes_metadata_and_sheet(self):
        answers = {"subject": "grid lighthouse", "count": 2,
                   "platforms": ["og-image", "square-post"], "backend": "gpt-image-2"}
        scaffold = illustrate.build_scaffold(_tree(), answers)
        calls = []

        def fake_runner(cmd):
            calls.append(cmd)
            return FakeProc(0)

        with tempfile.TemporaryDirectory() as d:
            res = illustrate.run_batch(
                scaffold, str(FIXTURE), d, runner=fake_runner,
                found={"gpt-image-2": "/fake/gpt_image_2.py"})
            self.assertTrue(res["ok"])
            # 2 subjects x 2 platforms = 4 generations
            self.assertEqual(len(calls), 4)
            meta = json.loads(pathlib.Path(res["metadata"]).read_text())
            self.assertEqual(len(meta["outputs"]), 4)
            self.assertEqual(meta["backend"], "gpt-image-2")
            self.assertIsNotNone(meta["seed"])  # default seed injected
            self.assertTrue(pathlib.Path(res["contact_sheet"]).exists())
            # gpt-image-2 command carries the seed for series coherence
            self.assertIn("--seed", calls[0])

    def test_command_uses_size_for_flagless_platform(self):
        spot = {"name": "spot-ui", "w": 512, "h": 512, "flag": None}
        cmd = illustrate.build_command("/g", "gpt-image-2", "p", "/out.png",
                                       spot, (512, 512), draft=True, seed=7)
        self.assertIn("--size", cmd)
        self.assertIn("512x512", cmd)


class RecipeTests(unittest.TestCase):
    def test_recipe_round_trip(self):
        answers = {"subject": "grid lighthouse", "count": 3, "style": "isotype",
                   "platforms": ["og-image"], "backend": "auto", "budget": "draft"}
        scaffold = illustrate.build_scaffold(_tree(), answers)
        with tempfile.TemporaryDirectory() as d:
            tokens_copy = pathlib.Path(d) / "brand.tokens.json"
            tokens_copy.write_text(FIXTURE.read_text())
            rp = illustrate.save_recipe(scaffold, str(tokens_copy))
            self.assertTrue(pathlib.Path(rp).exists())
            # recipe lands next to the token set, .tokens stripped from stem
            self.assertTrue(rp.endswith("brand.illustrate-recipe.json"))
            rec = illustrate.load_recipe(rp)
            self.assertEqual(rec["answers"], answers)
            self.assertEqual(rec["tokens"], str(tokens_copy))
            # rebuilding from the recipe reproduces the same items
            rebuilt = illustrate.build_scaffold(json.loads(
                pathlib.Path(rec["tokens"]).read_text()), rec["answers"])
            self.assertEqual([i["prompt"] for i in rebuilt["items"]],
                             [i["prompt"] for i in scaffold["items"]])


if __name__ == "__main__":
    unittest.main()
