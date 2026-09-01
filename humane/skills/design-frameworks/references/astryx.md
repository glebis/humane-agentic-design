# Astryx preset

Astryx is the first full preset. Its installed CLI is the authority because it
is explicitly designed as the shared human/machine interface and exposes a
self-describing typed JSON manifest.

## Detect

Look for `@astryxdesign/core`, `@astryxdesign/cli`,
`@astryxdesign/theme-*`, `astryx.config.{ts,mjs,js}`, or a project
`package.json` script that invokes the local CLI. Detection is read-only.

Do not run bare `npx astryx`: before the scoped CLI is installed that name can
resolve to an unrelated package. Do not download `@astryxdesign/cli` merely to
probe. If the project has a package script, use its detected package manager's
`run <script> -- <args>` form. Otherwise resolve the installed scoped package's
`bin` field and invoke that exact local entrypoint with the project's runtime.
Do not guess a global binary or package-manager forwarding syntax.

## Probe and read

Start with the installed CLI's `manifest --json`. Record its `apiVersion`, CLI
version, command tree, JSON-supported commands, and response discriminators.
Then use the smallest relevant JSON queries:

```text
astryx manifest --json
astryx component --list --json
astryx component <Name> --props --json
astryx component <Name> --source --json
astryx search <query> --json
astryx docs <topic> --json
astryx template --list --json
astryx template <name> --skeleton --json
astryx theme --list --json
```

Command availability and argument order come from the observed manifest. The
examples above are routing hints, not a substitute for it.

Keep Astryx integration contributions beside core resources and preserve their
owner package. A component name without its package/import specifier loses the
information needed for safe implementation.

## Writes

Use the native command only after an exact preview:

- preview a swizzle with `component <Name> --source`; applying it transfers
  source ownership to the project and must not overwrite an existing copy.
  Source output is an input to the preview, not a sufficient preview by itself:
  resolve the destination, dependencies, config changes, and ancillary files;
- preview an upgrade without `--apply`; run `--apply` only after the codemods,
  target version, and affected files are accepted;
- inspect a template's skeleton/content and destination before copying it;
- treat `init`, theme scaffolding/builds, agent-doc generation, and integration
  changes as separate writes with their own target list.

If this CLI version cannot preview an operation, mark `apply` unsupported for
that operation. Do not compensate with `--force`.

## Never override

- `astryx.config.*`, installed theme choice, CSS custom-property overrides, or
  integration manifests;
- source already ejected by swizzle or manually modified;
- user content outside Astryx-managed agent-document markers;
- existing templates, generated theme output, package versions, or lockfiles;
- CLI warnings about version alignment, invalid config, or broken integrations.

## Validate

When the observed manifest confirms `doctor --json` is read-only, it may run
once during discovery as a recorded baseline and again after approved writes as
validation. Run any applicable `validate-integration` command exposed by the
manifest, then the project's own type-check, build, tests, and
Storybook/accessibility checks when they are in scope. A clean `doctor` means
the Astryx integration is healthy; it does not mean the product job or flow has
been validated.

Primary references:

- <https://astryx.atmeta.com/docs/cli>
- <https://github.com/facebook/astryx/blob/main/packages/cli/README.md>
