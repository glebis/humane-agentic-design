# Format contracts

The exact shape of each fidelity rung. `SKILL.md` decides *which* rung runs;
this file says what each one must look like to count.

## Rung 1 — ASCII

A box-drawing sketch in a fenced code block, one block per screen.

- Use `┌ ─ │ └` box-drawing characters, not `+--|`. Monospace alignment is the
  whole medium — check every right edge lines up.
- Max width 80 columns, so it survives any terminal and any chat surface.
- Label regions in place (`[Search…]`, `◉ tab`, `▸ row`), not with a legend.
- One line under each block: what the screen is for, in the words of the job.
- Multiple screens: name each block (`## Screen: Inbox`) and note which control
  on one screen leads to which other, as prose — ASCII does not click.

Nothing else. Shading, pseudo-color, or elaborate ornament on rung 1 is effort
spent on the wrong question.

## Rung 2 — SVG click-dummy

One self-contained `.html` file; each screen is an inline `<svg>` frame;
hotspots are links that switch screens.

**Screen switching is CSS `:target`, no JavaScript.** Each screen is a
`<section id="screen-name">`; hotspots are `<a href="#screen-name">` wrapping
an SVG `<rect>`. Why: the URL then names the current screen, back/forward walk
the history, and the file stays inert — nothing to break, nothing to audit.

The canonical scaffold — use exactly this, not an improvised variant (a naïve
sibling fallback leaves the first screen visible beside the targeted one):

```css
section { display: none; }
section:target { display: block; }
/* no-hash state: show the first screen only when nothing is targeted */
body:not(:has(section:target)) #first-screen-id { display: block; }
```

`:has()` is the baseline (all evergreen browsers since 2023 — fine for a
prototype opened on the reviewer's machine). Escape hatch, only if a target
browser genuinely lacks `:has()`: give the first section `display: block` and
accept that it stays visible under other screens, saying so in the "what is
fake" note.

- Frame each screen at a stated device size (`viewBox="0 0 390 844"` for a
  phone, `0 0 1280 800` for desktop) and say which was chosen.
- Grayscale only: strokes, fills `#e5e5e5`–`#404040`, one accent at most for
  the hotspot affordance. A palette on rung 2 is a `design-tokens` question
  asked too early.
- Real drafted copy in `<text>` elements — no lorem, no `xxxxx`.
- Every hotspot gets a visible affordance (underline, border, or the single
  accent) — an invisible hotspot tests the reviewer's patience, not the flow.
- Dead controls (drawn but not wired) are listed in the "what is fake" note.
- A screen map at the top of the file — plain `<nav>` of links to every
  screen — so a reviewer can jump anywhere without solving the maze first.

Two SVG text traps, both caught in a real build — check for them before
handing the file over:

- **A stylesheet rule beats a `fill` attribute.** `svg text { fill: #262626 }`
  silently overrides every `<text fill="#fff">`, so labels on dark boxes render
  dark-on-dark. Style SVG text through classes (`text.inv { fill: #fff }`),
  never by relying on presentation attributes once a stylesheet exists.
- **SVG text neither wraps nor clips.** A string longer than its box runs
  straight over the neighbouring element. Estimate width (~0.5 × font-size per
  character) against the container before committing a string; break long lines
  into stacked `<text>` elements yourself, and re-check every string a copy
  rewrite lengthens — a rewrite that fixes the wording and overflows the box
  has traded one defect for another.

## Rung 3 — HTML

One self-contained `.html` file per prototype: inline `<style>`, inline
`<script>` only if an interaction under test needs it, system font stack, no
CDN, no build step, no external requests of any kind.

Two tiers — the user chooses (`SKILL.md` owns the ask):

**Wireframe tier**

- Grayscale, `font-family: system-ui`, borders over shadows, no brand.
- Real drafted copy and realistic data shapes (a table with 3 plausible rows,
  not one row of "Item name").
- Deliberately un-designed: the tier exists so nobody argues about the color
  of a button whose existence is still in question.

**Token-faithful tier**

- Only when a compiled `design-tokens` CSS exists in the project. Inline a copy
  of it (self-containment beats linking) and render every color, radius, space,
  and type value from those variables — zero hard-coded design values.
- If a needed token does not exist, use the nearest existing one and flag the
  gap for `design-tokens`; do not mint a value.
- Contrast is still not this skill's call: if a pairing looks doubtful, name it
  for `tokens contrast` rather than eyeballing a fix.

Both tiers: multiple screens use the same `:target` mechanism as rung 2 unless
the interaction under test requires state that `:target` cannot hold — then the
minimum JS that holds it, and the script is listed in the "what is fake" note
as prototype scaffolding, not proposed implementation.
