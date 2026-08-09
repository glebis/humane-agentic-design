---
name: prototype
description: Turn a captured job into something a person can look at and click before any design system exists — an ASCII sketch, an SVG click-dummy with hotspots linking screens, or a self-contained HTML file. Picks the cheapest fidelity that answers the open question and escalates only when asked or when the question demands it. Runs after jtbd and before design-tokens; its output is a first-class artifact for respondent-panel, walkthrough, and before-after. Use when the user wants to see or try an idea before committing to structure, tokens, or copy. Triggers on prototype, wireframe, mockup, click-dummy, sketch the screens, "what would this look like", "mock this up", "show me the flow", "прототип", "макет".
handoffs:
  - to: design-tokens
    when: the structure has survived a look or a click-through and needs a system to render under
  - to: respondent-panel
    when: the prototype needs gut reactions from strangers, not from its maker
  - to: walkthrough
    when: a job from the corpus needs attempting on the click-dummy
  - to: ux-writing
    when: drafted prototype strings are about to outlive the prototype
accepts:
  - from: jtbd
---

# Prototype

**Announce at start:** "I'm using the humane:prototype skill to make this idea lookable and clickable at the cheapest fidelity that answers the question."

A prototype exists to answer exactly one open question — is this the right
structure, does the navigation make sense, does the screen read at a glance —
before anything expensive is committed. This skill produces the cheapest
artifact that answers that question and stops.

## Where it sits

After `jtbd`, before `design-tokens`. The corpus says what job the interface
serves; the prototype proposes a structure for it; only a structure that
survives being looked at or clicked through deserves a token set. A prototype
built after the token set exists is a render, not a prototype — that work
belongs to the build itself, reviewed by `layout-rules`.

## The fidelity ladder

Three formats, in escalation order. Name the open question first, then pick the
lowest rung that can answer it. The user's explicit format request always wins.

| Rung | Format | Answers | Never claims |
| --- | --- | --- | --- |
| 1 | **ASCII** — box-drawing sketch in a fenced code block | Is this the right structure? What goes where? | Proportion, color, feel |
| 2 | **SVG click-dummy** — screens as SVG frames, hotspots linking them, in one self-contained HTML file | Does the navigation make sense? Can you get from A to B? | Visual polish, real rendering behavior |
| 3 | **HTML** — real markup and CSS, self-contained file | Does the screen read? Do the interactions feel right? | That it is the product |

Escalate only when the current rung's question is settled or when the open
question lives on a higher rung. Do not skip rung 1 for a new structure — an
ASCII sketch that is wrong costs one message to redraw; an HTML page that is
wrong costs an argument.

**HTML fidelity is the user's choice.** Before building rung 3, ask which tier:

- **Wireframe** — grayscale, system font, real copy, no brand. Default when no
  token set exists (the normal case at this point in the cycle).
- **Token-faithful** — reads the project's compiled `design-tokens` CSS if one
  exists and renders under it. Offer this only when the tokens exist; never
  invent a palette to fake it — inventing one is `brandkit`'s job.

Format contracts — file layout, hotspot markup, the self-containment rules —
live in `references/formats.md`. Read it before producing rung 2 or 3.

## The editable exit: a design file

When the host exposes a design-file backend, a prototype can be produced as an
editable design file (`.pen`) instead of a rung-3 HTML page.

**This is not rung 4.** The ladder produces disposable artifacts that answer one
question and are thrown away. A design file is the opposite: a living document
someone keeps editing. Take this exit when the user wants to *carry on
designing* — in a visual editor, or by handing it to someone who will — not when
they want an answer to a question. If the question is "does this structure
work", rung 1 still costs one message and a design file costs an afternoon.

Two things the ladder guarantees that a design file does not:

- **It is not double-clickable.** Opening it needs the application. Where the
  user wants something they can just open — to send to a colleague, to look at
  on a phone — rung 2 or 3 is the answer, and a design file is not a substitute.
- **Its HTML export is not self-contained.** The export emits Tailwind or CSS
  with image assets referenced by relative path, never embedded. That is a
  handoff to implementation, not a prototype artifact, and it must not be
  offered as one.

Say which of the two you produced. "Here is your prototype" means different
things for a file that opens and a file that needs an app.

### Availability, and what to do without it

The `design_tool` setting (`setup`) is `auto` by default: use a design-file
backend when the host exposes one, otherwise stay on the ladder. `none` pins it
off. `setup`'s doctor reports the setting and does **not** claim to have
verified the backend — it is a host capability, not a binary on `PATH`, so it
cannot be probed from a script.

If the backend is unavailable, say so plainly and produce the rung the question
actually needs. Never describe a design file you did not create, and never
silently substitute an HTML page for one the user asked for.

### Whose decisions these are

A design-file backend arrives with its own visual style archetypes. They are
reference values, not brand decisions, and this skill does not get to make a
brand decision through them.

- **A token set exists** — build from it. The design file reads the project's
  compiled `design-tokens` output, exactly as the token-faithful HTML tier does.
- **No token set exists** — a style archetype is scaffolding. It goes in the
  "what is fake" list with everything else invented for the prototype, and it is
  named as a placeholder in the handoff. A direction that survives contact goes
  to `brandkit` to be explored properly and then into `design-tokens`, which
  owns it from that point. A style archetype that quietly becomes the brand
  because nobody objected is the failure this rule exists to prevent.

Copy in a design file is scaffolding on the same terms as anywhere else in this
skill: any string that outlives the prototype belongs to `ux-writing`.

### Where it goes

`<artifact_root>/<slug>/prototypes/<name>.pen` — the same anchor as every other
prototype, resolved through `setup`, never the working directory. See
`setup/references/paths.md`.

## Copy in a prototype

The prototype drafts its own strings freely — buttons need words before
`ux-writing` has run, and lorem ipsum hides layout truths. Ground the wording
in the JTBD corpus where it exists. But drafted copy is scaffolding: if any
prototype string is about to be reused in the real product, hand it to
`ux-writing` — that skill owns the source wording of every user-facing string,
and prototype copy that skips the handoff ships unreviewed.

## Output

Every prototype is a file the user can open, not a paste into chat (rung 1 may
also be shown inline). It is **self-contained**: no CDN, no external fonts, no
build step. Double-click opens it.

It goes in `<artifact_root>/<slug>/prototypes/<name>/` — the `setup` setting,
which defaults to `corpus_root`. `setup` owns the whole path table
(`setup/references/paths.md`); resolve it rather than building it:

```python
from humane_setup import artifact_dir
artifact_dir(slug, "prototype")
```

**Never write to the current working directory**, and never to a bare relative
`prototypes/`. That puts the user's prototype wherever the agent happens to be
standing — an earlier version of this rule did exactly that and wrote a
prototype into the humane plugin's own source tree, untracked and one
`git add -A` from shipping to every user. If the user names a place, use it.

> **Claude Code extras:** offer to publish the file as an Artifact when the
> user wants a shareable link; the file on disk remains the source of truth.

State with the artifact:

1. **The question** this prototype answers, in one sentence.
2. **The job** it serves, cited from the corpus (`jtbd.json` outcome or force)
   — or "no corpus; structure is a guess" when `jtbd` has not run.
3. **What is fake** — drafted copy, invented data, dead controls — so a
   reviewer does not report scaffolding as findings.

## What this skill does not own

| Concern | Owner |
| --- | --- |
| Whether the structure serves a real job | `jtbd` — cite it, don't re-derive it |
| The token set, colors, and contrast measurement | `design-tokens` |
| Typeface selection | `type-specimen` |
| Final wording of any string that outlives the prototype | `ux-writing` |
| Structural defect classes in the eventual real build | `layout-rules` |
| How the prototype lands with strangers | `respondent-panel` |
| Whether a person can complete a task on it | `walkthrough` |

A prototype is never reviewed by this skill. It is handed to the reviewers as a
first-class artifact and judged there, once, by the skill that owns each rule.

## Conflict precedence

The user's explicit words > this ruleset > the project's existing system >
personal taste. If the project already has screens the prototype contradicts,
flag the conflict; don't silently redesign the product.
