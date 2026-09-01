# Common adapter contract v0.1

The machine-readable schema is `adapter-contract.schema.json`. The contract is
small on purpose: presets normalize discovery and receipts, not the design
system's whole domain model.

## Objects

### AdapterManifest

Records the preset, composed profiles, upstream identity, project root,
authoritative surfaces, operation capabilities, native checks, and known
limitations. It describes what was observed in this project, not everything the
brand may support.

An operation capability declares `supported`, `access`, `network`, `preview`,
and `approval`. Every supported write must have an exact preview and require
approval. If either is unavailable, expose the operation as unsupported.

### FrameworkResource

One component, pattern, template, token set, theme, document, or check. Keep its
native ID, source surface, locator, upstream version, dependencies, constraints,
and unmodified native payload. Normalization adds a common index; it does not
erase native semantics.

### FitPlan

References an immutable implementation brief and names selected resources,
proposed operations, conflicts, deviations, and validation checks. It never
embeds or rewrites Humane source artifacts. `ready` means the operations are
fully previewed; `blocked` means a conflict or missing capability needs a human
decision.

### Finding

Carries one check in either the `framework` or `humane` lane, with status,
evidence locators, and optional remediation. `not-run` and `not-supported` are
first-class results and may not be collapsed into `pass`.

## Operations

The shared vocabulary is deliberately narrow:

| Operation | Meaning |
| --- | --- |
| `probe` | Discover versions, surfaces, capabilities, and limitations |
| `catalog` | List resources within the requested scope |
| `inspect` | Retrieve native details for a resource |
| `plan` | Produce a read-only fit plan |
| `preview` | Resolve exact commands, files, dependencies, and conflicts |
| `apply` | Execute only approved preview receipts; optional |
| `validate` | Run native checks and Humane traceability checks |

## ImplementationBrief reference

The adapter receives references, not ownership:

```json
{
  "briefId": "checkout-v3",
  "jobRef": "jtbd.json#outcomes/O-04",
  "evidenceRefs": ["jtbd.json#evidence/Q12"],
  "conceptRef": ".design/concept-checkout.md",
  "prototypeRef": ".design/prototype-checkout.html",
  "acceptanceCriteria": ["A returning customer can pay without re-entering saved details"]
}
```

If those references do not exist, use `traceability: "not-available"`. Never
invent references to make the plan look complete.

## Required safety invariants

1. A supported write declares `preview: "supported"` and
   `approval: "required"`.
2. The selected resource IDs in a fit plan exist in the same discovery set.
3. Every proposed operation is declared by the manifest.
4. A plan with unresolved blocking conflicts has `status: "blocked"`.
5. Native IDs and provenance survive normalization.
6. Unsupported/unrun checks remain explicit.
7. Humane artifacts appear only as references and are never write targets.
8. Secrets are represented only by variable names, never values.

`scripts/validate_fixtures.py` exercises these invariants against the three
golden fixtures. It is a maintainer conformance check, not a runtime wrapper for
the upstream systems.

