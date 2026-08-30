#!/usr/bin/env python3
"""Round-4 review of tron PR #3879 as Alexey: HTML (PR3879/alexey-review.html) + Markdown
(PR3879/alexey-review-4.md). Every comment carries a source snippet from the NEW head tree.

Data: round1_comments.json (round-1 text), status.json (per-id status at the new head,
produced from the workflow journal), and NEW below (round-2 comments authored here).
"""
import html, re, json, sys, os

SP = os.path.dirname(os.path.abspath(__file__))
HEAD = "/home/jhan/workspace/tron-amx"  # working tree: d176c88b3 + uncommitted doc/intel-amx.md
OUT_HTML = "/home/jhan/workspace/intel-AMX/PR3879/alexey-review.html"
OUT_MD = "/home/jhan/workspace/intel-AMX/PR3879/alexey-review-4.md"

PR = dict(num=3879, title="AMX software attention (default-off): QK/PV tile kernels + K-mirror arena",
          head="d176c88b3 (+ uncommitted doc/intel-amx.md)", prev="96b5a6c72", base="1407f48dd", files=16, add=2755, dele=37,
          url="https://github.com/positron-ai/tron/pull/3879", date="2026-08-25",
          delta_commit='d176c88b3 "Register t_amx_logit_ab DISABLED and inside BUILD_INGEST_MODELS" + the uncommitted edit of doc/intel-amx.md (+30/-22)')

R1 = {x["id"]: x for x in json.load(open(os.path.join(SP, "r4", "round3_comments.json")))}  # open comments after round 3 (R1/R2 carried + R3-xx)
ST = json.load(open(os.path.join(SP, "r4", "status.json")))  # id -> dict (working tree)
# Author decisions, one entry per review id (PR3879/triage.json): decision done|partial|ignore|defer|question,
# reason, commit, date, by. Shown under each item as "your triage: ..." and handed to the round's agents so a
# declined item gets the persona's predicted reply instead of being re-raised verbatim.
_TRIAGE_PATH = "/home/jhan/workspace/intel-AMX/PR3879/triage.json"
_TRIAGE = {k: v for k, v in json.load(open(_TRIAGE_PATH)).items() if not k.startswith("_")} if os.path.exists(_TRIAGE_PATH) else {}
TRIAGE = {k: f'{v["decision"]}' + (f' ({v["commit"]})' if v.get("commit") else "") + f' - {v["reason"]}' for k, v in _TRIAGE.items()}

# Round-2 follow-up sentences (his voice) appended to PARTIAL round-1 comments, keyed by id.
FOLLOWUP = {}
TRIAGE = {}
TRIAGE_PREDICTION = {}
# Round-1 comments to drop/merge in round 2 (id -> reason), e.g. superseded by a new comment.
DROP = {}
SNIP_OVERRIDE = {}  # id -> (start, end) when the agent's snippet range does not contain the anchor
# New round-2 comments: dict(file, line, snip=(start,end), text, tag, note, blocker)
NEW = []

VERDICT = "CHANGES_REQUESTED"
BODY = ""
TAKE = ""
FIXED_VOICE = {}  # id -> one-liner he would write on the resolved thread (rare)
EAGLE_HTML = ''
EAGLE_MD = ''
FIX = {}  # id -> dict(lines=(a,b), text=replacement, note=for jhan)

def load_round2_data():
    """Filled in by the block at the bottom (kept separate so the data is easy to edit)."""
    pass

# ---------------------------------------------------------------- helpers
def esc(s): return html.escape(s, quote=False)

def render_text(t):
    t = esc(t)
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", t)

_file_cache = {}
def src_lines(file):
    if file not in _file_cache:
        p = os.path.join(HEAD, file)
        _file_cache[file] = open(p, encoding="utf-8", errors="replace").read().split("\n") if os.path.exists(p) else None
    return _file_cache[file]

def snippet(file, start, end, anchor):
    lines = src_lines(file)
    if lines is None: return []
    n = len(lines)
    if not (1 <= start <= end <= n) or end - start > 14:
        start, end = max(1, anchor - 2), min(n, anchor + 3)
    return [(i, lines[i - 1]) for i in range(start, end + 1)]

def snippet_html(file, start, end, anchor):
    rows = snippet(file, start, end, anchor)
    if not rows: return ""
    body = "\n".join(f'<span class="ln{" hit" if i == anchor else ""}">{i:5d}</span>  {esc(l.rstrip())}' for i, l in rows)
    return f'<pre class="src">{body}</pre>'

def snippet_md(file, start, end, anchor):
    rows = snippet(file, start, end, anchor)
    if not rows: return ""
    lang = "markdown" if file.endswith(".md") else ("cmake" if file.endswith("CMakeLists.txt") else "cpp")
    body = "\n".join(f'{i:5d}{"*" if i == anchor else " "} {l.rstrip()}' for i, l in rows)
    return f"```{lang}\n{body}\n```"

def all_comments():
    """Ordered list of round-2 comments: carried-over open round-1 comments + NEW, grouped by file in review order."""
    out = []
    for cid, r in R1.items():
        s = ST.get(cid)
        if s is None or cid in DROP: continue
        if s["status"] in ("FIXED", "OBSOLETE"): continue
        text = r["text"]
        if cid in FOLLOWUP:
            text = text + "  " + FOLLOWUP[cid]
        note = f'{ {"R1": "round 1", "R2": "round 2", "R3": "round 3"}[cid[:2]] } ({cid}), {s["status"].lower().replace("_", " ")}'
        if s["status"] == "PARTIAL": note += ": " + s.get("remaining", "")
        if cid in TRIAGE:
            note += f' | your triage: {TRIAGE[cid]}'
            if cid in TRIAGE_PREDICTION: note += ' | persona prediction: ' + TRIAGE_PREDICTION[cid]
        snip = SNIP_OVERRIDE.get(cid, (s["snippet_start"], s["snippet_end"]))
        out.append(dict(id=cid, file=r["file"], line=s["new_line"], snip=snip,
                        text=text, tag=r["tag"], note=note, blocker=s.get("still_blocker", r["blocker"]), origin="carried", fix=FIX.get(cid)))
    for k, x in enumerate(NEW, 1):
        out.append(dict(id=f"R4-{k:02d}", origin="r4", fix=FIX.get(f"R4-{k:02d}"), **x))
    order = ["doc/intel-amx.md", "h/tron/kernels/amx_attn_iface.hpp", "h/tron/kernels/page_share_counters.hpp",
             "h/tron/models/kv_cache.hpp", "h/tron/models/model.hpp", "h/tron/models/self_attention.hpp",
             "h/tron/scheduler/full.hpp", "src/tron/CMakeLists.txt", "src/tron/kernels/amx_attn.cpp",
             "src/amx_fused_bench.cpp", "t/CMakeLists.txt", "t/t_amx_arena_leak.cpp", "t/t_amx_mirror.cpp",
             "t/t_amx_numerics.cpp", "t/t_llama_unit.cpp"]
    out.sort(key=lambda c: (order.index(c["file"]) if c["file"] in order else 99, c["line"]))
    return out

def fixed_rows():
    rows = []
    for cid, r in R1.items():
        s = ST.get(cid)
        if s and s["status"] in ("FIXED", "OBSOLETE"):
            ev = s.get("evidence", "")
            if cid in TRIAGE: ev += f" | your triage: {TRIAGE[cid]}"
            rows.append((cid, r["file"], s["new_line"], r["text"], s["status"], ev, FIXED_VOICE.get(cid, "")))
    return rows

def chart(counts):
    w, rowh, left, right = 980, 22, 300, 60
    n = len(counts); h = n * rowh + 40
    mx = max(c[1] + c[2] for c in counts) or 1
    scale = (w - left - right) / mx
    tot = sum(c[1] + c[2] for c in counts)
    p = [f'<svg viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="Open comments per file after round 4, {tot} total">']
    p.append(f'<text x="14" y="18" font-size="12.5" fill="#0b0b0b" font-weight="600">Open comments per file after round 4 ({tot}); carried over from rounds 1-3 vs new in round 4</text>')
    for i, (f, r1n, r2n, blk) in enumerate(counts):
        y = 34 + i * rowh
        p.append(f'<text x="{left-8}" y="{y+12}" font-size="11" fill="#52514e" text-anchor="end" font-family="ui-monospace,monospace">{esc(f)}</text>')
        w1 = r1n * scale; w2 = r2n * scale
        if r1n:
            p.append(f'<rect x="{left}" y="{y+3}" width="{w1:.1f}" height="14" rx="4" fill="#2a78d6"><title>{esc(f)}: {r1n} carried over from round 1</title></rect>')
        if r2n:
            p.append(f'<rect x="{left+w1+(2 if r1n else 0):.1f}" y="{y+3}" width="{max(w2-(2 if r1n else 0),1):.1f}" height="14" rx="4" fill="#eb6834"><title>{esc(f)}: {r2n} new in round 4</title></rect>')
        lab = f"{r1n + r2n}" + (f"  ({r2n} new)" if r2n else "") + (f"  [{blk} in body]" if blk else "")
        p.append(f'<text x="{left+w1+w2+6:.1f}" y="{y+14}" font-size="11" fill="#0b0b0b">{esc(lab)}</text>')
    p.append(f'<line x1="{left}" y1="30" x2="{left}" y2="{h-6}" stroke="#d8d6d0" stroke-width="1"/>')
    # legend (2 series)
    ly = h - 2
    p.append(f'<rect x="{left}" y="{ly-10}" width="10" height="10" rx="2" fill="#2a78d6"/><text x="{left+14}" y="{ly-1}" font-size="11" fill="#52514e">carried over from rounds 1-3</text>')
    p.append(f'<rect x="{left+190}" y="{ly-10}" width="10" height="10" rx="2" fill="#eb6834"/><text x="{left+204}" y="{ly-1}" font-size="11" fill="#52514e">new in round 4</text>')
    p.append('</svg>')
    return "\n".join(p)

CSS = """
body { background:#ffffff; color:#0b0b0b; font-family:system-ui,sans-serif; max-width:1080px; margin:24px auto; padding:0 20px; line-height:1.5; }
h1 { font-size:23px; margin-bottom:2px; }
h2 { font-size:17px; margin-top:30px; border-bottom:1px solid #e1e0d9; padding-bottom:6px; }
h3 { font-size:14px; margin:18px 0 6px 0; font-family:ui-monospace,monospace; }
p.sub { color:#52514e; margin-top:0; }
figure { margin:12px 0 4px 0; overflow-x:auto; }
figcaption { font-size:12.5px; color:#52514e; }
table { border-collapse:collapse; font-size:13px; width:100%; }
th,td { border:1px solid #d8d6d0; padding:5px 8px; text-align:left; vertical-align:top; }
th { background:#f4f3ef; }
code { background:#f4f3ef; padding:1px 4px; font-size:12px; }
.verdict { border:2px solid #e34948; border-radius:6px; padding:10px 14px; margin:14px 0; }
.verdict .state { font-weight:700; color:#e34948; font-family:ui-monospace,monospace; font-size:14px; }
.body { white-space:pre-wrap; font-size:14px; margin:8px 0 0 0; }
.cmt { border-top:1px solid #eeede8; padding:10px 0; }
.cmt .hdr { display:flex; gap:12px; align-items:baseline; font-size:12px; color:#52514e; font-family:ui-monospace,monospace; }
.cmt .hdr b { color:#0b0b0b; font-size:13px; }
.cmt .hdr .tag { background:#f4f3ef; border:1px solid #d8d6d0; border-radius:3px; padding:0 5px; }
.cmt .hdr .r2 { color:#eb6834; font-weight:600; }
.cmt.blk .hdr b { border-left:3px solid #e34948; padding-left:5px; }
.cmt .txt { white-space:pre-wrap; font-size:14px; margin:6px 0; }
.cmt .note { font-size:11.5px; color:#52514e; }
pre.src { background:#f7f6f2; border:1px solid #e1e0d9; border-radius:4px; padding:6px 8px; font-size:11.5px; line-height:1.35; overflow-x:auto; margin:6px 0; white-space:pre; }
pre.src .ln { color:#9a988f; }
pre.src .ln.hit { color:#d95f02; font-weight:700; }
.fixhdr { font-size:12px; color:#008300; font-weight:600; margin-top:6px; }
pre.fix { background:#f0f8f0; border:1px solid #b8dcb8; border-left:4px solid #008300; border-radius:4px; padding:6px 8px; font-size:12px; line-height:1.4; overflow-x:auto; margin:4px 0; white-space:pre-wrap; }
.take { background:#f4f3ef; border-left:4px solid #d95f02; padding:8px 12px; font-size:14px; margin:12px 0; }
.lineage { background:#f4f3ef; border-left:4px solid #7570b3; padding:8px 12px; font-size:13px; margin:12px 0; }
details { margin:10px 0; } summary { cursor:pointer; font-size:14px; }
pre.raw { background:#f4f3ef; padding:10px; font-size:12px; overflow-x:auto; white-space:pre-wrap; }
dl dt { font-weight:600; margin-top:8px; } dl dd { margin-left:0; font-size:13.5px; }
ul.plain { padding-left:18px; }
"""

GLOSSARY = [
  ("canonical-K", "Project shorthand: K kept in today's original single-copy row-major storage and read as-is by the AVX dotter, the FPGA DMA and the canonical AMX kernel."),
  ("mirror / k_vnni", "A second, derived copy of K in the pair-interleaved (VNNI) layout the AMX B operand wants. The mirror <em>formulation</em> originates from Bill's PR #2934 (<code>k_vnni</code>); the parallel-arena implementation and all numbers in PR #3879 are ours (<code>jhan-amx-p0</code>)."),
  ("parallel arena", "Ordinary (non-DMA) RAM owned by the <code>book</code>, sized kv_bytes/2, one mirror plane per (storage slot, kv_head, page). Not the book's DMA <code>arena_data</code>."),
  ("shape gate / <code>amx_attn::shape_ok</code>", "New in cc8a86bb3: <code>head_size == 128 &amp;&amp; kv_mul == 4</code> in one function, used by the dispatch, the <code>save_k</code> write-through and (via <code>amx_mirror_eligible</code>) the arena allocation."),
  ("<code>amx_mirror_eligible</code>", "New in cc8a86bb3: (a) a constexpr function over a plugin's <code>attention_kernels</code> (true if any kernel passes the shape gate); (b) a <code>bool</code> carried on every <code>node_base</code> and passed to <code>book::try_create</code>; (c) a constructor parameter of <code>book</code>. The 3-argument <code>book</code>/<code>try_create</code> forms default it to true."),
  ("storage view / <code>kv_blocks_alias</code>", "<code>book::set_storage_view()</code> repoints <code>kv_blocks_alias</code> so logical slot 0 resolves to the extra EAGLE physical slot for the whole draft forward; canonical K accessors follow it, the mirror accessors do not (still true at cc8a86bb3)."),
  ("EAGLE", "Speculative-decoding draft model that runs its own forward through the same books, storing its layer-0 K/V in an extra physical storage slot after the validator's logical slots."),
  ("ready / pending pass", "Software attention runs twice per operation: over pages that receive no K/V this forward (ready), then after <code>upstream_kvs_ready.wait()</code> over pages being written this forward (pending)."),
  ("RX worker", "Per-card driver thread running DMA completion callbacks; <code>rope_k</code>/<code>save_k</code> execute there."),
  ("Note [Title]", "GHC-style named long comment, checked by <code>make lint-notes</code>."),
  ("A3, B6, ... tags", "Item numbers from <code>~/workspace/reviewers/alexey.md</code> section 1; shown only in the verification line, never in the comment text."),
]

def build_html(comments, fixed, method, clean):
    order = []
    for c in comments:
        if c["file"] not in order: order.append(c["file"])
    counts = [(f, sum(1 for c in comments if c["file"] == f and c["origin"] == "carried"),
                  sum(1 for c in comments if c["file"] == f and c["origin"] == "r4"),
                  sum(1 for c in comments if c["file"] == f and c["blocker"])) for f in order]
    nb = sum(1 for c in comments if c["blocker"]); nnew = sum(1 for c in comments if c["origin"] == "r4")
    o = ['<meta charset="utf-8">', '<title>PR 3879 review as Alexey, round 4</title>', f"<style>{CSS}</style>"]
    o.append(f'<h1>Review of PR #{PR["num"]} as Alexey would write it &mdash; round 4</h1>')
    o.append(f'<p class="sub"><a href="{PR["url"]}">positron-ai/tron#{PR["num"]}</a> &mdash; {esc(PR["title"])} &mdash; head <code>{PR["head"]}</code> (round 3 reviewed <code>{PR["prev"]}</code>; delta = {esc(PR["delta_commit"])}, 3 files, +46/&minus;26), base <code>{PR["base"]}</code>, {PR["files"]} files, +{PR["add"]}/&minus;{PR["dele"]}. Written {PR["date"]}. Rounds 1-3 are archived as <code>alexey-review-1.html</code> / <code>-2.html</code> / <code>-3.html</code>; the Markdown twin of this page is <code>alexey-review-4.md</code>. '
             f'Each comment shows the source lines it refers to (from the working tree; the anchored line is marked); the small grey line under each comment is the verification record for you and is not part of the review.</p>')
    o.append('<div class="lineage">Lineage note: &ldquo;mirror&rdquo; names the formulation S = Q&middot;K<sup>T</sup> read from a second, VNNI-interleaved copy of K, which originates from Bill&rsquo;s PR #2934 (<code>k_vnni</code>); the parallel-arena implementation and all numbers in PR #3879 are ours (<code>jhan-amx-p0</code>). &ldquo;canonical-K&rdquo; = K in today&rsquo;s original single-copy storage, read as-is.</div>')
    o.append('<h2>1. Verdict</h2>')
    o.append(f'<div class="verdict"><span class="state">{VERDICT}</span><div class="body">{render_text(BODY)}</div></div>')
    o.append(f'<div class="take">{TAKE.replace("__F__", str(len(fixed))).replace("__O__", str(len(comments)-nnew)).replace("__N__", str(nnew))}</div>')

    o.append(EAGLE_HTML)
    o.append('<h2>2. Resolved by d176c88b3 + the doc edit</h2>')
    o.append('<p class="sub">Open comments the delta addressed. He would resolve these threads without text; the few one-liners he might leave are in the last column.</p>')
    o.append('<table><tr><th>comment</th><th>where (working tree)</th><th>what was asked</th><th>how it was addressed</th><th>his reply, if any</th></tr>')
    for cid, f, ln, text, status, ev, voice in fixed:
        short = text if len(text) < 220 else text[:217] + "..."
        o.append(f'<tr><td>{cid}<br><span style="color:#52514e">{status.lower()}</span></td><td><code>{esc(f)}:{ln}</code></td><td>{render_text(short)}</td><td style="font-size:12px">{esc(ev)}</td><td>{render_text(voice)}</td></tr>')
    o.append('</table>')

    o.append('<h2>3. Where the open comments land</h2>')
    o.append('<figure>' + chart(counts) + f'<figcaption>{len(comments)} open comments over {len(order)} files: {len(comments)-nnew} carried over from rounds 1-3 (blue) and {nnew} new on the delta (orange). {nb} are cited in the body as blockers. Files with no open comment: <code>t/t_amx_logit_ab.cpp</code> (covered under <code>t/CMakeLists.txt</code>).</figcaption></figure>')

    o.append('<h2>4. Open comments (carried over + new in round 4)</h2>')
    o.append('<p class="sub">Line numbers are in the working tree (<code>d176c88b3</code> + the uncommitted <code>doc/intel-amx.md</code>). Carried-over comments keep their earlier text (a GitHub thread stays as written); where the commits addressed a comment in part, one follow-up sentence is appended. New comments are marked <span style="color:#eb6834;font-weight:600">new</span>.</p>')
    for f in order:
        o.append(f'<h3>{esc(f)}</h3>')
        for c in [x for x in comments if x["file"] == f]:
            cls = "cmt blk" if c["blocker"] else "cmt"
            newmark = '<span class="r2">new</span>' if c["origin"] == "r4" else f'<span>{c["id"]}</span>'
            o.append(f'<div class="{cls}"><div class="hdr"><b>:{c["line"]}</b>{newmark}<span class="tag">{esc(c["tag"])}</span></div>')
            o.append(snippet_html(f, c["snip"][0], c["snip"][1], c["line"]))
            o.append(f'<div class="txt">{render_text(c["text"])}</div>')
            if c.get("fix"):
                fx = c["fix"]
                o.append(f'<div class="fixhdr">Suggested fix (added at your request) - replace lines {fx["lines"][0]}-{fx["lines"][1]} with:</div>')
                o.append(f'<pre class="fix">{esc(fx["text"])}</pre>')
                o.append(f'<div class="note">fix note: {esc(fx["note"])}</div>')
            o.append(f'<div class="note">{esc(c["note"])}</div></div>')

    o.append('<h2>5. Checked and clean in the delta</h2><table><tr><th>area</th><th>what was verified</th><th>source</th></tr>')
    for a, b, s in clean: o.append(f'<tr><td>{esc(a)}</td><td>{esc(b)}</td><td>{esc(s)}</td></tr>')
    o.append('</table>')
    o.append('<h2>6. Glossary</h2><dl>')
    for k, v in GLOSSARY: o.append(f'<dt>{k}</dt><dd>{v}</dd>')
    o.append('</dl>')
    o.append('<h2>7. Method and limits</h2><ul class="plain">')
    for m in method: o.append(f'<li>{m}</li>')
    o.append('</ul>')
    o.append('<details><summary>All open comments as plain text (GitHub markdown, for copy-paste)</summary><pre class="raw">')
    o.append(esc(f"REVIEW: {VERDICT}\n\n{BODY}\n\n"))
    for c in comments: o.append(esc(f"{c['file']}:{c['line']}\n{c['text']}\n\n"))
    o.append('</pre></details>')
    return "\n".join(o)

def build_md(comments, fixed, method, clean):
    L = []
    L.append(f"# Review of PR #{PR['num']} as Alexey would write it - round 4\n")
    L.append(f"{PR['url']} - {PR['title']}  ")
    L.append(f"Head `{PR['head']}` (round 3 reviewed `{PR['prev']}`; delta = {PR['delta_commit']}, 3 files, +46/-26); base `{PR['base']}`; {PR['files']} files, +{PR['add']}/-{PR['dele']}. Written {PR['date']}. HTML twin: `alexey-review.html`; rounds 1-3 archived as `alexey-review-1.html` / `-2.html` / `-3.html`.\n")
    L.append("Lineage note: \"mirror\" names the formulation S = Q.K^T read from a second, VNNI-interleaved copy of K, which originates from Bill's PR #2934 (`k_vnni`); the parallel-arena implementation and all numbers in PR #3879 are ours (`jhan-amx-p0`). \"canonical-K\" = K in today's original single-copy storage, read as-is.\n")
    L.append("Each comment shows the source lines it refers to (working tree: d176c88b3 + the uncommitted doc/intel-amx.md; the anchored line is marked with `*`). The line starting `Verification:` is the evidence record for jhan, not part of the review.\n")
    L.append(f"## 1. Verdict\n\n**{VERDICT}**\n\n{BODY}\n")
    L.append(EAGLE_MD)
    L.append("## 2. Resolved by d176c88b3 + the doc edit\n")
    L.append("| comment | where (working tree) | what was asked | how it was addressed | his reply, if any |\n|---|---|---|---|---|")
    for cid, f, ln, text, status, ev, voice in fixed:
        short = (text if len(text) < 220 else text[:217] + "...").replace("|", "\\|").replace("\n", " ")
        ev2 = ev.replace("|", "\\|").replace("\n", " ")
        L.append(f"| {cid} ({status.lower()}) | `{f}:{ln}` | {short} | {ev2} | {voice} |")
    L.append("")
    nnew = sum(1 for c in comments if c["origin"] == "r4")
    L.append(f"## 3. Open comments ({len(comments)}: {len(comments)-nnew} carried over from rounds 1-3, {nnew} new in round 4)\n")
    L.append("Carried-over comments keep their earlier text; where the commits addressed a comment in part, one follow-up sentence is appended. New comments are marked **new**. A leading `[blocker]` marks the comments the body names.\n")
    cur = None
    for c in comments:
        if c["file"] != cur:
            cur = c["file"]; L.append(f"### {cur}\n")
        mark = "**new** " if c["origin"] == "r4" else f"{c['id']} "
        blk = "[blocker] " if c["blocker"] else ""
        L.append(f"#### {blk}`{c['file']}:{c['line']}` {mark}({c['tag']})\n")
        L.append(snippet_md(c["file"], c["snip"][0], c["snip"][1], c["line"]))
        L.append("")
        L.append(c["text"])
        L.append("")
        if c.get("fix"):
            fx = c["fix"]
            fence = "````" if "```" in fx["text"] else "```"
            L.append(f"**Suggested fix** (added at your request) - replace lines {fx['lines'][0]}-{fx['lines'][1]} with:")
            L.append("")
            L.append(f"{fence}suggestion\n{fx['text']}\n{fence}")
            L.append("")
            L.append(f"_Fix note: {fx['note']}_\n")
        L.append(f"_Verification: {c['note']}_\n")
    L.append("## 4. Checked and clean in the delta\n")
    L.append("| area | what was verified | source |\n|---|---|---|")
    for a, b, s in clean:
        b2 = b.replace("|", "\\|")
        L.append(f"| {a} | {b2} | {s} |")
    L.append("")
    L.append("## 5. Glossary\n")
    for k, v in GLOSSARY:
        L.append(f"- **{re.sub(r'<[^>]+>','',k)}** - {html.unescape(re.sub(r'<[^>]+>','',v))}")
    L.append("")
    L.append("## 6. Method and limits\n")
    for m in method: L.append(f"- {html.unescape(re.sub(r'<[^>]+>','',m))}")
    L.append("")
    return "\n".join(L)

def main(method, clean):
    comments = all_comments()
    fixed = fixed_rows()
    method = [m.replace("__N__", str(len(comments))).replace("__F__", str(len(fixed))) for m in method]
    out = build_html(comments, fixed, method, clean)
    # HTML deliverables are pure ASCII + entities (mojibake rule); agent-supplied text may carry UTF-8.
    out = out.encode("ascii", "xmlcharrefreplace").decode("ascii")
    open(OUT_HTML, "w").write(out)
    md = build_md(comments, fixed, method, clean)
    open(OUT_MD, "w").write(md)
    print(f"wrote {OUT_HTML} ({len(out)} bytes) and {OUT_MD} ({len(md)} bytes); open={len(comments)} (new={sum(1 for c in comments if c['origin']=='r4')}), resolved={len(fixed)}")

if __name__ == "__main__":
    _loaded_triage = dict(TRIAGE)
    exec(open(os.path.join(SP, "r4", "round4_data.py")).read())  # sets BODY, NEW, FOLLOWUP, DROP, FIXED_VOICE, METHOD, CLEAN
    if not TRIAGE: TRIAGE = _loaded_triage  # data file may leave TRIAGE empty; the json is the source of truth
    main(METHOD, CLEAN)
