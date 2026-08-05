"""The specimen config: its slot contract, defaults, and validation.

The page renders ten text slots. Each has a fixed shape — one line or many,
and for some, a fixed number of `::`-separated cells per line. The shape is
enforced here rather than in the page, because a malformed slot in the browser
degrades into a silently empty table cell that nobody notices.
"""

import json
import pathlib
import re

from . import SpecimenError

# name -> (multiline, cells_per_line)
# cells_per_line of 1 means the line is not split on `::` at all.
SLOTS = {
    "display": (False, 1),
    "timer": (False, 1),
    "headline": (False, 1),
    "weights": (False, 1),
    "prose": (True, 1),
    "caps": (False, 1),
    "rows": (True, 2),
    "table": (True, 3),
    "tableHead": (False, 3),
    "alphabet": (True, 1),
}

LOCALES = ("en", "ru")

# Written into a fresh config so `init` produces a page that renders, and so a
# reviewer can see at a glance which slots are still boilerplate.
PLACEHOLDER = "TODO"

_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")

DEFAULTS = {
    "locale": "en",
    "scriptRange": "",
    "probe": "Hamburgefonstiv 0123456789",
    "bg": "#000000",
    "fg": "#E6E1DA",
    "dark": ["#000000", "#E6E1DA"],
    "light": ["#FFFFFF", "#171310"],
    "contrastPreview": ["Aa", "Aa"],
    "palette": ["#000000", "#171310", "#171717", "#E6E1DA", "#FFFFFF",
                "#B0A9A1", "#8F8880", "#FF995E", "#E1AE42", "#89C5F8"],
    "size": 16,
    "weight": 400,
    "lh": 1.55,
    "ls": 0.0,
    "groups": [],
    "families": [],
    "glyphSets": [],
    "notes": [],
    "context": "",
}

# Slot text for a config that has not been filled in yet. Deliberately generic:
# the skill's job is to replace all of it with copy from the real product.
STARTER_TEXTS = {
    "display": PLACEHOLDER,
    "timer": "0123456789",
    "headline": PLACEHOLDER,
    "weights": PLACEHOLDER,
    "prose": PLACEHOLDER,
    "caps": PLACEHOLDER,
    "rows": f"{PLACEHOLDER} :: {PLACEHOLDER}",
    "table": f"{PLACEHOLDER} :: {PLACEHOLDER} :: {PLACEHOLDER}",
    "tableHead": f"{PLACEHOLDER} :: {PLACEHOLDER} :: {PLACEHOLDER}",
    "alphabet": "ABCDEFGHIJKLMNOPQRSTUVWXYZ\nabcdefghijklmnopqrstuvwxyz\n0123456789",
}

STARTER_GLYPH_SETS = [
    ["Arrows", "← → ↑ ↓ ↔ ⇄"],
    ["Maths and currency", "± × ÷ ≈ ≠ ≤ ≥ € $ ¥ £"],
    ["Typography", "« » „ “ ” – — … § ¶ № † ‡ • ‰"],
]


def starter(locale="en", context="", title="Type specimen", ident="specimen"):
    """A config that builds and renders, with every judgement call left as TODO."""
    if locale not in LOCALES:
        raise SpecimenError(f"locale must be one of {', '.join(LOCALES)}, got {locale!r}")
    cfg = dict(DEFAULTS)
    cfg.update({
        "id": ident,
        "title": title,
        "locale": locale,
        "context": context,
        "texts": dict(STARTER_TEXTS),
        "glyphSets": [list(g) for g in STARTER_GLYPH_SETS],
        "families": [{"name": "Inter", "group": "sf", "note": ""}],
        "groups": [{"id": "sf", "label": "Sans"}],
    })
    if locale == "ru":
        cfg["scriptRange"] = r"U\+04"
        cfg["probe"] = "Съешь ещё этих мягких булок 0123456789"
        # A Cyrillic specimen that only shows Latin proves nothing about the
        # half of the font the reader actually cares about.
        cfg["texts"]["alphabet"] = (
            "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ\n"
            "абвгдеёжзийклмнопрстуфхцчшщъыьэюя\n"
            "ABCDEFGHIJKLMNOPQRSTUVWXYZ\n0123456789")
        cfg["glyphSets"] = [
            ["Стрелки", "← → ↑ ↓ ↔ ⇄"],
            ["Математика и валюты", "± × ÷ ≈ ≠ ≤ ≥ ₽ € $ ¥ £"],
            ["Типографика", "« » „ “ ” – — … § ¶ № † ‡ • ‰"],
        ]
        cfg["groups"] = [{"id": "sf", "label": "Гротески"}]
    return cfg


def load(path):
    """Read a config, apply defaults, and validate. Raises SpecimenError."""
    p = pathlib.Path(path)
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SpecimenError(f"no such config: {p}")
    except json.JSONDecodeError as exc:
        raise SpecimenError(f"{p} is not valid JSON: {exc}")
    if not isinstance(raw, dict):
        raise SpecimenError(f"{p} must contain a JSON object")
    cfg = dict(DEFAULTS)
    cfg.update(raw)
    cfg.setdefault("id", p.stem)
    cfg.setdefault("title", cfg["id"])
    cfg["texts"] = {**STARTER_TEXTS, **(raw.get("texts") or {})}
    errors = validate(cfg)
    if errors:
        raise SpecimenError("\n".join(f"  - {e}" for e in errors))
    return cfg


def validate(cfg):
    """Every problem in the config, as a list of messages. Empty means valid."""
    errors = []

    if cfg.get("locale") not in LOCALES:
        errors.append(f"locale must be one of {', '.join(LOCALES)}, got {cfg.get('locale')!r}")

    ident = cfg.get("id") or ""
    if not re.fullmatch(r"[A-Za-z0-9._-]+", str(ident)):
        # `id` keys the localStorage bucket, so two specimens sharing one would
        # overwrite each other's saved state.
        errors.append(f"id must be non-empty and match [A-Za-z0-9._-]+, got {ident!r}")

    errors += _validate_colors(cfg)
    errors += _validate_families(cfg)
    errors += _validate_texts(cfg.get("texts") or {})
    errors += _validate_glyph_sets(cfg.get("glyphSets"))

    if cfg.get("scriptRange"):
        try:
            re.compile(cfg["scriptRange"])
        except re.error as exc:
            errors.append(f"scriptRange is not a valid regex: {exc}")

    for key, lo, hi in (("size", 11, 30), ("weight", 100, 900), ("lh", 1.0, 2.2), ("ls", -0.05, 0.2)):
        v = cfg.get(key)
        if not isinstance(v, (int, float)) or isinstance(v, bool) or not lo <= v <= hi:
            # The panel sliders clamp to these ranges; a value outside them
            # cannot be reached again once the user touches the slider.
            errors.append(f"{key} must be a number in {lo}..{hi}, got {v!r}")

    cp = cfg.get("contrastPreview")
    if not (isinstance(cp, list) and len(cp) == 2 and all(isinstance(x, str) for x in cp)):
        errors.append("contrastPreview must be a list of exactly 2 strings")

    for key in ("notes",):
        v = cfg.get(key)
        if not isinstance(v, list) or not all(isinstance(x, str) for x in v):
            errors.append(f"{key} must be a list of strings")

    return errors


def _validate_colors(cfg):
    errors = []
    for key in ("bg", "fg"):
        if not _HEX.match(str(cfg.get(key, ""))):
            errors.append(f"{key} must be a #RRGGBB hex colour, got {cfg.get(key)!r}")
    for key in ("dark", "light"):
        pair = cfg.get(key)
        if not (isinstance(pair, list) and len(pair) == 2 and all(_HEX.match(str(c)) for c in pair)):
            errors.append(f"{key} must be a [background, text] pair of #RRGGBB colours, got {pair!r}")
    pal = cfg.get("palette")
    if not isinstance(pal, list) or not pal:
        errors.append("palette must be a non-empty list of #RRGGBB colours")
    else:
        bad = [c for c in pal if not _HEX.match(str(c))]
        if bad:
            errors.append(f"palette contains non-hex entries: {bad}")
    return errors


def _validate_families(cfg):
    errors = []
    fams = cfg.get("families")
    if not isinstance(fams, list) or not fams:
        return ["families must be a non-empty list of {name, group, note} objects"]

    group_ids = set()
    groups = cfg.get("groups")
    if not isinstance(groups, list):
        errors.append("groups must be a list of {id, label} objects")
    else:
        for g in groups:
            if not (isinstance(g, dict) and isinstance(g.get("id"), str) and isinstance(g.get("label"), str)):
                errors.append(f"each group needs a string id and label, got {g!r}")
            elif g["id"] == "all":
                # "all" is the built-in filter the page prepends.
                errors.append("group id 'all' is reserved")
            else:
                group_ids.add(g["id"])

    seen = set()
    for f in fams:
        if not (isinstance(f, dict) and isinstance(f.get("name"), str) and f["name"].strip()):
            errors.append(f"each family needs a non-empty string name, got {f!r}")
            continue
        name = f["name"].strip()
        if "::" in name or "\n" in name:
            # The panel round-trips families through a `name :: group :: note`
            # textarea, so either character would corrupt the list on Apply.
            errors.append(f"family name may not contain '::' or a newline: {name!r}")
        if name in seen:
            errors.append(f"duplicate family: {name!r}")
        seen.add(name)
        grp = f.get("group", "")
        if grp and group_ids and grp not in group_ids:
            errors.append(f"family {name!r} is in group {grp!r}, which is not declared in groups")
    return errors


def _validate_texts(texts):
    errors = []
    if not isinstance(texts, dict):
        return ["texts must be an object"]
    for key in texts:
        if key not in SLOTS:
            errors.append(f"unknown text slot {key!r}; known slots: {', '.join(SLOTS)}")
    for key, (multiline, cells) in SLOTS.items():
        v = texts.get(key)
        if not isinstance(v, str) or not v.strip():
            errors.append(f"texts.{key} must be a non-empty string")
            continue
        lines = [ln for ln in v.split("\n") if ln.strip()]
        if not multiline and len(lines) > 1:
            errors.append(f"texts.{key} must be a single line, got {len(lines)}")
        for i, ln in enumerate(lines, 1):
            got = len(ln.split("::"))
            if got != cells:
                errors.append(
                    f"texts.{key} line {i} must have {cells} '::'-separated "
                    f"cell(s), got {got}: {ln.strip()!r}")
    return errors


def _validate_glyph_sets(sets):
    if not isinstance(sets, list):
        return ["glyphSets must be a list of [label, characters] pairs"]
    errors = []
    for g in sets:
        if not (isinstance(g, list) and len(g) == 2 and all(isinstance(x, str) and x.strip() for x in g)):
            errors.append(f"each glyphSet must be a [label, characters] pair of non-empty strings, got {g!r}")
    return errors


def todos(cfg):
    """Slots still holding starter boilerplate, in config order."""
    texts = cfg.get("texts") or {}
    return [k for k in SLOTS if PLACEHOLDER in str(texts.get(k, ""))]
