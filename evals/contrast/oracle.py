"""The single import point for contrast ground truth in the eval harness.

The eval measures whether running `humane:review` on a UI beats not running it.
Its ground truth is colour contrast only, and that truth is computed by
`humane/skills/design-tokens/scripts/dtokens/contrast.py` — the same code the
skill ships. Nothing in `evals/` may import `dtokens` directly: the moment two
modules reach for it, one of them will drift into reimplementing a formula, and
a fixture manifest that disagrees with the skill invalidates every number the
harness produces.

Two behaviours of the oracle are easy to assume wrongly, and both produce a
silently wrong manifest rather than a crash:

* **APCA Lc is signed.** Light text on a dark ground gives a negative Lc.
  `contrast.check()` gates on `abs(lc)`, so `measure` does too. Comparing the
  raw signed value marks every light-on-dark pair as failing and plants defects
  that are not defects.
* **The default standard is "both".** `#767676` on white clears WCAG (4.54) and
  misses APCA (71.6 against a 75 bar), so it *is* a body-text defect under the
  default. These disagreement cases are the point of the fixture.

This module is dev-only. Nothing under `humane/` imports it, and it must never
become a runtime dependency of a shipped skill.
"""

import sys
from pathlib import Path

_DTOKENS_SCRIPTS = (
    Path(__file__).resolve().parents[2]
    / "humane" / "skills" / "design-tokens" / "scripts"
)

# Resolved from __file__, never from cwd: the harness is run from the repo root,
# from evals/, and from pytest's rootdir, and a cwd-relative path would import
# under one of those and fail under the others.
if str(_DTOKENS_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_DTOKENS_SCRIPTS))

from dtokens.contrast import (  # noqa: E402
    THRESHOLDS,
    Unparseable,
    apca_lc,
    oklch_to_rgb,
    parse_color,
    to_hex,
    wcag_ratio,
)

__all__ = [
    "THRESHOLDS",
    "Unparseable",
    "apca_lc",
    "measure",
    "oklch_to_rgb",
    "parse_color",
    "to_hex",
    "wcag_ratio",
    "LEVELS",
    "STANDARD",
]

# The standard the manifest is computed under. `check()` defaults to "both" and
# the manifest records it, so a later change here is visible in the fixtures
# rather than silent.
STANDARD = "both"

LEVELS = tuple(sorted(THRESHOLDS))  # ("body", "graphic", "non-body")


def measure(fg_hex, bg_hex, level):
    """Return the contrast verdict for one foreground/background pair.

    `level` must be declared by the caller — `contrast.py` never infers
    "graphic", because a token's name cannot tell you whether it is painted as
    type, and the fixture generator is in exactly that position.

    An unparseable colour raises. In this harness a colour that cannot be read
    is a generator bug, not a "not measured" honesty case: dropping the pair
    would leave the manifest claiming a page has fewer colours than it renders.
    """
    if level not in THRESHOLDS:
        raise ValueError(
            f"level {level!r} is not one of {', '.join(LEVELS)}. `graphic` in "
            "particular must be declared, never inferred — a colour cannot tell "
            "you whether it is painted as type."
        )
    fg_rgb = parse_color(fg_hex)
    bg_rgb = parse_color(bg_hex)

    want = THRESHOLDS[level]
    lc = apca_lc(fg_rgb, bg_rgb)
    ratio = wcag_ratio(fg_rgb, bg_rgb)
    apca_pass = abs(lc) >= want["apca"]
    wcag_pass = ratio >= want["wcag"]
    return {
        "fg": fg_hex,
        "bg": bg_hex,
        "level": level,
        # Signed, as the oracle reports it. The pass flag above is what uses
        # abs(); the recorded number stays signed so a reader of the manifest
        # can see the polarity.
        "apca": round(lc, 1),
        "wcag": round(ratio, 2),
        "apca_pass": apca_pass,
        "wcag_pass": wcag_pass,
        "passed": apca_pass and wcag_pass,  # standard="both"
    }
