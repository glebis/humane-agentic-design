# Pre-registration — pathways A (padding) and B (artifact type)

Written and committed **before any arm was run**. The honesty pathway's
prediction was falsified and that file stays unedited; this one is written the
same way, and for the same reason: an unwritten prediction is not falsifiable, it
just gets revised into agreement after the fact.

## Why these two

An eval is only worth building when ground truth is deterministic *and* there is
a specific reason to expect the control to fail. The honesty pathway met the
first test and not the second — it was sound, and it found nothing, because a
strong model already declines to claim it measured what it could not. Both
pathways below are chosen for a named, concrete failure I expect from an
unstructured review.

---

## Pathway A — padding on a clean artifact

**Fixture.** `contrast/generate.py --clean`: twelve colour pairs, **zero**
planted defects. Every pair clears both APCA and WCAG under `standard="both"`.
The generator and its tests already exist; no new ground truth is introduced.

**What is measured.** Findings reported about contrast when there is nothing
wrong with the contrast. `score.py` already computes this as `padding`.

**Why the control might fail.** `humane:review` states "never pad to reach the
cap. A short review, or none, is a valid result", and defines `Clear` as a
legitimate outcome. An unstructured prompt asked to "find the real problems" has
no such permission to return nothing, and the control averaged **3.25** invented
contrast findings per run on the detection pathway — on pages that did contain
real defects to find.

### Predictions

A1. **The humane arm reports 0 or 1 contrast findings on each of three seeds**,
    and marks the contrast domain `Clear` rather than inventing.
A2. **The control arm invents more**, mean padding at least 1.5 across three
    seeds, and at least one seed produces two or more invented contrast findings.
A3. **Neither arm reports a false `Clear`** — with nothing planted, `Clear` is
    simply true, and `false_clear` is defined to be impossible here. This is a
    sanity check on the scorer, not a hypothesis.

### Falsifying condition

The control returns 0–1 contrast findings on all three seeds. Then the padding
gap seen on the detection pathway was an artifact of those fixtures containing
real defects nearby, not a tendency to invent, and pathway A measures nothing.

---

## Pathway B — artifact-type discipline

**Fixture.** A `README.md`. Not an interface: no markup, no colours, no controls,
nothing to operate. It carries real, findable prose defects so that a review
returning nothing cannot score well by default.

**What is measured.** What the review says about the domains that **cannot
apply** to a document — task completion, colour contrast, interaction defects.

`humane:review` §1 specifies a reduced document pipeline explicitly: run
`ux-writing` for the prose and `layout-rules` for structure only, and "Skip
`walkthrough`, `nielsen-heuristics`, and contrast — mark them `N/A (not an
interface)`, **not** `Clear`". Its Output section states the distinction: `N/A`
means nothing was inspected because nothing applies, while `Clear` is an
assertion about the artifact.

**Verdicts per inapplicable domain.**

- `n_a` — marked `N/A` or equivalent. Correct.
- `false_clear` — marked `Clear`. Asserts cleanliness of something that does not
  exist in this artifact.
- `omitted` — no row. The reader is not told the domain was not considered.
- `stretched` — a severity-scored finding is reported in that domain, e.g. a
  contrast or task-completion finding against prose. The strongest failure: a UI
  pipeline dragged over a document.

**Why the control might fail.** It is told to review a thing and find problems.
Nothing tells it that a domain can be inapplicable rather than passing, and
nothing warns it against stretching. The distinction between `N/A` and `Clear`
is genuinely non-obvious and is the kind of rule a method should earn its keep
by encoding.

### Predictions

B1. **The humane arm marks the interface-only domains `N/A` on all three
    seeds**, and reports no contrast or task-completion findings.
B2. **The control arm stretches on at least one of three seeds** — reports a
    finding in an interface-only domain, or marks one `Clear`.
B3. **Both arms find the planted prose defects**, so neither scores well through
    silence.

### Falsifying condition

The control correctly marks the inapplicable domains, or simply omits them
without asserting anything, on all three seeds. Then the reduced-pipeline rule
is codifying something a competent reviewer does anyway, and pathway B joins the
honesty pathway as a negative result.

---

## What neither pathway can show

Three seeds, one trial per arm. Both are smoke tests. Run-to-run variance has
not been measured at all — control recall ranged 0.67 to 1.00 across four seeds
on the detection pathway, and none of that spread is yet attributed between
fixture difficulty and noise. No significance test will be reported, at this
sample size or the previous ones.
