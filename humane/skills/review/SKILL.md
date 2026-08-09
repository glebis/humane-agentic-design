---
name: review
description: User-invoked review that coordinates the humane review skills — layout-rules, ux-writing, nielsen-heuristics, walkthrough, design-tokens contrast — into one prioritized verdict, and marks the domains it cannot cover instead of improvising them. Supports quick and full modes. Identifies the artifact first and runs a reduced document pipeline for a README, PRD, or docs page rather than stretching a UI pipeline over it. Use when explicitly asked for a holistic review of a screen, flow, feature, product, or document. Triggers on humane review, full review, review the whole thing, holistic UI audit, cross-skill design review, "review this properly", "полный ревью".
accepts:
  - from: brand-illustrate
orchestrates:
  - layout-rules
  - ux-writing
  - nielsen-heuristics
  - walkthrough
  - design-tokens
---

# Review the whole thing, once

**Announce at start:** "I'm using the humane:review skill to run the review cycle and consolidate one verdict."

Five separate audits stapled together is not a review — it is five reports the
reader has to reconcile. This skill runs the domains, lets each owning skill
apply its own rules, and consolidates the evidence into one ranked verdict.

**This skill owns orchestration only.** It never restates or overrides a domain
rule. Structure and defect classes belong to `layout-rules`; wording to
`ux-writing`; usability principles to `nielsen-heuristics`; task completion to
`walkthrough`; color measurement to `design-tokens`. If you find yourself
writing a rule here, it belongs in the skill that owns it.

## 1. Identify the artifact before anything else

This pipeline is built for an interface. Given something else it will happily
stretch — returning a table of `N/A` and one strained domain — so decide what
you are holding first, and say so in the output.

| Artifact | What to run |
| --- | --- |
| Screen, flow, feature, running app, UI source | The full pipeline below |
| **Document** — README, docs page, PRD, spec, proposal | The **document pipeline**: `ux-writing` for the prose, `layout-rules` for structure and hierarchy only (rules 1–4, 39), plus `persona-review` if the reader's objections matter more than the wording. Skip `walkthrough`, `nielsen-heuristics`, and contrast — mark them `N/A (not an interface)`, not `Clear` |
| **Copy in isolation** — a tagline, a hero, brand values | Not a review. Hand it to `respondent-panel`, and to `ux-writing` for the rewrite |
| **Spec for an unbuilt interface** | `nielsen-heuristics` design-risk mode, which produces unscored risk flags. Never severity-score a thing that does not run |
| Token set with no UI | `design-tokens contrast` alone |

A document still gets the full contract — findings table, considered-but-rejected,
verification, verdict — just over fewer domains. State the reduced pipeline in
Scope and Coverage so the reader knows what was and was not possible.

**Why 1–4 and 39, and not 5, 8, 9, 38.** Those four are wording rules living in
the `layout-rules` file — "a summary line must add a conclusion", "link the
entity", "empty states teach", "copy slop". `ux-writing` owns wording, and it
already covers each of them. Routing them here would review the same sentence
twice under two owners and risk two different rewrites of it. Send anything
about what a string *says* to `ux-writing`; keep `layout-rules` on structure,
hierarchy, and the boldness budget.

**If the artifact is a document that describes an interface** (a README for a UI
tool, a design doc), review the document *as a document*. Do not review the
interface it describes from its description alone — that is a claim you cannot
evidence.

## 2. Resolve scope and mode

Infer the screen, flow, feature, document, or repository scope from the request
and the workspace. State the resolved scope in the output. Default to `full`.

| Mode | Coverage | Finding cap |
| --- | --- | --- |
| `quick` | The primary path and highest-traffic states; report `HIGH` and `MEDIUM` only | 5 |
| `full` | The whole requested scope across every available domain, including empty, loading, error, and narrow-width states where they exist | 15 |

In `full` mode on a runnable interface, the **mobile device tier is part of the
scope**: the primary flow is driven at the mobile tier per `walkthrough`'s
`references/driven.md` (which owns the tool ladder, device matrix, and
screenshot contract). If no browser tool rung is available, the mobile tier is
reported **Not reviewed** in Scope and Coverage — never silently narrowed to
desktop.

If the scope is too large to inspect credibly, narrow it to the highest-traffic
complete flow and **state the boundary**. Never imply that uninspected surfaces
were reviewed.

## 3. Recon before judgment

Identify the stack, styling system, component library, token file, supported
viewports, and any preview or test command. Read the project's `jtbd.json` if
one exists — it tells you which flows matter and which outcomes are underserved,
and a review that ranks findings without it is ranking by taste.

Follow the project's established conventions. Conflict precedence, as everywhere
in humane: the user's explicit words > the skill's ruleset > the project's
existing system > personal taste.

## 4. Run the domains in this order

Foundational failures first, so polish never hides them:

| # | Domain | Owner | Skip when |
| --- | --- | --- | --- |
| 1 | Task completion | `walkthrough` | There is nothing operable to attempt |
| 2 | Usability principles | `nielsen-heuristics` | — |
| 3 | Structure and defect classes | `layout-rules` | — |
| 4 | Interface copy | `ux-writing` | — |
| 5 | Color and contrast | `design-tokens` (`tokens contrast`) | The project has no token set — then report contrast **Not measured**, naming the pairs you could not check. Never substitute an eyeball estimate for a measurement |

Apply each owner's principles, but **ignore its standalone Review Output
Format** — this skill owns the final response, and its format, severity scale,
consolidation rules, and cap take precedence.

`respondent-panel` is deliberately **not** in this pipeline. It costs real
tokens, needs the user to confirm a panel first, and produces reactions rather
than findings. Offer it as a follow-up when the review turns up copy problems;
never fold its output into a findings table.

### Inline, or fanned out

Run the domains **inline** by default — one context, in the order above. Simple,
portable, and correct for `quick` mode or a small scope.

Run them **fanned out** when the scope is large enough that inline would fill the
context before consolidation: a `full` review of a runnable interface, a driven
walkthrough across two device tiers, or any scope where the five domains' rules
plus the artifact plus the evidence will not comfortably coexist. Each domain
runs in its own context and returns **only its findings table** — not its
reasoning, not the artifact, not its screenshots.

**The rationale this mode shipped with is not supported by the one test of it.**

It was introduced on an argument: a host that compacts does not fail, it
summarizes and continues, so evidence from an early domain could be summarized
away while the *impression* of coverage survived to consolidation — and the
review would then report `Clear` over a domain whose evidence it no longer held.

Measured, that did not happen. On a 60-pair page carrying 24 planted contrast
defects, an inline review found **all 24**, with a position bias of 0.500 —
perfectly even across the document, no decay toward the tail. Fanning out
matched it and did not beat it (`evals/fanout/`, preregistered, n=1).

So do not reach for fan-out expecting evidence to survive that would otherwise
be lost. That benefit is **undemonstrated**. What the same run did show is
narrower and partly an artifact of how the arms were set up: the fanned-out
domains reported less outside their own lane — precision 1.00 against 0.83,
padding 1 against 2, and routing 1.00 against 0.67, the last of which is close
to given, since each domain agent was told which skill it was applying.

Fan out when the scope is genuinely too large for one pass, or when you want
each domain's findings kept in its own lane. Do not fan out because this file
once claimed it rescues evidence. If a larger artifact ever does show decay,
that is worth measuring and saying — one fixture at one size is not a general
result, and it is the claim, not the mode, that failed here.

Two constraints on how to fan out:

1. **`walkthrough` runs first, and alone.** It is stateful — it drives a live
   browser across ordered steps, and its device matrix and screenshot contract
   belong to `references/driven.md`. It may be one subagent that owns the whole
   walk; it may never be split per step, and it may not run concurrently with
   another domain that drives the same interface. The other four have no shared
   state and fan out together once it returns.
2. **A silent domain is `Not reviewed`, never `Clear`.** If a domain's run dies,
   returns nothing, or returns something that is not a findings table, record it
   as `Not reviewed` and name what happened. Absence of findings from a domain
   that never reported is not absence of findings.

> **Claude Code extras:** launch the four independent domains as subagents in a
> single message so they run concurrently, each told to apply its owning skill
> and return the findings table alone.
>
> **On other agents:** fan out if the host has an equivalent; otherwise run
> inline and narrow the scope per §2 rather than letting a full review outgrow
> one context. Say which you did — a fanned-out review and an inline one over a
> narrowed scope are not the same claim.

## 5. Mark what you did not cover

If an owning skill is unavailable, mark that domain **Not reviewed**, name the
missing skill, and continue. Do not recreate its rules from memory or substitute
a neighboring skill.

The same applies to the domains humane does not own at all — typography
mechanics, motion, accessibility engineering, OKLCH palette construction. If
`interfaces` (`better-typography`, `better-ui`, `better-accessibility`,
`better-colors`) is installed, run it for those and attribute the findings. If
it is not, say so:

> Craft domains (typography, motion, a11y depth): **Not reviewed** — install
> `interfaces@interfaces` for these.

An honest gap is worth more than a confident guess. Never claim holistic
coverage you did not have.

## 6. Require evidence

Every finding cites `path/to/file:line`, a screenshot, or the exact screen and
element. Do not report a code-level finding from appearance alone, or a visual
finding from source alone when runtime decides the result. Where the corpus
supports the ranking, cite the evidence id (`[Q2]`) or the outcome.

### Carry the locator, not the payload

A locator is durable; a payload is not. `src/Nav.tsx:42` and
`walks/2026-08-08-signup/step-03-mobile.png` survive summarizing, hand across a
subagent boundary intact, and can be re-read on demand. The file's contents and
the image itself cannot — they are the first thing a compacting host drops, and
once dropped they cannot be recovered from the summary.

So: read what you need to judge a finding, write down the locator, and let the
payload go. Never hold a screenshot in context to support a claim you will make
several domains later — cite its path instead and re-open it if consolidation
turns out to need it. When a domain runs fanned out, its findings table crosses
back as locators for exactly this reason, and a domain that returns prose
instead of locators has produced something this skill cannot verify or
consolidate.

## 7. Rank by user impact

One shared scale across all domains:

- `HIGH` — blocks a task, misleads, hides content or controls, risks data loss,
  or repeats systemically.
- `MEDIUM` — meaningfully harms comprehension, efficiency, adaptability, or
  consistency.
- `LOW` — isolated polish. `full` mode only.

Within a severity, rank by reach and leverage: a token or shared-component fix
outranks the same symptom in one leaf. An underserved outcome in the corpus
outranks a well-served one.

## 8. Consolidate

One root cause is one finding, listing every confirmed location — not a row per
occurrence. When two skills surface the same issue, assign it to the skill that
**owns the underlying rule** (see the repo `CLAUDE.md` ownership map) and note
secondary effects in the Why cell. Report it once.

Never pad to reach the cap. A short review, or none, is a valid result.

## 9. Verify, and say what you could not

Run the safe checks the project offers. Inspect the rendered interface when
runtime or visual judgment decides the answer — driving and screenshots follow
`walkthrough`'s `references/driven.md`, and the screenshot filenames are the
evidence locators. Run `tokens contrast` per theme rather than eyeballing
color. Report the exact command or interaction and the observed result.

If a check could not be run, label it **Not verified** and state what remains.
**Never convert a verification gap into a finding.**

## 10. Do not mutate

A review request is read-only. Do not edit source unless the user also asks for
the fixes. When they do, keep the consolidated report as the change scope and
re-run the relevant verification afterwards.

## Output

### Scope and coverage

Mode, exact scope, stack and conventions, any boundary, and whether the domains
ran **inline** or **fanned out** — the reader is owed the difference, because a
fanned-out review consolidated locators while an inline one held the evidence
itself. Then:

| Domain | Evidence inspected | Result |
| --- | --- | --- |
| Task completion | Task walked, states reached | Findings count · `Clear` · `Not reviewed` · `N/A` |

List every domain, including the ones humane does not own. The four results are
not interchangeable, and collapsing them is how a review overstates itself:

- **Findings count** — inspected, and this many things were found.
- **`Clear`** — inspected, nothing actionable. An assertion about the artifact.
- **`Not reviewed`** — *could* have applied here, but was not run. Must say why
  (skill unavailable, no runtime, out of scope). An admission of a gap.
- **`N/A`** — does not apply to this artifact at all, e.g. task completion on a
  README. Write it as `N/A (not an interface)`. Never `Clear`: nothing was
  inspected, so there is nothing to declare clean.

### Findings

| # | Severity | Domain | Location | Before | After | Why |
| --- | --- | --- | --- | --- | --- | --- |

One row per root cause, ordered by severity then reach. Domain is the owning
skill's name. Respect the cap. With no findings, omit the table and say "No
actionable findings."

### Considered but rejected

1–3 candidates in `quick`, 2–5 in `full`:

| Location | Candidate | Rejected because |
| --- | --- | --- |

Real candidates inspected during the review, never invented filler. If the scope
held fewer borderline calls, list those that exist and say so.

### Verification

Each check, the exact command or steps, and the observed result. Separate what
passed from what is **Not verified**.

### Verdict

Exactly one:

- `Block` — one or more `HIGH` findings remain.
- `Needs changes` — only `MEDIUM` or `LOW` remain.
- `Approve` — nothing actionable remains **and** the claimed coverage was
  verified.

Carry forward the caveats the domain skills attach: a single evaluator finds
roughly a third of usability problems, and an analytical walkthrough is not a
usability test. `Approve` means "clean in this review", never "ready to ship".
