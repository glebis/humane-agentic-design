# The specimen config

One JSON file describes the whole page. `scripts/specimen init` writes a valid
one; everything below is what you can change afterwards. `scripts/specimen
check` validates every field and refuses to build a config it cannot render.

## Identity

| Field | Type | Notes |
| --- | --- | --- |
| `id` | string | Keys the page's `localStorage` bucket. Must match `[A-Za-z0-9._-]+`. **Two specimens sharing an `id` overwrite each other's saved state** — give each project its own. |
| `title` | string | Browser tab and page heading. |
| `locale` | `"en"` or `"ru"` | Chooses the interface language of the page's own chrome. Not the language of the specimen copy — that is whatever you put in `texts`. |
| `context` | string | The brief the copy is written against. Stored for whoever writes it; **never shipped into the built HTML**. |

## Families

```json
"groups":   [{ "id": "sf", "label": "Sans" }, { "id": "sr", "label": "Serif" }],
"families": [{ "name": "Onest", "group": "sf", "note": "Paratype" }]
```

- `name` must match the Google Fonts catalogue exactly, and may not contain
  `::` or a newline — the page round-trips the list through a
  `name :: group :: note` textarea, and either character would corrupt it when
  the user hits Apply.
- `group` must be declared in `groups`, or empty. The id `all` is reserved for
  the built-in filter.
- Duplicates are rejected.

## Text slots

Ten keys under `texts`, each with a fixed shape. `check` enforces it, because
a malformed slot degrades in the browser into a silently empty cell rather than
an error.

| Slot | Lines | `::` cells per line |
| --- | --- | --- |
| `display`, `timer`, `headline`, `weights`, `caps` | one | 1 |
| `tableHead` | one | 3 |
| `prose`, `alphabet` | many | 1 |
| `rows` | many | 2 |
| `table` | many | 3 |

Blank lines are ignored, so you can space a long list out in the config.

Any slot still containing `TODO` blocks `build` unless you pass `--allow-todo`.
That gate is the whole reason `init` writes placeholders instead of plausible
filler: filler gets shipped, `TODO` does not.

## Script coverage

| Field | Notes |
| --- | --- |
| `probe` | The string the page uses to decide whether a family loaded at all. Must be in the script you care about. |
| `scriptRange` | A regex matched against the served `@font-face` CSS. `U\+04` catches Cyrillic. Empty means the specimen makes no script demand and every family that loads passes. |
| `glyphSets` | `[[label, "chars separated by spaces"], …]`. Each character is measured individually; missing ones are struck through. |

The check is a real one: Google Fonts serves a family whether or not it has
your script, so a page without `scriptRange` will happily show Cyrillic copy in
Latin fallback and look fine.

## Colour and type defaults

| Field | Notes |
| --- | --- |
| `bg`, `fg` | `#RRGGBB`. The pair the page opens with, and the pair the WCAG/APCA readout describes. |
| `dark`, `light` | `[background, text]` pairs behind the two mode buttons. |
| `palette` | Swatches in the panel. Click sets background, Alt-click sets text. |
| `contrastPreview` | Two short strings shown in the contrast preview box. |
| `size`, `weight`, `lh`, `ls` | Opening slider positions: `11–30`px, `100–900`, `1.0–2.2`, `-0.05–0.2`em. **A value outside a slider's range cannot be returned to once the user moves that slider**, so `check` rejects it. |

## Footnotes

`notes` is a list of strings rendered as paragraphs under the grid. HTML is
allowed — it is your own config — and is escaped against breaking out of the
script block, not against itself.
