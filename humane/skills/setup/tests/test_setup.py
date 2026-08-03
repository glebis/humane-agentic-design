"""Tests for humane setup. Stdlib unittest, no network, nothing installed."""

import json
import pathlib
import sys
import tempfile
import unittest
import unittest.mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
import humane_setup as hs  # noqa: E402


class ConfigResolutionTests(unittest.TestCase):
    """Precedence: project > global > env > built-in default."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = pathlib.Path(self.tmp.name)
        self.global_cfg = self.d / "global.json"
        self._patch = unittest.mock.patch.object(hs, "GLOBAL_CONFIG", self.global_cfg)
        self._patch.start()

    def tearDown(self):
        self._patch.stop()
        self.tmp.cleanup()

    def _clear_env(self):
        return unittest.mock.patch.dict(
            hs.os.environ, {v[0]: "" for v in hs.SETTINGS.values()}, clear=False)

    def test_defaults_when_nothing_is_set(self):
        with self._clear_env():
            cfg = hs.resolve_config(self.d)
        self.assertEqual(cfg["corpus_root"]["value"], "~/jtbd")
        self.assertEqual(cfg["corpus_root"]["source"], "default")

    def test_env_beats_default(self):
        with unittest.mock.patch.dict(hs.os.environ, {"HUMANE_CORPUS_ROOT": "/env/jtbd"}):
            cfg = hs.resolve_config(self.d)
        self.assertEqual(cfg["corpus_root"]["value"], "/env/jtbd")
        self.assertEqual(cfg["corpus_root"]["source"], "$HUMANE_CORPUS_ROOT")

    def test_global_beats_env(self):
        self.global_cfg.write_text(json.dumps({"corpus_root": "/global/jtbd"}))
        with unittest.mock.patch.dict(hs.os.environ, {"HUMANE_CORPUS_ROOT": "/env/jtbd"}):
            cfg = hs.resolve_config(self.d)
        self.assertEqual(cfg["corpus_root"]["value"], "/global/jtbd")

    def test_project_beats_global_and_env(self):
        self.global_cfg.write_text(json.dumps({"corpus_root": "/global/jtbd"}))
        (self.d / hs.PROJECT_CONFIG).write_text(json.dumps({"corpus_root": "./research"}))
        with unittest.mock.patch.dict(hs.os.environ, {"HUMANE_CORPUS_ROOT": "/env/jtbd"}):
            cfg = hs.resolve_config(self.d)
        self.assertEqual(cfg["corpus_root"]["value"], "./research")
        self.assertEqual(cfg["corpus_root"]["source"], hs.PROJECT_CONFIG)

    def test_layers_mix_per_key(self):
        """A project file setting one key must not shadow the others."""
        self.global_cfg.write_text(json.dumps({"language": "ru"}))
        (self.d / hs.PROJECT_CONFIG).write_text(json.dumps({"corpus_root": "./r"}))
        with self._clear_env():
            cfg = hs.resolve_config(self.d)
        self.assertEqual(cfg["corpus_root"]["source"], hs.PROJECT_CONFIG)
        self.assertEqual(cfg["language"]["value"], "ru")
        self.assertEqual(cfg["token_base"]["source"], "default")

    def test_malformed_config_is_ignored_not_fatal(self):
        self.global_cfg.write_text("{ this is not json")
        with self._clear_env():
            cfg = hs.resolve_config(self.d)
        self.assertEqual(cfg["corpus_root"]["source"], "default")

    def test_non_object_config_is_ignored(self):
        self.global_cfg.write_text("[1, 2, 3]")
        with self._clear_env():
            self.assertEqual(hs.resolve_config(self.d)["language"]["value"], "en")


class ConfigWriteTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = pathlib.Path(self.tmp.name)
        self._patch = unittest.mock.patch.object(hs, "GLOBAL_CONFIG", self.d / "g.json")
        self._patch.start()

    def tearDown(self):
        self._patch.stop()
        self.tmp.cleanup()

    def test_write_global_and_read_back(self):
        hs.write_config({"language": "ru"}, scope="global", project_dir=self.d)
        self.assertEqual(hs.resolve_config(self.d)["language"]["value"], "ru")

    def test_write_merges_rather_than_replaces(self):
        hs.write_config({"language": "ru"}, "global", self.d)
        hs.write_config({"task_export": "beads"}, "global", self.d)
        cfg = hs.resolve_config(self.d)
        self.assertEqual(cfg["language"]["value"], "ru")
        self.assertEqual(cfg["task_export"]["value"], "beads")

    def test_write_project_scope(self):
        path = hs.write_config({"corpus_root": "./r"}, "project", self.d)
        self.assertTrue(path.endswith(hs.PROJECT_CONFIG))
        self.assertEqual(hs.resolve_config(self.d)["corpus_root"]["value"], "./r")

    def test_unknown_setting_is_refused(self):
        """A typo must not be silently persisted as dead config."""
        with self.assertRaises(ValueError) as ctx:
            hs.write_config({"corpse_root": "/x"}, "global", self.d)
        self.assertIn("corpse_root", str(ctx.exception))


class CheckTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = pathlib.Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _cfg(self, **over):
        cfg = {k: {"value": v[1], "source": "default"} for k, v in hs.SETTINGS.items()}
        for k, v in over.items():
            cfg[k] = {"value": v, "source": "test"}
        return cfg

    def test_corpus_missing_dir(self):
        c = hs.check_corpus(self._cfg(corpus_root=str(self.d / "nope")))
        self.assertEqual(c["state"], "optional")
        self.assertIn("humane:jtbd", c["fix"])

    def test_corpus_present_but_empty(self):
        c = hs.check_corpus(self._cfg(corpus_root=str(self.d)))
        self.assertEqual(c["state"], "optional")
        self.assertIn("no jtbd.json", c["detail"])

    def test_corpus_counts_bundles(self):
        for name in ("a", "b"):
            (self.d / name).mkdir()
            (self.d / name / "jtbd.json").write_text("{}")
        (self.d / "not-a-bundle").mkdir()
        c = hs.check_corpus(self._cfg(corpus_root=str(self.d)))
        self.assertEqual(c["state"], "ok")
        self.assertIn("2 bundle", c["detail"])

    def test_token_base_found(self):
        base = self.d / "base.tokens.json"
        base.write_text("{}")
        self.assertEqual(hs.check_tokens(self._cfg(token_base=str(base)))["state"], "ok")

    def test_project_tokens_detected(self):
        (self.d / "design.tokens.json").write_text("{}")
        self.assertEqual(hs.check_project_tokens(self.d)["state"], "ok")

    def test_project_tokens_absent_suggests_setup(self):
        c = hs.check_project_tokens(self.d)
        self.assertEqual(c["state"], "optional")
        self.assertIn("setup-edit", c["fix"])

    def test_task_export_none_is_ok(self):
        self.assertEqual(hs.check_task_export(self._cfg(task_export="none"))["state"], "ok")

    def test_task_export_unknown_target(self):
        c = hs.check_task_export(self._cfg(task_export="jira"))
        self.assertEqual(c["state"], "optional")
        self.assertIn("jira", c["detail"])

    def test_task_export_missing_cli(self):
        with unittest.mock.patch.object(hs.shutil, "which", return_value=None):
            c = hs.check_task_export(self._cfg(task_export="linear"))
        self.assertEqual(c["state"], "optional")
        self.assertIn("not on PATH", c["detail"])

    def test_python_check_passes_on_this_interpreter(self):
        self.assertEqual(hs.check_python()["state"], "ok")


class DoctorTests(unittest.TestCase):
    def test_doctor_is_read_only(self):
        """The doctor must not create the paths it reports as missing."""
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            with unittest.mock.patch.object(hs, "GLOBAL_CONFIG", root / "g.json"), \
                 unittest.mock.patch.dict(hs.os.environ,
                                          {"HUMANE_CORPUS_ROOT": str(root / "corpus"),
                                           "HUMANE_TOKEN_BASE": str(root / "b.tokens.json")}):
                hs.doctor(root)
            self.assertFalse((root / "corpus").exists())
            self.assertFalse((root / "b.tokens.json").exists())
            self.assertFalse((root / "g.json").exists())

    def test_doctor_reports_every_setting_and_check(self):
        report = hs.doctor(".")
        self.assertEqual(set(report["config"]), set(hs.SETTINGS))
        names = [c["name"] for c in report["checks"]]
        for expected in ("python3", "corpus", "token base", "image backend"):
            self.assertIn(expected, names)

    def test_render_states_nothing_was_changed(self):
        text = hs.render(hs.doctor("."))
        self.assertIn("Nothing was installed or changed", text)

    def test_optional_gaps_do_not_block(self):
        """Only a genuinely required check may report `missing`."""
        report = hs.doctor(".")
        for c in report["checks"]:
            if c["name"].startswith("companion") or c["name"] in (
                    "corpus", "token base", "project tokens", "image backend", "task export"):
                self.assertNotEqual(c["state"], "missing", c["name"])


if __name__ == "__main__":
    unittest.main()


class CopyDriftTests(unittest.TestCase):
    """Drift between copies of a skill is a named outcome of this project, and
    the one failure the method cannot catch by reading a repo."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = pathlib.Path(self.tmp.name)
        # a canonical checkout: <root>/humane/skills/<skill>
        self.canon = self.d / "repo" / "humane" / "skills"
        (self.canon / "jtbd" / "scripts").mkdir(parents=True)
        (self.canon / "jtbd" / "SKILL.md").write_text("---\nname: jtbd\n---\nbody\n")
        (self.canon / "jtbd" / "scripts" / "graph.py").write_text("# graph\n")
        manifest = self.canon.parent / ".claude-plugin"
        manifest.mkdir(parents=True)
        (manifest / "plugin.json").write_text(json.dumps({"version": "9.9.9"}))
        self.root = self.d / "elsewhere" / "skills"
        self.root.mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def _check(self):
        return hs.check_humane_copies(roots=[self.root], canonical_root=self.canon,
                                      marketplaces=self.d / "no-marketplaces")

    def test_no_copies_is_clean(self):
        states = [c["state"] for c in self._check()]
        self.assertEqual(states, ["ok"])

    def test_symlink_back_to_the_checkout_is_the_good_case(self):
        (self.root / "jtbd").symlink_to(self.canon / "jtbd")
        checks = self._check()
        self.assertEqual(checks[0]["state"], "ok")
        self.assertIn("1 linked", checks[0]["detail"])

    def test_copy_missing_a_file_is_named_precisely(self):
        """The real case: ~/.codex/skills/jtbd had lost scripts/graph.py, so
        Graph Mode silently did not exist on that agent."""
        dst = self.root / "jtbd"
        (dst / "scripts").mkdir(parents=True)
        (dst / "SKILL.md").write_text("---\nname: jtbd\n---\nbody\n")
        checks = [c for c in self._check() if c["name"] == "humane copy"]
        self.assertEqual(len(checks), 1)
        self.assertIn("scripts/graph.py", checks[0]["detail"])
        self.assertIn("missing 1 file", checks[0]["detail"])

    def test_symlink_to_a_different_repo_is_flagged(self):
        other = self.d / "other-repo" / "jtbd"
        other.mkdir(parents=True)
        (other / "SKILL.md").write_text("---\nname: jtbd\n---\ndifferent\n")
        (self.root / "jtbd").symlink_to(other)
        detail = [c for c in self._check() if c["name"] == "humane copy"][0]["detail"]
        self.assertIn("links to a different source", detail)
        self.assertIn("SKILL.md differs", detail)

    def test_identical_independent_copy_is_still_reported(self):
        """Identical today is not linked; it will drift the moment either moves."""
        dst = self.root / "jtbd"
        (dst / "scripts").mkdir(parents=True)
        (dst / "SKILL.md").write_text((self.canon / "jtbd" / "SKILL.md").read_text())
        (dst / "scripts" / "graph.py").write_text("# graph\n")
        detail = [c for c in self._check() if c["name"] == "humane copy"][0]["detail"]
        self.assertIn("identical for now", detail)

    def test_build_artefacts_do_not_count_as_drift(self):
        dst = self.root / "jtbd"
        (dst / "scripts" / "__pycache__").mkdir(parents=True)
        (dst / "scripts" / "__pycache__" / "x.pyc").write_text("junk")
        (dst / "SKILL.md").write_text((self.canon / "jtbd" / "SKILL.md").read_text())
        (dst / "scripts" / "graph.py").write_text("# graph\n")
        detail = [c for c in self._check() if c["name"] == "humane copy"][0]["detail"]
        self.assertNotIn("extra file", detail)

    def test_drift_never_blocks(self):
        dst = self.root / "jtbd"
        dst.mkdir(parents=True)
        (dst / "SKILL.md").write_text("different\n")
        for c in self._check():
            self.assertNotEqual(c["state"], "missing")


class MarketplaceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = pathlib.Path(self.tmp.name)
        self.canon = self.d / "repo" / "humane" / "skills"
        (self.canon / "jtbd").mkdir(parents=True)
        (self.canon / "jtbd" / "SKILL.md").write_text("x")
        (self.canon.parent / ".claude-plugin").mkdir(parents=True)
        (self.canon.parent / ".claude-plugin" / "plugin.json").write_text(
            json.dumps({"version": "0.9.0"}))
        self.base = self.d / "marketplaces"

    def tearDown(self):
        self.tmp.cleanup()

    def _install(self, version, skills):
        d = self.base / "humane-agentic-design" / "humane"
        (d / ".claude-plugin").mkdir(parents=True)
        (d / ".claude-plugin" / "plugin.json").write_text(json.dumps({"version": version}))
        for s in skills:
            (d / "skills" / s).mkdir(parents=True)
            (d / "skills" / s / "SKILL.md").write_text("x")

    def test_pinned_old_marketplace_is_flagged(self):
        """A registered marketplace pins a commit, so it reports itself in sync
        with its own remote while sitting versions behind the repo."""
        self._install("0.6.1", ["jtbd"])
        c = hs._check_plugin_marketplaces(self.base, self.canon)[0]
        self.assertEqual(c["state"], "optional")
        self.assertIn("v0.6.1", c["detail"])
        self.assertIn("v0.9.0", c["detail"])
        self.assertIn("/plugin update", c["fix"])

    def test_matching_marketplace_is_ok(self):
        self._install("0.9.0", ["jtbd"])
        self.assertEqual(hs._check_plugin_marketplaces(self.base, self.canon)[0]["state"], "ok")

    def test_absent_marketplace_dir_is_silent(self):
        self.assertEqual(hs._check_plugin_marketplaces(self.d / "nope", self.canon), [])
