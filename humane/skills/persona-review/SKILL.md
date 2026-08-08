---
name: persona-review
description: Review a document from multiple stakeholder perspectives (personas), collect structured feedback, and optionally update the document. Use when a document should be stress-tested from different viewpoints before sharing — e.g., "review this PRD from an engineer's perspective", "what would a skeptical investor say about this pitch?" Triggers on persona review, review from a stakeholder perspective, what would an engineer say, stress-test this PRD, review this pitch, skeptical investor.
---

# Persona Review

## Overview

Takes a document and reviews it from N configurable personas. Each persona reads the document independently, provides structured feedback, then optionally the document is updated to address the feedback.

## Usage

```
/persona-review [file-path] [personas]
```

**Arguments:**
- `file-path` — path to the document to review (required). If omitted, ask user.
- `personas` — comma-separated persona names or "auto" (default: auto)

**Examples:**
```
/persona-review PRD.md engineer,designer,exec
/persona-review "Claude-Drafts/pitch-deck-script.md" auto
/persona-review  # will ask for file and use auto personas
```

## Workflow

### Step 1: Load Document

Read the target file. Extract its purpose from context (frontmatter, filename, content).

### Step 2: Select Personas

**If `auto`:** Choose 3 personas most relevant to the document type:
- PRD/spec → Skeptical Engineer, UX Designer, Business Stakeholder
- Pitch/proposal → Potential Customer, Investor, Competitor
- Blog post/article → Target Reader, Editor, Subject Expert
- Teaching material → Beginner Student, Advanced Practitioner, Curriculum Designer
- Marketing copy → Target Audience Member, Brand Skeptic, SEO Specialist

**If specified:** Use the named personas. Interpret flexibly — "engineer" becomes "Senior Engineer who has seen too many half-baked specs."

### Step 3: Review Rounds

For each persona, generate a review with this structure:

```markdown
### [Persona Name]
**Perspective:** [1-line description of who they are and what they care about]

**Reaction:** [2-3 sentences — their gut reaction on first read]

**Strengths:**
- [What works well from this perspective]

**Concerns:**
- [What's missing, unclear, or problematic]

**Key Question:** [The single most important question this persona would ask]

**Suggestion:** [One specific, actionable improvement]
```

### Step 4: Synthesis

After all persona reviews, create a synthesis section:

```markdown
## Synthesis

**Consensus strengths:** [What all personas agreed works]
**Consensus gaps:** [What multiple personas flagged]
**Tensions:** [Where personas disagree — these are the interesting trade-offs]
**Priority changes:** [Top 3 changes ranked by impact]
```

### Step 5: Ask User

Present the full review and ask:

> "Apply the top changes to the document? (all / pick / none)"

- **all** — Apply all priority changes
- **pick** — Let user select which to apply
- **none** — Leave document unchanged, keep review as reference

### Step 6: Apply (if requested)

Edit the original document to address selected feedback. Keep changes minimal and targeted. After editing, show a brief diff summary of what changed.

### Step 7: Save Review

Save the review alongside the document:
- If document is `path/to/doc.md`, save review as `path/to/doc-persona-review.md`
- Add frontmatter linking back to the original document:

```markdown
---
type: persona-review
source: "[[original-document]]"
personas: [list]
created_date: '[[YYYYMMDD]]'
---
```

## Guidelines

- Each persona should have a distinct voice — don't make them all sound like the same reviewer with different labels
- Personas should be constructively critical, not adversarial
- Focus on substance (logic, completeness, clarity) not style (grammar, formatting)
- If the document is in Russian, reviews should be in Russian
- Keep each persona review under 200 words — brevity forces prioritization
- The "Key Question" is the most valuable output — it should be something the author genuinely hadn't considered
