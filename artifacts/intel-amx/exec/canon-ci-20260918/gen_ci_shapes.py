#!/usr/bin/env python3
"""Generator of PR3879/new-PRs/PR1/CI-AMX-test-shapes.html: the recommendation page for the CI team on new nightly perf
shapes (configs) that make the AMX effect visible.

Style follows exec/canon-ci-20260918/gen_report.py (the canonical-AMX CI run report): same CSS, palette, glossary
style, Short version first, inline SVG charts, ASCII-only output through xmlcharrefreplace.

Every number on the page comes from the registry R below. Each entry carries a source tag:
  A    l8bload 2026-09-18 (VNNIed-K-in-place/status/llama8b-AMX-gain-vs-load.html)
  B    canon-ci 2026-09-18/19 nightly-layout campaign (PR3879/new-PRs/PR1/canonical-AMX-CI-run-report.html)
  C    wedperf 2026-09-16 (VNNIed-K-in-place/status/Wednesday-perf-test.html)
  D    more-testing round 1, 2026-09-05 (PR3879/more-testing/round-1/results.html)
  E    p0perf 2026-09-13 (PR3879/new-PRs/PR1/Sunday-CI-layout-results.html)
  F    make-sense-amx-vs-avx 2026-08-31, runtron prompt-length series (PR3879/make-sense-amx-vs-avx.html)
  H    l8b-levers 2026-09-19, test T0 as run (CI-test/status/Saturday-llama-3.1-8b.html, results
       exec/results/l8b-levers-20260919/summary.json read at generation time by exec/l8b-levers-20260919/h_registry.py)
  I    l8b-8u4k 2026-09-20, the 8-users-per-engine prompt-4096 cell (CI-test/status/llama-3.1-8b-8u-4k.html, results
       exec/results/l8b-8u4k-20260920/summary.json read at generation time by exec/l8b-8u4k-20260920/i_registry.py;
       the environment variable I_RES points it at another results directory; missing values render as n/a)
  P    prune probe 2026-09-19: testlib/prompt.py prune_convo run offline in the systems_test .venv over the ShareGPT
       seeds of the 8-user and 32-user configs (script: scratchpad prune_probe.py of the review session)
  est. an estimate (units and the arithmetic are on the page)
  derived  computed here from tagged numbers (arithmetic in the footnotes)
  config   a harness or machine constant (token counts, engine counts, user counts, policy fields)
  model    a public model-architecture fact (head size, kv_mul)
  id       an identifier (date, PR number, commit, line number, version string)
After writing the page the script lists every number found in the page text with its tag, and flags any number that no
registry entry explains. Run: python3 gen_ci_shapes.py [--out PATH]
"""
import argparse
import os
import re
import time

OUT_DEFAULT = "/home/jhan/workspace/intel-AMX/PR3879/new-PRs/PR1/CI-AMX-test-shapes.html"

# palette: dataviz reference instance, light surface (same as gen_report.py). Green (aqua) has 2.74:1 contrast on the
# surface, so every green mark carries a direct value label.
C_GREEN, C_GRAY, C_BLUE, C_ORANGE, C_BAND = "#1baf7a", "#898781", "#2a78d6", "#eb6834", "#e1e0d9"
INK, INK2, MUTED, GRID, SURF = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#fcfcfb"
TICK = "#6b6a66"


# ---------------- number registry ----------------
class Registry:
    """key -> (text, tag, note). Calling R('key') returns the text and records the use."""

    def __init__(self):
        self.items = {}
        self.used = set()

    def add(self, key, text, tag, note=""):
        if key in self.items:
            raise KeyError(f"duplicate registry key {key}")
        self.items[key] = (str(text), tag, note)

    def __call__(self, key):
        text, _, _ = self.items[key]
        self.used.add(key)
        return text

    def tag(self, key):
        return self.items[key][1]


R = Registry()
# ---- DATA A: l8bload 2026-09-18 ----
R.add("a_users", "2, 4 and 8", "config", "users per engine levels of data A")
R.add("a_off2", "141.57", "A", "TPS, 2 users/engine, kill switch on (no AMX)")
R.add("a_on2", "141.81", "A", "TPS, 2 users/engine, AMX on")
R.add("a_gain2", "+0.2", "A", "% gain at 2 users/engine")
R.add("a_t2", "+0.5", "A", "paired t at 2 users/engine (not resolved)")
R.add("a_ttft_off2", "834", "A", "ms TTFT, 2 users/engine, no AMX")
R.add("a_ttft_on2", "792", "A", "ms TTFT, 2 users/engine, AMX on")
R.add("a_busy_off", "0", "A", "AMX-busy cycles in every kill-switch cell")
R.add("a_busy2", "40.3", "A", "billion cycles AMX-busy, 2 users/engine, 20 s probe")
R.add("a_busy4", "67.8", "A", "billion cycles AMX-busy, 4 users/engine, 20 s probe (summary.md row 4)")
R.add("a_binary", "2026.09.18-29a8a547", "id", "tron package of data A: main 3faba6d0 + PR #4424, TRON_AMX_DISPATCH=ON, TRON_K_VNNI=ON (sha256 3ee9c8f0)")
R.add("a_t975", "4.30", "config", "data-A rule: |t| limit for 3 repetitions (t975 in summary.json)")
R.add("a_off8_r1", "70.35", "A", "TPS, 8 users/engine, kill switch, repetition 1 cell mean")
R.add("a_off8_r2", "69.67", "A", "TPS, 8 users/engine, kill switch, repetition 2 cell mean")
R.add("a_off8_r3", "70.22", "A", "TPS, 8 users/engine, kill switch, repetition 3 cell mean")
R.add("a_on8_r1", "79.53", "A", "TPS, 8 users/engine, AMX on, repetition 1 cell mean")
R.add("a_on8_r2", "79.04", "A", "TPS, 8 users/engine, AMX on, repetition 2 cell mean")
R.add("a_on8_r3", "78.86", "A", "TPS, 8 users/engine, AMX on, repetition 3 cell mean")
R.add("a_off4", "122.93", "A", "TPS, 4 users/engine, no AMX")
R.add("a_on4", "127.69", "A", "TPS, 4 users/engine, AMX on")
R.add("a_gain4", "+3.9", "A", "% gain at 4 users/engine")
R.add("a_t4", "+5.8", "A", "paired t at 4 users/engine (resolved)")
R.add("a_ttft_off4", "1472", "A", "ms TTFT, 4 users/engine, no AMX")
R.add("a_ttft_on4", "1424", "A", "ms TTFT, 4 users/engine, AMX on")
R.add("a_off8", "70.08", "A", "TPS, 8 users/engine, no AMX")
R.add("a_on8", "79.14", "A", "TPS, 8 users/engine, AMX on")
R.add("a_gain8", "+12.9", "A", "% gain at 8 users/engine")
R.add("a_t8", "+38.7", "A", "paired t at 8 users/engine (resolved)")
R.add("a_ttft_off8", "2768", "A", "ms TTFT, 8 users/engine, no AMX")
R.add("a_ttft_on8", "2693", "A", "ms TTFT, 8 users/engine, AMX on")
R.add("a_busy8", "92.0", "A", "billion cycles AMX-busy, 8 users/engine, 20 s probe")
R.add("a_sd_lo", "0.22", "A", "TPS per-cell sd, lower end, 8 users/engine")
R.add("a_sd_hi", "0.40", "A", "TPS per-cell sd, upper end, 8 users/engine")
R.add("a_slow_off8", "69.1", "A", "TPS slowest sample, 8 users/engine, no AMX")
R.add("a_slow_on8", "78.0", "A", "TPS slowest sample, 8 users/engine, AMX on")
R.add("a_reps", "3", "config", "repetitions per level and arm in data A")
R.add("a_engines", "2", "config", "engines in data A (socket-1 placement of the nightly)")
R.add("a_probe", "20", "config", "s AMX-busy probe length")
R.add("a_cell_lo", "3.6", "A", "min, shortest 8-user cell (benchmark + probe)")
R.add("a_cell_hi", "4.0", "A", "min, longest 8-user cell")
R.add("night13_mean", "139.73", "B", "TPS 13-night nightly mean, llama-8b @8u (exec/results/ci-mimic-20260918/reference/nightly_stats.json)")
R.add("night13_sd", "0.52", "B", "TPS night-to-night sd of the 13 nights, llama-8b @8u (nightly_stats.json)")
R.add("night13_gap", "1.3", "derived", "% gap of a_off2 to night13_mean: (141.57 - 139.73) / 139.73 = 0.0132 = 1.3 %")
# ---- DATA B: canon-ci nightly layout ----
R.add("b_target_gain", "+0.8", "B", "% llama-8b @8u, PR #4424 + AMX arm vs nightly deb")
R.add("b_target_t", "+3.0", "B", "paired t of the +0.8 % as report-v4 of the base arm prints it")
R.add("b_target_t_raw", "2.96", "A", "the same paired t unrounded, as the data-A summary.md lists it in its reference points")
R.add("b_anom_3b", "121", "B", "anomalous TPS samples on llama-3.2-3b @32u in the base arm of data B (client-stall indicator)")
R.add("b_canon_gain", "+1.2", "B", "% llama-8b @8u, canonical-AMX arm vs nightly deb (resolved)")
R.add("b_canon_t", "+2.8", "B", "paired t of the +1.2 %")
R.add("b_busy", "30.2", "B", "billion cycles AMX-busy on llama-8b in the canonical arm")
R.add("b_rounds", "10", "config", "rounds per config in the nightly and in data B")
R.add("b_llama3b", "+1.5", "B", "% canonical effect, llama-3b @32u, not resolved")
R.add("b_llama8b", "+1.2", "B", "% canonical effect, llama-8b @8u, resolved")
R.add("b_70b_tp2_8u", "+0.1", "B", "% canonical effect, 70b tp2 @8u")
R.add("b_70b_tp2_4u", "-0.0", "B", "% canonical effect, 70b tp2 @4u")
R.add("b_70b_tp4", "+1.8", "B", "% canonical effect, 70b tp4 @4u, not resolved")
R.add("b_mixtral", "-0.6", "B", "% canonical effect, mixtral @8u, not resolved")
R.add("b_qwen25", "+0.1", "B", "% canonical effect, qwen-2.5 @8u")
R.add("b_qwen34_tp2", "+0.1", "B", "% canonical effect, qwen-3-4b tp2 @8u")
R.add("b_qwen34_tp4", "-2.6", "B", "% canonical effect, qwen-3-4b tp4 @8u, not resolved")
R.add("b_gemma2", "-0.2", "B", "% canonical effect, gemma-2 @8u")
R.add("b_gptoss", "-3.9", "B", "% canonical effect, gpt-oss @8u, not resolved")
R.add("b_gemma4", "-0.3", "B", "% canonical effect, gemma-4 @8u")
R.add("b_perf_min", "79", "B", "min, duration of the nightly perf phase today")
R.add("b_deb_base", "2026.09.18-3faba6d0", "id", "nightly deb version")
R.add("b_deb_canon", "2026.09.18-0594dc54-jhan-ci-canon", "id", "canonical-AMX deb version")
# ---- DATA C: wedperf (base = main eb2de0265a before PR #3879, target = PR #4424 head ff680c8020) ----
R.add("c_gain256", "+2.0", "C", "% llama-8b, runtron, 8 users one engine, 256 generated tokens, target vs base, 3 repetitions")
R.add("c_gain1536", "+17.0", "C", "% llama-8b, runtron, 8 users one engine, 1536 generated tokens, target vs base, 2 repetitions")
R.add("c_off1536", "83.3", "C", "TPS llama-8b base at 1536 generated tokens")
R.add("c_on1536", "97.5", "C", "TPS llama-8b target at 1536 generated tokens")
R.add("c_reps256", "3", "config", "repetitions of the 256-token cell of data C")
R.add("c_reps1536", "2", "config", "repetitions of the 1536-token cell of data C")
R.add("c_attr_main", "+3.0", "C", "% llama-8b at 256 tokens, main's own change (PR #3879 kernel + PR #4400) vs base, block D")
R.add("c_attr_4424", "-1.1", "C", "% llama-8b at 256 tokens, PR #4424 alone (mid to target), not resolved, block D")
R.add("c_tok256", "256", "config", "generated tokens, short cell of data C")
# ---- DATA D: more-testing round 1 ----
R.add("d_llama8b", "+13.9", "D", "% llama-8b good, canonical kernel, 8 users on one engine")
R.add("d_mix_off", "33.22", "D", "TPS mixtral tp2, no AMX")
R.add("d_mix_on", "33.14", "D", "TPS mixtral tp2, AMX on")
R.add("d_mix_gain", "-0.2", "D", "% mixtral tp2 (parity)")
R.add("d_mix_sd", "0.2", "D", "TPS sd of the mixtral cells")
R.add("d_qwen", "+4.5", "D", "% qwen-3-4b tp4 with CPU attention (USE_HW_ATTN=0), 8 users one engine")
R.add("d_qwen_aa", "-2.2", "D", "% A/A repeat of the qwen-3-4b tp4 off arm, run to run")
R.add("d_floor", "2", "D", "% floor below which one run per arm cannot resolve a change (from the A/A repeat)")
# ---- DATA E: p0perf 2026-09-13 ----
R.add("e_qwen_off", "140.6", "E", "TPS qwen-3-4b tp2, CPU attention, no AMX, 2 engines x 2 users")
R.add("e_qwen_on", "152.5", "E", "TPS qwen-3-4b tp2, CPU attention, AMX on (152.46 in summary.md)")
R.add("e_qwen_tp2", "+8.4", "E", "% qwen-3-4b tp2 CPU attention gain")
R.add("e_qwen_tp4", "+7.9", "E", "% qwen-3-4b tp4 CPU attention gain")
R.add("e_loss_tp2", "-20.6", "E", "% CPU attention + AMX vs production FPGA attention, tp2")
R.add("e_loss_tp4", "-19.5", "E", "% same, tp4")
R.add("e_loss_tp2_abs", "20.6", "E", "% the same tp2 loss written without the sign ('20.6 % below production')")
# ---- DATA F: runtron prompt-length series (qwen-3-4b) ----
R.add("f_p2048", "+19.0", "F", "% canonical gain, qwen-3-4b, runtron, 8 users, prompt 2048")
R.add("f_p8192", "+17.5", "F", "% canonical gain, qwen-3-4b, runtron, 8 users, prompt 8192")
# ---- harness and machine constants ----
R.add("cards", "8", "config", "FPGA cards on delphi-3bda")
R.add("eng_tp2", "4", "config", "engines for tp2 = 8 // 2")
R.add("eng_tp4", "2", "config", "engines for tp4 = 8 // 4")
R.add("night_users", "8", "config", "users of today's llama-8b config")
R.add("night_upe", "2", "config", "users per engine today = 8 / 4")
R.add("prompt", "1024", "config", "prompt tokens")
R.add("gen", "1536", "config", "generated tokens")
R.add("cap_start", "896", "config", "first generated token of the TPS window")
R.add("cap_end", "1024", "config", "last generated token of the TPS window")
R.add("configs11", "11", "derived", "12 configs - 1 (llama-3b) = 11 configs with the 896 to 1024 window")
R.add("configs_tp2_8u_other", "six", "derived", "tp2 configs at 8 users besides llama-8b: 70b tp2 @8u, mixtral, qwen-2.5, qwen-3-4b tp2, gemma-2, gemma-4 = 6")
R.add("configs_tp2_8u", "7", "derived", "tp2 configs at 8 users including llama-8b = 7")
R.add("shared3b", "800", "config", "shared_prompt_length of llama-3.2-3b fast tp2 @32u")
R.add("prompt3b", "200", "config", "prompt_length of llama-3.2-3b fast tp2 @32u")
R.add("gen3b", "845", "config", "generate_length of llama-3.2-3b fast tp2 @32u")
R.add("cap3b_start", "2", "config", "start_capture of llama-3.2-3b fast tp2 @32u")
R.add("cap3b_end", "333", "config", "end_capture of llama-3.2-3b fast tp2 @32u")
R.add("ratio", "1.04", "config", "thresholds policy min_improvement_ratio")
R.add("seeds80", "80", "derived", "ShareGPT seeds of the 8-user config: 10 rounds x 8 users = 80 (seed = round x n_users + user)")
R.add("seeds320", "320", "derived", "ShareGPT seeds of the 32-user shape: 10 rounds x 32 users = 320")
R.add("seeds_new", "240", "derived", "320 - 80 = 240 conversations no run has used at prompt 1024")
R.add("seed_last", "319", "derived", "last seed of the 32-user shape = 320 - 1")
R.add("shortest_tokens", "1531", "P", "tokens of the shortest of the 320 conversations, harness system line included")
R.add("seed_shortest", "274", "P", "seed of the shortest conversation")
R.add("fail4096", "78", "P", "of 80 conversations that prune_convo rejects at prompt_length 4096")
R.add("fail8192", "80", "P", "of 80 conversations that prune_convo rejects at prompt_length 8192")
R.add("new_users", "32", "derived", "4 engines x 8 users per engine = 32 users")
R.add("new_upe", "8", "config", "users per engine of the proposed shape")
R.add("users16", "16", "derived", "4 engines x 4 users per engine = 16 users")
R.add("hist_runs", "14", "config", "thresholds policy history_runs")
R.add("q30", "0.30", "config", "thresholds policy support_quantile (q30)")
R.add("nights13", "13", "config", "nights in the Slack band series")
R.add("configs12", "12", "config", "perf configs in the nightly")
R.add("head128", "128", "model", "head size of the AMX kernel")
R.add("kvmul4", "4", "model", "query heads per KV head of the AMX kernel")
R.add("kvmul3", "3", "model", "kv_mul of llama-3.2-3b")
R.add("kvmul8", "8", "model", "kv_mul of llama-3.3-70b")
R.add("kvmul5", "5", "model", "kv_mul of qwen-2.5-32b")
R.add("head256", "256", "model", "head size of gemma-2 and gemma-4")
R.add("head64", "64", "model", "head size of gpt-oss")
R.add("kvmul2", "2", "model", "kv_mul of gemma-2-9b: 16 query heads / 8 KV heads (HF config.json)")
R.add("kvmul8_gptoss", "8", "model", "kv_mul of gpt-oss-120b: 64 query heads / 8 KV heads (HF config.json)")
R.add("heads_gemma2", "16", "model", "query heads of gemma-2-9b")
R.add("heads_gptoss", "64", "model", "query heads of gpt-oss-120b")
R.add("kvheads8", "8", "model", "KV heads of gemma-2-9b and of gpt-oss-120b")
R.add("prompt2048", "2048", "config", "prompt length of a considered long-context shape")
R.add("prompt4096", "4096", "config", "prompt length of a considered long-context shape")
R.add("prompt8192", "8192", "config", "prompt length of a considered long-context shape")
# ---- derived ----
R.add("step_tps", "9.06", "derived", "79.14 - 70.08 = 9.06 TPS")
R.add("step_pct", "12.9", "derived", "9.06 / 70.08 = 0.1293 = 12.9 %")
R.add("step_sd_lo", "23", "derived", "9.06 / 0.40 = 22.7, about 23 sd")
R.add("step_sd_hi", "41", "derived", "9.06 / 0.22 = 41.2, about 41 sd")
R.add("a_rr_sd_off", "0.36", "derived", "sd of the three kill-switch cell means 70.35, 69.67, 70.22 = 0.36 TPS")
R.add("a_rr_sd_on", "0.35", "derived", "sd of the three AMX-on cell means 79.53, 79.04, 78.86 = 0.35 TPS")
R.add("step_night_sd", "17", "derived", "9.06 / 0.52 = 17.4, more than 17 night-to-night sd")
R.add("step_vs_gptoss", "3.3", "derived", "12.9 / 3.9 = 3.3: the proposed bar against the longest existing bar")
R.add("gap_pts", "+12.7", "derived", "12.9 - 0.2 = 12.7 percentage points between 8 and 2 users per engine (data A)")
R.add("configs_other", "eight", "derived", "12 configs - 4 with a kernel path by shape (llama-8b, mixtral, qwen-3-4b tp2, qwen-3-4b tp4) = 8")
R.add("models_other", "six", "derived", "9 models - 3 with a kernel path by shape (llama-8b, mixtral, qwen-3-4b) = 6")
R.add("models9", "9", "config", "distinct models among the 12 configs")
R.add("kernel_configs", "4", "derived", "configs with a kernel path by shape")
R.add("ttft_s_lo", "2.7", "derived", "2693 ms = 2.7 s")
R.add("ttft_s_hi", "2.8", "derived", "2768 ms = 2.8 s")
R.add("acc_lo", "9.9", "derived", "12.9 - 3 = 9.9 %")
R.add("acc_hi", "15.9", "derived", "12.9 + 3 = 15.9 %")
R.add("acc_pts", "3", "config", "acceptance half-width in percentage points (pre-registered here)")
R.add("acc_sd", "1", "config", "acceptance: run-to-run sd below 1 TPS (pre-registered here)")
R.add("perf_new", "83", "est.", "79 + 4 = 83 min, perf phase with the new config")
R.add("cost_min", "4", "est.", "min per night for the new config (3.6 to 4.0 min per 8-user cell in data A, same per-engine load)")
R.add("t1_cells", "6", "config", "2 arms x 3 reps")
R.add("t1_bench_min", "24", "est.", "6 cells x 4 min = 24 min of benchmark time inside T1")
R.add("t_arms", "2", "config", "arms in T1, T2, T3")
R.add("t_reps", "3", "config", "repetitions per arm in T1, T2, T3")
R.add("t4_nights", "3", "config", "nights to watch before the static goals are set")
R.add("nightly_start", "03:30", "id", "UTC start of the nightly")
R.add("line_prov", "169", "id", "testlib/inventory.py line of the 'already provisioned' branch (checkout fc27f07, 2026-09-17)")
R.add("line_perf_name", "316", "id", "scripts/perf.py line of the '== Benchmarking ... ==' log line (config_name is assigned at 314)")
R.add("line_perf_describe", "434", "id", "scripts/perf.py line of the Talos summary key f'{config_name}_tps @ {nominal_users}'")
R.add("line_3b_lo", "48", "id", "scripts/perf.py first line of the llama-3.2-3b config dict fields")
R.add("line_3b_users", "51", "id", "scripts/perf.py line: nominal_users 32 of llama-3.2-3b")
R.add("line_3b_hi", "58", "id", "scripts/perf.py last line of the llama-3.2-3b config dict fields")
R.add("line_goal_tps", "232", "id", "scripts/system_ci.py line: ('llama-3.2-3b-instruct-fast-tp2', 32) in goal.tps")
R.add("line_goal_min", "246", "id", "scripts/system_ci.py line: ('llama-3.2-3b-instruct-fast-tp2', 32) in goal.min_tps")
R.add("line_yaml_lo", "108", "id", "thresholds/system_ci_perf.yaml first line of the granite llama-3b @32u entry")
R.add("line_yaml_hi", "110", "id", "thresholds/system_ci_perf.yaml line: users: 32 of that entry")
R.add("line_ratchet_lo", "143", "id", "testlib/system_ci_thresholds.py first line of the min_improvement_ratio check")
R.add("line_ratchet_hi", "145", "id", "testlib/system_ci_thresholds.py last line of that check")
R.add("line_prune", "32", "id", "testlib/prompt.py line of prune_convo")
R.add("line_prune_raise", "52", "id", "testlib/prompt.py line of the 'too short' ValueError")
R.add("line_seed", "147", "id", "testlib/tps.py line: seed = round_index * n_users + index")
R.add("line_engines", "87", "id", "testlib/inference_provisioner.py line: accelerator_count // tensor_parallelism")
R.add("line_bec_lo", "96", "id", "testlib/inference_provisioner.py first line of build_explicit_config")
R.add("line_bec_hi", "121", "id", "testlib/inference_provisioner.py last line of build_explicit_config")
R.add("line_patch", "252", "id", "testlib/inference_provisioner.py line: platformd_client.patch_config(payload)")
R.add("line_proxy", "265", "id", "testlib/inference_provisioner.py line: platformd_client.put_test_proxy")
R.add("line_setspec", "579", "id", "testlib/inference_provisioner.py line of the posadm config.set call in _set_speculation (defined at line 578)")
R.add("line_gate_lo", "148", "id", "h/tron/kernels/amx_attn_iface.hpp first line of shape_ok / query_scalar_ok / eligible")
R.add("line_gate_hi", "165", "id", "h/tron/kernels/amx_attn_iface.hpp last line of eligible")
R.add("line_amxon_lo", "1236", "id", "h/tron/models/self_attention.hpp first line of amx_eligible / amx_on")
R.add("line_amxon_hi", "1239", "id", "h/tron/models/self_attention.hpp line: amx_on = amx_eligible && available()")
R.add("tron_head", "85fc8ff4de", "id", "tron commit of the cited kernel lines (the merged PR #3879 head)")

# ---- v2 (2026-09-19) additions: data G, data F detail, KV-token arithmetic, code facts, data P recount, test T0 ----
# G    t4-shapes 2026-08-19: runtron, ingested-llama-3.1-8b-tp2, arena K-mirror binary, kill switch on vs off (exec/results/t4/t4-shapes.txt)
R.add("g_date", "2026-08-19", "id", "date of data G (t4-shapes.txt header 2026-08-19T14:54:27Z)")
R.add("g_off1", "111.82", "G", "TPS, llama-8b ingested plugin, 1 user, prompt 8192, kill switch (mean of 112.158 and 111.475)")
R.add("g_on1", "128.57", "G", "TPS, same cell, AMX (mirror build) on (mean of 128.689 and 128.447)")
R.add("g_gain1", "+15.0", "G", "% gain, 1 user, prompt 8192: 128.568 / 111.817 - 1 = 0.1498")
R.add("g_off8", "46.53", "G", "TPS per user, 8 users, prompt 2048, kill switch (mean of 16 request lines, 46.559 and 46.503)")
R.add("g_on8", "55.70", "G", "TPS per user, same cell, AMX on (55.680 and 55.720)")
R.add("g_gain8", "+19.7", "G", "% gain, 8 users, prompt 2048: 55.700 / 46.532 - 1 = 0.1970")
R.add("g_reps", "2", "config", "repetitions per cell in data G")
R.add("g_sha", "b66c691e", "id", "sha256 prefix of the data-G binary (arena K-mirror build, no commit hash in the file)")
# F detail (qwen-3-4b): 1-user context sweep 2026-09-01 (ctxfill, mirror vs clean, medians of 8 reps) and the 08-19 grid
R.add("f1_p1024", "+1.7", "F", "% qwen 1 user prompt 1024, mirror vs clean (curve.json 1.690)")
R.add("f1_p2048", "+5.0", "F", "% qwen 1 user prompt 2048, mirror vs clean (curve2.json 5.042)")
R.add("f1_p4096", "+14.9", "F", "% qwen 1 user prompt 4096, mirror vs clean (curve.json 14.921)")
R.add("f1_p8192", "+18.0", "F", "% qwen 1 user prompt 8192, mirror vs clean (curve2.json 18.005)")
R.add("f1_p16384", "+26.0", "F", "% qwen 1 user prompt 16384, mirror vs clean (curve.json 25.992)")
R.add("f1_p32768", "+27.6", "F", "% qwen 1 user prompt 32768, mirror vs clean (curve2.json 27.569)")
R.add("fc1_p2048", "+3.8", "F", "% qwen 1 user prompt 2048, canonical vs clean, 2026-08-19 grid (chart-check.csv 3.78)")
R.add("fc1_p8192", "+15.2", "F", "% qwen 1 user prompt 8192, canonical vs clean (15.24; 8-rep replication +15.3)")
R.add("fm8_p2048", "+22.8", "F", "% qwen 8 users prompt 2048, mirror vs clean (22.83)")
R.add("fm8_p8192", "+28.1", "F", "% qwen 8 users prompt 8192, mirror vs clean (28.07; 8-rep replication +27.8)")
R.add("f_rep1", "56.222", "F", "TPS per user, rep 1 of the qwen canonical 8-user prompt-2048 cell (amx-summary.csv)")
R.add("f_rep2", "52.359", "F", "TPS per user, rep 2 of that cell")
R.add("f_rep3", "52.223", "F", "TPS per user, rep 3 of that cell")
R.add("f_sd", "2.271", "F", "TPS sd of the three reps of that cell (every other decode cell of the grid has sd at most 0.73)")
R.add("f_clean8", "45.059", "F", "TPS per user, qwen clean binary, 8 users, prompt 2048 (amx-summary.csv)")
R.add("f_pr8", "52.26", "F", "TPS per user, qwen canonical, 8 users, prompt 2048 in the perf rounds of 2026-08-25 and 08-30 (52.263 and 52.262)")
R.add("f_p2048_alt", "+16.0", "derived", "52.26 / 45.059 - 1 = 0.1598: the same cell with the perf-round value instead of the noisy 3-rep mean")
R.add("f_share256", "15.9", "F", "% attention share of a decode token, qwen 1 user, prompt 256, kill-switch arm (fence3 medians.json 636.2 / 3994.9)")
R.add("f_share2048", "31.6", "F", "% attention share, prompt 2048 (1556.7 / 4930.2)")
R.add("f_share8192", "62.6", "F", "% attention share, prompt 8192 (5711.7 / 9124.6)")
R.add("f_agg", "1.10", "F", "ratio of the qwen 8-user aggregate rate to the 1-user rate at prompt 8192, clean binary (8 x 14.497 / 105.648)")
R.add("f_unit8192", "1.26", "F", "AVX / canonical per-unit attention time at prompt 8192 (single-attn-20260901 summary.json 3.64 / 2.89)")
R.add("f_ceiling", "+26", "derived", "1.26 - 1 = 0.26: the TPS gain if attention were the whole step and ran 1.26x faster (1 - 1 / 1.26 = 0.206 is the share of step time saved, not the TPS gain)")
R.add("f_saved", "20.6", "derived", "% of step time saved when attention is the whole step: 1 - 1 / 1.26")
R.add("f_steps8", "7.3", "derived", "one-user steps per 8-user step at prompt 8192: 8 / 1.10 = 7.27")
R.add("f_share8_est", "69", "est.", "% attention share of an 8-user qwen step at prompt 8192 if attention scales linearly with users: 8 x 62.6 / (8 / 1.10) = 5.01 / 7.27 = 0.69; not measured")
R.add("f_pred8", "+17", "derived", "predicted 8-user gain from the estimated share: 1 / (1 - 0.69 x 0.206) - 1 = 0.166, about +17 %")
R.add("fm1_p2048", "+4.5", "F", "% qwen 1 user prompt 2048, mirror vs clean, 2026-08-19 grid (chart-check.csv 4.47)")
R.add("fm1_p8192", "+19.6", "F", "% qwen 1 user prompt 8192, mirror vs clean, grid (19.64; 8-rep replication +19.7)")
R.add("f_mc_1u8192", "4.4", "derived", "points mirror above canonical, 1 user prompt 8192: 19.6 - 15.2")
R.add("f_mc_8u2048", "3.9", "derived", "points mirror above canonical, 8 users prompt 2048: 22.8 - 19.0 (grid values)")
R.add("f_mc_8u8192", "10.6", "derived", "points mirror above canonical, 8 users prompt 8192: 28.1 - 17.5")
R.add("ratio_lo", "3.8", "derived", "15.0 / 3.9 = 3.8: the data-G 1-user gain over the data-A 4-user gain at about 8K KV tokens per step")
R.add("ratio_hi", "7.5", "derived", "15.0 / 2.0 = 7.5: the same over the data-C 256-token gain")
R.add("spread_step", "13", "derived", "points: 15.0 - 2.0, the spread of the llama gains at 8 to 9K KV tokens per engine step")
R.add("spread_mb", "4.1", "derived", "points: 17.0 - 12.9, the spread of the llama gains at 7 to 9K KV tokens per minibatch (7168, 7965, 8320)")
R.add("st_frac24", "28", "derived", "% of the added step time that AMX saves, 2 to 4 users: 0.30 / 1.07")
R.add("st_frac48", "27", "derived", "% of the added step time that AMX saves, 4 to 8 users: 1.63 / 6.13")
R.add("st_ratio", "5.7", "derived", "6.13 / 1.07: the 4-to-8 step growth over the 2-to-4 step growth, for twice the added attention work")
R.add("rec_prompt_a", "1032", "A", "tokens, recorded mean prompt of the data-A 2-user cells (perf.json prompt_tokens_mean 1032.3) for prompt_length 1024")
R.add("rec_prompt_b", "1055", "B", "tokens, recorded mean prompt of llama-8b in the nightly layout (perf.json prompt_tokens 1054.85) for prompt_length 1024")
R.add("ctx_nominal", "1984", "derived", "1024 + (896 + 1024) / 2: the context per user with the nominal prompt instead of the recorded one")
R.add("qgap", "3.2", "derived", "points: 26.0 - 22.8, the qwen 1-user prompt-16384 gain over the 8-user prompt-2048 gain at similar KV tokens per step")
R.add("line_group_lo", "2146", "id", "h/tron/scheduler/full.hpp first line: live_group = parent.live ? parent.live_group : next_live_group++ (each root token forms its own group)")
R.add("line_group_hi", "2148", "id", "h/tron/scheduler/full.hpp last line of that assignment (repeated at lines 2230 to 2232)")
R.add("line_cfg_mb", "62", "id", "h/tron/models/config.hpp line: runtime max_minibatches default -1")
R.add("line_cfg_merge_lo", "103", "id", "h/tron/models/config.hpp first line of merge_max_minibatches (min of runtime and plugin bound)")
R.add("line_cfg_merge_hi", "108", "id", "h/tron/models/config.hpp last line of merge_max_minibatches")
R.add("line_perf_log", "211", "id", "scripts/perf.py line that prints shared_prefix= in the config log line")
R.add("line_perf_shared", "354", "id", "scripts/perf.py line that passes shared_prompt_length into Config")
R.add("line_ctrl_launch", "58", "id", "scripts/tps_controller.py line that launches scripts/tps_node.py")
R.add("line_sharegpt_load", "23", "id", "testlib/prompt.py line that opens sharegpt_1000.json")
R.add("fail2048", "39", "P", "of 80 default seeds that prune_convo rejects at prompt_length 2048")
R.add("f_grid_date", "2026-08-19", "id", "date of the qwen 8-user grid (t4-suite.txt)")
R.add("f_curve_date", "2026-09-01", "id", "date of the qwen 1-user context sweep (ctxfill, ctxfill2)")
# KV tokens per engine per decode step (users per engine x mean context per user), in thousands (K)
R.add("kv_a2", "4.0", "derived", "K KV tokens per engine step, data A 2 users: 2 x 1992 = 3985")
R.add("kv_a4", "8.0", "derived", "data A 4 users: 4 x 1989 = 7957")
R.add("kv_a8", "15.9", "derived", "data A 8 users: 8 x 1991 = 15930")
R.add("kv_b", "4.0", "derived", "data B: 2 x 2015 = 4030")
R.add("kv_c256", "9.2", "derived", "data C 256 tokens: 8 x 1152 = 9216")
R.add("kv_c1536", "14.3", "derived", "data C 1536 tokens: 8 x 1792 = 14336")
R.add("kv_g1", "8.3", "derived", "data G 1 user prompt 8192: 1 x 8320")
R.add("kv_g8", "17.4", "derived", "data G 8 users prompt 2048: 8 x 2176 = 17408")
R.add("kv_f8_2048", "17.4", "derived", "data F 8 users prompt 2048: 8 x 2176 = 17408")
R.add("kv_f8_8192", "66.6", "derived", "data F 8 users prompt 8192: 8 x 8320 = 66560")
R.add("kv_f1_1024", "1.2", "derived", "data F 1 user prompt 1024: 1152")
R.add("kv_f1_2048", "2.2", "derived", "1 user prompt 2048: 2176")
R.add("kv_f1_4096", "4.2", "derived", "1 user prompt 4096: 4224")
R.add("kv_f1_8192", "8.3", "derived", "1 user prompt 8192: 8320")
R.add("kv_f1_16384", "16.5", "derived", "1 user prompt 16384: 16512")
R.add("kv_f1_32768", "32.9", "derived", "1 user prompt 32768: 32896")
R.add("ctx_win", "1992", "derived", "mean context per user inside the CI window, data A 2 users: prompt_tokens_mean 1032 + (896 + 1024) / 2 = 1992")
R.add("ctx_c256", "1152", "derived", "mean context per user, runtron, prompt 1024, 256 generated: 1024 + 128")
R.add("ctx_c1536", "1792", "derived", "mean context per user, runtron, prompt 1024, 1536 generated: 1024 + 768")
R.add("ctx_g1", "8320", "derived", "mean context, runtron, prompt 8192, 256 generated: 8192 + 128")
R.add("ctx_g8", "2176", "derived", "mean context, runtron, prompt 2048, 256 generated: 2048 + 128")
R.add("kv_llama_tok", "128", "model", "KiB of KV per token, llama-3.1-8b: 32 layers x 8 KV heads x 128 x 2 (K and V) x 2 bytes")
R.add("kv_qwen_tok", "144", "model", "KiB of KV per token, qwen-3-4b: 36 layers x 8 KV heads x 128 x 2 x 2 bytes")
# step-time arithmetic, data A kill-switch arm (1000 / TPS)
R.add("st_off2", "7.06", "derived", "ms per decode step, 2 users, kill switch: 1000 / 141.57")
R.add("st_off4", "8.13", "derived", "ms per step, 4 users: 1000 / 122.93")
R.add("st_off8", "14.27", "derived", "ms per step, 8 users: 1000 / 70.08")
R.add("st_grow24", "1.07", "derived", "ms added to the step from 2 to 4 users: 8.13 - 7.06")
R.add("st_grow48", "6.13", "derived", "ms added from 4 to 8 users: 14.27 - 8.13")
R.add("st_save2", "0.01", "derived", "ms saved by AMX per step, 2 users: 1000 / 141.57 - 1000 / 141.81")
R.add("st_save4", "0.30", "derived", "ms saved, 4 users: 1000 / 122.93 - 1000 / 127.69")
R.add("st_save8", "1.63", "derived", "ms saved, 8 users: 1000 / 70.08 - 1000 / 79.14")
# tron code facts (worktree ~/workspace/tron-amx at 85fc8ff4de)
R.add("line_chunk_lo", "217", "id", "h/tron/models/model.hpp first line of the chunk count in chunk_evenly")
R.add("line_chunk_hi", "227", "id", "h/tron/models/model.hpp last line of the split rule")
R.add("line_llama_mb", "183", "id", "h/tron/plugins/llama.hpp line: max_minibatches = -1 (no plugin-imposed limit)")
R.add("line_ingest_mb", "262", "id", "ingest/src/TronCpp.hs line: max_minibatches = 1 for every ingested plugin")
R.add("line_grain", "309", "id", "h/tron/models/common.hpp line: minibatch_grain_size = 8")
R.add("line_wo", "1104", "id", "h/tron/plugins/llama.hpp line region where the WO matmul is prepared for the FPGA cards (fill_matmul_template, prepare_matmul)")
# systems_test code facts (checkout fc27f07)
R.add("line_tps_field", "79", "id", "testlib/tps.py line: shared_prompt_length Config field")
R.add("line_tps_cu", "85", "id", "testlib/tps.py line: continuous_usage default 1")
R.add("line_tps_gen_lo", "145", "id", "testlib/tps.py first line of the prompt_generator.generate call")
R.add("line_tps_gen_hi", "148", "id", "testlib/tps.py last line of that call")
R.add("line_tps_seq", "429", "id", "testlib/tps.py line: sequence_length bookkeeping (only when continuous_usage is 0)")
R.add("line_perf_ctrl", "11", "id", "scripts/perf.py line: the tps_controller import is commented out")
R.add("line_perf_import", "12", "id", "scripts/perf.py line: from testlib.tps import benchmark_tps")
R.add("line_perf_mode", "345", "id", "scripts/perf.py line: prompt_mode is commented out")
R.add("line_gen_lo", "56", "id", "testlib/prompt.py first line of PromptGenerator.generate")
R.add("line_gen_hi", "75", "id", "testlib/prompt.py last line of generate (seed % len(convos), then prune_convo)")
R.add("prompt3b_rec", "228", "B", "tokens, recorded prompt of llama-3.2-3b fast tp2 @32u in the nightly layout (perf.json prompt_tokens mean 227.8, ci-mimic base and canon-ci canon)")
# data P recount over the whole corpus (same tokenizer and system line; scratchpad sharegpt_tok_lens.json)
R.add("p_n", "1000", "P", "conversations in sharegpt_1000.json")
R.add("p_ge2048", "527", "P", "conversations of at least 2048 tokens")
R.add("p_ge2048_80", "41", "P", "of the 80 default seeds at least 2048 tokens (39 fail)")
R.add("p_ge4096", "12", "P", "conversations of at least 4096 tokens")
R.add("p_ge4096_80", "2", "P", "of the 80 default seeds at least 4096 tokens (78 fail)")
R.add("p_ge8192", "5", "P", "conversations of at least 8192 tokens")
R.add("p_ge8192_80", "0", "P", "of the 80 default seeds at least 8192 tokens (80 fail)")
R.add("p_min", "1531", "P", "tokens, shortest conversation")
R.add("p_median", "2064.5", "P", "tokens, median of the 1000 conversation lengths (between the two middle values)")
R.add("p_max", "21146", "P", "tokens, longest conversation")
# test T0 (llama-8b levers campaign, CI harness, nightly layout, whole machine)
R.add("t0_hours", "5.3", "est.", "h, T0 wall time with two arms: 6 passes x 44 min + 6 package switches x 6 min + the check cell (footnote 19)")
R.add("t0_pass_min", "44", "est.", "min per pass: 40 min of benchmark time (10 configs, footnote 19) + about 4 min for the ten 20 s AMX-busy probes and snapshots")
R.add("t0_bench_min", "40", "est.", "min of benchmark time per pass: 2.5 + 3 + 3.5 + 4 + 5.5 + 6 + 3 + 2.5 + 4 + 6")
R.add("t0_probe_min", "4", "est.", "min per pass for the ten AMX-busy probes (20 s each plus setup) and the layout snapshots")
R.add("t0_pass6_h", "4.4", "derived", "6 passes x 44 min = 264 min = 4.4 h")
R.add("cell_2u_b", "2.52", "B", "min, the llama-8b @8u config (2 users per engine, prompt 1024) in the canonical arm of data B, harness per_model_perf_test_duration (2.87 and 3.83 min in the two ci-mimic arms)")
R.add("cell_4u_a", "2.41", "A", "min, the 4-users-per-engine cell of data A (2 engines, no proxy)")
R.add("kv_t0_max8", "3.5", "derived", "GiB KV need of the largest T0 cell, 8 users x (2048 + 1536) tokens x 128 KiB")
R.add("kv_t0_max2", "2.4", "derived", "GiB KV need of the 2-user prompt-8192 cell, 2 x (8192 + 1536) x 128 KiB")
R.add("kv_check", "9.5", "derived", "GiB KV need of the check cell, 8 users x (8192 + 1536) tokens x 128 KiB (not a T0 config)")
R.add("hp_engine", "128", "config", "1 GiB hugepages per engine (RZ_CLI_ARGS --nr_hugepages 128 in every instance)")
R.add("t975_df", "2", "config", "degrees of freedom of the paired t over 3 passes")
R.add("line_deleted_check", "262", "id", "st_ci_perf.py first line of the deleted-binary check (logs only today; T0 makes it stop the pass)")
R.add("t0_switch_min", "6", "est.", "min per package switch: apt swap about 9 s, 20 s settle, engine stop and start with the idle test, re-provisioning 1 to 2 min (data B log and snapshots)")
R.add("t0_configs", "10", "config", "configs per arm pass in T0")
R.add("t0_passes", "3", "config", "passes per arm in T0 (repetitions), arms interleaved")
R.add("t0_cells", "60", "derived", "10 configs x 2 arms x 3 passes = 60 config-cells (90 with the optional kill-switch arm)")
R.add("t0_reps", "3", "config", "repetitions per arm and config in T0")
R.add("t0_p2u", "1024, 2048, 3000, 4096, 7168 and 8192", "config", "prompt lengths of the 2-users-per-engine cells (nominal_users 8)")
R.add("t0_p8u", "1024 and 2048", "config", "prompt lengths of the 8-users-per-engine cells (nominal_users 32)")
R.add("t0_p1u", "7168", "config", "prompt length of the 1-user-per-engine cell (nominal_users 4)")
R.add("ovh", "31", "B", "tokens the server counts around prompt_length in the nightly layout: recorded prompt 1054.85 for prompt_length 1024 in data B (data A's 2-engine layout recorded 1029.25 to 1032.3); assumed the same at every prompt length (est. above 1024)")
R.add("kv_t0_2u", "4.0, 6.1, 8.0, 10.2, 16.3 and 18.4", "derived", "K KV tokens per engine step of the 2-user cells: 2 x (prompt + 31 + 960)")
R.add("kv_t0_8u", "16.1 and 24.3", "derived", "8-user cells: 8 x (prompt + 991)")
R.add("kv_t0_4u", "8.1", "derived", "4 users x prompt 1024: 4 x 2015 = 8060")
R.add("kv_t0_1u", "8.2", "derived", "1 user x prompt 7168: 8159")
R.add("t0_pair16", "16.3K against 16.1K", "derived", "pair at 16K: 2 users x prompt 7168 (2 x 8159 = 16318) against 8 users x prompt 1024 (8 x 2015 = 16120), ratio 1.01")
R.add("t0_triple8", "8.2K, 8.0K and 8.1K", "derived", "triple at 8K: 1 user x prompt 7168 (8159), 2 users x prompt 3000 (2 x 3991 = 7982), 4 users x prompt 1024 (8060)")
R.add("t0_pass_cells_min", "2.5, 3, 3.5, 4, 5.5, 6, 3, 2.5, 4 and 6", "est.", "min per config in one pass: 2 users at prompt 1024 / 2048 / 3000 / 4096 / 7168 / 8192, then 1 user at 7168, 4 users at 1024, 8 users at 1024 / 2048 (anchors: 2.52 min for the prompt-1024 2-user config in data B, 2.41 min at 4 users and 3.6 to 4.0 min at 8 users in data A; long-prompt cells scaled for the longer TTFT and slower decode, no long-prompt cell timed yet)")
R.add("t0_window_h", "12", "config", "h between the nightly lease clearing (about 13:20 UTC) and the pre-CI hold (01:40 UTC)")
R.add("canon_preset", "6f37cd2ed9", "id", "commit of the two-line CMakePresets.json change (TRON_AMX_DISPATCH=ON in the deb preset) cherry-picked onto main 3faba6d0fd for the canonical deb")
R.add("canon_main", "3faba6d0fd", "id", "main commit the canonical deb was built from (the same commit the nightly deb 2026.09.18-3faba6d0 was built from)")
R.add("canon_insns", "86", "B", "AMX tile instructions in the packaged rinzler of the canonical deb (manifest.json checks.amx_tile_insns)")
R.add("t0_band", "3", "config", "percentage points: the two levers count as one mechanism when the equal-KV pairs agree within this band (pre-registered here)")
R.add("t0_t975", "4.303", "config", "|t| limit for 3 repetitions (the data-A rule)")
R.add("t0_start", "13:20", "id", "UTC, earliest start of T0 (the nightly's lease clears about then)")
R.add("mix_m2048_a", "-0.1", "F", "% mixtral tp2, 8 users, prompt 2048, mirror vs canonical, perf round 2026-08-25 (not an AMX gain)")
R.add("mix_m8192_a", "+8.9", "F", "% mixtral tp2, 8 users, prompt 8192, mirror vs canonical, 2026-08-25")
R.add("mix_m2048_b", "-1.9", "F", "% same cell, 2026-08-30; one outlier repetition (35.94 TPS) in the canonical cell; the other two repetitions give -0.1 %")
R.add("mix_outlier", "35.94", "F", "TPS, the outlier repetition of the mixtral canonical prompt-2048 cell of 2026-08-30 (33.752, 35.940, 33.891)")
R.add("mix_m8192_b", "+9.6", "F", "% same cell, 2026-08-30")


# ---- DATA H: l8b-levers 2026-09-19 (test T0 as run), registered from the campaign's summary.json ----
import sys as _sys
_sys.path.insert(0, "/home/jhan/workspace/intel-AMX/exec/l8b-levers-20260919")
from h_registry import register as _register_h  # noqa: E402
_register_h(R)
R.add("h_report", "CI-test/status/Saturday-llama-3.1-8b.html", "id", "report page of data H")

# ---- DATA I: l8b-8u4k 2026-09-20 (8 users per engine x prompt 4096), registered from the campaign's summary.json ----
_sys.path.insert(0, "/home/jhan/workspace/intel-AMX/exec/l8b-8u4k-20260920")
from i_registry import register as _register_i  # noqa: E402
_register_i(R)


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def wrap(text, width=108):
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width and cur:
            lines.append(cur); cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        lines.append(cur)
    return lines


def svg_header(W, H, title, subtitle_lines):
    out = [f'<svg viewBox="0 0 {W} {H}" width="{W}" height="{H}" style="max-width:{W}px;font-family:system-ui,-apple-system,\'Segoe UI\',sans-serif;background:{SURF}" role="img" aria-label="{esc(title)}">',
           f'<text x="16" y="24" font-size="16" font-weight="600" fill="{INK}">{esc(title)}</text>']
    for i, l in enumerate(subtitle_lines):
        out.append(f'<text x="16" y="{44 + 16 * i}" font-size="12" fill="{INK2}">{esc(l)}</text>')
    return out


def haloed_text(x, y, attrs, text):
    halo_attrs = re.sub(r'\s*fill="[^"]*"', "", attrs)
    return (f'<text x="{x:.1f}" y="{y:.1f}" {halo_attrs} stroke="{SURF}" stroke-width="3" stroke-linejoin="round" fill="{SURF}">{text}</text>'
            f'<text x="{x:.1f}" y="{y:.1f}" {attrs}>{text}</text>')


def legend(items):
    def sw(c, shape):
        if shape == "rect":
            return f'<i style="background:{c};width:18px;border-radius:2px"></i>'
        if shape == "rect-light":
            return f'<i style="background:{c};opacity:.45;width:18px;border-radius:2px;border:1px dashed {INK2}"></i>'
        if shape == "ring":
            return f'<i style="background:none;border:2px solid {c};width:8px;height:8px"></i>'
        if shape == "square":
            return f'<i style="background:none;border:2px solid {c};width:8px;height:8px;border-radius:0"></i>'
        return f'<i style="background:{c}"></i>'
    return '<div class="legend">' + "".join(f'<span>{sw(it[0], it[2] if len(it) > 2 else "dot")}{esc(it[1])}</span>' for it in items) + "</div>"


# ---------------- chart 1: gain vs users per engine ----------------
def chart_gain_vs_load():
    title = "AMX gain on llama-3.1-8b vs users per engine"
    sub = wrap("TPS with the AMX kernel against TPS without it, prompt 1024, 1536 generated tokens. "
               "Green = data A (2 engines placed like the nightly's socket-1 engines, one package with the kill switch off and on). "
               "Gray = data B (nightly layout, whole machine, 4 engines, AMX package against the nightly deb). "
               "Ring = data D (one engine, 8 users). Every point is a direct measurement. "
               "Points at the same load are offset sideways to stay apart.")
    W, H = 960, 490
    top = 52 + 16 * len(sub) + 10
    left, right, bottom = 90, 60, 70
    pw, ph = W - left - right, H - top - bottom
    ymin, ymax = -2.5, 16.0
    cats = [2, 4, 8]

    def X(i):
        return left + (i + 0.5) / len(cats) * pw

    def Y(v):
        return top + (ymax - v) / (ymax - ymin) * ph

    out = svg_header(W, H, title, sub)
    for v in range(0, 17, 2):
        out.append(f'<line x1="{left}" y1="{Y(v):.1f}" x2="{left + pw}" y2="{Y(v):.1f}" stroke="{GRID if v else MUTED}" stroke-width="1"/>')
        out.append(f'<text x="{left - 8}" y="{Y(v) + 4:.1f}" font-size="11" fill="{TICK}" text-anchor="end">{v:+d} %</text>')
    out.append(f'<text transform="translate(22,{top + ph / 2:.1f}) rotate(-90)" font-size="12" fill="{INK2}" text-anchor="middle">TPS gain, AMX on vs off (percent)</text>')
    for i, c in enumerate(cats):
        out.append(f'<text x="{X(i):.1f}" y="{top + ph + 22}" font-size="12" fill="{INK}" text-anchor="middle">{c}</text>')
    out.append(f'<text x="{left + pw / 2:.1f}" y="{top + ph + 44}" font-size="12" fill="{INK2}" text-anchor="middle">users per engine (today\'s nightly: 2. Proposed: 8)</text>')
    # data A points and the connecting line
    A = [(0, 0.2, R("a_gain2"), f'2 users per engine: {R("a_off2")} to {R("a_on2")} TPS, paired t {R("a_t2")} (not resolved)'),
         (1, 3.9, R("a_gain4"), f'4 users per engine: {R("a_off4")} to {R("a_on4")} TPS, paired t {R("a_t4")}'),
         (2, 12.9, R("a_gain8"), f'8 users per engine: {R("a_off8")} to {R("a_on8")} TPS, paired t {R("a_t8")}')]
    # the gap called out on the figure: a dashed line at today's level (+0.2 % at 2 users per engine) and a dashed
    # vertical guide from that level up to the 8-user dot
    out.append(f'<line x1="{X(0):.1f}" y1="{Y(0.2):.1f}" x2="{X(2):.1f}" y2="{Y(0.2):.1f}" stroke="{INK2}" stroke-width="1" stroke-dasharray="4 3"/>')
    out.append(f'<line x1="{X(2):.1f}" y1="{Y(0.2):.1f}" x2="{X(2):.1f}" y2="{Y(12.9):.1f}" stroke="{INK2}" stroke-width="1" stroke-dasharray="4 3"/>')
    out.append(haloed_text(X(2) - 12, Y(6.5) + 4, f'font-size="11" fill="{INK2}" text-anchor="end"', f'{R("gap_pts")} points above today\'s load'))
    out.append(haloed_text((X(1) + X(2)) / 2, Y(0.2) + 16, f'font-size="11" fill="{INK2}" text-anchor="middle"', "today's nightly level (2 users per engine)"))
    for i, v, lab, tip in A:
        out.append(f'<circle cx="{X(i):.1f}" cy="{Y(v):.1f}" r="8" fill="{SURF}"/>')
        out.append(f'<circle cx="{X(i):.1f}" cy="{Y(v):.1f}" r="6" fill="{C_GREEN}"><title>{esc(tip)}</title></circle>')
    # A labels
    # the 2-user label sits above-left of its dot, clear of the zero line
    out.append(haloed_text(X(0) - 12, Y(0.2) - 8, f'font-size="13" font-weight="600" fill="{INK}" text-anchor="end"', f'{R("a_gain2")} %'))
    out.append(haloed_text(X(1) + 12, Y(3.9) + 4, f'font-size="13" font-weight="600" fill="{INK}" text-anchor="start"', f'{R("a_gain4")} %'))
    out.append(haloed_text(X(2) + 12, Y(12.9) + 4, f'font-size="13" font-weight="600" fill="{INK}" text-anchor="start"', f'{R("a_gain8")} %'))
    out.append(haloed_text(X(2) + 12, Y(12.9) + 20, f'font-size="11" fill="{INK2}" text-anchor="start"', f'{R("step_tps")} TPS more with AMX'))
    # data B: two nightly-layout points at 2 users per engine, drawn right of the A dot (sideways offset for legibility).
    # Both labels are stacked above the zero line and below the 4-user dot (+3.9 %), each joined to its dot by a
    # short leader line. The +1.2 label sits lower because its dot is further right (its leader stays clear of the
    # other dot).
    lx = X(0) + 44 + 18
    B = [(1.2, 44, R("b_canon_gain"), f'canonical-AMX arm vs the nightly deb, paired t {R("b_canon_t")} (resolved)', Y(1.6) + 4, "nightly layout, canonical AMX (B)"),
         (0.8, 22, R("b_target_gain"), f'PR #4424 + AMX arm vs the nightly deb, paired t {R("b_target_t")}', Y(3.0) + 4, "nightly layout, PR #4424 + AMX (B)")]
    for v, dx, lab, tip, ly, name in B:
        cx = X(0) + dx
        out.append(f'<line x1="{cx:.1f}" y1="{Y(v) - 7:.1f}" x2="{lx - 4:.1f}" y2="{ly - 4:.1f}" stroke="{C_GRAY}" stroke-width="1"/>')
        out.append(f'<circle cx="{cx:.1f}" cy="{Y(v):.1f}" r="8" fill="{SURF}"/>')
        out.append(f'<circle cx="{cx:.1f}" cy="{Y(v):.1f}" r="6" fill="{C_GRAY}"><title>{esc(tip)}</title></circle>')
        out.append(haloed_text(lx, ly, f'font-size="12" fill="{INK2}" text-anchor="start"', f'{lab} % {name}'))
    # data D: one engine with 8 users, hollow ring left of the 8-user A dot, label to its left
    cx = X(2) - 26
    out.append(f'<circle cx="{cx:.1f}" cy="{Y(13.9):.1f}" r="6" fill="{SURF}" stroke="{C_GREEN}" stroke-width="2.5"><title>one engine, 8 users, rinzler + CI harness, canonical kernel</title></circle>')
    out.append(haloed_text(cx - 12, Y(13.9) + 4, f'font-size="12" fill="{INK2}" text-anchor="end"', f'{R("d_llama8b")} % one engine, 8 users (D)'))
    out.append("</svg>")
    return "\n".join(out)


# ---------------- chart 3: gain vs KV tokens per engine step (v2) ----------------
def chart_gain_vs_kv():
    import math
    title = "AMX gain against attention work per decode step (KV tokens per engine step)"
    sub = wrap("x = users per engine times the mean context per user during the TPS measurement, in thousands of tokens (log scale). "
               "Filled dots = llama-3.1-8b (data A green, B gray, C orange, G blue; ring = data D). Violet = qwen-3-4b (data F): "
               "the line is the 1-user context sweep (mirror build against a clean binary), the squares are the 8-user canonical "
               "cells. Black squares = data H, the T0 campaign in the nightly layout (3 passes, canonical deb against nightly deb); "
               "the dashed line joins its 2-users-per-engine context lever. If users and context were one lever, the llama dots would form one curve.")
    W, H = 960, 560
    top = 52 + 16 * len(sub) + 10
    left, right, bottom = 70, 40, 64
    pw, ph = W - left - right, H - top - bottom
    xmin, xmax = math.log2(1.0), math.log2(90.0)
    ymin, ymax = -2.0, 30.0
    C_VIOLET = "#4a3aa7"

    def X(k):
        return left + (math.log2(k) - xmin) / (xmax - xmin) * pw

    def Y(v):
        return top + (ymax - v) / (ymax - ymin) * ph

    out = svg_header(W, H, title, sub)
    for v in range(0, 31, 5):
        out.append(f'<line x1="{left}" y1="{Y(v):.1f}" x2="{left + pw}" y2="{Y(v):.1f}" stroke="{GRID if v else MUTED}" stroke-width="1"/>')
        out.append(f'<text x="{left - 8}" y="{Y(v) + 4:.1f}" font-size="11" fill="{TICK}" text-anchor="end">{v:+d} %</text>')
    for k in (1, 2, 4, 8, 16, 32, 64):
        out.append(f'<line x1="{X(k):.1f}" y1="{top}" x2="{X(k):.1f}" y2="{top + ph}" stroke="{GRID}" stroke-width="1"/>')
        out.append(f'<text x="{X(k):.1f}" y="{top + ph + 18}" font-size="11" fill="{TICK}" text-anchor="middle">{k}K</text>')
    out.append(f'<text x="{left + pw / 2:.1f}" y="{top + ph + 40}" font-size="12" fill="{INK2}" text-anchor="middle">KV tokens per engine per decode step = users per engine x mean context per user (thousands, log scale)</text>')
    out.append(f'<text transform="translate(20,{top + ph / 2:.1f}) rotate(-90)" font-size="12" fill="{INK2}" text-anchor="middle">TPS gain with the AMX kernel (percent)</text>')
    # qwen 1-user curve (data F), thin line, small dots
    q1 = [(1.152, 1.7), (2.176, 5.0), (4.224, 14.9), (8.320, 18.0), (16.512, 26.0), (32.896, 27.6)]
    pts = " ".join(f"{X(k):.1f},{Y(v):.1f}" for k, v in q1)
    out.append(f'<polyline points="{pts}" fill="none" stroke="{C_VIOLET}" stroke-width="1.5" stroke-opacity="0.8"/>')
    for k, v in q1:
        out.append(f'<circle cx="{X(k):.1f}" cy="{Y(v):.1f}" r="3.5" fill="{C_VIOLET}"><title>qwen-3-4b, 1 user, mean context {int(k * 1000)} tokens: {v:+.1f} % (mirror vs clean, data F)</title></circle>')
    out.append(haloed_text(X(32.896) - 10, Y(27.6) - 12, f'font-size="11" fill="{C_VIOLET}" text-anchor="end"', "qwen-3-4b, 1 user, prompt 1024 to 32768 (F, mirror build)"))
    out.append(haloed_text(X(4.224) - 8, Y(14.9) - 8, f'font-size="11" fill="{C_VIOLET}" text-anchor="end"', f'{R("f1_p4096")} % at prompt 4096'))
    out.append(haloed_text(X(2.176) + 8, Y(5.0) + 4, f'font-size="11" fill="{C_VIOLET}" text-anchor="start"', f'{R("f1_p2048")} % at prompt 2048'))
    # llama points: (kv K, gain, color, label, dx, dy, anchor)
    L = [
        (3.985, 0.2, C_GREEN, f'2 users per engine, prompt 1024 (A): {R("a_gain2")} %', -10, 17, "end"),
        (7.957, 3.9, C_GREEN, f'4 users per engine (A): {R("a_gain4")} %', -10, 4, "end"),
        (15.93, 12.9, C_GREEN, f'8 users per engine (A): {R("a_gain8")} %', 12, 26, "start"),
        (4.03, 1.2, C_GRAY, f'nightly layout (B): {R("b_canon_gain")} %', -12, -8, "end"),
        (9.216, 2.0, C_ORANGE, f'8 users, context {R("ctx_c256")} (C): {R("c_gain256")} and {R("c_attr_main")} %', 12, 6, "start"),
        (9.216, 3.0, C_ORANGE, f'8 users, context {R("ctx_c256")} (C): {R("c_attr_main")} % (canonical build against the clean binary)', 0, 0, "none"),
        (14.336, 17.0, C_ORANGE, f'8 users, context {R("ctx_c1536")} (C): {R("c_gain1536")} %', -12, -8, "end"),
        (8.32, 15.0, C_BLUE, f'1 user, prompt 8192 (G): {R("g_gain1")} %', -12, 16, "end"),
        (17.408, 19.7, C_BLUE, f'8 users, prompt 2048 (G): {R("g_gain8")} %', 12, -16, "start"),
    ]
    # the split at about 8K: a dashed bracket from +2.0 to +15.0
    out.append(f'<line x1="{X(8.32) + 22:.1f}" y1="{Y(15.0):.1f}" x2="{X(8.32) + 22:.1f}" y2="{Y(2.0):.1f}" stroke="{INK2}" stroke-width="1" stroke-dasharray="4 3"/>')
    out.append(haloed_text(X(8.32) + 28, Y(8.5) + 4, f'font-size="11" fill="{INK2}" text-anchor="start"', "same attention work (8 to 9K): +2.0 to +15.0 %, not one curve"))
    for k, v, col, lab, dx, dy, anc in L:
        out.append(f'<circle cx="{X(k):.1f}" cy="{Y(v):.1f}" r="8" fill="{SURF}"/>')
        out.append(f'<circle cx="{X(k):.1f}" cy="{Y(v):.1f}" r="6" fill="{col}"><title>{esc(lab)}</title></circle>')
        if lab and anc != "none":
            out.append(haloed_text(X(k) + dx, Y(v) + dy, f'font-size="11" fill="{INK}" text-anchor="{anc}"', esc(lab)))
    # qwen 8-user canonical cells (data F), hollow squares, drawn after the dots so they stay visible; the 17.4K square is
    # offset 9 px right of the data-G dot at the same load (the caption says so)
    for k, v, dx, lab in [(17.408, 19.0, 9, f'qwen 8 users, prompt 2048: {R("f_p2048")} % (F, canonical; {R("f_p2048_alt")} % est. with the perf-round value)'), (66.56, 17.5, 0, f'qwen 8 users, prompt 8192: {R("f_p8192")} % (F, canonical)')]:
        out.append(f'<rect x="{X(k) + dx - 6:.1f}" y="{Y(v) - 6:.1f}" width="12" height="12" fill="{SURF}" stroke="{C_VIOLET}" stroke-width="2"><title>{esc(lab)}</title></rect>')
    out.append(haloed_text(X(17.408) + 20, Y(19.0) + 4, f'font-size="11" fill="{C_VIOLET}" text-anchor="start"', f'qwen 8 users (F, canonical): {R("f_p2048")} %'))
    out.append(haloed_text(X(66.56) - 10, Y(17.5) + 4, f'font-size="11" fill="{C_VIOLET}" text-anchor="end"', f'qwen 8 users (F, canonical): {R("f_p8192")} %'))
    # data D ring at 15.9K
    out.append(f'<circle cx="{X(15.93):.1f}" cy="{Y(13.9):.1f}" r="6" fill="{SURF}" stroke="{C_GREEN}" stroke-width="2.5"><title>one engine, 8 users (D): +13.9 %</title></circle>')
    out.append(haloed_text(X(15.93) + 12, Y(13.9) + 18, f'font-size="11" fill="{INK2}" text-anchor="start"', f'one engine, 8 users (D): {R("d_llama8b")} %'))
    # data H: the T0 campaign in the nightly layout (ink squares), drawn last so they stay visible
    H_CELLS = [("2u1024", "2 users per engine, prompt 1024"), ("2u2048", "2 users, prompt 2048"), ("2u3000", "2 users, prompt 3000"),
               ("2u4096", "2 users, prompt 4096"), ("4u1024", "4 users, prompt 1024"), ("8u1024", "8 users, prompt 1024"), ("8u2048", "8 users, prompt 2048")]
    hpts = []
    for short, lab in H_CELLS:
        try:
            kv = float(R(f"h_kv_{short}")); g = float(R(f"h_gain_{short}"))
        except (ValueError, KeyError):
            continue
        hpts.append((kv, g, short, lab))
        g_txt, r_txt = R("h_gain_" + short), R("h_res_" + short)
        title_h = esc(lab + " (H): " + g_txt + " %, " + r_txt + f", {kv:.1f}K KV tokens per step")
        out.append(f'<rect x="{X(kv) - 6:.1f}" y="{Y(g) - 6:.1f}" width="12" height="12" fill="{INK}" stroke="{SURF}" stroke-width="2"><title>{title_h}</title></rect>')
    hpts.sort()
    lever = [(k, v) for k, v, short_, _lab in hpts if short_.startswith("2u")]   # the 2-users-per-engine context lever only
    if len(lever) > 1:
        pts = " ".join(f"{X(k):.1f},{Y(v):.1f}" for k, v in lever)
        out.append(f'<polyline points="{pts}" fill="none" stroke="{INK}" stroke-width="1" stroke-dasharray="3 3" stroke-opacity="0.7"/>')
    # label offsets chosen against the existing labels of data A, C, D and the 8K bracket text
    H_OFF = {"2u1024": (9, 18, "start"), "2u2048": (9, 16, "start"), "2u3000": (-9, -8, "end"), "2u4096": (10, 14, "start"),
             "4u1024": (12, 4, "start"), "8u1024": (-9, 16, "end"), "8u2048": (9, -12, "start")}
    for k, v, short, lab in hpts:
        dx, dy, anc = H_OFF.get(short, (9, -10, "start"))
        out.append(haloed_text(X(k) + dx, Y(v) + dy, f'font-size="10" fill="{INK}" text-anchor="{anc}"', esc("H " + short[:2] + " x " + short[2:] + ": " + R("h_gain_" + short) + " %")))
    out.append("</svg>")
    return "\n".join(out)


# ---------------- chart 2: expected step per config ----------------
def chart_step_per_config(rows):
    """rows: list of (label, value, tag_note, proposed: bool)"""
    title = "Expected AMX step per config when the deb preset change lands"
    sub = wrap("Gray bars = the canonical-AMX effect measured in the nightly layout (data B, whole machine, one run per arm, "
               "canonical deb against the nightly deb). The light green dashed bar = the proposed shape, measured in a 2-engine "
               "stand-in with the same users per engine (data A, one package with the kill switch off against on), not yet in the "
               "nightly layout. Colors follow chart 1: gray = data B, green = data A. n.r. = not resolved by the pre-registered rule "
               "of the data-B report.")
    W = 960
    left, right, rowh = 300, 250, 26
    top = 52 + 16 * len(sub) + 8
    n = len(rows)
    H = top + n * rowh + 78
    pw = W - left - right
    lo, hi = -5.0, 15.0

    def X(v):
        return left + (v - lo) / (hi - lo) * pw

    out = svg_header(W, H, title, sub)
    for v in (-5, 0, 5, 10, 15):
        out.append(f'<line x1="{X(v):.1f}" y1="{top - 6}" x2="{X(v):.1f}" y2="{top + n * rowh}" stroke="{GRID if v else MUTED}" stroke-width="1"/>')
        out.append(f'<text x="{X(v):.1f}" y="{top + n * rowh + 18}" font-size="11" fill="{TICK}" text-anchor="middle">{v:+d} %</text>')
    out.append(f'<text x="{X(5):.1f}" y="{top + n * rowh + 40}" font-size="12" fill="{INK2}" text-anchor="middle">TPS change with the AMX kernel against without it (percent)</text>')
    out.append(f'<text x="{X(5):.1f}" y="{top + n * rowh + 56}" font-size="11" fill="{TICK}" text-anchor="middle">gray: canonical deb against the nightly deb (data B). dashed: kill switch off against on in one package (data A)</text>')
    for i, (label, v, note, proposed) in enumerate(rows):
        cy = top + i * rowh + rowh / 2
        weight = "600" if proposed else "400"
        out.append(f'<text x="{left - 10}" y="{cy + 4:.1f}" font-size="12" font-weight="{weight}" fill="{INK if proposed else INK2}" text-anchor="end">{esc(label)}</text>')
        x0, x1 = X(0), X(v)
        bx, bw = min(x0, x1), max(2.0, abs(x1 - x0))
        if proposed:
            out.append(f'<rect x="{bx:.1f}" y="{cy - 9:.1f}" width="{bw:.1f}" height="18" fill="{C_GREEN}" fill-opacity="0.45" stroke="{INK2}" stroke-width="1" stroke-dasharray="4 3" rx="2"><title>{esc(note)}</title></rect>')
        else:
            out.append(f'<rect x="{bx:.1f}" y="{cy - 9:.1f}" width="{bw:.1f}" height="18" fill="{C_GRAY}" rx="2"><title>{esc(note)}</title></rect>')
        # every value label sits right of the bar's right end (right of the zero line for a negative bar), so the label
        # column never runs into the config names
        out.append(haloed_text(max(x0, x1) + 8, cy + 4, f'font-size="12" font-weight="{weight}" fill="{INK}" text-anchor="start"', esc(note)))
    out.append("</svg>")
    return "\n".join(out)


# ---------------- the page ----------------
def build_page():
    now = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())

    sv = [
        f"The AMX kernel (AMX = Intel Advanced Matrix Extensions) speeds up attention only, and today's llama-3.1-8b config (2 users per engine, prompt 1024) shows {R('a_gain2')} % to {R('b_canon_gain')} % (data A and B).",
        f"We recommend one new nightly perf config, llama-3.1-8b good tp2 (tp2 = two FPGA cards per engine) at {R('new_users')} users = {R('new_upe')} users per engine: measured {R('a_gain8')} % ({R('a_off8')} to {R('a_on8')} TPS, kernel on against kernel off in one binary, data A), and the harness can run it today.",
        f"Test T0 ran on {R('h_date')} (data H): with the CI harness in the nightly layout, the nightly deb against the same source with the AMX kernel compiled in, {R('h_passes')} interleaved passes, the kernel gains {R('h_gain_2u1024')} % at today's shape ({R('h_res_2u1024')}), {R('h_gain_8u1024')} % at the recommended 8-users-per-engine shape ({R('h_res_8u1024')}), and {R('h_gain_2u4096')} % at 2 users per engine and prompt 4096 ({R('h_res_2u4096')}). Prompts above {R('h_trunc')} tokens cannot be measured or served on this deployment: the deployed llama-8b tokenizer file truncates them (section 4).",
        f"A follow-up cell ran on {R('i_date')} (data I): llama-3.1-8b at {R('new_upe')} users per engine ({R('new_users')} users in total) and prompt {R('prompt4096')}, {R('i_kv')}K KV tokens per engine step (counted without the {R('h_ovh')}-token server overhead of data H because the tokenizer keeps exactly {R('prompt4096')} prompt tokens), the nightly deb against the canonical-AMX deb with the same driver and layout as T0, {R('i_passes')} interleaved passes. The kernel gains {R('i_gain')} % ({R('i_base')} to {R('i_canon')} TPS, paired t {R('i_t')}, {R('i_res')}). Against the pre-registered band (the gain range the plan fixed before the run) of {R('i_band_lo')} to {R('i_band_hi')} %: {R('i_inside')}. For comparison, the T0 cells of {R('h_date')} (data H) at {R('new_upe')} users per engine gave {R('h_gain_8u1024')} % at prompt {R('prompt')} and {R('h_gain_8u2048')} % at prompt {R('prompt2048')}. The difference against that prompt-{R('prompt2048')} cell is {R('i_diff2048')} percentage points. Candidate goal values from the nightly deb: {R('i_goal_tps')} TPS mean, {R('i_goal_min')} TPS slowest sample, {R('i_goal_p05')} TPS p05. Reading (the analyze.py verdict text): &quot;{R('i_reading')}&quot;. Report: <code>{R('i_report')}</code>.",
    ]
    take = [
        f"Why today's configs cannot show it: the kernel speeds up attention only, and at {R('night_upe')} users per engine the measured gain is {R('a_gain2')} % to {R('b_canon_gain')} % (data A, B). Hypothesis: at that load most of llama's attention time is hidden behind the FPGA work of the other minibatch, so the kernel has little exposed time to shorten (section 1.1); the attention share of a llama step is not measured.",
        f"Two ways raise the attention work of a step (this page calls them the two levers): more users per engine, or a longer prompt per user (section 1). They were never compared on llama-8b with one tool and one binary pair. The two llama-8b long-prompt cells that exist (data G: ingested plugin, mirror build, kill switch) gave {R('g_gain1')} % at 1 user and prompt 8192 and {R('g_gain8')} % at 8 users and prompt 2048.",
        f"Which models can react at all: llama-3.1-8b (yes), mixtral-8x7b (eligible by shape, measured parity, kernel engagement not measured), qwen-3-4b (only with CPU attention, which production does not use). The other {R('configs_other')} configs ({R('models_other')} models) have no kernel path (section 2).",
        f"Cost of the new config: about {R('cost_min')} min per night (est.), and the perf phase would go from {R('b_perf_min')} min to about {R('perf_new')} min (est.). The existing {R('night_users')}-user config stays (section 3).",
        f"Not recommended today: mixtral at 32 users, qwen-3-4b with CPU attention, one engine with 8 users, 16 users (section 4, each with its data). Longer prompts are deferred to T0, not rejected. No measurement of the nightly's llama-8b plugin exists above prompt 1024. The harness needs a small prompt-code change to reach prompt 2048 or more for every user (section 4, data P).",
        f"Correction to v1: v1 said longer prompts give no larger gain than more users. It inferred that from the flat qwen-3-4b 8-user prompt series ({R('f_p2048')} % at prompt 2048, {R('f_p8192')} % at 8192, data F). At 8 users attention is most of the decode step (est., section 1.1), so that series says nothing about the nightly's load. The inference is withdrawn.",
        f"Test plan: T0 is one whole-machine campaign with the CI harness in the nightly layout. T1 (the 32-user prompt-1024 cells) and T2 (the 2-users-per-engine long-prompt cells) are subsets of it. After T0: if the two levers agree within {R('t0_band')} points at equal KV tokens per step, a long-prompt shape is a peer recommendation. If the long prompt is ahead by more than {R('t0_band')} points, the long-prompt shape becomes the primary recommendation. If more users are ahead by more than {R('t0_band')} points, this page stands. T3 is optional. T4 is the watch period after the deb preset change lands (section 5).",
        "Decisions: this page is a recommendation. jhan decides whether to file the 32-user config and whether a long-prompt shape is added, both after T0. The CI team decides the goals and the name.",
        f"v3 status ({R('h_date')}, data H): T0 ran with {R('h_configs')} configs per pass instead of 10. The prompt-7168 and prompt-8192 cells were dropped before the first pass because the server keeps only the first {R('h_trunc')} prompt tokens of a llama-8b request (a truncation block in the deployed tokenizer.json, upstream Neural Magic revision of 2024-08-13, fixed upstream on 2024-09-30, never refreshed in the weights store). The 16K pair is therefore lost. {R('h_n_complete')} of {R('h_configs')} configs have all {R('h_passes')} passes on both arms and {R('h_n_resolved')} are resolved. The 8K triple verdict: {R('h_triple')}. T1 reference values are in section 3.2, the T2 cells in section 4.",
    ]

    # ---- section 2 table rows: (config, attention, head, kv_mul, eligible, effect text, note) ----
    cfg_rows = [
        ("llama-3.2-3b fast tp2 @32u", "CPU", R("head128"), R("kvmul3"), "no (kv_mul 3)", f"{R('b_llama3b')} % n.r.", "Control. No kernel path. The only 32-user config today (section 3)."),
        ("llama-3.1-8b good tp2 @8u", "CPU", R("head128"), R("kvmul4"), "yes", f"{R('b_llama8b')} % resolved", f"The only resolved change in the canonical arm. AMX-busy {R('b_busy')} billion cycles in the 20 s probe."),
        ("llama-3.3-70b good tp2 @8u", "CPU", R("head128"), R("kvmul8"), "no (kv_mul 8)", f"{R('b_70b_tp2_8u')} % n.r.", "Control."),
        ("llama-3.3-70b good tp2 @4u", "CPU", R("head128"), R("kvmul8"), "no (kv_mul 8)", f"{R('b_70b_tp2_4u')} % n.r.", "Control. Same engines as the @8u row (no re-provisioning)."),
        ("llama-3.3-70b good tp4 @4u", "CPU", R("head128"), R("kvmul8"), "no (kv_mul 8)", f"{R('b_70b_tp4')} % n.r.", "Control."),
        ("mixtral-8x7b tp2 @8u", "CPU", R("head128"), R("kvmul4"), "yes by shape", f"{R('b_mixtral')} % n.r.", f"Measured parity even at 8 users on one engine: {R('d_mix_off')} to {R('d_mix_on')} TPS ({R('d_mix_gain')} %, sd {R('d_mix_sd')} TPS, data D). No AMX-busy probe ran on mixtral in data B or data D, so whether the kernel engaged is not measured. Two hypotheses: (a) the kernel ran and the expert layers (MoE) dominate the step, (b) the kernel did not engage. One 20 s AMX-busy probe on a mixtral cell (kill switch off against on) separates them."),
        ("qwen-2.5-32b fast tp2 @8u", "CPU", R("head128"), R("kvmul5"), "no (kv_mul 5)", f"{R('b_qwen25')} % n.r.", "Control."),
        ("qwen-3-4b tp2 @8u", "FPGA", R("head128"), R("kvmul4"), "by shape only", f"{R('b_qwen34_tp2')} % n.r.", "FPGA attention in production. The kernel acts only in the CPU share of attention."),
        ("qwen-3-4b tp4 @8u", "FPGA", R("head128"), R("kvmul4"), "by shape only", f"{R('b_qwen34_tp4')} % n.r.", "As tp2. Night-to-night noisy."),
        ("gemma-2-9b fast tp2 @8u", "CPU", R("head256"), f"{R('kvmul2')} ({R('heads_gemma2')} / {R('kvheads8')})", "no (head 256)", f"{R('b_gemma2')} % n.r.", "Control. Head size alone rules the kernel out."),
        ("gpt-oss-120b tp4 @8u", "FPGA", R("head64"), f"{R('kvmul8_gptoss')} ({R('heads_gptoss')} / {R('kvheads8')})", "no (head 64)", f"{R('b_gptoss')} % n.r.", "Control. Noisy night to night."),
        ("gemma-4-31b tp2 @8u", "CPU", R("head256"), "n/a (head size decides)", "no (head 256)", f"{R('b_gemma4')} % n.r.", "Control. Ingested, but head 256 has no FPGA attention path."),
    ]
    FLAG = ' class="flag"'
    cfg_table = "".join(
        f"<tr{FLAG if el == 'yes' else ''}><td>{esc(c)}</td><td>{esc(att)}</td><td>{esc(h)}</td><td>{esc(k)}</td><td>{esc(el)}</td><td>{esc(eff)}</td><td>{esc(note)}</td></tr>"
        for c, att, h, k, el, eff, note in cfg_rows)

    # ---- chart 2 rows ----
    bars = [
        ("llama-3.2-3b fast tp2 @32u", 1.5, f"{R('b_llama3b')} % n.r.", False),
        ("llama-3.1-8b good tp2 @8u", 1.2, f"{R('b_llama8b')} % resolved", False),
        ("llama-3.3-70b good tp2 @8u", 0.1, f"{R('b_70b_tp2_8u')} % n.r.", False),
        ("llama-3.3-70b good tp2 @4u", -0.0, f"{R('b_70b_tp2_4u')} % n.r.", False),
        ("llama-3.3-70b good tp4 @4u", 1.8, f"{R('b_70b_tp4')} % n.r.", False),
        ("mixtral-8x7b tp2 @8u", -0.6, f"{R('b_mixtral')} % n.r.", False),
        ("qwen-2.5-32b fast tp2 @8u", 0.1, f"{R('b_qwen25')} % n.r.", False),
        ("qwen-3-4b tp2 @8u", 0.1, f"{R('b_qwen34_tp2')} % n.r.", False),
        ("qwen-3-4b tp4 @8u", -2.6, f"{R('b_qwen34_tp4')} % n.r.", False),
        ("gemma-2-9b fast tp2 @8u", -0.2, f"{R('b_gemma2')} % n.r.", False),
        ("gpt-oss-120b tp4 @8u", -3.9, f"{R('b_gptoss')} % n.r.", False),
        ("gemma-4-31b tp2 @8u", -0.3, f"{R('b_gemma4')} % n.r.", False),
        ("PROPOSED llama-3.1-8b good tp2 @32u", 12.9, f"{R('a_gain8')} % (data A, 2-engine stand-in)", True),
    ]

    perf_entry = f'''    {{
        "name": "llama_3_1_8b_instruct_good_tp2_32u",
        "sample_name": "llama_3_1_8b_instruct_good_tp2_32u",
        "model": "llama-3.1-8b-instruct-good-tp2",
        "nominal_users": {R("new_users")},
        "user_sets": [],
        "shared_prompt_length": 0,
        "prompt_length": {R("prompt")},
        "generate_length": {R("gen")},
        "start_capture": {R("cap_start")},
        "end_capture": {R("cap_end")},
        "prompt_mode": "sharegpt",
    }},'''
    goal_entry = f'''    elif platform_type in ['granite_rapids_72_rinzler']:
        goal.tps = {{
            ...
            ('llama-3.1-8b-instruct-good-tp2', {R("new_users")}) : <mean-TPS goal, set from nights on this shape>,
        }}
        goal.min_tps = {{
            ...
            ('llama-3.1-8b-instruct-good-tp2', {R("new_users")}) : <slowest-user goal, set from nights on this shape>,
        }}'''
    yaml_entry = f'''  - platform_type: granite_rapids_72_rinzler
    model: llama-3.1-8b-instruct-good-tp2
    users: {R("new_users")}
    average_tps:
      threshold: <from nights on this shape>
      update_policy: q30
    p05_tps:
      threshold: <from nights on this shape>
      update_policy: q30'''

    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>CI test shapes for the AMX effect</title>
<style>
:root{{color-scheme:light;--ink:{INK};--ink2:{INK2};--muted:{MUTED};--grid:{GRID};--surf:{SURF};--page:#f9f9f7;--green:{C_GREEN};--gray:{C_GRAY};--blue:{C_BLUE}}}
html,body{{background:var(--page);color:var(--ink);font-family:system-ui,-apple-system,"Segoe UI",sans-serif;margin:0}}
main{{max-width:1080px;margin:0 auto;padding:24px 16px 64px}}
h1{{font-size:24px;margin:0 0 4px}} h2{{font-size:18px;margin:36px 0 8px;border-bottom:1px solid var(--grid);padding-bottom:4px}} h3{{font-size:15px;margin:20px 0 6px}}
p,li{{line-height:1.45;font-size:14px}} .sub{{color:var(--ink2);font-size:13px}}
.short{{background:var(--surf);border:1px solid var(--grid);border-radius:8px;padding:12px 16px;margin:16px 0}}
.short p{{margin:6px 0}}
table{{border-collapse:collapse;font-size:12.5px;margin:8px 0 16px;background:var(--surf)}} th,td{{border:1px solid var(--grid);padding:4px 8px;text-align:left;vertical-align:top}} th{{color:var(--ink2);font-weight:600}}
td:nth-child(n+2){{font-variant-numeric:tabular-nums}} tr.flag td{{background:#eefaf4}}
.fig{{background:var(--surf);border:1px solid var(--grid);border-radius:8px;padding:8px;margin:12px 0}} .fig svg{{width:100%;height:auto;display:block;margin:0 auto}}
.tw{{overflow-x:auto;margin:8px 0 16px}} .tw table{{margin:0}}
.legend{{font-size:12px;color:var(--ink2);margin:4px 0 8px}} .legend span{{margin-right:16px}} .legend i{{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:5px;vertical-align:middle}}
.take{{font-size:13px;color:var(--ink2);margin:4px 0 0 8px}}
.cap{{font-size:13px;color:var(--ink2);margin:4px 0 12px 8px}}
code{{font-size:12px;background:#f1f0ec;padding:1px 4px;border-radius:3px}}
pre{{font-size:12px;background:#f1f0ec;padding:10px 12px;border-radius:6px;overflow-x:auto;line-height:1.4}}
.gloss dt{{font-weight:600;font-size:13px;margin-top:6px}} .gloss dd{{margin:0 0 0 16px;font-size:13px;color:var(--ink2)}}
.fn{{font-size:12.5px;color:var(--ink2)}} .fn li{{font-size:12.5px}}
</style></head><body><main>
<h1>CI test shapes that show the AMX effect: recommendation and test plan</h1>
<p class="sub">For the CI team (systems_test owners). Date 2026-09-19. Author: jhan's AMX work. Generated {now} by exec/canon-ci-20260918/gen_ci_shapes.py (v3: data H, the T0 results, added on 2026-09-19 evening; v4: data I, the {R("new_upe")}-users-per-engine prompt-{R("prompt4096")} cell, added {R("i_date")}). Every number is a measurement with a source tag (A to I and P, defined in section 6) unless it is marked est. or its arithmetic is in the footnotes. <b>Revision v2.2 (2026-09-19)</b> after a review of v1. Changes: section 1.1 added (do more users and longer prompts act as one factor or two). Data F detail and data G added. The section 4 row on longer prompts rewritten. Test T0 added, first as a runtron design on our half of the machine, then redesigned as a whole-machine CI-harness campaign in the nightly layout that contains T1 and T2. The v1 claim about the harness field shared_prompt_length corrected. v1 is kept as CI-AMX-test-shapes.v1-20260919.html.</p>

<div class="short"><h2 style="margin-top:0;border:0">Short version</h2>
{"".join(f"<p>{s}</p>" for s in sv)}
</div>
<ul class="take">{"".join(f"<li>{x}</li>" for x in take)}</ul>

<h2>Words used here</h2>
<dl class="gloss">
<dt>nightly, System CI, systems_test, perf phase</dt><dd>System CI is the automated nightly test job of the systems_test repository. The nightly is its run on delphi-3bda (the 72-core Intel Granite Rapids test machine) every night at {R("nightly_start")} UTC. The perf phase is the part of the nightly that measures decode speed on {R("configs12")} configs. It takes {R("b_perf_min")} min today (data B).</dd>
<dt>config, shape</dt><dd>A config is one row of the list in scripts/perf.py: a model, its tensor-parallel width (tp) and a user count, for example llama-3.1-8b good tp2 @8u (8 users). This page uses "shape" for the same thing when it talks about a config that does not exist yet. "Eligible by shape" (section 2) uses the word in a second sense: the model's architecture, head size and kv_mul.</dd>
<dt>canonical build, mirror build, arena, denominator, lever</dt><dd>canonical = the AMX kernel variant merged in PR #3879 and recommended here. mirror = an earlier, faster variant that keeps a second, AMX-friendly copy of the attention keys (the arena) in host RAM; it is not merged. denominator = the slower arm a gain is measured against: a clean binary (no AMX code) or the same binary with the kill switch. lever = one of the two ways to raise the attention work of a decode step: more users per engine, or a longer prompt per user.</dd>
<dt>tron, rinzler, engine, tp2, tp4, Caddy</dt><dd>tron is the inference program under test. rinzler is its production server. One running rinzler is one engine. tp2 and tp4 are the tensor-parallel widths: the number of FPGA cards one engine uses. The machine has {R("cards")} cards. The nightly therefore creates {R("cards")} // tp engines: {R("eng_tp2")} for tp2 and {R("eng_tp4")} for tp4 (testlib/inference_provisioner.py line {R("line_engines")}). Caddy is the port-80 proxy in front of the engines. platformd (the production process manager) creates it (put_test_proxy, testlib/inference_provisioner.py line {R("line_proxy")}). Its spreading policy is not visible in tron or systems_test. The evidence for an even spread is indirect: in the nightly-vs-ours campaign of 2026-09-11/13 the per-user "Done" lines of the harness showed two speed levels with even counts per round, which fits {R("night_users")} users on {R("eng_tp2")} engines = {R("night_upe")} users per engine. T1 measures the spread for the proposed shape directly (section 5).</dd>
<dt>good, fast</dt><dd>Names of tron's model-build variants: the same model built in different ways. They appear in perf.py's config names and in testlib/hf_models.py (llama-3.1-8b-instruct-good, -fast, -best). This page uses the "good" build of llama-3.1-8b, the one the nightly runs.</dd>
<dt>AMX, the AMX kernel, PR #3879, head size, kv_mul, KV head</dt><dd>AMX = Intel Advanced Matrix Extensions, the matrix instructions of Granite Rapids CPUs. PR #3879 (merged 2026-09-15) added an attention kernel that uses them. The kernel runs only for models with a head size of {R("head128")} elements and {R("kvmul4")} query heads per KV head (kv_mul {R("kvmul4")}), and only when attention runs on the CPU. A KV head is one key/value head of attention that several query heads share. Head size and kv_mul are properties of a model's architecture. The dispatch gate has a third condition: the executor's activation scalar (the number type of the query buffer) must be bf16 (eligible = shape_ok and query_scalar_ok, h/tron/kernels/amx_attn_iface.hpp lines {R("line_gate_lo")} to {R("line_gate_hi")}, and amx_on = eligible and available(), h/tron/models/self_attention.hpp lines {R("line_amxon_lo")} to {R("line_amxon_hi")}, at tron commit {R("tron_head")}). The tp2 and tp4 executors store bf16, so every nightly config meets it.</dd>
<dt>deb, deb preset, TRON_AMX_DISPATCH</dt><dd>The deb is the tron package the nightly installs each night. The deb preset is the CMake build recipe that builds it. The kernel is compiled only when the CMake option TRON_AMX_DISPATCH is ON. The nightly deb does not set it. The nightly's tron therefore has no AMX code today. "The deb preset change" is the one-line change that turns the option on (branch jhan-amx-deb-preset, not yet a PR). The two packages named on this page are the nightly deb {R("b_deb_base")} and our canonical-AMX deb {R("b_deb_canon")}.</dd>
<dt>kill switch, AMX-busy, probe</dt><dd>The kill switch is the environment variable TRON_AMX_DISABLE=1. It makes a tron with AMX code take the old path. "AMX on vs off" on this page means the same binary with the kill switch off and on. AMX-busy is the CPU counter EXE.AMX_BUSY, the number of cycles in which the AMX unit worked. A probe is a {R("a_probe")} s read of that counter over all engine processes while requests run. {R("a_busy_off")} cycles in a kill-switch cell proves that the old path ran.</dd>
<dt>VNNI-K, PR #4424</dt><dd>PR #4424 changes the layout of the K cache (the stored keys of earlier tokens) to the VNNI format. It is not merged and is not part of this recommendation. Three data points of this page were measured with PR #4424 binaries: data A (both arms, one package {R("a_binary")} with the kill switch on and off), data B's {R("b_target_gain")} % arm, and data C. In data A both arms carry the VNNI K layout, so its gain is the AMX kernel alone on that layout. T1 measures the exact nightly deb and the canonical deb.</dd>
<dt>TPS, TTFT, slowest user, p05, sd</dt><dd>TPS = decode tokens per second per user. The harness measures it inside a per-config window of generated tokens (start_capture to end_capture) and averages over users and rounds. The window is token {R("cap_start")} to {R("cap_end")} for {R("configs11")} of the {R("configs12")} configs, the llama-8b config and the proposed shape among them. llama-3b captures tokens {R("cap3b_start")} to {R("cap3b_end")} of its {R("gen3b")} generated tokens (scripts/perf.py lines {R("line_3b_lo")} to {R("line_3b_hi")}). Its dict lists shared_prompt_length {R("shared3b")} and prompt_length {R("prompt3b")}. The harness applies only prompt_length (see "shared_prompt_length" below). Its recorded prompt is {R("prompt3b_rec")} tokens (data B): the {R("prompt3b")} pruned tokens plus about 28 tokens the server counts around them (the llama-8b config records {R("rec_prompt_b")} tokens for prompt_length {R("prompt")} the same way). TTFT = time to first token, in ms. Slowest user = the lowest TPS sample of a config. p05 = the linearly interpolated 5th percentile of the TPS samples (testlib/perf_metrics.py), the quantity the ratchet thresholds use. sd = standard deviation.</dd>
<dt>static goals, get_goal, granite_rapids_72_rinzler</dt><dd>The static goals are the mean-TPS and slowest-user limits the Slack report applies. They live in scripts/system_ci.py, function get_goal, in two dicts (goal.tps and goal.min_tps) keyed by (model, users) per platform. granite_rapids_72_rinzler is the platform name of delphi-3bda.</dd>
<dt>ratchet thresholds</dt><dd>A second set of limits in thresholds/system_ci_perf.yaml, keyed by platform_type, model and users. Its policy uses the last {R("hist_runs")} runs (history_runs {R("hist_runs")}) and the {R("q30")} quantile (update_policy q30). The limits only move up: a new value is proposed only when the q30 support exceeds {R("ratio")} times the accepted value (min_improvement_ratio, testlib/system_ci_thresholds.py lines {R("line_ratchet_lo")} to {R("line_ratchet_hi")}). The YAML report is posted to a separate Slack channel (rhys-test) and is not the enforced verdict today. The static-goal report goes to ci-cd-notifications and is the one that fails the run (scripts/system_ci.py post_reports, add_current_threshold_compatibility, enforce_report).</dd>
<dt>FPGA attention, CPU attention, ingested, hand-written, USE_HW_ATTN, CPU share</dt><dd>Ingested models (converted by tron's ingest compiler, for example qwen-3-4b and gpt-oss) run attention on the FPGA cards by default. Hand-written models (coded by hand in tron, for example llama and mixtral) run attention on the CPU. The AMX kernel acts only in CPU attention. USE_HW_ATTN=0 is the environment variable that forces CPU attention on an ingested model. The CPU share is the part of attention the CPU still computes under FPGA attention (the first positions of each query and the newest tokens not yet copied to the card).</dd>
<dt>MoE</dt><dd>Mixture of experts: a model whose feed-forward layers are split into experts, of which each token uses a few. mixtral-8x7b is one. gpt-oss is another.</dd>
<dt>paired t, resolved, n.r.</dt><dd>Paired t = the mean of the per-round (or per-repetition) differences between two arms divided by its standard error. The prompts are fixed. Round r of one arm therefore pairs with round r of the other. A change is "resolved" when the data-B report's pre-registered rule holds: |t| at or above the 95 % limit, |change| at or above 1 %, and |change| at or above the config's 13-night band. Data A uses its own rule: {R("a_reps")} repetitions, |t| at or above {R("a_t975")} and |change| at or above 1 %. n.r. = not resolved.</dd>
<dt>13-night band</dt><dd>The night-to-night spread of a config in the nightly's own Slack reports: 2 sd of the {R("nights13")} nights 2026-09-05 to 09-17, in percent of their mean. A change smaller than the band cannot be told from a normal night.</dd>
<dt>runtron, CI harness, stand-in</dt><dd>runtron is tron's command-line benchmark tool (one process, no proxy). The CI harness is the nightly's own client code (scripts/perf.py and testlib/tps.py). A stand-in is a measurement made with rinzler and the CI harness on a part of the machine, placed like the nightly's engines, instead of the whole machine.</dd>
<dt>delphi-3bda, our half, Bill, CI lease</dt><dd>delphi-3bda is the test machine. Its first half (socket 0, 4 cards) is reserved for Bill when the marker file /bill-has-instance-0,2 exists. Our half is socket 1. The CI lease is the file /run/lock/systems-test-ci.lease the nightly holds while it runs. A whole-machine test needs Bill idle and the lease free.</dd>
<dt>KV tokens per engine step, context per user</dt><dd>The attention work of one decode step on one engine: the number of users the engine serves times the context (prompt plus generated tokens so far) of each user. Every KV token costs one read of its stored key and value in every layer: 4 KiB per layer, {R("kv_llama_tok")} KiB per token summed over llama-3.1-8b's 32 layers and {R("kv_qwen_tok")} KiB over qwen-3-4b's 36 layers. This page writes the count in thousands (K). For a CI-harness cell the context per user is the recorded prompt plus the middle of the TPS window (960 for the {R("cap_start")} to {R("cap_end")} window). The recorded prompt exceeds prompt_length {R("prompt")} by the tokens the server counts around it: {R("rec_prompt_a")} tokens in data A and {R("rec_prompt_b")} in data B, so the contexts are {R("ctx_win")} and 2015 (the nominal prompt would give {R("ctx_nominal")}). For a runtron cell the context per user is the prompt plus half the generated tokens. runtron averages TPS over the whole decode, so the middle of the decode is the representative context.</dd>
<dt>minibatch, matmul</dt><dd>tron cuts the users of one decode step into minibatches and pipelines them: while the FPGA cards run the matmuls (matrix multiplications of the model weights) of one minibatch, the CPU runs the attention of another. The rule is in h/tron/models/model.hpp lines {R("line_chunk_lo")} to {R("line_chunk_hi")} (chunk_evenly): a step with 2 or more groups is split into two minibatches "to enable FPGA-vs-CPU latency hiding" when the plugin allows it. Each user's decode token forms its own group (h/tron/scheduler/full.hpp lines {R("line_group_lo")} to {R("line_group_hi")}), so the split applies from 2 users up. The runtime limit defaults to -1, no limit (h/tron/models/config.hpp line {R("line_cfg_mb")}), and is merged with the plugin's bound by taking the smaller (lines {R("line_cfg_merge_lo")} to {R("line_cfg_merge_hi")}). The hand-written llama plugin sets no bound (h/tron/plugins/llama.hpp line {R("line_llama_mb")}, max_minibatches = -1). Every ingested plugin, qwen-3-4b among them, sets the bound 1 (ingest/src/TronCpp.hs line {R("line_ingest_mb")}), so it never splits. Section 1.1 uses this fact.</dd>
<dt>shared_prompt_length</dt><dd>A field of every perf.py config dict. The nightly's prompt code does not apply it. testlib/tps.py passes only prompt_length to PromptGenerator.generate (lines {R("line_tps_gen_lo")} to {R("line_tps_gen_hi")}). The field is read at line {R("line_tps_field")} (set from scripts/perf.py line {R("line_perf_shared")}) and printed in the config log line as shared_prefix= (perf.py line {R("line_perf_log")}). Inside the harness it is used only in a bookkeeping line ({R("line_tps_seq")}) that runs when continuous_usage is 0, and continuous_usage defaults to 1 (line {R("line_tps_cu")}). The recorded prompt of llama-3b @32u is {R("prompt3b_rec")} tokens (data B), not 800 plus 200. A shared-prefix generator exists only in scripts/tps_node.py. The nightly does not run it: scripts/perf.py line {R("line_perf_ctrl")} comments out the import of tps_controller, the module that launches tps_node (scripts/tps_controller.py line {R("line_ctrl_launch")}), and line {R("line_perf_import")} imports testlib.tps instead. v1 of this page called this a "shared-prefix path". That was wrong.</dd>
<dt>arm, pass, posadm, instance env file, hugepages, preflight, ensure-base, ensure-canon, tile instruction, manifest</dt><dd>Words of the T0 campaign (section 5). arm = one package or setting under comparison. pass = one run through the T0 configs with one package installed. posadm = the Positron admin command-line tool the harness uses to change engine settings; on this machine it calls platformd's settings API. instance env file = /etc/rinzler/instance-N.env, the environment variables a rinzler unit reads at start (written by platformd); /opt/positron/user/config.env is a second, normally empty file read after it. hugepages = the 1 GiB memory pages reserved for an engine ({R("hp_engine")} per engine). preflight = the read-only check list dut.sh prints once before a campaign. ensure-base and ensure-canon = the dut.sh steps that install the nightly deb or the canonical deb and verify the installed version and the sha256 of the rinzler binary. tile instruction = an AMX machine instruction (tileloadd, tdpbf16ps and the like); their count in a binary shows the kernel was compiled in. manifest = manifest.json written by the canonical deb's build script, with the source commits and the instruction count. ci-mimic driver = the 2026-09-18 campaign that ran the nightly deb against the PR #4424 deb with the same scripts.</dd>
<dt>ShareGPT, prune_convo</dt><dd>ShareGPT is the public set of chat conversations the harness always uses as prompts (PromptGenerator loads sharegpt_1000.json, testlib/prompt.py line {R("line_sharegpt_load")}; the dict field prompt_mode is not read, scripts/perf.py line {R("line_perf_mode")}). prune_convo (testlib/prompt.py line {R("line_prune")}) cuts a conversation to prompt_length tokens and raises "Prompt length ... too short" when the conversation has fewer tokens (line {R("line_prune_raise")}).</dd>
</dl>

<h2>1. Why today's configs cannot show AMX</h2>
<h3>Mechanism</h3>
<ul>
<li>The kernel speeds up attention only. For llama the matmuls of a decode step (WQ, WK, WV, WO = the weight matrices that produce attention's query, key, value and output, plus the feed-forward weights) run on the FPGA cards (h/tron/plugins/llama.hpp line {R("line_wo")} region, fill_matmul_template and prepare_matmul). Attention runs on the CPU.</li>
<li>Attention work per decode step grows with the number of users per engine times the context per user (KV tokens per engine step, glossary). More users per engine and longer prompts both raise it. Whether they raise the AMX gain equally is the question of section 1.1.</li>
<li>For llama-3.1-8b and the {R("configs_tp2_8u_other")} other tp2 configs at {R("night_users")} users [footnote 11], the nightly spreads {R("night_users")} users over {R("eng_tp2")} tp2 engines. That is {R("night_upe")} users per engine, with prompt {R("prompt")} and {R("gen")} generated tokens. At that load attention is a small part of the step. The kernel then has little to speed up.</li>
</ul>
<h3>Data</h3>
<ul>
<li><b>Data A (l8bload, 2026-09-18).</b> rinzler plus the nightly's own client code, {R("a_engines")} engines placed like the nightly's socket-1 engines, {R("a_reps")} repetitions per level, llama-3.1-8b good tp2, prompt {R("prompt")}, {R("gen")} generated tokens. Binary: the PR #4424 package {R("a_binary")} (AMX kernel plus VNNI K layout compiled in), kill switch TRON_AMX_DISABLE=1 against unset. Both arms carry the VNNI K layout, so the gain is the AMX kernel alone on that layout. Neither arm is today's deb or the canonical deb. Two differences from the nightly: no Caddy hop (one 8-user client per engine, connected to the engine's own port), and one client process per engine instead of one for all users. Both clients used the {R("seeds80")} ShareGPT conversations of today's 8-user config [footnote 12]. At 2 users per engine one on-arm cell was excluded for an unexplained slowdown and replaced by a fourth repetition (data-A report, note A). T1 removes both layout differences. Users per engine {R("a_users")}:
  <div class="tw"><table><tr><th>users per engine</th><th>TPS, kernel off (kill switch)</th><th>TPS, kernel on</th><th>gain</th><th>paired t</th><th>TTFT off / on</th><th>AMX-busy off / on</th></tr>
  <tr><td>2 (today's nightly)</td><td>{R("a_off2")}</td><td>{R("a_on2")}</td><td>{R("a_gain2")} %</td><td>{R("a_t2")} (n.r. by the data-A rule)</td><td>{R("a_ttft_off2")} / {R("a_ttft_on2")} ms</td><td>{R("a_busy_off")} / {R("a_busy2")} billion cycles</td></tr>
  <tr><td>4</td><td>{R("a_off4")}</td><td>{R("a_on4")}</td><td>{R("a_gain4")} %</td><td>{R("a_t4")}</td><td>{R("a_ttft_off4")} / {R("a_ttft_on4")} ms</td><td>{R("a_busy_off")} / {R("a_busy4")} billion cycles</td></tr>
  <tr class="flag"><td>8 (proposed)</td><td>{R("a_off8")}</td><td>{R("a_on8")}</td><td>{R("a_gain8")} %</td><td>{R("a_t8")}</td><td>{R("a_ttft_off8")} / {R("a_ttft_on8")} ms</td><td>{R("a_busy_off")} / {R("a_busy8")} billion cycles</td></tr></table></div>
  The per-cell sd at 8 users per engine is {R("a_sd_lo")} to {R("a_sd_hi")} TPS. The slowest sample at 8 users per engine is {R("a_slow_off8")} TPS with the kernel off and {R("a_slow_on8")} TPS with it on. The 2-user value with the kernel off ({R("a_off2")} TPS) matches the {R("nights13")}-night nightly mean of {R("night13_mean")} TPS within {R("night13_gap")} % [footnote 1]. So the stand-in reproduces the nightly's own number at the nightly's load.</li>
<li><b>Data B (nightly layout, whole machine, 2026-09-18/19).</b> The exact nightly layout ({R("eng_tp2")} tp2 engines behind Caddy, {R("b_rounds")} rounds). On llama-8b @8u the PR #4424 + AMX arm gave {R("b_target_gain")} % (paired t {R("b_target_t")} as report-v4 prints it, {R("b_target_t_raw")} unrounded in the data-A summary) and the canonical-AMX arm gave {R("b_canon_gain")} % (paired t {R("b_canon_t")}) against the nightly deb. In the canonical arm no other config changed by a resolved amount. AMX-busy on llama-8b was {R("b_busy")} billion cycles. The kernel therefore did run. It ran on too little attention work to matter.</li>
<li><b>Data C (wedperf, 2026-09-16).</b> runtron, 8 users on one engine, llama-8b. Base = main before PR #3879 (no AMX code). Target = the PR #4424 head (AMX kernel plus VNNI K layout). Target against base: {R("c_gain256")} % at {R("c_tok256")} generated tokens ({R("c_reps256")} repetitions) and {R("c_gain1536")} % at {R("gen")} ({R("c_reps1536")} repetitions, {R("c_off1536")} to {R("c_on1536")} TPS). At {R("c_tok256")} tokens main's own change (the kernel plus PR #4400) gave {R("c_attr_main")} % and PR #4424 alone {R("c_attr_4424")} % (not resolved). So the {R("gen")}-token gain is mostly the kernel (hypothesis: no {R("gen")}-token attribution run exists). Data C is the one llama-8b measurement in which only the context changed and the comparison arm is a clean binary (no AMX code). The mean context per user is {R("ctx_c256")} tokens over 256 generated tokens ({R("kv_c256")}K KV tokens per engine step) and {R("ctx_c1536")} over 1536 ({R("kv_c1536")}K). The gain rises from {R("c_gain256")} % to {R("c_gain1536")} %. VNNI-K is part of the target arm.</li>
<li><b>Data D (more-testing round 1, 2026-09-05).</b> rinzler plus the CI harness, 8 users on one engine, prompt {R("prompt")}, {R("gen")} tokens: llama-8b good {R("d_llama8b")} % (canonical kernel). mixtral-8x7b tp2 {R("d_mix_off")} to {R("d_mix_on")} TPS ({R("d_mix_gain")} %, sd {R("d_mix_sd")} TPS): parity. No AMX-busy probe existed yet (validated 2026-09-17), so kernel engagement is not measured in data D. qwen-3-4b tp4 with CPU attention (USE_HW_ATTN=0) {R("d_qwen")} %. An A/A repeat of that off arm differed by {R("d_qwen_aa")} % run to run, so changes under {R("d_floor")} % are not resolved by one run per arm.</li>
<li><b>Data F (runtron prompt-length series, qwen-3-4b).</b> The ingested qwen-3-4b tp2 model with CPU attention forced (USE_HW_ATTN=0), one runtron process, 256 generated tokens. Two parts. (1) The {R("f_grid_date")} grid: 1 and 8 users at prompt 2048 and 8192, canonical kernel and mirror build against a clean no-AMX binary. Canonical: {R("fc1_p2048")} % and {R("fc1_p8192")} % at 1 user, {R("f_p2048")} % and {R("f_p8192")} % at 8 users. Mirror: {R("fm1_p2048")} % and {R("fm1_p8192")} % at 1 user, {R("fm8_p2048")} % and {R("fm8_p8192")} % at 8 users. The 8-user prompt-2048 canonical cell is one 3-repetition run with repetitions {R("f_rep1")}, {R("f_rep2")} and {R("f_rep3")} TPS (sd {R("f_sd")} TPS, the noisiest cell of the grid). The perf rounds of 2026-08-25 and 08-30 (two runtron campaigns that compared the canonical and mirror builds, with no clean arm) measured {R("f_pr8")} TPS for the same canonical cell. Against the 2026-08-19 clean value {R("f_clean8")} TPS that is {R("f_p2048_alt")} % (est., a cross-day ratio, not a paired measurement) [footnote 15]. The prompt-8192 cells were replicated 8 times. (2) The {R("f_curve_date")} 1-user context sweep, mirror build against a clean binary, 8 repetitions per cell, medians: {R("f1_p1024")} % at prompt 1024, {R("f1_p2048")} % at 2048, {R("f1_p4096")} % at 4096, {R("f1_p8192")} % at 8192, {R("f1_p16384")} % at 16384, {R("f1_p32768")} % at 32768. The measured attention share of a decode token at 1 user is {R("f_share256")} / {R("f_share2048")} / {R("f_share8192")} % at prompt 256 / 2048 / 8192 (fence round 3, a 2026-09-01 campaign that timed the attention phase of each decode step, kill-switch arm). The qwen series of data F has no llama cell.</li>
<li><b>Data G (t4-shapes, {R("g_date")}).</b> The only llama-8b measurement at a prompt above 1024 with an AMX-off arm. runtron, the ingested llama-3.1-8b tp2 plugin (not the hand-written "good" plugin the nightly runs), CPU attention (USE_HW_ATTN=0), the arena K-mirror binary (sha256 {R("g_sha")}...) with the kill switch on against off, {R("g_reps")} repetitions per cell, 256 generated tokens. 1 user at prompt 8192: {R("g_off1")} to {R("g_on1")} TPS ({R("g_gain1")} %, {R("kv_g1")}K KV tokens per step). 8 users at prompt 2048: {R("g_off8")} to {R("g_on8")} TPS per user ({R("g_gain8")} %, {R("kv_g8")}K). Caveats: kill-switch denominator, mirror build not canonical, ingested plugin, 2 repetitions. The perf rounds of 2026-08-25 and 08-30 ran the same two llama cells with canonical and mirror arms only (no AMX-off arm). They therefore give no AMX gain.</li>
<li><b>Data E (p0perf, 2026-09-13).</b> Our half, the nightly's per-engine load (tp2: 2 engines x 2 users, tp4: 1 engine x 4 users), CPU attention forced with USE_HW_ATTN=0: qwen-3-4b tp2 {R("e_qwen_off")} to {R("e_qwen_on")} TPS ({R("e_qwen_tp2")} %), tp4 {R("e_qwen_tp4")} %. But CPU attention with AMX is {R("e_loss_tp2")} % (tp2) and {R("e_loss_tp4")} % (tp4) TPS against the production FPGA attention. A CPU-attention qwen config would therefore fail today's goals.</li>
<li><b>Data H (l8b-levers, {R("h_date")}, test T0 as run).</b> The whole machine, the exact nightly layout ({R("eng_tp2")} tp2 engines behind Caddy), the nightly's own client, the nightly deb {R("b_deb_base")} against the canonical-AMX deb {R("b_deb_canon")}, {R("h_passes")} interleaved passes, {R("h_configs")} configs (the 7168 and 8192 cells dropped, see section 4). Users lever at prompt {R("prompt")}: {R("h_gain_2u1024")} % at 2 users per engine ({R("h_res_2u1024")}), {R("h_gain_4u1024")} % at 4 ({R("h_res_4u1024")}), {R("h_gain_8u1024")} % at 8 ({R("h_res_8u1024")}). Context lever at 2 users per engine: {R("h_gain_2u2048")} % at prompt 2048, {R("h_gain_2u3000")} % at 3000, {R("h_gain_2u4096")} % at 4096. 8 users per engine at prompt 2048: {R("h_gain_8u2048")} %. Every cell had an even Caddy spread and the AMX-busy probe proved the kernel ran only on the canonical deb. Report: <code>{R("h_report")}</code>.</li>
</ul>
<h3>Chart 1</h3>
{legend([(C_GREEN, "data A: 2-engine stand-in, kill switch off vs on"), (C_GRAY, "data B: nightly layout, whole machine"), (C_GREEN, "data D: one engine, 8 users", "ring")])}
<div class="fig">{chart_gain_vs_load()}</div>
<p class="cap">Only the 8-users-per-engine point is large ({R("gap_pts")} points above today's load, footnote 9). The three points at 2 users per engine (today's nightly load) are all at or below {R("b_canon_gain")} %.</p>

<h3>1.1 Are more users and longer prompts one lever?</h3>
<p>Both levers raise the attention work per decode step (glossary: KV tokens per engine step). If that product were all that mattered, every llama-8b point in chart 3 would sit on one curve. It does not.</p>
<ul>
<li>At about 8K to 9K KV tokens per engine step the llama-8b gains are {R("g_gain1")} % (1 user, prompt 8192, data G), {R("a_gain4")} % (4 users per engine, prompt 1024, data A) and {R("c_gain256")} % to {R("c_attr_main")} % (8 users, mean context {R("ctx_c256")}, data C). About the same attention work, and the largest gain is {R("ratio_lo")} to {R("ratio_hi")} times the other two (a {R("spread_step")}-point spread) [footnote 20].</li>
<li>Those measurements differ in tool, denominator, build and plugin (table below). The spread of the gains is therefore not attributed to one cause. One code fact points at the user count itself. tron splits a decode step of 2 or more users into two minibatches. The FPGA matmuls of one half then overlap the CPU attention of the other half. The llama plugin allows this. Ingested plugins such as qwen do not (glossary: minibatch).</li>
<li>Hypothesis: at low user counts part of llama's attention time is hidden behind the FPGA work of the other minibatch, and the kernel can only shorten attention time that is exposed. Counted per minibatch (users per engine x context / 2 for llama at 2 or more users), the llama points come closer to one curve: the gains at 7K to 9K per minibatch span {R("spread_mb")} points instead of {R("spread_step")}, with two points still out of order [footnote 16]. The step times of data A fit the hypothesis in one respect. Adding users 2 to 4 adds only {R("st_grow24")} ms to a step. Adding users 4 to 8 adds {R("st_grow48")} ms, {R("st_ratio")} times more for twice the added attention work, which fits attention hidden at 2 to 4 users and exposed at 8. The AMX saving is {R("st_frac48")} to {R("st_frac24")} % of the added time in both pairs [footnote 17]. Not measured on llama: the exposed attention time per step. T0 ranks the two levers with one model, one tool (the CI harness) and one binary pair. Its three cells at about 8K KV tokens per step (1, 2 and 4 users per engine) test the hiding hypothesis (section 5).</li>
<li>For qwen (one minibatch) the two levers give gains {R("qgap")} points apart at similar KV tokens per step. 8 users at prompt 2048 ({R("kv_f8_2048")}K) gives {R("fm8_p2048")} %. 1 user at prompt 16384 ({R("kv_f1_16384")}K) gives {R("f1_p16384")} % (both mirror builds against a clean binary, data F, but from the 2026-08-19 grid and the 2026-09-01 sweep). That gap is just outside the {R("t0_band")}-point rule T0 uses, and the longer-prompt point is the higher one.</li>
<li>The 8-user qwen canonical series is flat ({R("f_p2048")} % or {R("f_p2048_alt")} % at {R("kv_f8_2048")}K, {R("f_p8192")} % at {R("kv_f8_8192")}K). Hypothesis: at 8 users attention is most of the step. Evidence: at prompt 8192 the 8 users together produce only {R("f_agg")} times the tokens per second of 1 user (clean binary), so one 8-user step takes {R("f_steps8")} one-user steps. If attention scales linearly with users its share is about {R("f_share8_est")} % (est., from the measured 1-user share of {R("f_share8192")} %; the 8-user share is not measured). The canonical kernel's per-unit speedup (the AVX time of one attention work unit divided by its AMX time, measured at prompt 8192) is {R("f_unit8192")}x. A {R("f_share8_est")} % share times that speedup predicts about {R("f_pred8")} % [footnote 18], which matches the measured series. The TPS ceiling with attention as the whole step would be {R("f_ceiling")} %. So the flat series is the load where the gain is close to what the per-unit speedup allows, and it says nothing about the nightly's operating point at {R("kv_a2")}K, where the qwen 1-user curve rises steepest ({R("f1_p1024")} % at prompt 1024, {R("f1_p2048")} % at 2048, {R("f1_p4096")} % at 4096). Whether llama at 2 users per engine rises the same way is untested (T0).</li>
<li>A reviewer asked whether data F has a llama-8b cell. It does not. The nearest data is data G (1 user, prompt 8192: {R("g_gain1")} %; 8 users, prompt 2048: {R("g_gain8")} %) and data C. No measurement of the hand-written llama-8b plugin exists at any prompt above 1024, and none of llama-8b at prompt 4096 or at 2 users per engine with a long prompt. Insufficient data for ranking the levers on llama-8b. T0 is that measurement.</li>
</ul>

{legend([(INK, "llama-8b, data H (nightly layout, whole machine, 3 passes, canonical deb vs nightly deb)", "square"), (C_GREEN, "llama-8b, data A (rinzler + CI harness, kernel on vs kill switch)"), (C_GRAY, "llama-8b, data B (nightly layout, canonical deb vs nightly deb)"), (C_ORANGE, "llama-8b, data C (runtron, clean no-AMX binary)"), (C_BLUE, "llama-8b, data G (runtron, mirror build, kill switch)"), (C_GREEN, "llama-8b, data D (one engine, 8 users)", "ring"), ("#4a3aa7", "qwen-3-4b, data F, 1-user sweep (runtron, mirror build against a clean binary)"), ("#4a3aa7", "qwen-3-4b, data F, 8 users (canonical against a clean binary)", "square")])}
<div class="fig">{chart_gain_vs_kv()}</div>
<p class="cap">Black squares = data H, the T0 campaign in the nightly layout: the dashed line joins its 2-users-per-engine context lever (prompt 1024 to 4096), and the two 8-user squares sit at 16K and 24K. The four llama-8b dots at 8K to 9K (three measurements; data C has two values at 9.2K) span {R("c_gain256")} % to {R("g_gain1")} %. On qwen the 1-user mirror line ({R("f1_p16384")} % at {R("kv_f1_16384")}K) sits 7 points above the 8-user canonical square at {R("kv_f8_2048")}K ({R("f_p2048")} %). The two qwen squares are the canonical kernel. The line is the mirror build, which ran {R("f_mc_8u2048")} to {R("f_mc_8u8192")} points above the canonical kernel in the grid ({R("f_mc_1u8192")} at 1 user and prompt 8192, {R("f_mc_8u2048")} at 8 users and prompt 2048, {R("f_mc_8u8192")} at 8 users and prompt 8192; data F). The square at {R("kv_f8_2048")}K is drawn a little to the right of the data-G dot at the same load so that both stay visible.</p>
<div class="tw"><table>
<tr><th>model, plugin</th><th>tool</th><th>users per engine</th><th>mean context per user</th><th>KV tokens per engine step</th><th>gain</th><th>denominator</th><th>data</th></tr>
<tr><td>llama-8b good</td><td>rinzler + CI harness, 2 engines</td><td>2</td><td>{R("ctx_win")}</td><td>{R("kv_a2")}K</td><td>{R("a_gain2")} %</td><td>kill switch, PR #4424 package</td><td>A</td></tr>
<tr><td>llama-8b good</td><td>rinzler + CI harness, nightly layout</td><td>2</td><td>2015</td><td>{R("kv_b")}K</td><td>{R("b_canon_gain")} % (canonical), {R("b_target_gain")} % (PR #4424)</td><td>clean nightly deb</td><td>B</td></tr>
<tr><td>llama-8b good</td><td>rinzler + CI harness, 2 engines</td><td>4</td><td>1989</td><td>{R("kv_a4")}K</td><td>{R("a_gain4")} %</td><td>kill switch, PR #4424 package</td><td>A</td></tr>
<tr><td>llama-8b ingested</td><td>runtron</td><td>1</td><td>{R("ctx_g1")}</td><td>{R("kv_g1")}K</td><td>{R("g_gain1")} %</td><td>kill switch, mirror build</td><td>G</td></tr>
<tr><td>llama-8b good</td><td>runtron</td><td>8</td><td>{R("ctx_c256")}</td><td>{R("kv_c256")}K</td><td>{R("c_gain256")} % (PR #4424 head), {R("c_attr_main")} % (canonical)</td><td>clean binary before PR #3879</td><td>C</td></tr>
<tr><td>llama-8b good</td><td>runtron</td><td>8</td><td>{R("ctx_c1536")}</td><td>{R("kv_c1536")}K</td><td>{R("c_gain1536")} %</td><td>clean binary before PR #3879</td><td>C</td></tr>
<tr class="flag"><td>llama-8b good</td><td>rinzler + CI harness, 2 engines</td><td>8</td><td>1991</td><td>{R("kv_a8")}K</td><td>{R("a_gain8")} %</td><td>kill switch, PR #4424 package</td><td>A</td></tr>
<tr><td>llama-8b good</td><td>rinzler + CI harness, 1 engine</td><td>8</td><td>1991</td><td>{R("kv_a8")}K</td><td>{R("d_llama8b")} %</td><td>kill switch, canonical build</td><td>D</td></tr>
<tr><td>llama-8b ingested</td><td>runtron</td><td>8</td><td>{R("ctx_g8")}</td><td>{R("kv_g8")}K</td><td>{R("g_gain8")} %</td><td>kill switch, mirror build</td><td>G</td></tr>
<tr class="flag"><td>llama-8b good</td><td>rinzler + CI harness, nightly layout (H)</td><td>2</td><td>1024 / 2048 / 3000 / 4096 + {R("h_ovh")} + 960</td><td>{R("h_kv_2u1024")} / {R("h_kv_2u2048")} / {R("h_kv_2u3000")} / {R("h_kv_2u4096")}K</td><td>{R("h_gain_2u1024")} / {R("h_gain_2u2048")} / {R("h_gain_2u3000")} / {R("h_gain_2u4096")} %</td><td>clean nightly deb</td><td>H</td></tr>
<tr class="flag"><td>llama-8b good</td><td>rinzler + CI harness, nightly layout (H)</td><td>4</td><td>1024 + {R("h_ovh")} + 960</td><td>{R("h_kv_4u1024")}K</td><td>{R("h_gain_4u1024")} %</td><td>clean nightly deb</td><td>H</td></tr>
<tr class="flag"><td>llama-8b good</td><td>rinzler + CI harness, nightly layout (H)</td><td>8</td><td>1024 / 2048 + {R("h_ovh")} + 960</td><td>{R("h_kv_8u1024")} / {R("h_kv_8u2048")}K</td><td>{R("h_gain_8u1024")} / {R("h_gain_8u2048")} %</td><td>clean nightly deb</td><td>H</td></tr>
<tr><td>qwen-3-4b</td><td>runtron</td><td>1</td><td>1152 / 2176 / 4224 / 8320 / 16512 / 32896</td><td>{R("kv_f1_1024")} / {R("kv_f1_2048")} / {R("kv_f1_4096")} / {R("kv_f1_8192")} / {R("kv_f1_16384")} / {R("kv_f1_32768")}K</td><td>{R("f1_p1024")} / {R("f1_p2048")} / {R("f1_p4096")} / {R("f1_p8192")} / {R("f1_p16384")} / {R("f1_p32768")} % (mirror)</td><td>clean binary</td><td>F</td></tr>
<tr><td>qwen-3-4b</td><td>runtron</td><td>8</td><td>{R("ctx_g8")} / {R("ctx_g1")}</td><td>{R("kv_f8_2048")} / {R("kv_f8_8192")}K</td><td>{R("f_p2048")} / {R("f_p8192")} % (canonical); {R("fm8_p2048")} / {R("fm8_p8192")} % (mirror)</td><td>clean binary</td><td>F</td></tr>
</table></div>

<h2>2. Which CI models can react</h2>
<p>The kernel needs three things at once: head size {R("head128")}, kv_mul {R("kvmul4")} and CPU attention (plus the bf16 activation scalar that every nightly config has, see the glossary). The table lists the {R("configs12")} nightly perf configs against those three, with the canonical-AMX effect measured in the nightly layout (data B). Only the llama-8b change is resolved. Every other row is not resolved (n.r.). Green rows are the configs the kernel can act on in production.</p>
<div class="tw"><table>
<tr><th>config</th><th>attention</th><th>head size</th><th>kv_mul</th><th>kernel eligible?</th><th>canonical effect in the nightly layout (data B)</th><th>note</th></tr>
{cfg_table}
</table></div>
<ul>
<li><b>llama-3.1-8b</b> is the one config that meets all three conditions and reacts when the load is high enough (data A, C, D).</li>
<li><b>mixtral-8x7b</b> meets the shape conditions but measured parity at 8 users on one engine (data D). Whether the kernel engaged there is not measured: no AMX-busy probe ran on mixtral in data B or data D. Two hypotheses: (a) the kernel ran and the expert layers dominate the step, so attention stays a small share even at high load, (b) the kernel did not engage. The runtron perf rounds argue against (b): at prompt 8192 the mirror build ran about 9 % faster than the canonical build on mixtral (section 4), and the two builds differ only in the AMX attention path. One {R("a_probe")} s AMX-busy probe on a mixtral cell, kill switch off against on, settles it. If (a) holds, a per-layer time split would confirm it.</li>
<li><b>qwen-3-4b</b> meets the shape conditions but runs FPGA attention in production. The kernel acts only in the CPU share. Forcing CPU attention makes it react ({R("e_qwen_tp2")} %, data E) but at {R("e_loss_tp2")} % TPS against production (data E).</li>
<li>llama-3b (kv_mul {R("kvmul3")}), llama-70b (kv_mul {R("kvmul8")}), qwen-2.5 (kv_mul {R("kvmul5")}), gemma-2 and gemma-4 (head {R("head256")}) and gpt-oss (head {R("head64")}) have no kernel path. They are controls: any change on them is noise or a package effect outside the kernel. That is {R("configs_other")} configs and {R("models_other")} models [footnote 10].</li>
</ul>

<h2>3. Recommendation</h2>
<p><b>Add one config: llama-3.1-8b good tp2 at {R("new_users")} users.</b> On the existing {R("eng_tp2")} tp2 engines that is {R("new_upe")} users per engine [footnote 2], the load at which data A measured {R("a_gain8")} %. Nothing else changes: same model, same prompt {R("prompt")}, same {R("gen")} generated tokens, same TPS window.</p>
<p>The harness already runs {R("new_users")} users on {R("eng_tp2")} tp2 engines every night: llama-3.2-3b fast tp2 has nominal_users {R("new_users")} (scripts/perf.py line {R("line_3b_users")}). Its (model, {R("new_users")}) entries in get_goal (scripts/system_ci.py lines {R("line_goal_tps")} and {R("line_goal_min")}) and in thresholds/system_ci_perf.yaml (lines {R("line_yaml_lo")} to {R("line_yaml_hi")}) are the template for the new keys. That config uses different prompt and window settings: recorded prompt {R("prompt3b_rec")} tokens, generate_length {R("gen3b")}, capture {R("cap3b_start")} to {R("cap3b_end")}. Its shared_prompt_length {R("shared3b")} is not applied (glossary). Its duration and TPS therefore do not transfer to the new shape.</p>
<p>This page is a recommendation. jhan decides whether to file the config after T0 (whose 32-user prompt-1024 cells are T1). The CI team decides the goals and the name.</p>
<h3>3.1 The perf.py entry</h3>
<p>A dict like the existing ones. Place it right after the existing llama-3.1-8b @8u entry. The model is unchanged, and the harness then skips provisioning (testlib/inventory.py line {R("line_prov")}, the "already provisioned" branch). The llama-3.3-70b tp2 @8u and @4u pair already works this way.</p>
<pre>{esc(perf_entry)}</pre>
<p class="cap">The "name" field appears in two places: the log line "== Benchmarking ... ==" (scripts/perf.py line {R("line_perf_name")}) and the Talos summary key f"{{config_name}}_tps @ {{nominal_users}}" (line {R("line_perf_describe")}). Results, goals and thresholds are keyed by (model, users). Because the Talos key also carries the user count, the 70b pair keeps one name for both user counts. The CI team may prefer that pattern over the _32u suffix.</p>
<h3>3.2 Goals to add</h3>
<p>Two places need a new (model, {R("new_users")}) key. The values must be set from nights on the shape itself, by the CI team's own policy. This page gives the reference values measured in the stand-in (data A, {R("a_engines")} engines, 8 users each, the PR #4424 package {R("a_binary")} in both arms):</p>
<div class="tw"><table><tr><th>arm</th><th>mean TPS</th><th>slowest sample TPS</th><th>TTFT</th></tr>
<tr><td>AMX kernel off (kill switch, PR #4424 package)</td><td>{R("a_off8")}</td><td>{R("a_slow_off8")}</td><td>{R("a_ttft_off8")} ms</td></tr>
<tr><td>AMX kernel on (PR #4424 package)</td><td>{R("a_on8")}</td><td>{R("a_slow_on8")}</td><td>{R("a_ttft_on8")} ms</td></tr></table></div>
<p><b>T1 reference values, measured (data H).</b> The recommended shape in the exact nightly layout, {R("h_passes")} passes per arm, {R("b_rounds")} rounds each; the mean-TPS and slowest-user goals are the CI team's to set from these.</p>
<div class="tw"><table><tr><th>arm</th><th>mean TPS</th><th>slowest sample TPS (over the passes)</th><th>p05 TPS</th><th>TTFT</th><th>gain</th></tr>
<tr><td>nightly deb {R("b_deb_base")} (no AMX code)</td><td>{R("h_base_8u1024")}</td><td colspan="2">{R("h_min_8u1024")} (nightly / AMX)</td><td>{R("h_ttft_8u1024")} ms (nightly / AMX)</td><td rowspan="2">{R("h_gain_8u1024")} %, paired t {R("h_t_8u1024")}, {R("h_res_8u1024")}</td></tr>
<tr><td>canonical-AMX deb {R("b_deb_canon")}</td><td>{R("h_canon_8u1024")}</td><td colspan="2">p05 {R("h_p05_8u1024")} (nightly / AMX)</td><td>one config takes {R("h_wall_8u1024")} min (10 rounds)</td></tr></table></div>
<p class="cap">Today's shape in the same campaign: {R("h_base_2u1024")} against {R("h_canon_2u1024")} TPS ({R("h_gain_2u1024")} %, {R("h_res_2u1024")}), inside the pre-registered +0.2 to +1.2 % band: {R("h_band2")}; the recommended shape against its 9.9 to 15.9 % band: {R("h_band8")}.</p>
<p class="cap">Neither row above is today's deb or the canonical deb; the T1 table below has those two packages. T0 has no kill-switch arm (jhan's decision), so whether a kill-switch arm equals a clean binary on llama stays unmeasured. The YAML entry needs p05 TPS (the 5th percentile), which is not the slowest sample. This page has no p05 value for the shape, so T1 reports it per arm.</p>
<p>scripts/system_ci.py, function get_goal, platform granite_rapids_72_rinzler:</p>
<pre>{esc(goal_entry)}</pre>
<p>thresholds/system_ci_perf.yaml, one new entry:</p>
<pre>{esc(yaml_entry)}</pre>
<ul>
<li>TTFT at {R("new_users")} users is about {R("ttft_s_lo")} to {R("ttft_s_hi")} s (data A) [footnote 3]. TTFT is shown on the Slack line but not judged (testlib/results.py marks it informational), so only the mean-TPS and slowest-user goals need values. The slowest-user goal must be set for this shape, not copied from the @8u config.</li>
<li>The provisional goals are the CI team's decision. T1 in section 5 (part of T0) gives whole-machine values for them.</li>
</ul>
<h3>3.3 Expected visibility and cost</h3>
<ul>
<li>Expected step: {R("a_gain8")} % = about {R("step_tps")} TPS [footnote 4] against a per-cell sd of {R("a_sd_lo")} to {R("a_sd_hi")} TPS. That is about {R("step_sd_lo")} to {R("step_sd_hi")} sd [footnote 5]. The run-to-run sd of the cell means was {R("a_rr_sd_on")} to {R("a_rr_sd_off")} TPS (derived from the three repetitions), and the @8u config's night-to-night sd over {R("nights13")} nights is {R("night13_sd")} TPS (data B reference), so the {R("step_tps")} TPS step is more than {R("step_night_sd")} of either [footnote 13]. In the Slack report the night the deb preset change lands, the new config's TPS steps up by a visible amount. In the canonical arm of data B the existing configs moved between {R("b_gptoss")} % and {R("b_70b_tp4")} %, and the only resolved change was {R("b_canon_gain")} % on llama-8b.</li>
<li>Cost: about {R("cost_min")} min per night (est.). The 8-user cells of data A took {R("a_cell_lo")} to {R("a_cell_hi")} min each, including a {R("a_probe")} s probe, on {R("a_engines")} engines. The 4-engine shape has the same load per engine. Its duration is therefore the same (est.). The perf phase would go from {R("b_perf_min")} min to about {R("perf_new")} min (est.) [footnote 6].</li>
<li>Keep the existing @8u config. It is the production-like load and the 13-night history belongs to it.</li>
</ul>

<h2>4. Shapes considered and not recommended today</h2>
<p>Four shapes are not recommended. The fifth, longer prompts, is deferred to test T0. That is a change from v1 of this page (section 1.1).</p>
<div class="tw"><table>
<tr><th>shape</th><th>data</th><th>why not, or why deferred</th></tr>
<tr><td>mixtral-8x7b tp2 at 32 users</td><td>Data D: {R("d_mix_off")} to {R("d_mix_on")} TPS ({R("d_mix_gain")} %, sd {R("d_mix_sd")} TPS) at 8 users on one engine.</td><td>Parity is measured at the same users per engine the new llama shape uses. Kernel engagement is not measured (no AMX-busy probe, section 2). No visible step expected either way at prompt 1024. At prompt 8192 the mirror build ran {R("mix_m8192_a")} % and {R("mix_m8192_b")} % faster than the canonical build on mixtral (8 users, the runtron perf rounds of 2026-08-25 and 08-30, which compared the two kernel variants with no AMX-off arm). At prompt 2048 the difference was {R("mix_m2048_a")} % and {R("mix_m2048_b")} % (the {R("mix_m2048_b")} % rests on one outlier repetition of {R("mix_outlier")} TPS in the canonical cell; the other two repetitions give {R("mix_m2048_a")} %). That is mirror against canonical, not an AMX gain. Hypothesis: a speed difference between the two kernel variants means the AMX path ran on mixtral at prompt 8192 and not visibly at 2048, so a long prompt exposes what prompt 1024 does not. A {R("a_probe")} s AMX-busy probe on one mixtral cell would confirm it.</td></tr>
<tr><td>qwen-3-4b with CPU attention</td><td>Data E: {R("e_qwen_tp2")} % (tp2) and {R("e_qwen_tp4")} % (tp4) gain, but {R("e_loss_tp2")} % / {R("e_loss_tp4")} % TPS against production FPGA attention.</td><td>Needs USE_HW_ATTN=0 per config. The harness cannot set that today: both provisioning paths carry only the speculation flag (build_explicit_config, testlib/inference_provisioner.py lines {R("line_bec_lo")} to {R("line_bec_hi")}, and _set_speculation, line {R("line_setspec")}). It runs {R("e_loss_tp2_abs")} % below production, and it would need its own goals. See T3.</td></tr>
<tr><td>one engine with 8 users</td><td>Data D: llama-8b {R("d_llama8b")} %.</td><td>The engine count is {R("cards")} // tp in testlib/inference_provisioner.py (line {R("line_engines")}), not a per-config setting. The 32-user shape reaches the same users per engine without a harness change.</td></tr>
<tr><td>{R("users16")} users (4 per engine)</td><td>Data A: {R("a_gain4")} % at 4 users per engine (paired t {R("a_t4")}).</td><td>Visible but small. The 32-user shape gives {R("a_gain8")} % for about the same cost.</td></tr>
<tr><td>longer prompts, measured in T0 (data H): prompt 2048, 3000 and 4096 at 2 users per engine</td><td>Data H: {R("h_gain_2u2048")} % at prompt 2048 ({R("h_res_2u2048")}), {R("h_gain_2u3000")} % at 3000 ({R("h_res_2u3000")}), {R("h_gain_2u4096")} % at 4096 ({R("h_res_2u4096")}), against {R("h_gain_8u1024")} % for 8 users per engine at prompt 1024. Cell cost: {R("h_wall_2u4096")} min at prompt 4096 against {R("h_wall_8u1024")} min for the 32-user cell.</td><td>The context lever works on the nightly's own plugin, but at 2 users per engine it reaches {R("h_gain_2u4096")} % at prompt 4096, below the {R("h_gain_8u1024")} % of the users lever, and the longest usable prompt is {R("h_trunc")} tokens: the deployed tokenizer.json of the llama-8b w4a16 weights carries a truncation block (max_length {R("h_trunc")}, the upstream revision of 2024-08-13; Neural Magic removed it on 2024-09-30; the weights store never refreshed the file; the 70b w4a16 file has the same block at {R("h_trunc70")}). Until that file is refreshed, no CI or production request above {R("h_trunc")} prompt tokens is served as sent. A long-prompt shape is therefore not recommended today; the 8-users-per-engine shape stands. The 16K pair of section 5 could not be measured (its prompt-7168 cell is truncated to 4096). Update {R("i_date")} (data I): at {R("new_upe")} users per engine and prompt {R("prompt4096")} the kernel gains {R("i_gain")} % ({R("i_res")}, {R("i_inside")} the pre-registered band of {R("i_band_lo")} to {R("i_band_hi")} %). Cell cost {R("i_wall")} min, TTFT {R("i_ttft_base")} / {R("i_ttft_amx")} ms nightly / AMX. The reading of that result is in the Short version, fourth paragraph.</td></tr>
</table></div>

<h2>5. Test plan</h2>
<p><b>Status after {R("h_date")}: T0 ran (data H).</b> The check cell (32 users x prompt_length 8192, canonical deb) completed in {R("h_check_min")} min at {R("h_check_tps")} TPS and TTFT {R("h_check_ttft")} ms, but the server counted {R("h_check_pt")} prompt tokens per request: the deployed tokenizer file truncates prompts to {R("h_trunc")} tokens (section 4). The 7168 and 8192 cells were dropped before the first pass (the plan's fallback for cells that cannot be measured), the campaign was stopped, restored and relaunched with {R("h_configs")} configs and ran {R("h_passes")} interleaved passes per arm. Verdicts by the pre-registered rule: 16K pair: {R("h_pair")}. 8K triple: {R("h_triple")} (1-user cell had 10 requests per engine in every run: {R("h_triple_ok")}). The measured server overhead around prompt_length was {R("h_ovh")} tokens (the plan assumed {R("ovh")}). Full report: <code>{R("h_report")}</code>. The plan as pre-registered follows.</p>
<div class="tw"><table>
<tr><th>cell (users per engine x prompt)</th><th>KV tokens per step</th><th>paired passes</th><th>nightly TPS</th><th>AMX TPS</th><th>gain</th><th>paired t</th><th>resolved</th><th>slowest sample nightly / AMX</th><th>p05 nightly / AMX</th><th>TTFT ms nightly / AMX</th><th>min per config</th></tr>
<tr><td>2 x 1024 (today's nightly cell)</td><td>{R("h_kv_2u1024")}K</td><td>{R("h_n_2u1024")}</td><td>{R("h_base_2u1024")}</td><td>{R("h_canon_2u1024")}</td><td>{R("h_gain_2u1024")} %</td><td>{R("h_t_2u1024")}</td><td>{R("h_res_2u1024")}</td><td>{R("h_min_2u1024")}</td><td>{R("h_p05_2u1024")}</td><td>{R("h_ttft_2u1024")}</td><td>{R("h_wall_2u1024")}</td></tr>
<tr><td>2 x 2048</td><td>{R("h_kv_2u2048")}K</td><td>{R("h_n_2u2048")}</td><td>{R("h_base_2u2048")}</td><td>{R("h_canon_2u2048")}</td><td>{R("h_gain_2u2048")} %</td><td>{R("h_t_2u2048")}</td><td>{R("h_res_2u2048")}</td><td>{R("h_min_2u2048")}</td><td>{R("h_p05_2u2048")}</td><td>{R("h_ttft_2u2048")}</td><td>{R("h_wall_2u2048")}</td></tr>
<tr><td>2 x 3000</td><td>{R("h_kv_2u3000")}K</td><td>{R("h_n_2u3000")}</td><td>{R("h_base_2u3000")}</td><td>{R("h_canon_2u3000")}</td><td>{R("h_gain_2u3000")} %</td><td>{R("h_t_2u3000")}</td><td>{R("h_res_2u3000")}</td><td>{R("h_min_2u3000")}</td><td>{R("h_p05_2u3000")}</td><td>{R("h_ttft_2u3000")}</td><td>{R("h_wall_2u3000")}</td></tr>
<tr><td>2 x 4096 (T2)</td><td>{R("h_kv_2u4096")}K</td><td>{R("h_n_2u4096")}</td><td>{R("h_base_2u4096")}</td><td>{R("h_canon_2u4096")}</td><td>{R("h_gain_2u4096")} %</td><td>{R("h_t_2u4096")}</td><td>{R("h_res_2u4096")}</td><td>{R("h_min_2u4096")}</td><td>{R("h_p05_2u4096")}</td><td>{R("h_ttft_2u4096")}</td><td>{R("h_wall_2u4096")}</td></tr>
<tr><td>4 x 1024</td><td>{R("h_kv_4u1024")}K</td><td>{R("h_n_4u1024")}</td><td>{R("h_base_4u1024")}</td><td>{R("h_canon_4u1024")}</td><td>{R("h_gain_4u1024")} %</td><td>{R("h_t_4u1024")}</td><td>{R("h_res_4u1024")}</td><td>{R("h_min_4u1024")}</td><td>{R("h_p05_4u1024")}</td><td>{R("h_ttft_4u1024")}</td><td>{R("h_wall_4u1024")}</td></tr>
<tr class="flag"><td>8 x 1024 (T1, the recommended shape)</td><td>{R("h_kv_8u1024")}K</td><td>{R("h_n_8u1024")}</td><td>{R("h_base_8u1024")}</td><td>{R("h_canon_8u1024")}</td><td>{R("h_gain_8u1024")} %</td><td>{R("h_t_8u1024")}</td><td>{R("h_res_8u1024")}</td><td>{R("h_min_8u1024")}</td><td>{R("h_p05_8u1024")}</td><td>{R("h_ttft_8u1024")}</td><td>{R("h_wall_8u1024")}</td></tr>
<tr><td>8 x 2048</td><td>{R("h_kv_8u2048")}K</td><td>{R("h_n_8u2048")}</td><td>{R("h_base_8u2048")}</td><td>{R("h_canon_8u2048")}</td><td>{R("h_gain_8u2048")} %</td><td>{R("h_t_8u2048")}</td><td>{R("h_res_8u2048")}</td><td>{R("h_min_8u2048")}</td><td>{R("h_p05_8u2048")}</td><td>{R("h_ttft_8u2048")}</td><td>{R("h_wall_8u2048")}</td></tr>
</table></div>
<p class="cap">TTFT and prefix-cache figures of the cells above prompt 1024 are affected by warm prefixes: every config reuses the same ShareGPT seeds, so a longer prompt of a seed starts with the shorter prompt sent minutes earlier; decode TPS is not affected. Minutes per config are the harness wall time of 10 rounds.</p>
<ul>
<li><b>T0 (required).</b> One whole-machine campaign of about {R("t0_hours")} h (est.) on delphi-3bda with the CI harness in the exact nightly layout. It needs the CI lease free and Bill idle: jhan removes Bill's marker with exec/bill-share.sh take (launch.sh runs it on his order). Earliest start about {R("t0_start")} UTC (est., when the nightly's lease clears). The window until the pre-CI hold at 01:40 UTC is about {R("t0_window_h")} h. Two arms, the nightly deb and the canonical deb (no kill-switch arm, jhan's decision of 2026-09-19). One model, one tool, one binary pair, both levers; the cells of T1 and T2 below are part of it.
  <ul>
  <li><b>Tool and layout.</b> rinzler provisioned by platformd as the nightly does it: {R("eng_tp2")} tp2 engines behind Caddy, the harness client (scripts/perf.py through exec/canon-ci-20260918/st_ci_perf.py from the systems_test checkout at ~/workspace/ai-runs/systems_test), {R("b_rounds")} rounds per config, {R("gen")} generated tokens, TPS window tokens {R("cap_start")} to {R("cap_end")}. The same driver ran data B.</li>
  <li><b>Arms.</b> nightly deb {R("b_deb_base")} (clean, no AMX code) against the canonical-AMX deb {R("b_deb_canon")}; both packages exist on the machine. The two packages come from the same main commit {R("canon_main")}. The canonical deb adds one change, the deb-preset commit {R("canon_preset")} (TRON_AMX_DISPATCH=ON in CMakePresets.json). Its packaged rinzler therefore carries the kernel: {R("canon_insns")} AMX tile instructions and the TRON_AMX_DISABLE string, counted at build time (manifest; PR #4424 not included). A rinzler built without that preset change has no AMX code, whatever its source commit. Before each pass dut.sh ensure-base or ensure-canon compares the installed version and the sha256 of /opt/positron/bin/rinzler with the expected package. The per-config AMX-busy probe then confirms which arm ran (0 cycles on the nightly deb, about {R("b_busy")} billion cycles on the canonical deb at 2 users per engine, data B). {R("t0_passes")} passes per arm, arms interleaved (clean, canonical, clean, ...), one package switch between passes. After every switch the driver restarts the engines (dut.sh serving-down, then the pass's provisioning starts them): apt never restarts engines, T0 provisions the same model in every pass, so without the restart a pass could run the previous arm's binary. The driver stops the pass if any engine runs a deleted binary (st_ci_perf.py line {R("line_deleted_check")} only logs it today), and the after-provision snapshot must show every engine on the installed rinzler sha.</li>
  <li><b>Configs (each pass, {R("t0_configs")} configs, all llama-3.1-8b good tp2 with prompt_mode sharegpt).</b> Users lever at prompt {R("prompt")}: nominal_users {R("night_users")} (2 per engine, today's config), {R("users16")} (4 per engine) and {R("new_users")} (8 per engine, the recommended shape). Context lever at 2 users per engine (nominal_users {R("night_users")}): prompt {R("t0_p2u")}. Context lever at 8 users per engine (nominal_users {R("new_users")}): prompt {R("t0_p8u")}. One cell at nominal_users 4 (1 user per engine if Caddy spreads the 4 users evenly): prompt {R("t0_p1u")}. The prompt-1024 cells at nominal_users {R("night_users")} and {R("new_users")} belong to both levers and are counted once: {R("t0_configs")} configs. Each config dict carries a distinct name with the prompt length (for example llama_3_1_8b_instruct_good_tp2_8u_p4096), because the harness keys its summary by name and user count only. KV tokens per engine step in the TPS window (context = prompt + {R("ovh")} + 960, where {R("ovh")} = the extra tokens the server counted around prompt {R("prompt")} in data B and 960 = the middle of the TPS window; est. at the longer prompts): 2 users {R("kv_t0_2u")}K; 4 users {R("kv_t0_4u")}K; 8 users {R("kv_t0_8u")}K; 1 user {R("kv_t0_1u")}K [footnote 19].</li>
  <li><b>Step 0, the prompt source.</b> The harness fails for {R("fail2048")} of the 80 default seeds at prompt {R("prompt2048")} and for all 80 at {R("prompt8192")} (data P). One change in PromptGenerator.generate (testlib/prompt.py lines {R("line_gen_lo")} to {R("line_gen_hi")}) fixes it: copy the conversation list (today the code inserts the system line into the stored list in place, and workers share those lists), append copies of the next conversations (seed + 1, seed + 2, ...) until the token count reaches prompt_length, then prune as today. Every conversation is at least {R("p_min")} tokens (data P). At prompt {R("prompt")} the loop therefore never runs. The prompt-1024 cells stay comparable with the nightly. The change lives in our checkout at ~/workspace/ai-runs/systems_test, the one the driver runs. The nightly's checkout is not touched. Offline check before the campaign: seeds 0 to 319 give the same token count in two runs at every T0 prompt length.</li>
  <li><b>Equal-KV comparisons.</b> Pair at 16K: 2 users x prompt 7168 against 8 users x prompt 1024 ({R("t0_pair16")} KV tokens per step). Triple at 8K: 1 user x prompt 7168, 2 users x prompt 3000 and 4 users x prompt 1024 ({R("t0_triple8")}). The three cells do the same attention work per step. The 1-user cell runs it in one minibatch, the other two in two minibatches (glossary: minibatch), so per minibatch their loads are 8.2K, 4.0K and 4.0K. The triple therefore tests the hiding hypothesis of section 1.1. The per-engine request counts of the nominal_users-4 cell (read from the rinzler journal per unit) must show 10 requests per engine, or the cell is excluded from the triple. The 2-user cells at prompt 4096 and 8192 are the long-prompt shape at today's user count (T2), with their durations recorded for the cost per night.</li>
  <li><b>Decision rule, pre-registered here.</b> Per config and comparison a paired t over the {R("t0_reps")} passes (pass r of one arm pairs with pass r of the other). A change is resolved at |t| at or above {R("t0_t975")} (the 95 % two-sided limit of Student's t with {R("t975_df")} degrees of freedom) and |change| at or above 1 %. Pair at 16K: if the two gains agree within {R("t0_band")} percentage points, the two levers count as one mechanism and a long-prompt shape is a peer recommendation. If the 2-user cell gains more than {R("t0_band")} points above the 8-user cell, the context lever counts as stronger and the long-prompt shape is the primary recommendation. If the 8-user cell gains more than {R("t0_band")} points above, the users lever counts as stronger and this page stands. Triple at 8K: the hiding hypothesis is supported when the 1-user cell gains more than {R("t0_band")} points above both the 2-user and the 4-user cell and those two agree within {R("t0_band")} points. It is rejected when all three agree within {R("t0_band")} points. Every other pattern is recorded as undecided and named in the report.</li>
  <li><b>Expected.</b> {R("a_gain2")} % to {R("b_canon_gain")} % at 2 users and prompt {R("prompt")} (data A, B). About {R("a_gain8")} % at 8 users and prompt {R("prompt")} (data A; acceptance band {R("acc_lo")} % to {R("acc_hi")} % as T1 pre-registered). A rising prompt axis at 2 users (the qwen 1-user curve, data F; hypothesis for llama).</li>
  <li><b>Also recorded.</b> Per config: mean TPS, slowest sample, p05 TPS, TTFT, client CPU pressure, anomalous-sample counts, cell duration (the harness sample per_model_perf_test_duration), and a 20 s AMX-busy probe (the driver probes llama-8b already). New for T0: per-engine request counts, read from the rinzler journal per unit before and after each config; they give the Caddy spread. The driver records the prompt length in every raw record.</li>
  <li><b>Check before the campaign.</b> Run one canonical-deb cell at 8 users per engine and prompt 8192 by hand with a short timeout. It is a load above every T0 cell: its KV need is 8 x 9728 tokens x {R("kv_llama_tok")} KiB = {R("kv_check")} GiB per engine, inside the {R("hp_engine")} GiB of hugepages of an engine; the largest T0 cell (8 users at prompt 2048) needs {R("kv_t0_max8")} GiB. No record shows the hand-written llama plugin above prompt 1024. Its duration is an upper bound for the long-prompt estimates of footnote 19.</li>
  <li><b>Tooling.</b> The exec/canon-ci-20260918/ driver with these changes: a configs override in st_ci_perf.py (a JSON list of perf.py dicts with distinct names replaces the module's configs, and prompt_length is added to every raw record); the prompt-source change of step 0; an arm loop that alternates ensure-base and ensure-canon over {R("t0_passes")} passes with an engine restart after every switch (both package steps exist in the canon-ci dut.sh; the alternation pattern is the one the ci-mimic campaign used); the deleted-binary check made to stop the pass; per-engine request counts from the rinzler journals. The changes are listed in exec/canon-ci-20260918/T0-script-changes.md.</li>
  </ul></li>

<li><b>T1 (the 32-user prompt-1024 cells of T0; about {R("t1_bench_min")} min of T0's benchmark time).</b> The proposed shape in the nightly layout: {R("eng_tp2")} tp2 engines behind Caddy, {R("new_users")} users in one client, prompt {R("prompt")}, {R("gen")} tokens, {R("b_rounds")} rounds. Arms: the nightly deb {R("b_deb_base")} against the canonical-AMX deb {R("b_deb_canon")}. {R("t_reps")} passes per arm, interleaved ({R("t1_cells")} cells) [footnote 7]. T1 is the first measurement of two things: the spread of {R("new_users")} users over the engines through Caddy (also exercised by T0's 32-user prompt-2048 cells), and the {R("seeds_new")} ShareGPT conversations (seeds {R("seeds80")} to {R("seed_last")}) no run has used at prompt {R("prompt")} [footnote 12]. The prompt source is not a blocker: prune_convo at prompt_length {R("prompt")} succeeds for all {R("seeds320")} seeds, the shortest conversation being {R("shortest_tokens")} tokens (seed {R("seed_shortest")}, data P). Outputs: mean TPS, slowest sample, p05 TPS and TTFT per arm, run-to-run sd, cell duration, per-engine request counts (the Caddy spread), client CPU pressure and the count of anomalous TPS samples per config as the data-B report records them (the existing 32-user config llama-3.2-3b showed {R("b_anom_3b")} anomalous samples in one arm of data B), and the provisional goals for the CI team. Tooling: T0's driver; T1 needs no separate change. Acceptance, pre-registered here: gain within {R("acc_pts")} points of {R("a_gain8")} % (that is {R("acc_lo")} % to {R("acc_hi")} %) [footnote 8] and run-to-run sd below {R("acc_sd")} TPS. Not measured until T0 runs: the 32-user llama-8b shape through Caddy with one client.</li>
<li><b>T2 (the 2-users-per-engine long-prompt cells of T0 at prompt {R("prompt4096")} and {R("prompt8192")}).</b> They are the long-prompt shape at today's user count, measured in the nightly layout with the nightly deb against the canonical deb, {R("t0_reps")} passes, durations recorded for the cost per night. A filed long-prompt config needs a prompt-source change in the systems_test repository. T0's step 0 (concatenation of ShareGPT conversations) serves every prompt length. The alternative draws seeds from the long conversations only: {R("p_ge4096")} of at least {R("prompt4096")} tokens and {R("p_ge8192")} of at least {R("prompt8192")} (data P), so at prompt {R("prompt8192")} the prompts repeat apart from the timestamp line. If a long-prompt shape is recommended after T0, the CI team picks one of the two.</li>
<li><b>T3 (only if the CI team wants a CPU-attention guard for ingested models).</b> First harness support for a per-config USE_HW_ATTN. The harness sets one engine variable today, TRON_USE_SPECULATION, through posadm config.set (testlib/inference_provisioner.py line {R("line_setspec")}); on this machine the value lands in the instance env files (data B snapshots). Whether the same call carries USE_HW_ATTN to an engine needs one check: one engine restart with the variable set and a 20 s AMX-busy probe; it has not run yet. The platformd config payload path (build_explicit_config, lines {R("line_bec_lo")} to {R("line_bec_hi")}; patch_config, line {R("line_patch")}) carries only the speculation flag. Then qwen-3-4b tp2 @8u with CPU attention, {R("t_arms")} arms x {R("t_reps")} repetitions, with its own goals.</li>
<li><b>T4 (after the deb preset change lands).</b> Watch the new config for {R("t4_nights")} nights before the static goals are set. The ratchet threshold's history (history_runs {R("hist_runs")}) is full only after {R("hist_runs")} nights.</li>
</ul>
<h3>Chart 2</h3>
{legend([(C_GRAY, "measured in the nightly layout (data B, canonical deb against the nightly deb)", "rect"), (C_GREEN, "proposed shape, measured in the 2-engine stand-in (data A, kill switch off against on)", "rect-light")])}
<div class="fig">{chart_step_per_config(bars)}</div>
<p class="cap">The proposed bar ({R("a_gain8")} %) is {R("step_vs_gptoss")} times the longest existing bar ({R("b_gptoss")} %, gpt-oss, not resolved) [footnote 14]. Every existing config sits between {R("b_gptoss")} % and {R("b_70b_tp4")} %, and only llama-8b's {R("b_llama8b")} % is resolved.</p>

<h2>6. Sources</h2>
<p>Paths are relative to the intel-AMX root unless they start with VNNIed-K-in-place/ or systems_test/.</p>
<ul>
<li><b>A</b> l8bload 2026-09-18: report <code>VNNIed-K-in-place/status/llama8b-AMX-gain-vs-load.html</code>, results <code>exec/results/l8bload-20260918/</code> (cells, summary.json), scripts <code>exec/l8bload-20260918/</code>.</li>
<li><b>B</b> canon-ci 2026-09-18/19: report <code>PR3879/new-PRs/PR1/canonical-AMX-CI-run-report.html</code>, results <code>exec/results/canon-ci-20260918/</code> and <code>exec/results/ci-mimic-20260918/</code> (base arm, nightly reference, 13-night statistics), scripts <code>exec/canon-ci-20260918/</code>.</li>
<li><b>C</b> wedperf 2026-09-16: report <code>VNNIed-K-in-place/status/Wednesday-perf-test.html</code>, scripts <code>exec/wedperf-20260916/</code>.</li>
<li><b>D</b> more-testing round 1, 2026-09-05: <code>PR3879/more-testing/round-1/results.html</code> and <code>status.md</code>, results <code>exec/results/more-testing-r1/</code>, scripts <code>exec/more-testing-r1/</code>.</li>
<li><b>E</b> p0perf 2026-09-13: report <code>PR3879/new-PRs/PR1/Sunday-CI-layout-results.html</code>, results <code>exec/results/p0perf-20260913/</code>, scripts <code>exec/p0perf-20260913/</code>.</li>
<li><b>F</b> runtron prompt-length series on qwen-3-4b, CPU attention forced (USE_HW_ATTN=0), summarized in <code>PR3879/make-sense-amx-vs-avx.html</code>. The {R("f_grid_date")} grid: 1 and 8 users, prompt 2048 and 8192, canonical and mirror against a clean binary (raw <code>tmp/amx-raw-data/chart-check.csv</code>, <code>amx-summary.csv</code>, <code>t4-suite.txt</code>). The {R("f_curve_date")} 1-user context sweep, mirror against clean (<code>exec/results/ctxfill-20260901/curve.json</code>, <code>ctxfill2-20260901/curve2.json</code>). The attention shares (<code>exec/results/fence3-20260901/medians.json</code>). The per-unit speedups (the AVX time of one attention work unit divided by its AMX time, <code>exec/results/single-attn-20260901/summary.json</code>). The perf rounds <code>exec/results/perf-round-20260825/</code> and <code>perf-round-20260830/</code> (runtron, canonical and mirror arms only, llama and mixtral cells included): the {R("f_pr8")} TPS canonical value of the qwen 8-user prompt-2048 cell and the mixtral mirror-against-canonical values.</li>
<li><b>G</b> t4-shapes {R("g_date")}: <code>exec/results/t4/t4-shapes.txt</code> (runtron, ingested-llama-3.1-8b-tp2, arena K-mirror binary, kill switch on against off; script <code>exec/p2-t4-shapes.sh</code>).</li>
<li><b>H</b> l8b-levers {R("h_date")} (test T0 as run): report <code>{R("h_report")}</code>, results <code>exec/results/l8b-levers-20260919/</code> (per pass perf.json, summary.json from analyze.py, the check cell, the prompt check), scripts <code>exec/l8b-levers-20260919/</code> (campaign.sh, st_ci_perf.py, analyze.py, gen_report.py, h_registry.py). The tokenizer finding: <code>/opt/positron/weights/huggingface/neuralmagic/Meta-Llama-3.1-8B-Instruct-quantized.w4a16/tokenizer.json</code> on the fleet store (sha256 4a49a5d5..., equal to upstream revision 8ecfb5aa0d) against the upstream fix commit 1455f0f5f7.</li>
<li><b>I</b> l8b-8u4k {R("i_date")} (the {R("new_upe")}-users-per-engine prompt-{R("prompt4096")} cell, same arms, driver and layout as H): report <code>{R("i_report")}</code>, results <code>exec/results/l8b-8u4k-{R("i_stamp")}/</code> (per pass perf.json, summary.json from analyze.py, the prompt check), scripts <code>exec/l8b-8u4k-{R("i_stamp")}/</code> (campaign.sh, st_ci_perf.py, analyze.py, gen_report.py, i_registry.py).</li>
<li><b>P</b> prune probe 2026-09-19: testlib/prompt.py prune_convo run offline in the systems_test .venv with the tokenizer of llama-3.1-8b good (neuralmagic/Meta-Llama-3.1-8B-Instruct-quantized.w4a16, testlib/hf_models.py) over sharegpt_1000.json, seeds 0 to {R("seed_last")} at prompt_length {R("prompt")} and seeds 0 to 79 at {R("prompt4096")} and {R("prompt8192")}; v2 adds a recount of all {R("p_n")} conversations at {R("prompt2048")}, {R("prompt4096")} and {R("prompt8192")} (review session, 2026-09-19). The token count includes the system line the harness inserts.</li>
<li>Nightly reference: <code>exec/results/ci-mimic-20260918/reference/nightly_stats.json</code> (13-night mean and sd per config) and <code>exec/results/ci-mimic-20260918/report-v4.html</code> (the base arm of data B against the PR #4424 package).</li>
<li>Harness code cited: <code>systems_test/scripts/perf.py</code>, <code>scripts/system_ci.py</code>, <code>thresholds/system_ci_perf.yaml</code>, <code>testlib/inventory.py</code>, <code>testlib/inference_provisioner.py</code>, <code>testlib/prompt.py</code>, <code>testlib/tps.py</code>, <code>testlib/results.py</code>, <code>testlib/perf_metrics.py</code>, <code>testlib/system_ci_thresholds.py</code>, <code>testlib/hf_models.py</code> (checkout fc27f07 of 2026-09-17 at ~/workspace/ai-runs/systems_test).</li>
<li>tron code cited: <code>h/tron/kernels/amx_attn_iface.hpp</code>, <code>h/tron/models/self_attention.hpp</code>, <code>h/tron/models/model.hpp</code> (chunk_evenly), <code>h/tron/models/common.hpp</code> (minibatch_grain_size {R("line_grain")} region), <code>h/tron/plugins/llama.hpp</code> and <code>ingest/src/TronCpp.hs</code> at commit {R("tron_head")} (the merged PR #3879 head, worktree ~/workspace/tron-amx).</li>
<li>Harness prompt code cited for the shared_prompt_length correction: <code>testlib/tps.py</code> lines {R("line_tps_field")}, {R("line_tps_cu")}, {R("line_tps_gen_lo")} to {R("line_tps_gen_hi")}, {R("line_tps_seq")}; <code>scripts/perf.py</code> lines {R("line_perf_ctrl")}, {R("line_perf_import")}, {R("line_perf_mode")}; <code>testlib/prompt.py</code> lines {R("line_gen_lo")} to {R("line_gen_hi")}; recorded prompts in <code>exec/results/ci-mimic-20260918/base-pass1/perf.json</code> and <code>exec/results/canon-ci-20260918/canon/perf.json</code>.</li>
<li>v2 follows a review of v1 on 2026-09-19 that re-read the data files behind sources A to G and P.</li>
<li>v4 ({R("i_date")}): data I, the {R("new_upe")}-users-per-engine prompt-{R("prompt4096")} cell of the l8b-8u4k campaign, added to the Short version, the section 4 row on longer prompts and the sources list.</li>
</ul>

<h2>Footnotes: arithmetic of the derived numbers</h2>
<ol class="fn">
<li>({R("a_off2")} - {R("night13_mean")}) / {R("night13_mean")} = 0.0132 = {R("night13_gap")} %.</li>
<li>{R("eng_tp2")} engines x {R("new_upe")} users per engine = {R("new_users")} users. Engine count: {R("cards")} cards // tp2 = {R("eng_tp2")}.</li>
<li>{R("a_ttft_on8")} ms = {R("ttft_s_lo")} s and {R("a_ttft_off8")} ms = {R("ttft_s_hi")} s (rounded to 0.1 s).</li>
<li>{R("a_on8")} - {R("a_off8")} = {R("step_tps")} TPS. {R("step_tps")} / {R("a_off8")} = 0.1293 = {R("step_pct")} %.</li>
<li>{R("step_tps")} / {R("a_sd_hi")} = 22.7, about {R("step_sd_lo")} sd. {R("step_tps")} / {R("a_sd_lo")} = 41.2, about {R("step_sd_hi")} sd.</li>
<li>{R("b_perf_min")} min + {R("cost_min")} min (est.) = {R("perf_new")} min (est.). The {R("cost_min")} min is the {R("a_cell_lo")} to {R("a_cell_hi")} min per 8-user cell of data A, rounded up.</li>
<li>{R("t_arms")} arms x {R("t_reps")} passes = {R("t1_cells")} cells. {R("t1_cells")} x {R("cost_min")} min = {R("t1_bench_min")} min of benchmark time (est.). The package switches and provisioning belong to T0 as a whole (footnote 19).</li>
<li>{R("step_pct")} - {R("acc_pts")} = {R("acc_lo")} %. {R("step_pct")} + {R("acc_pts")} = {R("acc_hi")} %.</li>
<li>Chart 1 gap: {R("step_pct")} - 0.2 = 12.7 percentage points ({R("gap_pts")} points) between 8 and 2 users per engine (data A).</li>
<li>{R("configs12")} configs - {R("kernel_configs")} with a kernel path by shape (llama-8b, mixtral, qwen-3-4b tp2, qwen-3-4b tp4) = {R("configs_other")} configs without one. {R("models9")} distinct models - 3 with a kernel path by shape (llama-8b, mixtral, qwen-3-4b) = {R("models_other")} models without one.</li>
<li>tp2 configs at {R("night_users")} users: llama-8b, 70b tp2 @8u, mixtral, qwen-2.5, qwen-3-4b tp2, gemma-2, gemma-4 = {R("configs_tp2_8u")}, that is llama-8b and {R("configs_tp2_8u_other")} others. The tp4 configs at 8 users (qwen-3-4b tp4, gpt-oss) run 8 users on {R("eng_tp4")} engines = 4 users per engine. The 70b tp2 @4u and tp4 @4u configs run 4 users. llama-3b runs {R("new_users")}.</li>
<li>ShareGPT seed = round x n_users + user (testlib/tps.py line {R("line_seed")}). {R("b_rounds")} rounds x {R("night_users")} users = {R("seeds80")} seeds (0 to 79) for the 8-user config and for each data-A client. {R("b_rounds")} rounds x {R("new_users")} users = {R("seeds320")} seeds (0 to {R("seed_last")}) for the proposed shape. {R("seeds320")} - {R("seeds80")} = {R("seeds_new")} conversations no run has used at prompt {R("prompt")}.</li>
<li>Run-to-run sd of the 8-user cell means (data A): kernel off {R("a_off8_r1")}, {R("a_off8_r2")}, {R("a_off8_r3")} TPS, sample sd = {R("a_rr_sd_off")} TPS. Kernel on {R("a_on8_r1")}, {R("a_on8_r2")}, {R("a_on8_r3")} TPS, sample sd = {R("a_rr_sd_on")} TPS. {R("step_tps")} / {R("night13_sd")} = 17.4, more than {R("step_night_sd")} night-to-night sd. {R("step_tps")} / {R("a_rr_sd_off")} = 25.2, more than {R("step_night_sd")} run-to-run sd.</li>
<li>{R("step_pct")} / 3.9 = {R("step_vs_gptoss")}: the proposed bar against the longest existing bar (gpt-oss, {R("b_gptoss")} %).</li>
<li>Data F noisy cell: mean of {R("f_rep1")}, {R("f_rep2")}, {R("f_rep3")} = 53.60 TPS; 53.60 / {R("f_clean8")} - 1 = {R("f_p2048")} %. With the perf-round canonical value: {R("f_pr8")} / {R("f_clean8")} - 1 = 0.1598 = {R("f_p2048_alt")} % (est.: the perf rounds had no clean arm, so the clean value is the 2026-08-19 one). Data G: {R("g_on1")} / {R("g_off1")} - 1 = 0.1498 = {R("g_gain1")} %; {R("g_on8")} / {R("g_off8")} - 1 = 0.1970 = {R("g_gain8")} %.</li>
<li>KV tokens per engine step (thousands): data A 2 x 1992.3 = 3985 ({R("kv_a2")}K), 4 x 1989.3 = 7957 ({R("kv_a4")}K), 8 x 1991.2 = 15930 ({R("kv_a8")}K), contexts = recorded prompt of each cell + 960; data B 2 x 2015 = 4030; data C 8 x {R("ctx_c256")} = 9216 and 8 x {R("ctx_c1536")} = 14336; data G 1 x {R("ctx_g1")} = 8320 and 8 x {R("ctx_g8")} = 17408; data F 8 users 17408 and 8 x 8320 = 66560; data F 1 user = prompt + 128. Per minibatch for the hand-written llama plugin at 2 or more users (two minibatches): 1992, 3979, 7965 (data A), 4608 and 7168 (data C). Data G used the ingested plugin, which runs one minibatch, so its cells stay 8320 (1 user) and 17408 (8 users). Sorted by the per-minibatch count the gains are 1992: {R("a_gain2")}, 3979: {R("a_gain4")}, 4608: {R("c_gain256")} to {R("c_attr_main")}, 7168: {R("c_gain1536")}, 7965: {R("a_gain8")}, 8320: {R("g_gain1")}, 17408: {R("g_gain8")} %. Two points break the rise: 4608 (data C at 256 tokens, the lowest gain) and 7965 (data A, {R("spread_mb")} points below the 7168 point of data C). The 7K to 9K group spans {R("spread_mb")} points against {R("spread_step")} points per engine step. Hypothesis, not a measurement.</li>
<li>Data A step times (kill switch): 1000 / {R("a_off2")} = {R("st_off2")} ms, 1000 / {R("a_off4")} = {R("st_off4")} ms, 1000 / {R("a_off8")} = {R("st_off8")} ms; growth {R("st_grow24")} ms (2 to 4 users) and {R("st_grow48")} ms (4 to 8); {R("st_grow48")} / {R("st_grow24")} = {R("st_ratio")}. Savings with AMX: {R("st_save2")}, {R("st_save4")}, {R("st_save8")} ms (1000 / off TPS - 1000 / on TPS); {R("st_save4")} / {R("st_grow24")} = 0.28 and {R("st_save8")} / {R("st_grow48")} = 0.27.</li>
<li>Aggregate ratio at prompt 8192: 8 x 14.497 / 105.648 = {R("f_agg")} (clean binary, data F); 8 / {R("f_agg")} = {R("f_steps8")} one-user steps per 8-user step. Share estimate: 8 x 0.626 / 7.27 = 0.69 ({R("f_share8_est")} %, est.). Time saved by the canonical kernel on attention: 1 - 1 / {R("f_unit8192")} = 0.206 ({R("f_saved")} %). Predicted gain: 1 / (1 - 0.69 x 0.206) - 1 = 0.166, about {R("f_pred8")} %. TPS ceiling with attention as the whole step: {R("f_unit8192")} - 1 = {R("f_ceiling")} %.</li>
<li>T0 KV tokens per engine step = users per engine x (prompt + {R("ovh")} + 960), the harness window ({R("ovh")} = data B's recorded overhead at prompt 1024, 1055 - 1024; est. at the longer prompts): 2 users at prompt 1024 / 2048 / 3000 / 4096 / 7168 / 8192 = 4030 / 6078 / 7982 / 10174 / 16318 / 18366 ({R("kv_t0_2u")}K); 4 users at 1024 = 8060 ({R("kv_t0_4u")}K); 8 users at 1024 / 2048 = 16120 / 24312 ({R("kv_t0_8u")}K); 1 user at 7168 = 8159 ({R("kv_t0_1u")}K). Pair at 16K: 16318 against 16120, ratio 1.01. Triple at 8K: 8159, 7982, 8060; per minibatch 8159, 3991, 4030. Cells: {R("t0_configs")} configs x 2 arms x {R("t0_passes")} passes = {R("t0_cells")}. Duration: per pass {R("t0_pass_cells_min")} min = {R("t0_bench_min")} min of benchmark time (est.; the prompt-1024 2-user config measured {R("cell_2u_b")} min in data B and the 4-user cell {R("cell_4u_a")} min in data A; no long-prompt cell has been timed), plus {R("t0_probe_min")} min of probes and snapshots = {R("t0_pass_min")} min per pass. 6 passes = {R("t0_pass6_h")} h; 6 package switches x {R("t0_switch_min")} min = 0.6 h; plus the check cell: about {R("t0_hours")} h (est.). KV need: the largest T0 cell, 8 users x (2048 + 1536) tokens x {R("kv_llama_tok")} KiB = {R("kv_t0_max8")} GiB per engine; the 2-user prompt-8192 cell 2 x (8192 + 1536) x {R("kv_llama_tok")} KiB = {R("kv_t0_max2")} GiB; the check cell (8 users x prompt 8192, not a T0 config) 8 x 9728 x {R("kv_llama_tok")} KiB = {R("kv_check")} GiB.</li>
<li>Section 1.1 ratios: {R("g_gain1")} / {R("a_gain4")} = {R("ratio_lo")}; {R("g_gain1")} / {R("c_gain256")} = {R("ratio_hi")}; spread {R("g_gain1")} - {R("c_gain256")} = {R("spread_step")} points. qwen gap: {R("f1_p16384")} - {R("fm8_p2048")} = {R("qgap")} points. Mirror over canonical in the grid: {R("fm1_p8192")} - {R("fc1_p8192")} = {R("f_mc_1u8192")}; {R("fm8_p2048")} - {R("f_p2048")} = {R("f_mc_8u2048")}; {R("fm8_p8192")} - {R("f_p8192")} = {R("f_mc_8u8192")} points.</li>
<li>Data H KV tokens per engine step = users per engine x (prompt + {R("h_ovh")} + 960), with the overhead measured in the campaign (server-counted prompt tokens minus prompt_length, cells below 4096); the prompt-4096 cell counts 4096 (its 4096 + overhead tokens are clipped to 4096).</li>
</ol>
</main></body></html>
"""
    return html


def audit(html):
    """List every number in the page text with its registry tag. Numbers that match no registry text are printed
    separately for a manual look."""
    text = re.sub(r"<style>.*?</style>", " ", html, flags=re.S)
    text = re.sub(r"<svg.*?</svg>", " ", text, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&#\d+;", " ", text)
    nums = re.findall(r"(?<![\w.])[+-]?\d[\d,]*(?:\.\d+)?(?![\w])", text)
    by_text = {}
    for k, (t, tag, note) in R.items.items():
        by_text.setdefault(t, []).append(k)
        by_text.setdefault(t.lstrip("+"), []).append(k)
    seen, unmatched = {}, {}
    for s in nums:
        s2 = s.lstrip("+")
        keys = by_text.get(s) or by_text.get(s2)
        if keys:
            seen.setdefault(s2, set()).update(keys)
        else:
            unmatched[s2] = unmatched.get(s2, 0) + 1
    return seen, unmatched


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT_DEFAULT)
    a = ap.parse_args()
    html = build_page()
    data = html.encode("ascii", "xmlcharrefreplace")
    assert all(b < 128 for b in data), "non-ASCII byte in output"
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    open(a.out, "wb").write(data)
    print(f"wrote {a.out} ({len(data):,} bytes, ASCII only)")
    unused = sorted(set(R.items) - R.used)
    if unused:
        print("registry entries not used on the page:", ", ".join(unused))
    print("\nNUMBER REGISTRY (value | tag | meaning):")
    for k in sorted(R.items, key=lambda k: (R.items[k][1], k)):
        t, tag, note = R.items[k]
        print(f"  {t:>34} | {tag:7} | {note}")
    seen, unmatched = audit(html)
    print("\nnumbers in the page text that match no registry entry (identifiers expected: dates, PR numbers, footnote indices, section numbers):")
    for s, c in sorted(unmatched.items(), key=lambda x: (-x[1], x[0])):
        print(f"  {s} x{c}")


if __name__ == "__main__":
    main()
