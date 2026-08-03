# Copy patterns

Ready-made shapes for the strings that recur in every product. Each pattern
names the parts that must be present; the wording is yours.

---

## Destructive confirmation

The dialog must be answerable without reading the body.

```
Title      Delete this project?              <- names the object and the action
Body       <what is lost> + <what survives> + <recovery window, if any>
Confirm    Delete project                    <- repeats the consequence
Cancel     Cancel                            <- never "No"
```

Read the corpus's `switch_forces.anxiety` before writing the body: the sentence
that defuses the actual fear is the whole job of this dialog. If the anxiety is
"I'll lose everything", the body says what is recoverable and for how long. If
it is "I'll be charged anyway", the body says what happens to billing.

Reserve type-to-confirm for genuinely unrecoverable actions. Using it for
recoverable ones trains people to type past it.

---

## Error message

```
<what happened, plainly> + <what to do next>
```

Placed adjacent to the failing field, not in a toast, whenever the failure has a
location. Positive phrasing ("Use only letters") rather than negative ("Don't
use numbers"). Shown before the mistake where the constraint is knowable in
advance.

| Situation | Shape |
| --- | --- |
| Validation, field-level | "Choose a password with at least 8 characters" |
| Validation, form-level | "Check the highlighted fields" + per-field errors |
| Network / transient | "Unable to save. Check your connection and try again." |
| Permission | What they lack and who grants it: "You need admin access. Ask a workspace owner." |
| Not found | What was looked for and one way forward |
| Server fault, no user action possible | Say so, give an ID to quote, don't fake agency |

Never: "Oops", exclamation marks, blame, "We're having trouble…", an error code
with no sentence around it, or a message that appears after the user has already
lost their input.

---

## Empty state

Three parts, in this order:

```
1. What this place is        "No projects yet"
2. Why it's worth filling    "Projects keep your tasks and files together."
3. One next action           [ Create a project ]
```

For tool and terminal-adjacent surfaces, part 3 is the **exact command**, in a
`<code>` block, plus a line confirming what still works without it:

```
No corpus found at ~/jtbd.

  python3 scripts/graph.py ~/jtbd/<slug>

Every other view still works on the projects you do have.
```

Variants:

| Kind | Extra requirement |
| --- | --- |
| First run | Should teach; may be the most-read screen in the product |
| Search / filter result | Name the query, offer the exit ("Clear filters") |
| Error-caused empty | Distinguish "nothing here" from "we couldn't load it" — never show the same string for both |
| Permission-caused empty | Say it's hidden, not absent |

Never park persistent information here. It disappears the moment content exists.

---

## Button and menu labels

| Element | Shape | Never |
| --- | --- | --- |
| Primary action | Verb + object: `Save draft` | `OK`, `Submit`, `Let's go!` |
| Secondary | Verb: `Cancel`, `Back` | `No`, `Nevermind` |
| Flow advance | One word, kept for the whole flow: `Continue` | Alternating `Next`/`Continue` |
| Flow finish | `Done` or the outcome: `Publish` | `Finish!` |
| Menu item | Same noun as everywhere else | A synonym invented for this menu |
| Toggle | The ON state: `Send read receipts` | `Don't send read receipts` |

A label that needs a tooltip to be understood is the wrong label.

---

## Notification and toast

```
<what changed> [+ <what to do about it>] [+ <undo>]
```

- Carries an action or an error → stays until dismissed.
- Purely informational → may auto-dismiss.
- Undo beats a confirmation dialog for reversible actions: do it, then offer
  the way back.
- Never the only place a consequential message appears; a toast missed is gone.

---

## Settings labels

```
Label        The ON state, as a plain statement
Description  What it affects, and any cost — one line
```

Group by what the user is trying to control, not by which subsystem implements
it. Link directly to a related setting rather than describing its path. If a
setting needs a paragraph to explain, the default is probably wrong.

---

## Placeholder text

Shows the expected **format**, never the label:

| Field | Placeholder |
| --- | --- |
| Email | `name@example.com` |
| Date | `DD/MM/YYYY` |
| Search | What is searchable: `Search projects and quotes` |
| Amount | `0.00` |

Every field keeps a visible label regardless.

---

## Loading and progress

| Duration | Shape |
| --- | --- |
| Under ~1s | Nothing; a flashed spinner is worse than none |
| 1–10s | Spinner or skeleton, no text needed |
| Over ~10s | Say what is happening and, if known, how much is left |
| Unbounded | Say what is happening, allow cancel, don't estimate what you can't |

Keep a submit button enabled until the request starts, then disable it with a
spinner while keeping its original label — the label is what tells the user what
they are waiting for.
