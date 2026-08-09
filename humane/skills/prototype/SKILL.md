---
name: prototype
description: Make an idea lookable and clickable at the cheapest fidelity that answers its one open question — an ASCII sketch, an SVG click-dummy with hotspots linking screens, or a self-contained HTML file. Use when the user wants to see or try an idea before committing to structure, tokens, or copy. Triggers on prototype, wireframe, mockup, click-dummy, sketch the screens, "what would this look like", "mock this up", "show me the flow", "прототип", "макет".
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

## Quick Reference

| Need | Where |
| --- | --- |
| Format contracts per rung: file layout, hotspot markup, self-containment, the SVG text traps | `references/formats.md` |
| Where the output file goes | `setup/references/paths.md` — `setup` owns the path table |

## The one question

Every prototype names, before anything is drawn, the single question it will
answer. A broad request ("mock up the app") contains several candidate
questions — extract them, and ask the user to pick one; a prototype chasing two
questions answers neither. Record the chosen question in the artifact's notes
block (see Output).

The question is **settled** only by the user saying so, or by a named
reviewer's output — a `respondent-panel` read, a `walkthrough` result. The
maker's own impression that a structure "looks right" settles nothing; this
skill never reviews its own output, and it does not certify its own handoffs
either. Until the question is settled, it stays open, and escalation waits.

## Where it sits

The home case is greenfield: after `jtbd`, before `design-tokens`. The corpus
says what job the interface serves; the prototype proposes a structure for it;
only a structure that survives being looked at or clicked through deserves a
token set.

`jtbd` is preferred, not required. Entered directly, with no corpus: offer to
run `jtbd` first, and if the user declines, proceed — with "no corpus;
structure is a guess" stated in the artifact's notes block.

Prototyping inside an existing system is also legitimate — a new screen for a
product that already has tokens. The existing tokens are then context, and the
token-faithful tier renders under them. What this skill still never does there
is re-litigate the system: a finding about the tokens themselves belongs to
`design-tokens`, and defects in the eventual real build to `layout-rules`.

## The fidelity ladder

Three formats, in escalation order. Name the open question first, then pick the
lowest rung that can answer it. The user's explicit format request always wins.

| Rung | Format | Answers | Never claims |
| --- | --- | --- | --- |
| 1 | **ASCII** — box-drawing sketch in a fenced code block | Is this the right structure? What goes where? | Proportion, color, feel |
| 2 | **SVG click-dummy** — screens as SVG frames, hotspots linking them, in one self-contained HTML file | Does the navigation make sense? Can you get from A to B? | Visual polish, real rendering behavior |
| 3 | **HTML** — real markup and CSS, self-contained file | Does the screen read? Do the interactions feel right? | That it is the product |

Escalate only when the current rung's question is settled (see "The one
question" — settled by the user or a named reviewer, never by the maker) or
when the open question lives on a higher rung. Do not skip rung 1 for a new structure — an
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

### Where it goes — and why you cannot choose

**A design-file backend writes into the document the application has open. You
do not get to pick the path, and it will not tell you that.**

This was established by testing, not assumed. Pencil's tools all take a
`filePath` argument documented as "access a .pen file". It is ignored. Passing
the path of a different, existing `.pen` returns the *active* document's nodes,
and building with a path to a file that does not exist silently builds into
whatever was already open — in the run that found this, a full dashboard and
fourteen variables were written into an unrelated icon file, and every call
returned `OK`.

So the pre-flight is not optional:

1. **Read the application state and print which document is active.**
2. **Compare it to where this prototype belongs** —
   `.design/prototype-<name>.pen`, resolved through `setup`
   (`setup/references/paths.md`).
3. **If they do not match, stop.** Ask the user to create and open the file at
   that path, and say why: you cannot create or switch documents, and building
   now would write into their open work.
4. Build only after the active document is the intended one. Say in the handoff
   which document you wrote into.

Never build into a document you did not confirm. An `OK` from the backend means
the operation succeeded somewhere, not that it succeeded where you meant.

If the user would rather not open anything, that is a complete answer: produce
the rung the question needs instead. A prototype in the wrong file is worse than
no prototype.

**Cleaning up after a mis-targeted build** is your job, not the user's: delete
the nodes you added, and check `GetVariables()` — variables merge into the host
document and survive node deletion.

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

The destination is `setup`'s rule, not this skill's: resolve
`artifact_path(name, "prototype", "html")` — it returns the `prototypes/` parent; create
`<name>/` inside it — and never write to the working directory. The full path
table, defaults, and prohibitions live in `setup/references/paths.md`. If the
user names a place, use it.

> **Claude Code extras:** offer to publish the file as an Artifact when the
> user wants a shareable link; the file on disk remains the source of truth.

Every prototype carries a **notes block inside the file itself** — a visible
footer (rung 1: a paragraph under the sketch) — so the context travels with
the artifact when it is opened alone. Chat may repeat it; it must never be the
only copy. Three fields:

1. **The question** this prototype answers, in one sentence.
2. **The job** it serves, cited from the corpus (`jtbd.json` outcome or force)
   — or "no corpus; structure is a guess" when `jtbd` has not run.
3. **What is fake** — drafted copy, invented data, dead controls — so a
   reviewer does not report scaffolding as findings.

## Smoke test before handoff

Producing the file includes proving it meets its own format contract. This is
production QA, not review — reviewing the design stays with `respondent-panel`,
`walkthrough`, and the rest. Before handing the artifact over:

- open the file with no hash and confirm the first screen shows;
- follow every hotspot and every back link once;
- confirm zero external requests (no CDN, fonts, or linked assets);
- check every string against its container (the SVG text traps in
  `references/formats.md`).

Anything on this list that cannot be run is reported as **Not verified**, never
silently assumed.

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
