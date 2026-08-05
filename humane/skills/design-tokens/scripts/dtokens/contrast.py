"""Measure foreground/background contrast across a resolved token set.

DTCG says nothing about contrast — it stores colors, not relationships. This
module is a SKILL CONVENTION layered on top: it uses the same role inference as
`brand_summary` to guess which color is text and which is a surface, measures
every plausible pair, and reports the ones that fail.

Two scales are computed:

* **WCAG 2.x contrast ratio** — the legal/conformance number (4.5:1 body,
  3:1 large text and UI). Well known, widely required, and a poor model of
  perceived readability at the extremes.
* **APCA Lc** (W3C draft, algorithm version 0.1.9) — perceptual lightness
  contrast, polarity-aware: |Lc| >= 75 for body text, >= 60 for non-body.
  Better predictor of actual readability; still a draft, so it never stands
  alone as a conformance claim.

Both are reported. A pair fails only when it misses the threshold on the
standard being applied.

Honesty rule: a color we cannot parse (`var()`, `currentColor`, a gradient) is
reported as **not measured**, never as a failure. A verification gap is not a
finding.

Fixes follow `better-colors`' rule and DTCG's own value model: adjust OKLCH
lightness first, preserve chroma and hue, then re-measure.
"""

import math
import re

from .brand_summary import _flat_name, _infer_role

# SKILL CONVENTION: an optional declaration of which pairs actually meet, under
# $extensions at the token-file root. Name inference cannot know intent — our
# own set has a `paper-50` surface documented as "printed / risograph contexts",
# which never sits behind screen text, yet reads as a background by name. When
# this block is present its `pairs` are the whole truth; `exclude` always
# applies. Absent, we fall back to inference, so existing sets keep working.
#
#   "$extensions": {
#     "community.design-tokens.contrast": {
#       "pairs": [["text", "background"], ["on-primary", "primary"]],
#       "exclude": ["surface"]
#     }
#   }
CONTRAST_EXT_KEY = "community.design-tokens.contrast"


def extract_spec(tree):
    """Return the contrast declaration from a raw token tree, or {}."""
    ext = tree.get("$extensions")
    if isinstance(ext, dict):
        spec = ext.get(CONTRAST_EXT_KEY)
        if isinstance(spec, dict):
            return spec
    return {}


# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

# Applied per pair according to the foreground's inferred usage. "body" is text
# meant to be read in quantity; "non-body" covers links, icons, badges, and
# large display text, which both standards allow to be lighter; "graphic" is for
# a color that is never text — a fill, a rule, a chart mark, an icon shape —
# where WCAG 1.4.11 asks 3:1 as a UI component and APCA's floor is lower than
# any reading threshold. Declare it explicitly; inference never assigns it,
# because a token's name cannot tell you whether it is painted as type.
THRESHOLDS = {
    "body": {"apca": 75.0, "wcag": 4.5},
    "non-body": {"apca": 60.0, "wcag": 3.0},
    "graphic": {"apca": 45.0, "wcag": 3.0},
}

# Roles that read as running text when used as a foreground.
_BODY_ROLES = ("text", "muted")
# Roles that are typically links, icons, badges, or fills — held to the
# non-body bar unless the caller overrides with --level.
_NON_BODY_ROLES = ("primary", "accent", "success", "warning", "danger")


# ---------------------------------------------------------------------------
# Color parsing  (sRGB in, 0..255 ints out; alpha and unparseables rejected)
# ---------------------------------------------------------------------------

_HEX_RE = re.compile(r"^#([0-9a-fA-F]{3,8})$")
_RGB_RE = re.compile(r"^rgba?\(([^)]*)\)$", re.I)
_OKLCH_RE = re.compile(r"^oklch\(([^)]*)\)$", re.I)


class Unparseable(Exception):
    """The color is legal CSS but not something we can measure."""


def parse_color(value):
    """Return (r, g, b) as 0-255 ints, or raise Unparseable.

    Every malformed input leaves here as Unparseable, never as a ValueError:
    callers treat Unparseable as "not measured", and an escaping ValueError
    would turn an unreadable token into a crashed run.

    Accepts hex (3/4/6/8 digit), rgb()/rgba(), and oklch(). Anything carrying
    alpha is refused: contrast against a translucent color depends on what is
    behind it, which the token file does not know.
    """
    if not isinstance(value, str):
        raise Unparseable("not a string color value")
    v = value.strip()

    m = _HEX_RE.match(v)
    if m:
        h = m.group(1)
        if len(h) in (3, 4):
            h = "".join(c * 2 for c in h)
        if len(h) == 8:
            raise Unparseable("has alpha; contrast depends on the layer beneath")
        if len(h) != 6:
            raise Unparseable(f"unrecognised hex length: #{m.group(1)}")
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

    try:
        return _parse_body(v)
    except Unparseable:
        raise
    except (ValueError, TypeError, ArithmeticError) as exc:
        raise Unparseable(f"malformed color {v!r}: {exc}")


def _parse_body(v):
    m = _RGB_RE.match(v)
    if m:
        parts = [p for p in re.split(r"[,\s/]+", m.group(1).strip()) if p]
        if len(parts) >= 4:
            raise Unparseable("has alpha; contrast depends on the layer beneath")
        if len(parts) != 3:
            raise Unparseable(f"cannot read rgb() components from {v!r}")
        out = []
        for p in parts:
            if p.endswith("%"):
                out.append(round(float(p[:-1]) * 255 / 100))
            else:
                out.append(round(float(p)))
        return tuple(max(0, min(255, c)) for c in out)

    m = _OKLCH_RE.match(v)
    if m:
        body = m.group(1)
        if "/" in body:
            raise Unparseable("has alpha; contrast depends on the layer beneath")
        parts = [p for p in re.split(r"[,\s]+", body.strip()) if p]
        if len(parts) != 3:
            raise Unparseable(f"cannot read oklch() components from {v!r}")
        lightness = float(parts[0][:-1]) / 100 if parts[0].endswith("%") else float(parts[0])
        chroma = float(parts[1][:-1]) * 0.4 / 100 if parts[1].endswith("%") else float(parts[1])
        hue = _angle_to_degrees(parts[2])
        return oklch_to_rgb(lightness, chroma, hue)

    raise Unparseable(f"unsupported color notation: {v!r}")


def _angle_to_degrees(raw):
    """CSS <angle> to degrees. deg is the default; rad, grad and turn are not.

    Stripping the unit and keeping the number treats `0.25turn` as a quarter of
    a degree instead of a quarter turn — a silently wrong hue rather than an
    error, which is the worst kind of parsing bug.
    """
    text = raw.strip().lower()
    for unit, factor in (("turn", 360.0), ("grad", 0.9), ("rad", 180.0 / math.pi),
                         ("deg", 1.0)):
        if text.endswith(unit):
            return float(text[: -len(unit)]) * factor
    return float(text)


# ---------------------------------------------------------------------------
# sRGB <-> OKLCH  (Ottosson's OKLab, standard matrices)
# ---------------------------------------------------------------------------

def _srgb_to_linear(c):
    c = c / 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _linear_to_srgb(c):
    c = 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055
    return max(0, min(255, round(c * 255)))


def rgb_to_oklch(rgb):
    """Return (L, C, H) with L in 0..1, C in 0..~0.4, H in degrees."""
    r, g, b = (_srgb_to_linear(c) for c in rgb)
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l_, m_, s_ = (math.copysign(abs(v) ** (1 / 3), v) for v in (l, m, s))
    L = 0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
    a = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    bb = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_
    C = math.hypot(a, bb)
    H = math.degrees(math.atan2(bb, a)) % 360
    return (L, C, H)


def oklch_to_rgb(L, C, H):
    """Return (r, g, b) 0-255, clipped into sRGB. Out-of-gamut values clamp."""
    a = C * math.cos(math.radians(H))
    b = C * math.sin(math.radians(H))
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = (v ** 3 for v in (l_, m_, s_))
    r = 4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
    g = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
    bl = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s
    return tuple(_linear_to_srgb(c) for c in (r, g, bl))


def to_hex(rgb):
    return "#%02x%02x%02x" % tuple(rgb)


# ---------------------------------------------------------------------------
# WCAG 2.x
# ---------------------------------------------------------------------------

def relative_luminance(rgb):
    r, g, b = (_srgb_to_linear(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def wcag_ratio(fg, bg):
    """Contrast ratio 1..21, order-independent."""
    a, b = relative_luminance(fg), relative_luminance(bg)
    lo, hi = min(a, b), max(a, b)
    return (hi + 0.05) / (lo + 0.05)


# ---------------------------------------------------------------------------
# APCA  (W3C draft, algorithm 0.1.9 constants)
# ---------------------------------------------------------------------------

_MAIN_TRC = 2.4
_RCO, _GCO, _BCO = 0.2126729, 0.7151522, 0.0721750
_NORM_BG, _NORM_TXT = 0.56, 0.57
_REV_TXT, _REV_BG = 0.62, 0.65
_BLK_THRS, _BLK_CLMP = 0.022, 1.414
_SCALE_BOW, _SCALE_WOB = 1.14, 1.14
_LO_BOW_OFFSET, _LO_WOB_OFFSET = 0.027, 0.027
_DELTA_Y_MIN, _LO_CLIP = 0.0005, 0.1


def _apca_y(rgb):
    y = sum(co * ((c / 255) ** _MAIN_TRC)
            for co, c in zip((_RCO, _GCO, _BCO), rgb))
    return y + (_BLK_THRS - y) ** _BLK_CLMP if y < _BLK_THRS else y


def apca_lc(text_rgb, bg_rgb):
    """Signed APCA Lc. Positive = dark text on light background (BoW),
    negative = light text on dark (WoB). Compare |Lc| to the threshold."""
    y_txt, y_bg = _apca_y(text_rgb), _apca_y(bg_rgb)
    if abs(y_bg - y_txt) < _DELTA_Y_MIN:
        return 0.0
    if y_bg > y_txt:  # dark text on light background
        sapc = (y_bg ** _NORM_BG - y_txt ** _NORM_TXT) * _SCALE_BOW
        out = 0.0 if sapc < _LO_CLIP else sapc - _LO_BOW_OFFSET
    else:             # light text on dark background
        sapc = (y_bg ** _REV_BG - y_txt ** _REV_TXT) * _SCALE_WOB
        out = 0.0 if sapc > -_LO_CLIP else sapc + _LO_WOB_OFFSET
    return out * 100


# ---------------------------------------------------------------------------
# Remediation: adjust L, preserve C and H
# ---------------------------------------------------------------------------

def suggest_fix_multi(fg, bg, requirements, steps=200):
    """Like suggest_fix, but the candidate must clear every named scale.

    requirements: {"apca": 75.0, "wcag": 4.5}. Returns (hex, L) or None.
    """
    L, C, H = rgb_to_oklch(fg)
    direction = -1 if relative_luminance(bg) > relative_luminance(fg) else 1
    for i in range(1, steps + 1):
        cand_L = L + direction * (i / steps)
        if not 0 <= cand_L <= 1:
            break
        cand = oklch_to_rgb(cand_L, C, H)
        if all((abs(apca_lc(cand, bg)) if scale == "apca" else wcag_ratio(cand, bg)) >= want
               for scale, want in requirements.items()):
            return to_hex(cand), round(cand_L, 3)
    return None


def suggest_fix(fg, bg, standard, threshold, steps=200):
    """Walk the foreground's OKLCH lightness away from the background until the
    pair clears `threshold`, keeping chroma and hue. Returns (hex, L) or None
    when no lightness on the axis clears it (then chroma or the background has
    to move, which is a design decision, not a mechanical one)."""
    L, C, H = rgb_to_oklch(fg)
    # Move away from the background: darker text on a light ground, lighter on dark.
    direction = -1 if relative_luminance(bg) > relative_luminance(fg) else 1
    for i in range(1, steps + 1):
        cand_L = L + direction * (i / steps)
        if not 0 <= cand_L <= 1:
            break
        cand = oklch_to_rgb(cand_L, C, H)
        got = abs(apca_lc(cand, bg)) if standard == "apca" else wcag_ratio(cand, bg)
        if got >= threshold:
            return to_hex(cand), round(cand_L, 3)
    return None


# ---------------------------------------------------------------------------
# Pairing policy  (SKILL CONVENTION)
# ---------------------------------------------------------------------------

def _colors(resolved):
    """[(path, flat_name, role, value)] for every color token, sorted."""
    out = []
    for path in sorted(resolved):
        entry = resolved[path]
        if entry.get("type") == "color":
            name = _flat_name(path)
            out.append((path, name, _infer_role(name), entry.get("value")))
    return out


def _is_on_token(name):
    """True for an ink-on-fill token, at any nesting depth.

    `_flat_name` joins every group after the first, so `color.brand.on-primary`
    arrives as `brand-on-primary` — a prefix test alone misses it, and the token
    then falls through to role inference and gets measured against the *page
    background* instead of the fill it is painted on. Match the final segment
    instead, which is where the `on-` convention actually lives.
    """
    leaf = re.split(r"[-_.]", str(name).lower())
    for i, part in enumerate(leaf):
        if part == "on" and i + 1 < len(leaf):
            return True
    return str(name).lower().startswith(("on-", "on_"))


def _on_target(name):
    """The fill an `on-X` token names: everything after the `on` segment."""
    parts = re.split(r"[-_.]", str(name).lower())
    for i, part in enumerate(parts):
        if part == "on" and i + 1 < len(parts):
            return "-".join(parts[i + 1:])
    return None


# A trailing numeric step (`ink-950`, `amber-500`, `slate.800`) marks a palette
# ramp primitive, not a role assignment. `ink-950` is a swatch that happens to
# contain "ink"; `text` is the token that says where ink goes. Measuring ramp
# steps against backgrounds produces confident nonsense — in our own token set
# it paired `ink-950` with a near-identical `background` and demanded the ink
# be lightened. Roles are read from semantic names only.
_RAMP_STEP_RE = re.compile(r"[-_.]\d{2,4}$")


def is_palette_step(name):
    return bool(_RAMP_STEP_RE.search(name))


def _lookup(token, resolved, by_name, by_role, near=None):
    """Resolve a name from the contrast declaration to a token path. Accepts a
    full path ('color.text'), a flat name ('text'), or a role ('background').

    `near` is a path whose group should win a tie. Flat names are not unique —
    `color.brand.primary` and `color.chart.primary` share the leaf `primary` —
    and silently taking whichever sorted last means `on-primary` can be measured
    against a fill it was never painted on. That produces a confident number
    about the wrong pair, which is worse than no number. When `near` is given,
    a candidate in the same group is preferred before falling back.
    """
    # A declaration is user data: it can hold a list, a dict, or None where a
    # name belongs. `token in resolved` raises TypeError on an unhashable one,
    # which turns a bad declaration into a crashed run — the same failure mode
    # parse_color was fixed for.
    if not isinstance(token, str):
        return None
    if token in resolved:
        return token
    low = token.lower()
    hits = by_name.get(low) or by_role.get(low) or []
    if not hits:
        return None
    if len(hits) > 1 and near:
        group = near.rsplit(".", 1)[0]
        for path in hits:
            if path.rsplit(".", 1)[0] == group:
                return path
    return hits[0]


def build_pairs(resolved, level="auto", spec=None, unresolved=None):
    """Return [(fg, bg, level)] of token paths worth measuring.

    `unresolved` is an optional list that collects
    `(name, where, why)` for every declared token that could not be resolved, so
    the caller can report it rather than drop it.

    When `spec` declares `pairs`, those are measured and nothing else — including
    when the list is empty. Otherwise pairs are inferred:
      * every text/muted color over every background color        -> body
      * every primary/accent/success/warning/danger over every
        background color                                          -> non-body
      * every `on-X` color over the fill it names (only that fill) -> body

    `spec["exclude"]` drops any pair touching those tokens either way. Palette
    ramp steps (`ink-950`, `amber-500`) are skipped on both sides — see
    `is_palette_step`. `level` of "body"/"non-body" overrides the per-pair choice.
    """
    spec = spec or {}
    unresolved = [] if unresolved is None else unresolved
    cols = [c for c in _colors(resolved) if not is_palette_step(c[1])]
    by_role, by_name, role_of = {}, {}, {}
    for path, name, role, _value in cols:
        # Index both the flat name (`brand-primary`) and the bare final segment
        # (`primary`), each to every path that carries it — not just the last
        # one seen. A declaration says `["on-primary", "primary"]`, not
        # `["brand-on-primary", "brand-primary"]`, so the short form has to
        # resolve; and because it is ambiguous across groups, `_lookup` needs
        # every candidate in order to prefer the one in the same group.
        for key in {name.lower(), path.rsplit(".", 1)[-1].lower()}:
            by_name.setdefault(key, []).append(path)
        role_of[path] = role
        if role:
            by_role.setdefault(role, []).append(path)

    excluded = set()
    exclude_spec = spec.get("exclude")
    if exclude_spec is not None and not isinstance(exclude_spec, (list, tuple)):
        # `"exclude": 1` would otherwise raise TypeError from iteration.
        unresolved.append((repr(exclude_spec), "exclude",
                           "must be a list of token names; ignored"))
        exclude_spec = []
    for token in exclude_spec or []:
        path = _lookup(token, resolved, by_name, by_role)
        if path:
            excluded.add(path)
        else:
            unresolved.append((str(token), "exclude", "no such color token"))

    pairs = []

    def add(fg, bg, lvl):
        if fg != bg and fg not in excluded and bg not in excluded:
            pairs.append((fg, bg, level if level != "auto" else lvl))

    # `pairs` **present but empty** is a declaration that nothing meets, not an
    # absent declaration. Falling through to inference there would measure a set
    # the author explicitly emptied, which is the opposite of what they wrote.
    declared = spec.get("pairs")
    if declared is not None and not isinstance(declared, (list, tuple)):
        # A `pairs` key of the wrong shape is still a *declaration*. Falling
        # through to inference here would measure the whole set the author was
        # trying to narrow, and exit 0 on it — a green gate produced by a typo.
        unresolved.append((repr(declared), "pairs",
                           "must be a list of [foreground, background] entries; "
                           "nothing was measured"))
        return pairs
    if declared is not None:
        for entry in declared:
            if not isinstance(entry, (list, tuple)) or len(entry) < 2:
                unresolved.append((repr(entry), "pairs",
                                   "not a [foreground, background] entry"))
                continue
            # Resolve the unambiguous side first and use it as the group hint for
            # the other. Passing `near` only to the background meant an exact
            # background could not disambiguate a short foreground name, so
            # `["on-primary", "color.z.primary"]` measured `color.a.on-primary`
            # against `color.z.primary` — a confident number about two tokens
            # that never meet.
            fg = _lookup(entry[0], resolved, by_name, by_role)
            bg = _lookup(entry[1], resolved, by_name, by_role, near=fg)
            if bg:
                fg = _lookup(entry[0], resolved, by_name, by_role, near=bg)
            # A declared pair that does not resolve is the one case that must
            # never pass quietly: the author named it *because* it is the pair
            # that matters, so dropping it leaves the gate green over the very
            # thing it was told to check. Report it as unmeasured.
            if not fg or not bg:
                missing = [str(t) for t, p in ((entry[0], fg), (entry[1], bg)) if not p]
                unresolved.append((" / ".join(missing), "pairs",
                                   "no such color token"))
                continue
            if fg == bg:
                # Both names point at one token. There is no pair to measure,
                # and staying silent means a declaration of `["text", "text"]`
                # yields no results, no error, and exit 0.
                unresolved.append((f"{entry[0]} / {entry[1]}", "pairs",
                                   f"both names resolve to {fg} — a token has no "
                                   f"contrast with itself"))
                continue
            # A declared pair is measured at the level its foreground role
            # implies, unless the entry names one explicitly as a third item.
            lvl = None
            if len(entry) > 2:
                if entry[2] in THRESHOLDS:
                    lvl = entry[2]
                else:
                    # Skip the pair rather than fall back to the inferred level.
                    # Measuring it anyway against a bar the author did not choose,
                    # while the report says "NOT measured", is a contradiction in
                    # a single run — and the fallback bar may be the laxer one.
                    unresolved.append((
                        str(entry[2]), "pairs",
                        f"unknown level; expected one of {', '.join(sorted(THRESHOLDS))}"))
                    continue
            if lvl is None:
                # An `on-X` token is ink by definition, whatever fill name it
                # carries: `on-primary` infers the role "primary" and would
                # otherwise be held to the non-body bar here while inference
                # holds the very same pair to `body` — the same ink measured
                # more leniently just because someone declared it.
                if _is_on_token(_flat_name(fg)):
                    lvl = "body"
                else:
                    lvl = "non-body" if role_of.get(fg) in _NON_BODY_ROLES else "body"
            add(fg, bg, lvl)
        return pairs

    backgrounds = by_role.get("background", [])

    for path, name, role, _value in cols:
        if _is_on_token(name):
            # `on-primary` is ink placed on the `primary` fill — pair it with
            # that fill, not with the page background. `near=path` keeps the
            # match inside the same group, so `brand.on-primary` resolves to
            # `brand.primary` and not to a `chart.primary` that merely shares
            # the leaf name.
            target = _on_target(name)
            fill = _lookup(target, resolved, by_name, by_role, near=path) if target else None
            if fill:
                add(path, fill, "body")
            continue
        if role in _BODY_ROLES:
            for bg in backgrounds:
                add(path, bg, "body")
        elif role in _NON_BODY_ROLES:
            for bg in backgrounds:
                add(path, bg, "non-body")

    return pairs


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def check(resolved, standard="both", level="auto", spec=None):
    """Measure every pair. Returns {'results': [...], 'unmeasured': [...]}.

    Each result: {fg, bg, fg_value, bg_value, level, apca, wcag, apca_pass,
    wcag_pass, passed, fix}. `passed` reflects `standard` ("apca", "wcag", or
    "both" = must clear both). `unmeasured` holds (path, value, reason) for
    colors we refused to guess at, and `undeclared` holds (name, where, why) for
    names in the contrast declaration that match no token — a typo in a declared
    pair must not read as a clean run.
    """
    results, unmeasured, cache = [], [], {}
    undeclared = []

    def rgb_of(path):
        if path not in cache:
            value = resolved[path].get("value")
            try:
                cache[path] = parse_color(value)
            except Unparseable as exc:
                cache[path] = None
                unmeasured.append((path, value, str(exc)))
        return cache[path]

    identical = []
    for fg, bg, lvl in build_pairs(resolved, level=level, spec=spec,
                                   unresolved=undeclared):
        fg_rgb, bg_rgb = rgb_of(fg), rgb_of(bg)
        if fg_rgb is None or bg_rgb is None:
            continue
        if fg_rgb == bg_rgb:
            # Two names for one color. Whether that is benign depends entirely
            # on the pair: two neutrals sharing a value is an alias worth
            # noting, but a *declared* foreground/background pair resolving to
            # one color means invisible text — Lc 0, ratio 1:1 — and the worst
            # possible thing for this command to do is call it "not a contrast
            # question" and exit 0. It is the most severe failure there is.
            identical.append((fg, bg, to_hex(fg_rgb)))
            want = THRESHOLDS[lvl]
            results.append({
                "fg": fg, "bg": bg,
                "fg_value": to_hex(fg_rgb), "bg_value": to_hex(bg_rgb),
                "level": lvl, "apca": 0.0, "wcag": 1.0,
                "apca_pass": False, "wcag_pass": False, "passed": False,
                "identical": True,
                # No lightness move on the foreground alone is "the fix" here;
                # the pair itself is wrong. Say so instead of proposing a colour.
                "fix": None,
            })
            continue
        want = THRESHOLDS[lvl]
        lc = apca_lc(fg_rgb, bg_rgb)
        ratio = wcag_ratio(fg_rgb, bg_rgb)
        apca_ok = abs(lc) >= want["apca"]
        wcag_ok = ratio >= want["wcag"]
        passed = {"apca": apca_ok, "wcag": wcag_ok,
                  "both": apca_ok and wcag_ok}[standard]
        fix = None
        if not passed:
            # Satisfy whichever scales actually gate. Optimising for APCA alone
            # usually clears WCAG too, but "usually" is not a guarantee, and a
            # proposed fix that still fails the gate is worse than none.
            need = {"apca": ["apca"], "wcag": ["wcag"],
                    "both": ["apca", "wcag"]}[standard]
            fix = suggest_fix_multi(fg_rgb, bg_rgb, {s: want[s] for s in need})
        results.append({
            "fg": fg, "bg": bg,
            "fg_value": to_hex(fg_rgb), "bg_value": to_hex(bg_rgb),
            "level": lvl,
            "apca": round(lc, 1), "wcag": round(ratio, 2),
            "apca_pass": apca_ok, "wcag_pass": wcag_ok,
            "passed": passed, "fix": fix,
        })

    # Deduplicate unmeasured (a color can appear in many pairs).
    seen, uniq = set(), []
    for item in unmeasured:
        if item[0] not in seen:
            seen.add(item[0])
            uniq.append(item)
    declared = (spec or {}).get("pairs")
    return {"results": results, "unmeasured": uniq, "identical": identical,
            "undeclared": undeclared,
            "declared_empty": isinstance(declared, (list, tuple)) and not declared}


def failures(resolved, standard="both", level="auto", spec=None):
    """Failing pairs only, as advisory strings — the shape validate/use want."""
    report = check(resolved, standard=standard, level=level, spec=spec)
    out = []
    for r in report["results"]:
        if r["passed"]:
            continue
        if r.get("identical"):
            out.append(f"contrast: {r['fg']} and {r['bg']} are both "
                       f"{r['fg_value']} — the text is invisible on its own "
                       f"background (Lc 0, 1.0:1). Point one of them at a "
                       f"different token.")
            continue
        want = THRESHOLDS[r["level"]]
        msg = (f"contrast: {r['fg']} ({r['fg_value']}) on {r['bg']} "
               f"({r['bg_value']}) — APCA Lc {r['apca']} "
               f"(need {want['apca']:g}), WCAG {r['wcag']}:1 "
               f"(need {want['wcag']:g}) for {r['level']} text")
        if r["fix"]:
            msg += f"; try {r['fix'][0]} (same hue and chroma, L={r['fix'][1]})"
        out.append(msg)
    for name, where, why in report.get("undeclared") or []:
        # An author names a pair precisely because it is the one that matters.
        # If the name is wrong, silence would leave the gate green over exactly
        # the pair it was told to check.
        out.append(f"contrast: {where} names {name} — {why}. That pair was "
                   f"not measured.")
    return out


def format_report(report, standard="both"):
    """Human-readable text for the `contrast` command."""
    lines = []
    results = report["results"]
    if not results:
        # Say which of the two reasons applies. "No tokens matched the roles"
        # sent to someone who wrote `pairs: []` is a wrong answer to "why did it
        # measure nothing?".
        if report.get("declared_empty"):
            lines.append("no pairs measured: the contrast declaration lists an "
                         "empty `pairs` array, so nothing was checked")
        else:
            lines.append("no measurable text/background pairs found "
                         "(no color tokens matched the text/background roles)")
    else:
        fails = [r for r in results if not r["passed"]]
        lines.append(f"{len(results)} pair(s) measured, {len(fails)} failing "
                     f"(standard: {standard})")
        lines.append("")
        width = max(len(f"{r['fg']} on {r['bg']}") for r in results)
        for r in sorted(results, key=lambda r: (r["passed"], r["fg"], r["bg"])):
            mark = "PASS" if r["passed"] else "FAIL"
            label = f"{r['fg']} on {r['bg']}".ljust(width)
            lines.append(f"  {mark}  {label}  Lc {r['apca']:>6}  "
                         f"{r['wcag']:>5}:1  [{r['level']}]")
            if r["fix"]:
                lines.append(f"        fix: {r['fg_value']} -> {r['fix'][0]} "
                             f"(OKLCH L {r['fix'][1]}, chroma and hue unchanged)")
    if report.get("identical"):
        lines.append("")
        # These are counted among the failures above. The header used to call
        # them "not a contrast failure", which contradicted the gate that fails
        # them — a declared pair resolving to one color is invisible text.
        lines.append("same color on both sides — invisible text, "
                     "counted as failures above:")
        for fg, bg, value in report["identical"]:
            lines.append(f"  {fg} and {bg} are both {value}")
    if report["unmeasured"]:
        lines.append("")
        lines.append("not measured (reported, not counted as failures):")
        for path, value, reason in report["unmeasured"]:
            lines.append(f"  {path} = {value!r} — {reason}")
    if report.get("undeclared"):
        lines.append("")
        lines.append("named in the contrast declaration but not found "
                     "(these pairs were NOT measured):")
        for name, where, why in report["undeclared"]:
            lines.append(f"  {where}: {name} — {why}")
    return "\n".join(lines) + "\n"
