"""Generate a contrast fixture page and the manifest that tells the truth about it.

The eval asks whether running `humane:review` on a UI finds defects an unaided
pass misses. That question is only answerable if the fixture's ground truth is
exact — every colour on the page known, every verdict computed by the oracle
rather than asserted by hand. So:

* Every rendered text/background pair carries inline colours and an id, and
  appears in the manifest with the 1-based line of fixture.html where it lives.
  There is no colour on the page the manifest does not know about.
* `planted` is derived as `not passed` from `oracle.measure`. It is never set by
  the code that chose the colour. A generator that "plants a defect" and then
  records its own intent would happily ship a manifest describing a page that
  does not exist.
* At least a third of planted defects are **disagreement** pairs, where APCA and
  WCAG return opposite verdicts (`#767676` on white: WCAG 4.54 passes, APCA 71.6
  fails the 75 bar). A reviewer working from the familiar 4.5:1 number will walk
  straight past those, which is exactly where the with-skill/without-skill delta
  should show. A fixture built only from grey-on-grey mush measures almost
  nothing.

Determinism is a hard requirement — the harness compares runs. Only
`random.Random(seed)` is used: no global `random`, no clock, no uuid.

    python3 generate.py --seed 1337 --pairs 12 --defects 5 --out fixtures/a
    python3 generate.py --seed 1337 --pairs 12 --clean     --out fixtures/clean

Dev-only. Nothing under `humane/` may import this.
"""

import argparse
import json
import math
import random
import subprocess
import sys
from pathlib import Path

from pathlib import Path as pathlib_Path  # noqa: N813

from oracle import LEVELS, STANDARD, measure, oklch_to_rgb, to_hex

# ---------------------------------------------------------------------------
# Colour search
# ---------------------------------------------------------------------------

# Backgrounds a real page actually uses: paper whites, faint greys, and two dark
# surfaces. The dark ones are load-bearing — they are what produce negative APCA
# Lc, the regression the manifest must not mistake for a failure.
_BACKGROUNDS = (
    "#ffffff", "#fbfbfa", "#f5f6f7", "#eef1f4",
    "#12141a", "#08080a", "#1b1d23",
)

_CHROMAS = (0.0, 0.01, 0.02, 0.04, 0.06, 0.09, 0.12)
_L_STEPS = 101  # lightness samples along one hue/chroma ray


def _ray(rng, bg_hex, level):
    """Measure one hue/chroma ray of foregrounds against `bg_hex`.

    Sampling a ray rather than sampling colours independently is what makes the
    narrow disagreement band findable: the band is a couple of lightness steps
    wide, so a walk across lightness crosses it, while uniform random hex almost
    never lands in it.
    """
    hue = rng.uniform(0.0, 360.0)
    chroma = rng.choice(_CHROMAS)
    out = []
    for i in range(_L_STEPS):
        fg = to_hex(oklch_to_rgb(i / (_L_STEPS - 1), chroma, hue))
        out.append(measure(fg, bg_hex, level))
    return out


def _search(rng, level, want, backgrounds, used, attempts=400):
    """Return a measured pair satisfying `want`, or raise.

    `want` is a predicate over the measurement dict. `used` holds (fg, bg) pairs
    already spent, so the fixture never repeats a pair — a duplicate would let a
    reviewer find one defect and score two.
    """
    for _ in range(attempts):
        bg = rng.choice(backgrounds)
        hits = [m for m in _ray(rng, bg, level)
                if want(m) and (m["fg"], m["bg"]) not in used]
        if hits:
            return rng.choice(hits)
    raise RuntimeError(
        f"no {level} pair matching the requested predicate after {attempts} rays; "
        "widen _BACKGROUNDS/_CHROMAS or lower the request"
    )


def _disagreement(m):
    return m["apca_pass"] != m["wcag_pass"]


def _both_fail(m):
    return not m["apca_pass"] and not m["wcag_pass"]


# ---------------------------------------------------------------------------
# Page content
# ---------------------------------------------------------------------------

_TITLE = "Northwind Freight — Shipment Console"

_HEADINGS = (
    "Shipments in transit", "Customs holds", "Carrier performance",
    "Unassigned loads", "Dock schedule", "Exceptions this week",
    "Invoices awaiting approval", "Fuel surcharges",
)

_BODY = (
    "Fourteen loads cleared the Rotterdam gate this morning; two are held "
    "pending a corrected commercial invoice.",
    "Carrier on-time rate slipped to 91% after the storm closure on the A2 "
    "corridor. The backlog clears by Thursday on current projections.",
    "Three shipments have no assigned driver. Assign them before the 18:00 "
    "cut-off or they roll to tomorrow's manifest.",
    "Dock 4 is out of service for scheduled maintenance until Friday. Inbound "
    "trailers are being routed to docks 6 and 7.",
    "The consolidated invoice for week 31 is ready for approval and covers "
    "seven carriers across two regions.",
    "Temperature excursions were logged on two reefer units. Both remained "
    "within tolerance and no product was condemned.",
    "Duty rates for the HS 8471 category changed on the first of the month. "
    "Quotes issued before that date have been reflagged.",
    "Weekend pickups now require a booking reference. Drivers arriving without "
    "one are turned away at the gate.",
)

_LINKS = (
    "View all shipments", "Open the customs queue", "Download the manifest",
    "Contact the carrier desk", "See last week's report", "Manage dock slots",
    "Export to CSV", "Review the audit log",
)

_CHIPS = (
    "In transit", "Held", "Delivered", "Delayed",
    "Booked", "Cancelled", "At dock", "Cleared",
)

_FOOTER = ("Northwind Freight BV · Shipment Console v4.2 · "
           "Data refreshed every 15 minutes")


def _level_for(index, count):
    """Assign a level per slot, mixing all three across the page.

    `graphic` is stated explicitly here and recorded in the manifest for the
    same reason `contrast.py` refuses to infer it: nothing about a colour tells
    you whether it is painted as type.
    """
    if index == 0:
        return "non-body"          # site title
    if index == count - 1:
        return "body"              # footer
    return ("body", "non-body", "graphic", "body")[index % 4]


def _render(pair_id, level, index, count, fg, bg):
    """One line of HTML for one pair. One pair, one line, one recorded locator."""
    style = f"color:{fg};background-color:{bg}"
    if index == 0:
        return f'  <h1 id="{pair_id}" style="{style}">{_TITLE}</h1>'
    if index == count - 1:
        return f'  <p id="{pair_id}" style="{style}">{_FOOTER}</p>'
    if level == "graphic":
        return (f'  <span id="{pair_id}" style="{style};'
                f'display:inline-block;padding:2px 10px;border-radius:10px">'
                f'{_CHIPS[index % len(_CHIPS)]}</span>')
    if level == "non-body":
        return (f'  <a id="{pair_id}" href="#" style="{style}">'
                f'{_LINKS[index % len(_LINKS)]}</a>')
    if index % 3 == 1:
        return (f'  <h2 id="{pair_id}" style="{style}">'
                f'{_HEADINGS[index % len(_HEADINGS)]}</h2>')
    return f'  <p id="{pair_id}" style="{style}">{_BODY[index % len(_BODY)]}</p>'


# Accessibility defects this generator can plant, all inside the vetted axe
# allow-list in ../axe/owners.json. `planted` is still never asserted: these are
# candidates, and only what axe actually reports lands in the manifest.
A11Y_DEFECTS = {
    "heading-order":  "a heading level skips (h1 followed by h4)",
    "empty-heading":  "a heading with no text",
    "html-has-lang":  "the document declares no language",
    "no-main":        "no main landmark, so content sits outside any region",
}


def build_html(entries, a11y=()):
    """Return (html_text, {pair_id: line_number}).

    Line numbers are 1-based and computed while the document is assembled, not
    grepped afterwards — a locator derived from a second pass can drift from the
    file it claims to describe.
    """
    a11y = set(a11y)
    lines = [
        "<!doctype html>",
        "<html>" if "html-has-lang" in a11y else '<html lang="en">',
        "<head>",
        '  <meta charset="utf-8">',
        f"  <title>{_TITLE}</title>",
        # No comment here, deliberately. An earlier version explained that every
        # colour was recorded in manifest.json — inside the file handed to the
        # reviewer being evaluated. That tells a subject an answer key exists and
        # names it, and one arm duly reported the comment as a finding. The
        # invariant it described is real and belongs in this generator's
        # docstring, where the reviewer cannot read it.
        "</head>",
        "<body>",
    ]
    # Without a landmark, axe reports `region` once per element — twelve
    # violations for one structural omission. A fixture must not carry an
    # unplanted accessibility defect, so the default wraps content in <main>
    # and omitting it becomes something you plant on purpose.
    if "no-main" not in a11y:
        lines.append("  <main>")
    at = {}
    for entry in entries:
        line = _render(entry["id"], entry["level"], entry["index"],
                       entry["count"], entry["fg"], entry["bg"])
        lines.append(line)
        at[entry["id"]] = len(lines)  # 1-based: len() after append
    if "heading-order" in a11y:
        lines.append('  <h4 id="ax-heading-order">Skipped two levels to get here</h4>')
        at["ax-heading-order"] = len(lines)
    if "empty-heading" in a11y:
        lines.append('  <h2 id="ax-empty-heading"></h2>')
        at["ax-empty-heading"] = len(lines)
    if "no-main" not in a11y:
        lines.append("  </main>")
    lines += ["</body>", "</html>", ""]
    return "\n".join(lines), at


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------

def generate(seed, pairs, defects=0, clean=False, a11y=()):
    """Return (html_text, manifest_dict). Pure — writes nothing."""
    if pairs < 3:
        raise ValueError("--pairs must be at least 3 (title, content, footer)")
    if clean:
        defects = 0
    elif not 0 <= defects <= pairs:
        raise ValueError(f"--defects must be between 0 and --pairs ({pairs})")

    rng = random.Random(seed)

    # A third of the planted defects, rounded up, must be disagreement pairs.
    # Rounded up rather than down so that a single-defect fixture still carries
    # the case the eval exists to measure.
    quota = math.ceil(defects / 3) if defects else 0

    defect_slots = sorted(rng.sample(range(pairs), defects)) if defects else []
    disagreement_slots = set(rng.sample(defect_slots, quota)) if quota else set()

    used, entries = set(), []
    for index in range(pairs):
        level = _level_for(index, pairs)
        if index in disagreement_slots:
            want = _disagreement
        elif index in set(defect_slots):
            want = _both_fail
        elif clean:
            # A clean fixture must be clean under any defensible level
            # assignment, so a passing pair is not enough — it must also clear
            # the body-text bar, the strictest of the three. Otherwise a
            # reviewer who reads a link as running text flags it, correctly,
            # and `padding` scores that judgement as an invented finding.
            want = lambda m: m["passed"] and measure(  # noqa: E731
                m["fg"], m["bg"], "body")["passed"]
        else:
            want = lambda m: m["passed"]  # noqa: E731
        m = _search(rng, level, want, _BACKGROUNDS, used)
        used.add((m["fg"], m["bg"]))
        entries.append({
            "id": f"pair-{index + 1:02d}",
            "index": index,
            "count": pairs,
            **m,
            # Derived, never asserted. If the search returned something other
            # than what was asked for, the manifest says what is on the page.
            "planted": not m["passed"],
            "disagreement": _disagreement(m),
        })

    html, at = build_html(entries, a11y)

    got_planted = sum(1 for e in entries if e["planted"])
    got_disagreement = sum(1 for e in entries if e["planted"] and e["disagreement"])
    if got_planted != defects:
        raise AssertionError(
            f"asked for {defects} planted defects, the page carries {got_planted}; "
            "the colour search returned a pair that does not match its predicate"
        )
    if got_disagreement < quota:
        raise AssertionError(
            f"only {got_disagreement} of {got_planted} planted defects disagree "
            f"between APCA and WCAG, quota is {quota}. A fixture of obvious "
            "failures measures almost nothing — widen _BACKGROUNDS/_CHROMAS or "
            "raise the search attempt budget in _search()"
        )
    if clean and got_planted:
        raise AssertionError("--clean produced a failing pair")
    if clean:
        # A clean fixture must be clean under ANY defensible level assignment,
        # not only the one this generator picked. The first clean run had 1-3
        # pairs per fixture that passed at their declared level (`non-body`,
        # `graphic`) and failed at `body`: #65635d on #eef1f4 is Lc 71.5 — fine
        # for a link, short of the 75 body floor. Reviewers reasonably read some
        # of those as body text and flagged them, and `padding` then scored a
        # defensible disagreement about level as an invented finding. The
        # pathway could not answer the question it was built for.
        soft = [e for e in entries
                if not measure(e["fg"], e["bg"], "body")["passed"]]
        if soft:
            raise AssertionError(
                "--clean produced %d pair(s) that fail when judged as body text "
                "(%s). Clean must hold at the strictest threshold, or `padding` "
                "measures a level disagreement rather than invention."
                % (len(soft), ", ".join(e["id"] for e in soft))
            )

    manifest = {
        "seed": seed,
        "clean": bool(clean),
        "a11y_planted": sorted(a11y),
        "fixture": "fixture.html",
        "oracle": {"module": "dtokens.contrast", "standard": STANDARD},
        "counts": {
            "pairs": pairs,
            "planted": got_planted,
            "disagreement": got_disagreement,
        },
        "pairs": [
            {
                "id": e["id"], "line": at[e["id"]],
                "fg": e["fg"], "bg": e["bg"], "level": e["level"],
                "apca": e["apca"], "wcag": e["wcag"],
                "apca_pass": e["apca_pass"], "wcag_pass": e["wcag_pass"],
                "passed": e["passed"],
                "planted": e["planted"], "disagreement": e["disagreement"],
            }
            for e in entries
        ],
    }
    return html, manifest


def run_axe(fixture_path):
    """Ask oracle #2 what it finds, and record that — never what we intended.

    Same discipline as the contrast oracle: a defect exists because a program
    says so. A generator that planted a defect and then wrote down its own
    intent would happily ship a manifest describing a page that is not there.

    Unavailability is a recorded state, not a crash. A run on a machine without
    node must not look like a smaller but complete result, so the manifest says
    the pathway went unchecked and the scorer reports that domain Not reviewed.
    """
    runner = pathlib_Path(__file__).resolve().parents[1] / "axe" / "run_axe.js"
    try:
        out = subprocess.run(["node", str(runner), str(fixture_path)],
                             capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"available": False, "reason": f"could not run node: {exc}"}
    if out.returncode != 0:
        return {"available": False, "reason": f"runner exited {out.returncode}: {out.stderr[:200]}"}
    try:
        return json.loads(out.stdout)
    except json.JSONDecodeError as exc:
        return {"available": False, "reason": f"unparseable runner output: {exc}"}


def collapse(violations, owners):
    """One root cause is one defect, listing every node it affects.

    `region` fires once per element outside a landmark — twelve violations for
    one missing <main>. Counting those as twelve would let a reviewer that named
    the single real cause score 1/12 on recall, which is the same mistake the
    contrast scorer made with consolidated findings and had to be corrected for.
    """
    out, seen = [], {}
    for v in violations:
        rule = v["rule"]
        if owners.get("rules", {}).get(rule, {}).get("one_root_cause"):
            if rule in seen:
                seen[rule]["selectors"].append(v["selector"])
                continue
            entry = dict(v, selectors=[v["selector"]])
            entry.pop("selector", None)
            seen[rule] = entry
            out.append(entry)
        else:
            out.append(dict(v, selectors=[v.pop("selector")]))
    return out


def write(out_dir, html, manifest):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "fixture.html").write_text(html, encoding="utf-8")
    (out / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    return out


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--pairs", type=int, required=True)
    p.add_argument("--defects", type=int, default=None,
                   help="how many pairs must fail the oracle")
    p.add_argument("--a11y", nargs="*", metavar="DEFECT", default=None,
                   help="plant accessibility defects for oracle #2. No names = all of them. "
                        "Known: " + ", ".join(sorted(A11Y_DEFECTS)))
    p.add_argument("--clean", action="store_true",
                   help="produce a fixture with zero failing pairs")
    p.add_argument("--out", required=True)
    args = p.parse_args(argv)

    if args.clean and args.defects is not None:
        p.error("--defects cannot be combined with --clean: a clean fixture has "
                "zero defects by definition")
    if not args.clean and args.defects is None:
        p.error("pass --defects N, or --clean for a fixture with none")

    a11y = sorted(A11Y_DEFECTS) if args.a11y == [] else list(args.a11y or [])
    unknown = [d for d in a11y if d not in A11Y_DEFECTS]
    if unknown:
        p.error(f"unknown --a11y defect(s) {unknown}; known: {sorted(A11Y_DEFECTS)}")

    html, manifest = generate(args.seed, args.pairs,
                              defects=args.defects or 0, clean=args.clean, a11y=a11y)
    out = write(args.out, html, manifest)

    # Oracle #2 runs against the file as written, and the manifest records what
    # it actually reports. Availability is a recorded state: a machine without
    # node produces a manifest that says this domain went unchecked, not one
    # that quietly omits it.
    owners_path = pathlib_Path(__file__).resolve().parents[1] / "axe" / "owners.json"
    owners = json.loads(owners_path.read_text(encoding="utf-8"))
    axe = run_axe(pathlib_Path(out) / "fixture.html")
    manifest["axe"] = {k: axe.get(k) for k in ("available", "reason", "axe_version")}
    manifest["violations"] = collapse(axe.get("violations", []), owners) if axe.get("available") else []
    manifest["counts"]["violations"] = len(manifest["violations"])
    (pathlib_Path(out) / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    c = manifest["counts"]
    note = (f", {c['violations']} axe violation(s)" if axe.get("available")
            else f", axe unavailable ({axe.get('reason', 'unknown')})")
    print(f"{out}/fixture.html — {c['pairs']} pairs, {c['planted']} planted, "
          f"{c['disagreement']} disagreement{note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
