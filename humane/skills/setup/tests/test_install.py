"""The `install` command: it runs the doctor's own fixes, and only confirmed.

WHY. The fix strings the doctor prints were the single source of truth, but
executing them was left to whoever read the output — so "install what the user
confirms" had no machine path, and a second, drifting install recipe was one
helpful contributor away. `install` runs exactly the doctor's fix strings; these
tests pin the safety edges: agent slash commands are never shelled out,
non-interactive runs never treat piped input as consent, and an unknown name is
an error rather than a no-op.

Run:  cd humane/skills/setup && PYTHONPATH=scripts python3 -m pytest tests/ -v
"""

import io
import pathlib
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))

import humane_setup  # noqa: E402


def fake_report(fixes):
    checks = [{"name": n, "state": s, "detail": "", "fix": f} for n, s, f in fixes]
    return {"config": {}, "checks": checks, "problems": []}


class TestInstall(unittest.TestCase):
    def run_install(self, fixes, names=(), run_all=False, yes=False, tty=False):
        report = fake_report(fixes)
        with mock.patch.object(humane_setup, "doctor", return_value=report), \
             mock.patch.object(humane_setup, "render", return_value=""), \
             mock.patch.object(humane_setup.subprocess, "run") as run, \
             mock.patch.object(humane_setup.sys.stdin, "isatty", return_value=tty), \
             mock.patch("sys.stdout", new=io.StringIO()) as out, \
             mock.patch("sys.stderr", new=io.StringIO()) as err:
            code = humane_setup.install(list(names), run_all, yes)
        return code, run, out.getvalue(), err.getvalue()

    def test_no_names_lists_gaps_and_runs_nothing(self):
        code, run, out, _ = self.run_install(
            [("browser tool", "optional", "npm i -g agent-browser")])
        self.assertEqual(code, 0)
        run.assert_not_called()
        self.assertIn("npm i -g agent-browser", out)

    def test_agent_slash_command_is_never_shelled_out(self):
        code, run, out, _ = self.run_install(
            [("companion: interfaces", "optional", "/plugin install interfaces")],
            run_all=True, yes=True)
        run.assert_not_called()
        self.assertIn("agent command", out)

    def test_non_interactive_without_yes_refuses(self):
        # Piped input must never be consumed as consent to a shell command.
        code, run, _, err = self.run_install(
            [("browser tool", "optional", "npm i -g agent-browser")],
            names=["browser"], tty=False)
        run.assert_not_called()
        self.assertIn("--yes", err)

    def test_yes_runs_the_exact_fix_string(self):
        run_result = mock.Mock(returncode=0)
        report = fake_report([("browser tool", "optional", "npm i -g agent-browser")])
        with mock.patch.object(humane_setup, "doctor", return_value=report), \
             mock.patch.object(humane_setup, "render", return_value=""), \
             mock.patch.object(humane_setup.subprocess, "run",
                               return_value=run_result) as run, \
             mock.patch("sys.stdout", new=io.StringIO()):
            humane_setup.install(["browser"], False, True)
        run.assert_called_once_with("npm i -g agent-browser", shell=True)

    def test_unknown_name_is_an_error(self):
        code, run, _, err = self.run_install(
            [("browser tool", "optional", "npm i -g agent-browser")],
            names=["nonsense"], yes=True)
        self.assertEqual(code, 2)
        run.assert_not_called()
        self.assertIn("no gap matches", err)


if __name__ == "__main__":
    unittest.main()
