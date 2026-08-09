---
name: design-tokens
description: Sets up, validates, resolves, and exports design tokens per the DTCG (Design Tokens Community Group) Format Module 2025.10 standard, and owns all colour contrast measurement and remediation — every text/background pair on both APCA Lc and the WCAG ratio via `tokens contrast`, with a fix that moves OKLCH lightness only. Use when the user wants to define a design token set globally or per project, compile tokens to CSS variables, layer a project's tokens over a global brand base, check whether a palette is readable, or produce an on-brand context file for other generation skills. Triggers on "set up design tokens", "create a token set", "compile tokens to CSS", "design system variables", "brand tokens", "check contrast", "WCAG", "APCA", "is this text readable", "contrast audit", "проверь контраст".
handoffs:
  - to: brand-illustrate
    when: a token set exists and assets must be produced under it
accepts:
  - from: brandkit
  - from: layout-rules
  - from: type-specimen
  - from: walkthrough
  - from: prototype
---

# Design Tokens

**Announce at start:** "I'm using the humane:design-tokens skill to set up, resolve, and export this token set."

Manage [DTCG 2025.10](https://www.designtokens.org/tr/drafts/format/) design tokens
with a dependency-free Python core. v1 covers the deterministic spine: scaffold,
validate, merge (global base + project override), resolve aliases, and export CSS.

## Standard vs convention

- **Standard (DTCG):** `*.tokens.json`, `$value`/`$type`, whole-value `{alias}` references.
- **Skill convention (NOT DTCG):** global-base / project-override layering via `merge`,
  and theme-as-override-file. These are labelled in code; do not present them as standard.

## v1 scope

Supported `$type`: `color` (string values), `dimension`, `duration`, `fontFamily`,
`fontWeight`, `number`, `typography`, `shadow`. Outputs: CSS custom properties, a
Google-Labs **DESIGN.md** (alpha), a standalone HTML preview, and **generation
prompts** (gpt-image-2 / nano-banana CLI lines + a `/tufte-report` theme) via the
prompt door. CSS **import**
covers color/dimension/duration/fontFamily/number; composite values (box-shadow,
gradients, multi-part typography) are skipped and reported. Not in v1: JSON Pointer
`$ref`, `$root`, structured color objects, name-restriction enforcement, Style
Dictionary, Figma/Pencil importers, share bundles, `skillify` (see the phased spec).

## Commands

Run via `scripts/tokens <command>` (or `PYTHONPATH=scripts python3 -m dtokens.cli`):

| Command | What it does |
| --- | --- |
| `setup-edit <dest> [--from SRC]` | Scaffold a token file at `<dest>` and validate it (refuses to overwrite). With `--from`, deterministically clone an existing set's structure + content to edit (byte-stable for a given source) instead of the blank template. Ships `templates/base.tokens.json` (minimal), `templates/monaspace.tokens.json` (a real set extracted from a live site — see *Extracting from a site*), and `templates/gsap.tokens.json` (a motion-first set: `duration` tokens under `motion.*` render as a body Motion table, and its `$extensions` brand block carries GSAP animation recipes for `--rich`). Also compiles a **DESIGN.md** next to the token file (provenance-stamped; won't clobber a hand-edited one — see *DESIGN.md output*). If a `brand-block.draft.json` (a `humane:brandkit` handoff for a set that didn't exist yet) sits in the destination directory, its `$extensions` brand block is imported into the scaffolded set. |
| `import <css> [-o OUT]` | Import a CSS file's `:root` custom properties into DTCG, preserving variable names. Skips composites (shadow/gradient) and reports them on stderr. |
| `validate <file> [--strict]` | Print `OK` or a list of errors; exit 1 if invalid. Also prints non-fatal `warning:` lines to stderr when the brand-style block / its `imageryStyle` is missing, or when a dimension/duration value is legitimate CSS but not DTCG-shapeable (`clamp()`/`calc()`/`var()` and bare unit strings — kept verbatim in outputs). Advisory only, never changes the exit code — except under `--strict`, which promotes the non-DTCG dimension advisories to errors (exit 1) so they can gate CI. |
| `contrast <file> [--standard apca\|wcag\|both] [--level auto\|body\|non-body\|graphic] [--json] [--no-fail] [-o OUT]` | Measure **APCA Lc** and **WCAG 2.x ratio** for every foreground/background pair in the set, and propose a fix that moves OKLCH lightness while preserving chroma and hue. Exits 1 on any failure (`--no-fail` to report without gating). See *Contrast* below. |
| `merge <base> <override> [-o OUT]` | Layer project override on global base. |
| `resolve <file> [-o OUT]` | Flatten aliases to concrete values (JSON map). |
| `export-css <file> [--selector SEL] [-o OUT]` | Emit CSS custom properties. |
| `design-md <file> [--name N] [--description D] [--rich] [--yes] [-o OUT]` | Emit a Google-Labs [DESIGN.md](https://github.com/google-labs-code/design.md) (alpha) — YAML token frontmatter + a table-based body (colors carry their `$description` as a Role column). It is provenance-stamped (generated, do-not-edit) and, when the `$extensions` brand block is present, renders a default `## Brand direction` section (mood / imageryStyle / subjects / avoid). `--rich` (also on `use`) appends style-guide sections from the brand `$extensions` block — components, do's/don'ts, surfaces, imagery, layout, similar brands, plus a Quick Start CSS block. **Non-standard**: `--rich` extends the Labs alpha body, so the CLI shows a confirmation (auto-accepted with `--yes` or when non-interactive; the note still prints to stderr). |
| `preview <file> [--name N] [--full] [--description D] [-o OUT]` | Emit a standalone HTML swatch page (colors, type specimens, spacing, rounded, shadow). With `--full`, emit a **landing-page mockup** instead — the brand applied in situ (hero, prose, accent band, footer), driven entirely by the role/type/space tokens via `:root` vars. Type specimens load their families via a deterministic Google Fonts `@import` so brand faces render (degrades to a generic fallback offline / for non-Google fonts). |
| `prompt <file> [--target gpt-image-2\|nano-banana\|tufte\|all] [--preset P ...] [--platform P] [--subject S] [--name N] [-o OUT]` | The **prompt door**: turn resolved tokens into ready-to-paste generation prompts. Image targets emit per-preset CLI invocations with the brand's hex/fonts/shape baked into the subject; `tufte` emits a CSS `:root` theme mapping brand roles onto `/tufte-report`'s variables. |
| `use <file> [--name N] [--description D] [--out-dir DIR] [--serve/--no-serve] [--port N] [--no-open]` | Validate + resolve, then write `tokens.css`, `DESIGN.md`, `preview.html`, `preview-full.html` (landing-page mockup), `image-prompts.md`, and `tufte-theme.css`. **Serves the output over HTTP and opens it by default when interactive** (see below). |
| `generate <file> [--target gpt-image-2\|nano-banana\|all] [--subject S] [--refs DIR] [--out-dir D] [--final] [--dry-run]` | **Actually generate** on-brand images: composes the winning art-direction-prose prompt (fidelity-tested) from tokens + `$extensions` brand block and shells out to the gpt-image-2 / nano-banana skill scripts (cheap draft by default; `--final` = high/pro). With `--refs`, reads the `refs.json` manifest: each annotated image becomes a `--reference` flag plus a role-annotated prompt clause ("from reference image 1 take: palette, mood — …"). |
| `annotate <dir> [--port N] [--no-open]` | Serve a **reference-image annotator** for a directory of images: per-image role chips (style, palette, composition, subject, texture, typography, mood) + a free-text note, with voice dictation via Groq Whisper when `GROQ_API_KEY` is set (text-only otherwise). Save writes a `refs.json` manifest next to the images (SKILL CONVENTION) — the source of truth for "what to take from each reference" in multi-reference generation. |
| `serve <path> [--port N] [--no-open]` | Serve a generated `.html` (or an output dir) over `http://127.0.0.1` and open it. Use this to view previews — `file://` URLs are unique origins and break web-font loads, `fetch`, and extensions. |

## Contrast

DTCG stores colors, not relationships — nothing in the standard says which token
is text and which is the surface behind it. `contrast` adds that layer as a
SKILL CONVENTION and makes it executable, so a token set cannot compile with an
unreadable role pair.

Two scales, both reported:

| Scale | Body text | Non-body (links, icons, badges, large text) |
| --- | --- | --- |
| **APCA Lc** (W3C draft, algorithm 0.1.9) | \|Lc\| ≥ 75 | \|Lc\| ≥ 60 |
| **WCAG 2.x ratio** | 4.5:1 | 3:1 |

`--standard both` (the default) requires clearing both. They genuinely disagree:
`#747474` on white is 4.67:1 (passes WCAG AA) but Lc 72.5 (fails APCA). APCA is
the better predictor of perceived readability; WCAG is the one auditors ask for.
Reporting both, and letting the caller pick which gates, is the honest split.

**Fixes move lightness only.** The suggestion walks OKLCH `L` away from the
background until the pair clears, keeping `C` and `H` — so the brand hue
survives the fix. When no lightness on that axis clears the bar, no fix is
offered: chroma or the background has to move, and that is a design decision,
not a mechanical one.

**Unparseable colors are reported, never failed.** `var(--x)`, `currentColor`, a
gradient, or any value carrying alpha (contrast depends on what is behind it) is
listed as *not measured*. A verification gap is not a finding.

**Palette ramp steps are skipped.** A trailing numeric step (`ink-950`,
`amber-500`) marks a swatch, not a role assignment — `ink-950` is a color that
happens to contain "ink"; `text` is the token that says where ink goes. Pairing
ramp steps produced confident nonsense on real sets, so roles are read from
semantic names only.

**Two names resolving to the same value fail.** A declared foreground and
background that carry one color is invisible text — Lc 0 at 1.0:1 — and the
worst thing this command could do is call it a benign alias and exit 0. It is
reported as the most severe failure there is, with no proposed fix: no
lightness move on the foreground repairs a pair that is wrong in itself.
Two *unrelated* neutrals sharing a hex are still listed, but they only reach
the gate when the set declares them as a pair.

### Declaring the pairs that actually meet

Name inference cannot know intent. Our own set defines `paper-50` — a *warm
paper surface for printed / risograph contexts* — which reads as a background by
name but never sits behind screen text. Declare the real pairs to fix this
permanently (SKILL CONVENTION, at the token-file root):

```json
"$extensions": {
  "community.design-tokens.contrast": {
    "pairs": [["text", "background"], ["muted", "background"], ["on-primary", "primary"]],
    "exclude": ["surface", "accent"]
  }
}
```

- **`pairs`** — when present, these are measured and nothing else. Each entry is
  `[foreground, background]`, optionally
  `[foreground, background, "body"|"non-body"|"graphic"]`.
  Names resolve as a full path (`color.text`), a flat name (`brand-primary`), a
  bare final segment (`primary`), or a role. Where a short name is ambiguous
  across groups, a candidate in the **same group** wins — so
  `color.brand.on-primary` pairs with `color.brand.primary`, never with a
  `color.chart.primary` that merely shares the leaf.
- **`exclude`** — tokens never paired in either position; applies whether pairs
  are declared or inferred.
- **`pairs: []`** measures **nothing**. An empty list is a declaration that no
  pair meets, not an absent declaration — it does not fall back to inference.
- Absent entirely, pairs are inferred from roles, so existing sets keep working.
- **A name that resolves to no token is reported, never dropped.** A typo in a
  declared pair prints under *named in the contrast declaration but not found*
  and exits non-zero. Silence there would leave the gate green over exactly the
  pair you asked it to check. The same applies to an unknown level.

**Levels.** `body` (Lc 75 / 4.5:1) is text read in quantity; `non-body`
(Lc 60 / 3:1) covers links, icons, badges, and large display text; `graphic`
(Lc 45 / 3:1) is color that is **never** text — a fill, a rule, a chart mark.
`graphic` must be declared, per pair or via `--level graphic`: inference never
assigns it, because a token's name cannot tell you whether it is painted as
type. An `on-X` token is always measured as `body` — it is ink by definition,
whichever fill it names.

### Gating

- `validate <file>` and `use` print failures as `warning:` lines — advisory, exit 0.
- `validate <file> --strict` promotes them to **errors** (exit 1), so CI can gate on them.
- `contrast <file>` exits 1 on any failure by itself.

### Themes

A token file is one theme (the convention is one override file per theme, merged
before use). So run `contrast` **after** the merge, once per theme — a palette
verified only in light mode is a palette half-verified.

## Brand-style extensions ($extensions)

SKILL CONVENTION: a `$extensions["community.design-tokens.brand"]` block at the token-file root (`mood` adjectives, `imageryStyle`/`voice` prose, `subjects`, `avoid`, `negativePrompt`) feeds the prompt door: mood/imageryStyle join the brand clause, `avoid` becomes DON'T lines, `negativePrompt` an "Avoid:" tail. See `templates/brand-extensions.example.json` (worked ai-design example). Fidelity tests (`references/prompt-fidelity-notes.md`): art-direction **prose** with hexes + color words beats both the bare comma-clause and strict constraint blocks (which are unreliable on Nano Banana); provider capabilities in `references/providers.md`.

The block is technically optional in DTCG, but leaving it out makes the **art-direction contract silent**: palette and type say nothing about illustration style, so every downstream generator (`brand-illustrate`, the prompt door) has to guess or ask. Treat it as a first-class part of setup, not an afterthought — author it during `setup-edit`, and `validate`/`use` will **warn** (never fail) when it or `imageryStyle` is missing.

### Authoring the brand block (questionnaire)

After scaffolding a set (`setup-edit`), or when editing a set whose validate/​use output warns that the block is missing, walk the user through these questions **one at a time**. Use a structured multiple-choice question tool when the agent has one; fall back to a plain numbered question otherwise. Write the answers into `$extensions["community.design-tokens.brand"]`.

> **Claude Code extras:** use `AskUserQuestion` for the pick-one/pick-many steps (imageryStyle direction, mood adjectives) so the options render as chips. On other agents, list them as plain text and read the reply back.

1. **imageryStyle** *(load-bearing — never skip)*. "What visual language should on-brand imagery use?" Offer concrete directions, let the user pick one or describe their own:
   - **flat-geometric** — flat vector, geometric shapes, dot-grid/stipple textures, code-native
   - **technical-line** — thin-line technical/blueprint drawing, engineering diagram feel
   - **risograph** — textured print, limited flat inks, grain, zine aesthetic
   - **painterly** — brush/ink or gouache, organic, hand-made
   - **photographic** — real photography, lighting/lens language
   - **3D-sculptural** — rendered forms, material and depth
   - **Other** — the user's own prose (capture verbatim)
   Store as a short prose sentence (e.g. "flat vector illustration with dot-grid textures; no photorealism"), not just the keyword — fidelity tests show prose beats a bare tag.
2. **mood** — "Two to four adjectives for how the brand should feel." (e.g. precise, editorial, calm.) Store as a list.
3. **avoid** — "Anything specific this brand must never show?" Brand-specific negatives (stock-photo people, glossy 3D blobs, lens flares). Store as a list; these become DON'T lines. (The generic de-slop negatives are added downstream by `brand-illustrate`, so don't restate them here.)

Optionally capture `voice`, `subjects`, and a terse `negativePrompt` tail when the user offers them. Confirm existing values on edit rather than re-asking from scratch.

## Serving previews (default)

Generated HTML is meant to be **served, not opened from disk**. Browsers treat
`file://` URLs as unique security origins, which breaks cross-origin web-font
loads, `fetch`, and many extensions (`Unsafe attempt to load URL … 'file:' URLs
are treated as unique security origins`). So `use` (and `preview` when it writes a
file) start a tiny stdlib HTTP server on `http://127.0.0.1` and open the result —
**by default when run interactively** (a TTY). In scripts / CI (non-TTY) serving
is skipped so nothing blocks; force it either way with `--serve` / `--no-serve`.
`serve <path>` does the same for any existing file or directory. Dependency-free
(`http.server`).

## Extracting tokens from a live site

Tokens can be reverse-engineered from any shipping site, then saved as a template.
The method doesn't matter — pick what the site allows:

1. **Fetch the CSS** (static sites): grab the linked stylesheet(s), then resolve
   the variable indirection to ground values. Modern design systems alias twice —
   e.g. Monaspace's `--color-neon-primary: rgb(var(--color-neon-primary-rgb))` and
   `--color-neon-primary-rgb: 245 184 165` → `#F5B8A5`. Base scales
   (`--base-size-16: 1rem`) give the spacing/radius steps.
2. **Computed styles** (JS-rendered sites): drive a real browser (`/browser-mate`)
   and read `getComputedStyle(:root)` plus key elements — yields ground-truth values
   no matter how they're authored.
3. **`import <css>`**: if the site exposes a flat `:root` block, pipe it straight
   through the importer (names preserved).
4. Hand-curate the extracted values into `<name>.tokens.json` with explicit role
   aliases (`primary`, `text`, `background`, …) so the prompt door and tufte map
   light up, and `validate`.

`templates/monaspace.tokens.json` is the worked result for
[monaspace.githubnext.com](https://monaspace.githubnext.com/) — its five-font
superfamily (Neon/Argon/Xenon/Radon/Krypton) as accent colours over the GitHub
dark canvas (`#0D1117`), on the 4/8/16/24 base scale. Scaffold from it with
`setup-edit my.tokens.json --from templates/monaspace.tokens.json`.

## Prompt door (tokens → generation)

The spine ends at CSS/DESIGN.md; the **prompt door** carries the brand onward
into image and report generation so it never needs hand-translating. All of this
is **skill convention**, not DTCG — colour *roles*, the curated preset picks, and
the tufte variable map are generation aids layered on the standard.

- **Brand summary** (`brand_summary.py`): distils resolved tokens into palette
  (with roles inferred from token names: `primary`, `text`, `background`,
  `accent`, `success`, `warning`, `danger`, `muted`), fonts, type specimens, and
  a shape word from the largest corner radius (`sharp`/`soft`/`rounded`/`pill`).
- **`gpt-image-2`**: emits CLI lines across that tool's **unique** presets
  (`editorial`, `bauhaus`, `isometric`, `poster`) so one brand yields distinct
  moods; the brand's exact hex/fonts/shape are baked into each subject.
- **`nano-banana`**: steers to *its* edge — accurate in-image text (`--model
  pro`) and reference-image anchoring — over the shared presets. (It has no
  presets unique to itself; its set is a subset of gpt-image-2's shared eight.)
- **`tufte`**: emits a `:root` block mapping brand roles onto `/tufte-report`'s
  own variables (`--ink`, `--bg`, `--spark-primary/secondary/tertiary`,
  `--status-red/amber/green`, `--accent`). Roles with no matching token fall back
  to tufte-report's defaults, labelled inline. (`/tufte-report` consumes a theme,
  not a DESIGN.md.)

## DESIGN.md output

`use` and `design-md` emit a **DESIGN.md** — the agent-facing format read by Claude
Code, Cursor, v0, Lovable, Stitch. It is complementary to DTCG: DTCG `.tokens.json`
is the rigorous source of truth; DESIGN.md is the prose+tokens artifact agents apply.
Our resolved tokens map to its frontmatter as: `color` → `colors`, `typography` →
`typography`, `dimension` under `space*` → `spacing`, `dimension` under
`radius/rounded*` → `rounded`. Names are flattened (drop the top group, dots → `-`).
Types without a DESIGN.md home (`duration`, `shadow`, `number`, `fontFamily`,
`fontWeight` standalone) are noted in the Overview, not the frontmatter. This
name/bucket mapping is a skill convention over the DESIGN.md alpha schema.

**Generated, not hand-edited.** DESIGN.md is a compiled render of the token set —
the same one-way pipeline as CSS. It carries provenance frontmatter (`generator:
"design-tokens"`, `source:`, `regenerate:`) plus a do-not-edit line in the
Overview naming the source file and the exact regeneration command. `setup-edit`
writes it next to the token file (its canonical home per the storage convention);
`use` writes it into the output dir; `design-md` prints or `-o`-writes it.
**Stale-overwrite guard:** before overwriting, an existing DESIGN.md that lacks
the `generator: "design-tokens"` marker is treated as hand-written/foreign — the
tool warns and leaves it untouched rather than clobber it; regenerate explicitly
with `design-md <src> -o DESIGN.md`.

**Brand direction (default output).** Whenever the `$extensions` brand block
carries `mood` / `imageryStyle` / `subjects` / `avoid`, a `## Brand direction`
section renders in the **default** DESIGN.md (not gated behind `--rich`) — so the
art-direction contract travels with the compiled artifact. The frontmatter schema
is otherwise unchanged for Labs consumers.

**Rich mode (opt-in, non-standard).** `--rich` sources extra sections from optional
keys in `$extensions["community.design-tokens.brand"]`: `essence` (prose),
`components` `[{name, role, spec}]`, `animations` `[{name, role, spec}]` (spec may embed code fences — motion recipes render under "Animation Recipes"), `dos`/`donts` `[str]`, `surfaces`
`[{level, name, value, purpose}]`, `elevation` `{label: note}`, `imagery` (prose,
falls back to `imageryStyle`), `layout` (prose), `similarBrands` `[{name, note}|str]`.
The frontmatter stays standard; the body gains a labelled skill-convention block, so
the file is no longer a plain Labs alpha document — hence the confirmation prompt.

## Storage convention

Token files are **canonical source — keep them visible and committed, never in a
hidden dotdir** (a leading dot reads as ignorable tool state; Style Dictionary uses
`tokens/`, DESIGN.md lives at repo root, DTCG mandates the extension but no path).

- Global sets: `~/design-tokens/<set>/base.tokens.json` (a shared, user-level location outside any project — put your agent's config dir here if it has one)
- Project, single set: `<project>/design.tokens.json` + `<project>/DESIGN.md` at root
- Project, multi-scope: `<project>/tokens/base.tokens.json` + `<project>/tokens/<name>.tokens.json`
- Multiple themes (light/dark): keep one override file per theme and merge it before `use`.
- Reserve a dotdir, if any, only for *generated* output (`tokens.css`, `preview.html`).

## Tests

`cd design-tokens && PYTHONPATH=scripts python3 -m pytest tests/ -v`
