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
    def test_follows_corpus_root_when_unset(self):
        config = {"corpus_root": {"value": "~/work/jtbd"},
                  "artifact_root": {"value": ""}}
        self.assertEqual(humane_setup.artifact_root(config),
                         pathlib.Path("~/work/jtbd").expanduser())

    def test_overrides_corpus_root_when_set(self):
        config = {"corpus_root": {"value": "~/work/jtbd"},
                  "artifact_root": {"value": "~/product/design"}}
        self.assertEqual(humane_setup.artifact_root(config),
                         pathlib.Path("~/product/design").expanduser())

    def test_whitespace_only_counts_as_unset(self):
        config = {"corpus_root": {"value": "~/jtbd"},
                  "artifact_root": {"value": "   "}}
        self.assertEqual(humane_setup.artifact_root(config),
                         pathlib.Path("~/jtbd").expanduser())

    def test_it_is_a_known_setting(self):
        self.assertIn("artifact_root", humane_setup.SETTINGS)


class TestArtifactDir(unittest.TestCase):
    CONFIG = {"corpus_root": {"value": "~/jtbd"}, "artifact_root": {"value": ""}}

    def test_there_are_kinds_to_check(self):
        # Without this the loops below pass vacuously if the table is emptied.
        self.assertGreater(len(humane_setup.ARTIFACT_KINDS), 0)

    def test_every_kind_resolves_to_an_absolute_path(self):
        for kind in humane_setup.ARTIFACT_KINDS:
            with self.subTest(kind=kind):
                path = humane_setup.artifact_dir("acme", kind, self.CONFIG)
                self.assertTrue(
                    path.is_absolute(),
                    f"{kind} resolved to {path}, which is relative — a relative "
                    "path writes into whatever directory the agent is standing "
                    "in, which is how a prototype landed in the plugin source",
                )

    def test_the_slug_appears_in_the_path(self):
        path = humane_setup.artifact_dir("acme-till", "prototype", self.CONFIG)
        self.assertIn("acme-till", path.parts)

    def test_unknown_kind_is_refused(self):
        with self.assertRaises(ValueError):
            humane_setup.artifact_dir("acme", "mockup", self.CONFIG)

    def test_slug_cannot_escape_the_root(self):
        for bad in ("../escape", "a/b", ".hidden", ""):
            with self.subTest(slug=bad):
                with self.assertRaises(ValueError):
                    humane_setup.artifact_dir(bad, "prototype", self.CONFIG)


class TestPathsReference(unittest.TestCase):
    """The reference is what a reader consults; a kind missing from it is lost."""

    REFERENCE = (pathlib.Path(humane_setup.__file__).resolve().parents[1]
                 / "references" / "paths.md")

    def test_the_reference_exists(self):
        self.assertTrue(self.REFERENCE.exists(), f"missing {self.REFERENCE}")

    def test_every_kind_is_documented(self):
        text = self.REFERENCE.read_text(encoding="utf-8")
        for kind, directory in humane_setup.ARTIFACT_KINDS.items():
            with self.subTest(kind=kind):
                self.assertIn(
                    f"{directory}/", text,
                    f"`{directory}/` (kind {kind}) is not in references/paths.md — "
                    "add the row, or a reader cannot find what that skill wrote",
                )

    def test_the_design_file_exit_is_documented(self):
        # The .pen exit writes to the prototypes anchor but is the one artifact
        # here that cannot be opened without its application. A reader looking
        # up "where did my design file go" must find it in the table.
        text = self.REFERENCE.read_text(encoding="utf-8")
        self.assertIn(".pen", text,
                      "the design-file exit is not in references/paths.md")
        self.assertIn("design_tool", text,
                      "the setting that enables it is not named in the table")

    def test_design_tool_is_a_known_setting(self):
        self.assertIn("design_tool", humane_setup.SETTINGS)

    def test_both_roots_are_documented(self):
        text = self.REFERENCE.read_text(encoding="utf-8")
        for setting in ("corpus_root", "artifact_root"):
            with self.subTest(setting=setting):
                self.assertIn(setting, text)


if __name__ == "__main__":
    unittest.main()
