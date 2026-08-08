---
name: nielsen-heuristics
description: Run a formal heuristic evaluation of a design artifact against Jakob Nielsen's 10 usability heuristics, producing an evidence-backed, severity-scored report with honesty guards. Accepts a screenshot, live URL, codebase/HTML, interface description, or JTBD/spec doc, and adapts its rigor to what is actually observable. Renders as markdown or a Tufte-style HTML report, and can export findings as Linear or Beads tasks after confirmation. Triggers on heuristic evaluation, usability review, Nielsen heuristics check, UX heuristic audit, usability inspection.
---

# Nielsen Heuristics Validator

> Mascot: `assets/jakob-nielsen.png` — a line-art portrait of Jakob Nielsen. Surface it (embed or attach) when producing a rendered/HTML report or a shareable summary, as the evaluation's signature. It is an output asset, not context to read while evaluating.

**Announce at start:** "I'm using the humane:nielsen-heuristics skill to evaluate this against Nielsen's 10 usability heuristics."

Run a rigorous, evidence-disciplined heuristic evaluation against Jakob Nielsen's 10 usability heuristics (Nielsen & Molich 1990, refined 1994). The value over an ad-hoc "critique this UI" prompt is a **consistent rubric plus honesty guards**: sharp per-heuristic probes, a per-finding severity scale, a mandatory evidence-locator requirement, and correct handling of artifacts that have no observable interface.

## Scope guard (read first)

This skill does ONE thing: a formal heuristic inspection. It does NOT run a parallel accessibility (WCAG) audit, performance audit, or general design critique. Flag an accessibility issue **only when it is also a heuristic violation** (e.g., an invisible focus state violates H1: visibility of system status). If the user wants comprehensive multi-dimension auditing, defer to `humane:review`, which orchestrates this skill alongside `layout-rules`, `ux-writing`, `walkthrough`, and `design-tokens` contrast — and marks the domains it cannot cover rather than improvising them. For post-build polish specifically, `impeccable:audit` is the right tool if installed.

## Step 1 — Detect artifact type and select a mode

Heuristic evaluation is an inspection of an *interface*. Some inputs have one to observe; some only describe one that does not yet exist. Detect the input type, then announce the mode and why.

**Evaluation mode** (observable interface → findings are severity-scored):
- **Screenshot / image** — read it visually.
- **Live URL** — drive it to observe states and flows, following
  `walkthrough`'s `references/driven.md` for the tool ladder, device matrix,
  and screenshot evidence contract (that file is the single owner of the
  driving procedure). A heuristic only observable on a tier that was not
  driven is **N/A at that tier**, not silently assessed from desktop.
- **Codebase / HTML page** — grep and read the UI source.

**Design-risk review mode** (interface described but not built → findings are UNSCORED risk flags):
- **Interface description** (text/markdown).
- **JTBD / spec document.**

Never assign a 0–4 severity to a pure spec or JTBD doc — there is no running system to observe, so a number would be speculation dressed as measurement. Reframe the question as *"which heuristics does this design direction put at risk when built."*

See `references/artifact-guide.md` for how to ingest each type, which heuristics are assessable vs. N/A for it, and which mode applies.

## Step 2 — Inventory (mandatory, before judging)

Enumerate the concrete units that will be examined BEFORE forming any finding. This is the structural safeguard against shallow, agreeable output.
- Evaluation mode: list the screens, key elements, and flows observed.
- Design-risk mode: list the spec sections / described flows.

Walk this inventory in Step 3. Do not evaluate from vibes.

## Step 3 — Walk all 10 heuristics

Load `references/heuristics.md` for the definition, "what to look for" probes, common violations, and the 0–4 severity rubric. For EACH of the 10 heuristics:

1. Produce **zero or more findings** (not exactly one — real evaluations have zero for some heuristics and several for others).
2. **Every finding MUST cite an evidence locator.** Unevidenced findings are disallowed. A locator is one of: a described screenshot region, a DOM element/CSS selector, a `file:line` reference, a quoted sentence from the spec, or the specific URL interaction performed.
3. In evaluation mode, assign a **severity 0–4** per finding. In design-risk mode, mark each as an **unscored risk flag** ("potential, unverified").
4. If a heuristic is **not assessable** from this artifact (e.g., undo/redo on a static screenshot), mark it **N/A** and state why.
5. If a heuristic has **no findings**, state **what was checked** ("checked X, Y, Z — no issues") — never silently bless it.

## Step 3b — Restraint, caps, and what you could not check

Three disciplines that apply before the report is written. They exist because a
rubric that walks 10 heuristics feels obliged to fill all ten, and a padded
evaluation is worse than a short one — it buries the real findings and teaches
the reader to skim.

**Cap the findings.** 15 in a full evaluation, 5 in a quick one. Never pad to
reach the cap; **a short evaluation, or none at all, is a valid result.** If the
artifact genuinely has more than the cap, report the highest-severity ones and
state plainly how many you left out and on what basis.

**Record what you considered and rejected.** Include 2–5 candidates you
inspected and deliberately did not report, with the reason: the convention is
intentional, the evidence is insufficient, the heuristic permits the current
behavior, or the change would add complexity without user benefit. These must be
real candidates encountered during the walk, not invented filler. If the scope
contained fewer borderline calls, list the ones that exist and say so.

**Never convert a verification gap into a finding.** If a state could not be
reached, a flow could not be driven, or a behavior was not observable in the
artifact, label it **Not verified** and say what remains. "I could not check the
error state" is a coverage note, not a severity-3 finding.

**Reviews do not mutate.** Treat an evaluation request as read-only. Do not edit
source, copy, or styles unless the user also asks for the fixes to be applied.
When they do, keep the report as the change scope and re-verify afterwards.

## Step 4 — Emit the report (choose an output format)

Findings are always **grouped by heuristic** with a **max-severity rollup**, followed by **Considered but Rejected**, **Top-3 prioritized fixes**, **Verification**, and the **Verdict**. Two render targets:

- **`markdown` (default)** — emit inline using `references/report-template.md`. Use this unless the user asks for a rendered/shareable report.
- **`tufte`** — a Tufte-style standalone HTML report. Follow `references/tufte-preset.md`: build the structured findings first, then invoke the `tufte-report` skill with that preset (which maps findings onto its strip-chart / status-strip / flyout blocks and uses `assets/jakob-nielsen.png` as the hero). Trigger when the user says "tufte report", "HTML report", "shareable report", or "make it pretty".

Select the format from the user's request; if ambiguous and they only said "report", default to `markdown`.

## Verdict (scoped — never "ready to ship")

A single evaluator finds only ~1/3 of usability problems (Nielsen); 3–5 evaluators are recommended for confidence. The verdict must carry this caveat and use these defined levels (evaluation mode):

- **Blockers present** — one or more severity-4 findings.
- **Major issues** — one or more severity-3, none at 4.
- **Minor issues only** — nothing above severity-2.
- **No blockers found in heuristic inspection** — clean pass, with the explicit single-evaluator caveat.

Design-risk mode produces a **risk summary** (which heuristics are most at risk, and what to specify to de-risk them) instead of a scored verdict — there are no severities to roll up.

**Mapping to the shared humane verdict.** So this composes with other review skills, also state one of: `Block` (any severity-4), `Needs changes` (anything actionable below that), or `Approve` (no actionable findings **and** the claimed coverage was verified). Keep the single-evaluator caveat attached to `Approve` — it means "clean in this inspection", never "ready to ship".

## Step 5 — Export findings as tasks (optional)

When the user asks to "create tasks", "file these", "make Linear issues", "open beads", etc., turn qualifying findings into tracker issues. Follow `references/task-export.md` for the exact command templates and field mapping.

Rules (all defaults overridable per run):
- **Threshold:** default **severity ≥ 3** (Major + Catastrophe). The user may set another (`≥ 4`, `≥ 2`). In **design-risk mode** there are no severities — only export flags the user explicitly selects or the "highest-risk" flags named in the risk summary, and say so.
- **Propose, then confirm (mandatory gate):** first print the list of tasks that WOULD be created — title, severity, target tracker, and the heuristic — and ask for confirmation. Create nothing until the user approves. This gate is required for Linear (outward-facing/cloud); keep it for Beads too.
- **Target:** **Linear** (`linear` CLI, cloud) or **Beads** (`bd` CLI, local/per-repo). Ask which if unspecified. Beads requires being inside the target repo (its `.beads` dir); confirm the repo before creating.
- **One task per finding**, titled `[H<n>] <short finding>`, with the evidence locator, fix, and severity in the body. Map severity → tracker priority per `references/task-export.md`.
- After creation, report back the created issue IDs/URLs.
