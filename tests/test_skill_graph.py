"""The handoff graph between skills, declared in frontmatter and checked here.

Claude Code's loader ignores these keys — nothing auto-runs the next skill.
Their value is that the graph becomes data instead of prose scattered across
fourteen files, so a handoff naming a skill that does not exist, or one the
receiving skill has never heard of, fails a test instead of being discovered by
a user mid-cycle.

The contract, both keys optional:

    handoffs:                       # what this skill hands to, and when
      - to: design-tokens
        when: a direction wins and needs to become a token set
    accepts:                        # who may hand to this skill
      - from: brandkit

Reciprocity is the point. `brandkit` claiming a handoff into `design-tokens`
means nothing unless `design-tokens` acknowledges it — an unacknowledged edge is
one skill reaching across an ownership boundary the other never opened. Cycles
are legal: humane is a cycle, and `before-after` → `jtbd` closing it is correct.

Run:  python3 -m pytest tests/ -v
"""

import unittest

from test_skill_frontmatter import parse_frontmatter, skill_files


def graph():
    """Return {skill_name: frontmatter} for every skill in the plugin."""
    return {path.parent.name: parse_frontmatter(path) for path in skill_files()}


def edges(data):
    """Yield (to, when) for each declared handoff, validating the entry shape."""
    for entry in data.get("handoffs") or []:
        if not isinstance(entry, dict):
            raise AssertionError(f"handoff entry is {entry!r}, expected a mapping with `to:`")
        yield entry.get("to"), entry.get("when")


def sources(data):
    """Yield each `from:` this skill acknowledges, validating the entry shape."""
    for entry in data.get("accepts") or []:
        if not isinstance(entry, dict):
            raise AssertionError(f"accepts entry is {entry!r}, expected a mapping with `from:`")
        yield entry.get("from")


class TestSkillGraph(unittest.TestCase):
    def setUp(self):
        self.skills = graph()

    def test_there_are_skills_to_check(self):
        self.assertGreater(len(self.skills), 0, "no skills found")

    def test_some_skill_declares_a_handoff(self):
        # Without this, every test below passes vacuously the day the key is
        # renamed or the frontmatter stops parsing the way we expect.
        declared = [name for name, data in self.skills.items() if data.get("handoffs")]
        self.assertGreater(len(declared), 0, "no skill declares `handoffs:` — is the key misspelled?")

    def test_handoff_entries_are_well_formed(self):
        for name, data in self.skills.items():
            with self.subTest(skill=name):
                for target, when in edges(data):
                    self.assertTrue(target, f"{name}: a handoff entry has no `to:`")
                    self.assertTrue(
                        when,
                        f"{name}: handoff to `{target}` has no `when:` — a handoff "
                        "without its condition is not a rule, it is a suggestion",
                    )
                for source in sources(data):
                    self.assertTrue(source, f"{name}: an accepts entry has no `from:`")

    def test_handoff_targets_exist(self):
        for name, data in self.skills.items():
            with self.subTest(skill=name):
                for target, _ in edges(data):
                    self.assertIn(
                        target,
                        self.skills,
                        f"{name}: hands off to `{target}`, which is not a skill in this plugin",
                    )

    def test_accepts_sources_exist(self):
        for name, data in self.skills.items():
            with self.subTest(skill=name):
                for source in sources(data):
                    self.assertIn(
                        source,
                        self.skills,
                        f"{name}: accepts from `{source}`, which is not a skill in this plugin",
                    )

    def test_no_skill_hands_off_to_itself(self):
        for name, data in self.skills.items():
            with self.subTest(skill=name):
                targets = [t for t, _ in edges(data)]
                self.assertNotIn(name, targets, f"{name}: hands off to itself")

    def test_every_handoff_is_acknowledged_by_its_receiver(self):
        for name, data in self.skills.items():
            for target, _ in edges(data):
                if target not in self.skills:
                    continue  # reported by test_handoff_targets_exist
                with self.subTest(edge=f"{name} -> {target}"):
                    self.assertIn(
                        name,
                        list(sources(self.skills[target])),
                        f"`{name}` hands off to `{target}`, but `{target}` does not "
                        f"list `- from: {name}` under `accepts:`. Either add it there, "
                        f"or drop the handoff from `{name}` — an unacknowledged edge "
                        "is one skill reaching across a boundary the other never opened.",
                    )

    def test_every_accepted_source_actually_hands_off(self):
        # The mirror image: an `accepts:` entry nobody sends to is dead metadata
        # that reads as a live route.
        for name, data in self.skills.items():
            for source in sources(data):
                if source not in self.skills:
                    continue  # reported by test_accepts_sources_exist
                with self.subTest(edge=f"{source} -> {name}"):
                    self.assertIn(
                        name,
                        [t for t, _ in edges(self.skills[source])],
                        f"`{name}` accepts from `{source}`, but `{source}` declares no "
                        f"handoff to `{name}`. Remove the stale `accepts:` entry.",
                    )

    def test_orchestrated_skills_exist_and_are_not_confused_with_handoffs(self):
        # `orchestrates:` is deliberately a different key from `handoffs:`.
        # `review` calls its domain skills and consolidates their findings; it
        # does not hand work across an ownership boundary, so no reciprocity is
        # owed and the receiving skills stay unaware of it. Collapsing the two
        # would flatten the distinction the whole rule-ownership table rests on.
        for name, data in self.skills.items():
            with self.subTest(skill=name):
                orchestrated = data.get("orchestrates") or []
                for target in orchestrated:
                    self.assertIn(
                        target,
                        self.skills,
                        f"{name}: orchestrates `{target}`, which is not a skill in this plugin",
                    )
                self.assertNotIn(name, orchestrated, f"{name}: orchestrates itself")
                self.assertEqual(
                    len(orchestrated),
                    len(set(orchestrated)),
                    f"{name}: orchestrates the same skill twice",
                )
                overlap = set(orchestrated) & {t for t, _ in edges(data)}
                self.assertEqual(
                    overlap,
                    set(),
                    f"{name}: {sorted(overlap)} appears under both `orchestrates:` and "
                    "`handoffs:` — a skill is either called by this one or handed to, not both",
                )

    def test_handoffs_are_not_duplicated(self):
        for name, data in self.skills.items():
            with self.subTest(skill=name):
                targets = [t for t, _ in edges(data)]
                self.assertEqual(
                    len(targets), len(set(targets)), f"{name}: declares the same handoff twice"
                )
                froms = list(sources(data))
                self.assertEqual(
                    len(froms), len(set(froms)), f"{name}: accepts the same source twice"
                )


if __name__ == "__main__":
    unittest.main()
