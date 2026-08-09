# Pre-registration — pathway D (fan-out) and pathway A, re-run

Written and committed **before any fixture was generated or any arm was run**.
Two earlier predictions in this repo were falsified and their files stand
unedited; this one is written on the same terms.

---

## Pathway D — does fanning out actually preserve findings?

**Why this one matters more than the others.** Every other pathway evaluates the
skills. This evaluates a decision *I* made and shipped as 0.13.0 with a
confident commit message, on argument alone, having measured nothing. The
argument was: a full review runs five domains inline in one context, a host that
compacts summarizes rather than fails, and evidence from the first domain can be
summarized away while the *impression* of coverage survives to the verdict — so
each domain should run in its own context and return only its findings table.

That is a plausible mechanism. It is not evidence.

### The fixture

One large page: 60 colour pairs, 24 of them genuinely failing per
`dtokens/contrast.py`, at least a third disagreement cases. Large enough that a
single reviewer must hold a lot at once before it reaches consolidation.

### The arms

- **inline** — one agent runs `humane:review` over the whole artifact in one
  context, as the skill's default path directs.
- **fanned out** — four agents, one per domain, each given the artifact and its
  own owning skill, each returning only its findings table. Consolidation is
  **mechanical** — the tables are concatenated. I do not judge, rank, or filter,
  because a human consolidator would be a third variable.

Both arms are blind: no manifest in their directories.

### Predictions

D1. **Fan-out recall exceeds inline recall** on this fixture. This is the claim
    0.13.0 rests on.
D2. **Inline findings skew toward pairs early in the document.** If evidence
    decays as context fills, the pairs it reports should cluster at low indices.
    Measured as the mean index of matched planted pairs, normalised 0–1; inline
    below 0.5 and materially below fan-out's.
D3. **Fan-out precision is no better, and probably worse.** Four independent
    finders produce more noise than one. If fan-out costs precision to buy
    recall, that is a trade the skill should state and currently does not.

### What would falsify it

Fan-out recall at or below inline recall. Then the 0.13.0 rationale is
unsupported at this size, the mode is a cost with no measured benefit, and the
honest response is to re-scope it or revert it — not to explain the number away.

### The limitation I cannot engineer away

**I cannot force, observe, or verify context compaction inside a subagent.** So
this measures whether fanning out finds and retains more on a large artifact.
That is necessary evidence for the compaction argument, not sufficient. A null
result does not disprove the mechanism at every size; it does mean I shipped a
mode whose benefit I have not demonstrated, which is the thing worth knowing.

---

## Pathway A, re-run — padding on a genuinely clean artifact

The first attempt was voided by its own fixture. "Clean" meant clean at each
pair's *declared* level, so each page still held one to three pairs that fail if
judged as body text. Reviewers flagged them, correctly, and the harness scored
that defensible judgement as invented findings. `generate.py --clean` now
refuses to emit a fixture unless every pair clears the strictest bar, so the
question is answerable this time.

Three seeds, twelve pairs each, **zero** planted defects.

### Predictions

A1. **The humane arm reports 0 or 1 contrast findings per seed**, and marks the
    contrast domain `Clear` — with nothing planted, `Clear` is simply true.
A2. **The control invents more**: mean padding at least 1.5 across three seeds.
    On the detection fixtures it averaged 3.25 while missing a fifth of the real
    defects.
A3. **Neither arm records a false `Clear`.** With nothing planted it is
    definitionally impossible; this is a scorer sanity check, not a hypothesis.

### What would falsify it

The control returns 0–1 contrast findings on all three seeds. Then the padding
gap seen earlier was an artifact of real defects sitting nearby rather than a
tendency to invent, and pathway A measures nothing — the same negative the
coverage-honesty pathway returned.

---

## What neither can show

One trial per arm per seed. Run-to-run variance has still never been measured,
so none of the spread here is attributable between fixture difficulty and noise.
No significance test will be reported at this sample size.
