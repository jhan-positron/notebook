#!/usr/bin/env python3
"""Recomputes every number used in attention-stats-claude.html from the raw
exit reports and FUSE leaf snapshots, and asserts each closed form.
Run: python3 attention-stats-claude-check.py  (prints a JSON dict of facts)."""
import json, re, glob, os, sys
R = "/home/jhan/workspace/intel-AMX/exec/results"

def report(path, label_prefix=""):
    """Parse the [attn-stats] lines of one log into {summary, cls: {totals, forwards, layers}}."""
    out = {"layers": {}}
    for line in open(path, errors="replace"):
        if not line.startswith("[attn-stats] "): continue
        body = line[len("[attn-stats] "):].rstrip("\n")
        m = re.match(r"model (\S*): (\{.*\})$", body)
        if m: out["summary"] = json.loads(m.group(2)); continue
        m = re.match(r"(\S+) (totals|forwards): (\{.*\})$", body)
        if m:
            cls = m.group(1).split("/")[0]
            out.setdefault(cls, {})[m.group(2)] = json.loads(m.group(3)); continue
        m = re.match(r"(\S+) k_tokens per layer \(amx/avx/fpga\): (.*)$", body)
        if m:
            cls = m.group(1).split("/")[0]
            out["layers"][cls] = {int(k): tuple(int(x) for x in v.split("/"))
                                  for k, v in (t.split("=") for t in m.group(2).split())}
    return out

facts = {}
def check(name, got, want):
    ok = (got == want)
    facts[name] = {"got": got, "want": want, "ok": ok}
    if not ok: print(f"MISMATCH {name}: got {got} want {want}", file=sys.stderr)
    return ok

# ---------- Sample A: CPU attention, head bff317e0d3, 2026-09-29 23:24 UTC ----------
A = report(f"{R}/attnstats-20260929-cpu/rt/q3-4b-tp2-8u-p1024__cpu__headon4__rep1.log")
S = A["summary"]; U, L, H, P, G = 8, S["n_layers"], S["n_kv_heads"], S["page_size"], 256
PROMPT, CHUNK = 1024, 128
assert (L, H, P) == (36, 8, 64)
UHL = U * H * L  # (user, kv head, layer) triples = 2304
check("A.uhl", UHL, 2304)
dec, pre = A["decode_like"], A["prompt_or_mixed"]
# forwards and token jobs
check("A.dec.forwards", dec["forwards"]["forwards"], G - 1)
check("A.dec.token_jobs", dec["forwards"]["token_jobs"], U * (G - 1))
check("A.dec.listener_jobs", dec["forwards"]["listener_jobs"], U * (G - 1))
check("A.dec.kv_only_jobs", dec["forwards"]["kv_only_jobs"], 0)
check("A.pre.forwards", pre["forwards"]["forwards"], PROMPT // CHUNK)
check("A.pre.token_jobs", pre["forwards"]["token_jobs"], U * PROMPT)
check("A.pre.listener_jobs", pre["forwards"]["listener_jobs"], U * (PROMPT // CHUNK))
check("A.pre.kv_only_jobs", pre["forwards"]["kv_only_jobs"], U * PROMPT - U * (PROMPT // CHUNK))
# attention jobs = forwards x layers x attention workers (one minibatch per forward)
W = dec["forwards"]["n_attn_workers_max"]; check("A.split", W, 20)
check("A.dec.attn_jobs", dec["totals"]["attn_jobs"], (G - 1) * L * W)
check("A.pre.attn_jobs", pre["totals"]["attn_jobs"], (PROMPT // CHUNK) * L * W)
# decode visits, per (user, kv head, layer), step s = 1..255: context after write = PROMPT + s
ready_pages = sum((PROMPT + s - 1) // P for s in range(1, G))        # pages before the pending one
full_steps = [s for s in range(1, G) if (PROMPT + s) % P == 0]        # pending page becomes full
pend_avx_steps = (G - 1) - len(full_steps)
pend_avx_tokens = sum((PROMPT + s) % P for s in range(1, G) if (PROMPT + s) % P != 0)
check("A.dec.ready_pages_per_uhl", ready_pages, 4461)
check("A.dec.full_steps", full_steps, [64, 128, 192])
check("A.dec.ready_amx_visits", dec["totals"]["ready_amx_visits"], ready_pages * UHL)
check("A.dec.ready_amx_k_tokens", dec["totals"]["ready_amx_k_tokens"], ready_pages * P * UHL)
check("A.dec.pending_amx_visits", dec["totals"]["pending_amx_visits"], len(full_steps) * UHL)
check("A.dec.pending_amx_k_tokens", dec["totals"]["pending_amx_k_tokens"], len(full_steps) * P * UHL)
check("A.dec.pending_avx_visits", dec["totals"]["pending_avx_visits"], pend_avx_steps * UHL)
check("A.dec.pending_avx_k_tokens", dec["totals"]["pending_avx_k_tokens"], pend_avx_tokens * UHL)
check("A.dec.pend_avx_tokens_per_uhl", pend_avx_tokens, 8064)
ctx_sum = sum(PROMPT + s for s in range(1, G))
check("A.dec.k_tokens_all_per_uhl", (dec["totals"]["ready_amx_k_tokens"] + dec["totals"]["pending_amx_k_tokens"] + dec["totals"]["pending_avx_k_tokens"]) // UHL, ctx_sum)
check("A.dec.ctx_sum", ctx_sum, 293760)
check("A.dec.zero_counters", [dec["totals"][k] for k in ("ready_avx_visits","ready_empty_visits","pending_empty_visits","pending_avx_full_page_visits","ready_avx_full_page_visits","fpga_k_tokens","fpga_query_passes")], [0]*7)
# per-layer line
for l in range(L):
    amx, avx, fpga = A["layers"]["decode_like"][l]
    assert amx == (ready_pages * P + len(full_steps) * P) * U * H and avx == pend_avx_tokens * U * H and fpga == 0, l
facts["A.dec.layer_line"] = {"amx": A["layers"]["decode_like"][0][0], "avx": A["layers"]["decode_like"][0][1], "ok": True}
check("A.dec.layer_amx", A["layers"]["decode_like"][0][0], 18284544)
check("A.dec.layer_avx", A["layers"]["decode_like"][0][1], 516096)
# path sets: amx-only = the 3 full-page steps x 8 users; avx+amx = the other 252 x 8
ps = dec["forwards"]["token_jobs_by_path_set"]
check("A.dec.pathset_amx", ps["amx"], len(full_steps) * U)
check("A.dec.pathset_avx+amx", ps["avx+amx"], pend_avx_steps * U)
check("A.dec.pathset_rest", sum(v for k, v in ps.items() if k not in ("amx", "avx+amx")), 0)
# prefill visits, per (user, kv head, layer), chunk c = 0..7 of 128 queries over 2 pending pages
NC = PROMPT // CHUNK; PPC = CHUNK // P  # pages per chunk = 2
ready_pre = sum(CHUNK * PPC * c for c in range(NC))
def pend_visits_one_chunk():
    v = k = full = 0
    for q in range(CHUNK):
        for pg in range(PPC):
            lo = pg * P
            if q < lo: continue                 # page entirely in the future: not a visit
            rel = min(q - lo + 1, P)
            v += 1; k += rel; full += (rel == P)
    return v, k, full
pv, pk, pf = pend_visits_one_chunk()
check("A.pre.ready_amx_visits", pre["totals"]["ready_amx_visits"], ready_pre * UHL)
check("A.pre.ready_amx_k_tokens", pre["totals"]["ready_amx_k_tokens"], ready_pre * P * UHL)
check("A.pre.pending_avx_visits", pre["totals"]["pending_avx_visits"], pv * NC * UHL)
check("A.pre.pending_avx_k_tokens", pre["totals"]["pending_avx_k_tokens"], pk * NC * UHL)
check("A.pre.pending_avx_full_page_visits", pre["totals"]["pending_avx_full_page_visits"], pf * NC * UHL)
check("A.pre.pending_amx_visits", pre["totals"]["pending_amx_visits"], 0)
check("A.pre.per_chunk", (pv, pk, pf), (192, 8256, 66))
check("A.pre.ready_pre_per_uhl", ready_pre, 7168)
ps = pre["forwards"]["token_jobs_by_path_set"]
check("A.pre.pathset_avx", ps["avx"], U * CHUNK)            # chunk 0: no ready pages
check("A.pre.pathset_avx+amx", ps["avx+amx"], U * CHUNK * (NC - 1))
check("A.pre.layer_amx", A["layers"]["prompt_or_mixed"][0][0], ready_pre * P * U * H)
check("A.pre.layer_avx", A["layers"]["prompt_or_mixed"][0][1], pk * NC * U * H)
# period counts: one period per (forward, layer) except the last layer
check("A.dec.period_count", dec["totals"]["period_count_w0"], (G - 1) * (L - 1))
check("A.pre.period_count", pre["totals"]["period_count_w0"], NC * (L - 1))
# timers to seconds
hz = S["tsc_hz"]; facts["A.tsc_hz"] = hz
def us(c): return c / hz * 1e6
T = {}
T["dec.T1_per_forward_ms"] = dec["forwards"]["wall_cycles"] / (G - 1) / hz * 1e3
T["dec.T1_max_ms"] = dec["forwards"]["wall_max_cycles"] / hz * 1e3
T["dec.T2_per_job_us"] = us(dec["totals"]["busy_cycles"] / dec["totals"]["attn_jobs"])
T["dec.T2_per_worker_per_forward_ms"] = dec["totals"]["busy_cycles"] / W / (G - 1) / hz * 1e3
T["dec.T2_share_of_T1_pct"] = T["dec.T2_per_worker_per_forward_ms"] / T["dec.T1_per_forward_ms"] * 100
T["dec.T3_per_job_us"] = us(dec["totals"]["wall_cycles_w0"] / ((G - 1) * L))
T["dec.T3_max_us"] = us(dec["totals"]["wall_max_cycles_w0"])
T["dec.T4_per_layer_us"] = us(dec["totals"]["period_cycles_w0"] / dec["totals"]["period_count_w0"])
T["dec.T4_max_us"] = us(dec["totals"]["period_max_cycles_w0"])
T["dec.T4_x_layers_ms"] = T["dec.T4_per_layer_us"] * L / 1e3
T["dec.T5_per_job_us"] = us(dec["totals"]["join_wait_cycles"] / dec["totals"]["attn_jobs"])
T["dec.T5_share_of_T2_pct"] = dec["totals"]["join_wait_cycles"] / dec["totals"]["busy_cycles"] * 100
T["pre.T1_per_forward_ms"] = pre["forwards"]["wall_cycles"] / NC / hz * 1e3
T["pre.T1_max_ms"] = pre["forwards"]["wall_max_cycles"] / hz * 1e3
T["pre.T2_per_job_ms"] = pre["totals"]["busy_cycles"] / pre["totals"]["attn_jobs"] / hz * 1e3
T["pre.T2_per_worker_per_forward_ms"] = pre["totals"]["busy_cycles"] / W / NC / hz * 1e3
T["pre.T2_share_of_T1_pct"] = T["pre.T2_per_worker_per_forward_ms"] / T["pre.T1_per_forward_ms"] * 100
T["pre.T3_per_job_ms"] = pre["totals"]["wall_cycles_w0"] / (NC * L) / hz * 1e3
T["pre.T4_per_layer_ms"] = pre["totals"]["period_cycles_w0"] / pre["totals"]["period_count_w0"] / hz * 1e3
T["pre.T4_x_layers_ms"] = T["pre.T4_per_layer_ms"] * L
T["pre.T5_per_job_us"] = us(pre["totals"]["join_wait_cycles"] / pre["totals"]["attn_jobs"])
T["pre.T5_share_of_T2_pct"] = pre["totals"]["join_wait_cycles"] / pre["totals"]["busy_cycles"] * 100
T["dec.amx_share_of_sw_k_tokens_pct"] = (dec["totals"]["ready_amx_k_tokens"] + dec["totals"]["pending_amx_k_tokens"]) / (dec["totals"]["ready_amx_k_tokens"] + dec["totals"]["pending_amx_k_tokens"] + dec["totals"]["pending_avx_k_tokens"]) * 100
T["pre.amx_share_of_sw_k_tokens_pct"] = pre["totals"]["ready_amx_k_tokens"] / (pre["totals"]["ready_amx_k_tokens"] + pre["totals"]["pending_avx_k_tokens"]) * 100
T["dec.dot_products"] = (dec["totals"]["ready_amx_k_tokens"] + dec["totals"]["pending_amx_k_tokens"] + dec["totals"]["pending_avx_k_tokens"]) * S["kv_mul"]
T["dec.per_step_k_tokens_per_layer_per_user"] = ctx_sum / (G - 1)
T["rows_bytes"] = S["n_workers"] * L * 2 * 192
T["main_helpers"] = S["n_workers"] - W
facts["A.timers"] = {k: (round(v, 3) if isinstance(v, float) else v) for k, v in T.items()}
facts["A.raw"] = A

# ---------- Sample B: FPGA attention, head cbf1bb6c0c, 2026-09-25 13:24 UTC ----------
B = report(f"{R}/attnstats-20260925-fpga/rt/q3-4b-tp2-8u-p1024__fpga__headon2__rep1.log")
bd, bp = B["decode_like"], B["prompt_or_mixed"]
check("B.dec.forwards", bd["forwards"]["forwards"], G - 1)
check("B.dec.token_jobs", bd["forwards"]["token_jobs"], U * (G - 1))
check("B.dec.fpga_queries", bd["forwards"]["fpga_queries"], U * (G - 1))
check("B.dec.pathset_fpga+avx", bd["forwards"]["token_jobs_by_path_set"]["fpga+avx"], U * (G - 1))
check("B.dec.fpga_query_passes", bd["totals"]["fpga_query_passes"], (G - 1) * U * L)   # one pass per (forward, user, layer)
check("B.dec.pending_avx_visits", bd["totals"]["pending_avx_visits"], (G - 1) * UHL)  # one AVX visit per step
check("B.dec.amx_zero", bd["totals"]["ready_amx_visits"] + bd["totals"]["pending_amx_visits"] + bd["totals"]["ready_avx_visits"], 0)
# card tokens + AVX tail = the whole context per step, per (user, layer)
card_plus_tail = bd["totals"]["fpga_k_tokens"] / (U * L) + bd["totals"]["pending_avx_k_tokens"] / UHL
check("B.dec.card_plus_tail_eq_ctx", card_plus_tail, float(ctx_sum))
check("B.dec.fpga_x_kv_heads", bd["totals"]["fpga_k_tokens_x_kv_heads"], bd["totals"]["fpga_k_tokens"] * H)
facts["B.dec.avx_tail_tokens_per_step"] = bd["totals"]["pending_avx_k_tokens"] / UHL / (G - 1)
facts["B.dec.card_tokens_per_pass"] = bd["totals"]["fpga_k_tokens"] / bd["totals"]["fpga_query_passes"]
facts["B.dec.card_share_pct"] = bd["totals"]["fpga_k_tokens_x_kv_heads"] / (bd["totals"]["fpga_k_tokens_x_kv_heads"] + bd["totals"]["pending_avx_k_tokens"]) * 100
check("B.pre.forwards", bp["forwards"]["forwards"], NC)
check("B.pre.fpga_queries", bp["forwards"]["fpga_queries"], U * CHUNK * (NC - 1))
check("B.pre.pathset_avx", bp["forwards"]["token_jobs_by_path_set"]["avx"], U * CHUNK)
check("B.pre.pathset_fpga+avx", bp["forwards"]["token_jobs_by_path_set"]["fpga+avx"], U * CHUNK * (NC - 1))
check("B.pre.fpga_query_passes", bp["totals"]["fpga_query_passes"], U * CHUNK * (NC - 1) * L)
check("B.pre.fpga_k_tokens", bp["totals"]["fpga_k_tokens"], ready_pre * P * U * L)  # the ready pages, all kv heads at once
check("B.pre.fpga_x_kv_heads_eq_cpu_ready_amx", bp["totals"]["fpga_k_tokens_x_kv_heads"], pre["totals"]["ready_amx_k_tokens"])
check("B.pre.pending_same_as_cpu", (bp["totals"]["pending_avx_visits"], bp["totals"]["pending_avx_k_tokens"], bp["totals"]["pending_avx_full_page_visits"]), (pre["totals"]["pending_avx_visits"], pre["totals"]["pending_avx_k_tokens"], pre["totals"]["pending_avx_full_page_visits"]))
hzb = B["summary"]["tsc_hz"]
TB = {}
TB["dec.T1_per_forward_ms"] = bd["forwards"]["wall_cycles"] / (G - 1) / hzb * 1e3
TB["dec.T2_per_job_us"] = bd["totals"]["busy_cycles"] / bd["totals"]["attn_jobs"] / hzb * 1e6
TB["dec.T5_per_job_us"] = bd["totals"]["join_wait_cycles"] / bd["totals"]["attn_jobs"] / hzb * 1e6
TB["dec.T5_share_of_T2_pct"] = bd["totals"]["join_wait_cycles"] / bd["totals"]["busy_cycles"] * 100
TB["dec.T4_per_layer_us"] = bd["totals"]["period_cycles_w0"] / bd["totals"]["period_count_w0"] / hzb * 1e6
TB["pre.T1_per_forward_ms"] = bp["forwards"]["wall_cycles"] / NC / hzb * 1e3
TB["pre.T5_share_of_T2_pct"] = bp["totals"]["join_wait_cycles"] / bp["totals"]["busy_cycles"] * 100
TB["active_workers"] = B["summary"]["active_workers"]
facts["B.timers"] = {k: (round(v, 3) if isinstance(v, float) else v) for k, v in TB.items()}
facts["B.raw"] = B

# ---------- Cross-check C: kill switch (TRON_AMX_DISABLE=1) vs AMX on, 2026-09-24, head 9b3832eb4b ----------
Con = report(f"{R}/attnstats-20260924/rt/q3-4b-tp2-8u-p1024__cpu__headon__rep1.log")
Ck = report(f"{R}/attnstats-20260924/rt/q3-4b-tp2-8u-p1024__cpu__headkill__rep1.log")
for cls in ("decode_like", "prompt_or_mixed"):
    on, kill = Con[cls]["totals"], Ck[cls]["totals"]
    amx_on = on["ready_amx_visits"] + on["pending_amx_visits"]
    full_on = on["ready_avx_full_page_visits"] + on["pending_avx_full_page_visits"]
    full_kill = kill["ready_avx_full_page_visits"] + kill["pending_avx_full_page_visits"]
    check(f"C.{cls}.identity", full_kill, amx_on + full_on)
    sw = lambda t: sum(t[f"{p}_{q}_k_tokens"] for p in ("ready", "pending") for q in ("avx", "amx"))
    check(f"C.{cls}.sw_k_tokens_equal", sw(kill), sw(on))
    facts[f"C.{cls}.numbers"] = {"amx_on": amx_on, "full_on": full_on, "full_kill": full_kill, "sw_k_tokens": sw(on),
                                 "busy_on": on["busy_cycles"], "busy_kill": kill["busy_cycles"],
                                 "T1_on": Con[cls]["forwards"]["wall_cycles"], "T1_kill": Ck[cls]["forwards"]["wall_cycles"]}
check("C.same_visits_as_A", (Con["decode_like"]["totals"]["ready_amx_visits"], Con["prompt_or_mixed"]["totals"]["ready_amx_visits"]), (dec["totals"]["ready_amx_visits"], pre["totals"]["ready_amx_visits"]))
facts["C.kill_pathset_dec"] = Ck["decode_like"]["forwards"]["token_jobs_by_path_set"]

# ---------- Snapshot D: live FUSE leaves during the repeat run (head bff317e0d3), read at decode forward 142/143 ----------
D = f"{R}/attnstats-20260929-cpu2/leaves-latest"
leaf = lambda n: json.loads(open(f"{D}/{n}").read())
fw = leaf("decode_like_forwards")
facts["D.forwards_leaf"] = fw
check("D.listener_ahead_by_one_forward", fw["listener_jobs"] - fw["token_jobs"], U)  # bff317e0d3 added listener_jobs in begin_forward; fixed by 04da001cb5
workers = [leaf(f"decode_like_worker_{w}") for w in range(S["n_workers"])]
layers = [leaf(f"decode_like_layer_{l}") for l in range(L)]
# The snapshot copied the leaves one file at a time (cpu-cell.sh: cat per leaf into a temp dir), so it is
# not one consistent cut: the run advanced while the copy ran. Record the read span and the drift.
mt = lambda n: os.stat(f"{D}/{n}").st_mtime
span_s = max(mt(f"decode_like_worker_{w}") for w in range(S["n_workers"])) - mt("decode_like_forwards")
facts["D.read_span_s"] = round(span_s, 3)
facts["D.sum_layers_vs_sum_workers"] = {key: (sum(l[key] for l in layers), sum(w[key] for w in workers))
                                        for key in ("ready_amx_visits", "pending_avx_visits", "attn_jobs")}
check("D.workers_read_after_layers", sum(w["attn_jobs"] for w in workers) > sum(l["attn_jobs"] for l in layers), True)
# cpu-cell.sh copied the leaves in shell glob order (lexicographic: worker_1, worker_10, worker_11, ...), so
# attn_jobs grows along that order: a later-read row has seen more forwards.
lex = sorted(range(S["n_workers"] - W, S["n_workers"]), key=lambda w: f"decode_like_worker_{w}")
check("D.attn_jobs_monotone_in_lexicographic_read_order", all(workers[a]["attn_jobs"] <= workers[b]["attn_jobs"] for a, b in zip(lex, lex[1:])), True)
# forwards advanced between the forwards leaf (142) and the attention row of pool worker 7 (read 0.236 s later): from its
# attn_jobs, 5817 / 36 layers - 142 = 19.6 (the page cites this key)
facts["D.forwards_advanced_est"] = round(workers[S["n_workers"] - W]["attn_jobs"] / L - fw["forwards"], 1)
# the same span in forwards at the snapshot's OWN mean T1 (its forwards leaf / its summary tsc_hz), not sample A's
SD = leaf("summary")
facts["D.T1_per_forward_ms"] = round(fw["wall_cycles"] / fw["forwards"] / SD["tsc_hz"] * 1e3, 2)
facts["D.read_span_forwards_est"] = round(span_s / (facts["D.T1_per_forward_ms"] / 1e3), 1)
check("D.helper_rows_zero", [workers[w]["attn_jobs"] for w in range(S["n_workers"] - W)], [0] * (S["n_workers"] - W))
check("D.attn_rows_nonzero", all(workers[w]["attn_jobs"] > 0 for w in range(S["n_workers"] - W, S["n_workers"])), True)
facts["D.worker_ready_amx_visits"] = {w: workers[w]["ready_amx_visits"] for w in range(S["n_workers"] - W, S["n_workers"])}
facts["D.worker_pending_avx_visits"] = {w: workers[w]["pending_avx_visits"] for w in range(S["n_workers"] - W, S["n_workers"])}
facts["D.worker_attn_jobs"] = {w: workers[w]["attn_jobs"] for w in range(S["n_workers"] - W, S["n_workers"])}
tot_ready = sum(w["ready_amx_visits"] for w in workers)
thru = lambda n: sum((PROMPT + s - 1) // P for s in range(1, n + 1)) * UHL
facts["D.ready_visits_total"] = tot_ready; facts["D.ready_thru_142"] = thru(142); facts["D.ready_thru_143"] = thru(143)
# The layer leaves were read 0.004 s to 0.116 s after the forwards leaf; their sum lies a few forwards ahead of 142.
lay_sum = sum(l["ready_amx_visits"] for l in layers)
facts["D.layer_sum_ready_forward_bracket"] = next((n for n in range(142, 200) if thru(n) <= lay_sum < thru(n + 1)), None)
check("D.layer_sum_ready_ahead_of_142", thru(142) <= lay_sum <= thru(142 + 30), True)
# the attention jobs of the snapshot: 5817 on worker 7 vs 143 forwards x 36 layers = 5148? no: jobs per worker per forward can exceed 1 layer... record only
facts["D.jobs_per_worker_min_max"] = (min(workers[w]["attn_jobs"] for w in range(S["n_workers"] - W, S["n_workers"])), max(workers[w]["attn_jobs"] for w in range(S["n_workers"] - W, S["n_workers"])))

bad = [k for k, v in facts.items() if isinstance(v, dict) and v.get("ok") is False]
print(json.dumps(facts, indent=1, default=str))
print(f"\nCHECKS: {sum(1 for v in facts.values() if isinstance(v, dict) and 'ok' in v)} run, {len(bad)} failed {bad}", file=sys.stderr)
sys.exit(1 if bad else 0)
