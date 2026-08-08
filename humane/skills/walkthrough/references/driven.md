# Driven mode — the procedure

This file is the single standard for driving a real interface during a
walkthrough. `review` and `nielsen-heuristics` cite it instead of describing
their own driving procedure; the viewport matrix and the evidence contract
below are the same in all three.

## The tool ladder

Resolve the browser tool in this order and **name the rung you are on** in the
output. `setup` detects the first rung and prints the install command when it
is missing.

1. **`agent-browser` CLI** (default) — a plain command-line tool, callable from
   any agent's shell. Install: `npm i -g agent-browser`. Headless by default.
2. **Playwright MCP** — when the host already runs it and `agent-browser` is
   absent. MCP-capable hosts only.
3. **The host's own browser tools** — whatever the agent ships. Usually no
   device emulation; see the degraded matrix below.
4. **The user drives** — ask them to perform each step and describe or
   screenshot what happened. Record that evidence is second-hand.

> **Claude Code extras:** an authenticated session in the user's real,
> logged-in browser (a live dashboard behind a login) is the one case where the
> Claude-in-Chrome extension beats every rung above. Use it for that case only,
> with the user's confirmation, and say so in the basis.

## The device matrix

Emulate devices, not just widths — a narrow window has desktop UA, mouse
hover, and DPR 1, so it cannot surface touch-target or hover-dependency
breaks. With `agent-browser`:

| Tier | Command | When |
| --- | --- | --- |
| **Mobile** | `agent-browser set device "iPhone 14"` | **Mandatory** whenever the walk feeds a `review` full-mode pass, and whenever the corpus actor's entry state names a phone |
| **Desktop** | `agent-browser set viewport 1440 900` | Always |
| Tablet | `agent-browser set device "iPad"` | Only when the product targets tablets — do not claim a tier you did not walk |

On a rung without device emulation, the degraded substitute is a bare
390×844 viewport — usable, but findings that depend on touch, UA, or DPR are
**Not verified** at that tier, and the report must say the emulation was
partial. Never present a resized desktop window as a device pass.

A finding is observed **at a tier**. Every finding names the tier(s) it was
seen on; a break that exists only on mobile is a mobile finding, not a
general one.

## The evidence contract

One screenshot per step per tier walked, captured **before moving to the next
step**, saved to:

```
<corpus_root>/<slug>/walks/<date>-<task-slug>/step-NN-<tier>.png
```

(No corpus? Use `./walks/…` in the project and say so.) With `agent-browser`:

```bash
agent-browser screenshot walks/2026-08-08-close-shift/step-03-mobile.png
agent-browser screenshot --full ...   # when the break is below the fold
agent-browser screenshot --annotate ... # numbered interactive elements, when "will they notice?" is the question
```

The filename **is** the evidence locator in the findings table — the same role
`path:line` plays in a code review. After each step also run
`agent-browser errors`; a console error during a step is evidence for Q4
(silent failure) and gets quoted in the row.

## The mode gate

A claimed mode is only as strong as the evidence behind it. Before writing
"Driven" in the basis, check the row:

| Claim | Requires | Not sufficient |
| --- | --- | --- |
| Driven | A step-NN screenshot for every step, at every tier claimed, plus the console check | "I navigated through it"; screenshots of only the breaks; a desktop-only walk presented as covering mobile |
| Prototype | An ordered artifact for every transition claimed | A verbal description of the prototype |
| Static | The screenshots themselves | Someone else's description of them |
| Code | The files read, cited `file:line` | — (weakest already) |

Missing evidence does not block the walk — it **downgrades the claim**. A walk
with gaps in its screenshot trail reports the mode the evidence supports, and
lists the undocumented steps as **Not verified**. Never let the intended mode
outrun the captured evidence.

## Mobile checks folded into the walk

While on the mobile tier, these ride along at each step — they are owned
elsewhere and route there as findings:

- **Tap targets** (`layout-rules` rules 23–24): measure the actual element via
  the annotated screenshot or the DOM, don't eyeball. 24×24 CSS px minimum,
  44×44 for primary actions.
- **Horizontal scroll**: the page body must not scroll sideways at the mobile
  tier (`layout-rules`).
- **Hover-only affordances**: anything reachable only by hover is invisible on
  this tier — a Q2 break, and a `layout-rules` rule 23 finding.
- **Both themes** (`layout-rules` rule 29): when the product ships two, the
  screenshot trail covers the walked path in both at least once per tier.
  Contrast stays measured, never eyeballed — `design-tokens tokens contrast`.
