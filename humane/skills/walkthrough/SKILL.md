---
name: walkthrough
description: Task-based evaluation of a real interface — take one job from the JTBD corpus, attempt it step by step as the person who has it, and record where the attempt breaks. Answers "can someone actually complete this?", which inspection and reaction methods do not. Runs a cognitive walkthrough (four questions per step) against a live URL, a prototype, screenshots, or the code, and reports task success against the outcome it was derived from. Use when you have a task and something operable to attempt it on. Triggers on walkthrough, cognitive walkthrough, task analysis, "can a user actually do this", "test this task", "where do people get stuck", "walk through the signup flow", "пройди сценарий".
---

# Walkthrough

Inspection asks whether an interface obeys principles. Reaction asks how words
land. Neither asks the question that decides whether the product works: **can
this person, with this goal, get through?**

A walkthrough answers that by attempting the task — one concrete task, one
concrete person, one step at a time — and recording exactly where the attempt
would break.

## When to invoke — and when not

Reach for this when you have a task and something to attempt it on.

| You want | Skill |
| --- | --- |
| Can someone complete this task? | **this skill** |
| Does the interface violate usability principles? | `nielsen-heuristics` |
| How does this copy land with strangers? | `respondent-panel` |
| Would an expert stakeholder object to this document? | `persona-review` |
| Did the change actually improve things? | `before-after` (feed it these results) |

Do not run this on a spec or a description. A walkthrough needs something to
*operate*. If all you have is a document, `nielsen-heuristics` design-risk mode
is the honest substitute — say so and switch.

## Step 1 — Derive the task from the corpus, not from the interface

The most common way this method fails is walking the flow the designer built
instead of the job the person has. Guard against it by taking the task from
outside the interface.

1. **Read `<corpus_root>/<slug>/jtbd.json`** — `corpus_root` is the `setup`
   setting, default `~/jtbd`; read the configured value, not the default.
   Prefer a task derived from an
   `odi.outcomes[]` entry — those already carry a `stage` (one of
   define/locate/prepare/confirm/execute/monitor/modify/conclude) and a `touch`
   (the surface it lives on). An underserved outcome (high importance, low
   satisfaction) is the highest-value thing you can walk.
2. **Write the task as the person's goal**, in their words, with no interface
   nouns in it. "Find out what I spent on models last week" — not "open the
   billing dashboard and apply a date filter." If your task statement names a
   button, you have already assumed the answer.
3. **Name the actor and their entry state.** Who they are, what they already
   know, what they have already done, where they arrive from, on what device.
   Use the corpus `actor` and `jtbd.situation`. First-time and returning users
   walk different paths through the same screens — pick one and say which.
4. **State the success condition** — the observable thing that is true when the
   job is done. This is what "task success" is measured against, and it must be
   decided *before* the walk.

If no corpus exists, ask the user for the task and the actor, and record in the
output that the task was supplied rather than derived. That is a weaker basis and
the reader should know.

## Step 2 — Pick the mode honestly

| Mode | Artifact | What you can claim |
| --- | --- | --- |
| **Driven** | Live URL or running app | Strongest. You observed real behavior, real states, real errors. |
| **Prototype** | Clickable prototype, or an ordered set of screenshots | You observed intended behavior. Anything not prototyped is unknown, not working. |
| **Static** | Screenshots with no flow | You can assess each step's affordances, not the transitions between them. |
| **Code** | Source only | You can reconstruct the intended flow. You cannot claim what renders. Weakest — pair it with one of the above whenever possible. |

Announce the mode and its ceiling in the output. Never let a code reading
masquerade as an observation.

> **Claude Code extras:** in driven mode use the browser tools to navigate,
> click, fill, and screenshot each step; capture a screenshot per step as the
> evidence locator. On other agents, drive whatever browser automation is
> available, or ask the user to perform the steps and describe what happened.

## Step 3 — Walk it, one step at a time

A step is one decision the person makes, not one screen. A screen with three
plausible next actions is three steps' worth of decision.

At every step, answer the four cognitive-walkthrough questions. Each gets a
yes/no and a reason:

1. **Will they try to achieve this effect?** Does the person, at this moment,
   actually want to do this sub-goal — or is it something the system needs and
   they don't care about?
2. **Will they notice the control is available?** Is it visible, in the scan
   path, not below the fold, not hidden behind a hover or a menu?
3. **Will they connect the control to the effect they want?** Does the label,
   icon, or position say what it does *in their vocabulary*? (This is where
   `habit` from the switch forces bites: they are looking for the old product's
   word.)
4. **Will they see that progress was made?** After acting, is there feedback
   that they got closer — or does the system go quiet and leave them guessing?

**Any "no" is a break.** Record it with:

- the step number and what the person was trying to do,
- which of the four questions failed,
- the evidence locator (screenshot, URL, `file:line`, or the exact element),
- what the person most likely does next: recover, take a wrong path, or abandon.

That last field is what makes a walkthrough actionable. A break the user
recovers from in one second is not the same defect as one that sends them into a
dead end, even when the same question failed.

**Do not fix as you go.** Walk the whole task first. Stopping to redesign at the
first break hides everything downstream of it, and downstream breaks are often
the worse ones.

## Step 4 — Walk the unhappy paths too

A task that only works when nothing goes wrong is not a task that works. Once
the happy path is walked, walk at least the applicable ones:

- **empty** — first run, nothing created yet
- **error** — the request fails, the input is rejected, the connection drops
- **slow** — the response takes 10 seconds; what does the person see and do?
- **interrupted** — they navigate away and come back, or reload mid-task
- **permission** — they lack access to something the path requires

Reloading mid-task is the cheapest high-yield check there is: if state does not
survive it, `layout-rules` rule 16 is violated and the task is fragile in a way
no happy-path walk reveals.

## Step 5 — Report

### Task and basis

The task in the person's words, the actor and entry state, the success
condition, the corpus outcome it came from (with its importance/satisfaction if
scored), the mode, and the mode's ceiling.

### Walk

One row per step. Keep the steps the person passed — a walkthrough that lists
only failures cannot show how far they got before breaking.

| # | Goal at this step | Q1 try | Q2 notice | Q3 connect | Q4 feedback | Evidence | Likely next |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 3 | Narrow to last week | yes | **no** | — | — | `step-3.png`, date control below fold | scrolls, or gives up on filtering |

### Findings

The breaks, consolidated and ranked — one root cause per row, listing every step
it affected:

| Severity | Step(s) | Question | Location | Before | After | Why |
| --- | --- | --- | --- | --- | --- | --- |

`Step(s)` and `Question` are this skill's two additions to the shared five-column
findings table — they carry where in the walk the break happened and which of the
four questions failed, which no other domain has. **Under `review`, drop them**:
that skill owns the consolidated format, and a wider table cannot merge with the
others. Fold the step and question into *Why* instead of losing them.

- `HIGH` — the task cannot be completed, or completes wrongly without the person
  noticing.
- `MEDIUM` — the task completes, but through recovery, a wrong turn, or
  unreasonable effort.
- `LOW` — friction that a person absorbs without deviating.

Cap at 15; never pad. Route each finding to its owner rather than solving it
here: wording to `ux-writing`, a defect class to `layout-rules`, a principle
violation to `nielsen-heuristics`, a contrast measurement to `design-tokens`.

### Considered but Rejected

Two to five steps that looked like breaks and were not, with the reason — the
convention is learnable, the affordance is discoverable in one scan, the
recovery is immediate.

### Verification

Every state actually reached, and how. Unhappy paths that could not be triggered
are **Not verified**, with what remains — never reported as failures. "I could
not make the payment fail" is a coverage gap, not a finding.

### Verdict

Both of these:

- **Task success:** `Completed` · `Completed with recovery` · `Completed
  incorrectly` · `Blocked at step N`.
- **Overall:** `Block` (any HIGH), `Needs changes` (only MEDIUM/LOW), `Approve`
  (no actionable findings and the claimed coverage was verified).

## What this method is and is not

This is an **analytical** walkthrough performed by an agent reasoning about a
person, not a usability test with a real person. It reliably surfaces missing
affordances, vocabulary mismatches, silent failures, and dead ends — cheaply and
before anyone is recruited. It cannot tell you how long something takes, how
frustrating it feels, or what people do that no one anticipated.

Never report it as a usability study, never attach a task-success *percentage*
to it, and never let it be the reason not to watch one real person try. Two
evaluators walking the same task independently find noticeably more than one; if
that is affordable, do it and merge.

## Handoff

- Breaks fixed → re-walk the *same* task, same actor, same success condition, so
  the comparison is clean.
- Task now completes → `before-after` can use the walk as the evidence that the
  change worked. A before/after grid backed by a blocked-then-completed task is
  a claim with a receipt.
- Outcome still underserved after the fix → back to `jtbd`; the problem may be
  the job, not the flow.
