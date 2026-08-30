#!/usr/bin/env python3
"""Round-5 review of tron PR #3879 as Alexey: HTML (PR3879/alexey-review.html) + Markdown
(PR3879/alexey-review-5.md). Every comment carries a source snippet from the head tree a5ef6576
with the anchored line marked.

Data (all in r5/): round4_comments.json (the 77 comments open after round 4, with their round-4
text and R4-tree lines), status.json (per-id status at a5ef6576, built by build_status5.py from the
verification workflow), round5_data.py (BODY, FOLLOWUP, NEW, FIX, FIXED_VOICE, METHOD, CLEAN authored
from the workflow output), carry.json (EAGLE background section + glossary carried from round 3/4).
"""
import html, re, json, os, subprocess, sys

SP = os.path.dirname(os.path.abspath(__file__))
R5 = os.path.join(SP, "r5")
HEAD = "/home/jhan/workspace/tron-amx"  # must be at a5ef6576, clean (checked in main)
HEAD_SHA = "234c02bde4bd41700dde901438ad4bddfca15943"
OUT_HTML = "/home/jhan/workspace/intel-AMX/PR3879/alexey-review.html"
OUT_MD = "/home/jhan/workspace/intel-AMX/PR3879/alexey-review-5.md"

PR = dict(num=3879, title="AMX software attention (default-off): QK/PV tile kernels + K-mirror arena",
          head="234c02bde", prev="d176c88b3", base="1407f48dd", files=14, add=1817, dele=37,
          url="https://github.com/positron-ai/tron/pull/3879", date="2026-08-25",
          delta_commit='ff7269a9f + 901f30d8e (delete src/amx_fused_bench.cpp; rewrite the numbers in Note [Mirror orientation] and three amx_attn.cpp comments), a5ef65761 + 234c02bde (a file since removed from the PR)',
          delta_stat='5 files, +47/-977, of which -732 is the deleted src/amx_fused_bench.cpp')

R4 = {x["id"]: x for x in json.load(open(os.path.join(R5, "round4_comments.json")))}  # open comments after round 4
ST = json.load(open(os.path.join(R5, "status.json")))  # id -> dict at a5ef6576
CARRY = json.load(open(os.path.join(R5, "carry.json")))

# Filled by r5/round5_data.py (exec'd at the bottom).
FOLLOWUP = {}           # id -> one follow-up sentence in his voice, appended to a PARTIAL comment
TEXT_EDIT = {}          # id -> (old, new) substitution applied to a carried comment's text (recorded in the verification line)
TRIAGE = {}
TRIAGE_PREDICTION = {}
DROP = {}               # id -> reason (comment dropped/merged this round)
SNIP_OVERRIDE = {}      # id -> (start, end)
NEW = []                # dict(file, line, snip=(a,b), text, tag, note, blocker, reply_to=None)
VERDICT = "CHANGES_REQUESTED"
BODY = ""
TAKE = ""
FIXED_VOICE = {}        # id -> one-liner he would leave on a resolved thread (rare)
FIX = {}                # id -> dict(lines=(a,b), text, note)  suggested replacement text (added at jhan's request)
EAGLE_HTML = CARRY["EAGLE_HTML"]
EAGLE_MD = CARRY["EAGLE_MD"]
CODEX = []              # list of dict(id, path, line, author, body) - the bot review's inline comments, for the record

ROUND_NAME = {"R1": "round 1", "R2": "round 2", "R3": "round 3", "R4": "round 4", "R5": "round 5"}
HIDDEN_FILES = {"doc/intel-amx.md"}  # removed from the PR in 234c02bde; comments on it are not carried or listed

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
    if lines is None or anchor <= 0: return []
    n = len(lines)
    if not (1 <= start <= anchor <= end <= n) or end - start > 14:
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

ORDER = ["h/tron/kernels/amx_attn_iface.hpp", "h/tron/kernels/page_share_counters.hpp",
         "h/tron/models/kv_cache.hpp", "h/tron/models/model.hpp", "h/tron/models/self_attention.hpp",
         "h/tron/scheduler/full.hpp", "src/tron/CMakeLists.txt", "src/tron/kernels/amx_attn.cpp",
         "t/CMakeLists.txt", "t/t_amx_arena_leak.cpp", "t/t_amx_logit_ab.cpp", "t/t_amx_mirror.cpp",
         "t/t_amx_numerics.cpp", "t/t_llama_unit.cpp"]

def all_comments():
    """Open comments this round: carried-over open round-1..4 comments + NEW, grouped by file in review order."""
    out = []
    for cid, r in R4.items():
        s = ST.get(cid)
        if s is None or cid in DROP or r["file"] in HIDDEN_FILES: continue
        if s["status"] in ("FIXED", "OBSOLETE"): continue
        text = r["text"]
        if cid in TEXT_EDIT:
            assert TEXT_EDIT[cid][0] in text, cid
            text = text.replace(TEXT_EDIT[cid][0], TEXT_EDIT[cid][1])
        if cid in FOLLOWUP:
            text = text + "  " + FOLLOWUP[cid]
        note = f'{ROUND_NAME[cid[:2]]} ({cid}), {s["status"].lower().replace("_", " ")}'
        if cid in TEXT_EDIT: note += " | text edited in round 5: " + TEXT_EDIT[cid][2]
        if s["status"] == "PARTIAL" and s.get("remaining"): note += ": " + s["remaining"]
        if s.get("evidence"): note += " | evidence: " + s["evidence"]
        if cid in TRIAGE:
            note += f' | your triage: {TRIAGE[cid]}'
            if cid in TRIAGE_PREDICTION: note += ' | persona prediction: ' + TRIAGE_PREDICTION[cid]
        snip = SNIP_OVERRIDE.get(cid, (s["snippet_start"], s["snippet_end"]))
        out.append(dict(id=cid, file=r["file"], line=s["new_line"], snip=snip,
                        text=text, tag=r["tag"], note=note, blocker=s.get("still_blocker", r["blocker"]), origin="carried",
                        fix=FIX.get(cid), reply_to=None))
    for k, x in enumerate(NEW, 1):
        d = dict(id=f"R5-{k:02d}", origin="r5", reply_to=None)
        d.update(x)
        d["fix"] = FIX.get(d["id"])
        out.append(d)
    out.sort(key=lambda c: (ORDER.index(c["file"]) if c["file"] in ORDER else 99, c["line"]))
    return out

def fixed_rows():
    """Resolved this round: FIXED / OBSOLETE by status, plus DROP-ped comments shown as MERGED (reason = DROP[cid])."""
    rows = []
    for cid, r in R4.items():
        s = ST.get(cid)
        if r["file"] in HIDDEN_FILES: continue
        if cid in DROP:
            rows.append((cid, r["file"], s["new_line"] if s else 0, r["text"], "MERGED", DROP[cid], FIXED_VOICE.get(cid, "")))
        elif s and s["status"] in ("FIXED", "OBSOLETE"):
            ev = s.get("evidence", "")
            if cid in TRIAGE: ev += f" | your triage: {TRIAGE[cid]}"
            rows.append((cid, r["file"], s["new_line"], r["text"], s["status"], ev, FIXED_VOICE.get(cid, "")))
    order = {"FIXED": 0, "MERGED": 1, "OBSOLETE": 2}
    rows.sort(key=lambda t: (order[t[4]], ORDER.index(t[1]) if t[1] in ORDER else 99, t[2]))
    return rows

def chart(counts):
    w, rowh, left, right = 980, 22, 300, 120  # right margin fits '15  [1 in body]' after a full-width bar
    n = len(counts); h = n * rowh + 56
    mx = max(c[1] + c[2] for c in counts) or 1
    scale = (w - left - right) / mx
    tot = sum(c[1] + c[2] for c in counts)
    p = [f'<svg viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="Open comments per file after round 5, {tot} total">']
    p.append(f'<text x="14" y="18" font-size="12.5" fill="#0b0b0b" font-weight="600">Open comments per file after round 5 ({tot}); carried over from rounds 1-4 vs new in round 5</text>')
    for i, (f, r1n, r2n, blk) in enumerate(counts):
        y = 34 + i * rowh
        p.append(f'<text x="{left-8}" y="{y+12}" font-size="11" fill="#52514e" text-anchor="end" font-family="ui-monospace,monospace">{esc(f)}</text>')
        w1 = r1n * scale; w2 = r2n * scale
        if r1n:
            p.append(f'<rect x="{left}" y="{y+3}" width="{w1:.1f}" height="14" rx="4" fill="#2a78d6"><title>{esc(f)}: {r1n} carried over from rounds 1-4</title></rect>')
        if r2n:
            p.append(f'<rect x="{left+w1+(2 if r1n else 0):.1f}" y="{y+3}" width="{max(w2-(2 if r1n else 0),1):.1f}" height="14" rx="4" fill="#eb6834"><title>{esc(f)}: {r2n} new in round 5</title></rect>')
        lab = f"{r1n + r2n}" + (f"  ({r2n} new)" if r2n else "") + (f"  [{blk} in body]" if blk else "")
        p.append(f'<text x="{left+w1+w2+6:.1f}" y="{y+14}" font-size="11" fill="#0b0b0b">{esc(lab)}</text>')
    p.append(f'<line x1="{left}" y1="30" x2="{left}" y2="{h-6}" stroke="#d8d6d0" stroke-width="1"/>')
    ly = h - 6
    p.append(f'<rect x="{left}" y="{ly-10}" width="10" height="10" rx="2" fill="#2a78d6"/><text x="{left+14}" y="{ly-1}" font-size="11" fill="#52514e">carried over from rounds 1-4</text>')
    p.append(f'<rect x="{left+190}" y="{ly-10}" width="10" height="10" rx="2" fill="#eb6834"/><text x="{left+204}" y="{ly-1}" font-size="11" fill="#52514e">new in round 5</text>')
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
.cmt .hdr { display:flex; gap:12px; align-items:baseline; font-size:12px; color:#52514e; font-family:ui-monospace,monospace; flex-wrap:wrap; }
.cmt .hdr b { color:#0b0b0b; font-size:13px; }
.cmt .hdr .tag { background:#f4f3ef; border:1px solid #d8d6d0; border-radius:3px; padding:0 5px; }
.cmt .hdr .r2 { color:#eb6834; font-weight:600; }
.cmt .hdr .reply { color:#7570b3; font-weight:600; }
.cmt.blk .hdr b { border-left:3px solid #e34948; padding-left:5px; }
.cmt .txt { white-space:pre-wrap; font-size:14px; margin:6px 0; }
.cmt .note { font-size:11.5px; color:#52514e; }
.cmt .quoted { border-left:3px solid #d8d6d0; padding:4px 10px; margin:6px 0; font-size:12.5px; color:#52514e; white-space:pre-wrap; }
pre.src { background:#f7f6f2; border:1px solid #e1e0d9; border-radius:4px; padding:6px 8px; font-size:11.5px; line-height:1.35; overflow-x:auto; margin:6px 0; white-space:pre; }
pre.src .ln { color:#9a988f; }
pre.src .ln.hit { color:#d95f02; font-weight:700; }
.fixhdr { font-size:12px; color:#008300; font-weight:600; margin-top:6px; }
pre.fix { background:#f0f8f0; border:1px solid #b8dcb8; border-left:4px solid #008300; border-radius:4px; padding:6px 8px; font-size:12px; line-height:1.4; overflow-x:auto; margin:4px 0; white-space:pre-wrap; }
ol.plan { font-size:13.5px; margin:6px 0 6px 0; } table.sites { font-size:12px; margin:6px 0; } table.sites code { font-size:11px; }
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
  ("shape gate / <code>amx_attn::shape_ok</code>", "<code>head_size == 128 &amp;&amp; kv_mul == 4</code> in one function, used by the dispatch, the <code>save_k</code> write-through and (via <code>amx_mirror_eligible</code>) the arena allocation."),
  ("<code>amx_mirror_eligible</code>", "(a) a constexpr function over a plugin's <code>attention_kernels</code> (true if any kernel passes the shape gate); (b) a <code>bool</code> carried on every <code>node_base</code> and passed to <code>book::try_create</code>; (c) a constructor parameter of <code>book</code>. The 3-argument <code>book</code>/<code>try_create</code> forms default it to true (blocker R2-03)."),
  ("storage view / <code>kv_blocks_alias</code>", "<code>book::set_storage_view()</code> repoints <code>kv_blocks_alias</code> so logical slot 0 resolves to the extra EAGLE physical slot for the whole draft forward; since 96b5a6c72 the mirror accessors follow it through <code>mirror_view_offset_</code>."),
  ("EAGLE", "Speculative-decoding draft model that runs its own forward through the same books, storing its layer-0 K/V in an extra physical storage slot after the validator's logical slots."),
  ("ready / pending pass", "Software attention runs twice per operation: over pages that receive no K/V this forward (ready), then after <code>upstream_kvs_ready.wait()</code> over pages being written this forward (pending)."),
  ("RX worker", "Per-card driver thread running DMA completion callbacks; <code>rope_k</code>/<code>save_k</code> execute there."),
  ("work region", "One <code>begin_region()</code>/<code>end_region()</code> bracket = one <code>LDTILECFG</code>/<code>TILERELEASE</code> pair, held for one <code>apply_page_range</code> call (~229 cycles measured for the pair)."),
  ("whole-path benchmark / <code>amx_fused_bench.cpp</code>", "A stand-alone program (deleted in ff7269a9f, in history up to d176c88b3) that timed scores + softmax + PV of one 64-token page on hand-written copies of the kernels. Its recorded sweep (<code>exec/results/slot1/fused-sweep-v2.txt</code> in the campaign workspace, outside the tron tree) is the source of the 1250 / 686 ns figures."),
  ("Codex review", "An automated review posted on 2026-08-25 by jeremyconner1975 (&ldquo;Review performed by Codex at Jeremy&rsquo;s request&rdquo;) with two inline comments on <code>self_attention.hpp</code>. Alexey answers bot findings rather than ignoring them (persona C2); his replies are in section 4 marked <span style=\"color:#7570b3;font-weight:600\">reply</span>."),
  ("Run CI label", "Draft PRs skip the build/test jobs of <code>cmake-single-platform.yml</code> unless the PR carries the <code>Run CI</code> label at the next push (Note [Draft PR Filtering and Label Override])."),
  ("Note [Title]", "GHC-style named long comment, checked by <code>make lint-notes</code>."),
  ("A3, B6, ... tags", "Item numbers from <code>~/workspace/reviewers/alexey.md</code> section 1; shown only in the verification line, never in the comment text."),
]

def _lang(file):
    return "markdown" if file.endswith(".md") else ("cmake" if file.endswith("CMakeLists.txt") else "cpp")

def fix_html(cfile, fx):
    """Suggested-fix block. fx = dict(lines, text, note) for one hunk in the comment's file, or
    dict(plan=[...], hunks=[dict(file, lines|None, what, text)], sites=[(where, current, replacement)], note)."""
    o = ['<div class="fixhdr">Suggested fix (added at your request)</div>']
    if "text" in fx:
        o.append(f'<div class="note">replace lines {fx["lines"][0]}-{fx["lines"][1]} with:</div>')
        o.append(f'<pre class="fix">{esc(fx["text"])}</pre>')
    if fx.get("plan"):
        o.append('<ol class="plan">' + "".join(f"<li>{render_text(p)}</li>" for p in fx["plan"]) + "</ol>")
    for h in fx.get("hunks", []):
        where = f'<code>{esc(h["file"])}</code>' + (f':{h["lines"][0]}-{h["lines"][1]}' if h.get("lines") else " (new file)")
        o.append(f'<div class="note">{where} &mdash; {render_text(h["what"])}</div>')
        o.append(f'<pre class="fix">{esc(h["text"])}</pre>')
    if fx.get("sites"):
        o.append('<table class="sites"><tr><th>site</th><th>now</th><th>with the flag explicit</th></tr>')
        for w, cur, new in fx["sites"]:
            o.append(f'<tr><td><code>{esc(w)}</code></td><td><code>{esc(cur)}</code></td><td><code>{esc(new)}</code></td></tr>')
        o.append('</table>')
    o.append(f'<div class="note">fix note: {esc(fx["note"])}</div>')
    return "\n".join(o)

def fix_md(cfile, fx):
    L = ["**Suggested fix** (added at your request)", ""]
    if "text" in fx:
        fence = "````" if "```" in fx["text"] else "```"
        L += [f"Replace lines {fx['lines'][0]}-{fx['lines'][1]} with:", "", f"{fence}suggestion\n{fx['text']}\n{fence}", ""]
    for i, p in enumerate(fx.get("plan", []), 1):
        L.append(f"{i}. {p}")
    if fx.get("plan"): L.append("")
    for h in fx.get("hunks", []):
        where = f"`{h['file']}`" + (f":{h['lines'][0]}-{h['lines'][1]}" if h.get("lines") else " (new file)")
        L += [f"{where} - {h['what']}", ""]
        fence = "````" if "```" in h["text"] else "```"
        lang = "suggestion" if (h["file"] == cfile and h.get("lines")) else _lang(h["file"])
        L += [f"{fence}{lang}\n{h['text']}\n{fence}", ""]
    if fx.get("sites"):
        L += ["| site | now | with the flag explicit |", "|---|---|---|"]
        for w, cur, new in fx["sites"]:
            L.append(f"| `{w}` | `{cur}` | `{new}` |")
        L.append("")
    L.append(f"_Fix note: {fx['note']}_\n")
    return L

def build_html(comments, fixed, method, clean):
    order = []
    for c in comments:
        if c["file"] not in order: order.append(c["file"])
    counts = [(f, sum(1 for c in comments if c["file"] == f and c["origin"] == "carried"),
                  sum(1 for c in comments if c["file"] == f and c["origin"] == "r5"),
                  sum(1 for c in comments if c["file"] == f and c["blocker"])) for f in order]
    nb = sum(1 for c in comments if c["blocker"]); nnew = sum(1 for c in comments if c["origin"] == "r5")
    nfix = sum(1 for r in fixed if r[4] == "FIXED"); nobs = sum(1 for r in fixed if r[4] == "OBSOLETE"); nmer = sum(1 for r in fixed if r[4] == "MERGED")
    o = ['<meta charset="utf-8">', '<title>PR 3879 review as Alexey, round 5</title>', f"<style>{CSS}</style>"]
    o.append(f'<h1>Review of PR #{PR["num"]} as Alexey would write it &mdash; round 5</h1>')
    o.append(f'<p class="sub"><a href="{PR["url"]}">positron-ai/tron#{PR["num"]}</a> &mdash; {esc(PR["title"])} &mdash; head <code>{PR["head"]}</code> (round 4 reviewed <code>{esc(PR["prev"])}</code>; delta = {esc(PR["delta_commit"])}: {esc(PR["delta_stat"])}), base <code>{PR["base"]}</code>, {PR["files"]} files, +{PR["add"]}/&minus;{PR["dele"]}. Written {PR["date"]}. Rounds 1-4 are archived as <code>alexey-review-1.html</code> &hellip; <code>-4.html</code>; the Markdown twin of this page is <code>alexey-review-5.md</code>. '
             f'Each comment shows the source lines it refers to (from <code>234c02bde</code>; the anchored line is marked); the small grey line under each comment is the verification record for you and is not part of the review.</p>')
    o.append('<div class="lineage">Lineage note: &ldquo;mirror&rdquo; names the formulation S = Q&middot;K<sup>T</sup> read from a second, VNNI-interleaved copy of K, which originates from Bill&rsquo;s PR #2934 (<code>k_vnni</code>); the parallel-arena implementation and all numbers in PR #3879 are ours (<code>jhan-amx-p0</code>). &ldquo;canonical-K&rdquo; = K in today&rsquo;s original single-copy storage, read as-is.</div>')
    o.append('<h2>1. Verdict</h2>')
    o.append(f'<div class="verdict"><span class="state">{VERDICT}</span><div class="body">{render_text(BODY)}</div></div>')
    o.append(f'<div class="take">{TAKE.replace("__F__", str(nfix)).replace("__X__", str(nobs)).replace("__M__", str(nmer)).replace("__O__", str(len(comments)-nnew)).replace("__N__", str(nnew)).replace("__B__", str(nb))}</div>')

    o.append(EAGLE_HTML)
    o.append('<h2>2. Resolved since round 4</h2>')
    o.append(f'<p class="sub">Open comments the three commits addressed ({nfix} fixed), made moot by deleting the file they were about ({nobs} obsolete), or whose remaining half now lives in another thread ({nmer} merged; the "how it was addressed" column names the threads). He would resolve these threads without text; the few one-liners he might leave are in the last column.</p>')
    o.append('<table><tr><th>comment</th><th>where (234c02bde)</th><th>what was asked</th><th>how it was addressed</th><th>his reply, if any</th></tr>')
    for cid, f, ln, text, status, ev, voice in fixed:
        short = text if len(text) < 220 else text[:217] + "..."
        where = f'<code>{esc(f)}:{ln}</code>' if ln else f'<code>{esc(f)}</code> (deleted)'
        o.append(f'<tr><td>{cid}<br><span style="color:#52514e">{status.lower()}</span></td><td>{where}</td><td>{render_text(short)}</td><td style="font-size:12px">{esc(ev)}</td><td>{render_text(voice)}</td></tr>')
    o.append('</table>')

    o.append('<h2>3. Where the open comments land</h2>')
    o.append('<figure>' + chart(counts) + f'<figcaption>{len(comments)} open comments over {len(order)} files: {len(comments)-nnew} carried over from rounds 1-4 (blue) and {nnew} new in round 5 (orange; {sum(1 for c in comments if c.get("reply_to"))} of them are replies in the Codex threads). {nb} are cited in the body as blockers.</figcaption></figure>')

    o.append('<h2>4. Open comments (carried over + new in round 5)</h2>')
    o.append('<p class="sub">Line numbers are in <code>234c02bde</code>. Carried-over comments keep their earlier text (a GitHub thread stays as written); where the commits addressed a comment in part, one follow-up sentence is appended. New comments are marked <span style="color:#eb6834;font-weight:600">new</span>; replies he would post in the two Codex threads are marked <span style="color:#7570b3;font-weight:600">reply</span> and quote the bot comment they answer.</p>')
    for f in order:
        o.append(f'<h3>{esc(f)}</h3>')
        for c in [x for x in comments if x["file"] == f]:
            cls = "cmt blk" if c["blocker"] else "cmt"
            if c.get("reply_to"):
                newmark = f'<span class="reply">reply</span><span>to Codex comment {c["reply_to"]["id"]}</span>'
            elif c["origin"] == "r5":
                newmark = '<span class="r2">new</span>'
            else:
                newmark = f'<span>{c["id"]}</span>'
            o.append(f'<div class="{cls}"><div class="hdr"><b>:{c["line"]}</b>{newmark}<span class="tag">{esc(c["tag"])}</span></div>')
            o.append(snippet_html(f, c["snip"][0], c["snip"][1], c["line"]))
            if c.get("reply_to"):
                o.append(f'<div class="quoted">{esc(c["reply_to"]["author"])} (Codex): {esc(c["reply_to"]["body"])}</div>')
            o.append(f'<div class="txt">{render_text(c["text"])}</div>')
            if c.get("fix"):
                o.append(fix_html(c["file"], c["fix"]))
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
    for c in comments:
        hdr = f"{c['file']}:{c['line']}" + (f"  (reply in Codex thread {c['reply_to']['id']})" if c.get("reply_to") else "")
        o.append(esc(f"{hdr}\n{c['text']}\n\n"))
    o.append('</pre></details>')
    return "\n".join(o)

def build_md(comments, fixed, method, clean):
    L = []
    nnew = sum(1 for c in comments if c["origin"] == "r5")
    nfix = sum(1 for r in fixed if r[4] == "FIXED"); nobs = sum(1 for r in fixed if r[4] == "OBSOLETE"); nmer = sum(1 for r in fixed if r[4] == "MERGED")
    L.append(f"# Review of PR #{PR['num']} as Alexey would write it - round 5\n")
    L.append(f"{PR['url']} - {PR['title']}  ")
    L.append(f"Head `{PR['head']}` (round 4 reviewed `{PR['prev']}`; delta = {PR['delta_commit']}: {PR['delta_stat']}); base `{PR['base']}`; {PR['files']} files, +{PR['add']}/-{PR['dele']}. Written {PR['date']}. HTML twin: `alexey-review.html`; rounds 1-4 archived as `alexey-review-1.html` ... `-4.html`.\n")
    L.append("Lineage note: \"mirror\" names the formulation S = Q.K^T read from a second, VNNI-interleaved copy of K, which originates from Bill's PR #2934 (`k_vnni`); the parallel-arena implementation and all numbers in PR #3879 are ours (`jhan-amx-p0`). \"canonical-K\" = K in today's original single-copy storage, read as-is.\n")
    L.append("Each comment shows the source lines it refers to (head `234c02bde`; the anchored line is marked with `*`). The line starting `Verification:` is the evidence record for jhan, not part of the review.\n")
    L.append(f"## 1. Verdict\n\n**{VERDICT}**\n\n{BODY}\n")
    L.append(TAKE_MD.replace("__F__", str(nfix)).replace("__X__", str(nobs)).replace("__M__", str(nmer)).replace("__O__", str(len(comments)-nnew)).replace("__N__", str(nnew)).replace("__B__", str(sum(1 for c in comments if c["blocker"]))) + "\n")
    L.append(EAGLE_MD)
    L.append("## 2. Resolved since round 4\n")
    L.append(f"Open comments the three commits addressed ({nfix} fixed), made moot by deleting the file they were about ({nobs} obsolete), or whose remaining half now lives in another thread ({nmer} merged; the 'how it was addressed' column names the threads).\n")
    L.append("| comment | where (234c02bde) | what was asked | how it was addressed | his reply, if any |\n|---|---|---|---|---|")
    for cid, f, ln, text, status, ev, voice in fixed:
        short = (text if len(text) < 220 else text[:217] + "...").replace("|", "\\|").replace("\n", " ")
        ev2 = ev.replace("|", "\\|").replace("\n", " ")
        where = f"`{f}:{ln}`" if ln else f"`{f}` (deleted)"
        L.append(f"| {cid} ({status.lower()}) | {where} | {short} | {ev2} | {voice} |")
    L.append("")
    L.append(f"## 3. Open comments ({len(comments)}: {len(comments)-nnew} carried over from rounds 1-4, {nnew} new in round 5)\n")
    L.append("Carried-over comments keep their earlier text; where the commits addressed a comment in part, one follow-up sentence is appended. New comments are marked **new**; replies he would post in the two Codex threads are marked **reply** and quote the bot comment they answer. A leading `[blocker]` marks the comments the body names.\n")
    cur = None
    for c in comments:
        if c["file"] != cur:
            cur = c["file"]; L.append(f"### {cur}\n")
        if c.get("reply_to"):
            mark = f"**reply** to Codex comment {c['reply_to']['id']} "
        elif c["origin"] == "r5":
            mark = "**new** "
        else:
            mark = f"{c['id']} "
        blk = "[blocker] " if c["blocker"] else ""
        L.append(f"#### {blk}`{c['file']}:{c['line']}` {mark}({c['tag']})\n")
        L.append(snippet_md(c["file"], c["snip"][0], c["snip"][1], c["line"]))
        L.append("")
        if c.get("reply_to"):
            L.append("> " + c["reply_to"]["author"] + " (Codex): " + c["reply_to"]["body"].replace("\n", "\n> "))
            L.append("")
        L.append(c["text"])
        L.append("")
        if c.get("fix"):
            L.extend(fix_md(c["file"], c["fix"]))
        L.append(f"_Verification: {c['note']}_\n")
    L.append("## 4. Checked and clean in the delta\n")
    L.append("| area | what was verified | source |\n|---|---|---|")
    for a, b, s in clean:
        L.append(f"| {a} | {b.replace('|', chr(92) + '|')} | {s.replace('|', chr(92) + '|')} |")
    L.append("")
    L.append("## 5. Glossary\n")
    for k, v in GLOSSARY:
        L.append(f"- **{re.sub(r'<[^>]+>','',k)}** - {html.unescape(re.sub(r'<[^>]+>','',v))}")
    L.append("")
    L.append("## 6. Method and limits\n")
    for m in method: L.append(f"- {html.unescape(re.sub(r'<[^>]+>','',m))}")
    L.append("")
    return "\n".join(L)

def check_head():
    sha = subprocess.check_output(["git", "-C", HEAD, "rev-parse", "HEAD"], text=True).strip()
    dirty = subprocess.check_output(["git", "-C", HEAD, "status", "--porcelain"], text=True).strip()
    if sha != HEAD_SHA or dirty:
        sys.exit(f"HEAD tree {HEAD} is at {sha[:9]} (want {HEAD_SHA[:9]}), dirty={bool(dirty)}; refusing to snippet from the wrong tree")

def main(method, clean):
    check_head()
    comments = all_comments()
    fixed = fixed_rows()
    # Every open comment must have a snippet from the head tree (or be about a deleted file: not allowed in the open list).
    for c in comments:
        if not snippet(c["file"], c["snip"][0], c["snip"][1], c["line"]):
            sys.exit(f"no snippet for {c['id']} {c['file']}:{c['line']}")
    method = [m.replace("__N__", str(len(comments))).replace("__F__", str(len(fixed))) for m in method]
    out = build_html(comments, fixed, method, clean)
    out = out.encode("ascii", "xmlcharrefreplace").decode("ascii")  # HTML deliverables are pure ASCII + entities
    open(OUT_HTML, "w").write(out)
    md = build_md(comments, fixed, method, clean)
    open(OUT_MD, "w").write(md)
    print(f"wrote {OUT_HTML} ({len(out)} bytes) and {OUT_MD} ({len(md)} bytes); open={len(comments)} (new={sum(1 for c in comments if c['origin']=='r5')}, blockers={sum(1 for c in comments if c['blocker'])}), resolved={len(fixed)} (fixed={sum(1 for r in fixed if r[4]=='FIXED')}, obsolete={sum(1 for r in fixed if r[4]=='OBSOLETE')})")

if __name__ == "__main__":
    exec(open(os.path.join(R5, "round5_data.py")).read())  # sets VERDICT, BODY, TAKE, TAKE_MD, NEW, FOLLOWUP, DROP, FIXED_VOICE, FIX, METHOD, CLEAN
    main(METHOD, CLEAN)
