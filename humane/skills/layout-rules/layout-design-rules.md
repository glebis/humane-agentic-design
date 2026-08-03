# Layout & UI design rules

Distilled from the JTBD Graph viewer build/audit cycle (2026-07). Each rule is a defect class actually caught in review — phrase them as constraints when designing or prompting a new layout. Applies to data-dense tools/dashboards first, but most rules are general.

## Structure & hierarchy

1. **Never use left-side border rails** (accent bars on quotes, callouts, cards). Carry meaning with a background tint, a leading color dot on the label, or a typographic device (hanging quote mark) instead. If a color rail encoded semantics, the semantics must survive the replacement.
2. **No eyebrow labels** (tiny mono ALL-CAPS section markers). Prefer sentence-case, story-telling headers that state a conclusion: «Эту работу нанимают 3 проекта: …» beats "MANAGE AI VISUAL PRODUCTION · 3". Navigation lists don't need a label saying they're navigation.
3. **No heading-scale cliffs.** Every heading level must be distinguishable from body text AND from adjacent levels. A 22px → 9.5px-caps jump means the third level doesn't exist. Target a real modular scale (e.g. 29 / 22 / 14.5 / 13.5 body / 10.5 utility); table `th` may be small mono-caps but is then a utility style, not a heading.
4. **Structure encodes truth**: numbering, dividers, group headers only when the content genuinely is a sequence/grouping. A group header should say what the group means, not repeat its filter value.

## Footers, metrics, copy

5. **A summary/verdict line must add a conclusion or a next action** — never restate the metrics row, the subtitle, or the data the user just saw. If it can't add anything, drop it.
6. **No decorative metrics.** Every displayed number is either informative on its own or actionable. Drop counts that duplicate visible context (sidebar already says "All 12 projects" → no "Projects 12" stat).
7. **Numbers are entry points**: metric values that describe a subset should filter to that subset on click (toggle, `aria-pressed`), with a brief (~300ms) highlight animation on the surviving rows; respect `prefers-reduced-motion`. Non-actionable metrics stay visually plain — affordance only where action exists.
8. **When a sentence names an entity, link the entity** to its detail view ("open the story"). Verdicts, tooltips, and empty states are navigation, not decoration.
9. **Empty states teach**: show the exact next command/action in a `<code>` block, plus "everything else still works". Never a bare "no data".

## Tables & lists

10. **Data tables are sortable and filterable by default**: clickable headers with `aria-sort` and ▲▼, sort direction flip on re-click, a per-table fuzzy filter input with a live match count, `font-variant-numeric: tabular-nums` for numeric columns.
11. **Truncation must stay meaningful.** A label cut to 2–3 chars ("EX…") is noise: below the fit threshold switch to a designed short form (stage number 01–08) or drop the label entirely (honest barcode) — the tooltip keeps the full text.

## Color & contrast

12. **Audit the faintest text token.** Anything used for text must clear WCAG 4.5:1 **and** APCA Lc 75 on BOTH themes; reserve the faintest tint for decorative lines/dots only. Small ALL-CAPS text needs the same bar as body. Don't eyeball this — if the project has a token set, run `design-tokens contrast <file>` per theme (it measures both scales and proposes a lightness-only fix that keeps the hue). WCAG alone is not enough: `#747474` on white passes 4.5:1 and still fails APCA.
13. **Labels over colored fills pick their color by luminance** (dark-on-light / white-on-dark via relative luminance), never a fixed token.
14. **Semantic color ≠ accent.** Ramps (good→warn→bad) are consistent across all views; the interactive accent is a separate hue.
15. **Tokenize shadows** per theme (stronger on dark); no hard-coded rgba.

## State & navigation

16. **Every distinct place in the app has a URL.** View, selected entity, filters, sort, search query — all in query params; `pushState` on navigation clicks, `replaceState` on tweaks; `popstate` restores fully. Deep links are the test: reload must land exactly where you were.
17. **Fetch app data with `cache:"no-store"`** (or versioned URLs) — stale-data bugs masquerade as logic bugs.

## Interaction correctness (recurring JS traps)

18. **Delegated click handlers with early `return`s silently skip global concerns** (closing popovers, clearing selection). Run "close/reset" logic first, before any branch returns.
19. **`hidden` loses to any `display` set by a class.** Every component styled with `display:flex/grid` needs an explicit `[hidden]{display:none}` companion.
20. **CSS class `fill`/`color` beats SVG presentation attributes.** When a helper takes an explicit color, promote it to an inline style.
21. **Filter/search inputs must keep focus** while results update — re-render the results container, not the input's ancestor.

## Accessibility & touch

22. **Custom interactives are real buttons**: `tabindex`, `role`, `aria-label`, Enter/Space activation, and a **visible** `:focus-visible` ring — including SVG nodes.
23. **Hover-only tooltips are a desktop-only feature.** Provide tap-to-toggle on touch and focus-triggered display for keyboard; data shown only in a tooltip is data some users never see.
24. **Hit areas: 24×24 CSS px is the floor, 44 is the target.** WCAG 2.5.8 (AA) requires 24×24 — that is the conformance bar, *not* 44. Aim for 44×44 in touch contexts and 40×40 on desktop where density permits, but a smaller control is not automatically a failure: under the spacing exception it passes if a 24px circle centred on its bounding box doesn't intersect another target's circle (≈4px gap between 20px targets). Expand the hit area with padding or a negative-inset pseudo-element rather than inflating the visuals — and put that pseudo-element on the wrapping `<label>`/`<button>`, never on the `<input>`: replaced elements don't render `::before`/`::after` reliably. Check the exception before reporting a violation; compact professional tools are allowed to be compact.
25. **Filter chip groups: one row per dimension.** Don't let two filter dimensions wrap into one visual stream.
26. **Narrow screens get native controls**: long button lists collapse to `<select>` at the breakpoint.

## i18n & theming

27. **Every user-facing string exists in every locale from the first commit** (single STR table, key-parity check). No calques — idiomatic target language ("прогони проход" → "запусти оценку"). Verbatim quotes/data stay in their captured language; only chrome translates.
28. **Design both themes at token level**: define palette on `:root`, override tokens in `@media (prefers-color-scheme: dark)` and again under `[data-theme=…]`; components never reference raw colors.

## Process rules that caught the bugs

29. **Screenshot-test in a real browser after every batch** — the popover-open-on-load, washed SVG labels, and chip-wrap bugs were invisible in code review and obvious in one screenshot.
30. **Verify against the real corpus AND a minimal/empty one** — every view must degrade with instructions, not blank space.

## De-slop (from impeccable / frontend-design audit criteria)

Anti-patterns that read as "AI-generated" regardless of correctness — avoid unless the brief explicitly asks:

31. **Default look clusters**: warm cream (#F4F1EA-ish) + high-contrast serif + terracotta accent; near-black + lone acid-green/vermilion pop; broadsheet hairline-rules with dense columns. All legitimate somewhere — but as *choices*, never as the unexamined default.
32. **Template hero**: big number + small label + supporting stats + gradient accent. Open with the most characteristic thing in the subject's world instead.
33. **Surface slop**: gradient text, glassmorphism, uniform `rounded-lg` on everything, nested cards (card inside card), card-grid-of-everything.
34. **Type slop**: Inter/Space Grotesk as the "safe" pick; same pair on every project. Pair faces for this subject.
35. **Marker slop**: emoji as section markers; numbered markers (01/02/03) where content isn't a sequence; everything centered.
36. **Color slop**: gray text on colored backgrounds (tint the text toward the background hue instead); accent that fights the ground — shift analogous or desaturate rather than swap.
37. **Motion slop**: bounce easing, scattered micro-effects. One orchestrated moment beats many; sometimes none is right.
38. **Copy slop**: redundant restating copy, selling adjectives, "Submit" buttons. A control names its exact action; label labels, example demonstrates, nothing does double duty.
39. **Boldness budget**: spend it in one signature place, keep everything around it quiet; before shipping, remove one accessory (Chanel rule).
