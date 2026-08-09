---
name: using-humane
description: Route a design task to the right humane skill, and after any humane skill finishes, name the next one from the declared handoff graph instead of guessing. Reads the `handoffs:` / `accepts:` / `orchestrates:` keys in each skill's frontmatter, so the route is data, not recollection. Use at the start of design work when it is not obvious which skill owns the task, and at the end of any humane skill to find what it hands to. Not for non-design work. Triggers on where do I start, which humane skill, what comes next, what should I run after, humane cycle, design cycle order, "I finished the jtbd interview now what", "какой скилл дальше".
---

# Using humane

**Announce at start:** "I'm using the humane:using-humane skill to route this to the skill that owns it."

## Scope

This skill routes design work. It does **not** claim authority over unrelated
tasks — a bug fix, a deploy, or a shell question has no humane owner, and
routing one here is a false positive. If nothing below matches, say so and move
on rather than stretching a design skill over a non-design task.

## The two questions it answers

**"Where do I start?"** — match the intent to an entry point (table below).

**"I just finished X, what now?"** — do not recall the cycle from memory. Ask
the graph:

```bash
python3 scripts/graph.py --from layout-rules   # what it hands to, and when
python3 scripts/graph.py --to ux-writing       # who hands in here, and when
python3 scripts/graph.py                       # the whole graph
python3 scripts/graph.py --mermaid             # the graph as a diagram
```

The script reads the frontmatter of every skill in the plugin. It is stdlib-only
and has no dependencies, so it runs anywhere the plugin is checked out.

## Entry points

| The user says | Start with | Not with |
| --- | --- | --- |
| "something's missing / nothing works / fresh machine" | `humane:setup` | anything else — it diagnoses first |
| "what should I build", "what are people hiring this for" | `humane:jtbd` | a review skill; there is nothing to review yet |
| "mock this up", "show me the flow", "wireframe this" | `humane:prototype` | `humane:design-tokens` — the structure is not settled yet |
| "we need a brand / an identity" | `humane:brandkit` | `humane:design-tokens` — the tokens do not exist yet |
| "set up tokens", "compile to CSS", "check contrast" | `humane:design-tokens` | `humane:layout-rules`, which only flags the pair |
| "pick a font", "does this font have Cyrillic" | `humane:type-specimen` | `humane:design-tokens`, until a family is chosen |
| "generate on-brand images" | `humane:brand-illustrate` | `humane:brandkit`, which explores rather than produces |
| "what should this button say", "rewrite this error" | `humane:ux-writing` | — |
| "how does this land", "test this tagline" | `humane:respondent-panel` | `humane:persona-review` — strangers, not experts |
| "review this PRD as an engineer / investor" | `humane:persona-review` | `humane:respondent-panel` — experts, not strangers |
| "review this UI", "check this dashboard" | `humane:layout-rules` | — |
| "usability audit", "heuristic evaluation" | `humane:nielsen-heuristics` | — |
| "can someone actually complete this", "test this flow" | `humane:walkthrough` | `humane:nielsen-heuristics` — attempt, not inspect |
| "what's the transformation" | `humane:before-after` | — |
| "review this properly", "full review", "holistic audit" | `humane:review` | any single domain skill |

When more than one row matches, **`humane:review` wins** — it is the one skill
allowed to run several domains and consolidate them into a single verdict. When
the user names a skill explicitly, their words win over this table.

## What the graph keys mean

Three keys, three different relationships. Do not collapse them.

- **`handoffs:`** — a peer route across an ownership boundary, with the `when:`
  that opens it. `humane:layout-rules` hands a contrast pair to
  `humane:design-tokens` because it does not own the fix.
- **`accepts:`** — the receiving skill's acknowledgement of that route. Every
  handoff has one; the repo's test suite fails the build if it does not.
- **`orchestrates:`** — a call, not a handoff. `humane:review` runs its domain
  skills and consolidates their findings. No reciprocity is owed, and the
  domain skills are unaware of it.

Cycles are legal and deliberate. `humane:ux-writing` and
`humane:respondent-panel` route both ways: writing hands copy out for reactions,
reactions hand the rewrite back.

## Honesty guards

- **A handoff is a condition, not an instruction.** Each edge carries a `when:`.
  If the condition did not occur, the cycle ends here — do not run the next
  skill for completeness. A `humane:layout-rules` pass that found no contrast
  issue does not hand to `humane:design-tokens`.
- **Ask before continuing.** A handoff names what *could* come next. The user
  decides whether it runs.
- **The graph is not coverage.** Following every edge is not a full review, and
  saying "I ran the cycle" is only true for the skills that actually ran. Name
  the ones that did not.
- **Never invent an edge.** If `scripts/graph.py` shows no route, there is no
  route. Add one to the frontmatter — on both sides — rather than improvising it
  in conversation.

> **Claude Code extras:** the skills are invoked as `humane:<skill>`. Announce
> each one as it starts, so a multi-skill cycle narrates itself.
