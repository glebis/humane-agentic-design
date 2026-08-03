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


def validate(tree, strict=False):
    """Return a list of error strings; empty means the tree is valid.

    `strict=True` also promotes non-DTCG dimension/duration values (clamp(),
    calc(), var(), and other CSS kept verbatim) from warnings to errors — i.e.
    it flags them as spec deviations. Default behaviour keeps them as warnings.
    """
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
    if strict:
        resolved = _safe_resolve(tree)
        errors.extend(dimension_warnings(resolved))
        errors.extend(contrast_warnings(resolved, _contrast_spec(tree)))
    return errors


def _safe_resolve(tree):
    """Resolve for advisory checks; return {} if the tree can't resolve (its
    hard errors are reported by validate() and take precedence)."""
    from . import resolve as _resolve
    from . import TokenError
    try:
        return _resolve.resolve(tree)
    except TokenError:
        return {}


def _is_dtcg_dimension(value):
    return isinstance(value, dict) and "value" in value and "unit" in value


def dimension_warnings(resolved):
    """Advisories for dimension/duration (and typography.fontSize) values that
    are strings we can't parse into {value, unit} — legitimate CSS (clamp/calc/
    var) kept verbatim rather than dropped. Empty means nothing to flag."""
    out = []
    for path in sorted(resolved):
        entry = resolved[path]
        ttype, value = entry["type"], entry["value"]
        if ttype in ("dimension", "duration"):
            if isinstance(value, str) and not _is_dtcg_dimension(value):
                out.append(f"non-DTCG {ttype} kept verbatim: {path} = {value!r}")
        elif ttype == "typography" and isinstance(value, dict):
            fs = value.get("fontSize")
            if isinstance(fs, str):
                out.append(f"non-DTCG dimension kept verbatim: {path}.fontSize = {fs!r}")
    return out


def brand_warnings(tree):
    """Non-fatal advisories on the art-direction contract: the brand-style block
    and its load-bearing `imageryStyle` field. Missing either is legal DTCG but
    leaves image generation without a style to confirm, so we warn."""
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


def contrast_warnings(resolved, spec=None):
    """Advisories for role pairs that miss the readability thresholds. SKILL
    CONVENTION: DTCG stores no relationships, so the text/background pairs are
    inferred from token names (see contrast.build_pairs). Colors we cannot parse
    are reported as unmeasured by the `contrast` command, never as failures
    here — a verification gap is not a finding."""
    if not resolved:
        return []
    from . import contrast as _contrast
    return _contrast.failures(resolved, spec=spec)


def warnings(tree):
    """All non-fatal advisories for a tree: the brand-style contract, any
    non-DTCG dimension/duration values kept verbatim, and failing contrast
    pairs. Best-effort — resolved checks are skipped if the tree can't resolve."""
    resolved = _safe_resolve(tree)
    return (brand_warnings(tree)
            + dimension_warnings(resolved)
            + contrast_warnings(resolved, _contrast_spec(tree)))


def _contrast_spec(tree):
    from . import contrast as _contrast
    return _contrast.extract_spec(tree)
