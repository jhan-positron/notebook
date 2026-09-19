#!/usr/bin/env python3
"""Build VNNIed-K-in-place/status/mirror-vs-VNNI-K.html from rows.json (the rows extracted
from the existing result files by the pull-mirror-vs-vnni-data workflow, verified against
the raw files). No new measurement: every number comes from a file that already existed.

Two tables, never mixed: our runtron tests, and the CI-harness tests (the nightly's
throughput test driven by us against a rinzler server). Columns = the five arms jhan named:
AMX off, AMX compiled off, canonical, mirror, VNNI-K; each with TPS and TTFT. One table row = one
cell of one campaign (model, tp, users, prompt) so that the arms inside a row are directly
comparable (same day, same binary lineage, same placement). The raw file names and
locations are listed below each table by row key, not inside the table.
Usage: gen_compare.py ROWS_JSON [OUT_HTML]
"""
import html
import json
import sys
import datetime

ROWS = sys.argv[1]
OUT = sys.argv[2] if len(sys.argv) > 2 else "/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/status/mirror-vs-VNNI-K.html"
NOW = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

ARMS = [("off", "AMX off"), ("clean", "AMX compiled off"), ("canonical", "canonical"), ("mirror", "mirror"), ("vnni", "VNNI-K")]


def esc(s):
    return html.escape(str(s), quote=True)


data = json.load(open(ROWS))
rows = data["rows"]

def model_short(m):
    m = (m or "").lower()
    if "qwen" in m:
        return "qwen3-4b"
    if "llama-3.1-8b" in m or "llama-3-8b" in m or "llama-3.1" in m:
        return "llama-3.1-8b"
    if "gpt-oss-120b" in m:
        return "gpt-oss-120b"
    if "gpt-oss" in m:
        return "gpt-oss-20b"
    if "mixtral" in m:
        return "mixtral-8x7b"
    return m


# ------------------------------------------------------------- group into table rows
def placement_class(pl):
    pl = (pl or "").lower()
    if "90:00.0" in pl or "instance 2,4" in pl or "instance 1,2" in pl or "socket 1" in pl or "socket-1" in pl:
        return "socket1"
    if "10:00.0" in pl or "38:00.0" in pl or "instance 0,4" in pl or "instance 1,4" in pl or "socket 0" in pl or "socket-0" in pl:
        return "socket0"
    return ""


def campaign(r):
    d = (r.get("date") or "")[:10]
    if r["source_id"] == "more-testing-r1":   # one CI round that ran across midnight UTC
        return r["source_id"]
    return r["source_id"] + "|" + d + "|" + placement_class(r.get("placement"))


def cell_key(r):
    return (r["harness"], model_short(r["model"]), int(r["tp"] or 0), int(r["users"] or 0), int(r["prompt_tokens"] or 0), campaign(r))


def better(new, old):
    """Which of two rows of the same arm in one cell the table shows: more repetitions
    first, then an arena mirror over an in-block mirror, else the earlier one."""
    nn, no = new.get("n_reps") or 0, old.get("n_reps") or 0
    if nn != no:
        return nn > no
    dn, do = (new.get("arm_detail") or "").lower(), (old.get("arm_detail") or "").lower()
    if "arena" in dn and "in-block" in do:
        return True
    return False


groups = {}
for r in rows:
    if r["arm"] not in dict(ARMS):
        continue
    if r.get("tps_per_user") is None and r.get("ttft_value") is None:
        continue
    k = cell_key(r)
    g = groups.setdefault(k, {"harness": r["harness"], "model": r["model"], "tp": r["tp"], "users": r["users"], "prompt": r["prompt_tokens"],
                              "source_id": r["source_id"], "date": (r.get("date") or "")[:10], "arms": {}, "files": set(), "commit": set(), "placement": set(), "generated": set(), "ttft_unit": set(), "ttft_def": set(), "notes": []})
    if (r.get("date") or "")[:10] > g["date"]:
        g["date"] = (r.get("date") or "")[:10] if g["source_id"] != "more-testing-r1" else g["date"]
    prev = g["arms"].get(r["arm"])
    if prev is None:
        g["arms"][r["arm"]] = r
    elif better(r, prev):
        g["notes"].append("%s also as %s: TPS %s, TTFT %s %s (%s reps)" % (dict(ARMS)[r["arm"]], prev.get("arm_detail"), prev.get("tps_per_user"), prev.get("ttft_value"), prev.get("ttft_unit") or "", prev.get("n_reps")))
        g["arms"][r["arm"]] = r
    else:
        g["notes"].append("%s also as %s: TPS %s, TTFT %s %s (%s reps)" % (dict(ARMS)[r["arm"]], r.get("arm_detail"), r.get("tps_per_user"), r.get("ttft_value"), r.get("ttft_unit") or "", r.get("n_reps")))
    for f in r.get("source_files") or []:
        g["files"].add(f.split(":")[0] if f.startswith("/") else f)
    if r.get("commit_or_binary"):
        g["commit"].add(r["commit_or_binary"][:90])
    if r.get("placement"):
        g["placement"].add(r["placement"][:160])
    if r.get("generated_tokens"):
        g["generated"].add(str(r["generated_tokens"]))
    if r.get("ttft_unit"):
        g["ttft_unit"].add(r["ttft_unit"])
    if r.get("ttft_definition"):
        g["ttft_def"].add(r["ttft_definition"])
# drop cells that carry no decode rate at all (capacity probes with prefill only)
groups = {k: g for k, g in groups.items() if any(v.get("tps_per_user") is not None for v in g["arms"].values())}


def fmt_tps(r):
    if not r or r.get("tps_per_user") is None:
        return "-"
    s = "%.2f" % r["tps_per_user"]
    if r.get("tps_sd") is not None and r.get("n_reps") and r["n_reps"] > 1:
        s += '<span class="sd"> &plusmn;%.2f</span>' % r["tps_sd"]
    return s


def fmt_ttft(r, harness):
    if not r or r.get("ttft_value") is None:
        return "-"
    u = (r.get("ttft_unit") or "").lower()
    if harness == "runtron":
        v = r["ttft_value"]
        if "ms" in u:
            v = v / 1000.0
        return "%.3f" % v
    v = r["ttft_value"]
    if u.startswith("s") and "ms" not in u:
        v = v * 1000.0
    return "%.0f" % v


def table(harness, title, ttft_label, repeat_head=False):
    keys = sorted([k for k in groups if groups[k]["harness"] == harness],
                  key=lambda k: (model_short(groups[k]["model"]), int(groups[k]["tp"] or 0), int(groups[k]["users"] or 0), int(groups[k]["prompt"] or 0), groups[k]["date"], k[5]))
    if not keys:
        return "<p class='pending'>no rows</p>", []
    out = ['<h2>%s</h2>' % esc(title)]
    head = ['<tr><th rowspan="2">key</th><th rowspan="2">model</th><th rowspan="2">tp</th><th rowspan="2">users</th><th rowspan="2">prompt</th><th rowspan="2">date</th>']
    for _, label in ARMS:
        head.append('<th colspan="2">%s</th>' % esc(label))
    head.append('</tr><tr>')
    for _ in ARMS:
        head.append('<th>TPS</th><th>%s</th>' % esc(ttft_label))
    head.append('</tr>')
    head = "".join(head)
    out.append('<table class="cmp"><thead>' + head + '</thead><tbody>')
    legend = []
    for i, k in enumerate(keys):
        g = groups[k]
        key = "%s%d" % ("R" if harness == "runtron" else "C", i + 1)
        legend.append((key, g))
        out.append('<tr><td class="key">%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td>' % (
            key, esc(model_short(g["model"])), esc(g["tp"]), esc(g["users"]), esc(g["prompt"]), esc(g["date"][:10])))
        for arm, _ in ARMS:
            r = g["arms"].get(arm)
            out.append('<td class="num">%s</td><td class="num">%s</td>' % (fmt_tps(r), fmt_ttft(r, harness)))
        out.append('</tr>')
    out.append('</tbody>')
    if repeat_head:   # long table: the header row is repeated at the bottom (jhan, 2026-09-15)
        out.append('<tfoot>' + head + '</tfoot>')
    out.append('</table>')
    return "".join(out), legend


def one_cell_table(legend):
    """The one cell measured in every arm across the campaigns: qwen3-4b tp2, 8 users, prompt 8192 (runtron)."""
    sel = [(k, g) for k, g in legend
           if model_short(g["model"]) == "qwen3-4b" and int(g["tp"] or 0) == 2 and int(g["users"] or 0) == 8 and int(g["prompt"] or 0) == 8192]
    out = ['<h2>The one cell where every arm exists (qwen3-4b tp2, 8 users, prompt 8192; TPS per user / prefill s)</h2>']
    out.append('<p class="sub">Our runtron tests only, 256 generated tokens per run. Each cell reads decode TPS per user / prefill time in seconds (time to first token). '
               'A dash means the arm was not run in that campaign. The first column names the Table 1 row that holds the same campaign; the raw data files are listed under Table 1 by that key.</p>')
    out.append('<div class="wrap"><table class="cmp"><thead><tr><th>Table 1 row</th><th>date</th><th>placement</th>' + "".join('<th>%s</th>' % esc(l) for _, l in ARMS) + '</tr></thead><tbody>')
    text = []
    for k, g in sel:
        pc = placement_class(" ".join(sorted(g["placement"])))
        where = {"socket1": "our half (socket 1)", "socket0": "socket 0"}.get(pc, "not recorded")
        out.append('<tr><td class="key">%s</td><td>%s</td><td>%s</td>' % (k, esc(g["date"][:10]), where))
        line = [k, g["date"][:10], where]
        for arm, _ in ARMS:
            r = g["arms"].get(arm)
            if not r or r.get("tps_per_user") is None:
                cell = "-"
            else:
                if r.get("ttft_value") is None:
                    pre = "-"
                else:
                    v = r["ttft_value"]
                    if "ms" in (r.get("ttft_unit") or "").lower():
                        v = v / 1000.0
                    pre = "%.1f" % v
                cell = "%.2f / %s" % (r["tps_per_user"], pre)
            out.append('<td class="num">%s</td>' % cell)
            line.append(cell)
        out.append('</tr>')
        text.append(line)
    out.append('</tbody></table></div>')
    return "".join(out), text


def sources(legend):
    out = ['<h3>Raw data by row key</h3><ul class="src">']
    for key, g in legend:
        arms = ", ".join("%s = %s" % (dict(ARMS)[a], esc(g["arms"][a].get("arm_detail") or a)) for a in g["arms"])
        out.append('<li><b>%s</b> %s tp%s, %s users, prompt %s, %s generated; %s; %s; %s.<br><span class="files">%s</span>%s</li>' % (
            key, esc(model_short(g["model"])), esc(g["tp"]), esc(g["users"]), esc(g["prompt"]), esc("/".join(sorted(g["generated"])) or "?"),
            esc("; ".join(sorted(g["commit"])) or "commit not recorded"), esc("; ".join(sorted(g["placement"])) or "placement not recorded"),
            arms, "<br>".join(esc(f) for f in sorted(g["files"])),
            ('<br><span class="note">%s</span>' % esc(" | ".join(g["notes"][:6]))) if g["notes"] else ""))
    out.append('</ul>')
    return "".join(out)


rt_table, rt_legend = table("runtron", "Table 1. Our tests (runtron, one process, all users in one batch)", "TTFT s", repeat_head=True)
cell_table, cell_text = one_cell_table(rt_legend)
ci_table, ci_legend = table("ci-harness", "Table 2. CI-harness tests (systems_test throughput test against a rinzler server)", "TTFT ms")

page = []
page.append("""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Mirror vs VNNI-K</title>
<style>
:root { --ink:#0b0b0b; --muted:#52514e; --line:#e6e5e1; --bg:#fcfcfb; --panel:#f3f2ef; --accent:#2a78d6; }
body { margin:0; padding:24px 16px 48px; background:var(--bg); color:var(--ink); font:14px/1.45 system-ui,-apple-system,Segoe UI,Roboto,sans-serif; }
main { max-width:1180px; margin:0 auto; }
h1 { font-size:24px; margin:0 0 6px; } h2 { font-size:18px; margin:28px 0 8px; border-bottom:1px solid var(--line); padding-bottom:4px; } h3 { font-size:15px; margin:16px 0 6px; }
.sub { color:var(--muted); margin-bottom:14px; }
.short { background:var(--panel); border-left:4px solid var(--accent); padding:10px 14px; margin:12px 0; }
.wrap { overflow-x:auto; }
table.cmp { border-collapse:collapse; width:100%%; font-size:13px; }
table.cmp th, table.cmp td { border:1px solid var(--line); padding:4px 6px; text-align:left; vertical-align:top; white-space:nowrap; }
table.cmp th { background:var(--panel); text-align:center; }
table.cmp td.num { text-align:right; font-variant-numeric: tabular-nums; }
table.cmp td.key { font-weight:600; color:var(--accent); }
table.cmp tbody tr:nth-child(even) td { background:#f9f8f6; }
.sd { color:var(--muted); font-size:11px; }
table.terms { border-collapse:collapse; width:100%%; font-size:13px; margin:8px 0 14px; } table.terms th, table.terms td { border:1px solid var(--line); padding:5px 8px; text-align:left; vertical-align:top; } table.terms th { background:var(--panel); }
ul.src { list-style:none; padding:0; margin:6px 0; } ul.src li { margin:0 0 10px; padding:6px 8px; border-left:3px solid var(--line); font-size:13px; }
.files { font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-size:12px; color:var(--muted); } .note { color:var(--muted); font-size:12px; }
.pending { color:var(--muted); font-style:italic; }
ul { margin:6px 0 10px 22px; } li { margin:3px 0; }
</style></head><body><main>
<h1>Mirror vs VNNI-K</h1>
<p class="sub">One glance at every measured arm of the AMX software-attention work on delphi-3bda: AMX off, AMX compiled off, canonical, mirror and VNNI-K, with decode rate (TPS) and time to first token (TTFT). Pulled from the existing result files on %s; nothing was re-run. Our runtron tests and the CI-harness tests are in separate tables. The raw data file names and locations are listed under each table by row key.</p>
""" % NOW)

page.append("""<div class="short"><p><b>Short version.</b> Within one row (one campaign, one cell) the five arms are directly comparable; across rows they are not (different days, commits and placements), so read across rows only for direction. The mirror rows come from the August and early-September campaigns; the VNNI-K rows come from the 2026-09-14 campaign, which had no mirror arm, and no CI-harness measurement of VNNI-K exists yet. Cells: TPS = decode tokens per second per user; TTFT = time to first token, in seconds of batched prefill for runtron and in milliseconds to the first streamed chunk for the CI harness. A dash means the arm was not measured in that campaign; &plusmn; is the standard deviation over the repetitions where more than one exists.</p></div>""")

page.append("""<h2>Words used here</h2>
<table class="terms"><tr><th>Column</th><th>What ran</th></tr>
<tr><td>AMX off</td><td>The AMX-capable binary with the kill switch TRON_AMX_DISABLE=1: the AVX-512 software attention on row-major K (or, in the VNNI-K campaign's own binary, the AVX-512 VNNI reader; that arm is not in the table, see the notes). Earlier campaign names: off, kill, amxoff, g1kill.</td></tr>
<tr><td>AMX compiled off</td><td>A binary built WITHOUT any AMX option: main as shipped. Earlier campaign names: clean, pr1clean. Not built in every campaign. It is a different binary from the AMX off arm, so the two differ by a small code-layout effect: in the 2026-09-07/09 rounds the AMX off arm ran 0.6 to 0.7% ABOVE AMX compiled off (three rounds, same direction each time), in the August arena-mirror binary the kill switch ran 1 to 5% BELOW AMX compiled off. The ordering of these two columns is therefore not a sign of an error; see the note below Table 2.</td></tr>
<tr><td>canonical</td><td>PR #3879: AMX on with K stored row-major (canonical K). Earlier names: canon, AMX, on, base, amxon, g1canon. The Monday report of 2026-09-14 calls this arm &quot;base&quot; / &quot;AMX AMX compiled off&quot;.</td></tr>
<tr><td>mirror</td><td>AMX on with the K mirror: a second copy of K in the VNNI layout. Arena mirror (parallel arena, PR 2 lineage) unless the source list says in-block mirror (the 2026-08-19 first version, which held the copy inside the KV block). Earlier names: mirror, g1mirror.</td></tr>
<tr><td>VNNI-K</td><td>Branch jhan-amx-vnniK (2026-09-14): K stored once, in the VNNI layout, in place of the row-major rows; AMX on. Campaign name: vnni.</td></tr>
<tr><td>TPS, TTFT</td><td>TPS = decode tokens per second per user (runtron: mean of the per-request &quot;average tok/s&quot;; CI harness: tps_mean over users and rounds). TTFT = runtron: &quot;Parsing the prompt took&quot; seconds, the batched prefill of all users; CI harness: milliseconds to the first streamed chunk, mean over users and rounds.</td></tr>
<tr><td>tp, users, prompt</td><td>tp = tensor-parallel degree = number of FPGA cards; users = concurrent requests; prompt = prompt length in tokens (earlier scripts wrote &quot;ctx N&quot; for this).</td></tr>
</table>""")

page.append(cell_table)
page.append('<div class="wrap">' + rt_table + '</div>' + sources(rt_legend))
page.append('<div class="wrap">' + ci_table + '</div>' + sources(ci_legend))

caveats = data.get("caveats") or []
page.append("<h2>Notes on the data</h2><ul>")
page.append("<li>Rows are one campaign each; the same cell measured on different days appears as separate rows (different commits and placements: socket 0 with cards 10/13/38/3b in August, our half socket 1 with cards 90/93/b9/bc from 2026-09-06 on).</li>")
page.append("<li>AMX compiled off below AMX off (for example the 2026-09-09 row: 14.65 vs 14.74 TPS per user, prompt 8192) is measured, not a data error. Both are AVX-512 software attention on row-major K, but they are two different binaries. Per-round values, decode TPS per user at prompt 8192, 8 users: 2026-09-07 our half AMX compiled off 14.62 / 14.69 vs AMX off 14.74 / 14.76; 2026-09-07 socket 0 AMX compiled off 14.66 / 14.68 vs AMX off 14.80 / 14.76; 2026-09-09 our half AMX compiled off 14.65 / 14.65 vs AMX off 14.74 / 14.75. The gap is 0.6 to 0.7% and has the same sign in all six pairs, so it is a real property of those two builds (code layout), not run-to-run noise (within-arm spread 0.0 to 0.5%). In August the opposite sign was measured on the arena-mirror binary (kill switch 1 to 5% below the clean build). Canonical WAS measured in the same rounds (arm amxon = PR #3879 at its head of the day: 9723d56f62 on 2026-09-07, 26a0338c3b on 2026-09-09).</li>")
page.append("<li>The VNNI-K campaign also ran a fourth arm, vnni-off (the VNNI-K binary with the kill switch); it is not one of the five columns and is reported in status/Monday-morning-report.html.</li>")
page.append("<li>Probe arms of the G1 campaign (sonly, inplace, g1mirror) and the fpga arm of the 2026-09-13 campaign are not shown; they are in the source files listed.</li>")
for c in caveats:
    if c:
        page.append("<li>%s</li>" % esc(c[:600]))
page.append("</ul></main></body></html>")

out = "".join(page)
out = "".join(("&#%d;" % ord(ch)) if ord(ch) > 127 else ch for ch in out)
open(OUT, "w").write(out)
print("wrote", OUT, len(out), "bytes;", len(rt_legend), "runtron rows,", len(ci_legend), "CI rows")
for line in cell_text:
    print(" | ".join(line))
