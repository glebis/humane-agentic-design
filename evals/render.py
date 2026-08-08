#!/usr/bin/env python3
"""Render an eval report from a spec. One renderer, many reports.

    python3 render.py spec.json -o report.html
    python3 render.py spec.json -o report.html --serve

WHY ONE RENDERER. The reference implementation this borrows its reporting
discipline from (confide) has `make_report_synth.py`, `make_report_science.py`,
`make_report_long.py`, `make_report_texture.py`, `make_report_master.py` and
more — one script per report, each a copy of the last with the data edited in.
Every fix to a chart default has to be made in ten places, and in practice is
made in one. This module exists so a new pathway writes a JSON spec and gets a
report, rather than forking an HTML file.

THE SPEC is a dict:

    {
      "title": "...", "subtitle": "...",
      "tags": ["4 SEEDS", "n=4 PER ARM"],
      "lede": ["paragraph", "paragraph"],
      "status": [{"label","value","note","tone"}],       # optional KPI strip
      "sections": [
        {"id","title","state_line",
         "blocks": [ ... ]}
      ],
      "footer": "..."
    }

BLOCKS are typed and each one owns its own HTML. Adding a block type is the only
way to add a visual element — that keeps the vocabulary small and every report
recognisably the same document.

    {"type":"prose",   "html": "<p>…</p>"}
    {"type":"aside",   "main": [...blocks], "notes": [["Bold lead","text"], ...]}
    {"type":"cards",   "cards": [{"label","value","delta","note","tone"}]}
    {"type":"flyout",  "lead": "…", "html": "…"}
    {"type":"chart",   "id","kind":"bar","labels":[],"datasets":[{"label","data"}],
                       "axis":"rate|count","horizontal":bool,"caption":"…"}
    {"type":"table",   "headers":[], "rows":[[...]], "tones":[[...]], "caption":"…"}
    {"type":"ornament"}

TONES are semantic, never decorative: "win" (green), "lose" (red), "flat"
(muted). A cell with no tone is plain. The renderer refuses an unknown tone
rather than silently dropping the class, because a finding coloured by accident
is worse than one not coloured at all.

Design system: Tufte-style, per ~/.claude/skills/tufte-report — EB Garamond for
prose, Monaspace Argon for every number, warm-white ground, no chart junk.
Python standard library only.
"""

import argparse
import html as html_mod
import json
import subprocess
import sys
from pathlib import Path

TONES = {"win", "lose", "flat", ""}

CSS = """
  @font-face { font-family:'Monaspace Argon';
    src:url('https://cdn.jsdelivr.net/gh/githubnext/monaspace@v1.101/fonts/webfonts/MonaspaceArgon-Regular.woff2') format('woff2');
    font-weight:400; font-display:swap; }
  :root{
    --ink:#1a1a1a; --ink-light:#555; --ink-muted:#888;
    --bg:#fffff8; --bg-aside:#f9f6ee; --accent:#a00; --rule:#ccc;
    --status-red:#a02a2a; --status-green:#2a7a3a;
    --mono:'Monaspace Argon',ui-monospace,SFMono-Regular,Menlo,monospace;
  }
  *{box-sizing:border-box}
  body{background:var(--bg);color:var(--ink);font-family:'EB Garamond',Georgia,serif;
    font-size:18px;line-height:1.6;max-width:1200px;margin:0 auto;padding:2rem 1.5rem 4rem}
  h1{font-size:2.2rem;font-weight:400;font-variant:small-caps;margin:0 0 .3rem}
  h2{font-size:1.5rem;font-weight:400;font-variant:small-caps;margin:0}
  .subtitle{font-size:1.15rem;color:var(--ink-light);font-style:italic;margin:0 0 1rem}
  .tags{font-family:var(--mono);font-size:.65rem;color:var(--rule);letter-spacing:.06em;margin-bottom:2rem}
  .tags span{margin-right:1.2rem}
  .lede{font-size:1.25rem;line-height:1.6}
  .lede::first-letter{float:left;font-size:3.4rem;line-height:.82;padding:.1rem .5rem .1rem 0;color:#c45a28}
  .toc-layout{display:grid;grid-template-columns:1fr 180px;gap:2rem;align-items:start}
  .toc{font-size:.8rem;line-height:1.9;border-left:1px solid var(--rule);padding-left:1rem;position:sticky;top:1.5rem}
  .toc a{color:var(--ink-light);text-decoration:none;display:block}
  .toc a:hover{color:#c45a28}
  .toc .toc-title{font-variant:small-caps;color:var(--ink-muted);letter-spacing:.06em;margin-bottom:.4rem}
  .status-strip{display:grid;border-top:1px solid var(--ink);border-bottom:1px solid var(--ink);margin:2rem 0}
  .status-cell{padding:1rem 1.2rem;border-right:1px solid var(--rule)}
  .status-cell:last-child{border-right:0}
  .status-label{font-variant:small-caps;font-size:.82rem;color:var(--ink-muted);letter-spacing:.05em}
  .status-value{font-family:var(--mono);font-size:1.5rem;font-variant-numeric:tabular-nums;margin:.2rem 0}
  .status-note{font-size:.8rem;color:var(--ink-light);font-style:italic;line-height:1.35}
  .cards{display:grid;gap:1.5rem;margin:2rem 0}
  .card{border:1px solid var(--rule);padding:1.1rem 1.2rem;transition:border-color .3s ease,box-shadow .3s ease}
  .card:hover{border-color:var(--ink-muted);box-shadow:0 1px 6px rgba(0,0,0,.05)}
  .card .label{font-variant:small-caps;font-size:.85rem;color:var(--ink-muted);letter-spacing:.05em}
  .card .big{font-family:var(--mono);font-size:2.6rem;letter-spacing:-.02em;line-height:1.1;margin:.3rem 0}
  .card .delta{font-family:var(--mono);font-size:.8rem;color:var(--ink-light)}
  .card .note{font-size:.85rem;color:var(--ink-light);font-style:italic;margin-top:.5rem;line-height:1.4}
  .aside-container{display:grid;grid-template-columns:1fr 280px;gap:2rem;align-items:start;margin:1.5rem 0}
  .aside{font-size:.85rem;line-height:1.5;font-style:italic;color:var(--ink-light);border-left:1px solid var(--rule);padding-left:1rem}
  .aside p{margin:0 0 .8rem}
  .aside b{font-style:normal;color:var(--ink)}
  .state-line{font-size:1.5rem;line-height:1.45;font-style:italic;color:var(--ink-light);margin:1.5rem 0 2rem}
  .flyout{background:var(--bg-aside);border:1px solid var(--rule);padding:1rem 1.2rem;margin:1.5rem 0;font-size:.92rem;line-height:1.55}
  .flyout::before{content:"\\2726";color:var(--accent);margin-right:.5rem}
  .flyout b{font-variant:small-caps;letter-spacing:.03em}
  .chart-wrap{margin:2rem 0;padding:0 5%}
  .caption{font-size:.82rem;font-style:italic;color:var(--ink-muted);text-align:center;margin-top:.6rem}
  .table-wrapper{overflow-x:auto;margin:1.5rem 0}
  table{border-collapse:collapse;width:100%}
  th{font-variant:small-caps;font-size:.92rem;color:var(--ink-muted);font-weight:400;letter-spacing:.04em;
     text-align:left;border-bottom:1px solid var(--ink);padding:.4rem .6rem}
  td{font-family:var(--mono);font-size:.85rem;font-variant-numeric:tabular-nums;padding:.4rem .6rem;border-bottom:1px solid #eee}
  td.text{font-family:'EB Garamond',Georgia,serif;font-size:.95rem}
  tbody tr:hover td{background:#f1ecdc}
  .win{color:var(--status-green)} .lose{color:var(--status-red)} .flat{color:var(--ink-muted)}
  .ornament{font-family:var(--mono);font-size:.9rem;color:var(--rule);text-align:center;margin:2rem 0;letter-spacing:.3em}
  .back{float:right;font-size:.8rem;color:var(--ink-muted);text-decoration:none}
  .back:hover{color:#c45a28}
  section{margin-top:2.5rem}
  footer{margin-top:4rem;padding-top:1rem;border-top:1px solid var(--rule);font-size:.8rem;color:var(--ink-muted);font-family:var(--mono)}
  .reveal{opacity:0;transform:translateY(16px);transition:opacity .6s cubic-bezier(.25,.1,.25,1),transform .6s cubic-bezier(.25,.1,.25,1)}
  .reveal.in{opacity:1;transform:none}
  @media (prefers-reduced-motion:reduce){.reveal{opacity:1;transform:none;transition:none}*{transition:none!important}}
  @media (max-width:800px){
    .toc-layout,.aside-container,.cards,.status-strip{grid-template-columns:1fr!important}
    .toc{position:static;border-left:0;border-top:1px solid var(--rule);padding:1rem 0 0}
    .status-cell{border-right:0;border-bottom:1px solid var(--rule)}
    .chart-wrap{padding:0}
    .hide-mobile{display:none}
  }
"""


def esc(text):
    return html_mod.escape(str(text), quote=False)


def _tone(value):
    if value not in TONES:
        raise ValueError(
            f"unknown tone {value!r}; use one of {sorted(TONES - {''})} or omit it. "
            "Refusing rather than dropping the class — a number coloured by "
            "accident misleads worse than one left plain."
        )
    return f' class="{value}"' if value else ""


def block_prose(b, charts):
    return b["html"]


def block_ornament(b, charts):
    return '<div class="ornament">:::</div>'


def block_flyout(b, charts):
    lead = f"<b>{esc(b['lead'])}</b> " if b.get("lead") else ""
    return f'<div class="flyout">{lead}{b["html"]}</div>'


def block_cards(b, charts):
    cards = b["cards"]
    out = [f'<div class="cards" style="grid-template-columns:repeat({len(cards)},1fr)">']
    for c in cards:
        out.append('<div class="card">')
        out.append(f'<div class="label">{esc(c["label"])}</div>')
        out.append(f'<div class="big{" " + c["tone"] if c.get("tone") else ""}">{esc(c["value"])}</div>')
        if c.get("delta"):
            out.append(f'<div class="delta">{esc(c["delta"])}</div>')
        if c.get("note"):
            out.append(f'<div class="note">{esc(c["note"])}</div>')
        out.append("</div>")
    out.append("</div>")
    return "\n".join(out)


def block_aside(b, charts):
    main = "\n".join(render_block(x, charts) for x in b.get("main", []))
    notes = "".join(
        f"<p><b>{esc(lead)}</b> {body}</p>" for lead, body in b.get("notes", [])
    )
    return (f'<div class="aside-container"><div>{main}</div>'
            f'<div class="aside">{notes}</div></div>')


def block_table(b, charts):
    head = "".join(f"<th>{esc(h)}</th>" for h in b["headers"])
    rows = []
    tones = b.get("tones") or []
    for i, row in enumerate(b["rows"]):
        cells = []
        for j, cell in enumerate(row):
            tone = tones[i][j] if i < len(tones) and j < len(tones[i]) else ""
            text_cls = " text" if not str(cell).replace(".", "").replace("-", "").isdigit() else ""
            cls = _tone(tone)
            if text_cls:
                cls = f' class="text{" " + tone if tone else ""}"' if tone else ' class="text"'
            cells.append(f"<td{cls}>{esc(cell)}</td>")
        rows.append("<tr>" + "".join(cells) + "</tr>")
    caption = f'<p class="caption">{esc(b["caption"])}</p>' if b.get("caption") else ""
    return (f'<div class="table-wrapper"><table><thead><tr>{head}</tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div>{caption}')


def block_chart(b, charts):
    charts.append(b)
    caption = f'<p class="caption">{esc(b["caption"])}</p>' if b.get("caption") else ""
    height = b.get("height", 150)
    return f'<div class="chart-wrap"><canvas id="{b["id"]}" height="{height}"></canvas></div>{caption}'


BLOCKS = {
    "prose": block_prose, "ornament": block_ornament, "flyout": block_flyout,
    "cards": block_cards, "aside": block_aside, "table": block_table,
    "chart": block_chart,
}


def render_block(b, charts):
    kind = b.get("type")
    if kind not in BLOCKS:
        raise ValueError(f"unknown block type {kind!r}; known: {sorted(BLOCKS)}")
    return BLOCKS[kind](b, charts)


def chart_js(charts):
    """Chart.js configs. Rates and counts never share an axis.

    A dual axis draws two incomparable quantities at the same visual height. The
    first version of this report did exactly that by accident and the bars were
    not comparable, so `axis` is declared per chart and a rate chart is pinned
    to 0..1.
    """
    out = []
    for c in charts:
        datasets = ",".join(
            '{label:%s,data:%s,backgroundColor:%s}' % (
                json.dumps(d["label"]), json.dumps(d["data"]),
                json.dumps(["#c45a28", "rgba(42,80,140,0.7)", "#2a7a5a"][i % 3]))
            for i, d in enumerate(c["datasets"])
        )
        is_rate = c.get("axis", "rate") == "rate"
        value_axis = "x" if c.get("horizontal") else "y"
        other_axis = "y" if c.get("horizontal") else "x"
        scale = (f'{value_axis}:{{beginAtZero:true,'
                 + ("max:1.0," if is_rate else "")
                 + f'title:{{display:true,text:{json.dumps(c.get("axis_label", "rate (0-1)" if is_rate else "count"))}}}}},'
                 + f'{other_axis}:{{grid:{{display:false}}}}')
        out.append(
            "new Chart(document.getElementById(%s),{type:'bar',"
            "data:{labels:%s,datasets:[%s]},"
            "options:{responsive:true,maintainAspectRatio:true,%s"
            "scales:{%s},plugins:{legend:{position:'top',align:'end'}}}});"
            % (json.dumps(c["id"]), json.dumps(c["labels"]), datasets,
               "indexAxis:'y'," if c.get("horizontal") else "", scale)
        )
    return "\n".join(out)


def render(spec):
    charts = []
    tags = "".join(f"<span>{esc(t)}</span>" for t in spec.get("tags", []))

    status = ""
    if spec.get("status"):
        cells = "".join(
            f'<div class="status-cell"><div class="status-label">{esc(s["label"])}</div>'
            f'<div class="status-value{" " + s["tone"] if s.get("tone") else ""}">{esc(s["value"])}</div>'
            f'<div class="status-note">{esc(s.get("note", ""))}</div></div>'
            for s in spec["status"]
        )
        status = (f'<div class="status-strip" style="grid-template-columns:'
                  f'repeat({len(spec["status"])},1fr)">{cells}</div>')

    lede = "".join(
        f'<p class="{"lede" if i == 0 else ""}">{p}</p>'
        for i, p in enumerate(spec.get("lede", []))
    )
    toc = "".join(
        f'<a href="#{s["id"]}">{esc(s.get("nav") or s["title"])}</a>'
        for s in spec["sections"]
    )

    body = []
    for s in spec["sections"]:
        body.append('<div class="ornament">:::</div>')
        body.append(f'<section id="{s["id"]}">')
        body.append(f'<h2>{esc(s["title"])} <a class="back" href="#">&#8593;</a></h2>')
        if s.get("state_line"):
            body.append(f'<p class="state-line">{esc(s["state_line"])}</p>')
        for b in s.get("blocks", []):
            body.append(render_block(b, charts))
        body.append("</section>")

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(spec["title"])}</title>
<link href="https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,500;0,600;1,400&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>{CSS}</style></head><body>
<h1>{esc(spec["title"])}</h1>
<p class="subtitle">{spec.get("subtitle", "")}</p>
<div class="tags">{tags}</div>
{status}
<div class="toc-layout"><div>{lede}</div>
<nav class="toc"><div class="toc-title">Contents</div>{toc}</nav></div>
{"".join(body)}
<footer>{esc(spec.get("footer", ""))}</footer>
<script>
Chart.defaults.font.family="'EB Garamond', Georgia, serif";
Chart.defaults.font.size=13;
Chart.defaults.color='#555';
Chart.defaults.scale.grid.color='#eee';
Chart.defaults.plugins.legend.labels.usePointStyle=false;
Chart.defaults.plugins.legend.labels.boxWidth=8;
Chart.defaults.plugins.legend.labels.boxHeight=8;
Chart.defaults.plugins.legend.labels.borderRadius=4;
{chart_js(charts)}
const io=new IntersectionObserver(e=>{{e.forEach(x=>{{if(x.isIntersecting){{x.target.classList.add('in');io.unobserve(x.target)}}}})}},{{threshold:.08}});
document.querySelectorAll('section,.cards,.status-strip').forEach(el=>{{el.classList.add('reveal');io.observe(el)}});
</script></body></html>
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("spec")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--serve", action="store_true",
                    help="serve the directory afterwards (Chart.js needs http, not file://)")
    ap.add_argument("--port", type=int, default=8055)
    args = ap.parse_args()

    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    out = Path(args.out)
    out.write_text(render(spec), encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size} bytes)")

    if args.serve:
        subprocess.Popen(
            [sys.executable, "-m", "http.server", str(args.port),
             "--bind", "127.0.0.1", "--directory", str(out.parent)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        print(f"http://127.0.0.1:{args.port}/{out.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
