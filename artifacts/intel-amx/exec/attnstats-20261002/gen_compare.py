#!/usr/bin/env python3
"""attnstats-20261002: attention path stats, AMX kernel enabled vs disabled -> attn-stats-compare.md (stdout).

Usage: gen_compare.py <results dir>   (exec/results/attnstats-20261002)

Reads rt-results.txt (one '### runtron' header per run, then the grep of its log: TPS lines, the HW attention
line, HBM counts) and rt/<run>.log (the '[attn-stats]' exit report printed by tron at process end when
TRON_ATTN_STATS=1). Writes a Markdown report in plain English: tables carry the record, templated sentences
carry the arithmetic. The prose pass (definitions, one claim per sentence) is done on the output afterwards.

Scales. A visit = one (token job, KV head, page) scoring step of the software attention loop. K tokens of a
visit = the keys that step scored. The FPGA counts K tokens per query (all KV heads at once); the report puts
them on the software scale with fpga_k_tokens_x_kv_heads (= fpga_k_tokens x n_kv_heads). TSC cycles -> seconds
with tsc_hz from the header line.
"""
import glob
import json
import os
import re
import statistics
import sys

HDR = re.compile(r"^### runtron kind=(\w+) cell=(\S+) model=(\S+) tp=(\d+) users=(\d+) attn=(\w+) prompt=(\d+) len=(\d+) arm=(\w+) .*?rep=(\d+) attempt=(\d+)")
STAT_MODEL = re.compile(r"^\[attn-stats\] model (\S+): (\{.*\})\s*$")
STAT_OBJ = re.compile(r"^\[attn-stats\] (\S+) (totals|forwards): (\{.*\})\s*$")
STAT_LAYERS = re.compile(r"^\[attn-stats\] (\S+) k_tokens per layer \(amx/avx/fpga\): (.*)$")
PATH_SETS = ["none", "avx", "amx", "avx+amx", "fpga", "fpga+avx", "fpga+amx", "fpga+avx+amx"]
SHORT_MODEL = {"llama-3.1-8b-instruct-good-tp2": "llama-3.1-8b tp2", "ingested-gpt-oss-120b-tp4": "gpt-oss-120b tp4",
               "ingested-qwen-3-4b-instruct-2507-tp2": "qwen3-4b tp2"}
ATTN_WORDS = {"cpu": "CPU attention", "fpga": "FPGA attention", "fpga1": "FPGA attention forced with USE_HW_ATTN=1"}
HW_LINE = re.compile(r"HW attention (enabled|disabled)[^\n]*")
ON_ARMS = ("amxon", "headon", "on")
OFF_ARMS = ("amxoff", "headkill", "kill", "off")


def is_on(arm):
    return arm.startswith(ON_ARMS) and not arm.startswith(OFF_ARMS)


def is_off(arm):
    return arm.startswith(OFF_ARMS)


def short_model(m):
    return SHORT_MODEL.get(m, m)


def attn_word(a):
    return ATTN_WORDS.get(a, a)


def yesno(v):
    return "yes" if v is True else "no" if v is False else "n/a"


def fits(hm):
    """The AMX kernel is compiled only for head size 128 and kv_mul 4 (shape_ok, h/tron/kernels/amx_attn_iface.hpp:148-150 at main)."""
    if not hm:
        return None
    return hm.get("head_size") == 128 and hm.get("kv_mul") == 4


def hw_fields(line):
    """max_layers, hw_slots, kv_head_size, gqa from the 'HW attention enabled' line; {} when absent."""
    out = {}
    for key, pat in (("max_layers", r"max_layers=(\d+)"), ("hw_slots", r"hw_slots: (\d+)"), ("kv_head_size", r"kv_head_size: (\d+)"), ("gqa", r"gqa: (\d+)")):
        m = re.search(pat, line or "")
        if m:
            out[key] = int(m[1])
    return out


def fnum(x, nd=0):
    if x is None:
        return "n/a"
    if nd == 0:
        return f"{int(round(x)):,}"
    return f"{x:,.{nd}f}"


def pct(a, b, nd=1):
    if b in (0, None) or a is None:
        return "n/a"
    return f"{100.0 * a / b:.{nd}f} %"


def parse_results(path):
    runs, cur = [], None
    for line in open(path, errors="replace"):
        line = line.rstrip("\n")
        m = HDR.match(line)
        if m:
            cur = {"kind": m[1], "cell": m[2], "model": m[3], "tp": int(m[4]), "users": int(m[5]), "attn": m[6],
                   "prompt": int(m[7]), "len": int(m[8]), "arm": m[9], "rep": int(m[10]), "attempt": int(m[11]),
                   "tps": [], "ttft": [], "failed": False, "stopped": False, "hw_attn": None, "hbm_lose": None,
                   "hbm_exh": None, "version": None, "header": line,
                   "started": (re.search(r"(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ)", line) or [None, None])[1]}
            runs.append(cur)
            continue
        if cur is None:
            continue
        if line.startswith("RUN-FAILED"):
            cur["failed"] = True
        elif line.startswith("RUN-STOPPED") or line.startswith("RUN-GIVEN-UP"):
            cur["stopped"] = True
        m = re.match(r"HBM-EXHAUSTION lose=(\d+) exhausted=(\d+)", line)
        if m:
            cur["hbm_lose"], cur["hbm_exh"] = int(m[1]), int(m[2])
        m = re.search(r"Version: (\S+) hash: ([0-9a-f]+)", line)
        if m:
            cur["version"] = m[2][:10]
        m = re.search(r"HW attention (enabled|disabled)[^\n]*", line)
        if m and cur["hw_attn"] is None:
            cur["hw_attn"] = m[0][:200]
        m = re.search(r"Parsing the prompt took ([0-9.]+) s", line)
        if m:
            cur["ttft"].append(float(m[1]))
        m = re.search(r"Generating (\d+) response tokens with \d+ context took [0-9.]+ s at ([0-9.]+) average tok/s", line)
        if m:
            cur["tps"].append(float(m[2]))
    return runs


def parse_stats(log):
    """One run's exit report -> {'model': {...}, 'classes': {short: {'label', 'totals', 'forwards', 'layers'}}}."""
    st = {"model": None, "classes": {}, "hw_line": None}
    if not os.path.exists(log):
        return st
    for line in open(log, errors="replace"):
        line = line.rstrip("\n")
        if st["hw_line"] is None and "HW attention" in line:
            m = HW_LINE.search(line)
            if m:
                st["hw_line"] = m[0]
        if not line.startswith("[attn-stats]"):
            continue
        m = STAT_MODEL.match(line)
        if m:
            st["model"] = json.loads(m[2])
            continue
        m = STAT_OBJ.match(line)
        if m:
            cls = m[1].split("/")[0]
            st["classes"].setdefault(cls, {"label": m[1], "totals": None, "forwards": None, "layers": None})
            st["classes"][cls][m[2]] = json.loads(m[3])
            continue
        m = STAT_LAYERS.match(line)
        if m:
            cls = m[1].split("/")[0]
            st["classes"].setdefault(cls, {"label": m[1], "totals": None, "forwards": None, "layers": None})
            layers = []
            for tok in m[2].split():
                ix, vals = tok.split("=")
                a, v, f = (int(x) for x in vals.split("/"))
                layers.append((int(ix), a, v, f))
            st["classes"][cls]["layers"] = layers
    return st


def derived(cls, hz):
    """Per-class derived numbers from the totals/forwards objects."""
    t, f = cls.get("totals") or {}, cls.get("forwards") or {}
    if not t:
        return None
    d = {}
    d["k_amx"] = t.get("ready_amx_k_tokens", 0) + t.get("pending_amx_k_tokens", 0)
    d["k_avx"] = t.get("ready_avx_k_tokens", 0) + t.get("pending_avx_k_tokens", 0)
    d["k_fpga"] = t.get("fpga_k_tokens_x_kv_heads", 0)
    d["k_all"] = d["k_amx"] + d["k_avx"] + d["k_fpga"]
    d["v_amx"] = t.get("ready_amx_visits", 0) + t.get("pending_amx_visits", 0)
    d["v_avx"] = t.get("ready_avx_visits", 0) + t.get("pending_avx_visits", 0)
    d["v_empty"] = t.get("ready_empty_visits", 0) + t.get("pending_empty_visits", 0)
    d["v_avx_full"] = t.get("ready_avx_full_page_visits", 0) + t.get("pending_avx_full_page_visits", 0)
    d["v_ready_amx"], d["v_pending_amx"] = t.get("ready_amx_visits", 0), t.get("pending_amx_visits", 0)
    d["fpga_passes"] = t.get("fpga_query_passes", 0)
    d["forwards"] = f.get("forwards", 0)
    d["token_jobs"] = f.get("token_jobs", 0)
    d["fpga_queries"] = f.get("fpga_queries", 0)
    d["sets"] = f.get("token_jobs_by_path_set", {})
    d["attn_jobs"] = t.get("attn_jobs", 0)
    hz = hz or 0
    d["t1_ms_per_fwd"] = (f.get("wall_cycles", 0) / d["forwards"] / hz * 1e3) if d["forwards"] and hz else None
    d["busy_s"] = t.get("busy_cycles", 0) / hz if hz else None
    d["join_s"] = t.get("join_wait_cycles", 0) / hz if hz else None
    d["busy_ms_per_job"] = (t.get("busy_cycles", 0) / d["attn_jobs"] / hz * 1e3) if d["attn_jobs"] and hz else None
    d["join_share"] = (t.get("join_wait_cycles", 0) / t.get("busy_cycles", 1)) if t.get("busy_cycles") else None
    d["t4_ms_per_fwd"] = (t.get("period_cycles_w0", 0) / d["forwards"] / hz * 1e3) if d["forwards"] and hz else None
    return d


def ranges(ixs):
    """[0,1,2,5,7,8] -> '0-2, 5, 7-8'."""
    out, start, prev = [], None, None
    for i in ixs:
        if start is None:
            start = prev = i
        elif i == prev + 1:
            prev = i
        else:
            out.append(f"{start}-{prev}" if start != prev else f"{start}")
            start = prev = i
    if start is not None:
        out.append(f"{start}-{prev}" if start != prev else f"{start}")
    return ", ".join(out) if out else "none"


def layer_summary(layers):
    if not layers:
        return "n/a"
    amx = [ix for ix, a, v, f in layers if a > 0]
    fpga = [ix for ix, a, v, f in layers if f > 0]
    avx = [ix for ix, a, v, f in layers if v > 0]
    n = len(layers)
    return (f"{n} layers; AMX K tokens > 0 in {len(amx)} (layers {ranges(amx)}); FPGA > 0 in {len(fpga)} "
            f"(layers {ranges(fpga)}); AVX > 0 in {len(avx)}")


def main():
    res = sys.argv[1] if len(sys.argv) > 1 else "."
    rr = os.path.join(res, "rt-results.txt")
    if not os.path.exists(rr):
        print(f"# no rt-results.txt in {res}")
        return 1
    runs = parse_results(rr)
    # the last complete record per (cell, attn, arm, rep)
    done = {}
    for r in runs:
        if r["kind"] != "rt" or r["failed"] or r["stopped"] or not r["tps"]:
            continue
        done[(r["cell"], r["attn"], r["arm"], r["rep"])] = r
    for k, r in done.items():
        r["log"] = os.path.join(res, "rt", f"{r['cell']}__{r['attn']}__{r['arm']}__rep{r['rep']}.log")
        r["stats"] = parse_stats(r["log"])
        hz = (r["stats"]["model"] or {}).get("tsc_hz")
        r["d"] = {c: derived(v, hz) for c, v in r["stats"]["classes"].items()}
        r["tps_mean"] = statistics.mean(r["tps"]) if r["tps"] else None
        r["ttft_mean"] = statistics.mean(r["ttft"]) if r["ttft"] else None
    attempts_failed = [r for r in runs if r["kind"] == "rt" and (r["failed"] or r["stopped"])]
    failed = [r for r in attempts_failed if (r["cell"], r["attn"], r["arm"], r["rep"]) not in done]
    n_reps = max([r["rep"] for r in done.values()] or [0])
    cells = []
    for r in done.values():
        c = (r["cell"], r["attn"], r["model"], r["prompt"], r["users"], r["tp"])
        if c not in cells:
            cells.append(c)
    cells.sort(key=lambda c: (c[3], c[0]))
    name = os.path.basename(os.path.abspath(res))
    tip = next((r["version"] for r in done.values() if r["version"]), "?")

    def pair(cell, attn):
        """The first repetition's amxon and amxoff runs of a cell (the identity check needs one pair; extra reps are listed in the tables)."""
        on = sorted([r for (c, a, arm, rep), r in done.items() if c == cell and a == attn and is_on(arm)], key=lambda r: r["rep"])
        off = sorted([r for (c, a, arm, rep), r in done.items() if c == cell and a == attn and is_off(arm)], key=lambda r: r["rep"])
        if len(on) > 1 or len(off) > 1:
            print(f"note: {cell} {attn} has {len(on)} on / {len(off)} off runs; the pair uses repetition {on[0]['rep'] if on else '?'}", file=sys.stderr)
        return (on[0] if on else None), (off[0] if off else None)

    L = []
    p = L.append
    p(f"# Attention path stats: AMX kernel enabled vs disabled ({name})")
    p("")
    p("## Short version")
    p("")
    p(f"Tron main {tip} ran on our half of delphi-3bda with the attention path stats on (TRON_ATTN_STATS=1). "
      f"Each cell ran twice: with the AMX kernel enabled (amxon) and with it disabled by the kill switch (amxoff, TRON_AMX_DISABLE=1). "
      f"Cells: {len(cells)}. Runs finished: {len(done)}. Runs failed or stopped: {len(failed)}." + (f" Repetitions: {n_reps}; the pairs below use repetition 1." if n_reps > 1 else ""))
    # headline facts per situation
    heads = []
    for (cell, attn, model, prompt, users, tp) in cells:
        on, off = pair(cell, attn)
        if not on or "decode_like" not in on["d"] or not on["d"]["decode_like"]:
            continue
        d = on["d"]["decode_like"]
        share = pct(d["k_amx"], d["k_all"])
        tpsd = ""
        if off and off["tps_mean"] and on["tps_mean"]:
            tpsd = f"; TPS with AMX disabled {100.0 * (off['tps_mean'] / on['tps_mean'] - 1):+.1f} %"
        heads.append(f"{short_model(model)}, {attn_word(attn)}, prompt {prompt}, {users} users ({cell}): AMX scored {share} of the decode K tokens "
                     f"({fnum(d['k_amx'])} of {fnum(d['k_all'])}){tpsd}.")
    for h in heads:
        p(f"- {h}")
    p("")
    p("## Words used here")
    p("")
    p("- tron = the inference program under test. runtron = its command-line tool. One runtron process per run prints the stats to stderr at exit.")
    p("- AMX, AVX = two CPU instruction sets. The AMX kernel scores dense KV pages. The AVX software loop scores every other page.")
    p("- FPGA attention (AoF, attention on the FPGA) = the FPGA card scores the keys it holds. The CPU scores the rest: the pending pages, queries below the engagement point (position 127), and any 1024-token shard the card could not hold (the 'lose HW attention' warning).")
    p("- amxon = TRON_AMX_DISABLE unset. The AMX kernel is available.")
    p("- amxoff = TRON_AMX_DISABLE=1, the kill switch. Same binary; every page goes to the AVX loop.")
    p("- attn=cpu = USE_HW_ATTN=0, software attention on the CPU for every model.")
    p("- attn=fpga = USE_HW_ATTN unset, the model default: FPGA attention for generated plugins (gpt-oss, qwen3), CPU attention for llama.")
    p("- attn=fpga1 = USE_HW_ATTN=1, FPGA attention forced on (used for the llama control; the engagement point stays 127).")
    p("- visit = one (token job, KV head, page) scoring step of the software loop. K tokens = the keys that step scored.")
    p("- software scale = K tokens counted once per KV head, the unit of the AVX and AMX counters. The FPGA counts K tokens once per query (all KV heads at once). The report multiplies the FPGA count by n_kv_heads (fpga_k_tokens_x_kv_heads) to put it on the software scale.")
    p("- ready / pending = the two software passes of one attention job: the ready pass over pages whose K/V were written before this forward, and the pending pass, after the K/V wait, over the pages written in this forward.")
    p("- avx_full_page visits = AVX visits that scored a whole page (64 K tokens). With the kernel enabled these are full pages that failed the dense-page test, for example a page written in this forward. With the kill switch they also include every page the kernel would have taken. The identity in section 3 uses that.")
    p("- decode_like = forwards where every token job has a listener (decode steps). prompt_or_mixed = forwards with at least one job without a listener (prompt chunks).")
    p("- token_jobs_by_path_set = how many token jobs of the class touched which combination of paths in a forward.")
    p("- T1 = forward wall time.")
    p("- busy = T2, the time one worker spent inside one attention job: both software passes and the join, without the upstream K/V wait (the wait for the K/V of this forward before the pending pass).")
    p("- join wait = T5, the time inside busy spent waiting for peer workers or the card with no join progress.")
    p("- T4 per forward = the sum, over the layers of one forward, of the time from the first attention job of one layer to the first attention job of the next layer, as attention worker 0 sees it. The last layer has no successor, so the sum covers n_layers - 1 layers.")
    p("- kv_mul = query heads per KV head (GQA). head_size = elements per head.")
    p("- fitting shape = head size 128 and kv_mul 4, the only geometry the AMX kernel is compiled for (shape_ok in h/tron/kernels/amx_attn_iface.hpp:148-150 at main). llama-3.1-8b and qwen3-4b fit. gpt-oss-120b (head size 64, kv_mul 8) does not, so it cannot record an AMX visit in either arm.")
    p("- amx_available = the process-level probe (CPU support and the kill switch). It is not the shape verdict.")
    p("- card layers = hw_slots of the 'HW attention enabled' line, the layers the FPGA serves. gpt-oss has 18 card layers and 18 sliding-window layers (window 128) that always run in software.")
    p("")
    p("## 1. What ran")
    p("")
    p("| cell | model | kv heads / kv_mul / head size / layers | kernel shape | attention asked | card (log) | card layers | prompt | users | AMX compiled / available (amxon) | available (amxoff) | TPS amxon | TPS amxoff | TTFT amxon s | TTFT amxoff s |")
    p("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for (cell, attn, model, prompt, users, tp) in cells:
        on, off = pair(cell, attn)
        hm = next((r["stats"]["model"] for r in (on, off) if r and r["stats"]["model"]), {})
        geom = f"{hm.get('n_kv_heads', '?')} / {hm.get('kv_mul', '?')} / {hm.get('head_size', '?')} / {hm.get('n_layers', '?')}" if hm else "no exit report"
        shape = "fitting" if fits(hm) else "non-fitting" if hm else "n/a"
        hwl = next((r["stats"]["hw_line"] for r in (on, off) if r and r["stats"]["hw_line"]), None) or (on or off or {}).get("hw_attn")
        card = "on" if (hwl or "").startswith("HW attention enabled") else "off" if hwl else "no line"
        hf = hw_fields(hwl)
        card_layers = f"{hf['hw_slots']} of {hf.get('max_layers', hm.get('n_layers', '?'))}" if "hw_slots" in hf else "0" if card == "off" else "n/a"
        avail_on = f"{yesno(on['stats']['model'].get('amx_compiled'))} / {yesno(on['stats']['model'].get('amx_available'))}" if on and on["stats"]["model"] else "n/a"
        avail_off = yesno(off["stats"]["model"].get("amx_available")) if off and off["stats"]["model"] else "n/a"
        p(f"| {cell} | {short_model(model)} | {geom} | {shape} | {attn_word(attn)} | {card} | {card_layers} | {prompt} | {users} | {avail_on} | {avail_off} | "
          f"{fnum(on['tps_mean'], 2) if on else 'n/a'} | {fnum(off['tps_mean'], 2) if off else 'n/a'} | "
          f"{fnum(on['ttft_mean'], 2) if on else 'n/a'} | {fnum(off['ttft_mean'], 2) if off else 'n/a'} |")
    p("")
    p("TPS = generated tokens per second per user, mean over users (runtron 'average tok/s'). TTFT = prompt parsing time in seconds, mean over users. One repetition per cell: a TPS difference of a few percent cannot be separated from run-to-run variation here.")
    p("")
    p("HW attention line and HBM warnings per cell (the line is the first 'HW attention' line of the run's log):")
    p("")
    for (cell, attn, model, prompt, users, tp) in cells:
        on, off = pair(cell, attn)
        r = on or off
        if r:
            hwl = r["stats"]["hw_line"] or r["hw_attn"] or "no HW attention line"
            warn = ""
            if attn in ("fpga", "fpga1") and not hwl.startswith("HW attention enabled"):
                warn = " WARNING: the cell asked for FPGA attention but tron ran with the card off."
            hb = f"HBM warnings amxon lose={on['hbm_lose']} exhausted={on['hbm_exh']}" if on else "amxon missing"
            hb += f"; amxoff lose={off['hbm_lose']} exhausted={off['hbm_exh']}" if off else "; amxoff missing"
            p(f"- {cell}: {hwl}. {hb}.{warn}")
    p("")
    p("## 2. K tokens by path, AMX enabled vs disabled")
    p("")
    p("Per cell and class: the K tokens each path scored (software scale), the shares, and the visit counts. Shares are of the row's total K tokens (AMX + AVX + FPGA).")
    p("")
    p("| cell | class | arm | K tokens AMX | share | K tokens AVX | share | K tokens FPGA (x kv heads) | share | visits AMX (ready+pending) | visits AVX | avx_full_page visits | empty visits | FPGA query passes |")
    p("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for (cell, attn, model, prompt, users, tp) in cells:
        for cls in ("decode_like", "prompt_or_mixed"):
            for (c, a, arm, rep), r in sorted(done.items(), key=lambda kv: (not is_on(kv[0][2]), kv[0][2])):
                if c != cell or a != attn:
                    continue
                d = r["d"].get(cls)
                if not d:
                    p(f"| {cell} | {cls} | {arm} | no exit report | | | | | | | | | | |")
                    continue
                p(f"| {cell} | {cls} | {arm} | {fnum(d['k_amx'])} | {pct(d['k_amx'], d['k_all'])} | {fnum(d['k_avx'])} | {pct(d['k_avx'], d['k_all'])} | "
                  f"{fnum(d['k_fpga'])} | {pct(d['k_fpga'], d['k_all'])} | {fnum(d['v_amx'])} ({fnum(d['v_ready_amx'])}+{fnum(d['v_pending_amx'])}) | {fnum(d['v_avx'])} | "
                  f"{fnum(d['v_avx_full'])} | {fnum(d['v_empty'])} | {fnum(d['fpga_passes'])} |")
    p("")
    p("## 3. Kill-switch identity")
    p("")
    p("When both arms scored the same prompts, generated the same number of tokens (--dont-stop) and had the same HBM warning counts, every dense page the kernel took in amxon is an AVX full-page visit in amxoff. "
      "So avx_full_page(amxoff) must equal amx_visits(amxon) + avx_full_page(amxon). The AVX K tokens of amxoff must equal the AMX + AVX K tokens of amxon. A mismatch means the two runs did not score the same positions, or a counter defect. For a non-fitting shape both arms have 0 AMX visits and the identity degenerates to equal counts.")
    p("")
    p("| cell | class | amx visits (on) | avx_full_page (on) | avx_full_page (off) | visits identity | K tokens AMX+AVX (on) | K tokens AVX (off) | K identity | FPGA K tokens on / off |")
    p("|---|---|---|---|---|---|---|---|---|---|")
    for (cell, attn, model, prompt, users, tp) in cells:
        on, off = pair(cell, attn)
        for cls in ("decode_like", "prompt_or_mixed"):
            don = on["d"].get(cls) if on else None
            doff = off["d"].get(cls) if off else None
            if not don or not doff:
                p(f"| {cell} | {cls} | {'n/a' if not don else fnum(don['v_amx'])} | | {'n/a' if not doff else fnum(doff['v_avx_full'])} | one arm missing | | | | |")
                continue
            vid = "holds" if doff["v_avx_full"] == don["v_amx"] + don["v_avx_full"] else f"MISMATCH ({doff['v_avx_full'] - don['v_amx'] - don['v_avx_full']:+,})"
            kid = "holds" if doff["k_avx"] == don["k_amx"] + don["k_avx"] else f"MISMATCH ({doff['k_avx'] - don['k_amx'] - don['k_avx']:+,})"
            p(f"| {cell} | {cls} | {fnum(don['v_amx'])} | {fnum(don['v_avx_full'])} | {fnum(doff['v_avx_full'])} | {vid} | {fnum(don['k_amx'] + don['k_avx'])} | {fnum(doff['k_avx'])} | {kid} | {fnum(don['k_fpga'])} / {fnum(doff['k_fpga'])} |")
    p("")
    p("## 4. Token jobs by path set")
    p("")
    p("How many token jobs of a class touched which paths within a forward (a job may use several paths across its pages and layers).")
    p("")
    p("| cell | class | arm | token jobs | forwards | FPGA queries | " + " | ".join(PATH_SETS) + " |")
    p("|---|---|---|---|---|---|" + "---|" * len(PATH_SETS))
    for (cell, attn, model, prompt, users, tp) in cells:
        for cls in ("decode_like", "prompt_or_mixed"):
            for (c, a, arm, rep), r in sorted(done.items(), key=lambda kv: (not is_on(kv[0][2]), kv[0][2])):
                if c != cell or a != attn:
                    continue
                d = r["d"].get(cls)
                if not d:
                    continue
                p(f"| {cell} | {cls} | {arm} | {fnum(d['token_jobs'])} | {fnum(d['forwards'])} | {fnum(d['fpga_queries'])} | "
                  + " | ".join(fnum(d["sets"].get(s, 0)) for s in PATH_SETS) + " |")
    p("")
    p("## 5. Per-layer pattern")
    p("")
    p("From the 'k_tokens per layer' line of the exit report (ready + pending, summed over workers). Layers with FPGA > 0 are the layers the card served. Layers with AMX > 0 are the layers where the kernel ran. AMX and AVX are K tokens per KV head. The FPGA value is per query (all KV heads at once); multiply it by n_kv_heads (8 for all three models) to compare it with the other two.")
    p("")
    for (cell, attn, model, prompt, users, tp) in cells:
        for (c, a, arm, rep), r in sorted(done.items(), key=lambda kv: (not is_on(kv[0][2]), kv[0][2])):
            if c != cell or a != attn:
                continue
            for cls in ("decode_like", "prompt_or_mixed"):
                cl = r["stats"]["classes"].get(cls)
                if cl and cl.get("layers"):
                    p(f"- {cell} {arm} {cls}: {layer_summary(cl['layers'])}")
                    lay = cl["layers"]
                    vals = sorted(set((a_, v_, f_) for ix, a_, v_, f_ in lay))
                    if len(vals) <= 4:
                        p(f"  - distinct per-layer (amx/avx/fpga) triples: " + "; ".join(f"{a_:,}/{v_:,}/{f_:,} in layers {ranges([ix for ix, aa, vv, ff in lay if (aa, vv, ff) == (a_, v_, f_)])}" for a_, v_, f_ in vals))
    p("")
    p("## 6. Time")
    p("")
    p("Cycles are converted with tsc_hz of the run.")
    p("")
    p("- T1 ms per forward = forward wall time per forward.")
    p("- busy s = T2 summed over all workers and jobs of the class. busy ms per job = T2 per attention job (both software passes and the join, without the upstream K/V wait).")
    p("- join wait share = T5 / T2.")
    p("- T4 ms per forward = the layer-to-layer periods on attention worker 0, summed per forward (n_layers - 1 periods).")
    p("")
    p("| cell | class | arm | forwards | T1 ms per forward | busy s (all workers) | busy ms per job | join wait share | T4 ms per forward |")
    p("|---|---|---|---|---|---|---|---|---|")
    for (cell, attn, model, prompt, users, tp) in cells:
        for cls in ("decode_like", "prompt_or_mixed"):
            for (c, a, arm, rep), r in sorted(done.items(), key=lambda kv: (not is_on(kv[0][2]), kv[0][2])):
                if c != cell or a != attn:
                    continue
                d = r["d"].get(cls)
                if not d:
                    continue
                p(f"| {cell} | {cls} | {arm} | {fnum(d['forwards'])} | {fnum(d['t1_ms_per_fwd'], 2)} | {fnum(d['busy_s'], 2)} | {fnum(d['busy_ms_per_job'], 3)} | "
                  f"{pct(d['join_share'], 1.0) if d['join_share'] is not None else 'n/a'} | {fnum(d['t4_ms_per_fwd'], 2)} |")
    p("")
    p("## 7. Situations")
    p("")
    for title, pick in (("7.1 Attention on the FPGA (gpt-oss, qwen3)", lambda c: c[1] in ("fpga", "fpga1") and "l8b" not in c[0]),
                        ("7.2 Pure software attention (llama-3.1)", lambda c: c[1] == "cpu" and "l8b" in c[0]),
                        ("7.3 Fitting shape (llama-3.1, qwen3) vs non-fitting shape (gpt-oss), CPU attention controls", lambda c: c[1] == "cpu"),
                        ("7.4 Other controls (llama with USE_HW_ATTN=1)", lambda c: c[1] in ("fpga", "fpga1") and "l8b" in c[0])):
        p(f"### {title}")
        p("")
        any_ = False
        for cc in cells:
            if not pick(cc):
                continue
            cell, attn, model, prompt, users, tp = cc
            on, off = pair(cell, attn)
            if not on:
                p(f"- {cell}: amxon run missing.")
                continue
            any_ = True
            hm = on["stats"]["model"] or {}
            if not any(on["d"].values()):
                p(f"- {cell}: the amxon run finished but its log has no [attn-stats] exit report ({on['log']}).")
                continue
            shape = "fitting" if fits(hm) else "non-fitting"
            hwl = on["stats"]["hw_line"] or on["hw_attn"] or ""
            hf = hw_fields(hwl)
            card = f"card on, {hf['hw_slots']} of {hf.get('max_layers', hm.get('n_layers', '?'))} layers" if "hw_slots" in hf else ("card on" if hwl.startswith("HW attention enabled") else "card off")
            if attn in ("fpga", "fpga1") and not hwl.startswith("HW attention enabled"):
                p(f"- {cell}: WARNING, the cell asked for {attn_word(attn)} but tron ran with the card off ({hwl or 'no HW attention line'}).")
            for cls in ("decode_like", "prompt_or_mixed"):
                d = on["d"].get(cls)
                if not d:
                    continue
                doff = off["d"].get(cls) if off else None
                p(f"- {cell} ({short_model(model)}, {shape} shape: kv_mul {hm.get('kv_mul', '?')}, head size {hm.get('head_size', '?')}; {card}; amx_available {yesno(hm.get('amx_available'))}), {cls}, amxon: "
                  f"AMX {pct(d['k_amx'], d['k_all'])} of the K tokens ({fnum(d['v_amx'])} visits). AVX {pct(d['k_avx'], d['k_all'])}. FPGA {pct(d['k_fpga'], d['k_all'])}.")
                lay = (on["stats"]["classes"].get(cls) or {}).get("layers")
                if lay and any(f_ > 0 for ix, a_, v_, f_ in lay) and any(f_ == 0 for ix, a_, v_, f_ in lay):
                    avx_card = sum(v_ for ix, a_, v_, f_ in lay if f_ > 0)
                    avx_sw = sum(v_ for ix, a_, v_, f_ in lay if f_ == 0)
                    p(f"  - AVX K tokens split by layer kind: {fnum(avx_card)} in the card layers, {fnum(avx_sw)} in the software-only layers.")
                if doff:
                    p(f"  - amxoff: AVX {pct(doff['k_avx'], doff['k_all'])}, FPGA {pct(doff['k_fpga'], doff['k_all'])}, avx_full_page visits {fnum(doff['v_avx_full'])}.")
                    if d["busy_ms_per_job"]:
                        p(f"  - Busy per job goes from {fnum(d['busy_ms_per_job'], 3)} ms (amxon) to {fnum(doff['busy_ms_per_job'], 3)} ms (amxoff), {pct(doff['busy_ms_per_job'], d['busy_ms_per_job'])} of amxon.")
            if on["tps_mean"] and off and off["tps_mean"]:
                p(f"  - TPS {fnum(on['tps_mean'], 2)} (amxon) vs {fnum(off['tps_mean'], 2)} (amxoff), {100.0 * (off['tps_mean'] / on['tps_mean'] - 1):+.1f} % for the kill switch.")
        if not any_:
            p("- no finished cell in this group.")
        p("")
    p("## 8. Failed or stopped runs")
    p("")
    p("Runs with no complete attempt:")
    p("")
    if failed:
        for r in failed:
            p(f"- {r['cell']} {r['attn']} {r['arm']} rep{r['rep']} attempt {r['attempt']}: {'failed' if r['failed'] else 'stopped'} ({r['started']})")
    else:
        p("- none")
    retried = [r for r in attempts_failed if r not in failed]
    if retried:
        p("")
        p("Attempts that failed or were stopped before a later attempt completed:")
        p("")
        for r in retried:
            p(f"- {r['cell']} {r['attn']} {r['arm']} rep{r['rep']} attempt {r['attempt']}: {'failed' if r['failed'] else 'stopped'} ({r['started']})")
    p("")
    p("## 9. Files")
    p("")
    p(f"- results: exec/results/{name}/ (rt-results.txt, rt/<run>.log, exit-reports.txt, leaves/<run>/ = in-flight FUSE leaf snapshots for the worker and layer rows, possibly absent for short runs, not used by this report)")
    p(f"- scripts: exec/attnstats-20261002/ (chain.sh, campaign.sh, gen_compare.py, launch.sh, README.md)")
    p(f"- binary: runtron.main1002 built from main {tip} with -DTRON_AMX_DISPATCH=ON (see build-main1002.txt)")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    sys.exit(main())
