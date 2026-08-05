"""Tests for the brand-illustrate adapter. Stdlib unittest, no network, no spend."""

import contextlib
import json
import os
import pathlib
import sys
import tempfile
import unittest
import unittest.mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
import illustrate  # noqa: E402

FIXTURE = pathlib.Path(__file__).resolve().parent / "fixtures" / "brand.tokens.json"


def _tree():
    return json.loads(FIXTURE.read_text())


def _tokens_copy(d):
    """Copy the token fixture into a temp dir and return its path.

    run_batch saves the recipe *next to the token set*, so handing it the real
    fixture path wrote brand.illustrate-recipe.json into tests/fixtures/ on
    every run — the suite dirtied the working tree just by passing.
    """
    dest = pathlib.Path(d) / "brand.tokens.json"
    dest.write_text(FIXTURE.read_text())
    return dest


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
        # de-slop clauses lead
        self.assertEqual(negs[0], illustrate.DESLOP_NEGATIVES[0].split(",")[0].strip())
        # brand + user appended
        self.assertIn("hands", negs)
        # "neon glow" is already a de-slop ban ("no neon glow"), so the brand's
        # bare restatement collapses into it — the ban appears exactly once.
        glow = illustrate._neg_key("neon glow")
        self.assertEqual(sum(1 for n in negs if illustrate._neg_key(n) == glow), 1)

    def test_deslop_always_present(self):
        """Every de-slop ban survives the merge, at clause granularity."""
        negs = illustrate.merge_negatives({}, None)
        keys = [illustrate._neg_key(n) for n in negs]
        for entry in illustrate.DESLOP_NEGATIVES:
            for clause in illustrate._split_negatives(entry):
                self.assertIn(illustrate._neg_key(clause), keys, clause)

    def test_compound_entries_split_into_clauses(self):
        negs = illustrate.merge_negatives({}, ["no screens, no laptops, no phones"])
        for want in ("no screens", "no laptops", "no phones"):
            self.assertIn(want, negs)

    def test_comma_inside_a_clause_is_not_split(self):
        """Only a comma introducing a new `no ...` ban is a separator."""
        negs = illustrate.merge_negatives({}, ["no hero of big text, tiny label, gradient"])
        self.assertIn("no hero of big text, tiny label, gradient", negs)

    def test_semicolon_splits(self):
        negs = illustrate.merge_negatives({}, ["nothing dead-centre; no gray on color"])
        self.assertIn("nothing dead-centre", negs)
        self.assertIn("no gray on color", negs)

    def test_more_specific_restatement_is_dropped(self):
        """The real defect: brand `avoid` repeating a de-slop ban more verbosely."""
        brand = {"avoid": ["stock-photo people smiling at laptops"]}
        negs = illustrate.merge_negatives(brand, None)
        self.assertIn("no stock-photo people", negs)          # broad de-slop ban kept
        self.assertNotIn("stock-photo people smiling at laptops", negs)

    def test_plural_and_singular_are_the_same_ban(self):
        brand = {"avoid": ["glossy 3D blobs and lens flares"]}   # de-slop has "no lens flare"
        negs = illustrate.merge_negatives(brand, None)
        self.assertNotIn("glossy 3D blobs and lens flares", negs)

    def test_broader_later_ban_is_kept(self):
        """A later clause banning strictly more is not redundant."""
        negs = illustrate.merge_negatives({}, ["no faces"])
        self.assertIn("no faces", negs)

    def test_no_duplicate_keys_in_output(self):
        brand = {
            "avoid": ["stock-photo people smiling at laptops", "glossy 3D blobs and lens flares"],
            "negativePrompt": "no photorealism, no stock-photo people",
        }
        negs = illustrate.merge_negatives(brand, ["no faces", "no screens, no laptops"])
        keys = [illustrate._neg_key(n) for n in negs]
        self.assertEqual(len(keys), len(set(keys)))


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
    def test_no_backend_writes_prompts_instead_of_stopping(self):
        scaffold = illustrate.build_scaffold(
            _tree(), {"subject": "x", "platforms": ["og-image", "square-post"]})
        with tempfile.TemporaryDirectory() as d:
            res = illustrate.run_batch(scaffold, str(_tokens_copy(d)), d, found={})
            # the batch succeeds, it just did not generate
            self.assertTrue(res["ok"])
            self.assertFalse(res["generated"])
            self.assertEqual(res["error"], "no-backend")
            self.assertIsNone(res["backend"])
            # the prompts — the expensive part — are on disk
            prompts = pathlib.Path(res["prompts"])
            self.assertTrue(prompts.exists())
            body = prompts.read_text()
            self.assertIn(scaffold["items"][0]["prompt"], body)
            self.assertIn("1200x630", body)   # the size to paste it at
            # one entry per item x platform, same as a real run
            self.assertEqual(len(res["outputs"]),
                             len(scaffold["items"]) * len(scaffold["platforms"]))
            # and it is resumable
            self.assertTrue(pathlib.Path(res["metadata"]).exists())
            self.assertTrue(pathlib.Path(res["recipe"]).exists())

    def test_no_backend_message_says_how_to_proceed(self):
        msg = illustrate.NO_BACKEND_MESSAGE
        self.assertIn("gpt-image-2", msg)
        self.assertIn("nano-banana", msg)
        self.assertIn("npx skills add", msg)
        self.assertIn("HUMANE_IMAGE_BACKEND", msg)


class BackendResolutionTests(unittest.TestCase):
    def test_env_override_wins_and_is_reported(self):
        # No config file in play — this asserts the env layer beats *discovery*.
        # A config file legitimately beats the env var (setup: global > env);
        # that ordering is covered in ConfiguredBackendTests.
        with _no_configured_backend() as d:
            script = d / "my_generator.py"
            script.write_text("# stub\n")
            env = {"HUMANE_IMAGE_BACKEND": f"gpt-image-2:{script}"}
            with unittest.mock.patch.dict(illustrate.os.environ, env, clear=False):
                found = illustrate.probe_backends()
                self.assertEqual(found["gpt-image-2"], str(script))
                self.assertTrue(illustrate.backend_search_report()["override_valid"])

    def test_env_override_pointing_nowhere_is_ignored_not_fatal(self):
        with _no_configured_backend():
            env = {"HUMANE_IMAGE_BACKEND": "gpt-image-2:/nope/missing.py"}
            with unittest.mock.patch.dict(illustrate.os.environ, env, clear=False):
                report = illustrate.backend_search_report()
                self.assertFalse(report["override_valid"])

    def test_custom_skills_dir_is_searched(self):
        with _no_configured_backend() as home:
            script = home / "nano-banana" / "scripts" / "nano_banana.py"
            script.parent.mkdir(parents=True)
            script.write_text("# stub\n")
            env = {"HUMANE_SKILLS_DIR": str(home), "HUMANE_IMAGE_BACKEND": ""}
            with unittest.mock.patch.dict(illustrate.os.environ, env, clear=False):
                self.assertEqual(illustrate.probe_backends().get("nano-banana"),
                                 str(script))

    def test_search_is_not_claude_specific(self):
        roots = " ".join(illustrate.backend_search_report()["roots_searched"])
        self.assertIn(".codex", roots)
        self.assertIn(".agents", roots)
        # Claude is one candidate among several, not the assumption
        self.assertIn(".claude", roots)

    def test_pick_backend_auto_prefers_seeded(self):
        found = {"nano-banana": "/n", "gpt-image-2": "/g"}
        with _no_configured_backend():
            self.assertEqual(illustrate.pick_backend("auto", found), "gpt-image-2")
            self.assertEqual(illustrate.pick_backend("nano-banana", found), "nano-banana")
            self.assertIsNone(illustrate.pick_backend("missing", found))


@contextlib.contextmanager
def _no_configured_backend():
    """Run with no image_backend from any layer: an empty env var, a cwd holding
    no humane.json, and HOME pointed somewhere empty. Without this a developer's
    own ~/.humane/config.json decides the result and the suite passes by
    accident. HOME is what must be patched — `Path.expanduser` reads the
    environment variable and ignores a patched `Path.home`."""
    with tempfile.TemporaryDirectory() as d:
        prior = os.getcwd()
        os.chdir(d)
        try:
            with unittest.mock.patch.dict(
                    illustrate.os.environ,
                    {"HUMANE_IMAGE_BACKEND": "", "HOME": d}, clear=False):
                yield pathlib.Path(d)
        finally:
            os.chdir(prior)


class ConfiguredBackendTests(unittest.TestCase):
    """`image_backend` is a documented setting with four layers. Reading only
    the environment made `config --set image_backend=...` a silent no-op."""

    def test_project_humane_json_selects_the_backend(self):
        with _no_configured_backend() as d:
            (d / "humane.json").write_text('{"image_backend": "nano-banana"}')
            found = {"nano-banana": "/n", "gpt-image-2": "/g"}
            # ...even though auto would have preferred gpt-image-2.
            self.assertEqual(illustrate.pick_backend("auto", found), "nano-banana")
            self.assertEqual(illustrate._config_value()[0], "nano-banana")

    def test_project_file_outranks_the_environment(self):
        with _no_configured_backend() as d:
            (d / "humane.json").write_text('{"image_backend": "nano-banana"}')
            with unittest.mock.patch.dict(
                    illustrate.os.environ,
                    {"HUMANE_IMAGE_BACKEND": "gpt-image-2"}, clear=False):
                self.assertEqual(illustrate._config_value()[0], "nano-banana")

    def test_environment_still_applies_when_no_file_says_otherwise(self):
        with _no_configured_backend():
            with unittest.mock.patch.dict(
                    illustrate.os.environ,
                    {"HUMANE_IMAGE_BACKEND": "nano-banana"}, clear=False):
                found = {"nano-banana": "/n", "gpt-image-2": "/g"}
                self.assertEqual(illustrate.pick_backend("auto", found), "nano-banana")

    def test_auto_is_not_a_choice_and_leaves_the_recipe_alone(self):
        with _no_configured_backend() as d:
            (d / "humane.json").write_text('{"image_backend": "auto"}')
            found = {"nano-banana": "/n", "gpt-image-2": "/g"}
            # The recipe asked for nano-banana; a configured "auto" must not
            # override it, or the default value would silently beat the recipe.
            self.assertEqual(illustrate.pick_backend("nano-banana", found),
                             "nano-banana")

    def test_configured_backend_may_carry_a_path(self):
        with _no_configured_backend() as d:
            script = d / "gen.py"
            script.write_text("# stub\n")
            (d / "humane.json").write_text(
                json.dumps({"image_backend": f"gpt-image-2:{script}"}))
            self.assertEqual(illustrate.probe_backends()["gpt-image-2"], str(script))

    def test_global_config_outranks_the_environment(self):
        """setup's documented order is project > global > env. A machine-wide
        choice the user wrote down beats a variable that happens to be exported
        in whatever shell the run started from."""
        with _no_configured_backend() as home:
            (home / ".humane").mkdir()
            (home / ".humane" / "config.json").write_text(
                '{"image_backend": "nano-banana"}')
            with unittest.mock.patch.dict(
                    illustrate.os.environ,
                    {"HUMANE_IMAGE_BACKEND": "gpt-image-2"}, clear=False):
                self.assertEqual(illustrate._config_value()[0], "nano-banana")

    def test_a_directory_is_not_a_backend(self):
        """`.exists()` is true for a directory, so `name:/tmp` was reported as
        found and override_valid — then the run tried to execute a directory."""
        with _no_configured_backend() as d:
            (d / "humane.json").write_text(
                json.dumps({"image_backend": f"gpt-image-2:{d}"}))
            self.assertNotIn("gpt-image-2:" + str(d),
                             str(illustrate.probe_backends().get("gpt-image-2")))
            self.assertFalse(illustrate.backend_search_report()["override_valid"])

    def test_a_non_python_backend_must_be_executable(self):
        """A .py script gets `python3` in front of it; anything else is run
        directly and has to carry the executable bit."""
        with _no_configured_backend() as d:
            plain = d / "gen"
            plain.write_text("#!/bin/sh\n")
            self.assertFalse(illustrate._is_runnable(plain))
            plain.chmod(0o755)
            self.assertTrue(illustrate._is_runnable(plain))
            script = d / "gen.py"
            script.write_text("# stub\n")  # not chmod'ed
            self.assertTrue(illustrate._is_runnable(script))

    def test_probe_reads_the_project_dir_it_is_given(self):
        """setup's doctor passes --project-dir; without threading it through,
        the probe read a humane.json from the shell's cwd instead."""
        with _no_configured_backend() as d:
            elsewhere = d / "elsewhere"
            elsewhere.mkdir()
            (elsewhere / "humane.json").write_text(
                json.dumps({"image_backend": "nano-banana"}))
            self.assertEqual(illustrate._config_value(elsewhere)[0], "nano-banana")
            self.assertIsNone(illustrate._config_value(d)[0])

    def test_unparseable_config_does_not_crash_generation(self):
        """setup doctor explains a broken config; the generator just proceeds."""
        with _no_configured_backend() as d:
            (d / "humane.json").write_text("{not json")
            self.assertEqual(illustrate._config_value()[0], None)


class BatchRunTests(unittest.TestCase):
    def test_run_batch_writes_metadata_and_sheet(self):
        answers = {"subject": "grid lighthouse", "count": 2,
                   "platforms": ["og-image", "square-post"], "backend": "gpt-image-2"}
        scaffold = illustrate.build_scaffold(_tree(), answers)
        calls = []

        def fake_runner(cmd):
            calls.append(cmd)
            return FakeProc(0)

        # The scaffold asks for gpt-image-2; a configured backend would rightly
        # outrank it, so neutralise the config layers to test the batch itself.
        with _no_configured_backend(), tempfile.TemporaryDirectory() as d:
            res = illustrate.run_batch(
                scaffold, str(_tokens_copy(d)), d, runner=fake_runner,
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

    def test_nano_flagless_preset_is_recorded_as_unsized(self):
        """nano-banana has no free-form size flag, so `spot-ui` comes back at the
        backend's default. Nothing resizes it — the batch must say so instead of
        printing the target size as though it had been honoured."""
        answers = {"subject": "beacon", "count": 1,
                   "platforms": ["spot-ui", "og-image"], "backend": "nano-banana"}
        scaffold = illustrate.build_scaffold(_tree(), answers)
        with _no_configured_backend(), tempfile.TemporaryDirectory() as d:
            res = illustrate.run_batch(
                scaffold, str(_tokens_copy(d)), d, runner=lambda cmd: FakeProc(0),
                found={"nano-banana": "/fake/nano_banana.py"})
            self.assertEqual(res["unsized_platforms"], ["spot-ui"])
            by_plat = {o["platform"]: o for o in res["outputs"]}
            self.assertFalse(by_plat["spot-ui"]["size_requested"])
            # og-image maps to nano's `blog` platform at exactly 1200x630.
            self.assertTrue(by_plat["og-image"]["size_requested"])

    def test_no_backend_entries_carry_the_documented_schema(self):
        """SKILL.md says every metadata entry carries `size_requested`. The
        no-backend path is the one most likely to be read by hand, and it
        omitted the field entirely."""
        answers = {"subject": "beacon", "count": 1, "platforms": ["og-image"],
                   "backend": "auto"}
        scaffold = illustrate.build_scaffold(_tree(), answers)
        with tempfile.TemporaryDirectory() as d:
            res = illustrate.prompts_only(scaffold, d)
            meta = json.loads(pathlib.Path(res["metadata"]).read_text())
            self.assertTrue(meta["outputs"])
            for entry in meta["outputs"]:
                self.assertIn("size_requested", entry)
                # No backend ran, so no size was requested of one.
                self.assertIsNone(entry["size_requested"])

    def test_gpt_image_2_can_always_be_asked_for_a_size(self):
        for name in ("spot-ui", "og-image"):
            plat = dict(illustrate.PLATFORMS[name], name=name)
            self.assertTrue(illustrate._size_was_requested("gpt-image-2", plat))

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


class TestGallery(unittest.TestCase):
    def test_gallery_groups_batches_and_loose(self):
        import tempfile, json as _json, pathlib as _pl
        with tempfile.TemporaryDirectory() as td:
            root = _pl.Path(td)
            b = root / "20260101-batch"; b.mkdir()
            (b / "a.png").write_bytes(b"x" if isinstance(b"x", bytes) else b"x")
            (b / "metadata.json").write_text(_json.dumps({
                "backend": "gpt-image-2",
                "outputs": [{"file": "a.png", "subject": "loop", "platform": "square-post", "size": "1080x1080"}]}))
            (root / "loose.png").write_bytes(bytes(1))
            out = illustrate.write_gallery(root)
            html = _pl.Path(out).read_text()
            self.assertIn("20260101-batch", html)
            self.assertIn("Other images", html)
            self.assertIn("loose.png", html)
            self.assertIn('dialog id="lb"', html)          # lightbox present
            self.assertIn("ArrowRight", html)               # keyboard nav
            self.assertIn("2 images across 2 group(s)", html)

    def test_contact_sheet_has_lightbox(self):
        import tempfile, pathlib as _pl
        with tempfile.TemporaryDirectory() as td:
            bd = _pl.Path(td)
            (bd / "x.png").write_bytes(bytes(1))
            out = illustrate.write_contact_sheet(bd, [{"file": "x.png", "subject": "s", "platform": "og-image", "size": "1200x630"}])
            html = _pl.Path(out).read_text()
            self.assertIn('dialog id="lb"', html)
            self.assertIn('data-full="x.png"', html)
