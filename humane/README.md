# humane

A design *method* cycle, packaged as a plugin. Skills covering the work
**around** an interface — what to build, for whom, under which system and
constraints, in which words, audited and proven — plus one bundled agent and a
separate implementation-adapter layer.

Nothing here is a UI framework or a component library. These skills decide what
gets built and judge whether it worked.

Install and configuration: run `humane:setup`. It checks what the cycle needs,
writes the settings, and installs only what you confirm.

---

## The skills

Each rule lives in exactly one skill. When two could apply, the owner named here
wins and the other defers to it — that is what keeps a `humane:review` from
reviewing the same sentence twice under two names.

### Ring 1 — the cycle

| Skill | What it does | Owns |
| --- | --- | --- |
| **`setup`** | Diagnoses the environment, configures the five settings, installs the gaps it found. Start here. | Environment and configuration. No method rules. |
| **`jtbd`** | Interviews you (or mines reviews and transcripts) into a decision-grade corpus: jobs, switching forces, ODI outcomes, an evidence ledger. Exports JSON, a one-pager, messaging angles, a GTM brief. | The corpus. Every later claim cites it. |
| **`persona-review`** | Puts a document in front of expert stakeholders who read it properly and object. For briefs, PRDs, specs. | Expert critique of a document meant to be **studied**. |
| **`respondent-panel`** | Runs ~5 strangers against a user-facing artifact, each in an isolated context that has seen nothing else. Reads the panel for convergence, divergence, comprehension, and dead spots. | Gut reactions from strangers. Never rewrites, never votes. |
| **`design-tokens`** | A dependency-free DTCG core: scaffold, validate, resolve aliases, export CSS and `DESIGN.md`. Layers a project set over a global brand base. `tokens contrast` measures every text/background pair on WCAG **and** APCA and proposes an OKLCH-lightness-only fix. | The token set, and **all** colour measurement and remediation. |
| **`type-specimen`** | Sets every shortlisted typeface in your own copy on one standalone page — weight ladder, prose, data table, glyph coverage, variable axes — and flags families missing your script. Any specimen text edits in place, once, across all families. | Typeface **selection**, and what a specimen may conclude. Owns no token. |
| **`layout-rules`** | 39 defect classes for tool, dashboard, viewer, and admin UIs, each one caught in a real build-and-audit cycle. Load it *before* writing HTML, not after. | Structural and interaction defects, and the de-slop avoid-list. |
| **`ux-writing`** | Turns the corpus into interface copy — the anxiety force shapes the confirmation, the quotes supply the vocabulary. Covers documentation prose too. | The source wording of every user-facing string. |
| **`nielsen-heuristics`** | Formal inspection against the 10 heuristics, with severity and evidence locators. | Usability inspection against principles. |
| **`walkthrough`** | Takes one underserved outcome and attempts it as the person who has it — including the empty, error, and interrupted paths. | Task completion: can this person get through this interface. |
| **`review`** | Orchestrates the domain skills into one verdict, in a fixed order, and says which domains it could **not** cover. | Scope, consolidation, coverage honesty, the single verdict. Owns no domain rule. |
| **`before-after`** | The felt transformation claim, and the proof a change worked. Strongest when a task that was blocked now completes. | The transformation claim. |

### Ring 2 — brand identity

| Skill | What it does |
| --- | --- |
| **`brandkit`** | Runs **before** a token set exists. Explores competing directions for a brand that doesn't have one yet, then hands the winner into the `design-tokens` brand block. |
| **`brand-illustrate`** | Runs **after** one exists. Reads the palette, fonts, and brand block, merges the `layout-rules` de-slop negatives, and generates a batch that reads as one family. Shells out to whichever image backend is installed. |

### Adapter layer — implementation fit

| Skill | What it does | Owns |
| --- | --- | --- |
| **`design-frameworks`** | Selects and probes a design-system preset, maps an implementation brief to native components/tokens/templates, previews guarded writes, then validates framework compliance separately from Humane traceability. Astryx is the first full preset; shadcn and Storybook exercise registry and catalog/MCP surfaces. | Framework discovery, fit, guarded execution, and compliance. Never the job, concept, prototype, or product verdict. |

### Bundled agent

**`synthetic-respondent`** — an ordinary person reacting to copy: gut-level, no
expertise, no politeness filter. Takes an optional persona brief. `respondent-panel`
launches several concurrently for real context isolation; on other agents it
degrades to fresh sessions run one at a time.

---

## Order of use

```
setup  →  jtbd  →  persona-review / respondent-panel
                →  design-tokens (+ type-specimen if the face is still open)
                →  layout-rules  →  ux-writing
                →  nielsen-heuristics + walkthrough  →  review  →  before-after ⤾
```

When a surviving prototype must enter an existing design system, insert
`design-frameworks` after `prototype` and before `review`. It is an adapter, not
a new method stage.

The loop matters: `before-after` feeds back into `jtbd` as evidence, so the next
pass starts from what actually happened rather than what you hoped would.

You do not have to run all of it. Each skill stands alone; the corpus is what
makes them compound.

---

## Boundaries worth knowing

- **`type-specimen` chooses a face; `design-tokens` owns it** from the moment it
  becomes a token — including fixing a contrast failure. A specimen that
  corrects a colour by eye has stepped over the line.
- **`ux-writing` owns what a string says; `layout-rules` owns whether the layout
  survives it** once translated. Four rules in the `layout-rules` file are
  wording rules by nature (5, 8, 9, 38) and stay there because that is where the
  avoid-list lives — but `ux-writing` performs the rewrite.
- **`layout-rules` rule 12 says text must clear the contrast bar; `design-tokens`
  measures it.** A review that eyeballs contrast instead of running
  `tokens contrast` is doing it wrong.
- **`persona-review` and `respondent-panel` differ by artifact and attention** —
  a document studied by an expert, versus an artifact glanced at by a stranger.
- **`nielsen-heuristics` judges whether the flow works; `walkthrough` attempts
  the task.** An interface can pass every heuristic and still be impossible to
  get through. Run both; report each finding once.

## What this deliberately does not cover

Typography mechanics, motion recipes, OKLCH palette construction, and
accessibility engineering depth. When those matter, defer to `interfaces`
(`better-typography`, `better-ui`, `better-colors`, `better-accessibility`,
`better-layout`, `better-writing`) if installed, or to `impeccable` for
post-build polish.

A review that cannot cover a domain says **Not reviewed** and names what is
missing. It never improvises the rules from memory.

## The honesty guards

They are the reason to use these skills over an ad-hoc prompt:

- Nothing scores what cannot be observed.
- No confidence percentages on synthetic output — a panel is a rehearsal for
  contact with real people, not a replacement for it, and it refuses to call
  itself market research.
- A verification gap is reported as **Not verified**, never converted into a
  finding.
- The single-evaluator caveat is stated wherever it applies.

## Portability

Core flows name no Claude-only tool. Scripts are Python standard library only.
Anything genuinely Claude Code specific is marked **Claude Code extras:** and is
never load-bearing.

## Conflict precedence, everywhere

The user's explicit words > the skill's ruleset > the project's existing system >
personal taste. A conflict with an existing design system is flagged, never
silently rewritten.

---

Repository, full write-up, and changelog:
<https://github.com/glebis/humane-agentic-design>
