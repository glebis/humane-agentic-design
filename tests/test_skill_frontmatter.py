"""Frontmatter contract for every skill in the plugin.

The description is the discovery surface: it is the only part of a skill in
context before the skill fires, and it is parsed as a YAML scalar. A bare
`: ` inside an unquoted one takes the whole block down — the skill then has no
metadata at all, and nothing else in this repo would notice.

Run:  python3 -m pytest tests/ -v
"""

import re
import unittest
from pathlib import Path

SKILLS_DIR = Path(__file__).resolve().parent.parent / "humane" / "skills"

# Not a style budget — a ceiling. Descriptions sit in context permanently, so a
# runaway one costs every session that never invokes the skill.
MAX_DESCRIPTION_CHARS = 1200


def skill_files():
    return sorted(SKILLS_DIR.glob("*/SKILL.md"))


def parse_frontmatter(path):
    """Return the frontmatter dict, or raise with the file named."""
    import yaml

    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        raise AssertionError(f"{path}: no `---` frontmatter block at the top")
    try:
        data = yaml.safe_load(match.group(1))
    except yaml.YAMLError as exc:
        first_line = str(exc).splitlines()[0]
        raise AssertionError(
            f"{path}: frontmatter is not valid YAML — {first_line}. "
            "A colon followed by a space inside an unquoted description is the "
            "usual cause; reword it or quote the whole scalar."
        ) from exc
    if not isinstance(data, dict):
        raise AssertionError(f"{path}: frontmatter is not a mapping")
    return data


class TestSkillFrontmatter(unittest.TestCase):
    def test_there_are_skills_to_check(self):
        # A glob that silently matches nothing would make every test below pass.
        self.assertGreater(len(skill_files()), 0, f"no SKILL.md under {SKILLS_DIR}")

    def test_frontmatter_parses_and_carries_both_required_fields(self):
        for path in skill_files():
            with self.subTest(skill=path.parent.name):
                data = parse_frontmatter(path)
                self.assertTrue(data.get("name"), f"{path}: missing `name`")
                self.assertTrue(
                    data.get("description"), f"{path}: missing `description`"
                )

    def test_name_matches_directory(self):
        for path in skill_files():
            with self.subTest(skill=path.parent.name):
                data = parse_frontmatter(path)
                self.assertEqual(
                    data["name"],
                    path.parent.name,
                    f"{path}: frontmatter `name` must match the directory it lives in",
                )

    def test_description_names_its_triggers(self):
        # The authoring convention in CLAUDE.md: one sentence on what it does,
        # then "Use when…", then a `Triggers on …` keyword list.
        for path in skill_files():
            with self.subTest(skill=path.parent.name):
                description = parse_frontmatter(path)["description"]
                self.assertIn(
                    "Triggers on",
                    description,
                    f"{path}: description has no `Triggers on …` keyword list",
                )

    def test_description_stays_under_the_ceiling(self):
        for path in skill_files():
            with self.subTest(skill=path.parent.name):
                description = parse_frontmatter(path)["description"]
                self.assertLessEqual(
                    len(description),
                    MAX_DESCRIPTION_CHARS,
                    f"{path}: description is {len(description)} chars, over the "
                    f"{MAX_DESCRIPTION_CHARS} ceiling",
                )

    def test_no_stale_slash_command_names_for_humane_skills(self):
        # These ship as `humane:<skill>`, never as `/<skill>`. External skills
        # the user does have as slash commands (`/tufte-report`, `/nano-banana`)
        # are deliberately not checked.
        own = {p.parent.name for p in skill_files()}
        for path in sorted(SKILLS_DIR.glob("*/**/*.md")):
            stale = {m for m in re.findall(r"`/([a-z][a-z0-9-]*)`", path.read_text(encoding="utf-8")) if m in own}
            with self.subTest(file=str(path.relative_to(SKILLS_DIR))):
                self.assertEqual(
                    stale,
                    set(),
                    f"{path}: refers to {sorted('/' + s for s in stale)}; "
                    "humane skills are invoked as `humane:<skill>`",
                )


if __name__ == "__main__":
    unittest.main()
