---
name: layout-rules
description: This skill should be used when designing, building, or reviewing any layout, dashboard, data-dense tool UI, viewer, or admin interface. Loads a battle-tested avoid-list of 39 rules (structure, footers/metrics, tables, color/contrast, URL state, JS traps, accessibility/touch, i18n/theming, de-slop) distilled from a real build/audit cycle. Triggers on "design a layout", "build a dashboard", "make a viewer/tool UI", "review this UI", "какие правила дизайна", or before writing any HTML/CSS for a tool-like interface.
---

# Layout Rules

**Announce at start:** "I'm using the humane:layout-rules skill to check this layout against the defect avoid-list."

A defect-class avoid-list for tool/dashboard UIs. Every rule is a bug or design smell actually caught in a real build-and-audit cycle — treat them as hard constraints, not suggestions.

## Usage

1. Read the full ruleset: `layout-design-rules.md`, bundled next to this file (single source of truth — do not duplicate it here).
2. **Before designing**: apply sections «Structure & hierarchy», «Color & contrast», «De-slop» as constraints in the design plan. Say explicitly which rules shaped the plan.
3. **While building**: enforce «Footers, metrics, copy», «Tables & lists», «State & navigation», «Interaction correctness», «Accessibility & touch», «i18n & theming».
4. **After building**: run the post-build checklist below; screenshot-test in a real browser (rule 29) on both themes and on an empty/minimal dataset (rule 30).

## Post-build checklist (the ones most often violated)

- [ ] Zero left-border accent rails (rule 1); zero eyebrow caps-labels (rule 2)
- [ ] Third heading level actually exists and is distinguishable (rule 3)
- [ ] Every verdict/summary line adds a conclusion or names a linked entity (rules 5, 8)
- [ ] Every metric is informative or clickable-to-filter (rules 6–7)
- [ ] Tables sortable + filterable, tabular-nums (rule 10)
- [ ] Faintest text token clears 4.5:1 on both themes (rule 12)
- [ ] Every app location has a URL; reload restores it exactly (rule 16)
- [ ] `[hidden]{display:none}` for every display-classed component; close/reset logic before early returns in delegated handlers (rules 18–19)
- [ ] SVG interactives: focus ring, keyboard activation, tap-tooltips (rules 22–23)
- [ ] Both locales key-parity if i18n exists (rule 27)

## Conflict precedence

The user's explicit words > this ruleset > project's existing system > personal taste. If a rule conflicts with an existing design system in the repo, flag it, don't silently rewrite.

## What this skill does not own

Each rule lives in one place. When a concern crosses a boundary, name the handoff
rather than restating the rule here.

| Concern | Owner |
| --- | --- |
| Measuring a color pair, and changing it | `design-tokens` (`tokens contrast`) — rule 12 says *that* it must clear the bar; the command says *whether* it does |
| The source wording of any user-facing string | `ux-writing` — rules 5, 8, 9, 38 defer to it on wording |
| Whether the flow is usable at all | `nielsen-heuristics` |
| Art direction, palette, and type choice | `design-tokens` and `brandkit` |
| Typography mechanics, motion recipes, ARIA depth | Not covered here. If `interfaces` (`better-typography`, `better-ui`, `better-accessibility`) is installed, defer to it; otherwise say the domain was not reviewed rather than improvising |

## Review Output Format

When reviewing an existing UI rather than building one, report findings in this
shape so the result composes with the other humane review skills.

| Severity | Location | Before | After | Why |
| --- | --- | --- | --- | --- |
| MEDIUM | `src/Card.tsx:28` | `border-left: 3px solid var(--accent)` | Background tint + leading color dot on the label | Rule 1: left-border accent rails |

- **Severity** — `HIGH` blocks content or an action, loses state, or breaks a
  supported viewport; `MEDIUM` harms hierarchy, adaptability, or correctness;
  `LOW` is isolated polish.
- **Location** — `path/to/file:line`, or the exact screen and element.
- **Why** — name the numbered rule.

One root cause is one row, listing every affected location. Cap at 15 findings;
never pad — no findings is a valid result. Then:

- **Considered but Rejected** — 2–5 real candidates you inspected and chose not
  to report, with the reason (the project's system permits it, the deviation is
  intentional, the evidence is thin).
- **Verification** — which rules you actually checked and how. Rule 29 means a
  real browser screenshot on both themes; rule 30 means an empty dataset too.
  Anything unchecked is listed as **Not verified**, never converted into a
  finding.
- **Verdict** — `Block`, `Needs changes`, or `Approve`.

Reviews are read-only unless the user also asked for the fixes to be applied.
