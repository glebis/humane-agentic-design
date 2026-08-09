---
name: respondent-panel
description: Run a panel of independent synthetic respondents against copy, a slogan, brand values, a landing page, or any user-facing text — each in an isolated context, each a different specific person — then read the panel for convergence and divergence. Use when the user asks "how does this land", "what would people think of this", "test this tagline", "get reactions to this copy", "run a panel", or wants gut-level audience reaction rather than expert critique. Complements persona-review, which is expert stakeholder critique of a document. Triggers on respondent panel, how does this land, what would people think, test this tagline, reactions to this copy, gut reaction, audience reaction.
handoffs:
  - to: ux-writing
    when: the panel shows copy landing wrong and the rewrite is owed
accepts:
  - from: type-specimen
  - from: ux-writing
  - from: prototype
---

# Respondent Panel

**Announce at start:** "I'm using the humane:respondent-panel skill to collect gut reactions from isolated synthetic respondents."

Gut-level audience reaction to something user-facing, from several people at once,
each of whom has seen **only the thing itself**.

One reaction is an anecdote. Five reactions that all stumble on the same word is a
finding. This skill is about getting the second one.

## When to invoke

- "How does this tagline land?"
- "What would actual people think of this?"
- "Test this copy / these brand values / this landing page hero."
- "Run a respondent panel."
- After `jtbd` or `brandkit`, to check whether the language you landed on survives
  contact with someone who has not read the reasoning.

## When NOT to invoke

- The artifact is a **document meant to be studied** — a PRD, a spec, a pitch deck
  script. That is `persona-review`: expert stakeholders reading carefully and
  arguing back. This skill is strangers glancing.
- You want a **usability** judgement of an interface. That is `nielsen-heuristics`.
- You want the copy **fixed**. Respondents deliberately do not rewrite; bring their
  reactions back and revise yourself — `ux-writing` owns the rewrite, and knows to
  revise against convergent findings only.

## The one rule

**Respondents see the artifact and nothing else.**

Not the brief, not the JTBD corpus, not the positioning rationale, not the six
drafts you rejected, not what you were hoping they would feel. Every sentence of
context you add buys you a more agreeable answer and a less true one.

This is why respondents run in **isolated contexts** — a respondent that shares
your session has already read everything you know and cannot un-read it.

> **Claude Code extras:** launch each respondent as the bundled
> `synthetic-respondent` agent, all in a single message so they run concurrently
> and independently. Pass the artifact verbatim plus that respondent's persona
> brief — nothing else.
>
> **On other agents:** run them sequentially in **fresh sessions** (or after
> clearing context), pasting only the persona brief and the artifact. If neither
> is possible, run one respondent and say plainly in the output that it is a
> single uncontaminated reaction, not a panel.

## Workflow

### Step 1 — Get the artifact

Ask for the exact text or file to react to. Take it **verbatim**. Do not tidy
typos, expand abbreviations, or add the surrounding context you think is missing —
if it is missing for respondents, it will be missing for real readers, and that is
itself the finding.

Note the medium, because it sets the encounter: a billboard glimpsed at speed, an
app-store subtitle, a landing-page hero, a cold email subject line. Tell each
respondent where they are seeing it.

### Step 2 — Build the panel

Default to **5 respondents**. Three is thin; beyond seven you are paying for
repetition.

Vary them along axes that plausibly change the reaction to *this* artifact. Pick
3–4 axes and make each respondent specific:

| Axis | Why it moves the reaction |
|------|---------------------------|
| Relationship to the category | Newcomer vs. burned-before vs. current happy user of a competitor |
| Ad exposure | Someone who sees forty pitches a day is bored where a rare viewer is curious |
| Age / life stage | Changes what references land and what reads as dated |
| Place & language background | Idioms and wordplay travel badly; non-native readers catch ambiguity |
| Buying power over this | Someone who would pay reads the claims differently than someone who wouldn't |

Write each brief as a **person, not a segment** — two or three concrete sentences.
"38, runs a two-van plumbing business outside Leeds, has bought three scheduling
apps and abandoned all of them, reads nothing about software" beats "SMB owner,
skeptical."

**Ask the user to confirm the panel before spending on it**, and say which axes you
varied and why. If the artifact is aimed at a specific audience the user has already
described (a `jtbd.json` persona, a stated target market), build the panel around
that audience rather than a generic public — but keep at least one respondent from
outside it, because that is who tells you when the copy only works for insiders.

### Step 3 — Run them

All respondents get the identical artifact and medium. Only the persona brief
differs. Never tell a respondent what the others said.

### Step 4 — Read the panel

The panel is not a vote. Do not average the reactions or declare a winner. Report:

1. **Convergence** — anything two or more respondents independently hit. Same word
   misread, same confusion about what is being sold, same comparison to another
   brand. This is the strongest signal the method produces; lead with it and quote
   the respondents directly.
2. **Divergence** — where they split, and *along which axis*. If the newcomers liked
   it and everyone who has used a competitor was suspicious, that is a much more
   useful sentence than "reactions were mixed."
3. **Comprehension** — how many understood what is being sold, in one pass, without
   help. Report this as a count. It is often the real finding and it is easy to lose
   under the more colourful reactions.
4. **Dead spots** — parts of the artifact that no respondent mentioned at all. Copy
   nobody reacted to is copy nobody read.
5. **What actually landed** — the specific phrases that worked, named. A panel that
   only reports problems will get you a rewrite that loses the good parts.

Quote respondents verbatim rather than paraphrasing them into marketing language.
The unpolished phrasing *is* the evidence — "I thought it was an insurance thing"
survives translation into "brand-category confusion" badly.

### Step 5 — Hand off

State clearly what this panel is and is not: synthetic reactions that surface
confusion, clichés, and tone problems cheaply and early. They are a **rehearsal for
contact with real people, not a replacement for it**. Never present panel output as
market research, and never attach a confidence percentage to it.

Then offer the next step:

- Revise the copy with `ux-writing` against the convergent findings, then re-run the
  same panel — same briefs, so the comparison is clean.
- Run `before-after` if the artifact is claiming a transformation.
- Take the convergent findings to real users, if any are reachable.

## Output

Markdown. Convergence first, then divergence by axis, then comprehension count,
then dead spots, then what landed. Full individual reactions go at the end, under a
heading, so the reader meets the pattern before the anecdotes.
