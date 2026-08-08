---
name: ux-writing
description: Write and review the words inside a product — button labels, error messages, empty states, confirmations, settings labels, placeholders, notifications — and the documentation prose around it, including READMEs, docs pages and release notes. Grounds the wording in the JTBD corpus (the anxiety force tells you what a confirmation must defuse) and hands the result to respondent-panel to find out whether strangers read it the way you meant. Use when writing or reviewing any user-facing string. Triggers on UX writing, microcopy, interface copy, button labels, error messages, empty states, placeholder text, settings labels, confirmation dialog, notification copy, README wording, rewrite these docs, release notes copy, "what should this button say", "rewrite this error", "перепиши текст кнопки".
---

# UX Writing

The words are part of the interface, not a layer applied to it. A control that
names its exact action needs no tooltip; an error that says what to do next
needs no support ticket. Clear beats clever, consistent beats varied, and the
best error message is the interaction redesigned so the error cannot happen.

## What this skill owns, and what it doesn't

Owns: the **source wording** of every user-facing string, and the decision about
what a string must accomplish.

That includes **documentation prose** — READMEs, docs pages, release notes,
onboarding guides. The principles below were written for interface strings and
most transfer directly (accuracy, one vocabulary, nothing does double duty, no
selling); where a principle is interface-specific it is marked. A doc that
contradicts the thing it documents is a `HIGH` finding, not a typo.

| Adjacent concern | Owner |
| --- | --- |
| How copy renders — capitalization via `text-transform`, truncation, smart punctuation, measure | `layout-rules` (and `better-typography` if `interfaces` is installed) |
| Whether the layout has room for the translated string | `layout-rules` |
| Error markup and announcement (`aria-invalid`, live regions) | `nielsen-heuristics` for the heuristic; `better-accessibility` for the implementation |
| Whether the copy *lands* with strangers | `respondent-panel` |
| Whether a stakeholder objects to the argument | `persona-review` |
| Brand voice for marketing surfaces, taglines, transformation claims | `brandkit`, `before-after` |

This skill writes the words. It does not judge the usability of the flow around
them — that is `nielsen-heuristics`.

## Quick Reference

| Category | When to use | Reference |
| --- | --- | --- |
| Copy patterns | Ready-made shapes for errors, empty states, confirmations, toggles, notifications | [patterns.md](references/patterns.md) |

## Step 0 — Read the evidence before writing a word

This is the step that separates this skill from a style guide, and it is not
optional when a corpus exists.

1. **Look for `<corpus_root>/<slug>/jtbd.json`.** `corpus_root` is the `setup`
   setting (default `~/jtbd`); read the configured value rather than assuming
   the default, or a user who moved their corpus gets "no corpus found" and
   copy written from assumption. If one exists, read it. If several projects
   exist, ask which. If none exists, say so plainly in the output — the copy is
   then written from assumption, and that is a fact the reader should have.
2. **Mine the switch forces**, because each one tells you what a specific class
   of string has to accomplish:

| Force | What it means for the copy |
| --- | --- |
| `anxiety` | What a confirmation, a destructive dialog, or a first-run screen must defuse. If the anxiety is "I'll lose my data", the delete dialog says what is recoverable and for how long. |
| `habit` | What the old vocabulary was. Name things the way the thing they're leaving named them, or say explicitly that you renamed it. |
| `push` | The frustration to *name back* to them in an empty state or onboarding. Recognition beats persuasion. |
| `pull` | The one outcome a primary button should promise. It is usually the verb. |

3. **Reuse the corpus's own words.** `evidence.quotes[]` is the product's real
   vocabulary, captured from people who use it. A verbatim noun from a quote
   beats an invented one every time. When you take a word from a quote, cite the
   evidence id (`[Q2]`) beside the string.

## Step 1 — Recon the voice you already have

Before writing or changing anything, read the surrounding copy, the product's
terminology, its localization files, and any style guide. Preserve intentional
character. A difference from generic plain language is a finding only when it
creates inconsistency, ambiguity, translation risk, or a tone wrong for the
stakes — not merely because it has personality.

Tone flexes with the stakes; voice does not change:

| Context | Tone |
| --- | --- |
| Success, onboarding, empty states | Warm, can be light |
| Routine actions, settings | Neutral, minimal |
| Errors, destructive confirmations | Calm, plain, zero playfulness |
| Data loss, security, money | Serious, explicit, no compression |

## Core Principles

### 1. A Control Names Its Exact Action

Buttons start with a verb naming the specific thing that happens: `Send`,
`Save draft`, `Delete project`. Never `OK`, `Submit`, `Let's go!`, or a bare
`Yes`/`No` on anything consequential. A confirmation repeats the consequence so
the dialog is answerable without reading the body: "Delete this project?" offers
`Delete project` and `Cancel`.

### 2. Nothing Does Double Duty

A label labels, an example demonstrates, a hint hints. A placeholder is never
the field's only label — it disappears exactly when the user needs it. Copy that
restates the heading, the metric row, or the data just shown is deleted, not
rewritten. If a summary line can't add a conclusion or a next action, drop it.

### 3. Errors Are Instructions, Placed Where It Broke

An error names what to do next, adjacent to the failing field, phrased
positively, and shown before the mistake where possible.

| Bad | Good |
| --- | --- |
| That password is too short | Choose a password with at least 8 characters |
| Invalid name | Use only letters for your name |
| Oops! Something went wrong. | Unable to save. Check your connection and try again. |

No blame, no "oops", no exclamation marks, no "we" that obscures who failed or
what to do. If the same error keeps firing, the fix is the interaction, not the
wording — say so rather than polishing it.

### 4. Empty States Teach

An empty state says what this place is, how to fill it, and gives one clear next
action. In a tool or CLI-adjacent surface, show the **exact next command** in a
`<code>` block and add that everything else still works. Never a bare "No data".
Search and filter empties name the query and offer the exit: "No results for
'quarterly'. Clear filters." Never park persistent, load-bearing information in
an empty state — it vanishes the moment content arrives.

### 5. Settings Describe the ON State

Label a toggle for what happens when it is on — "Send read receipts" — and let
users infer the off state. Never label the negative; it turns the toggle into a
double negative. Link directly to a referenced setting instead of narrating the
path to it.

### 6. Links Describe Their Destination

Link text must make sense read out of context, because screen-reader users
navigate by a list of links: "Read the billing docs", never "Click here" (which
also assumes a mouse), and never several bare "Learn more" links on one page —
suffix each one.

### 7. When a Sentence Names an Entity, Link the Entity

Verdicts, tooltips, summaries, and empty states are navigation, not decoration.
If the copy says "3 projects hire this job", each is reachable from those words.

### 8. Write for Translation from the First String

Every user-facing string exists in every supported locale from the first commit,
in one string table, with a key-parity check. Never build a sentence by
concatenating fragments around a variable (`"You have " + n + " new messages"`) —
word order and plural rules differ per language; use full templated strings with
proper pluralization. No idioms, no wordplay, no humor that won't survive
translation. Translate chrome only: verbatim quotes and captured data stay in
the language they were captured in, because translating a quote destroys the
thing that made it evidence.

### 9. Address the Reader Directly

"You", not "the user". Skip unnecessary gender. Match the input device — "tap"
on touch, "click" with a pointer, "select" when both are possible. Use
possessives sparingly ("Favorites" over "Your Favorites") and never switch
perspective mid-flow.

### 10. One Vocabulary, One Capitalization Policy

If it's "Archive" in the menu, it is not "Move to storage" in the toast. A
multi-step flow picks one word for advancing and keeps it. Pick title case or
sentence case per element type and apply it consistently; sentence case is the
safer default — calmer, no per-word rules, localizes cleanly.

### 11. No Selling Inside the Product

Interface copy is not marketing copy. Delete adjectives that sell ("powerful",
"seamless", "delightful", "effortless"), superlatives, and enthusiasm the user
did not ask for. The transformation claims belong on the landing page, where
`before-after` owns them. Inside the product, describe.

### 12. Jargon Needs Evidence

Borrowed from `jtbd`'s kill switch, applied to user-facing strings: every term
of art in the copy must be one the user already uses (name the quote), one the
interface teaches on first use, or gone. When you cannot point to a quote or a
teaching moment, replace it with the plain word.

## Common Mistakes

| Mistake | Fix |
| --- | --- |
| Copy written before reading the corpus | Read `jtbd.json`; let the anxiety force shape the confirmation |
| Invented vocabulary where the corpus has a real word | Take the noun from `evidence.quotes[]` and cite the id |
| `OK` / `Yes` confirming a destructive action | Repeat the consequence: `Delete project` |
| `Submit` on a form | Name what it does: `Create account`, `Send request` |
| "Oops! Something went wrong." | Say what to do, next to the field that failed |
| "We're having trouble…" | Direct status and next step: "Unable to load content" |
| Error that only fires because the interaction is wrong | Report the interaction as the defect; don't reword it |
| "No data." as the whole empty state | Orient, show the exact next action, note what still works |
| Placeholder doing the label's job | Visible label; placeholder shows the format |
| "Don't send read receipts" toggle | Label the ON state |
| "Click here" / three bare "Learn more" links | Describe each destination |
| "Continue" on step 2, "Next" on step 3 | One flow vocabulary throughout |
| "Save Changes" beside "Discard changes" | One capitalization policy per element type |
| `"You have " + n + " messages"` | Full templated string with pluralization |
| A locale added "later" | Key parity from the first commit |
| Quote translated along with the chrome | Chrome translates; captured evidence does not |
| "Powerful", "seamless", "effortless" in a settings screen | Delete the adjective; describe the behavior |
| Summary line restating the metrics above it | Add a conclusion or delete the line |
| Entity named in prose but not linked | Link it to its detail view |

## Step 2 — Test it on someone who has read none of this

Copy that survives its author is not the same as copy that survives a stranger.
When the strings matter — a hero, an onboarding sequence, a destructive
confirmation, a pricing page — hand the artifact to `respondent-panel`
**verbatim**, with no rationale attached, and treat convergent misreadings as
defects in the copy rather than in the readers.

Then revise against the convergent findings only, and re-run the *same* panel
briefs so the comparison is clean. Divergence along an axis (newcomers fine,
burned-before users suspicious) is a targeting decision, not a rewrite mandate.

## Review Output Format

Use this format when reviewing existing copy rather than writing new copy. If an
orchestrator is running this skill as one domain of a larger review, hand it the
findings and let its format, severity scale, consolidation, cap, and verdict take
precedence over this section.

### Findings

One table, ordered by severity, then by reach:

| Severity | Location | Before | After | Why |
| --- | --- | --- | --- | --- |
| HIGH | `src/DeleteDialog.tsx:29` | "OK" | "Delete project" | A consequential action must repeat its consequence |
| MEDIUM | `src/PasswordField.tsx:36` | "Invalid password" | "Choose a password with at least 8 characters" | The error must say how to fix it |

- **Severity** — `HIGH` misleads, hides a consequence, or blocks recovery;
  `MEDIUM` makes a task harder to understand; `LOW` is isolated voice or
  consistency polish.
- **Location** — cite `path/to/file:line`, or the exact screen and element when
  there is no source. Quote the current string exactly, typos included.
- **Why** — name the violated principle and the comprehension or trust cost.

One root cause is one row; list every affected location in it. Never pad the
table: a short review is a valid result. Cap at 15 findings and say what you
left out.

### Considered but Rejected

Two to five candidates you inspected and deliberately did not report, with the
reason — the established voice permits it, the evidence is insufficient, the
convention is intentional, or the change adds churn without user benefit. These
must be real candidates, not invented filler.

### Verification

What you actually checked: the flow walked, the variable interpolation and
pluralization exercised, the locales compared for key parity, the narrow-width
wrapping observed, the panel run. Anything you could not check is listed as
**Not verified** with what remains. A verification gap is never reported as a
finding.

### Verdict

Exactly one: `Block` (a HIGH remains), `Needs changes` (only MEDIUM/LOW remain),
or `Approve` (no actionable findings and the claimed coverage was verified).
