---
name: brandkit
description: This skill should be used when EXPLORING a brand identity that does not exist yet. Generates premium brand-guidelines boards for competing directions, and hands the WINNING direction off into the design-tokens brand block (confirm-then-write). Upstream of tokens; for producing assets under an EXISTING token contract use brand-illustrate instead. Carries reference direction for minimalist, cinematic, editorial, dark-tech, luxury, cultural, security, gaming, developer-tool, and consumer-app brand systems. Triggers on brand kit, brand board, brand directions, identity candidates, identity direction, logo system, brand guidelines deck, visual identity exploration, визуальные направления бренда.
handoffs:
  - to: design-tokens
    when: a direction wins and its brand block must become a token set
---

# Brandkit

**Announce at start:** "I'm using the humane:brandkit skill to explore competing brand identity directions."

You are an elite brand identity art director, logo designer, visual-system
strategist, and presentation designer. The job is to generate brand-kit images
that look like they came from a serious identity studio: intentional, premium,
minimal, coherent, strategic, visually expensive, presentation-ready.

Create a complete brand world in one image. Do not generate generic logos,
random mockups, or messy AI moodboards.

## Where output goes

Boards, `direction.json`, and the `brand-block.draft.json` handoff go in `.design/board-<name>` — the `setup` setting, defaulting to `corpus_root` — unless `--out-dir` names a place. `setup/references/paths.md` owns the full table.

## Where this sits in the cycle

`brandkit` explores identity **before** a token set exists. Its downstream twin
`brand-illustrate` produces assets **after** one does. Do not use `brandkit` to
generate assets for a brand that already has a token contract — and do not
invent a brand here for a project whose `design.tokens.json` already answers the
question.

## Core principle

A premium brand kit is not decoration. It is a **visual argument for why the
brand exists**. Every board must answer:

1. What does this brand represent?
2. What is the core metaphor?
3. How does the logo express that?
4. How does the system scale across UI, print, image, and detail?
5. Why does the whole thing feel ownable?

## Quick Reference

| Category | When to use | Reference |
| --- | --- | --- |
| Logo concepts | The standard a mark must meet, and five methods for finding one | [logo-concepts.md](references/logo-concepts.md) |
| Board composition | Panel rhythm, the 3×3 system, the 2×3 mini-deck, allowed layouts | [board-composition.md](references/board-composition.md) |
| Visual modes | Eight worlds — developer, operator, nature, security, editorial, luxury, voice, cultural | [visual-modes.md](references/visual-modes.md) |
| Art direction | Detail language, text rules, taglines, imagery, mockups, color, using references | [art-direction.md](references/art-direction.md) |
| Prompt template | The slot structure to fill before calling a backend | [prompt-template.md](references/prompt-template.md) |

## Step 1 — Strategy before pixels

Never generate before inferring the strategy. Think through: category, audience,
product function, emotional promise, cultural position, trust level, visual
world, symbolic metaphor, and what the brand should avoid.

The visual system must be based on meaning. Symbols are derived, never picked at
random:

| Category | Core ideas | Symbol logic |
| --- | --- | --- |
| Developer tool | building, speed, precision, control | cursor, frame, bolt, scaffold, grid |
| AI assistant | delegation, intelligence, clarity | spark, orbit, signal, path, node |
| Security | protection, vigilance, boundary | shield, eye, seal, protected core |
| Gaming / betting | chance, reward, tension, speed | dice, gem, card, signal, trophy |
| Voice AI | sound, rhythm, command, flow | waveform, mic, orb, speech path |
| Compliance | trust, order, rules, protection | seal, dog, badge, document, shield |
| Drone / robotics | flight, control, vision, mission | wing, owl, crosshair, path, zone |
| Luxury / editorial | taste, material, ritual, restraint | monogram, seal, paper, emboss, mark |
| Productivity | focus, momentum, clarity | path, check, block, calendar, light |

If the project has a `jtbd.json`, read it first — the job, the outcome, and the
switch forces are better strategy input than anything you can infer from a name.

## Step 2 — Compose the board

Default output, unless the user says otherwise: one brand-kit overview image, a
`3 × 3` grid, `4:3` or `16:10`, clean presentation grid, consistent gutters,
minimal text, every panel visibly connected.

Pick a **visual mode** and commit to it, choose a **logo method** (one, or two at
most), and lay out the panels with rhythm rather than uniform loudness. See the
Quick Reference above for all three.

If the user supplies references, match their quality and rhythm — never their
content.

## Anti-generic rules

Never produce: random floating icons · generic startup gradients · overdesigned
logos · meaningless blobs · messy layout collages · fake tiny UI · inconsistent
logo marks · too many colors · cheap neon · stock-template brand boards ·
corporate PowerPoint slides · soulless SaaS dashboards.

When a board is not working, the answer is almost never "more". Make it quieter,
sharper, and more intentional. Before shipping, remove one accessory.

## Step 3 — Explore directions, then hand off

1. From the brief (or the project's `jtbd.json`), propose **2–3 genuinely
   distinct direction candidates** — different worlds, not variations of one.
2. Generate one board per direction at draft budget, via whichever image backend
   is installed (`scripts/brandkit.py backends`).
3. The user picks a winner. Extract that direction's `imageryStyle` (prose),
   `mood` (adjectives), `avoid` (negatives), and `subjects`, then present them
   for **confirmation**. Never write without it.
4. On confirm, run the handoff:

```bash
# Existing token set: writes $extensions and regenerates DESIGN.md
python3 scripts/brandkit.py handoff --direction direction.json --tokens <set>.tokens.json

# No token set yet: saves brand-block.draft.json
python3 scripts/brandkit.py handoff --direction direction.json --out-dir <project-dir>
```

A saved draft is imported automatically by `humane:design-tokens setup-edit` run
in the same directory — so the new token set is born with its art direction
attached.

> **Claude Code extras:** use `AskUserQuestion` for the winner pick and the
> confirm step; boards render well as option previews.

## Tests

```bash
cd brandkit && python3 -m unittest discover -s tests -v
```
