# Pre-registration — pathway E: two domains in one fixture

Written and committed **before any fixture was generated or any arm was run**.

## What is new here

Every previous pathway planted defects of one kind. This one plants both, in the
same page, confirmed by two independent oracles:

- **colour** — `dtokens/contrast.py`, the code `design-tokens` ships
- **structure** — `axe-core` under jsdom, the vetted allow-list in
  `axe/owners.json`

That changes what can be asked. A review that covers one domain well and the
other badly has been indistinguishable from a thorough one until now.

## The question

Does the skill's explicit domain pipeline produce **broader** coverage than an
unstructured review of the same page — or does a competent reviewer cover both
anyway?

## Fixture

Three seeds. Each: 24 colour pairs with 10 planted contrast defects (at least a
third disagreement cases), plus four planted structural defects — a heading-level
skip, an empty heading, no declared language, and content outside any landmark.
Every one confirmed by its oracle before it enters the manifest; nothing is
asserted by hand.

## Predictions

E1. **Contrast recall favours the skill**, as in the detection pathway — roughly
    1.00 against 0.79, and the gap widest on the measurement-only pairs.
E2. **Structural recall also favours the skill**, and this is the new claim.
    `layout-rules` is an explicit stop in the pipeline; an unstructured review
    asked to "find what's wrong" with a visibly colourful page has no such
    prompt and should skew toward what it can see.
E3. **Both arms find the empty heading and the heading-level skip** — those are
    plainly visible in the source. The gap, if there is one, should sit in
    `html-has-lang` and the missing landmark, which are absences rather than
    things on the page.

## The metric I am declaring unfair in advance

**`routing_accuracy` is not a fair comparison here and will not be reported as a
win.** It asks whether a finding names the humane skill that owns the rule. The
control has never heard of those skills, so it scores near zero by construction
— it did exactly that, 0.000, on the detection pathway. Reporting that as the
skill "winning" would be measuring whether an arm was told the vocabulary.

It stays in the output as a description of the skill arm alone: does the skill
route a structural defect to `layout-rules` and a colour defect to
`design-tokens`, now that both are present and confusing them is possible? Until
this pathway every defect had one possible owner and the number was close to
given.

## What would falsify it

Structural recall equal or better in the control arm. Then the domain pipeline
buys no breadth on a two-domain artifact, and E2 — the reason this pathway was
built — is wrong. That result would join coverage honesty and padding as a third
place where the discipline codifies something a strong model already does.

## What this cannot show

Three seeds, one trial per arm. Structural coverage here is the subset axe can
judge under jsdom, which excludes the accessible-name rules `CLAUDE.md` puts
outside humane's scope. Run-to-run variance has still never been measured. No
significance test will be reported.
