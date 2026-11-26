#!/usr/bin/env python3
"""Verifier (cost lens): recompute the cost claims C01-C17 and correct them with measurements
that exist on disk but were not used by the specification.

Inputs that are MEASUREMENTS on delphi-3b35 (read from files, 2026-11-20):
  P  = /home/jhan/workspace/intel-AMX/exec/results/gdn-20261120/bench/clock-probe.txt, clock-probe2.txt
       (core clock and instruction times under AVX-512 FMA, tile products, and mixes; cpu 140)
  TR = /home/jhan/workspace/intel-AMX/exec/results/gdn-20261120/trace/*.summary.json
       (GatedDeltaNet slices of traced runtron runs: wall share of a pass, CPU time per group step)
Inputs that are the task's givens: M1, M2, M3, C1-C6.
Everything derived is an estimate (est.) and prints its arithmetic.
"""
import glob
import json
import re

RES = "/home/jhan/workspace/intel-AMX/exec/results/gdn-20261120"
GHZ = 2.70
M1_US, CONV_US, NVH = 102.1, 8.15, 32
TDP, TLOAD, TSTORE, TZERO = 16.2, 8.4, 16.1, 0.5
out = {}


def hdr(s):
    print("\n" + s)
    print("-" * len(s))


# ------------------------------------------------------------------ measured files
hdr("MEASURED ON delphi-3b35 (files P)")
probe = {}
for fn in ("clock-probe.txt", "clock-probe2.txt"):
    for line in open(f"{RES}/bench/{fn}"):
        m = re.match(r"(\S+)-(\d+) \| freq_khz_median (\d+)", line)
        if m:
            probe.setdefault(m.group(1), []).append((int(m.group(3)), line))
        m = re.match(r"insn-(\S+) \| freq_khz_median (\d+) .* ns_per_insn (\S+) tsc_ticks_per_insn (\S+)", line)
        if m:
            probe["insn_" + m.group(1)] = (int(m.group(2)), float(m.group(3)), float(m.group(4)))
        m = re.match(r"gdn-recurrence-\d+ \| .* ms\s+(\S+) us", line)
        if m:
            probe.setdefault("rec_us", []).append(float(m.group(1)))
        m = re.match(r"gdn-conv-\d+ \| .* ms\s+(\S+) us", line)
        if m:
            probe.setdefault("conv_us", []).append(float(m.group(1)))


def med(xs):
    xs = sorted(xs)
    return xs[len(xs) // 2]


def field(line, name):
    return float(re.search(name + r" (\S+)", line).group(1))


f_fma = med([k for k, _ in probe["fma"]]) / 1e6
f_tdp_dirty = med([k for k, _ in probe["tdp"]]) / 1e6
f_tdp_clean = med([k for k, _ in probe["tdpz"]]) / 1e6
f_mix = med([k for k, _ in probe["mix"]]) / 1e6
f_mixz = med([k for k, _ in probe["mixz"]]) / 1e6
f_mixzp = med([k for k, _ in probe["mixzp"]]) / 1e6
ticks_fma = med([field(l, "ticks_per_fma") for _, l in probe["fma"]])
ns_tdp_clean = med([field(l, "ns_total_per_tdp") for _, l in probe["tdpz"]])
ns_tdp_dirty = med([field(l, "ns_per_tdp") for _, l in probe["tdp"]])
ticks_round_mix = med([field(l, "ticks_per_round") for _, l in probe["mix"]])
ticks_tdp_dirty = med([field(l, "ticks_per_tdp") for _, l in probe["tdp"]])
print(f"  AVX-512 FMA loop (8 chains, registers): clock {f_fma:.3f} GHz; {ticks_fma:.4f} cycles per FMA = {1 / ticks_fma:.2f} FMA per cycle"
      f"  (C3 assumed 2.00 per cycle)")
print(f"  tile products only, upper vector halves cleared: clock {f_tdp_clean:.3f} GHz ({(f_tdp_clean / f_fma - 1) * 100:+.1f} %);"
      f" {ns_tdp_clean:.3f} ns = {ns_tdp_clean * f_tdp_clean:.2f} cycles per TDPBF16PS")
print(f"  tile products with live 512-bit registers:        clock {f_tdp_dirty:.3f} GHz ({(f_tdp_dirty / f_fma - 1) * 100:+.1f} %);"
      f" {ns_tdp_dirty:.3f} ns = {ns_tdp_dirty * f_tdp_dirty:.2f} cycles per TDPBF16PS")
print(f"  4 tile products then 64 FMAs, repeated (fine mix): clock {f_mix:.3f} GHz (registers) / {f_mixz:.3f} GHz (memory accumulators + vzeroupper)")
print(f"     one round = {ticks_round_mix:.2f} TSC ticks; 4 tile products alone = {4 * ticks_tdp_dirty:.2f} ticks -> the 64 FMAs add"
      f" {ticks_round_mix - 4 * ticks_tdp_dirty:+.2f} ticks (they overlap the tile products)")
print(f"  4,096 tile products then 16,384 FMAs, repeated (phases of about 25 us): clock {f_mixzp:.3f} GHz")
tp, lat, tld, vdp = probe["insn_tdp_tp"], probe["insn_tdp_lat"], probe["insn_tld_l1"], probe["insn_vdp_tp16"]
print(f"  TDPBF16PS, 4 destination tiles in turn: {tp[2]:.3f} ticks; same destination tile 4 times: {lat[2]:.3f} ticks"
      f" -> no penalty for consecutive products on one accumulator ({tp[2] * tp[0] / 2.7e6:.2f} cycles each at {tp[0] / 1e6:.3f} GHz)")
print(f"  TILELOADD from L1: {tld[2]:.3f} cycles at {tld[0] / 1e6:.2f} GHz; VDPBF16PS: {vdp[2]:.3f} cycles at {vdp[0] / 1e6:.2f} GHz")
print(f"  recurrence benchmark re-run on cpu 140: {', '.join(f'{x:.1f}' for x in probe['rec_us'])} us per token per layer (M1: {M1_US});"
      f" convolution: {', '.join(f'{x:.2f}' for x in probe['conv_us'])} us (M1: {CONV_US})")
R_CLEAN, R_DIRTY = f_tdp_clean / f_fma, f_tdp_dirty / f_fma
out["probe"] = dict(f_fma=f_fma, f_tdp_clean=f_tdp_clean, f_tdp_dirty=f_tdp_dirty, cycles_per_fma=ticks_fma,
                    tdp_same_dst_ticks=lat[2], tdp_indep_ticks=tp[2], rec_us=probe["rec_us"], conv_us=probe["conv_us"])

hdr("MEASURED IN tron ON delphi-3b35, traced runs (files TR)")
cells = {}
for f in sorted(glob.glob(f"{RES}/trace/*.summary.json")):
    d = json.load(open(f))
    name = f.split("/")[-1].split(".")[0]
    c = {}
    for kind, k in d["kinds"].items():
        g = k["gdn"]
        c[kind] = dict(pass_ms=k["mean_pass_ms"], gdn_ms=g["wall_span_ms_per_pass"], share=g["wall_span_pct_of_pass"] / 100,
                       step_us=g["cpu_us_per_group_step"], tokens=k["token_jobs"][0])
    cells[name] = c
    print(f"  {name}: prefill pass {c['prefill']['pass_ms']:.1f} ms, GDN {c['prefill']['gdn_ms']:.2f} ms = {c['prefill']['share'] * 100:.1f} %,"
          f" {c['prefill']['step_us']:.2f} us per group step | decode forward {c['decode']['pass_ms']:.2f} ms,"
          f" GDN {c['decode']['share'] * 100:.1f} %, {c['decode']['step_us']:.2f} us per group step")
out["trace"] = cells

# ------------------------------------------------------------------ C03
hdr("C03  today's kernel: operation count and M1")
fma_ops = 128 * 8 + 2 * 128 * 8      # loop 1: one FMA per row and chunk; loop 2: two
mul_ops = 128 * 8 + 128 * 8          # one decay multiply per row and chunk in each loop
ops = fma_ops + mul_ops
M1_CYC = M1_US / NVH * GHZ * 1e3
print(f"  loops of gated_delta_net.hpp:266-294: {fma_ops} FMA + {mul_ops} multiplies = {ops} zmm operations per token per value head (spec: 5,120)")
print(f"  at 2.00 per cycle: {ops / 2:.0f} cycles; at the measured {1 / ticks_fma:.2f} per cycle (P): {ops * ticks_fma:.0f} cycles")
print(f"  M1: {M1_US} us / 32 x {GHZ} GHz = {M1_CYC:.0f} cycles; probe re-run: "
      f"{min(probe['rec_us']) / NVH * GHZ * 1e3:.0f} to {max(probe['rec_us']) / NVH * GHZ * 1e3:.0f} cycles")
PRELUDE = 280.0  # est.; measured 258 cycles on the design host (bench_gdn.c section 3), a different CPU
print(f"  not in the 5,120 count but inside M1: the prelude (normalize q or k, decay, beta) est. {PRELUDE:.0f} cycles per value head"
      f" (measured 258 cycles on the design host, another CPU)")
LINE = (M1_CYC - ops / 2) / 2048
LINE_P = (M1_CYC - ops / 2 - PRELUDE) / 2048
LINE_PF = (M1_CYC - ops * ticks_fma - PRELUDE) / 2048
print(f"  line cost: spec ({M1_CYC:.0f} - 2,560) / 2,048 = {LINE:.2f}; with the prelude removed {LINE_P:.2f}; with the measured FMA rate too {LINE_PF:.2f} cycles per line")
tr_step = sum(c["prefill"]["step_us"] for c in cells.values()) / len(cells)
conv_p = sum(probe["conv_us"]) / len(probe["conv_us"])
print(f"  in tron (TR): prefill group step {tr_step:.2f} us for 2 value heads + convolution + postprocess."
      f" From M1: 2 x {M1_US / NVH:.3f} + {CONV_US}/16 = {2 * M1_US / NVH + CONV_US / 16:.2f} us. Ratio measured / M1-based = {tr_step / (2 * M1_US / NVH + CONV_US / 16):.3f}")
dec_steps = [c["decode"]["step_us"] for c in cells.values()]
print(f"  in tron (TR): decode group step {min(dec_steps):.1f} to {max(dec_steps):.1f} us = {min(dec_steps) / tr_step:.1f}x to {max(dec_steps) / tr_step:.1f}x the prefill step"
      " (same arithmetic + one NaN scan; the state then comes from L3 or DRAM) -> the kernel time follows where the state comes from")
out["C03"] = dict(ops=ops, m1_cycles=M1_CYC, line=LINE, prefill_step_us=tr_step, decode_step_us=dec_steps)

# ------------------------------------------------------------------ C05 slice replay
hdr("C05  slice replay (G1), cycles per token per value head")
g1_lo_spec, g1_hi_spec = ops / 2, ops / 2 + 80 * LINE
print(f"  spec: {g1_lo_spec:.0f} to {g1_lo_spec:.0f} + 80 x {LINE:.2f} = {g1_hi_spec:.0f}; {M1_CYC / g1_hi_spec:.2f}x to {M1_CYC / g1_lo_spec:.2f}x against M1")
g1_lo = ops / 2
g1_hi = ops * ticks_fma + 80 * LINE
print(f"  loops, corrected upper end: {ops} x {ticks_fma:.4f} (measured FMA rate, P) + 80 x {LINE:.2f} = {g1_hi:.0f}")
print(f"  with the prelude (it is inside M1): {g1_lo + PRELUDE:.0f} to {g1_hi + PRELUDE:.0f} cycles ->"
      f" {M1_CYC / (g1_hi + PRELUDE):.2f}x to {M1_CYC / (g1_lo + PRELUDE):.2f}x against M1 (spec: 3.1x to 3.4x)")
out["G1"] = dict(loops=(g1_lo, g1_hi), with_prelude=(g1_lo + PRELUDE, g1_hi + PRELUDE),
                 speedup_vs_m1=(M1_CYC / (g1_hi + PRELUDE), M1_CYC / (g1_lo + PRELUDE)))

# ------------------------------------------------------------------ C06 / C07 / C08 AMX block
hdr("C07 / C08  AMX block kernel (G2), C = 32, cycles per token per value head")
tiles = (384 * TDP + 224 * TLOAD + 32 * TSTORE + 32 * TZERO) / 32 + (32 * TDP + 40 * TLOAD + 8 * TSTORE + 8 * TZERO) / 2 / 32 \
    + (192 * TDP + 112 * TLOAD + 64 * TSTORE + 64 * TZERO) / 32
avx = 340.0
l1 = tiles + avx
l2 = l1 + (2048 + 2560) * LINE / 32
print(f"  spec: tiles {tiles:.0f} + AVX-512 {avx:.0f} = {l1:.0f} (every load from L1); + (2,048 + 2,560) x {LINE:.2f} / 32 = {l2:.0f}")
g2_lo = l1 + 2048 * LINE / 32
g2_hi = l2 + avx * (2 * ticks_fma - 1)
print(f"  lower end corrected: the 64 KiB state does not fit L1, so its 2,048 line fetches per block cannot be avoided:"
      f" {l1:.0f} + 2,048 x {LINE:.2f} / 32 = {g2_lo:.0f}")
print(f"  upper end corrected: AVX-512 parts at the measured FMA rate: {l2:.0f} + {avx:.0f} x ({2 * ticks_fma:.3f} - 1) = {g2_hi:.0f}")
print(f"  with the prelude: {g2_lo + PRELUDE:.0f} to {g2_hi + PRELUDE:.0f} cycles")
m1_us = M1_US / NVH
g1_us = ((g1_lo + PRELUDE) / GHZ / 1e3, (g1_hi + PRELUDE) / GHZ / 1e3)
print(f"  today (M1) {m1_us:.3f} us; slice replay with prelude {g1_us[0]:.3f} to {g1_us[1]:.3f} us at {GHZ} GHz")
print("  spec clock cases: 2.70 GHz, -7.7 %, -23 % -> 0.29 to 0.58 us; 5.5x to 11x vs M1; 1.6x to 3.6x vs G1")
g2 = {}
for label, f in (("tile phases, clean upper halves", f_tdp_clean), ("live 512-bit state or fine mix", f_tdp_dirty)):
    lo_us, hi_us = (g2_lo + PRELUDE) / f / 1e3, (g2_hi + PRELUDE) / f / 1e3
    g2[label] = (lo_us, hi_us)
    print(f"  measured clock {f:.3f} GHz ({label}): {lo_us:.3f} to {hi_us:.3f} us | vs M1 {m1_us / hi_us:.1f}x to {m1_us / lo_us:.1f}x"
          f" | vs G1 {g1_us[0] / hi_us:.2f}x to {g1_us[1] / lo_us:.2f}x")
allv = [v for pair in g2.values() for v in pair]
print(f"  corrected range over both measured clocks: {min(allv):.2f} to {max(allv):.2f} us; vs M1 {m1_us / max(allv):.1f}x to {m1_us / min(allv):.1f}x;"
      f" vs G1 {g1_us[0] / max(allv):.2f}x to {g1_us[1] / min(allv):.2f}x")
out["G2"] = dict(loops=(g2_lo, g2_hi), us=g2, vs_m1=(m1_us / max(allv), m1_us / min(allv)), vs_g1=(g1_us[0] / max(allv), g1_us[1] / min(allv)))

# ------------------------------------------------------------------ C10 / C11 forward level
hdr("C10 / C11  GDN share of a prefill pass and pass changes")
spec_cells = [("1 user, prompt 1024", "t-1u-p1024", 128, 48.1), ("1 user, prompt 4096", "t-1u-p4096", 128, 59.1),
              ("8 users, prompt 1024", "t-8u-p1024", 1024, 361.0), ("8 users, prompt 4096", "t-8u-p4096", 1024, 445.0)]
conv_us = conv_p
prel_us = NVH * PRELUDE / GHZ / 1e3
print(f"  per token per layer: convolution {conv_us:.2f} us (P), prelude est. {prel_us:.2f} us, other fixed work X = 0 to 5 us (postprocess, gather,"
      " chain copies; not measured)")
fw = {}
for name, key, tokens, pass_ms in spec_cells:
    c = cells[key]["prefill"]
    est_ms = tokens * 24 * (M1_US + CONV_US) / 16 / 1e3
    T = c["step_us"] * 16
    rows = []
    for X in (0.0, 5.0):
        fixed = conv_us + prel_us + X
        loops_today = T - fixed
        g1a = (fixed + NVH * g1_lo / GHZ / 1e3, fixed + NVH * g1_hi / GHZ / 1e3)
        g2a = {}
        for lab, f in (("2.396", f_tdp_clean), ("1.895", f_tdp_dirty)):
            g2a[lab] = (fixed / (f / f_fma) + NVH * g2_lo / f / 1e3, fixed / (f / f_fma) + NVH * g2_hi / f / 1e3)
        rows.append((X, loops_today, g1a, g2a))
    g1_after = (min(r[2][0] for r in rows), max(r[2][1] for r in rows))
    g1_change = (c["share"] * (1 - g1_after[1] / T), c["share"] * (1 - g1_after[0] / T))
    g2_change = {}
    extra = []
    for lab in ("2.396", "1.895"):
        a = (min(r[3][lab][0] for r in rows), max(r[3][lab][1] for r in rows))
        g2_change[lab] = (c["share"] * (1 - a[1] / T), c["share"] * (1 - a[0] / T))
        for r in rows:                    # like with like: same X, optimistic with optimistic, pessimistic with pessimistic
            extra.append(c["share"] * (r[2][0] - r[3][lab][0]) / T)
            extra.append(c["share"] * (r[2][1] - r[3][lab][1]) / T)
    fw[name] = dict(est_share=est_ms / pass_ms, measured_share=c["share"], T=T, g1_after=g1_after, g1_change=g1_change,
                    g2_change=g2_change, extra=(min(extra), max(extra)))
    print(f"  {name}: spec est. GDN {est_ms:.2f} ms = {est_ms / pass_ms * 100:.1f} % of {pass_ms} ms; traced run: {c['gdn_ms']:.2f} ms ="
          f" {c['share'] * 100:.1f} % of {c['pass_ms']:.1f} ms; GDN per token per layer {T:.1f} us (spec: 110.25)")
    print(f"      loops today in tron = {T:.1f} - fixed = {rows[0][1]:.1f} (X = 0) to {rows[1][1]:.1f} us (X = 5)"
          f" = {rows[0][1] / NVH * GHZ * 1e3:.0f} to {rows[1][1] / NVH * GHZ * 1e3:.0f} cycles per value head (M1 kernel: {M1_CYC - PRELUDE:.0f})")
    print(f"      G1: GDN {g1_after[0]:.1f} to {g1_after[1]:.1f} us ({T / g1_after[1]:.2f}x to {T / g1_after[0]:.2f}x); pass"
          f" -{g1_change[0] * 100:.1f} % to -{g1_change[1] * 100:.1f} %")
    for lab in ("2.396", "1.895"):
        print(f"      G2 at {lab} GHz: pass -{g2_change[lab][0] * 100:.1f} % to -{g2_change[lab][1] * 100:.1f} %")
    print(f"      G2 extra over G1 (same assumptions on both sides): {min(extra) * 100:.1f} to {max(extra) * 100:.1f} points")
out["forward"] = fw
print("  spec: G1 pass -22.4 % to -30.5 %; G2 -26.3 % to -39.5 %; extra 3.9 to 9.0 points")
lo = min(v["g1_change"][0] for v in fw.values()) * 100
hi = max(v["g1_change"][1] for v in fw.values()) * 100
print(f"  corrected over the 4 cells: G1 pass -{lo:.0f} % to -{hi:.0f} %;"
      f" G2 -{min(min(v['g2_change'][k][0] for k in v['g2_change']) for v in fw.values()) * 100:.0f} % to"
      f" -{max(max(v['g2_change'][k][1] for k in v['g2_change']) for v in fw.values()) * 100:.0f} %;"
      f" extra {min(v['extra'][0] for v in fw.values()) * 100:.1f} to {max(v['extra'][1] for v in fw.values()) * 100:.1f} points")

# ------------------------------------------------------------------ C01 / C02 / C12 attention
hdr("C01 / C12  attention 256x4")
amx = 64 * TDP + 80 * TLOAD + 20 * TSTORE
print(f"  64 x {TDP} + 80 x {TLOAD} + 20 x {TSTORE} = {amx:.0f} cycles (+ 20 TILEZERO = 10); AVX-512 4,096 x 2.0 = 8,192; ratio {8192 / amx:.2f}x")
print("  spec forward bound: share x (1 - 1/s), s = 1.26 to 2.6 (C6, measured on delphi-3bda with the clock at 3.60 / 3.90 = 0.923)")
print(f"  delphi-3b35 clock ratio under tile work (P): {R_CLEAN:.3f} (clean upper halves, phases) or {R_DIRTY:.3f} (live 512-bit state or fine mix).")
print("  The attention path runs AVX-512 (softmax, transpose, weight conversion) between the two tile kernels of every visit"
      " [self_attention.hpp:1760-1789; amx_attn.cpp:186-215, 233-241] and has no vzeroupper.")
att = {}
for lab, r in (("clean", R_CLEAN), ("live/fine mix", R_DIRTY)):
    s_hi = 2.6 * r / 0.923
    s_lo_clock = 1.26 * r / 0.923
    att[lab] = (s_lo_clock, s_hi)
    print(f"  {lab}: cache case s = 2.6 x {r:.3f} / 0.923 = {s_hi:.2f}; DRAM case between 1.26 (bound by memory) and"
          f" 1.26 x {r:.3f} / 0.923 = {s_lo_clock:.2f} (bound by the clock)")
m3 = [("1 user, prompt 1024", 0.129, 0.181, 0.874), ("1 user, prompt 4096", 0.181, 0.333, 0.969),
      ("8 users, prompt 1024", 0.180, 0.148, 0.874), ("8 users, prompt 4096", 0.412, 0.310, 0.969)]
for name, a_dec, a_pre, dense in m3:
    spec = (a_dec * (1 - 1 / 1.26), a_dec * (1 - 1 / 2.6))
    line = f"  {name}: decode forward, spec -{spec[0] * 100:.1f} % to -{spec[1] * 100:.1f} %;"
    for lab in att:
        s_lo, s_hi = att[lab]
        line += f" {lab}: {-a_dec * (1 - 1 / s_lo) * 100:+.1f} % to {-a_dec * (1 - 1 / s_hi) * 100:+.1f} %;"
    print(line)
    line = f"      prefill pass (x dense share {dense}), spec -{a_pre * (1 - 1 / 1.26) * dense * 100:.1f} % to -{a_pre * (1 - 1 / 2.6) * dense * 100:.1f} %;"
    for lab in att:
        s_lo, s_hi = att[lab]
        line += f" {lab}: {-a_pre * dense * (1 - 1 / s_lo) * 100:+.1f} % to {-a_pre * dense * (1 - 1 / s_hi) * 100:+.1f} %;"
    print(line)
out["attention_s"] = att

# ------------------------------------------------------------------ C13, C14, C15, C17
hdr("C13, C14, C15, C17  arithmetic")
for prompt in (1024, 4096):
    chunks = prompt // 128
    old = sum(128 * j for j in range(chunks)) / chunks
    own = sum(range(1, 129)) / 128
    print(f"  C13 prompt {prompt}: earlier chunks {old:.0f} tokens, own chunk {own:.1f} -> dense share {old / (old + own) * 100:.1f} %")
print(f"  C14: 96 x {TDP} = {96 * TDP:.0f}; 192 x {TDP} + 64 x {TLOAD} + 64 x {TSTORE} = {192 * TDP + 64 * TLOAD + 64 * TSTORE:.0f}; split 4,096;"
      f" total {96 * TDP + 192 * TDP + 64 * TLOAD + 64 * TSTORE + 4096:.0f} against 2,560")
g3 = 2048 + 1024 + 128 + 288
print(f"  C15: {g3} FMA / 2 = {g3 / 2:.0f}; + 426 = {g3 / 2 + 426:.0f}; vs G1 {g1_hi_spec / (g3 / 2 + 426):.2f}x to {g1_lo_spec / (g3 / 2):.2f}x")
for n, p, t in ((8, 48.1, 0.385), (32, 59.1, 1.895), (8, 361.0, 2.90), (32, 445.0, 14.28)):
    print(f"  C17: {n} x {p} ms = {n * p / 1e3:.3f} s (measured {t} s, {(n * p / 1e3 / t - 1) * 100:+.1f} %)")

# ------------------------------------------------------------------ C16 decode
hdr("C16  decode: fewer passes over the state (G5)")
spec_today = 3 * 1024 * LINE + 2560
print(f"  spec (state from cache): today {spec_today:.0f}; (a) {2 * 1024 * LINE + 2560:.0f} = {spec_today / (2 * 1024 * LINE + 2560):.2f}x;"
      f" (a)+(b) {1024 * LINE + 2560:.0f} = {spec_today / (1024 * LINE + 2560):.2f}x")
for lab, step in (("lowest", min(dec_steps)), ("highest", max(dec_steps))):
    per_vh = (step - conv_us / 16 - 2 * PRELUDE / GHZ / 1e3) / 2 * GHZ * 1e3     # cycles per value head, recurrence loops + scan (+ postprocess)
    save_a, save_ab = 1024 * LINE, 2 * 1024 * LINE     # a pass that is fed from L2 after the first fetch
    print(f"  tron decode, {lab} measured group step {step:.1f} us (TR): about {per_vh:.0f} cycles per value head for scan + loops."
          f" (a) saves one L2-fed pass ({save_a:.0f}): {per_vh / (per_vh - save_a):.2f}x; (a)+(b) saves two ({save_ab:.0f}): {per_vh / (per_vh - save_ab):.2f}x")
    out.setdefault("C16", {})[lab] = (per_vh, per_vh / (per_vh - save_a), per_vh / (per_vh - save_ab))

json.dump(out, open(__file__.replace(".py", ".json"), "w"), indent=1, default=str)
