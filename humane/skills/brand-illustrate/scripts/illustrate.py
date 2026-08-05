#!/usr/bin/env python3
"""brand-illustrate adapter: token file + questionnaire answers -> on-brand image batch.

Ring-2 humane skill. Stdlib only, self-contained, portable. It sits ABOVE
design-tokens' own `generate` command and adds the layer that turns one-off
generation into a *coherent set*:

  - reads the on-brand contract straight from the token `.tokens.json`
    (palette with roles, fonts, shape, and the $extensions brand block) — it
    does NOT import the dtokens package, so it runs on any agent that installed
    brand-illustrate alone;
  - assembles a deterministic prompt scaffold: palette prose + mood/imageryStyle
    + the user's questionnaire answers + a shared series-coherence block + a
    negative-prompt list that MERGES the built-in de-slop rules (layout-rules
    31-39) with the brand's own avoid/negativePrompt and any user negatives;
  - resolves platform presets (og-image, 16:9 thumbnail, square post, deck
    cover, spot/UI) into a size manifest;
  - discovers the gpt-image-2 / nano-banana backend scripts (generators stay
    OUTSIDE the plugin — guardrail) without assuming any one agent's layout:
    HUMANE_IMAGE_BACKEND, then HUMANE_SKILLS_DIR, then the known agent skill
    roots (Claude Code, Codex, XDG, project .agents/.claude), then a matching
    executable on PATH — shells out and writes a batch dir with metadata.json
    + recipe.json;
  - when NO backend is found it does not stop: it writes prompts.md with every
    final on-brand prompt plus metadata and the recipe, so the work survives and
    the batch resumes with `run --recipe` once a generator exists.

Design note (adapter shape): the backend *scripts* are the stable, documented
public surface (their SKILL.md publishes the CLI). Probing + shelling them here
gives one testable unit that captures deterministic metadata, instead of asking
the agent to orchestrate N generations by hand (no metadata, non-deterministic)
or importing dtokens internals (private API, breaks portability).

CLI:
  illustrate.py platforms                       # list platform presets
  illustrate.py backends [-v]                    # what was found, and where we looked
  illustrate.py scaffold --tokens F --answers A  # print resolved scaffold JSON
  illustrate.py run --tokens F --answers A [--out-dir D] [--dry-run]
  illustrate.py run --recipe recipe.json [--out-dir D]   # reuse last recipe
"""

import argparse
import colorsys
import datetime
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

# ---------------------------------------------------------------------------
# Platform presets (target sizes) and their nearest backend-native platform.
# `flag` is the backend `--platform` name when one matches exactly; otherwise
# None and we pass the raw --size (gpt-image-2) / record a resize note (nano).
# ---------------------------------------------------------------------------
PLATFORMS = {
    "og-image":      {"w": 1200, "h": 630,  "flag": "blog",   "desc": "Open Graph / link preview"},
    "thumbnail-16-9":{"w": 1280, "h": 720,  "flag": "youtube","desc": "16:9 video / card thumbnail"},
    "square-post":   {"w": 1080, "h": 1080, "flag": "square", "desc": "Instagram / square social post"},
    "deck-cover":    {"w": 1920, "h": 1080, "flag": "slides", "desc": "Slide / deck cover"},
    "spot-ui":       {"w": 512,  "h": 512,  "flag": None,     "desc": "Spot illustration / UI asset"},
}
DEFAULT_PLATFORM = "square-post"

# De-slop negative prompts, derived from layout-rules 31-39. Phrased for image
# models. Merged with the brand's own avoid-list and any user negatives.
DESLOP_NEGATIVES = [
    "no gradient soup, no gradient-filled text, no glassmorphism",           # 33
    "no generic 3D blobs, no glossy corporate-memphis mascots",              # brief + 33
    "no uniform rounded-corner cards, no nested card-in-card layouts",       # 33
    "no default-AI cliche: warm-cream + high-contrast serif + terracotta",   # 31
    "no near-black canvas with a lone acid-green or vermilion pop",          # 31
    "no template hero of big-number + tiny-label + gradient accent",         # 32
    "no emoji or 01/02/03 numbered markers used as decoration",              # 35
    "nothing forced dead-centre; no gray text on a colored fill",            # 35, 36
    "no lens flare, no neon glow, no bokeh, no stock-photo people",          # de-slop / brand
]

# Backend resolution. The generators live outside the plugin, so we discover
# them rather than depend on them — and the search must not assume any one
# agent's directory layout. Precedence, first hit wins:
#
#   1. HUMANE_IMAGE_BACKEND=<name>:<path>  — an explicit override, always wins
#   2. HUMANE_SKILLS_DIR                   — a colon-separated list of skill roots
#   3. the agent skill dirs we know about  — Claude Code, Codex, the `skills`
#      CLI convention, and this plugin's own tree
#   4. an executable of that name on PATH  — a generator packaged as a CLI
#
# Nothing here is Claude-specific: ~/.claude/skills is one candidate among
# several, not the assumption.
_PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[3]  # .../humane

# Where agents keep skills, relative to $HOME unless absolute.
_SKILL_ROOTS = [
    pathlib.Path("~/.claude/skills"),      # Claude Code
    pathlib.Path("~/.codex/skills"),       # Codex
    pathlib.Path("~/.config/skills"),      # XDG-ish
    pathlib.Path(".agents/skills"),        # `npx skills add`, project scope
    pathlib.Path(".claude/skills"),        # project scope
    _PLUGIN_ROOT / "skills",               # bundled alongside humane, if ever
]

# script filename within a skill dir, and the PATH executable name
_BACKENDS = {
    "gpt-image-2": {"script": "gpt_image_2.py", "exe": "gpt-image-2"},
    "nano-banana": {"script": "nano_banana.py", "exe": "nano-banana"},
}


def _config_value(project_dir=None):
    """The raw `image_backend` setting and where it came from, or (None, None).

    `setup` owns this setting: project `humane.json` > `~/.humane/config.json` >
    `HUMANE_IMAGE_BACKEND` > `auto`. It is re-read here rather than imported
    because skills install independently — brand-illustrate may sit on a machine
    without `setup`, and a hard import would break generation outright. Keep this
    order identical to setup's table.

    Reading only the environment (as this did) made the documented setting a
    no-op: `config --set image_backend=nano-banana` wrote a file nobody read,
    and the run silently went to whichever backend `auto` preferred.
    """
    def _get(path):
        try:
            data = json.loads(pathlib.Path(path).expanduser().read_text())
        except (OSError, ValueError):
            return None
        return data.get("image_backend") if isinstance(data, dict) else None

    for candidate in (pathlib.Path(project_dir or ".") / "humane.json",
                      pathlib.Path("~/.humane/config.json")):
        value = _get(candidate)
        if value:
            return str(value).strip(), str(candidate)
    raw = os.environ.get("HUMANE_IMAGE_BACKEND", "").strip()
    return (raw, "$HUMANE_IMAGE_BACKEND") if raw else (None, None)


def _env_override(project_dir=None):
    """The configured backend as (name, path). Accepts 'auto', 'name', or
    'name:/path/to/script'. 'auto' means "no explicit choice" — it resolves to
    (None, None) so the recipe's own preference still applies."""
    raw, _source = _config_value(project_dir)
    if not raw or raw == "auto":
        return None, None
    name, _, path = raw.partition(":")
    return name.strip() or None, (path.strip() or None)


def _skill_roots():
    roots = []
    for entry in os.environ.get("HUMANE_SKILLS_DIR", "").split(os.pathsep):
        if entry.strip():
            roots.append(pathlib.Path(entry.strip()))
    roots.extend(_SKILL_ROOTS)
    return [r.expanduser() for r in roots]

# Which backends carry a real seed flag (for series coherence). nano-banana has
# none, so we anchor its series on the first output as a reference image.
_SEED_BACKENDS = {"gpt-image-2"}


# ---------------------------------------------------------------------------
# Token file -> brand summary (minimal, self-contained DTCG reader)
# ---------------------------------------------------------------------------
_ROLE_RULES = [
    ("background", ("background", "bg", "surface", "canvas", "base", "paper")),
    ("text", ("ink", "text", "foreground", "fg", "body", "content")),
    ("primary", ("primary", "brand", "action", "main")),
    ("accent", ("accent", "secondary", "highlight", "pop")),
    ("success", ("success", "positive", "ok", "moss", "green")),
    ("warning", ("warning", "caution", "warn", "amber", "yellow")),
    ("danger", ("danger", "error", "negative", "rust", "red")),
    ("muted", ("muted", "subtle", "neutral", "gray", "grey", "slate")),
]
_ROLE_ORDER = ["primary", "accent", "text", "background", "success", "warning", "danger", "muted"]
BRAND_EXT_KEY = "community.design-tokens.brand"


def _infer_role(name):
    low = name.lower()
    if low.startswith("on-") or low.startswith("on_"):
        return None
    for role, needles in _ROLE_RULES:
        if any(n in low for n in needles):
            return role
    return None


def _color_word(hex_):
    """Rough English name for a hex. Models ground the word even when they
    misread the digits, so scaffolds carry both."""
    h = hex_.lstrip("#")
    if len(h) != 6:
        return None
    try:
        r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return None
    mx, mn = max(r, g, b), min(r, g, b)
    if mx < 40:
        return "near-black"
    if mn > 235:
        return "near-white"
    if mx - mn < 24:
        return "gray" if mx < 180 else "light gray"
    hue = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)[0] * 360
    for limit, word in ((15, "red"), (45, "orange"), (70, "yellow"), (160, "green"),
                        (200, "cyan"), (255, "blue"), (290, "violet"),
                        (330, "magenta"), (360, "red")):
        if hue <= limit:
            return word
    return None


def _walk_tokens(node, path, out):
    """Yield (flat_name, $type, raw $value) for every leaf token."""
    if not isinstance(node, dict):
        return
    if "$value" in node:
        out.append((path, node.get("$type"), node["$value"]))
        return
    inherited = node.get("$type")
    for key, child in node.items():
        if key.startswith("$"):
            continue
        if isinstance(child, dict) and "$value" in child and "$type" not in child and inherited:
            child = {**child, "$type": inherited}
        _walk_tokens(child, f"{path}.{key}" if path else key, out)


def _resolve_alias(value, by_path):
    """Resolve a whole-value {group.token} alias one hop at a time."""
    seen = set()
    while isinstance(value, str) and value.startswith("{") and value.endswith("}"):
        ref = value[1:-1]
        if ref in seen or ref not in by_path:
            break
        seen.add(ref)
        value = by_path[ref]
    return value


def _flat_role_name(path):
    parts = path.split(".")
    return parts[-1] if parts else path


def summarize_tokens(tree):
    """Distil a token tree into {palette, fonts, shape, brand}. Self-contained."""
    leaves = []
    _walk_tokens(tree, "", leaves)
    by_path = {p: v for p, _, v in leaves}

    colors, fonts, radii = [], [], []
    seen_fonts = set()
    # Prefer explicit role-alias tokens (name == role) as authoritative.
    exact, keyword = {}, {}
    for path, ttype, raw in leaves:
        value = _resolve_alias(raw, by_path)
        name = _flat_role_name(path)
        if ttype == "color" and isinstance(value, str):
            role = _infer_role(name)
            colors.append({"name": name, "hex": value, "role": role})
            if role:
                if name.lower() == role:
                    exact.setdefault(role, value)
                else:
                    keyword.setdefault(role, value)
        elif ttype == "fontFamily":
            fams = value if isinstance(value, list) else [value]
            for fam in fams:
                if isinstance(fam, str) and fam not in seen_fonts:
                    seen_fonts.add(fam); fonts.append(fam)
        elif ttype == "typography" and isinstance(value, dict):
            fam = value.get("fontFamily")
            if isinstance(fam, list):
                fam = fam[0] if fam else None
            if isinstance(fam, str) and fam not in seen_fonts:
                seen_fonts.add(fam); fonts.append(fam)
        elif ttype == "dimension":
            group = path.split(".")[0].lower()
            if group in ("radius", "rounded", "corner", "corners"):
                if isinstance(value, dict) and "value" in value:
                    radii.append(float(value["value"]))

    roles = {**keyword, **exact}  # exact wins
    brand = {}
    ext = tree.get("$extensions")
    if isinstance(ext, dict) and isinstance(ext.get(BRAND_EXT_KEY), dict):
        brand = ext[BRAND_EXT_KEY]

    return {
        "palette": colors,
        "roles": roles,
        "fonts": fonts,
        "shape": _shape_language(radii),
        "brand": brand,
    }


def _shape_language(radii):
    if not radii:
        return None
    m = max(radii)
    if m == 0:
        return "sharp"
    if m <= 6:
        return "soft"
    if m <= 16:
        return "rounded"
    return "pill"


# ---------------------------------------------------------------------------
# Prompt scaffold
# ---------------------------------------------------------------------------
# Words carrying no meaning for negative-clause comparison.
_NEG_FILLER = {
    "a", "an", "the", "of", "or", "and", "with", "used", "as", "in", "on",
    "that", "into", "for", "its", "at", "to", "by",
}


def _split_negatives(entry):
    """Split a compound negative into atomic clauses.

    Sources phrase negatives at wildly different granularity — the de-slop list
    packs four bans into one string ("no lens flare, no neon glow, no bokeh, no
    stock-photo people") while a brand `avoid` entry is usually one idea. Without
    splitting, dedup can only compare whole strings and misses every overlap.

    Splits on `;` always, and on `,` only when the next fragment starts a new
    ban ("no ..."), so commas *inside* a clause ("a lone acid-green or vermilion
    pop") survive intact.
    """
    parts = [p for chunk in str(entry).split(";") for p in re.split(r",\s*(?=no\b)", chunk)]
    return [p.strip().strip(".") for p in parts if p.strip().strip(".")]


def _neg_key(clause):
    """Comparison token-set for a clause: lowercased, de-prefixed, singularised."""
    text = clause.lower().strip()
    for prefix in ("no ", "nothing ", "avoid ", "never "):
        if text.startswith(prefix):
            text = text[len(prefix):]
            break
    text = re.sub(r"[^a-z0-9\s-]", " ", text).replace("-", " ")
    tokens = set()
    for tok in text.split():
        if tok in _NEG_FILLER:
            continue
        if len(tok) > 3 and tok.endswith("s") and not tok.endswith("ss"):
            tok = tok[:-1]          # naive singular: flares -> flare
        tokens.add(tok)
    return frozenset(tokens)


def merge_negatives(brand, user_negatives=None):
    """De-slop list + brand.avoid + brand.negativePrompt + user negatives,
    de-duplicated, order-stable (de-slop first, then brand, then user).

    Compound entries are split into atomic clauses first, so dedup happens at
    the granularity a ban is actually expressed at. A clause is dropped when it
    repeats an earlier one, or when it is a strictly more specific restatement
    of one ("stock-photo people smiling at laptops" after "stock-photo people")
    — the broader ban already covers it. A later clause that is *broader* than
    an earlier one is kept, since it bans strictly more.
    """
    out, seen = [], []
    def add(items):
        for entry in items:
            for clause in _split_negatives(entry):
                key = _neg_key(clause)
                if not key:
                    continue
                if any(key == kept or kept < key for kept in seen):
                    continue
                seen.append(key); out.append(clause)
    add(DESLOP_NEGATIVES)
    add(brand.get("avoid") or [])
    if brand.get("negativePrompt"):
        add([brand["negativePrompt"]])
    add(user_negatives or [])
    return out


def palette_clause(summary):
    roles = summary["roles"]
    if not roles:
        return None
    ordered = sorted(roles, key=lambda r: _ROLE_ORDER.index(r) if r in _ROLE_ORDER else 99)
    swatches = []
    for role in ordered:
        word = _color_word(roles[role])
        swatches.append(f"{role} {word} ({roles[role]})" if word else f"{role} ({roles[role]})")
    return "Palette, exactly and only: " + ", ".join(swatches) + "."


def series_block(summary, answers):
    """Shared style descriptor that every image in the set repeats verbatim,
    so five outputs read as one family."""
    brand = summary["brand"]
    bits = []
    mood = brand.get("mood")
    if mood:
        bits.append(", ".join(mood) if isinstance(mood, list) else str(mood))
    if brand.get("imageryStyle"):
        bits.append(str(brand["imageryStyle"]).rstrip("."))
    if answers.get("style"):
        bits.append(str(answers["style"]).rstrip("."))
    if summary["shape"]:
        bits.append(f"{summary['shape']}-edged geometry")
    return "Shared style across the set: " + "; ".join(bits) + "." if bits else None


def compose_prompt(summary, subject, answers, refs=None):
    """Deterministic scaffold: lead mood -> subject -> series style -> palette
    -> type -> refs -> merged negatives."""
    brand = summary["brand"]
    parts = []
    mood = brand.get("mood")
    lead = ", ".join(mood) if isinstance(mood, list) else (mood or "")
    parts.append(f"A {lead} image: {subject}." if lead else f"{subject}.")
    sb = series_block(summary, answers)
    if sb:
        parts.append(sb)
    pc = palette_clause(summary)
    if pc:
        parts.append(pc)
    if summary["fonts"]:
        parts.append(f"Any visible text set in {summary['fonts'][0]}-style type.")
    for i, entry in enumerate(refs or [], start=1):
        take = ", ".join(entry.get("take", [])) or "overall style"
        clause = f"From reference image {i} ({entry.get('file', entry.get('path', ''))}) take: {take}"
        if entry.get("note"):
            clause += f" — {entry['note']}"
        parts.append(clause + ".")
    negs = merge_negatives(brand, answers.get("negatives"))
    if negs:
        parts.append("Strictly avoid: " + "; ".join(negs) + ".")
    return " ".join(parts)


def resolve_platforms(answers):
    names = answers.get("platforms") or [answers.get("purpose") or DEFAULT_PLATFORM]
    out = []
    for n in names:
        if n in PLATFORMS:
            out.append({"name": n, **PLATFORMS[n]})
    if not out:
        out.append({"name": DEFAULT_PLATFORM, **PLATFORMS[DEFAULT_PLATFORM]})
    return out


def variant_subjects(answers):
    """The list of per-image subjects. `variants` overrides; else `count` copies
    of the single subject (the backend's own seed/re-roll varies them)."""
    variants = answers.get("variants")
    if variants:
        return list(variants)
    count = int(answers.get("count") or 1)
    return [answers["subject"]] * max(1, count)


def build_scaffold(tree, answers):
    """Everything needed to run a batch, as a plain dict (also the recipe body)."""
    summary = summarize_tokens(tree)
    subjects = variant_subjects(answers)
    platforms = resolve_platforms(answers)
    refs = load_refs(answers.get("refs_dir")) if answers.get("refs_dir") else []
    items = []
    for idx, subj in enumerate(subjects):
        items.append({
            "index": idx,
            "subject": subj,
            "prompt": compose_prompt(summary, subj, answers, refs=refs),
        })
    return {
        "answers": answers,
        "backend": answers.get("backend", "auto"),
        "budget": answers.get("budget", "draft"),
        "seed": answers.get("seed"),
        "platforms": platforms,
        "negatives": merge_negatives(summary["brand"], answers.get("negatives")),
        "series_style": series_block(summary, answers),
        "fonts": summary["fonts"],
        "roles": summary["roles"],
        "refs": refs,
        "items": items,
    }


def load_refs(refs_dir):
    if not refs_dir:
        return []
    p = pathlib.Path(refs_dir).expanduser()
    manifest = p / "refs.json"
    if not manifest.exists():
        return []
    data = json.loads(manifest.read_text())
    imgs = data.get("images", data if isinstance(data, list) else [])
    out = []
    for e in imgs:
        if e.get("take") or e.get("note"):
            out.append({**e, "path": str(p / e["file"])})
    return out


# ---------------------------------------------------------------------------
# Backend probing + command building
# ---------------------------------------------------------------------------
def _is_runnable(path):
    """A backend must be a *file* we can actually execute.

    `.exists()` is true for a directory, so `HUMANE_IMAGE_BACKEND=name:/tmp` was
    reported as found and `override_valid`, and the run then tried to execute a
    directory. A `.py` script only needs to be readable (we put `python3` in
    front of it); anything else has to carry the executable bit.
    """
    p = pathlib.Path(path).expanduser()
    if not p.is_file():
        return False
    return p.suffix == ".py" or os.access(p, os.X_OK)


def probe_backends(project_dir=None):
    """Return {backend_name: script-path-or-executable}. See the precedence
    note at _SKILL_ROOTS; discovery never assumes a single agent's layout."""
    found = {}

    # 1. explicit override
    env_name, env_path = _env_override(project_dir)
    if env_name and env_path and _is_runnable(env_path):
        found[env_name] = str(pathlib.Path(env_path).expanduser())

    roots = _skill_roots()
    for name, spec in _BACKENDS.items():
        if name in found:
            continue
        # 2-3. a skill checkout under any known root
        for root in roots:
            cand = root / name / "scripts" / spec["script"]
            if cand.is_file():
                found[name] = str(cand)
                break
        else:
            # 4. a generator installed as a plain executable
            exe = shutil.which(spec["exe"])
            if exe:
                found[name] = exe
    return found


def backend_search_report(project_dir=None):
    """What was searched and what was found — for `backends` and for setup's
    doctor. Reporting the probed locations turns 'no backend' from a dead end
    into something the user can act on."""
    env_name, env_path = _env_override(project_dir)
    configured, source = _config_value(project_dir)
    return {
        "found": probe_backends(project_dir),
        "env": {"HUMANE_IMAGE_BACKEND": os.environ.get("HUMANE_IMAGE_BACKEND") or None,
                "HUMANE_SKILLS_DIR": os.environ.get("HUMANE_SKILLS_DIR") or None},
        # Which value won and which file supplied it — "why did it pick that?"
        # must be answerable without guessing at four layers.
        "configured": configured,
        "configured_source": source,
        "override_valid": bool(env_name and env_path and _is_runnable(env_path)),
        "roots_searched": [str(r) for r in _skill_roots()],
        "backends_known": sorted(_BACKENDS),
    }


def pick_backend(requested, found, project_dir=None):
    # An explicit configured backend outranks the recipe's stored choice: it is
    # the knob a user reaches for to redirect a run. `auto` is not a choice, so
    # it leaves the recipe's own preference intact.
    env_name, _ = _env_override(project_dir)
    if env_name:
        return env_name if env_name in found else None
    if requested and requested != "auto":
        return requested if requested in found else None
    # auto: prefer gpt-image-2 (has a seed flag for coherence), else nano-banana
    for pref in ("gpt-image-2", "nano-banana"):
        if pref in found:
            return pref
    return None


NO_BACKEND_MESSAGE = (
    "No image backend found — writing the prompts instead of stopping.\n"
    "brand-illustrate is a thin adapter; the generators live outside the plugin "
    "so it never bundles an API client or your keys.\n"
    "\n"
    "Every prompt below is final and on-brand. Paste one into any image tool you "
    "already use, or install a backend and re-run to generate them here:\n"
    "  - gpt-image-2  (carries a real --seed; best for a coherent series)\n"
    "  - nano-banana  (native reference-image style transfer)\n"
    "\n"
    "Point at one you already have:  HUMANE_IMAGE_BACKEND=<name>:/path/to/script\n"
    "Add a skills directory to the search:  HUMANE_SKILLS_DIR=/path/one:/path/two\n"
    "Or install into any agent:  npx skills add <source>"
)


def prompts_only(scaffold, out_dir, tokens_path=None, reason="no-backend"):
    """The soft landing: no generator, so emit what one would have been given.

    A batch that cannot run is still worth something. The prompts are the part
    this skill actually produces — assembled from the token palette, the brand
    block, and the merged de-slop negatives — and they are identical whether or
    not an API call follows. Stopping would throw that away and leave the user
    with nothing but an install instruction.

    Writes the same batch layout as run_batch (timestamped dir, metadata.json,
    saved recipe) so the run resumes with `run --recipe` once a backend exists.
    """
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    base = _slug(scaffold["answers"].get("subject", "batch"))
    batch_dir = pathlib.Path(out_dir).expanduser() / f"{stamp}-{base}"
    batch_dir.mkdir(parents=True, exist_ok=True)

    entries, lines = [], []
    for item in scaffold["items"]:
        for plat in scaffold["platforms"]:
            entries.append({
                "file": None, "platform": plat["name"],
                "size": f"{plat['w']}x{plat['h']}", "subject": item["subject"],
                # Same per-entry schema as run_batch, so a reader does not have
                # to know which path produced the file. No backend ran, so no
                # size was requested of one — null, not True.
                "size_requested": None,
                "prompt": item["prompt"], "command": None, "returncode": None,
            })

    lines += [f"# {base} — {len(entries)} prompt(s)", "",
              "brand-illustrate found no image backend, so it wrote the prompts",
              "instead of stopping. Each one is final and on-brand: paste it into",
              "any image tool at the size given, or install a backend and re-run",
              "",
              f"    illustrate.py run --recipe {_recipe_path(tokens_path) or '<recipe>'} --out-dir <dir>",
              ""]
    for i, e in enumerate(entries, 1):
        lines += [f"## {i}. {e['subject']} — {e['platform']} ({e['size']})", "",
                  "```", e["prompt"], "```", ""]
    (batch_dir / "prompts.md").write_text("\n".join(lines), encoding="utf-8")

    metadata = {
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "backend": None, "reason": reason,
        "budget": scaffold.get("budget"), "seed": scaffold.get("seed"),
        "tokens": str(pathlib.Path(tokens_path).expanduser()) if tokens_path else None,
        "series_style": scaffold.get("series_style"),
        "negatives": scaffold.get("negatives"),
        "platforms": [p["name"] for p in scaffold["platforms"]],
        "outputs": entries,
    }
    (batch_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")

    recipe = save_recipe(scaffold, tokens_path) if tokens_path else None
    return {"ok": True, "generated": False, "error": reason, "backend": None,
            "message": NO_BACKEND_MESSAGE, "batch_dir": str(batch_dir),
            "prompts": str(batch_dir / "prompts.md"),
            "metadata": str(batch_dir / "metadata.json"),
            "recipe": recipe, "outputs": entries}


def _recipe_path(tokens_path):
    if not tokens_path:
        return None
    p = pathlib.Path(tokens_path).expanduser()
    return str(p.with_name(p.name.replace(".tokens.json", "") + ".illustrate-recipe.json"))


def _size_was_requested(backend, platform):
    """Could this backend be asked for this preset's exact pixel size?

    gpt-image-2 takes a free-form --size, so always. nano-banana takes only a
    named platform, so only when the preset maps to one — `spot-ui` does not,
    and that image returns at the backend's default size.
    """
    return backend == "gpt-image-2" or bool(platform.get("flag"))


def build_command(script, backend, prompt, out_path, platform, size, draft,
                  seed=None, refs=None, anchor=None):
    # A backend discovered on PATH is an executable; only a .py script needs
    # an interpreter in front of it.
    cmd = ["python3", script] if str(script).endswith(".py") else [str(script)]
    flag, (w, h) = platform.get("flag"), (platform["w"], platform["h"])
    if backend == "gpt-image-2":
        if flag:
            cmd += ["--platform", flag]
        else:
            cmd += ["--size", f"{w}x{h}"]
        cmd += ["--draft"] if draft else ["--quality", "high"]
        cmd += ["-y"]
        if seed is not None:
            cmd += ["--seed", str(seed)]
    else:  # nano-banana
        # nano-banana takes a named platform but no free-form --size, so a
        # preset without an exact platform match cannot have its size requested
        # at all — the image comes back at the backend's own default. Nothing
        # here resizes it (that would need an image library, and these scripts
        # are stdlib only), so the size is recorded as not-requested rather than
        # quietly reported as if it had been honoured. See size_requested.
        if flag:
            cmd += ["--platform", flag]
        cmd += ["--model", "flash" if draft else "pro"]
    for entry in refs or []:
        cmd += ["--reference", entry["path"]]
    if anchor:  # series anchor for seedless backends
        cmd += ["--reference", anchor]
    cmd += [prompt, str(out_path)]
    return cmd


def _slug(text):
    out = "".join(c.lower() if c.isalnum() else "-" for c in (text or "brand"))
    while "--" in out:
        out = out.replace("--", "-")
    return out.strip("-")[:40] or "brand"


# ---------------------------------------------------------------------------
# Batch run
# ---------------------------------------------------------------------------
def run_batch(scaffold, tokens_path, out_dir, dry_run=False, runner=subprocess.run,
              found=None, project_dir=None):
    found = probe_backends(project_dir) if found is None else found
    backend = pick_backend(scaffold.get("backend"), found, project_dir)
    if not backend:
        # No generator available. Emit the prompts rather than throwing the
        # batch away — see prompts_only.
        return prompts_only(scaffold, out_dir, tokens_path)
    script = found[backend]
    draft = scaffold.get("budget", "draft") != "final"
    seed = scaffold.get("seed")
    if seed is None and backend in _SEED_BACKENDS and scaffold.get("items"):
        seed = 20260730  # deterministic default so a re-run reproduces the set

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    base = _slug(scaffold["answers"].get("subject", "batch"))
    batch_dir = pathlib.Path(out_dir).expanduser() / f"{stamp}-{base}"
    batch_dir.mkdir(parents=True, exist_ok=True)

    outputs, anchor = [], None
    for item in scaffold["items"]:
        for plat in scaffold["platforms"]:
            fname = f"{base}-{item['index']:02d}-{plat['name']}.png"
            out_path = batch_dir / fname
            cmd = build_command(
                script, backend, item["prompt"], out_path, plat,
                (plat["w"], plat["h"]), draft, seed=seed,
                refs=scaffold.get("refs"),
                anchor=anchor if backend not in _SEED_BACKENDS else None,
            )
            rc = 0
            if not dry_run:
                proc = runner(cmd)
                rc = getattr(proc, "returncode", 0)
                if rc == 0 and anchor is None and backend not in _SEED_BACKENDS:
                    anchor = str(out_path)  # anchor the rest of the series
            outputs.append({
                "file": str(out_path), "platform": plat["name"],
                "size": f"{plat['w']}x{plat['h']}", "subject": item["subject"],
                # Whether that size was actually asked of the backend. gpt-image-2
                # always takes one; nano-banana only via a named platform. Calling
                # the target size the delivered size when it was never requested
                # is the kind of quiet lie that shows up as a squashed OG image.
                "size_requested": _size_was_requested(backend, plat),
                "prompt": item["prompt"], "command": cmd, "returncode": rc,
            })

    metadata = {
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "backend": backend, "budget": scaffold.get("budget"), "seed": seed,
        "tokens": str(pathlib.Path(tokens_path).expanduser()) if tokens_path else None,
        "series_style": scaffold.get("series_style"),
        "negatives": scaffold.get("negatives"),
        "platforms": [p["name"] for p in scaffold["platforms"]],
        "outputs": outputs,
    }
    (batch_dir / "metadata.json").write_text(json.dumps(metadata, indent=2))

    recipe = save_recipe(scaffold, tokens_path)
    sheet = write_contact_sheet(batch_dir, outputs)
    # A non-zero return code from the generator means that image does not
    # exist. Reporting ok:true over a batch of failures is a false success —
    # the caller writes a contact sheet full of missing files and believes it.
    failed = [o for o in outputs if o.get("returncode")]
    # Images whose target size could not be asked for. Not a failure — the image
    # exists and is on-brand — but the caller must not paste it into a slot that
    # needs exact pixels without checking it first.
    unsized = sorted({o["platform"] for o in outputs if not o["size_requested"]})
    return {"ok": not failed, "generated": True, "failed": len(failed),
            "backend": backend, "batch_dir": str(batch_dir),
            "unsized_platforms": unsized,
            "outputs": outputs, "metadata": str(batch_dir / "metadata.json"),
            "recipe": recipe, "contact_sheet": sheet}


def recipe_path(tokens_path):
    """Recipe sits next to the token set (answers the jtbd open question:
    sidecar JSON, so the token file stays a clean DTCG document)."""
    p = pathlib.Path(tokens_path).expanduser()
    return p.with_name(p.stem.replace(".tokens", "") + ".illustrate-recipe.json")


def save_recipe(scaffold, tokens_path):
    if not tokens_path:
        return None
    body = {
        "tokens": str(pathlib.Path(tokens_path).expanduser()),
        "saved_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "answers": scaffold["answers"],
    }
    rp = recipe_path(tokens_path)
    rp.write_text(json.dumps(body, indent=2))
    return str(rp)


def load_recipe(path):
    return json.loads(pathlib.Path(path).expanduser().read_text())


def _sheet_html(title, lead, groups):
    """Shared sheet renderer: thumbnail grid(s) + a dependency-free lightbox.
    De-slop rules hold: real headings, honest filenames, both themes, no libs."""
    sections = []
    idx = 0
    for heading, items in groups:
        cells = []
        for it in items:
            cap = it.get("caption", "")
            sub = it.get("sub", "")
            cells.append(
                f'<figure><button type="button" class="th" data-i="{idx}" '
                f'data-full="{it["src"]}" data-cap="{cap}">'
                f'<img src="{it["src"]}" alt="{cap}" loading="lazy"></button>'
                f'<figcaption>{cap}{f"<br><span>{sub}</span>" if sub else ""}</figcaption></figure>'
            )
            idx += 1
        h = f"<h2>{heading}</h2>" if heading else ""
        sections.append(f'<section>{h}<div class="grid">{"".join(cells)}</div></section>')
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><style>
:root{{--bg:#fff;--fg:#16181d;--sub:#5b6270;--line:#e5e7eb}}
@media(prefers-color-scheme:dark){{:root{{--bg:#0f1115;--fg:#e8eaed;--sub:#9aa1ad;--line:#242832}}}}
body{{margin:0;padding:2rem;background:var(--bg);color:var(--fg);
font:15px/1.5 system-ui,-apple-system,sans-serif}}
h1{{font-size:1.4rem;margin:0 0 .25rem}}
h2{{font-size:1.05rem;margin:2.2rem 0 .9rem}}
p.lead{{color:var(--sub);margin:0 0 1.6rem}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:1.5rem}}
figure{{margin:0}}
.th{{display:block;width:100%;padding:0;border:0;background:none;cursor:zoom-in}}
.th:focus-visible{{outline:2.5px solid #4a7dcc;outline-offset:2px;border-radius:4px}}
img{{width:100%;height:auto;display:block;border:1px solid var(--line);border-radius:4px;background:var(--line)}}
figcaption{{margin-top:.5rem;font-size:.8rem;word-break:break-word}}
figcaption span{{color:var(--sub)}}
dialog#lb{{border:0;padding:0;background:rgba(10,11,14,.94);max-width:100vw;max-height:100vh;
width:100vw;height:100vh;display:none;align-items:center;justify-content:center}}
dialog#lb[open]{{display:flex}}
#lb img{{max-width:92vw;max-height:86vh;width:auto;height:auto;border:0;border-radius:4px}}
#lb figure{{margin:0;text-align:center}}
#lb figcaption{{color:#cfd4dc;margin-top:.8rem;font-size:.85rem}}
#lb .nav{{position:fixed;top:50%;transform:translateY(-50%);border:0;background:rgba(255,255,255,.09);
color:#fff;font-size:1.6rem;line-height:1;padding:.7rem 1rem;border-radius:6px;cursor:pointer}}
#lb .nav:focus-visible{{outline:2.5px solid #7fa8dc}}
#lb .prev{{left:1rem}} #lb .next{{right:1rem}}
#lb .close{{position:fixed;top:1rem;right:1rem;border:0;background:rgba(255,255,255,.09);
color:#fff;font-size:1.15rem;padding:.55rem .8rem;border-radius:6px;cursor:pointer}}
@media(prefers-reduced-motion:no-preference){{#lb img{{transition:opacity .15s}}}}
</style></head><body>
<h1>{title}</h1>
<p class="lead">{lead}</p>
{"".join(sections)}
<dialog id="lb" aria-label="Full-size image viewer">
  <figure><img alt=""><figcaption></figcaption></figure>
  <button type="button" class="nav prev" aria-label="Previous image">&#8592;</button>
  <button type="button" class="nav next" aria-label="Next image">&#8594;</button>
  <button type="button" class="close" aria-label="Close viewer">Esc &#10005;</button>
</dialog>
<script>
(function(){{
  var thumbs=[].slice.call(document.querySelectorAll(".th")),
      lb=document.getElementById("lb"), img=lb.querySelector("img"),
      cap=lb.querySelector("figcaption"), cur=0;
  function show(i){{
    cur=(i+thumbs.length)%thumbs.length;
    var t=thumbs[cur];
    img.src=t.dataset.full; img.alt=t.dataset.cap||"";
    cap.textContent=(t.dataset.cap||"")+"  ("+(cur+1)+"/"+thumbs.length+")";
  }}
  thumbs.forEach(function(t){{t.addEventListener("click",function(){{
    show(+t.dataset.i); if(!lb.open)lb.showModal();}});}});
  lb.querySelector(".prev").addEventListener("click",function(){{show(cur-1)}});
  lb.querySelector(".next").addEventListener("click",function(){{show(cur+1)}});
  lb.querySelector(".close").addEventListener("click",function(){{lb.close()}});
  lb.addEventListener("click",function(e){{if(e.target===lb)lb.close()}});
  lb.addEventListener("keydown",function(e){{
    if(e.key==="ArrowLeft"){{e.preventDefault();show(cur-1)}}
    if(e.key==="ArrowRight"){{e.preventDefault();show(cur+1)}}
  }});
  lb.addEventListener("close",function(){{
    var t=thumbs[cur]; if(t)t.focus();
  }});
}})();
</script>
</body></html>"""


def write_contact_sheet(batch_dir, outputs):
    """Per-batch sheet: thumbnail grid with a full-size lightbox."""
    items = [{"src": pathlib.Path(o["file"]).name,
              "caption": o.get("subject", pathlib.Path(o["file"]).name),
              "sub": f'{o.get("platform", "")} &middot; {o.get("size", "")}'.strip(" &middot;")}
             for o in outputs]
    html = _sheet_html("Illustration batch",
                       f"{len(outputs)} images. Click any thumbnail for full size; "
                       "&#8592;/&#8594; to move, Esc to close.",
                       [("", items)])
    sheet = batch_dir / "contact-sheet.html"
    sheet.write_text(html)
    return str(sheet)


def write_gallery(root, out_path=None):
    """Cross-batch gallery: every version ever generated under `root`, grouped by
    batch (metadata.json aware), loose images picked up as an ungrouped section."""
    root = pathlib.Path(root).expanduser()
    exts = {".png", ".jpg", ".jpeg", ".webp"}
    groups, seen = [], set()
    for meta_path in sorted(root.rglob("metadata.json")):
        try:
            meta = json.loads(meta_path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        bdir = meta_path.parent
        items = []
        for o in meta.get("outputs", []):
            f = bdir / pathlib.Path(o["file"]).name
            if not f.exists():
                continue
            seen.add(f.resolve())
            items.append({"src": str(f.relative_to(root)).replace("\\", "/"),
                          "caption": o.get("subject", f.name),
                          "sub": f'{o.get("platform", "")} &middot; {o.get("size", "")}'.strip(" &middot;")})
        if items:
            label = meta.get("subject") or bdir.name
            groups.append((f'{bdir.name} &middot; {meta.get("backend", "")}'.rstrip(" &middot;"), items))
    loose = [{"src": str(f.relative_to(root)).replace("\\", "/"), "caption": f.name, "sub": ""}
             for f in sorted(root.rglob("*")) if f.suffix.lower() in exts
             and f.resolve() not in seen and "contact-sheet" not in f.name]
    if loose:
        groups.append(("Other images", loose))
    total = sum(len(i) for _, i in groups)
    html = _sheet_html("All versions", f"{total} images across {len(groups)} group(s). "
                       "Click any thumbnail for full size; &#8592;/&#8594; to move, Esc to close.",
                       groups)
    out = pathlib.Path(out_path).expanduser() if out_path else root / "gallery.html"
    out.write_text(html)
    return str(out)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _load_json(path):
    return json.loads(pathlib.Path(path).expanduser().read_text())


def main(argv=None):
    ap = argparse.ArgumentParser(description="brand-illustrate adapter")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("platforms")
    sb = sub.add_parser("backends")
    sb.add_argument("-v", "--verbose", action="store_true",
                    help="also print every location searched")
    ga = sub.add_parser("gallery")
    ga.add_argument("--dir", required=True, help="root directory containing batches / images")
    ga.add_argument("-o", "--out", default=None, help="output html (default <dir>/gallery.html)")

    sc = sub.add_parser("scaffold")
    sc.add_argument("--tokens", required=True)
    sc.add_argument("--answers", required=True)

    rn = sub.add_parser("run")
    rn.add_argument("--tokens")
    rn.add_argument("--answers")
    rn.add_argument("--recipe")
    rn.add_argument("--out-dir", default=".")
    rn.add_argument("--dry-run", action="store_true")

    args = ap.parse_args(argv)

    if args.cmd == "platforms":
        for name, p in PLATFORMS.items():
            print(f"{name:16} {p['w']}x{p['h']:<5} {p['desc']}")
        return 0

    if args.cmd == "gallery":
        print(write_gallery(args.dir, args.out))
        return 0
    if args.cmd == "backends":
        report = backend_search_report()
        found = report["found"]
        for name in report["backends_known"]:
            path = found.get(name)
            print(f"  {'OK  ' if path else 'none'}  {name:14} {path or '-'}")
        env = report["env"]
        if report["configured"]:
            # Which layer won. "Why did it pick that one?" should never require
            # the user to guess across four of them.
            print(f"\nimage_backend={report['configured']}  "
                  f"(from {report['configured_source']})")
        if env["HUMANE_IMAGE_BACKEND"]:
            state = ("valid" if report["override_valid"]
                     else "set, but the path is not a runnable script")
            print(f"HUMANE_IMAGE_BACKEND={env['HUMANE_IMAGE_BACKEND']}  ({state})")
        if env["HUMANE_SKILLS_DIR"]:
            print(f"HUMANE_SKILLS_DIR={env['HUMANE_SKILLS_DIR']}")
        if args.verbose:
            print("\nsearched:")
            for r in report["roots_searched"]:
                print(f"  {r}/<backend>/scripts/")
            print("  then any <backend> executable on PATH")
        if not found:
            print()
            print(NO_BACKEND_MESSAGE)
            # Not an error: a run without a backend still writes its prompts.
        return 0

    if args.cmd == "scaffold":
        tree = _load_json(args.tokens)
        answers = _load_json(args.answers)
        print(json.dumps(build_scaffold(tree, answers), indent=2))
        return 0

    if args.cmd == "run":
        if args.recipe:
            rec = load_recipe(args.recipe)
            tokens_path = rec["tokens"]
            answers = rec["answers"]
        else:
            if not (args.tokens and args.answers):
                ap.error("run needs --recipe OR both --tokens and --answers")
            tokens_path = args.tokens
            answers = _load_json(args.answers)
        tree = _load_json(tokens_path)
        scaffold = build_scaffold(tree, answers)
        result = run_batch(scaffold, tokens_path, args.out_dir, dry_run=args.dry_run)
        print(json.dumps({k: v for k, v in result.items()
                          if k in ("backend", "batch_dir", "metadata", "recipe",
                                   "contact_sheet", "prompts", "generated",
                                   "failed")}, indent=2))
        if not result.get("generated", True):
            # Soft landing: no backend, prompts written. Not a failure.
            print(result["message"], file=sys.stderr)
            return 0
        if not result["ok"]:
            failed = [o for o in result.get("outputs", []) if o.get("returncode")]
            print(f"{len(failed)} image(s) failed to generate:", file=sys.stderr)
            for o in failed:
                print(f"  rc={o['returncode']}  {o['file']}", file=sys.stderr)
            return 1
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
