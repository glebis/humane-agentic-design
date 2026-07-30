"""Collect validation errors over a DTCG token tree (v1 subset).

`validate` returns hard errors (a non-empty list fails the CLI). `warnings`
returns soft advisories that never fail — used for the brand-style block: it is
optional per DTCG, but when it is absent the art-direction contract is silent and
downstream image generation (brand-illustrate, the prompt door) has no style to
honor. We nudge, we do not block.
"""

from . import model

# SKILL CONVENTION: brand-style block under $extensions at the token-file root.
BRAND_EXT_KEY = "community.design-tokens.brand"

ALLOWED_TYPES = {
    "color",
    "dimension",
    "duration",
    "fontFamily",
    "fontWeight",
    "number",
    "typography",
    "shadow",
}


def _detect_cycles(idx):
    errors = []
    for path, entry in idx.items():
        seen = []
        cur = path
        while True:
            node = idx[cur]["node"]
            value = node.get("$value")
            if not model.is_alias(value):
                break
            target = model.alias_target(value)
            if target not in idx:
                break  # dangling alias reported elsewhere
            if target in seen or target == path:
                errors.append(f"circular alias chain starting at {path}")
                break
            seen.append(target)
            cur = target
    return errors


def validate(tree):
    """Return a list of error strings; empty means the tree is valid."""
    idx = model.index(tree)
    errors = []

    for path, entry in idx.items():
        node = entry["node"]
        value = node.get("$value")

        if model.is_alias(value):
            target = model.alias_target(value)
            if target not in idx:
                errors.append(f"{path}: alias target {target} does not exist")

        ttype = model.resolve_type(path, entry, idx)
        if ttype is None:
            errors.append(f"{path}: cannot determine $type")
        elif ttype not in ALLOWED_TYPES:
            errors.append(f"{path}: $type {ttype!r} is not allowed in v1")

    errors.extend(_detect_cycles(idx))
    return errors


def warnings(tree):
    """Return a list of non-fatal advisory strings; empty means nothing to flag.

    Currently checks the art-direction contract: the brand-style block and its
    load-bearing `imageryStyle` field. Missing either is legal DTCG but leaves
    image generation without a style to confirm, so we warn.
    """
    out = []
    ext = tree.get("$extensions")
    brand = ext.get(BRAND_EXT_KEY) if isinstance(ext, dict) else None
    if not isinstance(brand, dict) or not brand:
        out.append(
            'no brand-style block ($extensions["%s"]): art direction is undefined, '
            "so downstream image generation has no style contract — brand-illustrate "
            "will ASK for a style instead of confirming one. Author mood + imageryStyle "
            "+ avoid (run design-tokens setup)." % BRAND_EXT_KEY
        )
    elif not brand.get("imageryStyle"):
        out.append(
            "brand block present but 'imageryStyle' is missing: it is the load-bearing "
            "art-direction field (flat-geometric / technical-line / risograph / painterly "
            "/ photographic / 3D-sculptural). Without it brand-illustrate cannot confirm a "
            "visual style and will ASK."
        )
    return out
