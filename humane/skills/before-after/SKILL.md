---
name: before-after
description: Generate emotional Before/After transformation grids for products, lectures, and offers. Chainable from humane:jtbd output. Uses empathy mapping, first-person voice, somatic markers, and valence scoring to produce grids ready for landing pages, slides, and messaging. This skill should be used when the user wants to articulate the transformation their product/service creates, build a before/after grid, or chain from a JTBD interview into emotional copywriting. Triggers on before/after grid, transformation grid, "what's the transformation", landing page transformation section, emotional copywriting, chain from JTBD.
handoffs:
  - to: jtbd
    when: the transformation claim has no evidence behind it in the corpus
accepts:
  - from: jtbd
---

# Before/After Transformation Grid

**Announce at start:** "I'm using the humane:before-after skill to capture the felt transformation as a before/after grid."

Generate emotionally precise Before/After grids that capture the felt transformation a product, lecture, or service creates. Not feature lists — lived experience shifts.

## When to invoke

- "Build a before/after grid"
- "What's the transformation?"
- "Chain this JTBD into a before/after"
- "I need a landing page transformation section"
- After completing a `humane:jtbd` interview, as a natural next step

## Mode selection

| Mode | Input | Flow |
|------|-------|------|
| **Chained** (preferred) | Path to `<corpus_root>/<slug>/jtbd.json` | Auto-map → present draft → sharpen |
| **Standalone** | None | Quick interview (3 questions) → draft → sharpen |

`<corpus_root>` throughout is the `setup` setting of that name — default
`~/jtbd`, but read the configured value. Writing to the default when the user
has moved their corpus scatters the bundle across two roots.

---

## Chained Mode: JTBD → Grid

When a `jtbd.json` path is provided (or exists from the current session):

### Step 1: Auto-map dimensions

Extract dimensions from JTBD data using this mapping:

| JTBD field | Grid dimension |
|------------|---------------|
| `switch_forces.push` | Primary BEFORE state |
| `switch_forces.pull` | Primary AFTER state |
| `switch_forces.habit` | BEFORE — inertia/stuckness dimension |
| `switch_forces.anxiety` | BEFORE — fear dimension (flip to confidence in AFTER) |
| `problem.what_hurts` | BEFORE — pain dimension |
| `needs.functional[]` | AFTER — capability dimensions |
| `needs.emotional[]` | AFTER — feeling dimensions |
| `jtbd.outcome` | AFTER — north star |
| `jtbd.situation` | BEFORE — triggering context |

Generate 5-9 dimensions. Each dimension gets a short label (2-4 words).

### Step 2: Draft the grid with emotional depth

For each dimension, write BEFORE and AFTER cells using these techniques:

**First-person voice**: Always "I..." not "The user..."
- BEFORE: "I check my API dashboard with dread every morning"
- AFTER: "I glance at costs once a week, casually"

**Somatic markers**: Include body-level experience where natural
- BEFORE: "My stomach drops when I see 'service unavailable'"
- AFTER: "I shrug — the fallback kicks in, I keep working"

**Behavioral evidence**: What they actually DO, not just feel
- BEFORE: "I google alternatives at 2am but never install anything"
- AFTER: "I have three providers configured and tested"

**Inner monologue**: What they'd say out loud
- BEFORE: "What if they ban my country next week?"
- AFTER: "Even if they do, I'm covered"

**Emotional valence scoring**: Rate each dimension's shift from -3 (deeply negative) to +3 (deeply positive). Most BEFORE states sit at -1 to -3. Most AFTER states at +1 to +3. The delta indicates transformation intensity.

### Step 3: Present and sharpen

Present the draft grid as a markdown table. Then ask targeted questions to increase emotional precision:

- "For [dimension X] — what does this feel like in the body? Chest tight? Shoulders up?"
- "In the BEFORE state of [dimension Y] — what would you literally say to a friend over coffee?"
- "Is the AFTER for [dimension Z] relief (absence of pain) or genuine excitement (presence of new energy)?"
- "Which of these dimensions hits hardest? Which feels lukewarm?"

Apply edits. Remove lukewarm dimensions. Intensify the strongest ones.

### Step 4: Polish pass — Emotion Modulation

Review the completed grid through these lenses:

**Contrast ratio**: Each row should have clear negative→positive movement. If both cells feel neutral, either sharpen or cut.

**Specificity gradient**: At least 3 dimensions should include a specific named thing (a tool, a moment, a number, a sensation). Generic grids don't land.

**Empathy mapping check**: Across the full grid, verify coverage of:
- Think (beliefs, mental models)
- Feel (emotions, physical sensations)
- Do (behaviors, actions)
- Say (inner monologue, things they'd tell others)

If any quadrant is missing across all dimensions, add one dimension that covers it.

**Temporal variety**: Mix immediate states ("right now I feel..."), habitual states ("every Monday I..."), and identity states ("I am the kind of person who...").

---

## Standalone Mode

When no JTBD input exists:

### Quick interview (3 questions, one at a time)

1. "Who is transforming, and what's the situation they're stuck in?"
2. "What's painful about today — what do they feel, do, and say?"
3. "After your thing works — what's different? Not features. How does Tuesday morning feel different from before?"

Then proceed to Step 2 (Draft) using the interview answers as dimension seeds.

---

## Output format

### Markdown table (always produced)

```markdown
## Before/After: [Project Name]

| Dimension | BEFORE (-valence) | AFTER (+valence) |
|-----------|-------------------|------------------|
| **Label** | First-person felt state | First-person felt state |
```

### JSON structure (produced on request or when saving to `<corpus_root>/<slug>/`)

```json
{
  "project": "slug",
  "dimensions": [
    {
      "label": "Provider dependency",
      "before": {
        "state": "I check my API dashboard with dread...",
        "valence": -2,
        "quadrant": "feel",
        "somatic": "chest tightness"
      },
      "after": {
        "state": "I glance at costs once a week, casually",
        "valence": 2,
        "quadrant": "do",
        "somatic": null
      }
    }
  ],
  "source_jtbd": "~/jtbd/crisis-survival-mode/jtbd.json",
  "sharpening_notes": ["removed 'mental model' dimension — too abstract"]
}
```

### ASCII table (terminal-friendly output)

Always produce a clean ASCII table alongside markdown. Useful for pasting into slides, terminals, social posts:

```
┌─────────────────────┬──────────────────────────────────┬──────────────────────────────────┐
│ DIMENSION           │ BEFORE                           │ AFTER                            │
├─────────────────────┼──────────────────────────────────┼──────────────────────────────────┤
│ Provider dependency │ "What if they ban my country     │ "Even if they do, I'm covered"   │
│                     │  next week?"                     │                                  │
├─────────────────────┼──────────────────────────────────┼──────────────────────────────────┤
│ Cost awareness      │ I pay $15/M tokens for tasks     │ I route 80% of work to $0.10/M   │
│                     │ that need $0.10/M                │ models — same quality             │
└─────────────────────┴──────────────────────────────────┴──────────────────────────────────┘
```

Column widths auto-fit content. Max 34 chars per cell, wrap with indentation.

### Save location

When chained from JTBD: save as `<corpus_root>/<slug>/before-after.json` and `<corpus_root>/<slug>/before-after.md` alongside the existing bundle.

When standalone: save to `<corpus_root>/<slug>/` (ask user for slug if not obvious).

---

## Visual generation

After the grid is finalized, offer to generate a visual card using GPT image generation (via `/nano-banana` or ChatGPT API).

### Visual style directive

Pass the following style prompt alongside the grid data:

```
Style: Minimalist infographic. Bauhaus-inspired geometric composition.
Icons: Gerd Arntz isotype pictograms — flat, monochrome, symbolic.
Typography: Nordic sans-serif (Inter, Söhne, or GT Walsheim style). 
Layout: Two-column (BEFORE | AFTER), clean vertical divider.
Color: Limited palette — dark background (#1a1a2e or #0f0f0f), 
       BEFORE in muted warm (#c4553a or desaturated amber),
       AFTER in cool confident (#4ecdc4 or clean blue-white).
Elements per row: One icon + one short quote (max 8 words from the grid cell).
Captions: Pull the strongest first-person quote as a large pull-quote at top.
Footer: Project name + "Before/After Transformation Grid"
Mood: Calm authority. Not corporate — editorial. Think Kinfolk meets information design.
```

### Visual generation flow

1. Select the 4-5 strongest dimensions (highest valence delta)
2. For each: pick a representative icon concept + the shortest quote from that cell
3. Compose the prompt: style directive + structured content
4. Generate using available image tool (nano-banana preferred, ChatGPT fallback)
5. Save as `<corpus_root>/<slug>/before-after-visual.png`

### Icon concepts mapping

Map common transformation themes to Arntz-style pictogram concepts:

| Theme | BEFORE icon | AFTER icon |
|-------|-------------|------------|
| Dependency/lock-in | Padlock / chain | Open door / key |
| Cost/waste | Leaking bucket | Balanced scale |
| Knowledge gap | Fog / question mark | Map / compass |
| Anxiety/fear | Storm cloud / figure hunched | Figure standing tall / sun |
| Capability | Empty toolbox | Full toolkit |
| Speed/efficiency | Hourglass draining | Arrow / lightning |
| Resilience | Single pillar | Three pillars / arch |

---

## Downstream use

The before/after grid feeds into:
- **Landing pages**: Each row becomes a transformation bullet or section
- **Slide decks**: Before/After as a two-column slide  
- **Visual cards**: Arntz-style infographic for social/presentations
- **Messaging angles**: Each dimension is a potential headline angle
- **Sales conversations**: "Right now you're [BEFORE]. After this, you'll [AFTER]."

After completing the grid, suggest: "Want me to generate a visual card, turn this into slide copy, or create a landing page section?"

---

## Anti-patterns to avoid

- Generic language ("better," "improved," "enhanced") — always specific
- Feature descriptions disguised as states ("Has access to local models" → rewrite as felt experience)
- Symmetric pairs that are just negation ("Doesn't have X" / "Has X") — each side needs its own texture
- More than 9 dimensions — cut the weakest, don't dilute
- All dimensions at the same emotional intensity — vary the drama

## Tone

Direct, evocative, slightly provocative. The grid should make someone reading it think "that's exactly how I feel right now" (BEFORE) and "I want that" (AFTER).
