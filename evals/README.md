# evals

Does running a humane skill actually produce a better result than not running
it? This directory answers that for the parts of the method a machine can check,
and says plainly which parts it cannot.

**Dev-only.** Nothing here is a runtime dependency of any shipped skill, and
nothing under `humane/` may import from `evals/`. Python standard library only,
no network.

## The trap this design exists to avoid

The obvious eval — run the task with and without the skill, ask a model which
output is better — is circular. The judge reads humane's own vocabulary (the
severity scale, `Not reviewed`, evidence locators) and scores the skill-run
higher because it matches the rubric it was handed. That measures conformance to
the skill, not improvement over its absence.

So the ground truth here is never a judgement. It is a number computed by
`humane/skills/design-tokens/scripts/dtokens/contrast.py` — the same oracle the
`design-tokens` skill uses in production. A defect is planted only if that code
says the pair fails. Nothing in this harness asserts a defect by hand.

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
