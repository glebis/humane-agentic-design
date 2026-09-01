#!/usr/bin/env python3
"""Validate Design Frameworks golden fixtures with the Python standard library.

This checks the cross-object safety invariants that JSON Schema alone cannot
express. It never invokes an upstream framework or writes to the project.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable

CONTRACT_VERSION = "0.1"
OPERATIONS = {"probe", "catalog", "inspect", "plan", "preview", "apply", "validate"}
PROFILES = {"native-cli", "registry", "catalog-mcp", "token-toolchain"}
FINDING_STATUSES = {"pass", "fail", "warn", "not-run", "not-supported"}
REQUIRED_DEFS = {
    "AdapterManifest",
    "FrameworkResource",
    "FitPlan",
    "Finding",
}


class ContractError(ValueError):
    """A fixture violates the Design Frameworks contract."""


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(f"{label} must be an object")
    return value


def _list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise ContractError(f"{label} must be an array")
    return value


def _required(obj: dict[str, Any], keys: Iterable[str], label: str) -> None:
    missing = sorted(set(keys) - obj.keys())
    if missing:
        raise ContractError(f"{label} is missing: {', '.join(missing)}")


def _unique_ids(items: list[Any], label: str) -> set[str]:
    ids: list[str] = []
    for index, item in enumerate(items):
        value = _mapping(item, f"{label}[{index}]").get("id")
        if not isinstance(value, str) or not value:
            raise ContractError(f"{label}[{index}].id must be a non-empty string")
        ids.append(value)
    if len(ids) != len(set(ids)):
        raise ContractError(f"{label} contains duplicate ids")
    return set(ids)


def validate_schema(schema: dict[str, Any]) -> None:
    if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        raise ContractError("schema must use JSON Schema draft 2020-12")
    definitions = _mapping(schema.get("$defs"), "schema.$defs")
    missing = sorted(REQUIRED_DEFS - definitions.keys())
    if missing:
        raise ContractError(f"schema is missing definitions: {', '.join(missing)}")


def validate_fixture(data: dict[str, Any]) -> None:
    _required(
        data,
        {"fixtureVersion", "source", "manifest", "resources", "plan", "findings"},
        "fixture",
    )
    if data["fixtureVersion"] != CONTRACT_VERSION:
        raise ContractError(f"fixtureVersion must be {CONTRACT_VERSION}")

    source = _mapping(data["source"], "source")
    _required(source, {"capturedAt", "evidence"}, "source")
    if not _list(source["evidence"], "source.evidence"):
        raise ContractError("source.evidence must contain at least one locator")

    manifest = _mapping(data["manifest"], "manifest")
    _required(
        manifest,
        {
            "contractVersion",
            "preset",
            "profiles",
            "upstream",
            "projectRoot",
            "surfaces",
            "capabilities",
            "checks",
            "limitations",
        },
        "manifest",
    )
    if manifest["contractVersion"] != CONTRACT_VERSION:
        raise ContractError(f"manifest.contractVersion must be {CONTRACT_VERSION}")
    profiles = set(_list(manifest["profiles"], "manifest.profiles"))
    if not profiles or not profiles <= PROFILES:
        raise ContractError("manifest.profiles contains an unknown or empty profile set")

    surfaces = _list(manifest["surfaces"], "manifest.surfaces")
    surface_ids = _unique_ids(surfaces, "manifest.surfaces")
    if not surface_ids:
        raise ContractError("manifest must expose at least one surface")

    capabilities = _list(manifest["capabilities"], "manifest.capabilities")
    by_operation: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(capabilities):
        capability = _mapping(raw, f"manifest.capabilities[{index}]")
        _required(
            capability,
            {
                "operation",
                "supported",
                "access",
                "network",
                "preview",
                "approval",
                "surfaceIds",
            },
            f"manifest.capabilities[{index}]",
        )
        operation = capability["operation"]
        if operation not in OPERATIONS:
            raise ContractError(f"unknown operation: {operation!r}")
        if operation in by_operation:
            raise ContractError(f"duplicate capability for operation {operation!r}")
        by_operation[operation] = capability
        declared_surfaces = set(_list(capability["surfaceIds"], f"{operation}.surfaceIds"))
        if not declared_surfaces or not declared_surfaces <= surface_ids:
            raise ContractError(f"{operation} refers to an unknown surface")
        if capability["access"] == "write" and capability["supported"]:
            if capability["preview"] != "supported":
                raise ContractError(f"supported write {operation!r} needs an exact preview")
            if capability["approval"] != "required":
                raise ContractError(f"supported write {operation!r} must require approval")
    if set(by_operation) != OPERATIONS:
        missing = sorted(OPERATIONS - by_operation.keys())
        raise ContractError(f"manifest lacks operation capabilities: {', '.join(missing)}")

    checks = _list(manifest["checks"], "manifest.checks")
    check_ids = _unique_ids(checks, "manifest.checks")
    for check in checks:
        if check.get("surfaceId") not in surface_ids:
            raise ContractError(f"check {check.get('id')!r} refers to an unknown surface")

    resources = _list(data["resources"], "resources")
    resource_ids = _unique_ids(resources, "resources")
    for resource in resources:
        _required(
            resource,
            {
                "kind",
                "name",
                "nativeId",
                "surfaceId",
                "sourceLocator",
                "upstreamVersion",
                "dependencies",
                "constraints",
                "nativePayload",
                "provenance",
            },
            f"resource {resource['id']!r}",
        )
        if resource["surfaceId"] not in surface_ids:
            raise ContractError(f"resource {resource['id']!r} refers to an unknown surface")
        provenance = _mapping(resource["provenance"], f"resource {resource['id']}.provenance")
        _required(provenance, {"authority", "evidence"}, "resource provenance")

    plan = _mapping(data["plan"], "plan")
    _required(
        plan,
        {
            "contractVersion",
            "id",
            "preset",
            "status",
            "traceability",
            "implementationBrief",
            "selectedResourceIds",
            "operations",
            "conflicts",
            "deviations",
            "validationCheckIds",
        },
        "plan",
    )
    if plan["contractVersion"] != CONTRACT_VERSION:
        raise ContractError(f"plan.contractVersion must be {CONTRACT_VERSION}")
    if plan["preset"] != manifest["preset"]:
        raise ContractError("plan.preset must match manifest.preset")
    selected = set(_list(plan["selectedResourceIds"], "plan.selectedResourceIds"))
    if not selected <= resource_ids:
        raise ContractError("plan selects a resource that discovery did not return")
    validation_ids = set(_list(plan["validationCheckIds"], "plan.validationCheckIds"))
    if not validation_ids <= check_ids:
        raise ContractError("plan names a native check that the manifest did not return")

    brief = _mapping(plan["implementationBrief"], "plan.implementationBrief")
    _required(
        brief,
        {"briefId", "jobRef", "evidenceRefs", "conceptRef", "prototypeRef", "acceptanceCriteria"},
        "plan.implementationBrief",
    )
    if plan["traceability"] == "available":
        if not brief["jobRef"] or not brief["prototypeRef"]:
            raise ContractError("available traceability needs jobRef and prototypeRef")
        if not _list(brief["evidenceRefs"], "evidenceRefs"):
            raise ContractError("available traceability needs evidenceRefs")
        if not _list(brief["acceptanceCriteria"], "acceptanceCriteria"):
            raise ContractError("available traceability needs acceptanceCriteria")

    operations = _list(plan["operations"], "plan.operations")
    for index, raw in enumerate(operations):
        operation = _mapping(raw, f"plan.operations[{index}]")
        _required(operation, {"operation", "surfaceId", "target", "preview", "approval"}, "planned operation")
        declared = by_operation.get(operation["operation"])
        if not declared or not declared["supported"]:
            raise ContractError(f"plan uses unsupported operation {operation['operation']!r}")
        if operation["surfaceId"] not in surface_ids:
            raise ContractError("planned operation refers to an unknown surface")
        preview = _mapping(operation["preview"], "planned operation preview")
        if preview.get("status") != "exact" or operation["approval"] != "required":
            raise ContractError("every planned write needs an exact preview and required approval")
        protected = {
            brief.get("jobRef"),
            brief.get("conceptRef"),
            brief.get("prototypeRef"),
            *_list(brief["evidenceRefs"], "evidenceRefs"),
        }
        if operation["target"] in protected:
            raise ContractError("a planned operation targets an immutable Humane artifact")

    conflicts = _list(plan["conflicts"], "plan.conflicts")
    has_blocker = any(_mapping(item, "conflict").get("severity") == "blocking" for item in conflicts)
    if has_blocker and plan["status"] != "blocked":
        raise ContractError("a plan with a blocking conflict must be blocked")

    findings = _list(data["findings"], "findings")
    _unique_ids(findings, "findings")
    for finding in findings:
        _required(finding, {"lane", "checkId", "status", "severity", "summary", "evidence"}, "finding")
        if finding["status"] not in FINDING_STATUSES:
            raise ContractError(f"unknown finding status: {finding['status']!r}")
        evidence = _list(finding["evidence"], "finding.evidence")
        if finding["status"] == "pass" and not evidence:
            raise ContractError("a passing finding needs evidence")


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"{path}: {exc}") from exc
    return _mapping(value, str(path))


def default_paths() -> tuple[Path, list[Path]]:
    skill_root = Path(__file__).resolve().parent.parent
    schema = skill_root / "references" / "adapter-contract.schema.json"
    fixtures = sorted((skill_root / "tests" / "fixtures").glob("*.json"))
    return schema, fixtures


def main(argv: list[str] | None = None) -> int:
    default_schema, default_fixtures = default_paths()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schema", type=Path, default=default_schema)
    parser.add_argument("fixtures", type=Path, nargs="*", default=default_fixtures)
    args = parser.parse_args(argv)

    errors: list[str] = []
    try:
        validate_schema(load_json(args.schema))
    except ContractError as exc:
        errors.append(str(exc))

    if not args.fixtures:
        errors.append("no fixture files found")
    for path in args.fixtures:
        try:
            validate_fixture(load_json(path))
            print(f"OK {path}")
        except ContractError as exc:
            errors.append(f"{path}: {exc}")

    if errors:
        for error in errors:
            print(f"ERROR {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

