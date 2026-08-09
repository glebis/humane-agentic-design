---
name: brand-illustrate
description: Turn design tokens into a coherent, on-brand illustration set through a short step-by-step questionnaire, then generate with whichever image backend is installed (gpt-image-2 / nano-banana). Assembles the prompt scaffold from the token palette + brand block, merges layout-rules de-slop negatives, requests platform preset sizes, saves a reusable recipe, and hands the batch to review. Use when a project already has a token set and needs images that match it, or when an earlier batch should be re-run from its saved recipe. Triggers on brand illustrations, on-brand images, illustration set, generate images matching my brand, illustrate this section on-brand, contact sheet.
handoffs:
  - to: review
    when: a generated batch needs reviewing before it ships
accepts:
  - from: design-tokens
---

# brand-illustrate

**Announce at start:** "I'm using the humane:brand-illustrate skill to generate an on-brand illustration set from existing tokens."

Ring-2 humane skill. It reads the on-brand contract a `design-tokens` set already
carries (palette with roles, fonts, shape, and the `$extensions` brand block) and
walks the user through a short questionnaire — JTBD-style, one step at a time — to
scaffold prompts that stay on-brand and generate a *set that reads as one family*.

Generators live **outside** the plugin. This skill is a thin adapter: it composes
the prompt and shells out to whichever backend is installed. It never bundles a
generator, an API client, or your keys.

**No backend is not a dead end.** The prompts are what this skill actually
produces — assembled from the palette, the brand block, and the merged de-slop
negatives — and they are the same whether or not an API call follows. With no
generator present, a run writes `prompts.md` with every final prompt at its
target size, plus `metadata.json` and the recipe. Paste them into any image tool,
or install a backend and resume with `run --recipe`.

### Finding a backend

Discovery makes no assumption about which agent you run. First hit wins:

| # | Source | |
| --- | --- | --- |
| 1 | The `image_backend` setting as `<name>` or `<name>:/path/to/script` | project `humane.json` > `~/.humane/config.json` > `HUMANE_IMAGE_BACKEND`; `auto` means "no explicit choice" |
| 2 | `HUMANE_SKILLS_DIR=/one:/two` | extra skill roots to search |
| 3 | Known agent skill roots | `~/.claude/skills`, `~/.codex/skills`, `~/.config/skills`, project `.agents/skills` and `.claude/skills`, and the plugin's own tree |
| 4 | `PATH` | a generator packaged as a plain executable |

Row 1 is the layered setting `setup` owns, not the environment variable alone —
a config file legitimately outranks a variable exported in the calling shell.

`scripts/illustrate.py backends -v` prints what was found and every location
searched — use it before concluding anything is missing.

## Where output goes

A batch — images, `prompts.md`, `metadata.json`, the contact sheet, and the saved recipe — goes in `.design/illustration-<batch><batch>/`, the `setup` setting defaulting to `corpus_root`, unless `--out-dir` names a place. `setup/references/paths.md` owns the full table.

## What you need first

A token file (`design.tokens.json` or `<name>.tokens.json`) produced by
`humane:design-tokens`. That file is the style contract. If the user has no token
set yet, send them to `design-tokens` first — do not invent a brand.

## The questionnaire

Ask **one step at a time** and wait for the answer before the next. Use a
structured multiple-choice question tool when the agent has one; fall back to a
plain numbered question otherwise. Never dump all seven steps at once.

> **Claude Code extras:** use `AskUserQuestion` for the multiple-choice steps
> (purpose, platforms, backend, budget) — it renders the presets as pickable
> options. On other agents, list the options as plain text and read back the reply.
> If a stale `OPENAI_API_KEY` env var shadows a keychain/SOPS key, invoke the
> gpt-image-2 path with `OPENAI_API_KEY=""` so the backend decrypts its own.

### Step 0 — Reuse last recipe? (only if one exists)

Look for `<tokenset>.illustrate-recipe.json` next to the token file. If present,
offer: "Reuse your last illustration recipe (subject, style, sizes, backend), or
start fresh?" Reuse means jump straight to generation with the saved answers;
"tweak" means pre-fill the questionnaire with them.

### Step 1 — Subject & purpose *(always asked)*

"What should the illustration show, and where will it live?" Capture a concrete
subject (the thing in frame) and the purpose/placement. This is the only
mandatory step — see **Fast path** below.

### Step 2 — Style & mood beyond the tokens

Read the token `$extensions["community.design-tokens.brand"]` block first. If it
already sets `mood` and `imageryStyle`, **confirm** them rather than re-ask
("Your brand reads as *precise, editorial, calm*, flat vector — keep that?").
If the tokens are **silent on art direction** (no brand block, or no
`imageryStyle`), you must **ASK** — never guess a style. Offer a few directions
(flat vector / editorial illustration / isotype pictograms / textured print) and
let the user pick or describe their own. To fix this permanently, run
`humane:design-tokens` setup and author the brand block once, so future batches
confirm the style instead of re-asking.

### Step 3 — Count & variants

"How many images, and are they variants of one idea or different subjects?"
- variants of one concept → set `count`, reuse one seed/anchor for coherence;
- a set of distinct subjects → collect a `variants` list (one subject per image).

### Step 4 — Sizes / platforms

Offer the presets (multi-select):

| Preset | Size | For |
| --- | --- | --- |
| `og-image` | 1200×630 | link / social preview |
| `thumbnail-16-9` | 1280×720 | video / card thumbnail |
| `square-post` | 1080×1080 | Instagram / square social |
| `deck-cover` | 1920×1080 | slide / deck cover |
| `spot-ui` | 512×512 | spot illustration / UI asset |

Multiple are fine — each subject renders at every chosen size.

**A preset is a size *requested* of the backend, never a resize.** Nothing in
this skill resizes an image — that would need an image library, and these
scripts are stdlib only. gpt-image-2 takes any exact size. nano-banana takes
only its own named platforms, which match the first four presets exactly but
have no equivalent for `spot-ui` — that image returns at nano's default size.
Each entry in `metadata.json` carries `size_requested`, and a run reports
`unsized_platforms`. When it is non-empty, say so rather than handing over an
image for a slot that needs exact pixels; switch to gpt-image-2 for that preset,
or resize it in a real image tool.

### Step 5 — Backend & budget

"Which generator, and draft or final?" Backends: `gpt-image-2` (accepts a seed
flag, though see *Coherence, honestly* — it is recorded, not yet sent),
`nano-banana` (native reference-image style transfer), or `auto` (prefers
gpt-image-2). Budget: `draft` (cheap, ~$0.006/img on gpt-image-2) first, `final`
only once a direction is approved.

The backend also comes from the `image_backend` setting owned by `setup` —
project `humane.json` > `~/.humane/config.json` > `HUMANE_IMAGE_BACKEND` >
`auto`. A configured value other than `auto` outranks a stored recipe's choice,
because that is what a user reaches for to redirect a run. `auto` is not a
choice and leaves the recipe alone. `scripts/illustrate.py backends` prints
which value won and which layer supplied it.

### Step 6 — Reference images *(optional)*

"Any reference images to steer the look?" If yes, point at a directory. If it has
a `refs.json` (from `design-tokens annotate`), roles are read from it; otherwise
ask per image what to take (palette / mood / composition / texture).

### Step 7 — Extra negatives *(optional)*

"Anything specific to avoid?" These merge on top of the built-in de-slop list —
you don't need to restate "no glassmorphism / no 3D blobs", those are always on.

## Fast path (guardrail)

If the user just wants **one** on-brand image ("make me an og-image of X"), ask
**only Step 1** and derive the rest from the tokens + defaults (count 1, the
purpose's platform preset, `auto` backend, `draft` budget, de-slop negatives). The
questionnaire must never be slower than a raw generator prompt for a single image.

## Running it

The adapter does scaffold assembly, backend probing, generation, metadata, recipe,
and the contact sheet. Write the answers to a small JSON file and run:

```bash
# Inspect the resolved scaffold (prompt, negatives, sizes) without spending:
scripts/illustrate.py scaffold --tokens <tokens.json> --answers answers.json

# Generate the batch:
scripts/illustrate.py run --tokens <tokens.json> --answers answers.json --out-dir <dir>

# Reuse the saved recipe (Step 0):
scripts/illustrate.py run --recipe <tokenset>.illustrate-recipe.json --out-dir <dir>

# Utilities:
scripts/illustrate.py platforms      # list size presets
scripts/illustrate.py backends       # show which generators are installed
scripts/illustrate.py run ... --dry-run   # print commands + write metadata, no API calls
scripts/illustrate.py gallery --dir <dir> [-o out.html]  # one sheet of ALL versions under <dir>, grouped by batch, full-size lightbox (arrows/Esc)
```

`answers.json` shape (only `subject` is required):

```json
{
  "subject": "a lighthouse built from interlocking grids",
  "purpose": "og-image",
  "style": "isotype pictograms",
  "count": 3,
  "variants": ["a lighthouse of grids", "a compass of grids", "an anchor of grids"],
  "platforms": ["og-image", "square-post"],
  "backend": "auto",
  "budget": "draft",
  "refs_dir": "/path/to/refs",
  "negatives": ["no boats", "no water"],
  "seed": 20260730
}
```

## What a batch produces

A timestamped batch directory containing:
- the generated PNGs, named `<subject>-<NN>-<platform>.png`;
- `metadata.json` — backend, seed, per-image prompt + command + size + return code;
- `contact-sheet.html` — a de-slop-clean thumbnail grid (open it to review);
- and, next to the **token file**, `<tokenset>.illustrate-recipe.json` — the
  resolved answers, so the next batch starts from Step 0, not from zero.

## Review handoff

After generation, offer review:
- if the `cull` CLI is available, import the batch dir for rating / shortlisting
  ("open these in Cull");
- otherwise open the generated `contact-sheet.html` — it already follows
  layout-rules (real headings, honest filenames, theme-aware, no eyebrow labels).

## Coherence, honestly

- **gpt-image-2** accepts a `--seed`, and the whole set reuses one so the intent
  is recorded; a default is injected when the user gives none. **This does not
  currently reproduce a batch.** The generator we shell out to takes the seed,
  prints it, and writes it to `metadata.json`, but its request builder marks the
  parameter *reserved for future API support* and never sends it. So the seed is
  a faithful record of what was asked for and nothing more. Do not promise a
  re-run will return the same images — check whether the installed generator
  sends the seed before telling a user otherwise.
- **nano-banana** has no seed. The adapter anchors the series instead: the first
  successful image becomes a `--reference` for the rest. Coherence is strong but
  not pixel-deterministic — say so if the user expects exact reproduction.
- In short: **neither backend reproduces a batch exactly today.** Coherence
  within a run is real; reproduction across runs is not.

## Guardrails (do not violate)

- Generators stay outside the plugin — never bundle or reimplement one, and
  never handle an API key. With none installed, hand back `prompts.md` and the
  resume command; do not treat it as a failure.
- No style invention. When the tokens are silent on art direction, ASK (Step 2).
- Fast path for one-off images: Step 1 only.
- Portability: the core flow names no Claude-only tool, and backend discovery
  names no single agent's directory. `illustrate.py` is stdlib-only and reads the
  token file directly (it does not import `design-tokens`), so the skill runs on
  any agent that installed it alone.

## Tests

```bash
cd brand-illustrate && python3 -m unittest discover -s tests -v
```

Covers scaffold assembly, negative-list merging, platform preset resolution, the
no-backend message, and recipe round-trip.
