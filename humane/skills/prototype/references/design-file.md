# The editable exit: a design file

The operational contract for producing a prototype as an editable design file
(`.pen`) when the host exposes a design-file backend. `SKILL.md` decides
*whether* to take this exit; this file says how to take it safely.

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

## Availability, and what to do without it

The `design_tool` setting (`setup`) is `auto` by default: use a design-file
backend when the host exposes one, otherwise stay on the ladder. `none` pins it
off. `setup`'s doctor reports the setting and does **not** claim to have
verified the backend — it is a host capability, not a binary on `PATH`, so it
cannot be probed from a script.

If the backend is unavailable, say so plainly and produce the rung the question
actually needs. Never describe a design file you did not create, and never
silently substitute an HTML page for one the user asked for.

## Whose decisions these are

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

## Where it goes — and why you cannot choose

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

1. **Read the application state and print which document is active** — the
   backend-reported identity is the only trustworthy name for it. A path is
   not: the backend ignores the paths it is given, and `.design` cannot hold
   the backend's document at all — it lives in the application's own store
   (`setup/references/paths.md`).
2. **Show the user what is active and ask, in so many words: "build this
   prototype into this document?"**
3. **Without an explicit yes, stop.** If the active document is the user's
   other work, ask them to create and open a fresh document for the prototype,
   and say why: you cannot create or switch documents, and building now would
   write into what is open.
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
