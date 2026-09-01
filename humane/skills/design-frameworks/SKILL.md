---
name: design-frameworks
description: Fit an already-decided interface to an existing design system or UI toolchain through a capability-probed preset, using the system's own CLI, registry, MCP server, manifests, tokens, and checks instead of inventing parallel conventions. Use after the product job, evidence, concept, and prototype are settled enough to implement, or when bringing an existing build back into framework compliance. Not for choosing the product concept, visual brand, or research method. Triggers on design frameworks, design system adapter, use Astryx, use shadcn, use Storybook, fit this to our component library, existing design system, component registry, framework compliance, agent-ready design system, "implement with our design system".
handoffs:
  - to: review
    when: the implementation has been fitted to the selected framework and is ready for consolidated product review
accepts:
  - from: prototype
---

# Design Frameworks

**Announce at start:** "I'm using the humane:design-frameworks skill to fit this implementation to the project's existing design system without changing the product decision above it."

This skill is an implementation adapter. It translates a settled-enough design
decision into the components, patterns, tokens, themes, templates, and checks an
existing system actually provides. It does not decide what the product should
be.

The Humane method stays above every preset:

`job → evidence → concept → prototype → review → learning`

A preset may report that the system cannot express the accepted concept. It may
not silently alter the job, acceptance criteria, content hierarchy, interaction
model, or prototype to make the available components look sufficient.

## Quick Reference

| Need | Read |
| --- | --- |
| Preset profiles, selection, and fallback behavior | `references/presets.md` |
| Common objects, capability rules, fit-plan and finding shapes | `references/contract.md` |
| Astryx native CLI/API commands and write boundaries | `references/astryx.md` |
| shadcn registry, CLI/MCP, and source-ownership boundaries | `references/shadcn.md` |
| Storybook manifests/MCP as a project-local catalog and test overlay | `references/storybook.md` |

Read only the selected preset reference. Read `contract.md` when producing a
machine-readable manifest, fit plan, operation receipt, or validation result.

## 1. Establish the implementation brief

Before touching the framework, name the immutable inputs you are fitting:

- the job or outcome reference;
- the evidence references supporting it;
- the accepted concept and acceptance criteria;
- the prototype or existing implementation being fitted;
- unresolved decisions and review findings that remain open.

References are enough; do not copy the whole Humane corpus into an adapter
object. If these inputs do not exist, ordinary framework help can still proceed,
but label Humane traceability **Not available**. Never invent research or claim
that a framework-compliant build has validated the product idea.

## 2. Select, then verify, a preset

The user's explicit preset wins. Otherwise inspect the project read-only:
`package.json`, lockfile, framework config, component directories, token files,
Storybook config, MCP configuration, and installed local binaries. Use the
selection table in `presets.md`.

A preset name is a bootstrap hint, not proof. Probe the native surface and
record what this version and project actually expose. If the probe contradicts
the preset reference, the probe wins and the difference is a limitation. Never
guess a capability from the system's brand or from a remembered release.

Prefer authoritative surfaces in this order when several expose the same fact:

1. a project-local machine manifest or documented programmatic API;
2. typed JSON from the system's installed CLI;
3. a schema-governed registry or generated project manifest;
4. negotiated MCP tools and resources;
5. installed package types and authored project documentation;
6. remote prose documentation, as a cited fallback only.

Do not download a CLI, start a server, connect a remote registry, or install an
MCP server merely to probe. Those are separate network or installation actions
and need the user's approval.

## 3. Discover before composing

Build a small catalog for the requested scope, not a dump of the whole system.
Inspect the native IDs, import paths, props, examples, variants, dependencies,
token requirements, theme behavior, and ownership model of likely resources.

Keep provenance attached. A normalized `Button` without its package, registry,
version, or source locator is not safe evidence. Preserve native fields the
adapter does not understand; for DTCG tokens, never infer type or purpose from a
group name and never discard unknown extensions.

## 4. Produce a fit plan before a patch

Map the implementation brief to native resources and return:

1. the selected components, patterns, templates, themes, and tokens;
2. how each choice serves an acceptance criterion or prototype behavior;
3. proposed commands and file operations, with exact targets;
4. conflicts and deviations, including capabilities the framework lacks;
5. the native checks that will run after implementation;
6. anything that remains **Not verified** or **Not supported**.

Planning is read-only. If a native preview or diff exists, use it. Otherwise the
operation is not safely applicable through this skill until an exact preview can
be produced another way.

## 5. Apply only an approved preview

Show the preview and ask before the first write. Approval covers only the shown
operations. Re-plan if a command resolves different files, dependencies,
environment variables, configuration, or migrations at execution time.

Always use the framework's supported CLI or public API for framework-owned
changes. Ordinary application source that composes public framework components
may use the project's normal editing path, but only after an exact file diff is
part of the approved preview. Do not reproduce the framework's installer,
registry resolver, codemod, or theme compiler in this skill. Capture the native
receipt or the resulting diff.

These operations are never implicit: dependency installation, network fetches,
`--force`/overwrite, eject/swizzle, codemods or migrations, theme replacement,
agent-instruction edits, lockfile changes, generated-file writes, and deletion.

## 6. Validate in two lanes

Framework compliance and Humane validity are different claims.

**Framework lane:** run only checks the discovered system actually provides —
schema validation, doctor/integration checks, type generation and type-checking,
builds, story interaction tests, accessibility checks, token/reference checks,
or project tests. Record the command/tool and evidence.

**Humane lane:** trace the result back to the implementation brief. Confirm that
the accepted job, concept, hierarchy, interactions, and prototype behavior did
not drift during adaptation. Product review and learning still belong to their
own Humane owners; this lane checks traceability, not whether the product idea
was good.

Use `pass`, `fail`, `warn`, `not-run`, or `not-supported`. Unsupported and
unrun checks are never passes. A clean build does not prove usability, and a
successful review does not prove framework compliance.

## Never override

- Humane corpus, evidence, concept, prototype notes, review findings, or
  learning artifacts;
- accepted product intent, information hierarchy, interaction model, or copy;
- project tokens, themes, framework config, agent instructions, or lockfiles;
- source-owned, ejected, swizzled, or manually modified components;
- generated files or unrelated source;
- secrets, credentials, registry tokens, or environment values;
- unknown registry metadata or DTCG extensions;
- an accessibility requirement to make a preset fit.

When the framework and the implementation brief conflict, stop at the fit plan
and name the decision the user must make. The adapter does not get a tie-breaker.

## Output

For read-only discovery, return **Preset**, **Observed capabilities**,
**Resources inspected**, **Limitations**, and **Next safe action**.

For implementation, return the **Fit plan**, the approved **Operation
receipts**, and **Validation** split into Framework and Humane lanes. State every
write and every check not run. Then offer the declared handoff to
`humane:review`; do not run it automatically.

Use these fit-plan headings so a human can approve the boundary without reading
the contract JSON: **Brief refs**, **Preset and observed version**, **Selected
native resources**, **Criterion mapping**, **Exact proposed operations**,
**Conflicts and deviations**, **Checks after apply**, **Not verified**, and
**Approval needed**.
