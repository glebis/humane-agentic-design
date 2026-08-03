---
name: setup
description: Get humane working on this machine — check what the cycle needs, configure the corpus root, token base, image backend, task-export target and language, and install the companions and generators that are missing. Diagnoses read-only first, then installs only what the user confirms. Use on a fresh machine, when a skill complains something is missing, or to see how humane is currently configured. Triggers on humane setup, set up humane, configure humane, humane doctor, "what do I need to install", "why can't it find my tokens", "check my humane install", "настрой humane".
---

# Setup

Two jobs, in this order: **find out what is actually wrong**, then **fix only
what the user agrees to fix**. Never the other way round — a setup flow that
installs first and reports afterwards is one that installs things nobody wanted.

```bash
scripts/humane_setup.py doctor          # read-only: config + every check + the fix for each gap
scripts/humane_setup.py config          # show resolved configuration and where each value came from
scripts/humane_setup.py config --set language=ru [--scope project]
scripts/humane_setup.py settings        # what each setting means
```

`doctor` writes nothing, installs nothing, and never asks for a key. It exits 1
only on a genuinely blocking gap; missing optional pieces exit 0, because most
of the cycle works without them.

## Configuration

Five settings, resolved highest-precedence first: **project `humane.json` >
`~/.humane/config.json` > `HUMANE_*` environment > built-in default**. `doctor`
and `config` print the source beside every value, so "why is it using that
path?" is always answerable.

| Setting | Default | What depends on it |
| --- | --- | --- |
| `corpus_root` | `~/jtbd` | where `jtbd` writes; every later skill reads it |
| `token_base` | `~/design-tokens/base.tokens.json` | the global brand a project layers over |
| `image_backend` | `auto` | which generator `brand-illustrate` shells out to |
| `task_export` | `none` | where `nielsen-heuristics` files findings (`linear`, `beads`, `none`) |
| `language` | `en` | the language skills speak; captured evidence is never translated |

Project beats environment deliberately: a repo that pins its corpus root should
win over a variable that happens to be exported in the shell. Set a value in the
project file when it belongs to the project, and globally when it belongs to you.

## Step 1 — Run the doctor and read it aloud

Run `doctor` and walk the output with the user. Report gaps as facts, not
alarms: most are optional, and the cycle degrades honestly without them.

- **corpus** — no bundles yet is the normal state of a new machine, not an
  error. The fix is to run `humane:jtbd`, which creates it.
- **token base** — only needed if they want a shared brand across projects. A
  single-project user never needs one.
- **image backend** — optional. Without it `brand-illustrate` still writes every
  prompt to `prompts.md`; it just cannot generate in place.
- **companions** — `interfaces` and `impeccable` are separate plugins humane
  defers to. Absent is fine; the review skills mark those domains **Not
  reviewed** rather than improvising rules they do not own.
- **humane copies** — other installed copies of humane's own skills, and
  whether they have drifted from this checkout. See below; this is the check
  most likely to surprise someone.

### Drift between copies

*Minimize drift between copies of a skill* is a named outcome of this project,
and it is the one failure the method cannot catch by reading a repo. A copy that
has silently lost a file is far harder to notice than one that is merely old —
on the machine this check was written for, `~/.codex/skills/jtbd` was missing
`scripts/graph.py`, so Graph Mode simply did not exist on that agent and nothing
said so.

The doctor enumerates the known skill roots and the registered plugin
marketplace, then classifies each copy it finds:

| State | Meaning |
| --- | --- |
| linked | a symlink back into this checkout — the good case, nothing to do |
| links to a different source | a symlink into another repo; two skills share one name |
| missing N file(s) | named explicitly, because *which* file is the whole point |
| identical for now | an independent copy that matches today and will drift the moment either side moves |

A **registered marketplace pins a commit**, so it reports itself perfectly in
sync with its own remote while sitting versions behind the repo. The check
compares version and skill count against this checkout instead, which is the
only comparison that catches it.

None of this blocks. Drift is reported, never auto-repaired: re-installing over
a copy someone is mid-edit on would be worse than the drift.

## Step 2 — Ask before configuring

Walk the settings that are still on defaults, one at a time, and only the ones
that matter for what the user is doing. Do not interview someone through five
questions they have no opinion on — a first-time user usually needs
`corpus_root` confirmed and nothing else.

> **Claude Code extras:** use `AskUserQuestion` for the pick-one steps
> (`language`, `task_export`, `scope`). On other agents ask in plain text.

Then write it, naming the file and scope out loud:

```bash
scripts/humane_setup.py config --set corpus_root=~/work/jtbd --scope global
scripts/humane_setup.py config --set language=ru --scope project
```

## Step 3 — Install what they confirm

The doctor prints the exact command for every gap. **Run them yourself only
after the user says yes, one at a time, showing the command first.** Each of
these reaches outside the repo, and two of them need money or credentials.

| Gap | Command | Note |
| --- | --- | --- |
| `interfaces` | `/plugin marketplace add jakubkrehel/skills` then `/plugin install interfaces@interfaces` | Claude Code plugin |
| `impeccable` | `/plugin install impeccable` | Claude Code plugin |
| humane on another agent | `npx skills add glebis/humane-agentic-design` | **interactive** — four prompts: agents, scope, method, confirmation. Choose scope deliberately (see below) |
| image generator | install `gpt-image-2` or `nano-banana` into any skills dir | needs `OPENAI_API_KEY` or `GEMINI_API_KEY` |
| token base | `tokens setup-edit ~/design-tokens/base.tokens.json` | runs the `design-tokens` questionnaire |
| task export | install the `linear` or `bd` CLI | or set `task_export=none` |

**On install scope.** `npx skills add` defaults to *Project*, which puts a copy
in `./.agents/skills`. That copy will drift from a global one, and drift between
copies of a skill is a known failure of this method — pick global unless the
user genuinely wants this project pinned, and say which you chose.

**Never store a key.** If a generator needs `OPENAI_API_KEY` or
`GEMINI_API_KEY`, say which variable is missing and let the user place it in
their own secret store. This skill does not read, write, print, or pass keys.

## Step 4 — Re-run the doctor

Verify the change rather than declaring success. Show the before/after gap count
and stop. If something still fails, say so plainly with the remaining fix —
`doctor` exiting non-zero is a result, not a reason to keep trying commands.

## Guardrails

- **Diagnose before you change.** Always `doctor` first, always show output.
- **Confirm every install.** These commands touch directories outside the repo,
  cost money, or hold credentials. No silent installs, ever.
- **Never handle secrets.** Name the missing variable; never ask for its value.
- **Absent is a valid state.** Report a missing optional piece with what it
  would enable, not as a failure to be fixed.
- **The script stays read-only.** `humane_setup.py` diagnoses and edits its own
  config file — nothing else. Installs are run by the operator with the user
  watching, because a doctor that installs silently is a doctor you stop
  trusting.

## Tests

```bash
cd setup && python3 -m unittest discover -s tests -v
```
