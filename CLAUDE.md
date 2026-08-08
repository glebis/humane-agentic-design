# CLAUDE.md

Guidance for agents working in this repository.

## What this repository is

`humane` — a design *method* cycle packaged as a Claude Code plugin and its own
single-entry marketplace, portable to other agents. It covers the work around an
interface: what to build (`jtbd`), for whom (`persona-review`,
`respondent-panel`), under which system (`design-tokens`) and constraints
(`layout-rules`), in which words (`ux-writing`), audited (`nielsen-heuristics`)
and proven (`before-after`). Ring 2 (`brandkit`, `brand-illustrate`) handles
visual identity.

Skills live in `humane/skills/<name>/SKILL.md`; the bundled agent is
`humane/agents/synthetic-respondent.md`. Bump `version` in
`humane/.claude-plugin/plugin.json` when plugin users should receive an update,
and add the entry to `CHANGELOG.md` in the same commit — its "How to write an
entry" section owns the format (capability heading, numbered steps, `### Fixed`
lists, and what never gets documented).

## Rule ownership

Each rule lives in exactly one skill. Other skills reference it by skill name in
backticks and name only the handoff — never restate or override it.

| Skill | Owns |
| --- | --- |
| `setup` | Environment and configuration: the six settings, their resolution order, dependency checks, and the install commands for each gap. Owns no method rules. |
| `jtbd` | The corpus: jobs, switch forces, ODI outcomes, evidence ledger, granularity and jargon gates. Every downstream claim cites it. |
| `persona-review` | Expert stakeholder critique of a **document** that is meant to be studied |
| `respondent-panel` | Gut reactions from strangers to a **user-facing artifact**, in isolated contexts. Never rewrites. |
| `design-tokens` | The token set: DTCG structure, resolution, CSS/DESIGN.md export, the brand block, and **all color measurement and remediation** (`tokens contrast`) |
| `type-specimen` | Typeface **selection**: the specimen page, its ten-slot copy contract, script and glyph coverage checks, and what a specimen may and may not conclude. Owns no token. |
| `layout-rules` | Structural and interaction defect classes for tool/dashboard UIs, and the de-slop avoid-list |
| `ux-writing` | The source wording of every user-facing string, and what each string must accomplish — including documentation prose (README, docs, release notes) |
| `nielsen-heuristics` | Formal usability inspection against the 10 heuristics, with severity and evidence locators |
| `walkthrough` | Task completion — whether a specific person with a specific job can get through a specific interface. Also owns the **driven-mode procedure** (`references/driven.md`): browser tool ladder, device matrix, screenshot evidence contract, mode gate |
| `review` | Orchestration only: scope, mode, domain order, consolidation, coverage honesty, and the single final verdict. Owns no domain rules. |
| `before-after` | The felt transformation claim, and the proof that a change worked |
| `brandkit` | Identity **exploration** — competing directions for a brand that does not exist yet |
| `brand-illustrate` | Asset **production** under an existing token contract |

Cross-boundary cases, resolved:

- `layout-rules` rule 12 states that text must clear the contrast bar;
  `design-tokens` owns measuring the pair and changing the color. A review that
  eyeballs contrast instead of running `tokens contrast` is doing it wrong.
- `ux-writing` owns what a string says; `layout-rules` owns whether the layout
  has room for it once translated, and how it renders. Several rules in the
  `layout-rules` file are wording rules by nature (5, 8, 9, 38 — summary lines,
  linking named entities, empty states, copy slop). They stay in that file
  because that is where the avoid-list lives, but **`ux-writing` owns them**:
  it performs the rewrite and reports the finding. A review that routes them to
  `layout-rules` reviews the same sentence twice under two owners.
- `nielsen-heuristics` judges whether the flow works; `layout-rules` judges
  whether the implementation contains known defect classes. An issue that is
  both is reported once, by the skill that owns the underlying rule.
- `respondent-panel` reports how copy lands; `ux-writing` performs the rewrite.
  Respondents never suggest alternatives — that is the point of them.
- `brandkit` runs before a token set exists and hands off into it;
  `brand-illustrate` runs after one exists and reads from it.
- `type-specimen` chooses a typeface and stops; `design-tokens` owns the family
  from the moment it becomes a token. The specimen page reports WCAG and APCA
  for the pair being previewed, but remediation is `tokens contrast` — a
  specimen that "fixes" a colour by eye has stepped over the line.
- `ux-writing` owns every string a specimen sets. `type-specimen` picks *which*
  strings prove something about a font and how long they must be; it never
  invents wording that the corpus or the product already has.
- `persona-review` and `respondent-panel` differ by artifact and by attention:
  a document studied by an expert vs. an artifact glanced at by a stranger.
- `nielsen-heuristics` inspects an interface against principles; `walkthrough`
  attempts a task on it. An interface can pass every heuristic and still be
  impossible to get through, and vice versa — run both, report each finding once
  under the skill that owns it.
- `walkthrough` owns *how* a live interface is driven — tool ladder, device
  tiers, screenshots (`references/driven.md`). `review` and
  `nielsen-heuristics` cite that file; a second driving procedure written
  anywhere else is a bug. What the mobile tier *finds* still routes to its
  owner: tap targets and horizontal scroll to `layout-rules`, contrast to
  `design-tokens`.
- `review` never restates a rule. When it needs one, it names the owner. A rule
  written into `review` is a bug.

## What we deliberately do not cover

Typography mechanics, motion recipes, OKLCH palette construction, and
accessibility engineering depth are **not** in scope. When those matter, defer
to `interfaces` (`better-typography`, `better-ui`, `better-colors`,
`better-accessibility`, `better-layout`, `better-writing`) if installed, or to
`impeccable` for post-build polish. A review that cannot cover a domain says
**Not reviewed** and names what is missing; it never improvises the rules from
memory or claims holistic coverage it did not have.

## Authoring conventions

- **Every skill announces itself.** One line after the H1 —
  `**Announce at start:** "I'm using the humane:<skill> skill to <purpose>."` —
  so the cycle narrates itself, matching the convention Superpowers established
  in the ecosystem.
- **Frontmatter `description` is the discovery surface.** One sentence on what
  the skill does, then "Use when…", then a `Triggers on …` keyword list. Update
  the triggers whenever scope changes.
- **Progressive disclosure.** `SKILL.md` is the entry point and should stay
  readable in one sitting; put recipes, lookup tables, and long-form depth in
  `references/*.md` and route to them from a Quick Reference table. Add a
  reference file only when it carries depth beyond the principle statements, not
  to restate them at length.
- **Prescribe exactly, and say why.** "Always `scale(0.96)`, never below `0.95`
  — anything lower reads as exaggerated" beats "use a subtle scale". Where a
  value is a heuristic rather than a requirement, name the escape condition.
- **Honesty guards are load-bearing.** Do not score what cannot be observed; do
  not attach confidence percentages to synthetic output; do not convert a
  verification gap into a finding; state the single-evaluator caveat where it
  applies. These are the reason to use these skills over an ad-hoc prompt.
- **Portability.** Core flows name no Claude-only tool — say "ask the user", not
  a tool name. Scripts are Python standard library only. Genuinely Claude Code
  specific capabilities go under a "**Claude Code extras:**" blockquote.
- **Conflict precedence**, everywhere: the user's explicit words > the skill's
  ruleset > the project's existing system > personal taste. Flag a conflict with
  an existing design system; never silently rewrite it.

## The shared review contract

Every skill that reviews rather than produces (`layout-rules`,
`nielsen-heuristics`, `ux-writing`, `walkthrough`) ends with the same shape, so
`review` can consolidate them. When `review` orchestrates, the domain skills hand
it findings and let its format, severity scale, cap, and verdict win:

1. **Findings** — one table: Severity | Location | Before | After | Why. One
   root cause is one row, listing every affected location. Cite
   `path/to/file:line` or the exact screen and element. Cap at 15 (5 for a quick
   pass) and never pad — no findings is a valid result. A skill may add columns
   **standalone** when it carries information no other domain has — `walkthrough`
   adds Step(s) and Question — provided it says so and drops them under `review`,
   whose format wins. It may never remove or rename one of the five.
2. **Considered but Rejected** — 2–5 real candidates inspected and not reported,
   with the reason. Not filler.
3. **Verification** — what was actually checked, and how. Anything unchecked is
   **Not verified**, never a finding.
4. **Verdict** — exactly one of `Block`, `Needs changes`, `Approve`.

Reviews are read-only unless the user also asked for the fixes to be applied.

`respondent-panel` and `before-after` are deliberately **exempt**: a panel is not
a vote and must not produce a verdict, and a transformation grid is a claim, not
an audit.

## Tests

The repo-level suite checks the frontmatter contract across every skill — YAML
that parses, `name` matching its directory, a `Triggers on` list, a description
under the ceiling, and no `/skill` invocations for skills that ship as
`humane:skill`. Run it after touching any `SKILL.md`, including the description.

```bash
python3 -m pytest tests/ -v

cd humane/skills/type-specimen && PYTHONPATH=scripts python3 -m pytest tests/ -v
cd humane/skills/design-tokens && PYTHONPATH=scripts python3 -m pytest tests/ -v
cd humane/skills/brand-illustrate && python3 -m unittest discover -s tests -v
cd humane/skills/jtbd && python3 -m pytest tests/ -v
```
