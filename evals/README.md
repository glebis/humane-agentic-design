# evals

Does running a humane skill actually produce a better result than not running
it? This directory answers that for the parts of the method a machine can check,
and says plainly which parts it cannot.

**Dev-only.** Nothing here is a runtime dependency of any shipped skill, and
nothing under `humane/` may import from `evals/`.

## Dependencies

| What | Needed for | Install |
| --- | --- | --- |
| Python 3, standard library only | the contrast pathway, fixtures, scoring | already present |
| Node 18+ | the accessibility pathway | already present, or `brew install node` |
| `axe-core` (pinned exactly) | oracle #2 | `npm install` in `evals/` |
| `jsdom` | the DOM axe runs against | `npm install` in `evals/` |

The Python side has **no dependencies at all** and never gains any — the repo's
stdlib-only rule governs shipped skill scripts, and while `evals/` is not one,
the fixture generator and scorer stay runnable on a bare machine on purpose.

The Node dependencies are for the accessibility oracle alone. Without them the
harness still runs: `run_axe.js` reports `available: false`, the manifest records
the pathway as unavailable, and that domain is scored **Not reviewed** rather
than quietly vanishing — the same distinction the skills themselves draw between
`Clear` and an admitted gap. A run on a machine without Node must not look like
a smaller but complete result.

`axe-core` is pinned to an exact version, not a range. The enabled rule set *is*
the oracle, so a minor upgrade that adds or changes a rule would silently move
ground truth underneath the fixtures.

## The trap this design exists to avoid

The obvious eval — run the task with and without the skill, ask a model which
output is better — is circular. The judge reads humane's own vocabulary (the
severity scale, `Not reviewed`, evidence locators) and scores the skill-run
higher because it matches the rubric it was handed. That measures conformance to
the skill, not improvement over its absence.

So the ground truth here is never a judgement. It is computed by a program, and
a defect is planted only if that program says so. Nothing here asserts a defect
by hand.

**Oracle #1 — colour.** `humane/skills/design-tokens/scripts/dtokens/contrast.py`,
the same code the `design-tokens` skill runs in production, reached through the
single import point in `contrast/oracle.py`.

**Oracle #2 — accessibility.** `axe-core` under jsdom, via `axe/run_axe.js`. It
runs a vetted **allow-list** of rules (`axe/owners.json`), never everything axe
ships: jsdom computes no layout, so rules needing geometry or a resolved cascade
cannot be judged soundly, and a deny-list would rot the first time an upgrade
added one.

Two rules of that allow-list are worth knowing:

- **`color-contrast` is excluded.** Two oracles ruling on one domain would
  produce contradictory truth — axe is WCAG-only and would pass exactly the
  WCAG-passes/APCA-fails pairs this harness plants on purpose. Under jsdom axe
  cannot decide it anyway; it returns `incomplete`, not a verdict.
- **The accessible-name rules are excluded** (`image-alt`, `label`,
  `button-name`, `link-name`). `CLAUDE.md` puts accessibility engineering depth
  *out of humane's scope*, deferring to `interfaces`. Planting a defect the
  method disclaims would test nothing about the method — and would penalise a
  review for correctly routing it elsewhere.

Each rule carries a set of **accepted owners**, not one name, because some
defects are defensibly routed to more than one skill. `routing_accuracy` must
not mark a defensible choice wrong.

## What is measured

| Metric | Question |
| --- | --- |
| `recall` | Of the defects actually present, how many were found? |
| `recall_disagreement` | How many of the defects were found that only a *measurement* catches? |
| `precision` | Of the findings reported, how many were real? |
| `false_clear` | Did it assert `Clear` over a domain holding real defects? |
| `padding` | How many findings did it invent on a clean fixture? |
| `routing_accuracy` | Was the finding reported by the skill that owns the rule? |

`false_clear` is the one that matters. Recall and precision are easy to game in
opposite directions — report everything, or report nothing. Only a calibrated
reviewer scores well on `false_clear` and `padding` at the same time, and that
pairing is the axis on which a disciplined skill should beat a bare prompt. If
it does not, the skill is not earning its tokens.

`recall_disagreement` is the headline. WCAG and APCA do not agree: `#767676` on
`#ffffff` clears the familiar 4.5:1 bar (4.54) and fails APCA for body text
(71.6 against a floor of 75). Under the default `standard="both"` that is a real
defect — and it is invisible to anyone reviewing from memory of the 4.5:1
number. A fixture built only from obvious grey-on-grey failures would show
almost no difference between arms and would wrongly conclude the method adds
nothing.

## What is NOT measured

This pathway covers **colour contrast only**. It says nothing about:

- structure, hierarchy, or the `layout-rules` defect classes
- copy quality, microcopy, or anything `ux-writing` owns
- task completion (`walkthrough`), heuristic violations (`nielsen-heuristics`)
- de-slop, brand fit, or whether a transformation claim is felt
- whether the findings were *usefully ranked*, only whether they were found

Those are most of the method. A score here is evidence about one domain, not a
grade for humane — reporting it as one would fail the same honesty guard the
skills impose on themselves. When this harness grows, each new pathway gets its
own deterministic oracle or it does not get built.

## Layout

    evals/
      contrast/
        oracle.py     the single import point for contrast truth
        generate.py   seeded fixture + manifest generator
        score.py      scores one saved review report against one manifest
        runs/         generated fixtures and saved reports (gitignored)
      tests/          tests for the harness itself

## Running a comparison

The harness is deterministic and never invokes a model. Model runs happen
separately and their reports are saved to disk, then scored.

```bash
# 1. generate a fixture and its ground-truth manifest
python3 evals/contrast/generate.py --seed 1337 --pairs 12 --defects 5 \
    --out evals/contrast/runs/seed-1337

# 2. review runs/seed-1337/fixture.html twice, saving each report:
#    with/    — the review performed under humane:review
#    without/ — the same artifact, same model, an unstructured
#               "review this UI thoroughly and report what's wrong"
#    The control must be a competent prompt, not a strawman.

# 3. score each arm
python3 evals/contrast/score.py \
    --manifest evals/contrast/runs/seed-1337/manifest.json \
    --report   evals/contrast/runs/seed-1337/with/trial-1.md --arm with
```

Run several trials per arm across several seeds. A single run's delta on model
output is noise, and a comparison reported from one trial per arm is not a
result.
