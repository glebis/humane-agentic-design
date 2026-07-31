# Humane Agentic Design

![The humane cycle — jtbd, persona-review, design-tokens, layout-rules, nielsen-heuristics, before-after, looping back; brandkit and brand-illustrate feed the token set](assets/cycle.svg)

> Taught live at the **[Agentic Design Lab](https://ai-design.salient.community/)** — a 5-week cohort where designers, PMs, and founders build real products with agents using exactly this method.

Agent-produced interface slop is a method problem, not a model problem. A capable model still ships generic UI when it jumps straight to pixels with no idea who it is building for or under which constraints. The fix is not a better model — it is the method, installed next to the agent: what to build, for whom, under which constraints, then proof it got better. This plugin packages that method as a cycle, for people and for the agents working alongside them.

It is one plugin (`humane`) and its own single-entry marketplace.

## The cycle

Each skill knows its place in the method. Run them in order for a new project, or reach for any one on its own.

### 1. `jtbd` — what people are hiring the product to do

A terminal-first Jobs-to-Be-Done engine. It runs a focused interview one question at a time, kills jargon as you speak it, and captures the four switching forces — Push (what hurts today), Pull (what attracts), Habit (what keeps them stuck), Anxiety (what scares them off). It also ingests material you already have: voice transcripts, customer-review exports, sales-call notes.

- **Outputs:** `~/jtbd/<slug>/jtbd.json` (the machine-readable corpus every later step reads), `one-pager.md`, `messaging-angles.md` derived from the Switch forces, and a GTM brief.
- **Also does:** ODI-style opportunity scoring — each outcome gets importance / satisfaction and one of the eight process stages, so "underserved" is a number, not a hunch. Evidence gets ids (`[E1]`, `[Q2]`) you can cite later.
- **Tools:** `scripts/graph.py` (interactive corpus viewer, 11 views), `scripts/report.py exec-summary <slug>`.
- **Reach for it when:** you're deciding what to build, rewriting positioning, or turning a pile of interviews into something decision-grade.

### 2. `persona-review` + `respondent-panel` — who reacts, and how

Two pressure tests in different registers — experts reading carefully, and strangers glancing.

**`persona-review`** reviews a document from N stakeholder viewpoints. Pass names (`engineer,designer,exec`) or let it pick 3 relevant ones by document type (PRD → skeptical engineer / UX designer / business stakeholder; pitch → customer / investor / competitor). Each persona reads independently and returns perspective, gut reaction, and specific objections; the document can optionally be revised against the feedback in the same pass.

**`respondent-panel`** is the opposite: no expertise, no politeness filter, and — critically — **no context**. It runs ~5 synthetic respondents against a slogan, brand values, or a landing-page hero, each in an isolated context that has seen the artifact and nothing else. No brief, no rationale, no rejected drafts. Then it reads the panel for *convergence* (two respondents stumbling on the same word is the finding), divergence by demographic axis, a plain comprehension count, and dead spots — copy nobody reacted to is copy nobody read.

- **Reach for it when:** a brief or PRD is about to go out and you want the objections before the meeting (`persona-review`); or copy is about to go live and you want to know how it lands on someone who hasn't read your reasoning (`respondent-panel`).
- **Claude Code extra:** `respondent-panel` runs on the bundled `synthetic-respondent` agent, launched concurrently for real context isolation. On other agents it degrades to fresh sessions run one at a time.
- **Honest about itself:** synthetic reactions surface confusion, clichés, and tone problems cheaply and early. They are a rehearsal for contact with real people, not a replacement for it — the skill refuses to attach confidence numbers or call itself market research.

### 3. `design-tokens` — the system, before any pixels

A dependency-free Python core over [DTCG Format Module 2025.10](https://www.designtokens.org/tr/drafts/format/). It scaffolds a token set, validates it, resolves `{alias}` references, and exports CSS custom properties. Its distinctive move is **layering**: a global brand base merged with a project override, so ten projects share one identity without copy-pasting hex codes.

- **Outputs:** validated `*.tokens.json`, compiled CSS variables, `DESIGN.md` — a single generated brand render with provenance and a stale guard — and an on-brand context file that downstream generators (including `brand-illustrate`) read as their style contract.
- **Reach for it when:** starting any project that will have a UI, or consolidating a brand that currently lives in a Figma file and three people's heads.

### 4. `layout-rules` — execution constraints

An avoid-list of **39 defect classes** for tool, dashboard, viewer, and admin UIs — every one of them a bug or design smell actually caught in a real build-and-audit cycle, not a style opinion. Sections cover structure & hierarchy, footers/metrics/copy, tables & lists, color & contrast, URL state, JS traps, interaction correctness, accessibility & touch, i18n & theming, and de-slop.

- **How it's used:** as *constraints in the plan* before you design, as enforcement while building, and as a post-build checklist — screenshot-tested in a real browser, on both themes, and against an empty dataset.
- **Reach for it when:** before writing the first line of HTML/CSS for anything tool-like. This is the single highest-leverage skill for stopping agent slop.

### 5. `nielsen-heuristics` — the classic audit

A formal heuristic evaluation against Nielsen's 10 usability heuristics (Nielsen & Molich 1990, refined 1994). What it adds over "critique this UI" is a **consistent rubric plus honesty guards**: sharp per-heuristic probes, a per-finding severity scale, and a mandatory evidence locator — a finding without a pointer to where it happens doesn't ship.

- **Accepts five input types:** screenshot, live URL, codebase/HTML, a written interface description, or a JTBD/spec doc — and adjusts its rigor honestly to what is actually observable.
- **Outputs:** markdown by default, or a Tufte-style HTML report; findings above a severity threshold can be exported as Linear or Beads tasks after confirmation.
- **Scope guard:** it does one thing. Accessibility issues are flagged only when they're also heuristic violations; for multi-dimension auditing it defers to `impeccable:audit`.

### 6. `before-after` — proof

Emotional Before/After transformation grids — the felt shift, not a feature list. It chains directly from `jtbd.json` (Push → primary BEFORE, Pull → primary AFTER, Anxiety → fear dimension flipped to confidence, and so on) or runs standalone from a 3-question interview. Cells are written in first person ("I check my dashboard with dread every morning" → "I glance at costs once a week, casually"), with somatic markers and valence scoring.

- **Outputs:** a 5–9 dimension grid ready to drop into a landing page, a slide, or messaging.
- **Reach for it when:** you need to show a change worked — or to articulate the transformation you're selling. If you can't fill the grid, question the change.

### Ring 2 — brand identity

Two extra skills sit alongside the cycle for visual identity work:

- **`brandkit`** (upstream of tokens) — explores a brand that *doesn't exist yet*. Generates premium brand-guidelines boards for several competing directions — logo systems, mockups, art-directed imagery — and then hands the winning direction into the `design-tokens` brand block via a confirm-then-write handoff, so a token set is born with its art direction attached.
- **`brand-illustrate`** (downstream of tokens) — produces assets under an *existing* token contract. It reads the palette, fonts, shape language, and brand block, runs a short one-question-at-a-time questionnaire, merges the `layout-rules` de-slop negatives into the prompt, and generates a batch that reads as one family. Generators live outside the plugin: it shells out to whichever backend is installed (`gpt-image-2`, `nano-banana`) and stops with instructions if none is. Saves a reusable recipe and builds a cross-batch contact-sheet gallery of every version.

## Install

### Claude Code

```
/plugin marketplace add glebis/humane-agentic-design
/plugin install humane@humane-agentic-design
```

The skills then activate on their triggers, and the `synthetic-respondent` agent becomes available for `respondent-panel` to launch (or for you to launch directly, one reaction at a time).

### Any other agent (Codex, and others) via npx skills

The skills are stdlib-only and self-contained. Add them to any agent that reads the `skills` convention:

```
npx skills add glebis/humane-agentic-design
```

Point your agent at the `humane/skills/` directory, or copy the individual skill folders into wherever your agent loads skills from.

## How to use it

Start a new product idea and let the cycle carry it end to end:

1. **Capture the job.** Say `describe my project with humane:jtbd` (or paste customer reviews / an interview transcript). The interview produces `~/jtbd/<slug>/jtbd.json` — the corpus every later step reads.
2. **Score and stage the outcomes.** Ask for the ODI pass: each outcome gets importance / satisfaction and one of the eight process stages. Honest scores beat flattering ones — `creator-estimate` is a valid, labeled source.
3. **Pressure-test with people.** Run `humane:persona-review` on the brief for expert objections, then `humane:respondent-panel` on the copy for gut reactions from people who have read none of your reasoning.
4. **Set the system.** `humane:design-tokens` turns the brand into DTCG tokens and compiled CSS variables before any layout exists.
5. **Build under constraints.** Before writing HTML/CSS, load `humane:layout-rules` and treat its avoid-list as hard rules; audit the result with `humane:nielsen-heuristics`.
6. **Prove it.** `humane:before-after` shows the change worked; feed what you learned back into step 1.

Two commands ship with the `jtbd` skill for looking at the corpus:

```
python3 <plugin>/skills/jtbd/scripts/graph.py            # interactive corpus viewer (11 views)
python3 <plugin>/skills/jtbd/scripts/report.py exec-summary <slug>   # one-page stakeholder summary
```

## Learn the method live

Reading a method is not the same as running one. The full cycle — jobs, personas, tokens, layout constraints, heuristic audits, proof — is taught hands-on at the **[Agentic Design Lab](https://ai-design.salient.community/)**: a 5-week cohort where designers, PMs, and founders ship a real product with agents, using exactly these skills, with critique on each stage. Current cohort dates and the syllabus are on the site.

→ **[ai-design.salient.community](https://ai-design.salient.community/)**

## Works with any agent

The core skills carry no absolute paths and no Claude-only tool imperatives — they say "ask the user", not any one tool's name, and their scripts use only the Python standard library. Where a capability is genuinely Claude Code specific (the bundled Linear CLI for task export, the `synthetic-respondent` agent format), it is called out under a "Claude Code extras" note rather than assumed. On other agents, those steps degrade gracefully to plain instructions.

## Humane and Impeccable

They complement each other. **Humane** is the method and system *before* code: what to build, for whom, under which constraints — jobs, personas, tokens, layout rules. **Impeccable** is interface quality *after*: audit, normalize, polish, harden. A project that runs both starts from evidence and ships without slop. Install both.

## For agents

You, the agent reading this: consult the cycle before adding or changing anything user-facing.

- Before any UX edit, read the project's `jtbd.json` corpus (if present) and check which jobs your change touches. Do not add friction to an outcome marked underserved.
- Before writing any HTML/CSS, load `layout-rules` and treat its avoid-list as hard constraints, not suggestions.
- When you justify a design decision, cite evidence ids from the corpus (`[E1]`, `[Q2]`) — an unreferenced claim is an assertion, not a finding.
- After a change, produce a `before-after` artifact. If you cannot show the difference, question the change.

## Roadmap

**Ring 2**: `brand-illustrate` (shipped) — turns the token set into coherent, platform-sized illustration batches via whichever image backend is installed. `brandkit` (shipped) — its upstream twin: explores competing identity directions as premium brand boards and hands the winning direction into the design-tokens brand block, so a token set is born with its art direction. Planned next: `dataviz` (chart constraints, the layout-rules of data).

## License

MIT © Gleb Kalinin
