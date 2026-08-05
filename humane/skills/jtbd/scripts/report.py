#!/usr/bin/env python3
"""Generate stakeholder-facing reports from jtbd.json bundles.

Starts with the executive summary: a one-page read for someone who has three
minutes. Single project or whole-corpus. Stdlib only.

    python3 scripts/report.py exec-summary <slug> [--root DIR] [--out PATH] [--lang en|ru]
    python3 scripts/report.py exec-summary --all  [--root DIR] [--out PATH] [--lang en|ru]

Honesty guards match the skill's ethos: creator-estimate scores carry a visible
caveat, partial/unknown forces are shown as such, and nothing is dressed up with
adjectives that are not in the data. Statements and quotes are printed as
captured — only the report's own headings follow --lang.
"""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from graph import DEFAULT_ROOT, _list, find_bundles, read_quotes, score, tier


# --- localized chrome (headings only; data stays as captured) ----------------

STRINGS = {
    "en": {
        "title": "Executive summary",
        "corpus_title": "Corpus executive summary",
        "job": "The job",
        "top_opps": "Top opportunities",
        "forces": "Switch forces",
        "evidence": "Evidence health",
        "quote": "Load-bearing quote",
        "open_q": "Open questions",
        "next_move": "Recommended next move",
        "caveat": "> Scores are a creator estimate, not survey data — read them as direction, not measurement.",
        "why": "Why it matters",
        "quotes_n": "{n} verbatim quote(s)",
        "source": "source",
        "weaknesses": "Key weaknesses",
        "none_weak": "none recorded",
        "toward": "Pull toward the switch:",
        "holdback": "Holding it back:",
        "flag_partial": "(forces flagged partial/unknown — not fully evidenced)",
        "open_count": "{n} open question(s). Top {k}:",
        "no_open": "No open questions recorded.",
        "next_tmpl": "The next build should attack the **{stage}** stage: {statement}",
        "next_nostage": "The next build should attack the worst-served outcome: {statement}",
        "no_odi": "No ODI scoring yet — run outcome scoring to surface opportunities and a recommended next move.",
        "cited": "cited by {ids}",
        "derived": "derived from the job outcome; no direct quote",
        "macros_h": "By macro (worst-served first)",
        "corpus_top": "Corpus-wide top {k} opportunities",
        "thin_h": "Evidence-thin projects",
        "thin_line": "{slug} — {n} quote(s)",
        "no_thin": "No evidence-thin projects.",
        "mean_opp": "mean opp",
        "projects": "projects",
        "col_project": "Project",
        "col_outcome": "Outcome",
        "unassigned": "unassigned macro",
    },
    "ru": {
        "title": "Резюме для стейкхолдера",
        "corpus_title": "Резюме по корпусу",
        "job": "Работа (job)",
        "top_opps": "Главные возможности",
        "forces": "Силы переключения",
        "evidence": "Здоровье доказательной базы",
        "quote": "Ключевая цитата",
        "open_q": "Открытые вопросы",
        "next_move": "Рекомендуемый следующий шаг",
        "caveat": "> Оценки — прикидка автора, не данные опроса: читать как направление, не как измерение.",
        "why": "Почему это важно",
        "quotes_n": "{n} дословных цитат(ы)",
        "source": "источник",
        "weaknesses": "Ключевые слабости",
        "none_weak": "не зафиксированы",
        "toward": "Тянет к переключению:",
        "holdback": "Удерживает:",
        "flag_partial": "(силы помечены partial/unknown — доказательная база неполна)",
        "open_count": "{n} открытых вопрос(ов). Топ-{k}:",
        "no_open": "Открытых вопросов нет.",
        "next_tmpl": "Следующая итерация должна закрыть стадию **{stage}**: {statement}",
        "next_nostage": "Следующая итерация должна закрыть худше всего обслуженный outcome: {statement}",
        "no_odi": "ODI-оценки ещё нет — проведите скоринг, чтобы получить возможности и следующий шаг.",
        "cited": "опирается на {ids}",
        "derived": "выведено из outcome работы; прямой цитаты нет",
        "macros_h": "По макро (худше всего обслуженные — первыми)",
        "corpus_top": "Топ-{k} возможностей по корпусу",
        "thin_h": "Проекты с тонкой доказательной базой",
        "thin_line": "{slug} — {n} цитат(ы)",
        "no_thin": "Проектов с тонкой базой нет.",
        "mean_opp": "средний opp",
        "projects": "проектов",
        "col_project": "Проект",
        "col_outcome": "Outcome",
        "unassigned": "без макро",
    },
}


# --- small text helpers ------------------------------------------------------

def clean_clause(text):
    """Trim trailing whitespace and dangling ellipsis/periods so the three job
    clauses flow into one sentence without keeping evidence ids intact."""
    if not text:
        return ""
    t = str(text).strip()
    while t and t[-1] in ".…":
        t = t[:-1].rstrip()
    return t


def first_sentence(text):
    if not text:
        return ""
    t = str(text).strip()
    for sep in (". ", "; ", " — "):
        idx = t.find(sep)
        if idx != -1:
            return t[:idx].strip()
    return clean_clause(t)


def has_flag(text):
    if not text:
        return False
    low = str(text).lower()
    return "partial" in low or "unknown" in low


def is_creator_estimate(odi):
    note = (odi.get("note") or "") + " " + (odi.get("method") or "")
    low = note.lower()
    return "creator-estimate" in low or "creator_estimate" in low


# --- outcome access ----------------------------------------------------------

def outcome_row(o):
    """Normalise one odi outcome to imp/sat/opp/tier, computing what's missing."""
    imp = o.get("importance")
    sat = o.get("satisfaction")
    opp = o.get("opportunity_score")
    if opp is None and imp is not None and sat is not None:
        opp = score(imp, sat)
    t = o.get("tier") or (tier(opp) if opp is not None else None)
    return {
        "statement": o.get("statement", ""),
        "stage": o.get("stage"),
        "imp": imp,
        "sat": sat,
        "opp": round(opp, 1) if opp is not None else None,
        "tier": t,
        "evidence": [e for e in _list(o.get("evidence")) if e],
        "basis": o.get("basis"),
    }


def scored_outcomes(data):
    outs = [outcome_row(o) for o in _list(data.get("odi", {}).get("outcomes"))]
    scored = [o for o in outs if o["opp"] is not None]
    scored.sort(key=lambda o: o["opp"], reverse=True)
    return scored


def why_it_matters(o, S):
    if o["basis"]:
        return first_sentence(o["basis"])
    if o["evidence"]:
        return S["cited"].format(ids=", ".join(o["evidence"]))
    return S["derived"]


def load_bearing_quote(data, top):
    """The single quote doing the most work: the ledger id referenced by the
    most scored outcomes, tie-broken toward the top opportunity's evidence."""
    quotes = read_quotes(data.get("evidence", {}))
    if not quotes:
        return None
    by_id = {q["id"]: q for q in quotes if q.get("id")}
    counts = {}
    for o in scored_outcomes(data):
        for eid in o["evidence"]:
            counts[eid] = counts.get(eid, 0) + 1
    if counts and by_id:
        top_ev = top[0]["evidence"] if top else []
        def rank(eid):
            return (counts.get(eid, 0), eid in top_ev)
        best = max((eid for eid in by_id), key=rank, default=None)
        if best and counts.get(best, 0) > 0:
            return by_id[best]
    return quotes[0]


# --- single-project exec summary ---------------------------------------------

def render_exec_summary(data, lang="en"):
    S = STRINGS.get(lang, STRINGS["en"])
    odi = data.get("odi", {}) or {}
    lines = []
    name = data.get("name", "(unnamed)")
    lines.append(f"# {S['title']} — {name}")
    lines.append("")
    if data.get("hook"):
        lines.append(str(data["hook"]).strip())
        lines.append("")
    if is_creator_estimate(odi):
        lines.append(S["caveat"])
        lines.append("")

    # The job — the triple as one flowing paragraph.
    jt = data.get("jtbd", {}) or {}
    triple = ". ".join(
        c for c in (
            clean_clause(jt.get("situation")),
            clean_clause(jt.get("motivation")),
            clean_clause(jt.get("outcome")),
        ) if c
    )
    if triple:
        lines.append(f"## {S['job']}")
        lines.append("")
        lines.append(triple + ("." if triple and triple[-1] not in ".!?" else ""))
        lines.append("")

    # Top opportunities.
    top = scored_outcomes(data)
    lines.append(f"## {S['top_opps']}")
    lines.append("")
    if not top:
        lines.append(S["no_odi"])
        lines.append("")
    else:
        for i, o in enumerate(top[:3], 1):
            ev = f" [{', '.join(o['evidence'])}]" if o["evidence"] else ""
            head = (f"{i}. **{o['statement']}** — "
                    f"imp {o['imp']} / sat {o['sat']} / opp {o['opp']}"
                    f" · _{o['tier']}_{ev}")
            lines.append(head)
            lines.append(f"   {S['why']}: {why_it_matters(o, S)}")
        lines.append("")

    # Switch forces in two sentences.
    sf = data.get("switch_forces", {}) or {}
    if any(sf.get(k) for k in ("push", "pull", "habit", "anxiety")):
        lines.append(f"## {S['forces']}")
        lines.append("")
        toward = "; ".join(
            first_sentence(sf.get(k)) for k in ("push", "pull") if sf.get(k)
        )
        holdback = "; ".join(
            first_sentence(sf.get(k)) for k in ("habit", "anxiety") if sf.get(k)
        )
        if toward:
            lines.append(f"**{S['toward']}** {toward}.")
        if holdback:
            flag = f" {S['flag_partial']}" if (
                has_flag(sf.get("habit")) or has_flag(sf.get("anxiety"))
            ) else ""
            lines.append(f"**{S['holdback']}** {holdback}.{flag}")
        lines.append("")

    # Evidence health.
    ev = data.get("evidence", {}) or {}
    quotes = read_quotes(ev)
    weak = [w for w in _list(ev.get("weaknesses")) if w]
    lines.append(f"## {S['evidence']}")
    lines.append("")
    parts = [S["quotes_n"].format(n=len(quotes))]
    if ev.get("source"):
        parts.append(f"{S['source']}: {first_sentence(ev['source'])}")
    lines.append(". ".join(parts) + ".")
    if weak:
        lines.append(f"{S['weaknesses']}: {weak[0]}" + (f" (+{len(weak)-1})" if len(weak) > 1 else "") + ".")
    else:
        lines.append(f"{S['weaknesses']}: {S['none_weak']}.")
    lines.append("")

    # Load-bearing quote.
    q = load_bearing_quote(data, top)
    if q and q.get("text"):
        lines.append(f"## {S['quote']}")
        lines.append("")
        who = f" — {q['who']}" if q.get("who") else ""
        lines.append(f"> \"{q['text'].strip().strip(chr(34))}\"{who}")
        lines.append("")

    # Open questions.
    oq = [q for q in _list(data.get("open_questions")) if q]
    lines.append(f"## {S['open_q']}")
    lines.append("")
    if oq:
        lines.append(S["open_count"].format(n=len(oq), k=min(2, len(oq))))
        for q in oq[:2]:
            lines.append(f"- {q}")
    else:
        lines.append(S["no_open"])
    lines.append("")

    # Recommended next move (mechanical: worst-served outcome + its stage).
    lines.append(f"## {S['next_move']}")
    lines.append("")
    if top:
        worst = top[0]
        if worst["stage"]:
            lines.append(S["next_tmpl"].format(stage=worst["stage"], statement=worst["statement"]))
        else:
            lines.append(S["next_nostage"].format(statement=worst["statement"]))
    else:
        lines.append(S["no_odi"])
    lines.append("")

    return "\n".join(lines).rstrip() + "\n"


# --- corpus exec summary -----------------------------------------------------

def load_corpus(root):
    p = Path(root) / "corpus.json"
    if p.is_file():
        try:
            return json.loads(p.read_text())
        except (ValueError, OSError):
            return {}
    return {}


def shape_project(path):
    data = json.loads(Path(path).read_text())
    slug = Path(path).parent.name or data.get("name", "?")
    outs = scored_outcomes(data)
    quotes = read_quotes(data.get("evidence", {}))
    return {
        "slug": slug,
        "name": data.get("name", slug),
        "macro": data.get("macro"),
        "outcomes": outs,
        "n_quotes": len(quotes),
    }


def render_corpus_summary(projects, corpus, lang="en"):
    S = STRINGS.get(lang, STRINGS["en"])
    macro_names = {m.get("id"): m.get("name", m.get("id"))
                   for m in _list(corpus.get("macros")) if isinstance(m, dict)}
    lines = [f"# {S['corpus_title']}", ""]
    lines.append(f"{len(projects)} {S['projects']}.")
    lines.append("")

    # Group by macro, mean opp across all scored outcomes in the macro.
    groups = {}
    for p in projects:
        key = p["macro"] or None
        groups.setdefault(key, []).append(p)

    def mean_opp(projs):
        vals = [o["opp"] for pr in projs for o in pr["outcomes"] if o["opp"] is not None]
        return sum(vals) / len(vals) if vals else None

    ranked = sorted(
        groups.items(),
        key=lambda kv: (mean_opp(kv[1]) if mean_opp(kv[1]) is not None else -1),
        reverse=True,
    )
    lines.append(f"## {S['macros_h']}")
    lines.append("")
    for key, projs in ranked:
        label = macro_names.get(key, key) if key else S["unassigned"]
        mo = mean_opp(projs)
        mo_txt = f"{mo:.1f}" if mo is not None else "—"
        names = ", ".join(sorted(p["slug"] for p in projs))
        lines.append(f"- **{label}** ({S['mean_opp']} {mo_txt}) — {names}")
    lines.append("")

    # Corpus-wide top 5 outcomes.
    flat = [(p, o) for p in projects for o in p["outcomes"] if o["opp"] is not None]
    flat.sort(key=lambda po: po[1]["opp"], reverse=True)
    lines.append(f"## {S['corpus_top'].format(k=5)}")
    lines.append("")
    if flat:
        lines.append(f"| {S['col_project']} | {S['col_outcome']} | imp | sat | opp | tier |")
        lines.append("|---|---|---|---|---|---|")
        for p, o in flat[:5]:
            lines.append(f"| {p['slug']} | {o['statement']} | {o['imp']} | {o['sat']} | {o['opp']} | {o['tier']} |")
    else:
        lines.append(S["no_odi"])
    lines.append("")

    # Evidence-thin projects.
    thin = sorted((p for p in projects if p["n_quotes"] < 3), key=lambda p: p["n_quotes"])
    lines.append(f"## {S['thin_h']}")
    lines.append("")
    if thin:
        for p in thin:
            lines.append(f"- {S['thin_line'].format(slug=p['slug'], n=p['n_quotes'])}")
    else:
        lines.append(S["no_thin"])
    lines.append("")

    # Recommended next move — the single worst-served outcome across the corpus.
    lines.append(f"## {S['next_move']}")
    lines.append("")
    if flat:
        p, o = flat[0]
        stmt = f"{o['statement']} ({p['slug']})"
        if o["stage"]:
            lines.append(S["next_tmpl"].format(stage=o["stage"], statement=stmt))
        else:
            lines.append(S["next_nostage"].format(statement=stmt))
    else:
        lines.append(S["no_odi"])
    lines.append("")

    return "\n".join(lines).rstrip() + "\n"


# --- CLI ---------------------------------------------------------------------

def cmd_exec_summary(args):
    root = Path(os.path.expanduser(args.root))
    if args.all:
        bundles = find_bundles(root)
        if not bundles:
            print(f"No jtbd.json bundles under {root}", file=sys.stderr)
            return 1
        projects = [shape_project(b) for b in bundles]
        corpus = load_corpus(root)
        out_text = render_corpus_summary(projects, corpus, args.lang)
        out_path = Path(args.out) if args.out else root / "exec-summary.md"
    else:
        if not args.slug:
            print("Provide a <slug> or --all.", file=sys.stderr)
            return 2
        bundle = root / args.slug / "jtbd.json"
        if not bundle.is_file():
            print(f"No bundle at {bundle}", file=sys.stderr)
            return 1
        data = json.loads(bundle.read_text())
        out_text = render_exec_summary(data, args.lang)
        out_path = Path(args.out) if args.out else root / args.slug / "exec-summary.md"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(out_text)
    print(f"Wrote {out_path}")
    return 0


def build_parser():
    p = argparse.ArgumentParser(description="Generate reports from jtbd.json bundles.")
    sub = p.add_subparsers(dest="command", required=True)
    es = sub.add_parser("exec-summary", help="One-page executive summary.")
    es.add_argument("slug", nargs="?", help="Project slug under --root.")
    es.add_argument("--all", action="store_true", help="Whole-corpus summary.")
    es.add_argument("--root", default=str(DEFAULT_ROOT),
                    help=f"Corpus root (default {DEFAULT_ROOT}, from the corpus_root setting).")
    es.add_argument("--out", help="Output path (default <root>/<slug>/exec-summary.md).")
    es.add_argument("--lang", choices=["en", "ru"], default="en", help="Report chrome language.")
    es.set_defaults(func=cmd_exec_summary)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
