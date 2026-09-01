# shadcn preset

shadcn is a registry/source-owned preset. The project receives source files;
after installation those files belong to the project, not to an opaque runtime
package.

## Detect and probe

Look for `components.json`, shadcn dependencies, registry namespaces, or
components with the project's configured aliases. Validate registry roots and
items against the published JSON Schemas before using their contents.

Use the installed CLI's read-only discovery commands and MCP when already
configured. Prefer documented imports under `shadcn/registry` and
`shadcn/schema` for programmatic work; the CLI's internal command modules are
not public API.

Record each item's qualified registry name, type, files, registry dependencies,
package dependencies, CSS variables, environment-variable names, and docs.
Registry content is external input even when its JSON validates.

## Plan and preview

Use native `info`, `search`, `docs`, `view`, `diff`, or `add --dry-run`
capabilities when the installed version exposes them. Resolve the full
dependency tree before approval. The preview must show:

- every target file and whether it already exists;
- package and registry dependencies;
- CSS variables, Tailwind/config changes, and environment-variable names;
- which files become project-owned source;
- network sources and authentication requirements.

## Writes

Apply with overwrite disabled. Never use `--overwrite` or a force equivalent
without a second, target-specific approval after showing the diff. Do not place
registry files outside configured aliases, execute code carried by a registry,
or expose credential values. If the installed version lacks a trustworthy dry
run/diff, this preset is read-only.

Schema validity proves shape, not safety, accessibility, or fitness to the job.
Run the project's type-check, build, tests, and any Storybook checks after a
write.

Primary references:

- <https://ui.shadcn.com/docs/registry/registry-json>
- <https://ui.shadcn.com/docs/registry/api-reference>
- <https://ui.shadcn.com/docs/mcp>

