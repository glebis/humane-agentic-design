#!/usr/bin/env python3
"""brandkit adapter + handoff: identity exploration -> (optional) board render,
then the confirm-then-write handoff into design-tokens' brand contract.

brandkit is the UPSTREAM identity-exploration skill: it produces direction
candidates (boards, logo systems, mood). When a direction wins, its art-direction
decisions — imageryStyle (prose), mood (adjectives), avoid (negatives) — are
written into the token set's `$extensions["community.design-tokens.brand"]` block,
which every downstream generator (design-tokens' DESIGN.md, brand-illustrate) then
honors. This script owns the deterministic, testable parts of that flow:

  - a thin backend adapter (probe for gpt-image-2 / nano-banana, degrade
    gracefully) — generators stay OUTSIDE the plugin, same rule as brand-illustrate;
  - the handoff WRITER: merge a chosen direction into the token file's brand block
    (creating the block, preserving every other key), or, when no token set exists
    yet, save a `brand-block.draft.json` for `design-tokens setup` to import;
  - a plugin-relative call to the sibling design-tokens CLI to regenerate DESIGN.md.

Stdlib only, no absolute paths, portable. The backend-probing pattern is a small
intentional duplication of brand-illustrate's (skills are copied individually, so
a cross-skill import would break `npx skills add <one-folder>` portability).

CLI:
  brandkit.py backends                                  # probe installed generators
  brandkit.py handoff --direction D.json [--tokens T]   # write brand block or draft
      [--out-dir DIR] [--no-regen]
"""

import argparse
import json
import pathlib
import subprocess
import sys

BRAND_EXT_KEY = "community.design-tokens.brand"

# Backend scripts live outside the plugin. Probe both the personal install and a
# plugin-relative co-install; first hit wins. Mirrors brand-illustrate.
_PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[3]  # .../humane
_BACKEND_CANDIDATES = {
    "gpt-image-2": [
        pathlib.Path("~/.claude/skills/gpt-image-2/scripts/gpt_image_2.py").expanduser(),
        _PLUGIN_ROOT / "skills" / "gpt-image-2" / "scripts" / "gpt_image_2.py",
    ],
    "nano-banana": [
        pathlib.Path("~/.claude/skills/nano-banana/scripts/nano_banana.py").expanduser(),
        _PLUGIN_ROOT / "skills" / "nano-banana" / "scripts" / "nano_banana.py",
    ],
}

NO_BACKEND_MESSAGE = (
    "No image backend found. brandkit renders boards through an external generator; "
    "none is bundled. Install ONE, then re-run:\n"
    "  - gpt-image-2 (readable in-image text, good for board labels)\n"
    "  - nano-banana (reference-image style transfer)\n"
    "Install channels:\n"
    "  Claude Code: place the skill under ~/.claude/skills/<name>/\n"
    "  Any agent:   npx skills add <source>\n"
    "You can still run the identity questionnaire and the handoff (brand-block write) "
    "without a backend — only the board render needs one."
)


def probe_backends():
    found = {}
    for name, cands in _BACKEND_CANDIDATES.items():
        for c in cands:
            if pathlib.Path(c).exists():
                found[name] = str(c)
                break
    return found


def pick_backend(requested, found):
    if requested and requested != "auto":
        return requested if requested in found else None
    for pref in ("gpt-image-2", "nano-banana"):
        if pref in found:
            return pref
    return None


def build_board_command(backend, script, prompt, out_path, draft=True):
    """Thin board-render invocation. Boards are wide identity decks, so default to
    a landscape platform where the backend supports it."""
    cmd = ["python3", script]
    if backend == "gpt-image-2":
        cmd += ["--size", "1536x1024"]  # ~3:2 landscape board
        cmd += ["--draft"] if draft else ["--quality", "high"]
        cmd += ["-y"]
    else:  # nano-banana
        cmd += ["--platform", "x"]  # 1600x900 landscape
        cmd += ["--model", "flash" if draft else "pro"]
    cmd += [prompt, str(out_path)]
    return cmd


# ---------------------------------------------------------------------------
# Confirm-then-write handoff
# ---------------------------------------------------------------------------
_DIRECTION_KEYS = ("imageryStyle", "mood", "avoid", "voice", "subjects")


def normalize_direction(direction):
    """Keep only the brand-contract keys a chosen direction contributes.
    imageryStyle is prose (str); mood/avoid/subjects are lists; voice is prose."""
    out = {}
    for k in _DIRECTION_KEYS:
        if k in direction and direction[k] not in (None, "", [], {}):
            out[k] = direction[k]
    return out


def merge_brand_block(tree, direction):
    """Return a new tree with `direction` merged into the brand block, preserving
    every other key (existing brand keys, other $extensions, all tokens). Existing
    brand keys are OVERWRITTEN by the chosen direction (the whole point of a
    confirmed handoff), but untouched keys survive."""
    tree = json.loads(json.dumps(tree))  # deep copy, don't mutate caller's dict
    ext = tree.setdefault("$extensions", {})
    if not isinstance(ext, dict):
        raise ValueError("$extensions exists but is not an object; refusing to overwrite")
    block = ext.setdefault(BRAND_EXT_KEY, {})
    if not isinstance(block, dict):
        raise ValueError(f"$extensions['{BRAND_EXT_KEY}'] is not an object")
    block.update(normalize_direction(direction))
    return tree


def write_brand_block(token_path, direction, out_dir=None):
    """Write the chosen direction into the token set's brand block, or save a draft.

    Returns {"action", "path", "block"}:
      - token file exists -> merge + rewrite it, action 'updated'|'created-block'
      - no token file      -> write <out_dir>/brand-block.draft.json, action 'draft'
    """
    norm = normalize_direction(direction)
    if token_path and pathlib.Path(token_path).expanduser().exists():
        p = pathlib.Path(token_path).expanduser()
        tree = json.loads(p.read_text(encoding="utf-8"))
        had_block = isinstance(tree.get("$extensions"), dict) and \
            isinstance(tree["$extensions"].get(BRAND_EXT_KEY), dict) and \
            bool(tree["$extensions"][BRAND_EXT_KEY])
        merged = merge_brand_block(tree, direction)
        p.write_text(json.dumps(merged, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return {"action": "updated" if had_block else "created-block",
                "path": str(p), "block": merged["$extensions"][BRAND_EXT_KEY]}
    # No token set yet: leave a draft for design-tokens setup to import.
    dest_dir = pathlib.Path(out_dir).expanduser() if out_dir else pathlib.Path.cwd()
    dest_dir.mkdir(parents=True, exist_ok=True)
    draft = dest_dir / "brand-block.draft.json"
    body = {
        "$description": ("brandkit draft brand block — run `humane:design-tokens` "
                         "setup in this directory to seed a token set's "
                         f"$extensions['{BRAND_EXT_KEY}'] from it."),
        "$extensions": {BRAND_EXT_KEY: norm},
    }
    draft.write_text(json.dumps(body, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"action": "draft", "path": str(draft), "block": norm}


# ---------------------------------------------------------------------------
# Sibling design-tokens CLI (plugin-relative) for DESIGN.md regeneration
# ---------------------------------------------------------------------------
def _dtokens_cli():
    """Locate the sibling design-tokens CLI. Plugin-relative first (portable),
    then the personal install. Returns a path string or None."""
    candidates = [
        _PLUGIN_ROOT / "skills" / "design-tokens" / "scripts" / "tokens",
        pathlib.Path("~/.claude/skills/design-tokens/scripts/tokens").expanduser(),
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    return None


def design_md_command(token_path, cli=None):
    cli = cli or _dtokens_cli()
    if not cli:
        return None
    return [cli, "design-md", str(token_path), "-o",
            str(pathlib.Path(token_path).expanduser().parent / "DESIGN.md")]


def regenerate_design_md(token_path, runner=subprocess.run, cli=None):
    """Regenerate the sibling DESIGN.md via the design-tokens CLI. Returns
    (command, returncode) or (None, None) when the CLI isn't installed."""
    cmd = design_md_command(token_path, cli=cli)
    if not cmd:
        return None, None
    proc = runner(cmd)
    return cmd, getattr(proc, "returncode", 0)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _load_json(path):
    return json.loads(pathlib.Path(path).expanduser().read_text(encoding="utf-8"))


def main(argv=None):
    ap = argparse.ArgumentParser(description="brandkit adapter + handoff")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("backends")

    ho = sub.add_parser("handoff")
    ho.add_argument("--direction", required=True,
                    help="JSON file with the chosen direction (imageryStyle, mood, avoid, ...)")
    ho.add_argument("--tokens", help="token set to write the brand block into")
    ho.add_argument("--out-dir", help="where to save brand-block.draft.json when no --tokens")
    ho.add_argument("--no-regen", action="store_true",
                    help="skip DESIGN.md regeneration after writing")

    args = ap.parse_args(argv)

    if args.cmd == "backends":
        found = probe_backends()
        if not found:
            print(NO_BACKEND_MESSAGE)
            return 1
        for name, path in found.items():
            print(f"{name:14} {path}")
        return 0

    if args.cmd == "handoff":
        direction = _load_json(args.direction)
        result = write_brand_block(direction=direction, token_path=args.tokens,
                                   out_dir=args.out_dir)
        print(json.dumps({k: result[k] for k in ("action", "path")}, indent=2))
        if result["action"] in ("updated", "created-block") and not args.no_regen:
            cmd, rc = regenerate_design_md(result["path"])
            if cmd is None:
                print("note: design-tokens CLI not found; skipped DESIGN.md regeneration "
                      "(install humane:design-tokens or run `tokens design-md` yourself).",
                      file=sys.stderr)
            else:
                print(f"{'regenerated' if rc == 0 else 'FAILED regen of'} DESIGN.md "
                      f"next to {result['path']}", file=sys.stderr)
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
