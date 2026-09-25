#!/usr/bin/env python3
"""Map the engine journal's HBM-exhaustion warnings onto the CI-harness cells of the q4b-fpga-20260921 campaign.

Reads every journal file named on the command line (default: exec/results/q4b-fpga-20260921/hbm-journal-*.txt, pulled with
journalctl -u 'rinzler@*' on delphi-3bda) and every <tag>/perf.json of the campaign, and writes hbm-exhaustion-cells.json next
to this script.  gen_page.py reads that file (hbm_subsection).

Words: a "lose" warning = one line "shard base tok_ix N: 36 of 36 slots lose HW attention" (one shard on one card could not be
placed on the card and its attention ran on the CPU).  A "bypass" line = the preceding "HBM bypass space exhausted; caller
degrades to SW attention (requires 0x10000B, only 0x.... available)" line.  A cell = one config of one driver run, with the
harness's t_start / t_end (epoch seconds) from perf.json raw[].  The AMX probe = the driver's 20 s perf-stat window before every
cell, which sends its own 4 streaming requests; warnings in a probe window are "outside" cells.
"""
import datetime as dt
import glob
import json
import math
import os
import re
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RES = "/home/jhan/workspace/intel-AMX/exec/results/q4b-fpga-20260921"
GEN_TOKENS = 1536          # generated tokens per request in every cell of configs-full.json / cold-p*.json
SHARD_TOKENS = 1024
USERS = 8
ROUNDS = 10


def parse_journal(paths):
    lose, bypass = [], []
    for p in paths:
        for l in open(p):
            if "lose HW attention" in l:
                kind = "lose"
            elif "HBM bypass space exhausted" in l:
                kind = "bypass"
            else:
                continue
            m = re.match(r"(\d{4}-\d\d-\d\d)T\d\d:\d\d:\d\d\+0000 \S+ rinzler\[\d+\]: \[(\d\d:\d\d:\d\d\.\d+)\|rz(\d)", l)
            if not m:
                continue
            day, hms, rz = m.group(1), m.group(2), int(m.group(3))
            # the journal prefix (second resolution) and the in-line clock (ns) can disagree across midnight
            t = dt.datetime.fromisoformat(f"{day}T{hms[:15]}").replace(tzinfo=dt.timezone.utc).timestamp()
            ph, ih = int(l[11:13]), int(hms[:2])
            if ph == 23 and ih == 0:
                t += 86400
            elif ph == 0 and ih == 23:
                t -= 86400
            rec = dict(t=t, rz=rz)
            if kind == "lose":
                mb = re.search(r"shard base tok_ix (\d+)", l)
                rec["tok_base"] = int(mb.group(1)) if mb else None
                lose.append(rec)
            else:
                ma = re.search(r"only 0x([0-9a-fA-F]+) available", l)
                rec["avail"] = int(ma.group(1), 16) if ma else None
                md = re.search(r"dev(?:ice)?\s*(\d)", l)
                bypass.append(rec)
    return lose, bypass


def round_starts(tag):
    """Epoch of every 'Running round (k/10)' line of the driver log, grouped per cell in run order."""
    out, cur = [], None
    for l in open(f"{RES}/{tag}/driver.log"):
        if "AMX probe" in l and "amx_busy=" in l:
            cur = []
            out.append(cur)
            continue
        m = re.search(r"\[(\d\d/\w+/\d{4} \d\d:\d\d:\d\d) UTC\].*Running round \((\d+)/\d+\)", l)
        if m and cur is not None:
            cur.append(dt.datetime.strptime(m.group(1), "%d/%b/%Y %H:%M:%S").replace(tzinfo=dt.timezone.utc).timestamp())
    return out


def main():
    paths = sys.argv[1:] or sorted(glob.glob(f"{RES}/hbm-journal-*.txt"))
    lose, bypass = parse_journal(paths)
    cells, windows = [], []
    for pj in sorted(glob.glob(f"{RES}/*/perf.json")):
        tag = os.path.basename(os.path.dirname(pj))
        if tag.startswith("prev-") or tag == "check-mode" or tag.endswith("-failed1"):
            continue
        d = json.load(open(pj))
        rs = round_starts(tag)
        results = {x["name"]: x for x in d.get("results", [])}
        prev_end = None
        for i, r in enumerate(d["raw"]):
            ts, te, p = r["t_start"], r["t_end"], r["prompt_length"]
            w = [x for x in lose if ts <= x["t"] <= te]
            dur = te - ts
            rounds = rs[i] if i < len(rs) else []
            first = min(x["t"] for x in w) - ts if w else None
            last = max(x["t"] for x in w) - ts if w else None
            first_round = (sum(1 for q in rounds if q <= ts + first) or 1) if w else None
            shards = USERS * ROUNDS * math.ceil((p + GEN_TOKENS) / SHARD_TOKENS)
            # new shards actually placed (est.): the cached prefix of a request places no new shard, so count
            # ceil((uncached prompt tokens + generated tokens) / 1024) per request from the harness's usage data
            pts, cts = r.get("prompt_tokens") or [], r.get("cached_tokens") or []
            shards_new = sum(math.ceil((pt - ct + GEN_TOKENS) / SHARD_TOKENS) for pt, ct in zip(pts, cts)) if pts and len(cts) == len(pts) else None
            eb = ((r.get("engine_counters_before") or {}).get("counters") or {})
            free_before = [v for e in eb.values() if isinstance(e, dict) for k, v in e.items() if k.endswith("allocator/free_total") and isinstance(v, (int, float))]
            tt = r.get("ttfts_ms") or []
            per_round = [round(statistics.mean(tt[k * USERS:(k + 1) * USERS]), 1) for k in range(len(tt) // USERS)] if tt else []
            fb = [v for k in ("hbm_sw_fallback_dev0", "hbm_sw_fallback_dev1") for v in (r.get(k) or {}).values() if isinstance(v, (int, float))]
            ft = [v for v in (r.get("hbm_free_total_after") or {}).values() if isinstance(v, (int, float))]
            cells.append(dict(
                tag=tag, prompt=p, t_start=ts, t_end=te, dur_s=round(dur, 1), lose=len(w),
                fallback_counter=(sum(fb) if (r.get("hbm_sw_fallback_dev0") or r.get("hbm_sw_fallback_dev1")) else None),
                free_min_after=(min(ft) if ft else None), free_max_after=(max(ft) if ft else None),
                engines=len({x["rz"] for x in w}), tok_bases=sorted({x["tok_base"] for x in w}),
                ttft_ms=results.get(r["name"], {}).get("ttft_mean"),
                first_s=None if first is None else round(first, 1), last_s=None if last is None else round(last, 1),
                last_pct=None if last is None else round(100.0 * last / dur), first_round=first_round,
                shards_est=shards, share_est_pct=round(100.0 * len(w) / shards, 1),
                shards_new_est=shards_new, share_new_pct=(round(100.0 * len(w) / shards_new, 1) if shards_new else None),
                free_before_min=(min(free_before) if free_before else None), free_before_max=(max(free_before) if free_before else None),
                ttft_per_round_ms=per_round,
            ))
            # the gap before this cell (probe window + provisioning) inside the same driver run
            if prev_end is not None:
                g = [x for x in lose if prev_end < x["t"] < ts]
                windows.append(dict(tag=tag, after_prompt=d["raw"][i - 1]["prompt_length"], before_prompt=p,
                                    gap_s=round(ts - prev_end, 1), lose=len(g), tok_bases=sorted({x["tok_base"] for x in g})))
            prev_end = te
    inside = sum(c["lose"] for c in cells)
    avail = {}
    for b in bypass:
        avail[b["avail"]] = avail.get(b["avail"], 0) + 1
    out = dict(
        source=" ; ".join(os.path.relpath(p, "/home/jhan/workspace/intel-AMX") for p in paths),
        total_lose=len(lose), total_exhausted=len(bypass), inside_cells=inside, outside_cells=len(lose) - inside,
        first_ts=dt.datetime.fromtimestamp(min(x["t"] for x in lose), dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if lose else None,
        avail_counts={f"0x{k:x}": v for k, v in sorted(avail.items()) if k is not None},
        gen_tokens=GEN_TOKENS, shard_tokens=SHARD_TOKENS,
        cells=cells, gaps=windows,
    )
    path = os.path.join(HERE, "hbm-exhaustion-cells.json")
    json.dump(out, open(path, "w"), indent=1)
    print(path, len(cells), "cells;", len(lose), "lose,", inside, "inside,", len(lose) - inside, "outside;", "avail", out["avail_counts"])
    for c in cells:
        if c["lose"]:
            print(f'{c["tag"]:22s} p{c["prompt"]:5d} lose {c["lose"]:4d} first +{c["first_s"]} s (round {c["first_round"]}) last {c["last_pct"]} % of {c["dur_s"]} s, {c["share_est_pct"]} % of {c["shards_est"]} shards est.')
    for g in windows:
        if g["lose"]:
            print(f'gap {g["tag"]:22s} after p{g["after_prompt"]} before p{g["before_prompt"]}: {g["lose"]} lose, bases {g["tok_bases"]}, gap {g["gap_s"]} s')


if __name__ == "__main__":
    main()
