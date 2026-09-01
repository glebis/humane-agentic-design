# Storybook overlay

Storybook is a project-local catalog and validation overlay. It documents the
components the project actually has; it is not itself the design system and
does not own component source.

## Detect and probe

Look for `.storybook/`, CSF/MDX stories, generated component/docs manifests, or
an already-configured Storybook MCP endpoint. Do not install the MCP addon or
start the development server merely to probe.

When MCP is already available, negotiate its capabilities and list its current
tools. Useful read surfaces include component documentation, story-specific
documentation, all-doc indexes, and story-generation instructions. Use the
generated JSON manifests directly when MCP is absent but manifests exist.

Record the Storybook version, renderer, manifest format, prop-extraction mode,
and whether testing/accessibility tools are present. Current AI manifests and
MCP support may be preview or renderer-limited; expose that as a limitation
rather than assuming parity.

## Use as evidence

- catalog components, props, stories, examples, and authored JSDoc/MDX;
- prefer project stories over remote generic examples when they disagree;
- use composed Storybooks only when the MCP/manifests expose their provenance;
- run story interaction or accessibility tests only when the project's existing
  setup exposes them.

Storybook has no `apply` operation in this preset. Source changes belong to the
primary implementation preset or to ordinary project edits after an approved
fit plan. A generated story is a proposed project file and needs the same
preview and approval as any other write.

Primary references:

- <https://storybook.js.org/docs/ai/manifests>
- <https://storybook.js.org/docs/ai/mcp/overview>

