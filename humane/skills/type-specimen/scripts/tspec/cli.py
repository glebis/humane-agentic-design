"""Command-line dispatch for type-specimen."""

import argparse
import json
import pathlib
import sys

from . import SpecimenError
from . import build as build_mod
from . import config as config_mod
from . import serve as serve_mod


def _families(cfg):
    n = len(cfg["families"])
    return f"{n} famil{'y' if n == 1 else 'ies'}"


def _write_config(cfg, path):
    pathlib.Path(path).write_text(
        json.dumps(cfg, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")


def _cmd_init(args):
    out = pathlib.Path(args.out)
    if out.exists() and not args.force:
        raise SpecimenError(f"{out} already exists; pass --force to overwrite")
    context = args.context or ""
    if args.from_file:
        context = _join_context(context, _read(args.from_file))
    cfg = config_mod.starter(locale=args.locale, context=context,
                             title=args.title or out.stem, ident=args.id or out.stem)
    _write_config(cfg, out)
    print(f"wrote {out}")
    print(f"{len(config_mod.todos(cfg))} text slot(s) still say "
          f"{config_mod.PLACEHOLDER} — fill them from the context, then `specimen build {out}`")
    return 0


def _read(path):
    try:
        return pathlib.Path(path).read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        raise SpecimenError(f"no such file: {path}")


def _join_context(existing, added):
    parts = [p for p in (existing.strip(), added.strip()) if p]
    return "\n\n".join(parts)


def _cmd_texts(args):
    path = pathlib.Path(args.config)
    cfg = config_mod.load(path)
    changed = False

    if args.context:
        cfg["context"] = _join_context(cfg.get("context", ""), args.context)
        changed = True
    if args.from_file:
        cfg["context"] = _join_context(cfg.get("context", ""), _read(args.from_file))
        changed = True

    for pair in args.set or []:
        key, sep, value = pair.partition("=")
        if not sep:
            raise SpecimenError(f"--set expects key=value, got {pair!r}")
        key = key.strip()
        if key not in config_mod.SLOTS:
            raise SpecimenError(
                f"unknown slot {key!r}; known slots: {', '.join(config_mod.SLOTS)}")
        # \n in a shell argument is a literal backslash-n; multi-line slots
        # would otherwise be unreachable from the command line.
        cfg["texts"][key] = value.replace("\\n", "\n")
        changed = True

    if changed:
        errors = config_mod.validate(cfg)
        if errors:
            # Report without writing, so a bad --set never corrupts the config.
            raise SpecimenError("\n".join(f"  - {e}" for e in errors))
        _write_config(cfg, path)
        print(f"updated {path}")

    _report_texts(cfg)
    return 0


def _report_texts(cfg):
    todo = config_mod.todos(cfg)
    if cfg.get("context"):
        print("\ncontext:")
        for line in cfg["context"].splitlines():
            print(f"  {line}")
    print("\nslots:")
    for key, (multiline, cells) in config_mod.SLOTS.items():
        shape = ("many lines" if multiline else "one line")
        if cells > 1:
            shape += f", {cells} '::' cells each"
        value = str(cfg["texts"].get(key, ""))
        first = value.splitlines()[0] if value.splitlines() else ""
        mark = "TODO" if key in todo else "  ok"
        print(f"  {mark}  {key:<10} ({shape}) {first[:48]}")
    if todo:
        print(f"\n{len(todo)} slot(s) unwritten: {', '.join(todo)}")


def _cmd_check(args):
    cfg = config_mod.load(args.config)  # raises on any structural problem
    todo = config_mod.todos(cfg)
    if todo:
        print(f"config is valid, but {len(todo)} slot(s) still say "
              f"{config_mod.PLACEHOLDER}: {', '.join(todo)}")
        return 1
    print(f"{args.config}: valid, {_families(cfg)}, all slots written")
    return 0


def _cmd_build(args):
    cfg = config_mod.load(args.config)
    todo = config_mod.todos(cfg)
    if todo and not args.allow_todo:
        raise SpecimenError(
            f"{len(todo)} text slot(s) still say {config_mod.PLACEHOLDER}: "
            f"{', '.join(todo)}\n"
            f"  Write them with `specimen texts {args.config} --set <slot>=...`, "
            f"or pass --allow-todo to build anyway.")

    out = pathlib.Path(args.out or (pathlib.Path(args.config).with_suffix(".html")))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build_mod.build(cfg, template=args.template), encoding="utf-8")
    print(f"wrote {out}  ({_families(cfg)})")
    if todo:
        print(f"warning: built with {len(todo)} unwritten slot(s): {', '.join(todo)}",
              file=sys.stderr)

    want = args.serve
    if want is None:
        want = sys.stdout.isatty()
    if want:
        serve_mod.serve(out.parent, out.name, port=args.port, open_browser=not args.no_open)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="specimen",
        description="Build a standalone type specimen page from a config file.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init", help="write a starter config")
    p.add_argument("-o", "--out", default="specimen.json")
    p.add_argument("--locale", default="en", choices=config_mod.LOCALES)
    p.add_argument("--title", help="page title (default: the config filename)")
    p.add_argument("--id", help="localStorage key (default: the config filename)")
    p.add_argument("--context", help="what the type is for — the brief the copy is written against")
    p.add_argument("--from-file", dest="from_file", metavar="FILE",
                   help="read further context from a file (a README, a spec, real product copy)")
    p.add_argument("--force", action="store_true", help="overwrite an existing config")
    p.set_defaults(fn=_cmd_init)

    p = sub.add_parser("texts", help="show, extend, or write the specimen copy")
    p.add_argument("config")
    p.add_argument("--set", action="append", metavar="SLOT=TEXT",
                   help="write one slot; repeatable. Use \\n for a line break.")
    p.add_argument("--context", help="add to the stored brief")
    p.add_argument("--from-file", dest="from_file", metavar="FILE",
                   help="add a file's contents to the stored brief")
    p.set_defaults(fn=_cmd_texts)

    p = sub.add_parser("check", help="validate a config without building")
    p.add_argument("config")
    p.set_defaults(fn=_cmd_check)

    p = sub.add_parser("build", help="render the config to a standalone HTML page")
    p.add_argument("config")
    p.add_argument("-o", "--out", help="output path (default: the config path with .html)")
    p.add_argument("--template", help="override the bundled template")
    p.add_argument("--allow-todo", action="store_true",
                   help="build even though some slots are still placeholders")
    p.add_argument("--serve", dest="serve", action="store_true", default=None,
                   help="serve over HTTP and open it (default: on when interactive)")
    p.add_argument("--no-serve", dest="serve", action="store_false",
                   help="just write the file")
    p.add_argument("--port", type=int)
    p.add_argument("--no-open", action="store_true", help="serve but do not open a browser")
    p.set_defaults(fn=_cmd_build)

    args = parser.parse_args(argv)
    try:
        return args.fn(args)
    except SpecimenError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
