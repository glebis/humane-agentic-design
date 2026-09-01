"""Conformance tests for the Design Frameworks adapter contract."""

from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = SKILL_ROOT / "scripts" / "validate_fixtures.py"
SPEC = importlib.util.spec_from_file_location("validate_fixtures", SCRIPT)
assert SPEC and SPEC.loader
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)


def fixture(name: str):
    path = Path(__file__).resolve().parent / "fixtures" / name
    return json.loads(path.read_text(encoding="utf-8"))


class TestAdapterContract(unittest.TestCase):
    def test_schema_has_all_public_objects(self):
        schema = json.loads(
            (SKILL_ROOT / "references" / "adapter-contract.schema.json").read_text(
                encoding="utf-8"
            )
        )
        validator.validate_schema(schema)

    def test_all_golden_discovery_fixtures_conform(self):
        paths = sorted((Path(__file__).resolve().parent / "fixtures").glob("*.json"))
        self.assertEqual(len(paths), 3)
        for path in paths:
            with self.subTest(fixture=path.name):
                validator.validate_fixture(json.loads(path.read_text(encoding="utf-8")))

    def test_supported_write_without_preview_is_rejected(self):
        data = fixture("astryx.discovery.json")
        apply = next(
            item for item in data["manifest"]["capabilities"] if item["operation"] == "apply"
        )
        apply["supported"] = True
        with self.assertRaisesRegex(validator.ContractError, "needs an exact preview"):
            validator.validate_fixture(data)

    def test_plan_cannot_select_an_undiscovered_resource(self):
        data = fixture("shadcn.discovery.json")
        data["plan"]["selectedResourceIds"].append("shadcn:registry:missing")
        with self.assertRaisesRegex(validator.ContractError, "did not return"):
            validator.validate_fixture(data)

    def test_blocking_conflict_blocks_the_plan(self):
        data = fixture("storybook.discovery.json")
        data["plan"]["conflicts"].append(
            {
                "severity": "blocking",
                "statement": "The renderer does not expose manifests.",
                "decision": "Choose a different catalog source.",
            }
        )
        with self.assertRaisesRegex(validator.ContractError, "must be blocked"):
            validator.validate_fixture(data)

    def test_write_cannot_target_a_humane_artifact(self):
        data = fixture("astryx.discovery.json")
        apply = next(
            item for item in data["manifest"]["capabilities"] if item["operation"] == "apply"
        )
        apply["supported"] = True
        apply["preview"] = "supported"
        data["plan"]["operations"] = [
            {
                "id": "bad-write",
                "operation": "apply",
                "surfaceId": "astryx-cli",
                "kind": "file",
                "target": data["plan"]["implementationBrief"]["prototypeRef"],
                "preview": {
                    "status": "exact",
                    "summary": "Overwrite the prototype",
                    "writes": [data["plan"]["implementationBrief"]["prototypeRef"]],
                    "dependencies": [],
                    "networkSources": [],
                },
                "approval": "required",
            }
        ]
        with self.assertRaisesRegex(validator.ContractError, "immutable Humane artifact"):
            validator.validate_fixture(data)

    def test_passing_finding_requires_evidence(self):
        data = copy.deepcopy(fixture("astryx.discovery.json"))
        data["findings"][0]["evidence"] = []
        with self.assertRaisesRegex(validator.ContractError, "needs evidence"):
            validator.validate_fixture(data)


if __name__ == "__main__":
    unittest.main()

