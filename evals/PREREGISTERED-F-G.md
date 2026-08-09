# Pre-registration — pathway F (variance) and pathway G (weaker reviewer)

Written and committed **before any arm was run**.

These two exist because of a pattern in the seven pathways already run: four
returned no difference, and the standing explanation for all four has been "a
strong model already does this." That is a hypothesis I have been repeating, not
a fact I have tested. F asks whether the differences I *did* report are real. G
asks whether the explanation for the ones I didn't is.

---

## Pathway F — run-to-run variance

Every number in the report so far comes from one trial per arm. I have written
"n=3, treat as a smoke test" under all of them without ever measuring how much
an identical run varies. So I do not know whether a reported gap is a finding or
a coin flip.

**Method.** One fixture — the detection fixture, seed 1337. Four trials per arm,
same prompt, same model, same everything. Trial 1 of each already exists; three
more per arm. Report the range and standard deviation of every metric.

### Predictions

F1. **Within-arm spread is large** — recall range at least 0.2 across four
    identical runs of the same arm.
F2. **At least one gap I have already reported does not survive it.** Named in
    advance so this cannot be chosen afterwards:
    - the combined-fixture contrast recall gap (**0.87 vs 0.80**) is *smaller*
      than within-arm spread and should be withdrawn as a finding;
    - the detection padding gap (**0.75 vs 3.25**) is large enough to survive.
F3. The control arm varies more than the humane arm, because a procedure that
    prescribes what to check should produce more repeatable output than one that
    does not. This is the only place I expect the skill to show an advantage
    that none of the seven pathways looked for.

### What would falsify it

Spread small enough that every reported gap survives. Then the existing numbers
are firmer than I have been claiming, and the caveats can be softened rather
than the findings withdrawn.

---

## Pathway G — the same evals with a weaker reviewer

Four null results have been explained by the reviewer being strong. If that is
right, humane's discipline is **insurance**: worth nothing when the reviewer
would have been careful anyway, and worth a lot when it would not. Insurance is
testable — you make the bad case happen.

**Method.** Re-run existing fixtures with **Haiku** in both arms, changing
nothing else. Two pathways:

- **coverage honesty** (3 seeds) — the purest null on Opus. Both arms abstained
  correctly, 6/6, when the colours were unknowable.
- **detection** (2 seeds) — where Opus showed the largest gap.

### Predictions

G1. **Haiku's control is materially worse than Opus's control** on contrast
    recall. If it is not, the fixture is too easy to separate anything and G
    cannot answer its question.
G2. **The honesty pathway separates on Haiku.** At least one Haiku control run
    produces a `false_clear` or an omitted contrast row over colours it could
    not resolve, while the Haiku humane arm abstains honestly on all three. This
    is the insurance hypothesis stated so it can fail.
G3. **The with/without gap is wider on Haiku than on Opus** for at least one
    metric.

### What would falsify it

No separation on Haiku either — both arms abstain honestly, and the detection
gap is no wider than Opus's. Then the insurance explanation is wrong too, and
four null results need a different account than the one I have been giving. That
would be the most interesting outcome available here, and the one I would least
like.

### What neither can show

F uses one fixture; variance may differ by fixture difficulty. G changes the
model and nothing else, so it says nothing about other weaker models, or about
whether the discipline helps a *hurried* strong reviewer rather than a weak one.
No significance test will be reported at either sample size.
