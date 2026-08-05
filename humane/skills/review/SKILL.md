---
name: review
description: User-invoked review that coordinates the humane review skills — layout-rules, ux-writing, nielsen-heuristics, walkthrough, design-tokens contrast — into one prioritized verdict, and marks the domains it cannot cover instead of improvising them. Supports quick and full modes. Identifies the artifact first and runs a reduced document pipeline for a README, PRD, or docs page rather than stretching a UI pipeline over it. Use when explicitly asked for a holistic review of a screen, flow, feature, product, or document. Triggers on humane review, full review, review the whole thing, holistic UI audit, cross-skill design review, "review this properly", "полный ревью".
---

# Review the whole thing, once

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
runtime or visual judgment decides the answer. Run `tokens contrast` per theme
rather than eyeballing color. Report the exact command or interaction and the
observed result.

If a check could not be run, label it **Not verified** and state what remains.
**Never convert a verification gap into a finding.**

## 10. Do not mutate

A review request is read-only. Do not edit source unless the user also asks for
the fixes. When they do, keep the consolidated report as the change scope and
re-run the relevant verification afterwards.

## Output

### Scope and coverage

Mode, exact scope, stack and conventions, and any boundary. Then:

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
