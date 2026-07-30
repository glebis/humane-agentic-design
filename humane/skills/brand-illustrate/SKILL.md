---
name: brand-illustrate
description: This skill should be used when the user wants illustrations, images, or visual assets that match their brand — "brand illustrations", "on-brand images", "an illustration set", "generate images matching my tokens/brand", "hero art for the site", "covers for social". Runs a short step-by-step questionnaire (JTBD-style), assembles a prompt scaffold from the design-tokens context, calls whichever image backend is installed (gpt-image-2 or nano-banana — not bundled), and ends with a coherent, reviewed, platform-sized batch plus a reusable recipe.
---

# Brand Illustrate

Turn a design-token set into a coherent illustration batch. The pipeline exists to kill four failure modes of raw generator prompting: off-brand drift, re-describing the brand every session, sets that don't read as one family, and review chaos.

## Flow

Ask the user **one step at a time**. Use a structured multiple-choice question tool when the agent has one; otherwise ask in plain language. Never dump all steps as one wall of questions.

**Step 0 — recipe reuse.** If a `<tokens-name>.illustrate-recipe.json` exists next to the token file, offer to reuse it (optionally with a new subject). A reused recipe skips straight to generation.

**Step 1 — subject & purpose.** What is being illustrated, and where will it live (site section, social post, deck, product UI)?

**Fast path:** for a single one-off image, stop asking here — derive everything else from the tokens and the defaults below. The questionnaire must never be slower than a raw prompt.

**Step 2 — style beyond tokens.** Ask ONLY what the token context does not answer (art direction: flat vs textured, line weight, abstraction level, human figures or not). If the tokens are silent on art direction, ask — never guess a style.

**Step 3 — count & variants.** How many pieces; variants per piece.

**Step 4 — sizes/platforms.** Offer the presets (`illustrate.py platforms`): og-image 1200×630, thumbnail-16-9 1280×720, square-post 1080×1080, deck-cover 1920×1080, spot-ui 512×512.

**Step 5 — backend & budget.** Which installed backend (`illustrate.py backends`), and draft vs final quality.

**Step 6 — reference images (optional).** A directory of prior winners to anchor style transfer (nano-banana supports references natively).

**Step 7 — negatives (optional).** Anything to avoid, merged on top of the built-in de-slop negatives (derived from layout-rules: no gradient soup, no glassmorphism, no generic 3D blobs / corporate-memphis, …).

## Commands

```bash
python3 scripts/illustrate.py backends                 # which generators are installed
python3 scripts/illustrate.py platforms                # size presets
python3 scripts/illustrate.py scaffold --tokens T --answers A.json   # inspect the assembled prompt, no generation
python3 scripts/illustrate.py run --tokens T --answers A.json [--out-dir D] [--dry-run]
python3 scripts/illustrate.py run --recipe R.json      # reuse a saved recipe
```

`--answers` is a JSON file of the questionnaire results: `purpose`, `style`, `count`, `variants`, `platforms` (list of preset names), `backend`, `budget` (`draft`|`final`), `refs_dir`, `negatives` (list), `seed`.

## What a run produces

- A batch directory with the generated images and a `metadata.json` (prompt, backend, seed, sizes, timestamps).
- `<tokens-name>.illustrate-recipe.json` saved next to the token file — the resolved scaffold + answers; offer it as Step 0 next time.
- Review handoff: if the `cull` CLI is available, offer importing the batch for rating; otherwise a plain contact-sheet HTML is written into the batch dir.

If **no backend is installed**, the script exits with instructions naming both backends and both install channels — it never half-generates.

## Guardrails

- Generators are NOT part of this skill; the adapter only detects and calls them.
- Series coherence comes from a shared style block and seed reuse — one batch, one visual family.
- When tokens lack art direction, ask the user (Step 2); style is a decision, not a default.
- `--dry-run` first when the user is cost-sensitive; `draft` budget for iteration, `final` for keepers.

## Claude Code extras

On Claude Code, run the questionnaire with the AskUserQuestion tool (one call per step, options + an Other escape). Backends resolve from `~/.claude/skills/{gpt-image-2,nano-banana}` in addition to plugin-relative paths. Note: if a stale `OPENAI_API_KEY` env var shadows a keychain/SOPS key, invoke the gpt-image-2 path with `OPENAI_API_KEY=""`.
