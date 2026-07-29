---
name: layout-rules
description: This skill should be used when designing, building, or reviewing any layout, dashboard, data-dense tool UI, viewer, or admin interface. Loads a battle-tested avoid-list of 39 rules (structure, footers/metrics, tables, color/contrast, URL state, JS traps, accessibility/touch, i18n/theming, de-slop) distilled from a real build/audit cycle. Triggers on "design a layout", "build a dashboard", "make a viewer/tool UI", "review this UI", "какие правила дизайна", or before writing any HTML/CSS for a tool-like interface.
---

# Layout Rules

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
