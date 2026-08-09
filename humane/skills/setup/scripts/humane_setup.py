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
import hashlib
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
    "browser_tool":  ("HUMANE_BROWSER_TOOL", "auto",
                      "what drives a live interface in walkthrough driven mode (auto | agent-browser | playwright-mcp | host | user)"),
    # Empty means "wherever the corpus lives" — see artifact_root() below. A
    # literal duplicate of corpus_root's default would drift the first time one
    # of them changed.
    "artifact_root": ("HUMANE_ARTIFACT_ROOT", "",
                      "where generated artifacts land (prototypes, specimens, boards, "
                      "illustrations); empty = same as corpus_root"),
}


# Every artifact a skill generates belongs under one of these, inside the
# project's slug directory. Skills name the kind; this table owns the layout, so
# a reader can find any artifact without knowing which skill made it.
ARTIFACT_KINDS = {
    "prototype":        "prototypes",
    "type-specimen":    "specimens",
    "brandkit":         "boards",
    "brand-illustrate": "illustrations",
    "walkthrough":      "walks",
    "review":           "reviews",
}


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

class ConfigUnreadable(Exception):
    """A config file exists but could not be parsed. Carries the path."""

    def __init__(self, path, reason):
        super().__init__(f"{path}: {reason}")
        self.path, self.reason = str(path), str(reason)


def _read_json(path):
    """Return (dict, problem). A missing file is ({}, None) — that is normal.

    A file that exists but will not parse is NOT normal, and returning {} for it
    is the bug this signature exists to prevent: every setting would silently
    fall through to the layer below while `doctor` reported `source: default`,
    which is exactly the "why is it using that path?" question the config layer
    promises to answer. The caller decides whether to warn or refuse; nobody
    gets to pretend the file was not there.
    """
    p = pathlib.Path(path).expanduser()
    if not p.is_file():
        return {}, None
    try:
        data = json.loads(p.read_text())
    except json.JSONDecodeError as exc:
        return {}, ConfigUnreadable(p, f"invalid JSON ({exc.msg}, line {exc.lineno})")
    except UnicodeDecodeError as exc:
        # `read_text` decodes before json ever sees the bytes, so a file saved
        # as UTF-16 or with a stray byte raised out of here and crashed the
        # doctor — the one command whose job is to explain a broken setup.
        return {}, ConfigUnreadable(p, f"is not valid UTF-8 ({exc.reason})")
    except OSError as exc:
        return {}, ConfigUnreadable(p, f"cannot be read ({exc.strerror or exc})")
    if not isinstance(data, dict):
        return {}, ConfigUnreadable(p, f"top level is {type(data).__name__}, expected an object")
    return data, None


def _config_layers(project_dir=None):
    """((project, global) dicts, [problem dicts]) — the raw layers plus what
    could not be read. Split out so `resolve_config` stays a clean
    {setting: {...}} map and problems never masquerade as a setting."""
    project, project_problem = _read_json(pathlib.Path(project_dir or ".") / PROJECT_CONFIG)
    glob, global_problem = _read_json(GLOBAL_CONFIG)
    problems = [{"path": p.path, "reason": p.reason}
                for p in (project_problem, global_problem) if p]
    return (project, glob), problems


def config_problems(project_dir=None):
    """Config files that exist but cannot be parsed. Empty is the normal case."""
    return _config_layers(project_dir)[1]


def resolve_config(project_dir=None):
    """Return {key: {value, source}} across every layer.

    A setting resolved while some layer was unreadable is marked `suspect`: its
    source is only correct if that file held nothing for it, and that is exactly
    what cannot be known. Callers report the problems via `config_problems`.
    """
    (project, glob), problems = _config_layers(project_dir)
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
        if problems:
            out[key]["suspect"] = True
    return out


def artifact_root(config=None, project_dir=None):
    """Resolve where generated artifacts belong, as an expanded path.

    Empty `artifact_root` resolves to `corpus_root`, so by default a project's
    prototypes, specimens and boards sit in the same bundle as its corpus and a
    reader has one place to look. Set it explicitly to put artifacts somewhere
    else — inside the product repo, say, where they can be committed.

    It exists as a separate setting because the two genuinely differ in kind: a
    JTBD corpus is usually personal and global, while a prototype is often
    something you want beside the code it describes.
    """
    config = config or resolve_config(project_dir)
    value = (config.get("artifact_root", {}).get("value") or "").strip()
    if not value:
        value = config.get("corpus_root", {}).get("value") or SETTINGS["corpus_root"][1]
    return pathlib.Path(value).expanduser()


def artifact_dir(slug, kind, config=None, project_dir=None):
    """The directory a skill must write `kind` artifacts for `slug` into.

    Never the current working directory. A CWD-relative default writes a user's
    artifact into whatever tree the agent happens to be standing in — which is
    how a prototype landed inside this plugin's own source, untracked and one
    `git add -A` away from shipping to every user of the plugin.
    """
    if kind not in ARTIFACT_KINDS:
        raise ValueError(
            f"unknown artifact kind {kind!r}. Known: {', '.join(sorted(ARTIFACT_KINDS))}. "
            "Add it to ARTIFACT_KINDS rather than inventing a path at the call site."
        )
    if not slug or "/" in slug or slug.startswith("."):
        raise ValueError(f"slug {slug!r} must be a plain directory name")
    return artifact_root(config, project_dir) / slug / ARTIFACT_KINDS[kind]


def write_config(updates, scope="global", project_dir=None):
    """Merge `updates` into the chosen config file. Returns the path written."""
    if scope == "project":
        path = pathlib.Path(project_dir or ".") / PROJECT_CONFIG
    else:
        path = GLOBAL_CONFIG.expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    current, problem = _read_json(path)
    if problem:
        # Merging into {} here would write a clean file over the user's broken
        # one — losing every setting it held, including ones this call never
        # mentioned. A typo in their JSON must not cost them the file.
        raise ValueError(
            f"refusing to write: {problem.path} exists but {problem.reason}. "
            "Fix or move that file first — merging into it now would silently "
            "discard whatever it currently holds.")
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


def check_image_backend(cfg, project_dir=None):
    """Delegates to brand-illustrate's own resolver — one source of truth for
    where backends live, rather than a second list that drifts.

    The check must judge the backend the user *chose*, not merely whether any
    backend exists. Reporting `ok` because gpt-image-2 is installed, while the
    config selects nano-banana, tells the user their setup is fine right up
    until the run picks a backend that is not there.
    """
    found, how = _probe_backends(project_dir)
    if not found:
        return _missing("image backend", "none found",
                        "optional — brand-illustrate writes prompts.md without one; "
                        "install gpt-image-2 or nano-banana to generate in place")
    names = ", ".join(sorted(found))
    wanted = str(cfg["image_backend"]["value"] or "auto").split(":", 1)[0].strip()
    if wanted and wanted != "auto" and wanted not in found:
        return _missing(
            "image backend",
            f"configured as {wanted!r} ({cfg['image_backend']['source']}), "
            f"but only {names} found",
            f"install {wanted}, point HUMANE_IMAGE_BACKEND at its script, "
            f"or set image_backend to one of: {names}, or auto")
    detail = f"{names} ({how})"
    if wanted and wanted != "auto":
        detail = f"{wanted} selected; {detail}"
    return _ok("image backend", detail)


def _probe_backends(project_dir=None):
    """Import brand-illustrate's probe if it is reachable; otherwise say so."""
    here = pathlib.Path(__file__).resolve()
    candidates = [here.parents[2] / "brand-illustrate" / "scripts"]
    for c in candidates:
        if (c / "illustrate.py").is_file():
            sys.path.insert(0, str(c))
            try:
                import illustrate  # noqa: E402
                # Pass the directory being diagnosed. Without it, `doctor
                # --project-dir /elsewhere` reads a humane.json from the shell's
                # cwd and reports on a project nobody asked about.
                return illustrate.probe_backends(project_dir), "via brand-illustrate"
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


def check_browser_tool(cfg):
    """Read-only: detects the `agent-browser` binary on PATH. Never executes it
    and never makes a network call — a driven walkthrough is not this doctor's
    job, only reporting whether the top rung of the ladder is reachable.
    """
    wanted = str(cfg["browser_tool"]["value"] or "auto").strip()
    if wanted and wanted != "auto" and wanted != "agent-browser":
        return _ok("browser tool", f"configured: {wanted} (not verifiable from here)")
    path = shutil.which("agent-browser")
    if path:
        return _ok("browser tool", path)
    return _missing("browser tool", "agent-browser not found on PATH — "
                    "driven walkthroughs and the mobile tier degrade",
                    "npm i -g agent-browser")


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


def _our_skills_root():
    """The skills/ directory this script lives in — the canonical copy."""
    return pathlib.Path(__file__).resolve().parents[2]


def _our_version():
    manifest = _our_skills_root().parent / ".claude-plugin" / "plugin.json"
    return _read_json(manifest)[0].get("version")


def _skill_signature(d):
    """(relative file names, SKILL.md digest) — a cheap, stable drift signal.

    Build artefacts are excluded so a copy is not called stale for lacking a
    __pycache__ the canonical happens to have.
    """
    if not d.is_dir():
        return None
    skip = ("__pycache__", ".pytest_cache", ".git")
    names = {
        str(p.relative_to(d)) for p in d.rglob("*")
        if p.is_file() and not any(s in p.parts for s in skip)
        and p.name not in (".gitignore", ".DS_Store")
    }
    # Hash every file, not just SKILL.md: a copy whose scripts have changed
    # while the prose stayed put is exactly the drift that is hardest to spot
    # by eye, and the earlier signature called it identical.
    h = hashlib.sha256()
    for rel in sorted(names):
        f = d / rel
        try:
            h.update(rel.encode())
            h.update(f.read_bytes())
        except OSError:
            h.update(b"<unreadable>")
    return names, h.hexdigest()[:12]


def check_humane_copies(project_dir=None, roots=None, canonical_root=None,
                        marketplaces=None):
    """Find other installed copies of humane's own skills and report drift.

    'Minimize drift between copies of a skill' is a named outcome of this
    project, and it is the one failure the method cannot catch by reading a
    repo: a copy that has silently lost a file is harder to notice than one
    that is merely old. So we look.

    A symlink pointing back into this checkout is the good case and is reported
    as such. A real directory, or a symlink into a different repo, can drift —
    and we say exactly how.
    """
    canonical_root = pathlib.Path(canonical_root) if canonical_root else _our_skills_root()
    if not canonical_root.is_dir():
        return [_ok("humane copies", "canonical skills not found; skipped")]
    ours = {p.name: p for p in sorted(canonical_root.iterdir())
            if p.is_dir() and (p / "SKILL.md").is_file()}
    if not ours:
        return [_ok("humane copies", "canonical skills not found; skipped")]

    if roots is None:
        roots = [pathlib.Path("~/.claude/skills"), pathlib.Path("~/.codex/skills"),
                 pathlib.Path("~/.config/skills"),
                 pathlib.Path(project_dir or ".") / ".agents" / "skills",
                 pathlib.Path(project_dir or ".") / ".claude" / "skills"]
    roots = [pathlib.Path(r) for r in roots]

    linked, drifted = 0, []
    for root in roots:
        root = root.expanduser()
        if not root.is_dir():
            continue
        for name, canonical in ours.items():
            p = root / name
            # `exists()` follows the link, so a *dangling* symlink read as
            # "not installed" and the doctor reported no other copies — the
            # loudest possible broken install, silently invisible.
            if not p.exists() and not p.is_symlink():
                continue
            if p.is_symlink() and not p.exists():
                drifted.append((p, [f"is a broken symlink (points at "
                                    f"{os.readlink(p)}, which does not exist)"]))
                continue
            target = p.resolve()
            if target == canonical.resolve():
                linked += 1
                continue
            problems = []
            if p.is_symlink():
                problems.append(f"links to a different source ({target})")
            sig, ref = _skill_signature(p), _skill_signature(canonical)
            if sig and ref:
                missing = sorted(ref[0] - sig[0])
                extra = sorted(sig[0] - ref[0])
                if missing:
                    problems.append(f"missing {len(missing)} file(s): "
                                    + ", ".join(missing[:3])
                                    + (" …" if len(missing) > 3 else ""))
                if extra:
                    problems.append(f"{len(extra)} extra file(s)")
                if sig[1] != ref[1] and not missing and not extra:
                    problems.append("same files, different contents")
                elif sig[1] != ref[1]:
                    problems.append("contents differ")
            if not problems and not p.is_symlink():
                problems.append("independent copy, identical for now")
            drifted.append((str(p), problems))

    out = []
    if linked:
        out.append(_ok("humane copies", f"{linked} linked to this checkout"))
    for path, problems in drifted:
        out.append(_missing("humane copy", f"{path} — {'; '.join(problems)}",
                            "re-install from this repo so one skill lives in one "
                            "channel: npx skills add glebis/humane-agentic-design"))
    if not linked and not drifted:
        out.append(_ok("humane copies", "no other copies found"))
    out.extend(_check_plugin_marketplaces(marketplaces, canonical_root))
    return out


def _check_plugin_marketplaces(base=None, canonical_root=None):
    """A registered Claude Code marketplace pins a commit, so it can sit behind
    the repo indefinitely while reporting itself perfectly in sync with its own
    remote. Compare version and skill count against this checkout instead."""
    base = pathlib.Path(base).expanduser() if base else \
        pathlib.Path("~/.claude/plugins/marketplaces").expanduser()
    canonical_root = pathlib.Path(canonical_root) if canonical_root else _our_skills_root()
    if not base.is_dir():
        return []
    ours_version = _read_json(canonical_root.parent / '.claude-plugin' / 'plugin.json')[0].get('version')
    ours_count = len([p for p in canonical_root.iterdir()
                      if p.is_dir() and (p / "SKILL.md").is_file()])
    out = []
    for entry in sorted(base.iterdir()):
        manifest = entry / "humane" / ".claude-plugin" / "plugin.json"
        if not manifest.is_file():
            continue
        version = _read_json(manifest)[0].get("version")
        skills_dir = entry / "humane" / "skills"
        count = len([p for p in skills_dir.iterdir()
                     if p.is_dir() and (p / "SKILL.md").is_file()]) if skills_dir.is_dir() else 0
        if version == ours_version and count == ours_count:
            out.append(_ok("plugin marketplace", f"{entry.name} v{version}, {count} skills"))
        else:
            out.append(_missing(
                "plugin marketplace",
                f"{entry.name} is at v{version} with {count} skills; "
                f"this checkout is v{ours_version} with {ours_count}",
                "/plugin marketplace update humane-agentic-design && /plugin update humane"))
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
              check_project_tokens(project_dir),
              check_image_backend(cfg, project_dir),
              check_task_export(cfg),
              check_browser_tool(cfg)]
    checks.extend(check_companions())
    checks.extend(check_humane_copies(project_dir))
    return {"config": cfg, "checks": checks,
            "problems": config_problems(project_dir)}


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

_MARK = {"ok": "ok  ", "missing": "MISS", "optional": "--  "}


def render(report):
    cfg, lines = report["config"], []
    lines.append("configuration")
    width = max(len(k) for k in SETTINGS)
    for key in SETTINGS:
        entry = cfg[key]
        mark = " (suspect)" if entry.get("suspect") else ""
        lines.append(f"  {key.ljust(width)}  {str(entry['value']):<44}  {entry['source']}{mark}")
    for problem in report.get("problems") or []:
        # Loud, and above the environment section: every value printed above is
        # only trustworthy if this file held nothing for it, and nobody can tell.
        lines.append(f"  !! {problem['path']} exists but {problem['reason']}.")
        lines.append("     Every value above is marked suspect until it parses. "
                     "Fix the file or move it aside; `config --set` refuses to "
                     "overwrite it.")
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
        problems = config_problems(args.project_dir)
        if args.json:
            print(json.dumps({"config": cfg, "problems": problems}, indent=2))
        else:
            width = max(len(k) for k in SETTINGS)
            for key in SETTINGS:
                e = cfg[key]
                mark = " (suspect)" if e.get("suspect") else ""
                print(f"  {key.ljust(width)}  {str(e['value']):<44}  {e['source']}{mark}")
            for problem in problems:
                print(f"  !! {problem['path']} exists but {problem['reason']}. "
                      "Values above are suspect.", file=sys.stderr)
        # An unreadable config is a non-zero exit: a script that greps this
        # output must not read a full table and conclude all is well.
        return 1 if problems else 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
