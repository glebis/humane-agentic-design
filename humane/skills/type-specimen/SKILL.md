---
name: type-specimen
description: Build a browsable type specimen that sets candidate typefaces in the product's own words, so a font is chosen against real copy rather than "Hamburgefonstiv". Loads families from Google Fonts, shows a weight ladder, prose, a data table, list rows, small caps, glyph coverage and variable axes per family, measures WCAG and APCA for the chosen background/text pair, and lets any specimen text be edited in place — one edit, every family. Use when picking a typeface, comparing shortlisted fonts, checking a font's Cyrillic or symbol coverage, or proving a font works for a specific interface before it enters the token set. Triggers on choose a font, pick a typeface, compare fonts, type specimen, font shortlist, does this font have Cyrillic, font pairing, which font for this dashboard, шрифтовой стенд, выбрать шрифт.
---

# type-specimen

Choosing a typeface from a foundry's own specimen tells you the font can be
made to look good. It does not tell you whether *your* numbers align in *your*
table at *your* size. This skill builds a single self-contained HTML page that
sets every shortlisted family in the copy the product actually ships — the same
headline, the same price column, the same empty-state sentence — so the
comparison is between candidates doing the real job.

The page is standalone: one HTML file, no build step, no dependencies. Families
load from the Google Fonts CSS API at view time.

## Quick reference

| You want to | Run |
| --- | --- |
| Start a specimen | `scripts/specimen init -o spec.json --locale ru --context "..."` |
| Feed it the brief | `scripts/specimen texts spec.json --from-file README.md` |
| See what still needs writing | `scripts/specimen texts spec.json` |
| Write a slot | `scripts/specimen texts spec.json --set headline="..."` |
| Validate without building | `scripts/specimen check spec.json` |
| Build and open it | `scripts/specimen build spec.json` |

Config field reference: `references/config.md`.

## The flow

### 1. Take the brief

Ask what the type is for, in one or two sentences: the product, the surface
(dashboard, receipt, marketing page), the reading distance, and the scripts it
must cover. Store it — `--context` for a sentence, `--from-file` for a README,
a spec, or a page of real product copy.

The brief is stored in the config and never shipped to the built page. It is
for whoever writes the copy, and a specimen often gets shared before the
product is announced.

### 2. Write the ten slots from real copy

The page renders ten text slots. Each has a fixed shape, enforced by
`specimen check`:

| Slot | Shape | What it has to prove |
| --- | --- | --- |
| `display` | one line | The largest thing on the screen, at its real length |
| `timer` | one line | Figures — lining, tabular, and whether they align |
| `headline` | one line | A heading in its real register |
| `weights` | one line | One phrase repeated down the weight ladder |
| `prose` | many lines | A paragraph at reading size, set in columns |
| `caps` | one line | Uppercase, and whether small caps exist |
| `rows` | many lines, `name :: value` | Label/value pairs, right-aligned |
| `table` | many lines, 3 `::` cells | A real data row |
| `tableHead` | one line, 3 `::` cells | The column labels above it |
| `alphabet` | many lines | Every script the product ships |

**Take the strings from the product, not from your head.** A specimen written
in invented copy tests an invented product. Where `ux-writing` owns a string,
use its wording verbatim; where the product exists, lift from the interface. If
neither is available, say so in the handoff rather than passing invention off
as evidence.

Two rules that decide whether the page is useful:

- **Longest realistic, not average.** A price column proves nothing at `9 ₽`.
  Set the widest figure the product can produce, because that is the one that
  breaks the layout.
- **The alphabet slot must cover every script.** A Cyrillic product whose
  specimen shows only Latin has tested half the font. `scriptRange` makes the
  page flag families that ship without the script — set it (`U\+04` for
  Cyrillic; `--locale ru` does this for you) or the badge never appears.

### 3. Choose the families

One family per line, `name :: group :: note`. Names must match the Google Fonts
catalogue exactly — a typo produces a "failed to load" badge, not an error.
`group` filters the grid and must be declared in `groups`; `note` is for the
foundry or whatever else you need to remember at a glance.

Six to ten candidates is the working range. Past that the grid stops being a
comparison and becomes a catalogue, which is the thing you were trying to
escape.

### 4. Build, then judge in the page

`scripts/specimen build spec.json` writes the HTML and serves it on
`127.0.0.1`. It serves rather than opening a `file://` URL on purpose: the
share link is copied via the clipboard API, which a `file://` page does not
get.

In the page:

- **Edit any specimen text in place.** Click a line inside any card, type, then
  Tab or click away. Escape reverts. The edit writes back to the single source
  of truth, so it lands in every family at once — the point being that you
  compare families, never accidentally compare copy. Table and row cells edit
  one cell at a time; everything else edits whole.
- **Set the real background and text colours** before judging anything. A
  typeface reads differently at a different contrast, and the panel reports
  WCAG and APCA for the pair as you go.
- **Expand a card** for prose, tables, glyph coverage and variable axes. The
  collapsed card answers only "is this worth a look".
- **Copy link** encodes the whole state in the URL, so a shortlist can be sent
  to someone else exactly as you left it.

### 5. Hand off

A chosen family is a token, not a note in a document. Hand the name and the
weights you actually used to `design-tokens`, which owns the token set from
that point on. If the pair you chose failed the contrast bar, that is
`design-tokens`' `tokens contrast` to resolve — do not fix it by eye in the
specimen and call it done.

## Honesty guards

- **A specimen is evidence, not a verdict.** It shows how families behave in
  the product's copy. It cannot tell you which is *right*, and neither can this
  skill — report what differed and let the person choose.
- **Do not rank families on a score.** There is no number here. If you find
  yourself writing "Onest: 8/10", you are inventing precision the page did not
  measure.
- **Never claim coverage you did not look at.** The glyph-coverage grid tests
  the characters in `glyphSets` and nothing else. A family that passes there
  may still be missing something you never asked about — say which sets were
  checked.
- **A "failed to load" badge is not a judgement of the font.** It usually means
  the name does not match the catalogue. Check the spelling before reporting a
  family as unavailable.
- **The contrast readout describes the pair you set, not the page.** Change the
  background and it changes. Cite the colours alongside the number or the
  number means nothing.

> **Claude Code extras:** with the `humane` plugin installed the specimen sits
> between `humane:jtbd` (who reads this, and where) and `humane:design-tokens`
> (where the chosen family lands). Slot copy should come from
> `humane:ux-writing` rather than being written fresh here, and a built page is
> a reviewable artifact — hand it to `humane:respondent-panel` when you want to
> know how the type *lands* rather than whether it is correct.

## Conflicts

The user's explicit words win, then this skill's rules, then the project's
existing system, then taste. If the project already has a typeface in its
tokens, say so and build the specimen with it included as a baseline rather
than quietly proposing a replacement.

## Tests

```bash
cd humane/skills/type-specimen && python3 -m pytest tests/ -q
```
