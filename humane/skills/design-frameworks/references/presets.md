# Presets and capability profiles

A preset teaches the skill how to probe and use one system's native surfaces.
It does not own the Humane workflow. Named presets compose one or more profiles:

| Profile | Machine surface | Typical strengths | Typical limitation |
| --- | --- | --- | --- |
| `native-cli` | Self-describing CLI or public API | Discovery, scaffolding, migrations, native checks | Commands may write broadly; CLI versions drift |
| `registry` | Schema-governed code registry | Exact files, dependencies, namespaced composition | Imported source becomes project-owned |
| `catalog-mcp` | MCP tools/resources or generated manifests | Fresh docs, props, examples, project-local tests | May be read-only or experimental |
| `token-toolchain` | DTCG/config/spec/codegen | Tokens, recipes, themes, cross-platform output | Usually no component or product semantics |

## Shipped presets

| Preset | Profiles | Use when |
| --- | --- | --- |
| `astryx` | `native-cli`, `token-toolchain` | `@astryxdesign/*` packages, an Astryx config, or an existing Astryx CLI script is present |
| `shadcn` | `registry`, `native-cli`, optionally `catalog-mcp` | `components.json`, a shadcn registry, or source-owned shadcn components are present |
| `storybook` | `catalog-mcp` | Storybook describes the project's real components; use as an overlay with another preset when possible |

`storybook` is not a design system by itself. It supplies project-local catalog
and test evidence for whatever system the stories document.

## Selection

1. Use the preset the user named.
2. Otherwise select from observed project files and installed dependencies.
3. If several apply, choose one implementation preset and add Storybook as an
   overlay. Do not merge two systems' write surfaces into one plan.
4. If no preset matches, use the four common contract operations in read-only
   mode over package types, tokens, and project docs. Label it `manual`; do not
   fabricate an `apply` capability.

Profiles are capabilities, not maturity scores. A read-only MCP can be the best
source of documentation while an installed CLI remains the only safe writer.

## Capability negotiation

Every probe records:

- source and upstream version;
- surface kind and locator;
- whether each operation is read or write;
- whether it needs network access;
- whether an exact preview exists;
- native validation commands/tools;
- limitations, experimental status, and unsupported resource kinds.

For MCP, use the negotiated protocol version and listed tools/resources. For a
CLI, prefer a native manifest or documented JSON output. For a registry, verify
its schema before treating any item as installable. For tokens, record the
actual format and preserve extensions instead of coercing everything to DTCG.

