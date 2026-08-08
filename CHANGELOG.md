# Changelog

What you can do with `humane` that you could not do before, newest first.

## How to write an entry

1. **Bump `version` in `humane/.claude-plugin/plugin.json` first.** The heading
   here is that number and the date of the release commit. A commit that does
   not bump the version belongs under the version it lands in, not its own
   heading.
2. **Lead with the capability, not the commit.** One `###` heading per feature,
   phrased as the thing a user can now do — "Configure humane before you run
   it", not "add setup skill".
3. **Under it, write the steps.** A numbered list of what the user actually
   types or answers, in order, ending in what they get. Commands in backticks.
   Three to six steps; if it needs more, the feature is two features.
4. **One sentence of why, only when the step list does not carry it.** No
   rationale essays — those live in the commit body, which is where anyone
   debugging will look.
5. **Fixes get a `### Fixed` list, not step lists.** One line each, stating the
   wrong behaviour and the new one: "`corpus_root` was read by no skill; every
   consumer now resolves it." A fix nobody could have hit does not go here.
6. **Never document what the user cannot reach.** Refactors, test-suite
   changes, and internal renames are invisible releases — skip them entirely
   rather than padding a section.
7. **Name skills as `humane:<skill>` and settings in backticks**, matching the
   ownership table in `CLAUDE.md`, so a reader can jump straight to the owner.

---

## 0.12.0 — 2026-08-08

### Find out what runs next without guessing the cycle

1. Run `humane:using-humane` when it is not obvious which skill owns a design
   task. It matches the intent to an entry point, and says plainly when a task
   has no humane owner instead of stretching a design skill over it.
2. Finished a skill and unsure what follows? Ask the graph rather than
   recalling it: `python3 scripts/graph.py --from layout-rules` prints what
   that skill hands to and the condition that opens each route. `--to <skill>`
   answers the reverse, and `--mermaid` draws the whole cycle.
3. The routes are declared in each skill's own frontmatter — `handoffs:` with a
   `when:`, `accepts:` on the receiving side, and `orchestrates:` for
   `humane:review`, which calls its domain skills rather than handing to them.
4. A handoff is a condition, not an instruction: a `humane:layout-rules` pass
   that found no contrast issue does not hand to `humane:design-tokens`. The
   route names what could come next; you decide whether it runs.

### Fixed

- A skill could reference a handoff the receiving skill had never heard of, and
  nothing noticed; every route now has to be acknowledged on both sides or the
  test suite fails, naming the edge and the fix.

## 0.11.0 — 2026-08-08

### Walk a task on a real device, not a resized window

1. Run `humane:walkthrough` against a live URL. Driven mode now follows a
   single written procedure — `walkthrough/references/driven.md` — instead of
   improvising with whatever browser tool is around.
2. The tool ladder resolves automatically: the `agent-browser` CLI first
   (portable, headless, real device emulation), then Playwright MCP, then the
   host's browser tools, then you drive and describe. `humane:setup`'s doctor
   detects the first rung and prints `npm i -g agent-browser` when it is
   missing; pin a rung with the new `browser_tool` setting.
3. The walk runs a device matrix: `set device "iPhone 14"` for the mobile
   tier (real UA, DPR, and touch — so tap-target and hover-only breaks are
   observed, not guessed), 1440×900 for desktop, iPad only when the product
   targets tablets. Every finding names the tier it was seen on.
4. One screenshot per step per tier lands in
   `<corpus_root>/<slug>/walks/<date>-<task>/step-NN-<tier>.png`; the filename
   is the evidence locator, and `agent-browser errors` is checked after each
   step.
5. The mode gate keeps the claim honest: a "Driven" walk without a complete
   screenshot trail is downgraded to what the evidence supports, with the
   undocumented steps listed as **Not verified**.

`humane:review` full mode now includes the mobile tier for any runnable
interface — or reports it **Not reviewed**, never silently narrowed to
desktop. `humane:nielsen-heuristics` live-URL evaluations drive by the same
file, so there is exactly one driving procedure in the cycle.

### Every skill announces itself

1. Each humane skill now opens with an announce line — "I'm using the
   humane:<skill> skill to …" — matching the convention Superpowers
   established, so a session mixing both plugins narrates which method owns
   the current step.

## 0.10.0 — 2026-08-05

### Choose a typeface against your own copy, not "Hamburgefonstiv"

1. `scripts/specimen init -o spec.json --locale ru --context "a till for cafés"`
   writes a config and stores the brief. `--from-file README.md` takes it from
   a document instead.
2. Fill the ten text slots with real product strings —
   `scripts/specimen texts spec.json --set headline="Смена закрыта в 21:40"`.
   `humane:ux-writing` owns the wording; this skill only says which strings
   prove something and how long they have to be.
3. List the shortlisted families, then `scripts/specimen build spec.json`. It
   writes one standalone HTML page and serves it on `127.0.0.1`.
4. Every family is set in the same copy: display line, figures, a weight ladder
   built from the weights the family actually ships, prose in columns, a data
   table, list rows, uppercase and small caps, glyph coverage and variable
   axes. Declare `scriptRange` to have a family missing your Cyrillic or symbol
   coverage badged, not silently shown in a fallback.
5. Click any specimen text in any card and edit it in place. The edit writes to
   one source of truth and lands in every family at once, so you are always
   comparing families rather than accidentally comparing copy. Escape reverts;
   **Copy link** encodes the whole shortlist into the URL.

`scripts/specimen check` refuses to build a config whose slots still say
`TODO` — the placeholders exist so unwritten copy cannot be mistaken for a
finished specimen.

It produces evidence, not a verdict: no score, no ranking, and coverage claims
cover only the glyph sets you asked it to test. The chosen family then enters
`humane:design-tokens`, which owns it — and owns any contrast remediation —
from that point on.

### Fixed

- The marketplace listing was pinned at 0.9.0 while the plugin was at 0.9.1, so
  anyone installing through the marketplace got a version behind. Both now
  carry the same number — the exact drift `humane:setup` exists to catch.

## 0.9.1 — 2026-08-05

### Fixed

- `corpus_root` was configured and then read by nobody — `humane:ux-writing`,
  `humane:walkthrough`, `humane:before-after` and `humane:jtbd` all assumed
  `~/jtbd`. Moving your corpus produced "no corpus found" everywhere and copy
  written from assumption. Every consumer now resolves project > global > env >
  default.
- `image_backend` never reached `humane:brand-illustrate`, which read only the
  environment variable. `config --set image_backend=nano-banana` wrote a file
  nothing opened. `backends` now prints which layer won.
- A `humane.json` with a trailing comma silently reverted every setting to the
  layer below while `doctor` reported `source: default`. Unreadable files are
  now named, values marked suspect, and the run exits non-zero.
- Identical text and background colours passed the contrast gate as a benign
  "alias collision". A declared foreground/background resolving to one colour
  is now the most severe failure `tokens contrast` reports.
- A declared contrast pair that named one token twice, carried the wrong type,
  or failed to resolve was ignored in silence — the narrowing you declared was
  quietly replaced by measuring everything. Each case is now reported.
- A failed image-generator subprocess returned `ok:true` and a contact sheet
  full of missing files.
- CSS angle units were stripped instead of converted, so `0.25turn` read as a
  quarter degree — a wrong hue rather than an error. `turn`/`rad`/`grad` now
  convert.

## 0.9.0 — 2026-08-03

### Configure humane once, before anything reads a setting

1. Run `humane:setup`. It reports what is installed, what each of the five
   settings resolves to, and which layer supplied it.
2. Answer the questions for the settings you want to pin.
3. Confirm the install commands it proposes — nothing is installed until you do.
4. Re-run `doctor` any time to re-diagnose.

### See when your installed copies of a skill have drifted apart

1. Run the setup doctor with humane installed in more than one place —
   `~/.claude/skills`, `~/.codex/skills`, a registered plugin marketplace.
2. Read the classification per copy: linked, links to a different source,
   missing N files (each one named), or identical for now.
3. Fix what you care about. Nothing is blocked and nothing is auto-repaired.

A marketplace pinned three versions back reports clean against its own remote;
comparing version and skill count against this checkout is what catches it.

### Get your illustration prompts even with no image backend installed

1. Run `humane:brand-illustrate` through its questionnaire as usual.
2. With no generator on the machine, the run writes `prompts.md` — every final
   prompt at its target size — plus `metadata.json` and the recipe.
3. Install a generator later and resume the same batch with `run --recipe`.

### Point humane at any image generator, on any agent

1. Set `HUMANE_IMAGE_BACKEND=<name>:<path>` to name one explicitly, or
2. let resolution fall through `HUMANE_SKILLS_DIR`, the known agent skill roots
   (Claude Code, Codex, XDG, project `.agents` and `.claude`), then `PATH`.
3. Run `backends -v` to see what was found and every location searched.

## 0.8.0 — 2026-08-03

### Read the whole method off the README

1. Open `README.md`: the hero diagram and the numbered cycle now both show the
   same nine steps in the same order.
2. Each skill has its own section — what it does, what it outputs, when to
   reach for it.
3. Install via `npx skills add` with the four interactive prompts documented,
   including where files land and which scope to pick.

Cross-agent manifests ship alongside, so the set is installable outside Claude
Code.

## 0.6.1 — 2026-07-30 → 07-31

*(0.7.0 was never published; `humane:respondent-panel` shipped inside this
version.)*

### Find out how an artifact lands on strangers

1. Run `humane:respondent-panel` with the user-facing artifact and nothing else.
2. Name the demographic axes for the panel; each respondent runs in an isolated
   context so it cannot inherit what your session already knows.
3. Read the analysis: convergence first, divergence named by axis, comprehension
   counted.
4. Send anything that needs rewriting to `humane:ux-writing` — respondents never
   suggest alternatives, which is the point of them.

### Compare every version of an illustration in one place

1. Generate two or more batches from the same recipe.
2. Open the contact sheet gallery: all versions across batches, full-size
   lightbox, keyboard navigation, both themes, no dependencies.

## 0.6.0 — 2026-07-30

### Explore a brand identity before any tokens exist

1. Run `humane:brandkit` on a project with no token set.
2. Review the competing identity directions it boards.
3. Confirm one — only then is it written into the `humane:design-tokens` brand
   block. Projects without tokens get a draft path instead.

## 0.5.0 — 2026-07-30

### Render your brand as one generated document

1. Run the design-tokens export.
2. Read `DESIGN.md` — the single generated brand render, carrying provenance and
   the brand direction in default output.
3. Edit the setup sibling rather than the render; a stale guard tells you when
   the two have diverged.
4. Add `--strict` to gate on verbatim `clamp()`/`calc()` tolerance.

## 0.4.0 — 2026-07-30

### Give downstream generators a real art direction

1. Answer the `imageryStyle` / `mood` / `avoid` prompts during token setup.
2. `validate` warns when the block is silent.
3. Any generation skill reading the contract now gets direction by default,
   never an empty one.

## 0.3.2 – 0.3.0 — 2026-07-30

### Generate an illustration set from your tokens

1. Run `humane:brand-illustrate` and answer the questionnaire (`variants` is the
   subject list).
2. It assembles prompts from the palette, the brand block, and the merged
   de-slop negatives from `humane:layout-rules`.
3. It generates through whichever backend adapter is installed and resizes to
   the platform presets.
4. It saves a reusable recipe and hands the batch to `humane:review`.

## 0.2.2 – 0.2.0 — 2026-07-29

### Get an executive summary out of a JTBD corpus

1. Run the `humane:jtbd` report for a single project or across the corpus.
2. Read the summary with its honesty guards intact — nothing scored that was
   not observed.
3. Switch chrome between English and Russian.

### Explore the corpus visually

1. Open the JTBD viewer.
2. Zoom and pan the graph; click any level of the icicle, which captions its own
   rows.
3. Navigate table rows by keyboard; read the matrix with diagonal headers, equal
   cells, and WCAG AA light tokens.

## 0.1.0 — 2026-07-29

### Install the method as a plugin

1. Add the marketplace, or install the skills directly — both channels work.
2. You get six skills — `humane:jtbd`, `humane:persona-review`,
   `humane:design-tokens`, `humane:layout-rules`, `humane:nielsen-heuristics`,
   `humane:before-after` — plus the `synthetic-respondent` agent.
3. Skills and agents are discovered by convention; nothing is declared by hand.
