# Every path a humane skill writes

One place to look up where an artifact goes, and which setting moves it. If a
skill writes something that is not in this table, that is a bug in the skill —
add the row, do not invent a path at the call site.

## The two roots

| Setting | Default | Holds |
| --- | --- | --- |
| `artifact_root` | `.design` | generated artifacts, beside the thing being designed |
| `corpus_root` | `~/jtbd` | the JTBD corpus and everything derived directly from it |

They differ in kind. A corpus is usually personal and global — one place you
keep every project's jobs. An artifact usually belongs with the code it
describes, so it travels with the project and can be committed with it.

**A relative `artifact_root` resolves against the project directory, never the
current working directory.** That distinction is the whole point of the setting:
a CWD-relative default is what once wrote a prototype into this plugin's own
source tree, and `.design` would reintroduce it exactly — an agent standing
anywhere would create `.design` right there.

```bash
scripts/humane_setup.py config --set artifact_root=docs/design --scope project
scripts/humane_setup.py config --set artifact_root=~/design --scope global
```

## The naming rule

Every artifact is named for the skill that made it, in one flat directory:

```
<project>/.design/
    prototype-dashboard.pen        prototype
    prototype-checkout.html        prototype
    specimen-headings.html         type-specimen
    board-editorial.png            brandkit
    illustration-onboarding/       brand-illustrate — a batch, so a directory
    walk-signup/                   walkthrough — screenshots per step per tier
    review-2026-08-09.md           review, nielsen-heuristics
```

A flat directory sorts by kind, and the prefix tells a reader which skill made a
file without opening it. Resolve it rather than building it:

```python
from humane_setup import artifact_path
artifact_path("dashboard", "prototype", "pen")   # -> <project>/.design/prototype-dashboard.pen
artifact_path("signup", "walkthrough")           # -> <project>/.design/walk-signup   (a directory)
```

Omit the extension for a kind that produces several files and you get a
directory of the same name. `artifact_path` refuses an unknown kind and refuses
a name containing `/` or starting with `.`, so a bad caller fails loudly.

## The full table

| Skill | Writes | Where | Anchor |
| --- | --- | --- | --- |
| `jtbd` | `jtbd.json`, one-pager, messaging angles, GTM brief | `<corpus_root>/<slug>/` | `corpus_root` |
| `before-after` | `before-after.json`, `.md`, `-visual.png` | `<corpus_root>/<slug>/` | `corpus_root` |
| `prototype` | ASCII sketch, SVG click-dummy, HTML prototype | `.design/prototype-<name>.html` | `artifact_root` |
| `prototype` | editable design file (`.pen`) | **wherever its application keeps documents — see below** | not enforceable |
| `type-specimen` | `specimen.json`, the built specimen page | `.design/specimen-<name>.html` | `artifact_root` |
| `brandkit` | brand boards, `direction.json`, `brand-block.draft.json` | `.design/board-<name>/` | `artifact_root` |
| `brand-illustrate` | images, `prompts.md`, `metadata.json`, contact sheet, recipe | `.design/illustration-<batch>/` | `artifact_root` |
| `walkthrough` | `step-NN-<tier>.png` per step per tier | `.design/walk-<task>/` | `artifact_root` |
| `review` · `nielsen-heuristics` | a saved report, **when the user asks for a file** | `.design/review-<date>.md` | `artifact_root` |
| `design-tokens` | `tokens.css`, `DESIGN.md`, `refs.json` | **beside the token file it compiled** | the input path |
| `persona-review` | `<doc>-persona-review.md` | **beside the document it reviewed** | the input path |
| `respondent-panel` · `ux-writing` · `layout-rules` | nothing — reported inline | — | — |

## Three rules that are not negotiable

**Never write to the current working directory.** A CWD-relative default puts a
user's artifact wherever the agent happened to be standing. This is not
hypothetical: a prototype was written to `./prototypes/<slug>/` and landed
inside this plugin's own source tree, untracked, one `git add -A` away from
being distributed to every user. Resolve through `artifact_path`.

**Output beside the input is a deliberate exception, not an oversight.**
`design-tokens` compiles `tokens.css` next to the token file it read, and
`persona-review` saves next to the document it reviewed. Moving those to a
central root would separate a compiled file from its source. They are anchored —
just to the input, not to a setting.

**A design file's location is not ours to set.** The `design_tool` setting says
whether a backend is used at all (`auto` · `pencil` · `none`); it does not, and
cannot, say where the file goes. A design-file backend keeps
documents in its own store — Pencil in `~/.pencil/documents/<uuid>/` — and the
`filePath` argument on its tools is accepted and ignored. Passing the path of a
different existing file returns the *active* document's nodes. So `.design`
cannot hold a `.pen`, and `humane:prototype` confirms which document is open
before building rather than pretending to choose. To get one into `.design`,
export from it: `export_nodes` for a PNG or PDF, `export_html` for markup.

## Adding a skill that writes something

1. Add the kind to `ARTIFACT_KINDS` in `scripts/humane_setup.py`.
2. Add a row to the table above.
3. Call `artifact_path(name, kind, ext)`. Never assemble the path from a literal.
4. If the output genuinely belongs beside its input, or the location is not
   yours to choose, say so in the row with the reason. Silence reads as an
   oversight.
