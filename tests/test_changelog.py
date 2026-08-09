"""The changelog's structural contract, checked instead of remembered.

Two sessions editing in parallel each prepend an entry without seeing the
other's, and the file ends up with the same version heading twice, or with
sections out of order. Neither is discoverable by reading your own diff — only
by reading the whole file, which nobody does at commit time. So the contract
is a test:

- every `## <version> — <date>` heading is unique,
- versions are strictly descending (newest first, as the file promises),
- the top heading matches `plugin.json`, and `marketplace.json` agrees —
  the drift that once stranded an install on 0.9.0.

Run:  python3 -m pytest tests/ -v
"""

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHANGELOG = ROOT / "CHANGELOG.md"
PLUGIN = ROOT / "humane" / ".claude-plugin" / "plugin.json"
MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"

HEADING = re.compile(r"^## (\d+)\.(\d+)\.(\d+) — ", re.MULTILINE)


def versions():
    """Return [(major, minor, patch), ...] in file order."""
    text = CHANGELOG.read_text(encoding="utf-8")
    return [tuple(int(n) for n in m.groups()) for m in HEADING.finditer(text)]


class TestChangelog(unittest.TestCase):
    def setUp(self):
        self.versions = versions()

    def test_there_are_entries(self):
        self.assertGreater(len(self.versions), 0, "no version headings found — did the format change?")

    def test_no_duplicate_versions(self):
        seen = set()
        for v in self.versions:
            self.assertNotIn(
                v,
                seen,
                f"{'.'.join(map(str, v))} appears twice — two parallel edits "
                "each prepended it; merge the sections into one",
            )
            seen.add(v)

    def test_versions_strictly_descending(self):
        for above, below in zip(self.versions, self.versions[1:]):
            self.assertGreater(
                above,
                below,
                f"{'.'.join(map(str, below))} sits above "
                f"{'.'.join(map(str, above))} — the file promises newest first",
            )

    def test_top_entry_matches_plugin_version(self):
        plugin = json.loads(PLUGIN.read_text())["version"]
        top = ".".join(map(str, self.versions[0]))
        self.assertEqual(
            top,
            plugin,
            f"top changelog entry is {top} but plugin.json says {plugin} — "
            "bump the version first, then write the entry under it",
        )

    def test_marketplace_agrees_with_plugin(self):
        plugin = json.loads(PLUGIN.read_text())["version"]
        market = json.loads(MARKETPLACE.read_text())["plugins"][0]["version"]
        self.assertEqual(
            market,
            plugin,
            f"marketplace.json says {market}, plugin.json says {plugin} — "
            "installs resolve through the marketplace, so the drift strands "
            "users on the old version",
        )
