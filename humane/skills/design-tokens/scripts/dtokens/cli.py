"""Command-line dispatch for the design-tokens v1 core."""

import argparse
import json
import pathlib
import sys

from . import TokenError
from . import annotate as annotate_mod
from . import brand_summary as brand_summary_mod
from . import contrast as contrast_mod
from . import generate as generate_mod
from . import export_css as export_css_mod
from . import export_design_md as design_md_mod
from . import export_preview_html as preview_mod
from . import export_prompt as prompt_mod
from . import import_css as import_css_mod
from . import merge as merge_mod
from . import model
from . import resolve as resolve_mod
from . import serve as serve_mod
from . import validate as validate_mod

_TEMPLATE = pathlib.Path(__file__).resolve().parents[2] / "templates" / "base.tokens.json"


def _emit(text, out):
    if out:
        pathlib.Path(out).write_text(text, encoding="utf-8")
    else:
        print(text, end="" if text.endswith("\n") else "\n")


def _maybe_serve(args, directory, open_path):
    """Serve previews over HTTP by default when interactive (avoids file:// origin
    breakage). `--serve`/`--no-serve` force it; non-TTY (scripts/CI) defaults off."""
    want = getattr(args, "serve", None)
    if want is None:
        want = sys.stdout.isatty()
    if want:
        serve_mod.serve(directory, open_path, port=getattr(args, "port", None),
                        open_browser=not getattr(args, "no_open", False))


def _add_serve_flags(parser):
    parser.add_argument("--serve", dest="serve", action="store_true", default=None,
                        help="serve the output over HTTP and open it (default: on when interactive)")
    parser.add_argument("--no-serve", dest="serve", action="store_false",
                        help="just write files; do not serve")
    parser.add_argument("--port", type=int, help="port for --serve (default: first free from 8787)")
    parser.add_argument("--no-open", action="store_true", help="serve but do not open a browser")


def _print_warnings(tree):
    """Emit non-fatal advisories (e.g. a silent art-direction contract) to stderr.
    Never affects exit status."""
    for w in validate_mod.warnings(tree):
        print(f"warning: {w}", file=sys.stderr)


def _cmd_validate(args):
    tree = model.load(args.file)
    strict = getattr(args, "strict", False)
    errors = validate_mod.validate(tree, strict=strict)
    # In strict mode the non-DTCG dimension issues are already promoted into
    # `errors`; only the brand-contract advisories remain warnings. Otherwise
    # print the full advisory set (brand + dimension) to stderr.
    if strict:
        for w in validate_mod.brand_warnings(tree):
            print(f"warning: {w}", file=sys.stderr)
    else:
        _print_warnings(tree)
    if errors:
        for e in errors:
            print(e)
        return 1
    print("OK")
    return 0


def _cmd_contrast(args):
    tree = model.load(args.file)
    resolved = resolve_mod.resolve(tree)
    report = contrast_mod.check(resolved, standard=args.standard, level=args.level,
                                spec=contrast_mod.extract_spec(tree))
    if args.json:
        _emit(json.dumps(report, indent=2, ensure_ascii=False) + "\n", args.out)
    else:
        _emit(contrast_mod.format_report(report, args.standard), args.out)
    failing = [r for r in report["results"] if not r["passed"]]
    # A declared pair whose name does not resolve was never measured. Exiting 0
    # there would let a typo in the declaration read as a clean gate — the same
    # false success as passing an unmeasured pair.
    gating = failing or report.get("undeclared")
    return 1 if gating and not args.no_fail else 0


def _cmd_merge(args):
    merged = merge_mod.merge(model.load(args.base), model.load(args.override))
    _emit(json.dumps(merged, indent=2, ensure_ascii=False) + "\n", args.out)
    return 0


def _cmd_resolve(args):
    resolved = resolve_mod.resolve(model.load(args.file))
    _emit(json.dumps(resolved, indent=2, ensure_ascii=False) + "\n", args.out)
    return 0


def _cmd_export_css(args):
    resolved = resolve_mod.resolve(model.load(args.file))
    _emit(export_css_mod.export_css(resolved, args.selector), args.out)
    return 0


def _cmd_setup_edit(args):
    dest = pathlib.Path(args.dest)
    if dest.exists():
        print(f"refusing to overwrite existing file: {dest}")
        return 1
    if args.source:
        # Generate from a previous set: a deterministic, validated clone of an
        # existing token file's structure + content to edit. Insertion order is
        # preserved and serialization is fixed, so a given source always yields
        # byte-identical output.
        src = pathlib.Path(args.source)
        if not src.exists():
            print(f"--from source not found: {src}")
            return 1
        src_errors = validate_mod.validate(model.load(str(src)))
        if src_errors:
            print(f"--from source is not a valid token set: {src}")
            for e in src_errors:
                print(e)
            return 1
        content = json.dumps(
            json.loads(src.read_text(encoding="utf-8")), indent=2, ensure_ascii=False
        ) + "\n"
    else:
        content = _TEMPLATE.read_text(encoding="utf-8")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")
    dest_tree = model.load(str(dest))
    # Seed the brand block from a brandkit handoff draft, if one sits alongside
    # (brandkit writes brand-block.draft.json when no token set existed yet).
    if _import_brand_draft(dest, dest_tree):
        dest.write_text(json.dumps(dest_tree, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")
    errors = validate_mod.validate(dest_tree)
    if errors:
        for e in errors:
            print(e)
        return 1
    _print_warnings(dest_tree)
    print(f"scaffolded {dest}" + (f" from {args.source}" if args.source else ""))
    design_path, action = _write_design_md_sibling(dest, dest_tree)
    if action != "skipped":
        print(f"{action} {design_path}")
    return 0


_BRAND_EXT_KEY = "community.design-tokens.brand"


def _import_brand_draft(dest, tree):
    """If a `brand-block.draft.json` sits next to the scaffolded token file (a
    brandkit handoff for a set that didn't exist yet), merge its brand block into
    the tree's $extensions in place. Returns True if anything was imported."""
    draft = pathlib.Path(dest).parent / "brand-block.draft.json"
    if not draft.exists():
        return False
    try:
        block = json.loads(draft.read_text(encoding="utf-8")) \
            .get("$extensions", {}).get(_BRAND_EXT_KEY)
    except (ValueError, OSError):
        return False
    if not isinstance(block, dict) or not block:
        return False
    ext = tree.setdefault("$extensions", {})
    if not isinstance(ext, dict):
        return False
    existing = ext.get(_BRAND_EXT_KEY)
    ext[_BRAND_EXT_KEY] = {**existing, **block} if isinstance(existing, dict) else block
    print(f"imported brand block from {draft.name}", file=sys.stderr)
    return True


def _write_design_md_sibling(token_path, tree):
    """Compile DESIGN.md next to the token file (its canonical home per the
    storage convention) with provenance. Stale-overwrite guard: an existing
    DESIGN.md without our generator marker is hand-written/foreign — warn and
    leave it, rather than clobber. Returns (path, 'wrote'|'regenerated'|'skipped')."""
    token_path = pathlib.Path(token_path)
    dest = token_path.parent / "DESIGN.md"
    source = token_path.name
    command = f"tokens design-md {source}"
    content = design_md_mod.to_design_md(
        resolve_mod.resolve(tree),
        token_path.stem.replace(".tokens", "") or token_path.stem,
        brand=brand_summary_mod.extract_brand(tree),
        source=source, command=command,
    )
    if dest.exists():
        existing = dest.read_text(encoding="utf-8")
        if design_md_mod.GENERATED_MARKER not in existing:
            print(f"warning: {dest} exists but carries no {design_md_mod.GENERATOR} "
                  f"generator marker — it looks hand-edited or foreign, leaving it "
                  f"untouched. Regenerate explicitly with: {command} -o {dest}",
                  file=sys.stderr)
            return dest, "skipped"
        dest.write_text(content, encoding="utf-8")
        return dest, "regenerated"
    dest.write_text(content, encoding="utf-8")
    return dest, "wrote"


_RICH_WARNING = (
    "--rich appends skill-convention sections (components, do's/don'ts, "
    "surfaces, imagery, Quick Start CSS) to the body. The result is no longer "
    "a plain Google-Labs DESIGN.md alpha document (frontmatter stays standard)."
)


def _confirm_rich(yes=False):
    """Confirm the non-standard rich format. Returns True to proceed.

    Interactive (TTY): ask. Non-interactive: proceed (the explicit --rich flag
    is the consent), but always print the warning to stderr.
    """
    print(f"note: {_RICH_WARNING}", file=sys.stderr)
    if yes or not sys.stdin.isatty():
        return True
    answer = input("Emit the extended (non-standard) format? [y/N] ").strip().lower()
    return answer in ("y", "yes")


def _cmd_design_md(args):
    tree = model.load(args.file)
    resolved = resolve_mod.resolve(tree)
    name = args.name or pathlib.Path(args.file).stem
    rich = args.rich
    if rich and not _confirm_rich(args.yes):
        print("aborted: emitting standard DESIGN.md instead", file=sys.stderr)
        rich = False
    # Always pass the brand block so the default Brand direction section renders;
    # rich only gates the extended skill-convention sections.
    brand = brand_summary_mod.extract_brand(tree)
    source = pathlib.Path(args.file).name
    _emit(design_md_mod.to_design_md(resolved, name, args.description,
                                     brand=brand, rich=rich,
                                     source=source, command=f"tokens design-md {source}"),
          args.out)
    return 0


def _cmd_import(args):
    css = pathlib.Path(args.file).read_text(encoding="utf-8")
    tree, skipped = import_css_mod.to_tokens(css)
    errors = validate_mod.validate(tree)
    if errors:
        for e in errors:
            print(e)
        return 1
    out_json = json.dumps(tree, indent=2, ensure_ascii=False) + "\n"
    _emit(out_json, args.out)
    print(f"imported {len(tree)} tokens; skipped {len(skipped)}", file=sys.stderr)
    for name, value, reason in skipped:
        print(f"  skipped --{name}: {reason} ({value})", file=sys.stderr)
    return 0


def _cmd_preview(args):
    resolved = resolve_mod.resolve(model.load(args.file))
    name = args.name or pathlib.Path(args.file).stem
    if args.full:
        html = preview_mod.to_full_preview_html(resolved, name, args.description)
    else:
        html = preview_mod.to_preview_html(resolved, name)
    # Default to a served file when interactive: write next to the source if no
    # -o was given, so the preview opens over http (not file://).
    out = args.out
    if out is None and (getattr(args, "serve", None) or
                        (args.serve is None and sys.stdout.isatty())):
        out = str(pathlib.Path(args.file).with_suffix("").as_posix() + ".preview.html")
    if out:
        pathlib.Path(out).write_text(html, encoding="utf-8")
        print(f"wrote {out}")
        _maybe_serve(args, pathlib.Path(out).resolve().parent, pathlib.Path(out))
    else:
        _emit(html, None)
    return 0


def _cmd_prompt(args):
    tree = model.load(args.file)
    resolved = resolve_mod.resolve(tree)
    brand = brand_summary_mod.extract_brand(tree)
    name = args.name or pathlib.Path(args.file).stem
    targets = ["gpt-image-2", "nano-banana", "tufte"] if args.target == "all" else [args.target]
    chunks = []
    for target in targets:
        if target == "tufte":
            chunks.append(prompt_mod.to_tufte_theme(resolved, name))
        else:
            chunks.append(prompt_mod.to_image_prompts(
                resolved, name, target, presets=args.preset,
                platform=args.platform, subject=args.subject, brand=brand,
            ))
    _emit("\n".join(chunks), args.out)
    return 0


def _cmd_generate(args):
    tree = model.load(args.file)
    resolved = resolve_mod.resolve(tree)
    name = args.name or pathlib.Path(args.file).stem
    targets = ["gpt-image-2", "nano-banana"] if args.target == "all" else [args.target]
    results = generate_mod.generate(
        tree, resolved, name, targets, subject=args.subject, refs_dir=args.refs,
        out_dir=args.out_dir or ".", draft=not args.final, platform=args.platform,
        dry_run=args.dry_run,
    )
    failed = [t for t, _, rc in results if rc != 0]
    for target, out, rc in results:
        print(f"{'ok' if rc == 0 else 'FAILED'}  {target}  {out}")
    return 1 if failed else 0


def _cmd_annotate(args):
    try:
        annotate_mod.annotate(args.dir, port=args.port, open_browser=not args.no_open)
    except FileNotFoundError as exc:
        print(exc)
        return 1
    return 0


def _cmd_serve(args):
    path = pathlib.Path(args.path)
    if not path.exists():
        print(f"not found: {path}")
        return 1
    if path.is_dir():
        directory, open_path = path, None
    else:
        directory, open_path = path.parent, path
    serve_mod.serve(directory, open_path, port=args.port, open_browser=not args.no_open)
    return 0


def _cmd_use(args):
    tree = model.load(args.file)
    errors = validate_mod.validate(tree)
    if errors:
        for e in errors:
            print(e)
        return 1
    _print_warnings(tree)
    resolved = resolve_mod.resolve(tree)
    name = args.name or pathlib.Path(args.file).stem
    out_dir = pathlib.Path(args.out_dir) if args.out_dir else pathlib.Path(args.file).parent / "resolved"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "tokens.css").write_text(export_css_mod.export_css(resolved), encoding="utf-8")
    rich = args.rich
    if rich and not _confirm_rich(args.yes):
        print("aborted: emitting standard DESIGN.md instead", file=sys.stderr)
        rich = False
    _use_source = pathlib.Path(args.file).name
    (out_dir / "DESIGN.md").write_text(
        design_md_mod.to_design_md(
            resolved, name, args.description,
            brand=brand_summary_mod.extract_brand(tree), rich=rich,
            source=_use_source, command=f"tokens use {_use_source}",
        ),
        encoding="utf-8",
    )
    (out_dir / "preview.html").write_text(
        preview_mod.to_preview_html(resolved, name), encoding="utf-8"
    )
    (out_dir / "preview-full.html").write_text(
        preview_mod.to_full_preview_html(resolved, name, args.description), encoding="utf-8"
    )
    # Bridge artifacts: tokens -> downstream generation (the prompt door).
    image_prompts = "\n".join(
        prompt_mod.to_image_prompts(resolved, name, t, brand=brand_summary_mod.extract_brand(tree))
        for t in ("gpt-image-2", "nano-banana")
    )
    (out_dir / "image-prompts.md").write_text(image_prompts, encoding="utf-8")
    (out_dir / "tufte-theme.css").write_text(
        prompt_mod.to_tufte_theme(resolved, name), encoding="utf-8"
    )
    print(
        f"wrote {out_dir / 'tokens.css'}, {out_dir / 'DESIGN.md'}, "
        f"{out_dir / 'preview.html'}, {out_dir / 'preview-full.html'}, "
        f"{out_dir / 'image-prompts.md'} and {out_dir / 'tufte-theme.css'}"
    )
    _maybe_serve(args, out_dir, out_dir / "preview-full.html")
    return 0


def _build_parser():
    p = argparse.ArgumentParser(prog="tokens", description="design-tokens v1 core")
    sub = p.add_subparsers(dest="command", required=True)

    sv = sub.add_parser("validate")
    sv.add_argument("file")
    sv.add_argument("--strict", action="store_true",
                    help="treat non-DTCG dimension/duration values (clamp/calc/var kept "
                         "verbatim) as errors, not warnings")
    sv.set_defaults(func=_cmd_validate)

    sc = sub.add_parser("contrast",
                        help="measure APCA/WCAG contrast for every inferred "
                             "text/background token pair")
    sc.add_argument("file")
    sc.add_argument("--standard", choices=("apca", "wcag", "both"), default="both",
                    help="which scale decides pass/fail (default: both must clear)")
    sc.add_argument("--level", choices=("auto", "body", "non-body", "graphic"),
                    default="auto",
                    help="threshold to apply; auto picks per pair from the "
                         "foreground's inferred role. `graphic` is for color "
                         "that is never text (fills, rules, chart marks) and is "
                         "never inferred — a token's name cannot tell you "
                         "whether it is painted as type (default: auto)")
    sc.add_argument("--json", action="store_true", help="emit the raw report as JSON")
    sc.add_argument("--no-fail", action="store_true",
                    help="always exit 0; report without gating")
    sc.add_argument("-o", "--out")
    sc.set_defaults(func=_cmd_contrast)

    sm = sub.add_parser("merge")
    sm.add_argument("base")
    sm.add_argument("override")
    sm.add_argument("-o", "--out")
    sm.set_defaults(func=_cmd_merge)

    sr = sub.add_parser("resolve")
    sr.add_argument("file")
    sr.add_argument("-o", "--out")
    sr.set_defaults(func=_cmd_resolve)

    se = sub.add_parser("export-css")
    se.add_argument("file")
    se.add_argument("--selector", default=":root")
    se.add_argument("-o", "--out")
    se.set_defaults(func=_cmd_export_css)

    ss = sub.add_parser("setup-edit")
    ss.add_argument("dest")
    ss.add_argument("--from", dest="source",
                    help="generate from an existing token set (deterministic validated clone)")
    ss.set_defaults(func=_cmd_setup_edit)

    sd = sub.add_parser("design-md")
    sd.add_argument("file")
    sd.add_argument("--name")
    sd.add_argument("--description")
    sd.add_argument("--rich", action="store_true",
                    help="append skill-convention sections (components, do's/don'ts, "
                         "surfaces, Quick Start CSS) from the $extensions brand block; "
                         "NON-STANDARD: extends the Labs DESIGN.md alpha body")
    sd.add_argument("--yes", action="store_true",
                    help="skip the --rich non-standard-format confirmation")
    sd.add_argument("-o", "--out")
    sd.set_defaults(func=_cmd_design_md)

    si = sub.add_parser("import")
    si.add_argument("file", help="a CSS file with :root custom properties")
    si.add_argument("-o", "--out", help="write DTCG tokens here (default: stdout)")
    si.set_defaults(func=_cmd_import)

    sp = sub.add_parser("preview")
    sp.add_argument("file")
    sp.add_argument("--name")
    sp.add_argument("--full", action="store_true",
                    help="render a full landing-page mockup (brand in situ) instead of a swatch sheet")
    sp.add_argument("--description", help="lede/about copy for --full")
    sp.add_argument("-o", "--out")
    _add_serve_flags(sp)
    sp.set_defaults(func=_cmd_preview)

    spr = sub.add_parser("prompt", help="emit generation prompts / theme from tokens")
    spr.add_argument("file")
    spr.add_argument("--target", choices=["gpt-image-2", "nano-banana", "tufte", "all"],
                     default="all")
    spr.add_argument("--preset", action="append",
                     help="override curated presets (image targets; repeatable)")
    spr.add_argument("--platform", default="square")
    spr.add_argument("--subject", help="override the brand mood-board subject")
    spr.add_argument("--name")
    spr.add_argument("-o", "--out")
    spr.set_defaults(func=_cmd_prompt)

    su = sub.add_parser("use")
    su.add_argument("file")
    su.add_argument("--name")
    su.add_argument("--description")
    su.add_argument("--out-dir")
    su.add_argument("--rich", action="store_true",
                    help="rich DESIGN.md from the $extensions brand block (non-standard body)")
    su.add_argument("--yes", action="store_true",
                    help="skip the --rich non-standard-format confirmation")
    _add_serve_flags(su)
    su.set_defaults(func=_cmd_use)

    sg = sub.add_parser(
        "generate",
        help="actually generate on-brand images (gpt-image-2 / nano-banana), optionally with refs.json",
    )
    sg.add_argument("file")
    sg.add_argument("--target", choices=["gpt-image-2", "nano-banana", "all"], default="all")
    sg.add_argument("--subject")
    sg.add_argument("--name")
    sg.add_argument("--refs", help="directory with reference images + refs.json (see `annotate`)")
    sg.add_argument("--out-dir")
    sg.add_argument("--platform", default="square")
    sg.add_argument("--final", action="store_true", help="high quality (default is cheap draft)")
    sg.add_argument("--dry-run", action="store_true", help="print the composed commands, no API calls")
    sg.set_defaults(func=_cmd_generate)

    sa = sub.add_parser(
        "annotate",
        help="serve a per-image role annotator for a directory of reference images -> refs.json",
    )
    sa.add_argument("dir", help="directory containing the reference images")
    sa.add_argument("--port", type=int)
    sa.add_argument("--no-open", action="store_true")
    sa.set_defaults(func=_cmd_annotate)

    sserve = sub.add_parser("serve", help="serve a file or directory over HTTP and open it")
    sserve.add_argument("path", help="a generated .html file or an output directory")
    sserve.add_argument("--port", type=int)
    sserve.add_argument("--no-open", action="store_true")
    sserve.set_defaults(func=_cmd_serve)

    return p


def main(argv=None):
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except TokenError as exc:
        print(f"error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
