# Every path a humane skill writes

One place to look up where an artifact goes, and which setting moves it. If a
skill writes something that is not in this table, that is a bug in the skill —
add the row, do not invent a path at the call site.

## The two roots

| Setting | Default | Holds |
| --- | --- | --- |
| `corpus_root` | `~/jtbd` | the JTBD corpus and everything derived directly from it |
| `artifact_root` | *empty → same as `corpus_root`* | generated artifacts: prototypes, specimens, boards, illustrations, walks, reviews |

They are separate settings because they differ in kind. A corpus is usually
personal and global — one place you keep every project's jobs. A prototype is
often something you want beside the code it describes, so it can be committed
with it. Left empty, `artifact_root` follows `corpus_root` and everything lives
in one bundle.

```bash
scripts/humane_setup.py config --set artifact_root=./design --scope project
scripts/humane_setup.py config --set corpus_root=~/work/jtbd --scope global
```

## The bundle

Everything for one project sits under one slug directory:

```
<corpus_root>/<slug>/
    jtbd.json                    the corpus — jtbd
    one-pager.md, gtm-brief.md   jtbd exports
    before-after.json|.md|.png   before-after

<artifact_root>/<slug>/
    prototypes/                  prototype
    specimens/                   type-specimen
    boards/                      brandkit
    illustrations/               brand-illustrate
    walks/<date>-<task>/         walkthrough — step-NN-<tier>.png
    reviews/<date>/              review, nielsen-heuristics reports
```

Resolve it in code rather than by string-building:

```python
from humane_setup import artifact_dir
artifact_dir("acme-till", "prototype")   # -> <artifact_root>/acme-till/prototypes
```

`artifact_dir` refuses an unknown kind and refuses a slug containing `/` or
starting with `.`, so a bad caller fails loudly instead of writing somewhere
surprising.

## The full table

| Skill | Writes | Where | Anchor |
| --- | --- | --- | --- |
| `jtbd` | `jtbd.json`, one-pager, messaging angles, GTM brief | `<corpus_root>/<slug>/` | `corpus_root` |
| `before-after` | `before-after.json`, `.md`, `-visual.png` | `<corpus_root>/<slug>/` | `corpus_root` |
| `walkthrough` | `step-NN-<tier>.png` per step per tier | `<artifact_root>/<slug>/walks/<date>-<task>/` | `artifact_root` |
| `prototype` | ASCII sketch, SVG click-dummy, HTML prototype | `<artifact_root>/<slug>/prototypes/<name>/` | `artifact_root` |
| `type-specimen` | `specimen.json`, the built specimen page | `<artifact_root>/<slug>/specimens/` | `artifact_root` |
| `brandkit` | brand boards, `direction.json`, `brand-block.draft.json` | `<artifact_root>/<slug>/boards/` | `artifact_root` |
| `brand-illustrate` | images, `prompts.md`, `metadata.json`, contact sheet, recipe | `<artifact_root>/<slug>/illustrations/<batch>/` | `artifact_root` |
| `review` · `nielsen-heuristics` | a saved report, **when the user asks for a file** | `<artifact_root>/<slug>/reviews/<date>/` | `artifact_root` |
| `design-tokens` | `tokens.css`, `DESIGN.md`, `refs.json` | **beside the token file it compiled** | the input path |
| `persona-review` | `<doc>-persona-review.md` | **beside the document it reviewed** | the input path |
| `respondent-panel` | nothing — reactions are reported inline | — | — |
| `ux-writing` · `layout-rules` | nothing — findings are reported inline | — | — |

## Two rules that are not negotiable

**Never write to the current working directory.** A CWD-relative default puts a
user's artifact wherever the agent happened to be standing. This is not
hypothetical: a prototype was written to `./prototypes/<slug>/` and landed
inside this plugin's own source tree, untracked, one `git add -A` away from
being distributed to every user of the plugin. Resolve through `artifact_dir`.

**Output beside the input is a deliberate exception, not an oversight.**
`design-tokens` compiles `tokens.css` next to the token file it read, and
`persona-review` saves next to the document it reviewed. Both are derived from a
path the user already named, and moving them to a central root would separate a
compiled file from its source. They are anchored — just to the input, not to a
setting.

## Adding a skill that writes something

1. Add the kind to `ARTIFACT_KINDS` in `scripts/humane_setup.py`.
2. Add a row to the table above.
3. Call `artifact_dir(slug, kind)`. Do not build the path from a literal.
4. If the output genuinely belongs beside its input, say so in the row and in
   the skill, with the reason. Silence reads as an oversight.
