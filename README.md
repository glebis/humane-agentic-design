# Humane Agentic Design

Agent-produced interface slop is a method problem, not a model problem. A capable model still ships generic UI when it jumps straight to pixels with no idea who it is building for or under which constraints. The fix is not a better model — it is the method, installed next to the agent: what to build, for whom, under which constraints, then proof it got better. This plugin packages that method as a cycle, for people and for the agents working alongside them.

It is one plugin (`humane`) and its own single-entry marketplace.

```mermaid
flowchart LR
  J[jtbd<br/>what people hire] --> P[persona-review<br/>synthetic-respondent<br/>who reacts, and how]
  P --> T[design-tokens<br/>the system]
  T --> L[layout-rules<br/>execution constraints]
  L --> N[nielsen-heuristics<br/>the classic audit]
  N --> B[before-after<br/>proof]
  B -. next iteration .-> J
```

## The cycle

Each skill knows its place in the method. Run them in order for a new project, or reach for any one on its own.

1. **jtbd** — what people are hiring the product to do. Interview fast, kill jargon, capture the real switching forces (Push / Pull / Habit / Anxiety), score opportunities, export a decision-grade brief.
2. **persona-review** / **synthetic-respondent** — who reacts and how. `persona-review` stress-tests a document from several stakeholder viewpoints; the `synthetic-respondent` agent gives an unfiltered gut reaction to copy and branding as an everyday consumer.
3. **design-tokens** — the system. Define brand tokens (DTCG 2025.10), layer a project's tokens over a global base, compile to CSS variables, and produce an on-brand context file for other generators.
4. **layout-rules** — execution constraints. A battle-tested avoid-list of layout and dashboard defects, applied before and after you write any HTML/CSS.
5. **nielsen-heuristics** — the classic audit. A rigorous, evidence-backed, severity-scored evaluation against Nielsen's 10 usability heuristics.
6. **before-after** — proof. Show the change worked, side by side.

## Install

### Claude Code

```
/plugin marketplace add glebis/humane-agentic-design
/plugin install humane@humane-agentic-design
```

The skills then activate on their triggers; the `synthetic-respondent` agent becomes available to launch.

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
3. **Pressure-test with people.** Run `humane:persona-review` on the brief, or launch the `synthetic-respondent` agent against your copy for a gut reaction with no politeness filter.
4. **Set the system.** `humane:design-tokens` turns the brand into DTCG tokens and compiled CSS variables before any layout exists.
5. **Build under constraints.** Before writing HTML/CSS, load `humane:layout-rules` and treat its avoid-list as hard rules; audit the result with `humane:nielsen-heuristics`.
6. **Prove it.** `humane:before-after` shows the change worked; feed what you learned back into step 1.

Two commands ship with the `jtbd` skill for looking at the corpus:

```
python3 <plugin>/skills/jtbd/scripts/graph.py            # interactive corpus viewer (11 views)
python3 <plugin>/skills/jtbd/scripts/report.py exec-summary <slug>   # one-page stakeholder summary
```

## Learn the method live

The cycle is taught hands-on at the [Agentic Design Lab](https://ai-design.salient.community/) — a 5-week cohort where designers, PMs, and founders build real products with agents using exactly this method. Current cohort dates are on the site.

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

**Ring 2**: `brand-illustrate` (shipped) — a questionnaire-driven pipeline that turns the token set into coherent, platform-sized illustration batches via whichever image backend is installed. Planned next: `brandkit` (brand boards between jobs and tokens) and `dataviz` (chart constraints, the layout-rules of data).

## License

MIT © Gleb Kalinin
