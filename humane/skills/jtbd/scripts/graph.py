#!/usr/bin/env python3
"""Build and serve a visual graph over one or more jtbd.json bundles.

Reads the artifacts the skill already writes (<corpus_root>/<slug>/jtbd.json), shapes
them into a single data.json, drops the viewer next to it and serves the pair.
Stdlib only, no build step, nothing leaves the machine.

    python3 scripts/graph.py                    # every project under the corpus root
    python3 scripts/graph.py ~/jtbd/my-thing    # one project (dir or file)
    python3 scripts/graph.py --no-serve         # just write the bundle
    python3 scripts/graph.py --port 8811

The default root follows the `corpus_root` setting owned by `setup`; pass a
path to override it for one run.
"""
from __future__ import annotations

import argparse
import http.server
import json
import os
import shutil
import socketserver
import sys
import webbrowser
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE.parent / "templates" / "graph.html"


def _corpus_root(project_dir=None):
    """Where the corpus lives, per the `corpus_root` setting.

    `setup` owns this setting and its precedence — project `humane.json` >
    `~/.humane/config.json` > `HUMANE_CORPUS_ROOT` > `~/jtbd`. It is re-read
    here rather than imported because skills install independently: jtbd may be
    present on a machine where `setup` is not, and a hard import would make the
    graph unopenable for that user. Keep the order identical to setup's table;
    a divergence here means a user's configured root is honoured by one command
    and ignored by the next, which is worse than not supporting it at all.

    Only this one key is read, and an unparseable file is skipped silently —
    `setup doctor` is the place that explains a broken config, not the viewer.
    """
    def _get(path):
        try:
            data = json.loads(Path(path).expanduser().read_text())
        except (OSError, ValueError):
            return None
        return data.get("corpus_root") if isinstance(data, dict) else None

    for candidate in (Path(project_dir or ".") / "humane.json",
                      Path("~/.humane/config.json")):
        value = _get(candidate)
        if value:
            return Path(value).expanduser()
    return Path(os.environ.get("HUMANE_CORPUS_ROOT") or "~/jtbd").expanduser()


DEFAULT_ROOT = _corpus_root()


def score(importance, satisfaction):
    """ODI opportunity score — same formula as scripts/odi_score.py."""
    return importance + max(0, importance - satisfaction)


def tier(opportunity_score):
    if opportunity_score >= 12:
        return "prioritize"
    if opportunity_score <= 8:
        return "skip"
    return "marginal"


def _list(value):
    """The schema allows a string where a list is meant; accept both."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, list):
        return [v for v in value if v]
    return []


def read_quotes(evidence: dict) -> list[dict]:
    """Evidence arrives in two shapes in the wild.

    `evidence.quotes[]` is the documented one — a flat list of strings. Some
    bundles instead carry `evidence.ledger[]`, an entry per quote with an id and
    an attribution, which is strictly richer. Read both, normalise to one shape,
    and never make the caller care which file used which.
    """
    out = []
    for q in _list(evidence.get("quotes")):
        if isinstance(q, str):
            out.append({"id": None, "text": q, "who": ""})
        elif isinstance(q, dict):
            out.append({"id": q.get("id"),
                        "text": q.get("quote") or q.get("text", ""),
                        "who": q.get("who", "")})
    for q in _list(evidence.get("ledger")):
        if isinstance(q, dict) and (q.get("quote") or q.get("text")):
            out.append({"id": q.get("id"),
                        "text": q.get("quote") or q.get("text", ""),
                        "who": q.get("who", "")})
    return out


def find_bundles(target: Path) -> list[Path]:
    if target.is_file():
        return [target]
    if (target / "jtbd.json").is_file():
        return [target / "jtbd.json"]
    return sorted(target.glob("*/jtbd.json"))


def read_evidence_ids(evidence: dict) -> set[str]:
    """The ledger ids an outcome is allowed to cite — the ones this file defines."""
    ids = set()
    for q in _list(evidence.get("ledger")):
        if isinstance(q, dict) and q.get("id"):
            ids.add(q["id"])
    for q in _list(evidence.get("quotes")):
        if isinstance(q, dict) and q.get("id"):
            ids.add(q["id"])
    return ids


def shape(path: Path) -> dict | None:
    """One jtbd.json → one project record the viewer understands."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"  skipped {path}: {exc}", file=sys.stderr)
        return None

    slug = raw.get("name") or path.parent.name
    core = raw.get("jtbd") or {}
    problem = raw.get("problem") or {}
    needs = raw.get("needs") or {}
    forces = raw.get("switch_forces") or {}
    evidence = raw.get("evidence") or {}
    ledger_ids = read_evidence_ids(evidence)

    def outcome_evidence(o, oid):
        """Only pass through ledger ids this file actually defines; warn on the rest."""
        kept = []
        for eid in _list(o.get("evidence")):
            if eid in ledger_ids:
                kept.append(eid)
            else:
                print(f"  {slug} {oid}: unknown evidence id {eid!r} "
                      f"(not in this bundle's ledger) — dropped", file=sys.stderr)
        return kept

    STAGES = ("define", "locate", "prepare", "confirm",
              "execute", "monitor", "modify", "conclude")
    outcomes = []
    for i, o in enumerate(_list((raw.get("odi") or {}).get("outcomes"))):
        if not isinstance(o, dict):
            continue
        oid = f"{slug}:o{i}"
        stage = o.get("stage")
        stage = stage if stage in STAGES else None
        touch = o.get("touch") if isinstance(o.get("touch"), str) and o.get("touch") else None
        ev = outcome_evidence(o, oid)
        imp, sat = o.get("importance"), o.get("satisfaction")
        if imp is None or sat is None:
            # an outcome with no measures still belongs in the record, it just
            # cannot be placed on the landscape
            outcomes.append({
                "id": oid, "statement": o.get("statement", ""),
                "imp": None, "sat": None, "opp": None, "tier": "unscored",
                "stage": stage, "touch": touch, "evidence": ev,
                "depends_on": _list(o.get("depends_on")),
            })
            continue
        opp = o.get("opportunity_score")
        if opp is None:
            opp = score(imp, sat)
        outcomes.append({
            "id": oid, "statement": o.get("statement", ""),
            "imp": imp, "sat": sat, "opp": round(opp, 1), "tier": tier(opp),
            "stage": stage, "touch": touch, "evidence": ev,
            "depends_on": _list(o.get("depends_on")),
        })

    macro = raw.get("macro")
    return {
        "slug": slug,
        "path": str(path),
        "name": slug,
        "actor": raw.get("actor", "") or "",
        "macro": macro if isinstance(macro, str) and macro else None,
        "context": raw.get("context", "") or "",
        "depends_on": _list(raw.get("depends_on")),
        "hook": raw.get("hook", ""),
        "situation": core.get("situation", ""),
        "motivation": core.get("motivation", ""),
        "outcome": core.get("outcome", ""),
        "what_hurts": problem.get("what_hurts", ""),
        "cost_today": problem.get("cost_today", ""),
        "needs": {k: _list(needs.get(k)) for k in ("functional", "emotional", "social")},
        "forces": {k: forces.get(k, "") for k in ("push", "pull", "habit", "anxiety")},
        "outputs": _list(raw.get("outputs")),
        "guardrails": _list(raw.get("guardrails")),
        # extended blocks the skill writes when they surface naturally
        "target_users": _list(raw.get("target_users")),
        "before_after": raw.get("before_after") or {},
        "scenarios": [s for s in _list(raw.get("scenarios")) if isinstance(s, dict)],
        "trigger": raw.get("trigger") or {},
        "version": raw.get("version"),
        "quotes": read_quotes(evidence),
        "evidence_source": evidence.get("source", ""),
        "evidence_limitation": evidence.get("limitation", ""),
        "pages_read": _list(evidence.get("pages_read")),
        "weaknesses": _list(evidence.get("weaknesses")),
        "open_questions": _list(raw.get("open_questions")),
        "links": [l for l in _list(raw.get("links")) if isinstance(l, str)],
        "outcomes": outcomes,
    }


LANGS = ("auto", "en", "ru")

EMPTY_CORPUS = {"business_outcomes": [], "macros": [], "touchpoints": []}


def load_corpus(target: Path) -> dict:
    """Read corpus.json next to the bundles (or the default root). Missing is fine —
    the corpus level is optional and the viewer must cope with empty lists."""
    base = target if target.is_dir() else target.parent
    for cand in (base / "corpus.json", DEFAULT_ROOT / "corpus.json"):
        if cand.is_file():
            try:
                raw = json.loads(cand.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                print(f"  corpus.json ignored ({cand}): {exc}", file=sys.stderr)
                return dict(EMPTY_CORPUS)
            return {k: _list(raw.get(k)) for k in EMPTY_CORPUS}
    return dict(EMPTY_CORPUS)


def build(target: Path, out: Path, lang: str = "auto") -> dict:
    bundles = find_bundles(target)
    if not bundles:
        raise SystemExit(
            f"No jtbd.json found under {target}.\n"
            f"Run the jtbd skill first, or pass a path to a bundle."
        )
    projects = [p for p in (shape(b) for b in bundles) if p]
    if not projects:
        raise SystemExit(f"Found {len(bundles)} file(s) under {target} but none parsed.")

    corpus = load_corpus(target)
    macro_ids = {m.get("id") for m in corpus["macros"] if isinstance(m, dict)}
    for bo in corpus["business_outcomes"]:
        if isinstance(bo, dict):
            for mref in _list(bo.get("macros")):
                if mref not in macro_ids:
                    print(f"  corpus: business outcome {bo.get('id')!r} references "
                          f"unknown macro {mref!r}", file=sys.stderr)
    # validate each project's macro against the corpus; null the ones that miss
    for p in projects:
        if p["macro"] and macro_ids and p["macro"] not in macro_ids:
            print(f"  {p['slug']}: macro {p['macro']!r} not in corpus — nulled",
                  file=sys.stderr)
            p["macro"] = None

    # "auto" lets the browser decide; an explicit code is the default the viewer
    # opens with, and its own language toggle still overrides per browser
    data = {"root": str(target), "lang": lang if lang in LANGS else "auto",
            "corpus": corpus, "projects": projects}
    out.mkdir(parents=True, exist_ok=True)
    (out / "data.json").write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    shutil.copyfile(TEMPLATE, out / "index.html")

    scored = sum(1 for p in projects for o in p["outcomes"] if o["opp"] is not None)
    unscored = sum(1 for p in projects for o in p["outcomes"] if o["opp"] is None)
    no_macro = sum(1 for p in projects if not p["macro"])
    macro_note = "all mapped to a macro" if not no_macro else f"{no_macro} without macro"
    print(f"  {len(projects)} project(s), {scored} scored outcome(s)"
          + (f", {unscored} unscored" if unscored else "")
          + f"; {len(corpus['macros'])} macro(s), {macro_note}")
    for p in projects:
        top = max((o for o in p["outcomes"] if o["opp"] is not None),
                  key=lambda o: o["opp"], default=None)
        line = f"  · {p['slug']}: {len(p['outcomes'])} outcomes, {len(p['quotes'])} quotes"
        if top:
            line += f", worst-served {top['opp']} ({top['tier']})"
        if not p["outcomes"]:
            line += "  — no ODI pass yet, landscape will be empty"
        print(line)
    return data


def serve(out: Path, port: int, open_browser: bool = True) -> None:
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(out), **kw)

        def log_message(self, *a):  # keep the terminal quiet
            pass

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", port), Handler) as httpd:
        url = f"http://localhost:{port}/"
        print(f"\n  JTBD graph → {url}   (ctrl-c to stop)")
        if open_browser:
            webbrowser.open(url)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n  stopped")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target", nargs="?", default=str(DEFAULT_ROOT),
                    help="a jtbd.json, a project dir, or a root of project dirs "
                         f"(default {DEFAULT_ROOT})")
    ap.add_argument("--out", default=None, help="where to write the viewer (default <target>/.graph)")
    ap.add_argument("--lang", choices=LANGS, default="auto",
                    help="interface language the viewer opens with (default auto: follow the browser). "
                         "The record itself is always shown as captured.")
    ap.add_argument("--port", type=int, default=8810)
    ap.add_argument("--no-serve", action="store_true", help="write the bundle and exit")
    ap.add_argument("--no-open", action="store_true", help="serve without opening a browser")
    args = ap.parse_args()

    target = Path(os.path.expanduser(args.target)).resolve()
    if not target.exists():
        raise SystemExit(f"{target} does not exist.")
    base = target if target.is_dir() else target.parent
    out = Path(os.path.expanduser(args.out)).resolve() if args.out else base / ".graph"

    print(f"Reading {target}")
    build(target, out, args.lang)
    print(f"  wrote {out}/data.json + index.html")
    if not args.no_serve:
        serve(out, args.port, open_browser=not args.no_open)


if __name__ == "__main__":
    main()
