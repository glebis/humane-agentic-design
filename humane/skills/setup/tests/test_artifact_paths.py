"""Where generated artifacts go, and the guard against writing into the CWD.

WHY. A prototype was written to `./prototypes/<slug>/` and landed inside this
plugin's own source tree — untracked, not gitignored, one `git add -A` away from
being distributed to every user of the plugin. The cause was a path built from a
literal at the call site instead of resolved from configuration.

These tests exist so that the next skill which invents a path fails here, rather
than in somebody's repository.

Run:  cd humane/skills/setup && PYTHONPATH=scripts python3 -m pytest tests/ -v
"""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))

import humane_setup  # noqa: E402


class TestArtifactRoot(unittest.TestCase):
    def test_relative_default_resolves_against_the_project_not_the_cwd(self):
        # The whole reason this function exists. `.design` resolved against the
        # working directory would recreate the original bug precisely: an agent
        # standing in the plugin's source would create `.design` there.
        root = humane_setup.artifact_root({"artifact_root": {"value": ".design"}},
                                          project_dir="/tmp/acme")
        self.assertTrue(root.is_absolute())
        self.assertEqual(root.name, ".design")
        self.assertIn("acme", root.parts)
        self.assertNotEqual(root.parent, pathlib.Path.cwd())

    def test_an_absolute_value_is_used_as_given(self):
        self.assertEqual(
            humane_setup.artifact_root({"artifact_root": {"value": "~/product/design"}}),
            pathlib.Path("~/product/design").expanduser())

    def test_whitespace_only_falls_back_to_the_default(self):
        root = humane_setup.artifact_root({"artifact_root": {"value": "   "}},
                                          project_dir="/tmp/acme")
        self.assertEqual(root.name, humane_setup.SETTINGS["artifact_root"][1])

    def test_the_default_is_design(self):
        self.assertEqual(humane_setup.SETTINGS["artifact_root"][1], ".design")

    def test_it_is_a_known_setting(self):
        self.assertIn("artifact_root", humane_setup.SETTINGS)


class TestArtifactPath(unittest.TestCase):
    CONFIG = {"artifact_root": {"value": ".design"}}
    PROJECT = "/tmp/acme"

    def test_there_are_kinds_to_check(self):
        # Without this the loops below pass vacuously if the table is emptied.
        self.assertGreater(len(humane_setup.ARTIFACT_KINDS), 0)

    def test_the_name_carries_the_skill_that_made_it(self):
        path = humane_setup.artifact_path("dashboard", "prototype", "pen",
                                          self.CONFIG, self.PROJECT)
        self.assertEqual(path.name, "prototype-dashboard.pen",
                         "the prefix is how a reader tells which skill wrote a file")

    def test_omitting_the_extension_gives_a_directory_name(self):
        path = humane_setup.artifact_path("signup", "walkthrough",
                                          None, self.CONFIG, self.PROJECT)
        self.assertEqual(path.name, "walk-signup")

    def test_every_kind_resolves_to_an_absolute_path(self):
        for kind in humane_setup.ARTIFACT_KINDS:
            with self.subTest(kind=kind):
                path = humane_setup.artifact_path("x", kind, "txt",
                                                  self.CONFIG, self.PROJECT)
                self.assertTrue(
                    path.is_absolute(),
                    f"{kind} resolved to {path}, which is relative — a relative "
                    "path writes into whatever directory the agent is standing "
                    "in, which is how a prototype landed in the plugin source",
                )

    def test_unknown_kind_is_refused(self):
        with self.assertRaises(ValueError):
            humane_setup.artifact_path("x", "mockup", "png", self.CONFIG, self.PROJECT)

    def test_name_cannot_escape_the_root(self):
        for bad in ("../escape", "a/b", ".hidden", ""):
            with self.subTest(name=bad):
                with self.assertRaises(ValueError):
                    humane_setup.artifact_path(bad, "prototype", "pen",
                                               self.CONFIG, self.PROJECT)


class TestPathsReference(unittest.TestCase):
    """The reference is what a reader consults; a kind missing from it is lost."""

    REFERENCE = (pathlib.Path(humane_setup.__file__).resolve().parents[1]
                 / "references" / "paths.md")

    def test_the_reference_exists(self):
        self.assertTrue(self.REFERENCE.exists(), f"missing {self.REFERENCE}")

    def test_every_kind_is_documented(self):
        text = self.REFERENCE.read_text(encoding="utf-8")
        for kind, prefix in humane_setup.ARTIFACT_KINDS.items():
            with self.subTest(kind=kind):
                self.assertIn(
                    f"{prefix}-", text,
                    f"the `{prefix}-` prefix (kind {kind}) is not in "
                    "references/paths.md — add the row, or a reader cannot tell "
                    "which skill wrote a file",
                )

    def test_the_design_file_exit_is_documented(self):
        # The .pen exit is the one artifact whose location this table cannot
        # enforce — the backend keeps its own document store and ignores any
        # path given to it. A reader asking "where did my design file go" must
        # find that stated, along with the setting that enables the exit.
        text = self.REFERENCE.read_text(encoding="utf-8")
        self.assertIn(".pen", text,
                      "the design-file exit is not in references/paths.md")
        self.assertIn("design_tool", text,
                      "the setting that enables it is not named in the table")

    def test_design_tool_is_a_known_setting(self):
        self.assertIn("design_tool", humane_setup.SETTINGS)

    def test_both_roots_are_documented(self):
        text = self.REFERENCE.read_text(encoding="utf-8")
        for setting in ("corpus_root", "artifact_root", ".design"):
            with self.subTest(setting=setting):
                self.assertIn(setting, text)


if __name__ == "__main__":
    unittest.main()
