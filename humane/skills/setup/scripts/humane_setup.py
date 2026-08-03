#!/usr/bin/env python3
"""humane setup: resolve configuration, check the environment, report what is missing.

Stdlib only. Two jobs, deliberately separated:

  doctor  — read-only. Resolve config, check every dependency the cycle needs,
            and print the exact command that fixes each gap. Never installs,
            never writes, never asks for a key.
  config  — read/write ~/.humane/config.json (and a project humane.json).

Installing companions is NOT done here. The install commands differ per agent
and per plugin, several are interactive, and one of them handles API keys — so
this script *prints* them and the skill's operator runs them with the user
watching. A doctor that silently installs things is a doctor you stop trusting.

Config resolution, highest precedence first:

    <project>/humane.json   an explicit, committed project override
    ~/.humane/config.json   machine-wide defaults
    HUMANE_* environment    ambient
    built-in defaults

Project beats environment on purpose: a repo that pins its corpus root should
win over a stray exported variable in the shell that happens to be running.
"""

import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys

GLOBAL_CONFIG = pathlib.Path("~/.humane/config.json")
PROJECT_CONFIG = "humane.json"

# key -> (env var, built-in default, one-line meaning)
SETTINGS = {
    "corpus_root":   ("HUMANE_CORPUS_ROOT",  "~/jtbd",
                      "where jtbd writes and every later skill reads"),
    "token_base":    ("HUMANE_TOKEN_BASE",   "~/design-tokens/base.tokens.json",
                      "global brand base that projects layer over"),
    "image_backend": ("HUMANE_IMAGE_BACKEND", "auto",
                      "generator for brand-illustrate (auto | name | name:/path)"),
    "task_export":   ("HUMANE_TASK_EXPORT",  "none",
                      "where nielsen-heuristics files findings (linear | beads | none)"),
    "language":      ("HUMANE_LANGUAGE",     "en",
                      "language for skill output; captured evidence is never translated"),
}


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def _read_json(path):
    p = pathlib.Path(path).expanduser()
    if not p.is_file():
        return {}
    try:
        data = json.loads(p.read_text())
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def resolve_config(project_dir=None):
    """Return {key: {value, source}} across every layer."""
    project = _read_json(pathlib.Path(project_dir or ".") / PROJECT_CONFIG)
    glob = _read_json(GLOBAL_CONFIG)
    out = {}
    for key, (env_var, default, _desc) in SETTINGS.items():
        if key in project:
            out[key] = {"value": project[key], "source": PROJECT_CONFIG}
        elif key in glob:
            out[key] = {"value": glob[key], "source": str(GLOBAL_CONFIG)}
        elif os.environ.get(env_var):
            out[key] = {"value": os.environ[env_var], "source": f"${env_var}"}
        else:
            out[key] = {"value": default, "source": "default"}
    return out


def write_config(updates, scope="global", project_dir=None):
    """Merge `updates` into the chosen config file. Returns the path written."""
    if scope == "project":
        path = pathlib.Path(project_dir or ".") / PROJECT_CONFIG
    else:
        path = GLOBAL_CONFIG.expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    current = _read_json(path)
    unknown = [k for k in updates if k not in SETTINGS]
    if unknown:
        raise ValueError(f"unknown setting(s): {', '.join(sorted(unknown))}. "
                         f"Known: {', '.join(sorted(SETTINGS))}")
    current.update(updates)
    path.write_text(json.dumps(current, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    return str(path)


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def _ok(name, detail=""):
    return {"name": name, "state": "ok", "detail": detail, "fix": None}


def _missing(name, detail, fix, required=False):
    return {"name": name, "state": "missing" if required else "optional",
            "detail": detail, "fix": fix}


def check_python():
    v = sys.version_info
    label = f"python {v.major}.{v.minor}.{v.micro}"
    if (v.major, v.minor) >= (3, 8):
        return _ok("python3", label)
    return _missing("python3", f"{label} — scripts target 3.8+",
                    "install a newer python3", required=True)


def check_corpus(cfg):
    root = pathlib.Path(cfg["corpus_root"]["value"]).expanduser()
    if not root.is_dir():
        return _missing("corpus", f"{root} does not exist",
                        "run humane:jtbd — it creates the corpus on first use")
    bundles = [p for p in root.iterdir() if p.is_dir() and (p / "jtbd.json").is_file()]
    if not bundles:
        return _missing("corpus", f"{root} exists but holds no jtbd.json bundle",
                        "run humane:jtbd to capture the first job")
    return _ok("corpus", f"{len(bundles)} bundle(s) in {root}")


def check_tokens(cfg):
    base = pathlib.Path(cfg["token_base"]["value"]).expanduser()
    if base.is_file():
        return _ok("token base", str(base))
    return _missing("token base", f"{base} not found",
                    f"tokens setup-edit {base}")


def check_project_tokens(project_dir=None):
    d = pathlib.Path(project_dir or ".")
    for cand in (d / "design.tokens.json", *sorted(d.glob("*.tokens.json")),
                 *sorted(d.glob("tokens/*.tokens.json"))):
        if cand.is_file():
            return _ok("project tokens", str(cand))
    return _missing("project tokens", "no *.tokens.json in this project",
                    "tokens setup-edit design.tokens.json")


def check_image_backend(cfg):
    """Delegates to brand-illustrate's own resolver — one source of truth for
    where backends live, rather than a second list that drifts."""
    found, how = _probe_backends()
    if found:
        names = ", ".join(f"{k}" for k in sorted(found))
        return _ok("image backend", f"{names} ({how})")
    return _missing("image backend", "none found",
                    "optional — brand-illustrate writes prompts.md without one; "
                    "install gpt-image-2 or nano-banana to generate in place")


def _probe_backends():
    """Import brand-illustrate's probe if it is reachable; otherwise say so."""
    here = pathlib.Path(__file__).resolve()
    candidates = [here.parents[2] / "brand-illustrate" / "scripts"]
    for c in candidates:
        if (c / "illustrate.py").is_file():
            sys.path.insert(0, str(c))
            try:
                import illustrate  # noqa: E402
                return illustrate.probe_backends(), "via brand-illustrate"
            except Exception:
                break
            finally:
                sys.path.pop(0)
    return {}, "brand-illustrate not reachable"


def check_task_export(cfg):
    target = str(cfg["task_export"]["value"]).lower()
    if target in ("none", "", "skip"):
        return _ok("task export", "not configured (findings stay in the report)")
    exe = {"linear": "linear", "beads": "bd"}.get(target)
    if not exe:
        return _missing("task export", f"unknown target {target!r}",
                        "set task_export to linear, beads, or none")
    path = shutil.which(exe)
    if path:
        return _ok("task export", f"{target} ({path})")
    return _missing("task export", f"{target} selected but `{exe}` is not on PATH",
                    f"install the {target} CLI, or set task_export to none")


def check_companions():
    """Plugins humane defers to. Absent is fine and reported honestly — the
    review skills mark those domains Not reviewed rather than improvising."""
    out = []
    for name, what, where in [
        ("interfaces", "typography, color, a11y, motion craft",
         "/plugin marketplace add jakubkrehel/skills && /plugin install interfaces@interfaces"),
        ("impeccable", "post-build audit and polish", "/plugin install impeccable"),
    ]:
        hit = _find_skill_dir(name)
        out.append(_ok(f"companion: {name}", str(hit)) if hit else
                   _missing(f"companion: {name}", f"not installed — {what} stay Not reviewed",
                            where))
    return out


def _find_skill_dir(name):
    roots = [pathlib.Path("~/.claude/skills"), pathlib.Path("~/.claude/plugins"),
             pathlib.Path("~/.codex/skills"), pathlib.Path(".agents/skills")]
    for r in roots:
        p = r.expanduser() / name
        if p.exists():
            return p
    return None


def doctor(project_dir=None):
    cfg = resolve_config(project_dir)
    checks = [check_python(), check_corpus(cfg), check_tokens(cfg),
              check_project_tokens(project_dir), check_image_backend(cfg),
              check_task_export(cfg)]
    checks.extend(check_companions())
    return {"config": cfg, "checks": checks}


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

_MARK = {"ok": "ok  ", "missing": "MISS", "optional": "--  "}


def render(report):
    cfg, lines = report["config"], []
    lines.append("configuration")
    width = max(len(k) for k in cfg)
    for key in SETTINGS:
        entry = cfg[key]
        lines.append(f"  {key.ljust(width)}  {str(entry['value']):<44}  {entry['source']}")
    lines.append("")
    lines.append("environment")
    width = max(len(c["name"]) for c in report["checks"])
    for c in report["checks"]:
        lines.append(f"  {_MARK[c['state']]}  {c['name'].ljust(width)}  {c['detail']}")
        if c["fix"]:
            lines.append(f"        {' ' * width}  -> {c['fix']}")
    missing = [c for c in report["checks"] if c["state"] == "missing"]
    optional = [c for c in report["checks"] if c["state"] == "optional"]
    lines.append("")
    lines.append(f"{len(missing)} blocking, {len(optional)} optional gap(s). "
                 "Nothing was installed or changed.")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv=None):
    p = argparse.ArgumentParser(prog="humane-setup",
                                description="resolve config and check the humane environment")
    sub = p.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("doctor", help="check the environment (read-only)")
    d.add_argument("--project-dir", default=".")
    d.add_argument("--json", action="store_true")

    s = sub.add_parser("config", help="show or set configuration")
    s.add_argument("--project-dir", default=".")
    s.add_argument("--set", action="append", default=[], metavar="KEY=VALUE")
    s.add_argument("--scope", choices=("global", "project"), default="global")
    s.add_argument("--json", action="store_true")

    sub.add_parser("settings", help="list known settings and their meaning")

    args = p.parse_args(argv)

    if args.cmd == "settings":
        for key, (env, default, desc) in SETTINGS.items():
            print(f"{key}\n  {desc}\n  env {env}   default {default}\n")
        return 0

    if args.cmd == "doctor":
        report = doctor(args.project_dir)
        print(json.dumps(report, indent=2) if args.json else render(report), end="")
        return 1 if any(c["state"] == "missing" for c in report["checks"]) else 0

    if args.cmd == "config":
        if args.set:
            updates = {}
            for pair in args.set:
                if "=" not in pair:
                    print(f"error: --set expects KEY=VALUE, got {pair!r}", file=sys.stderr)
                    return 2
                k, _, v = pair.partition("=")
                updates[k.strip()] = v.strip()
            try:
                path = write_config(updates, args.scope, args.project_dir)
            except ValueError as exc:
                print(f"error: {exc}", file=sys.stderr)
                return 2
            print(f"wrote {path}")
        cfg = resolve_config(args.project_dir)
        if args.json:
            print(json.dumps(cfg, indent=2))
        else:
            width = max(len(k) for k in cfg)
            for key in SETTINGS:
                e = cfg[key]
                print(f"  {key.ljust(width)}  {str(e['value']):<44}  {e['source']}")
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
