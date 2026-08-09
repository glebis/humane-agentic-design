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
7. **Before prepending, search the file for your version number.** Parallel
   sessions each writing "their" entry is how a heading appears twice; if the
   heading already exists, merge into it. `tests/test_changelog.py` enforces
   uniqueness, descending order, and version agreement with `plugin.json` and
   `marketplace.json` — run it after any edit here.
8. **Name skills as `humane:<skill>` and settings in backticks**, matching the
   ownership table in `CLAUDE.md`, so a reader can jump straight to the owner.

---

## 0.17.0 — 2026-08-09

### Artifacts live beside the project, named for the skill that made them

1. `artifact_root` now defaults to **`.design`**, next to the thing being
   designed, so artifacts travel with the project and can be committed with it.
   `corpus_root` is untouched — a JTBD corpus stays personal and global.
2. Every artifact is named for its skill in one flat directory:
   `.design/prototype-dashboard.pen`, `.design/specimen-headings.html`,
   `.design/board-editorial/`, `.design/walk-signup/`. The prefix tells a reader
   which skill wrote a file without opening it, and a flat directory sorts by
   kind.
3. `artifact_path(name, kind, ext)` resolves it. Omit the extension for a kind
   that produces several files and you get a directory of the same name.
4. A **relative** `artifact_root` resolves against the project directory, never
   the working directory — the distinction the setting exists for. `.design`
   resolved against the CWD would recreate the bug 0.15.0 fixed, with an agent
   creating `.design` wherever it happened to be standing.

### Fixed

- `references/paths.md` still claimed a design file would land under
  `artifact_root`. It cannot: a backend keeps documents in its own store —
  Pencil in `~/.pencil/documents/<uuid>/` — so `.design` cannot hold a `.pen`.
  The table now says the location is not ours to set, and names `export_nodes`
  and `export_html` as the way to get something from a design file into
  `.design`. `design_tool` says *whether* a backend is used, never *where* it
  writes.

## 0.16.1 — 2026-08-09

### Fixed

- `humane:prototype` claimed a prototype after tokens exist "is not a
  prototype" while also offering a token-faithful tier that requires them; the
  skill now distinguishes greenfield prototyping from prototyping inside an
  existing system, where the tokens are context.
- The one-question gate could be settled by the maker's own impression; a
  question now counts as settled only by the user or a named reviewer's output,
  and a broad request is narrowed to one question with the user before drawing.
- The question, corpus citation, and "what is fake" disclosure could live only
  in chat and detach from the file; every prototype now embeds them as a
  visible notes block.
- No conformance check existed on the artifact itself; a smoke test (no-hash
  load, every hotspot, zero external requests, string widths) now runs before
  handoff, with anything unrunnable reported "Not verified".
- The `:target` screen-switching rule allowed an improvised sibling fallback
  that leaves the first screen visible; `references/formats.md` now ships one
  canonical scaffold and names its browser baseline.
- The skill restated `setup`-owned path rules and named `before-after` as a
  consumer without a graph edge; the path contract now points at
  `setup/references/paths.md` and the description names only declared routes.
- `humane:prototype` claimed it would write a design file to
  `<artifact_root>/<slug>/prototypes/<name>.pen`. It cannot. A design-file
  backend writes into whichever document its application has open and ignores
  the path it is given — Pencil accepts a `filePath` argument on every tool and
  disregards it, so a build aimed at a path that is not open lands in an
  unrelated file and still reports success. Found by testing the 0.16.0 claim:
  a full dashboard and fourteen variables were written into an open icon file,
  every call returning `OK`. The skill now reads the active document, compares
  it to where the prototype belongs, and **stops** if they differ — asking the
  user to open the file, because the agent can neither create nor switch one.
  It also cleans up after a mis-targeted build, including the variables, which
  merge into the host document and survive node deletion.

## 0.16.0 — 2026-08-09

### Carry a prototype on into a design file

1. When the host exposes a design-file backend, `humane:prototype` can produce
   an editable design file (`.pen`) instead of a rung-3 HTML page. Take that
   exit when you want to *carry on designing* — in a visual editor, or by
   handing it to someone who will.
2. `scripts/humane_setup.py config --set design_tool=none` pins it off; `auto`
   (the default) uses a backend when the host has one and stays on the ASCII →
   SVG → HTML ladder when it does not.
3. The file lands at `<artifact_root>/<slug>/prototypes/<name>.pen`, alongside
   every other prototype.
4. If a token set exists the design file is built from it. If none exists, a
   backend's own style archetype is scaffolding — it goes in the "what is fake"
   list, and a direction that survives goes to `humane:brandkit` and then into
   `humane:design-tokens`, which owns it.

A design file is not a higher rung. The ladder makes disposable artifacts that
answer one question; a design file is a living document. It also does not open
on its own, and its HTML export references image assets by relative path rather
than embedding them — so it is a handoff to implementation, not the
self-contained artifact rungs 2 and 3 promise. The skill says which of the two
it produced.

## 0.15.1 — 2026-08-09

### Fixed

- `humane:prototype` click-dummies could render unreadable or overflowing SVG
  text: a stylesheet rule silently beats a `fill` attribute (dark-on-dark
  labels), and SVG text neither wraps nor clips (strings run over neighbouring
  elements). The rung-2 contract in `references/formats.md` now names both
  traps and requires a width check on every string, including after a copy
  rewrite lengthens one.

## 0.15.0 — 2026-08-09

### Put every generated artifact where you want it

1. `scripts/humane_setup.py config --set artifact_root=./design` moves every
   generated artifact — prototypes, specimens, boards, illustrations, walk
   screenshots, saved reviews — without touching where `humane:jtbd` keeps the
   corpus. Left unset it follows `corpus_root`, so everything stays in one
   bundle.
2. `humane:setup` gains `references/paths.md`: one table naming every file each
   skill writes, where it goes, and which setting moves it. If a skill writes
   something that is not in that table, that is a bug in the skill.
3. The layout is fixed per project slug — `prototypes/`, `specimens/`,
   `boards/`, `illustrations/`, `walks/<date>-<task>/`, `reviews/<date>/` — so
   an artifact can be found without knowing which skill made it.
4. `humane:design-tokens` and `humane:persona-review` still write beside their
   input, deliberately: a compiled `tokens.css` belongs next to the token file
   it came from. That is stated in the table rather than left to look like an
   oversight.

### Fixed

- `humane:prototype` wrote to a bare relative `prototypes/<slug>/`, so a
  prototype landed in whatever directory the agent was standing in — including,
  once, this plugin's own source tree. It now resolves through `artifact_root`,
  and the four artifact directories are gitignored so a stray one cannot be
  committed into the plugin.
- `humane:type-specimen`, `humane:brandkit` and `humane:brand-illustrate` had no
  default output location, leaving each run to invent one. All three now name
  `artifact_root` and say where their output lands.

## 0.14.0 — 2026-08-09

### See and click an idea before any design system exists

1. Ask for a prototype — "mock this up", "show me the flow", "wireframe this
   screen" — and `humane:prototype` names the one question the prototype must
   answer, then picks the cheapest fidelity that answers it: an ASCII sketch
   for structure, an SVG click-dummy with hotspots linking screens for
   navigation, or a self-contained HTML file for how a screen reads.
2. For HTML you choose the tier: grayscale wireframe (the default before a
   token set exists), or token-faithful, rendering under the project's
   compiled `humane:design-tokens` CSS.
3. You get one double-clickable file in `prototypes/<slug>/` — no CDN, no
   build step — with the question, the corpus citation, and a list of what is
   fake, so reviewers don't report scaffolding as findings.
4. The prototype is a first-class artifact for the rest of the cycle: hand it
   to `humane:respondent-panel` for gut reactions, `humane:walkthrough` to
   attempt the job on it, and on to `humane:design-tokens` once the structure
   survives.

Drafted prototype copy is scaffolding: any string that outlives the prototype
is handed to `humane:ux-writing`, which owns it.

## 0.13.0 — 2026-08-08

### Run a full review without the evidence quietly going missing

1. `humane:review` now chooses how to run: **inline** by default, or **fanned
   out** when a `full` review of a runnable interface would fill the context
   before it reaches consolidation.
2. Fanned out, each domain runs in its own context and returns only its findings
   table — not its reasoning, not the artifact, not its screenshots.
   `humane:walkthrough` goes first and alone, because it drives a live browser
   across ordered steps and cannot be split per step.
3. A domain that dies, returns nothing, or returns something that is not a
   findings table is recorded **Not reviewed**, never `Clear`.
4. Findings carry the locator, not the payload: `src/Nav.tsx:42` and a
   screenshot path survive summarizing and cross a subagent boundary intact —
   the file contents and the image itself do not.
5. Scope and coverage states which way the review ran, because a fanned-out
   review consolidated locators while an inline one held the evidence itself.

This is an honesty rule, not an efficiency one. A host that compacts a full
context does not fail — it summarizes and continues, and `Clear` can outlive the
evidence that justified it.

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
