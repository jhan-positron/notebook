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
R.add("t1_hours", "1", "est.", "h whole-machine time for T1")
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
R.add("line_patch", "250", "id", "testlib/inference_provisioner.py line: platformd_client.patch_config(payload)")
R.add("line_proxy", "265", "id", "testlib/inference_provisioner.py line: platformd_client.put_test_proxy")
R.add("line_setspec", "577", "id", "testlib/inference_provisioner.py line of _set_speculation (posadm config.set TRON_USE_SPECULATION)")
R.add("line_gate_lo", "148", "id", "h/tron/kernels/amx_attn_iface.hpp first line of shape_ok / query_scalar_ok / eligible")
R.add("line_gate_hi", "165", "id", "h/tron/kernels/amx_attn_iface.hpp last line of eligible")
R.add("line_amxon_lo", "1236", "id", "h/tron/models/self_attention.hpp first line of amx_eligible / amx_on")
R.add("line_amxon_hi", "1239", "id", "h/tron/models/self_attention.hpp line: amx_on = amx_eligible && available()")
R.add("tron_head", "85fc8ff4de", "id", "tron commit of the cited kernel lines (the merged PR #3879 head)")


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
        f"We recommend one new nightly perf config: llama-3.1-8b good tp2 (tp2 = two FPGA cards per engine) at {R('new_users')} users, which is {R('new_upe')} users per engine on the existing {R('eng_tp2')} tp2 engines.",
        f"Measured on a 2-engine stand-in (rinzler, the production server, plus the CI harness on half the machine), the AMX kernel raises this shape's TPS (decode tokens per second per user) from {R('a_off8')} to {R('a_on8')} TPS ({R('a_gain8')} %), against {R('a_gain2')} % to {R('b_canon_gain')} % for today's {R('night_users')}-user config (data A and B).",
        f"Before the config is filed, one whole-machine run of about {R('t1_hours')} h (test T1) tests the shape in the exact nightly layout and gives the CI team the reference values for its goals.",
    ]
    take = [
        f"Why today's configs cannot show it: the kernel speeds up attention only, and at {R('night_upe')} users per engine attention is a small part of a decode step (section 1).",
        f"Which models can react at all: llama-3.1-8b (yes), mixtral-8x7b (eligible by shape, measured parity, kernel engagement not measured), qwen-3-4b (only with CPU attention, which production does not use). The other {R('configs_other')} configs ({R('models_other')} models) have no kernel path (section 2).",
        f"Cost of the new config: about {R('cost_min')} min per night (est.), and the perf phase would go from {R('b_perf_min')} min to about {R('perf_new')} min (est.). The existing {R('night_users')}-user config stays (section 3).",
        "Not recommended: mixtral at 32 users, qwen-3-4b with CPU attention, one engine with 8 users, 16 users, longer prompts (section 4, each with its data).",
        "Test plan: T1 is required before filing. T2 and T3 are optional. T4 is the watch period after the deb preset change lands (section 5).",
        "Decisions: this page is a recommendation. jhan decides whether to file the config after T1. The CI team decides the goals and the name.",
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
<p class="sub">For the CI team (systems_test owners). Date 2026-09-19. Author: jhan's AMX work. Generated {now} by exec/canon-ci-20260918/gen_ci_shapes.py. Every number is a measurement with a source tag (A to F and P, defined in section 6) unless it is marked est. or its arithmetic is in the footnotes.</p>

<div class="short"><h2 style="margin-top:0;border:0">Short version</h2>
{"".join(f"<p>{s}</p>" for s in sv)}
</div>
<ul class="take">{"".join(f"<li>{x}</li>" for x in take)}</ul>

<h2>Words used here</h2>
<dl class="gloss">
<dt>nightly, System CI, systems_test, perf phase</dt><dd>System CI is the automated nightly test job of the systems_test repository. The nightly is its run on delphi-3bda (the 72-core Intel Granite Rapids test machine) every night at {R("nightly_start")} UTC. The perf phase is the part of the nightly that measures decode speed on {R("configs12")} configs. It takes {R("b_perf_min")} min today (data B).</dd>
<dt>config, shape</dt><dd>A config is one row of the list in scripts/perf.py: a model, its tensor-parallel width (tp) and a user count, for example llama-3.1-8b good tp2 @8u (8 users). This page uses "shape" for the same thing when it talks about a config that does not exist yet.</dd>
<dt>tron, rinzler, engine, tp2, tp4, Caddy</dt><dd>tron is the inference program under test. rinzler is its production server. One running rinzler is one engine. tp2 and tp4 are the tensor-parallel widths: the number of FPGA cards one engine uses. The machine has {R("cards")} cards. The nightly therefore creates {R("cards")} // tp engines: {R("eng_tp2")} for tp2 and {R("eng_tp4")} for tp4 (testlib/inference_provisioner.py line {R("line_engines")}). Caddy is the port-80 proxy in front of the engines. platformd (the production process manager) creates it (put_test_proxy, testlib/inference_provisioner.py line {R("line_proxy")}). Its spreading policy is not visible in tron or systems_test. The evidence for an even spread is indirect: in the nightly-vs-ours campaign of 2026-09-11/13 the per-user "Done" lines of the harness showed two speed levels with even counts per round, which fits {R("night_users")} users on {R("eng_tp2")} engines = {R("night_upe")} users per engine. T1 measures the spread for the proposed shape directly (section 5).</dd>
<dt>good, fast</dt><dd>Names of tron's model-build variants: the same model built in different ways. They appear in perf.py's config names and in testlib/hf_models.py (llama-3.1-8b-instruct-good, -fast, -best). This page uses the "good" build of llama-3.1-8b, the one the nightly runs.</dd>
<dt>AMX, the AMX kernel, PR #3879, head size, kv_mul, KV head</dt><dd>AMX = Intel Advanced Matrix Extensions, the matrix instructions of Granite Rapids CPUs. PR #3879 (merged 2026-09-15) added an attention kernel that uses them. The kernel runs only for models with a head size of {R("head128")} elements and {R("kvmul4")} query heads per KV head (kv_mul {R("kvmul4")}), and only when attention runs on the CPU. A KV head is one key/value head of attention that several query heads share. Head size and kv_mul are properties of a model's architecture. The dispatch gate has a third condition: the executor's activation scalar (the number type of the query buffer) must be bf16 (eligible = shape_ok and query_scalar_ok, h/tron/kernels/amx_attn_iface.hpp lines {R("line_gate_lo")} to {R("line_gate_hi")}, and amx_on = eligible and available(), h/tron/models/self_attention.hpp lines {R("line_amxon_lo")} to {R("line_amxon_hi")}, at tron commit {R("tron_head")}). The tp2 and tp4 executors store bf16, so every nightly config meets it.</dd>
<dt>deb, deb preset, TRON_AMX_DISPATCH</dt><dd>The deb is the tron package the nightly installs each night. The deb preset is the CMake build recipe that builds it. The kernel is compiled only when the CMake option TRON_AMX_DISPATCH is ON. The nightly deb does not set it. The nightly's tron therefore has no AMX code today. "The deb preset change" is the one-line change that turns the option on (branch jhan-amx-deb-preset, not yet a PR). The two packages named on this page are the nightly deb {R("b_deb_base")} and our canonical-AMX deb {R("b_deb_canon")}.</dd>
<dt>kill switch, AMX-busy, probe</dt><dd>The kill switch is the environment variable TRON_AMX_DISABLE=1. It makes a tron with AMX code take the old path. "AMX on vs off" on this page means the same binary with the kill switch off and on. AMX-busy is the CPU counter EXE.AMX_BUSY, the number of cycles in which the AMX unit worked. A probe is a {R("a_probe")} s read of that counter over all engine processes while requests run. {R("a_busy_off")} cycles in a kill-switch cell proves that the old path ran.</dd>
<dt>VNNI-K, PR #4424</dt><dd>PR #4424 changes the layout of the K cache (the stored keys of earlier tokens) to the VNNI format. It is not merged and is not part of this recommendation. Three data points of this page were measured with PR #4424 binaries: data A (both arms, one package {R("a_binary")} with the kill switch on and off), data B's {R("b_target_gain")} % arm, and data C. In data A both arms carry the VNNI K layout, so its gain is the AMX kernel alone on that layout. T1 measures the exact nightly deb and the canonical deb.</dd>
<dt>TPS, TTFT, slowest user, p05, sd</dt><dd>TPS = decode tokens per second per user. The harness measures it inside a per-config window of generated tokens (start_capture to end_capture) and averages over users and rounds. The window is token {R("cap_start")} to {R("cap_end")} for {R("configs11")} of the {R("configs12")} configs, the llama-8b config and the proposed shape among them. llama-3b captures tokens {R("cap3b_start")} to {R("cap3b_end")} after an {R("shared3b")}-token shared prefix and a {R("prompt3b")}-token own prompt (scripts/perf.py lines {R("line_3b_lo")} to {R("line_3b_hi")}). TTFT = time to first token, in ms. Slowest user = the lowest TPS sample of a config. p05 = the linearly interpolated 5th percentile of the TPS samples (testlib/perf_metrics.py), the quantity the ratchet thresholds use. sd = standard deviation.</dd>
<dt>static goals, get_goal, granite_rapids_72_rinzler</dt><dd>The static goals are the mean-TPS and slowest-user limits the Slack report applies. They live in scripts/system_ci.py, function get_goal, in two dicts (goal.tps and goal.min_tps) keyed by (model, users) per platform. granite_rapids_72_rinzler is the platform name of delphi-3bda.</dd>
<dt>ratchet thresholds</dt><dd>A second set of limits in thresholds/system_ci_perf.yaml, keyed by platform_type, model and users. Its policy uses the last {R("hist_runs")} runs (history_runs {R("hist_runs")}) and the {R("q30")} quantile (update_policy q30). The limits only move up: a new value is proposed only when the q30 support exceeds {R("ratio")} times the accepted value (min_improvement_ratio, testlib/system_ci_thresholds.py lines {R("line_ratchet_lo")} to {R("line_ratchet_hi")}). The YAML report is posted to a separate Slack channel (rhys-test) and is not the enforced verdict today. The static-goal report goes to ci-cd-notifications and is the one that fails the run (scripts/system_ci.py post_reports, add_current_threshold_compatibility, enforce_report).</dd>
<dt>FPGA attention, CPU attention, ingested, hand-written, USE_HW_ATTN, CPU share</dt><dd>Ingested models (converted by tron's ingest compiler, for example qwen-3-4b and gpt-oss) run attention on the FPGA cards by default. Hand-written models (coded by hand in tron, for example llama and mixtral) run attention on the CPU. The AMX kernel acts only in CPU attention. USE_HW_ATTN=0 is the environment variable that forces CPU attention on an ingested model. The CPU share is the part of attention the CPU still computes under FPGA attention (the first positions of each query and the newest tokens not yet copied to the card).</dd>
<dt>MoE</dt><dd>Mixture of experts: a model whose feed-forward layers are split into experts, of which each token uses a few. mixtral-8x7b is one. gpt-oss is another.</dd>
<dt>paired t, resolved, n.r.</dt><dd>Paired t = the mean of the per-round (or per-repetition) differences between two arms divided by its standard error. The prompts are fixed. Round r of one arm therefore pairs with round r of the other. A change is "resolved" when the data-B report's pre-registered rule holds: |t| at or above the 95 % limit, |change| at or above 1 %, and |change| at or above the config's 13-night band. Data A uses its own rule: {R("a_reps")} repetitions, |t| at or above {R("a_t975")} and |change| at or above 1 %. n.r. = not resolved.</dd>
<dt>13-night band</dt><dd>The night-to-night spread of a config in the nightly's own Slack reports: 2 sd of the {R("nights13")} nights 2026-09-05 to 09-17, in percent of their mean. A change smaller than the band cannot be told from a normal night.</dd>
<dt>runtron, CI harness, stand-in</dt><dd>runtron is tron's command-line benchmark tool (one process, no proxy). The CI harness is the nightly's own client code (scripts/perf.py and testlib/tps.py). A stand-in is a measurement made with rinzler and the CI harness on a part of the machine, placed like the nightly's engines, instead of the whole machine.</dd>
<dt>delphi-3bda, our half, Bill, CI lease</dt><dd>delphi-3bda is the test machine. Its first half (socket 0, 4 cards) is reserved for Bill when the marker file /bill-has-instance-0,2 exists. Our half is socket 1. The CI lease is the file /run/lock/systems-test-ci.lease the nightly holds while it runs. A whole-machine test needs Bill idle and the lease free.</dd>
<dt>ShareGPT, prune_convo</dt><dd>ShareGPT is the public set of chat conversations the harness uses as prompts (prompt_mode "sharegpt"). prune_convo (testlib/prompt.py line {R("line_prune")}) cuts a conversation to prompt_length tokens and raises "Prompt length ... too short" when the conversation has fewer tokens (line {R("line_prune_raise")}).</dd>
</dl>

<h2>1. Why today's configs cannot show AMX</h2>
<h3>Mechanism</h3>
<ul>
<li>The kernel speeds up attention only. The dense part of a decode step (streaming the model weights through the CPU) costs the same for 2 or 8 users.</li>
<li>Attention's share of a decode step grows with the number of users per engine times the context per user. More users per engine means more attention work per weight stream.</li>
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
<li><b>Data C (wedperf, 2026-09-16).</b> runtron, 8 users on one engine, llama-8b. Base = main before PR #3879 (no AMX code). Target = the PR #4424 head (AMX kernel plus VNNI K layout). Target against base: {R("c_gain256")} % at {R("c_tok256")} generated tokens ({R("c_reps256")} repetitions) and {R("c_gain1536")} % at {R("gen")} ({R("c_reps1536")} repetitions, {R("c_off1536")} to {R("c_on1536")} TPS). At {R("c_tok256")} tokens main's own change (the kernel plus PR #4400) gave {R("c_attr_main")} % and PR #4424 alone {R("c_attr_4424")} % (not resolved). So the {R("gen")}-token gain is mostly the kernel (hypothesis: no {R("gen")}-token attribution run exists). This page uses data C only for the trend: the gain grows with the context the users build up. VNNI-K is part of the target arm.</li>
<li><b>Data D (more-testing round 1, 2026-09-05).</b> rinzler plus the CI harness, 8 users on one engine, prompt {R("prompt")}, {R("gen")} tokens: llama-8b good {R("d_llama8b")} % (canonical kernel). mixtral-8x7b tp2 {R("d_mix_off")} to {R("d_mix_on")} TPS ({R("d_mix_gain")} %, sd {R("d_mix_sd")} TPS): parity. No AMX-busy probe existed yet (validated 2026-09-17), so kernel engagement is not measured in data D. qwen-3-4b tp4 with CPU attention (USE_HW_ATTN=0) {R("d_qwen")} %. An A/A repeat of that off arm differed by {R("d_qwen_aa")} % run to run, so changes under {R("d_floor")} % are not resolved by one run per arm.</li>
<li><b>Data E (p0perf, 2026-09-13).</b> Our half, the nightly's per-engine load (tp2: 2 engines x 2 users, tp4: 1 engine x 4 users), CPU attention forced with USE_HW_ATTN=0: qwen-3-4b tp2 {R("e_qwen_off")} to {R("e_qwen_on")} TPS ({R("e_qwen_tp2")} %), tp4 {R("e_qwen_tp4")} %. But CPU attention with AMX is {R("e_loss_tp2")} % (tp2) and {R("e_loss_tp4")} % (tp4) TPS against the production FPGA attention. A CPU-attention qwen config would therefore fail today's goals.</li>
</ul>
<h3>Chart 1</h3>
{legend([(C_GREEN, "data A: 2-engine stand-in, kill switch off vs on"), (C_GRAY, "data B: nightly layout, whole machine"), (C_GREEN, "data D: one engine, 8 users", "ring")])}
<div class="fig">{chart_gain_vs_load()}</div>
<p class="cap">Only the 8-users-per-engine point is large ({R("gap_pts")} points above today's load, footnote 9). The three points at 2 users per engine (today's nightly load) are all at or below {R("b_canon_gain")} %.</p>

<h2>2. Which CI models can react</h2>
<p>The kernel needs three things at once: head size {R("head128")}, kv_mul {R("kvmul4")} and CPU attention (plus the bf16 activation scalar that every nightly config has, see the glossary). The table lists the {R("configs12")} nightly perf configs against those three, with the canonical-AMX effect measured in the nightly layout (data B). Only the llama-8b change is resolved. Every other row is not resolved (n.r.). Green rows are the configs the kernel can act on in production.</p>
<div class="tw"><table>
<tr><th>config</th><th>attention</th><th>head size</th><th>kv_mul</th><th>kernel eligible?</th><th>canonical effect in the nightly layout (data B)</th><th>note</th></tr>
{cfg_table}
</table></div>
<ul>
<li><b>llama-3.1-8b</b> is the one config that meets all three conditions and reacts when the load is high enough (data A, C, D).</li>
<li><b>mixtral-8x7b</b> meets the shape conditions but measured parity at 8 users on one engine (data D). Whether the kernel engaged there is not measured: no AMX-busy probe ran on mixtral in data B or data D. Two hypotheses: (a) the kernel ran and the expert layers dominate the step, so attention stays a small share even at high load, (b) the kernel did not engage. One {R("a_probe")} s AMX-busy probe on a mixtral cell, kill switch off against on, separates them. If (a) holds, a per-layer time split would confirm it.</li>
<li><b>qwen-3-4b</b> meets the shape conditions but runs FPGA attention in production. The kernel acts only in the CPU share. Forcing CPU attention makes it react ({R("e_qwen_tp2")} %, data E) but at {R("e_loss_tp2")} % TPS against production (data E).</li>
<li>llama-3b (kv_mul {R("kvmul3")}), llama-70b (kv_mul {R("kvmul8")}), qwen-2.5 (kv_mul {R("kvmul5")}), gemma-2 and gemma-4 (head {R("head256")}) and gpt-oss (head {R("head64")}) have no kernel path. They are controls: any change on them is noise or a package effect outside the kernel. That is {R("configs_other")} configs and {R("models_other")} models [footnote 10].</li>
</ul>

<h2>3. Recommendation</h2>
<p><b>Add one config: llama-3.1-8b good tp2 at {R("new_users")} users.</b> On the existing {R("eng_tp2")} tp2 engines that is {R("new_upe")} users per engine [footnote 2], the load at which data A measured {R("a_gain8")} %. Nothing else changes: same model, same prompt {R("prompt")}, same {R("gen")} generated tokens, same TPS window.</p>
<p>The harness already runs {R("new_users")} users on {R("eng_tp2")} tp2 engines every night: llama-3.2-3b fast tp2 has nominal_users {R("new_users")} (scripts/perf.py line {R("line_3b_users")}). Its (model, {R("new_users")}) entries in get_goal (scripts/system_ci.py lines {R("line_goal_tps")} and {R("line_goal_min")}) and in thresholds/system_ci_perf.yaml (lines {R("line_yaml_lo")} to {R("line_yaml_hi")}) are the template for the new keys. That config uses a different prompt shape (shared_prompt_length {R("shared3b")}, prompt_length {R("prompt3b")}, generate_length {R("gen3b")}, capture {R("cap3b_start")} to {R("cap3b_end")}), so its duration and TPS do not transfer to the new shape.</p>
<p>This page is a recommendation. jhan decides whether to file the config after T1. The CI team decides the goals and the name.</p>
<h3>3.1 The perf.py entry</h3>
<p>A dict like the existing ones. Place it right after the existing llama-3.1-8b @8u entry. The model is unchanged, and the harness then skips provisioning (testlib/inventory.py line {R("line_prov")}, the "already provisioned" branch). The llama-3.3-70b tp2 @8u and @4u pair already works this way.</p>
<pre>{esc(perf_entry)}</pre>
<p class="cap">The "name" field appears in two places: the log line "== Benchmarking ... ==" (scripts/perf.py line {R("line_perf_name")}) and the Talos summary key f"{{config_name}}_tps @ {{nominal_users}}" (line {R("line_perf_describe")}). Results, goals and thresholds are keyed by (model, users). Because the Talos key also carries the user count, the 70b pair keeps one name for both user counts. The CI team may prefer that pattern over the _32u suffix.</p>
<h3>3.2 Goals to add</h3>
<p>Two places need a new (model, {R("new_users")}) key. The values must be set from nights on the shape itself, by the CI team's own policy. This page gives the reference values measured in the stand-in (data A, {R("a_engines")} engines, 8 users each, the PR #4424 package {R("a_binary")} in both arms):</p>
<div class="tw"><table><tr><th>arm</th><th>mean TPS</th><th>slowest sample TPS</th><th>TTFT</th></tr>
<tr><td>AMX kernel off (kill switch, PR #4424 package)</td><td>{R("a_off8")}</td><td>{R("a_slow_off8")}</td><td>{R("a_ttft_off8")} ms</td></tr>
<tr><td>AMX kernel on (PR #4424 package)</td><td>{R("a_on8")}</td><td>{R("a_slow_on8")}</td><td>{R("a_ttft_on8")} ms</td></tr></table></div>
<p class="cap">Neither row is today's deb or the canonical deb. T1 measures those two packages and also settles whether the kill-switch arm equals today's deb. The YAML entry needs p05 TPS (the 5th percentile), which is not the slowest sample. This page has no p05 value for the shape, so T1 reports it per arm.</p>
<p>scripts/system_ci.py, function get_goal, platform granite_rapids_72_rinzler:</p>
<pre>{esc(goal_entry)}</pre>
<p>thresholds/system_ci_perf.yaml, one new entry:</p>
<pre>{esc(yaml_entry)}</pre>
<ul>
<li>TTFT at {R("new_users")} users is about {R("ttft_s_lo")} to {R("ttft_s_hi")} s (data A) [footnote 3]. TTFT is shown on the Slack line but not judged (testlib/results.py marks it informational), so only the mean-TPS and slowest-user goals need values. The slowest-user goal must be set for this shape, not copied from the @8u config.</li>
<li>The provisional goals are the CI team's decision. T1 in section 5 gives whole-machine values for them.</li>
</ul>
<h3>3.3 Expected visibility and cost</h3>
<ul>
<li>Expected step: {R("a_gain8")} % = about {R("step_tps")} TPS [footnote 4] against a per-cell sd of {R("a_sd_lo")} to {R("a_sd_hi")} TPS. That is about {R("step_sd_lo")} to {R("step_sd_hi")} sd [footnote 5]. The run-to-run sd of the cell means was {R("a_rr_sd_on")} to {R("a_rr_sd_off")} TPS (derived from the three repetitions), and the @8u config's night-to-night sd over {R("nights13")} nights is {R("night13_sd")} TPS (data B reference), so the {R("step_tps")} TPS step is more than {R("step_night_sd")} of either [footnote 13]. In the Slack report the night the deb preset change lands, the new config's TPS steps up by a visible amount. In the canonical arm of data B the existing configs moved between {R("b_gptoss")} % and {R("b_70b_tp4")} %, and the only resolved change was {R("b_canon_gain")} % on llama-8b.</li>
<li>Cost: about {R("cost_min")} min per night (est.). The 8-user cells of data A took {R("a_cell_lo")} to {R("a_cell_hi")} min each, including a {R("a_probe")} s probe, on {R("a_engines")} engines. The 4-engine shape has the same load per engine. Its duration is therefore the same (est.). The perf phase would go from {R("b_perf_min")} min to about {R("perf_new")} min (est.) [footnote 6].</li>
<li>Keep the existing @8u config. It is the production-like load and the 13-night history belongs to it.</li>
</ul>

<h2>4. Shapes considered and not recommended</h2>
<div class="tw"><table>
<tr><th>shape</th><th>data</th><th>why not</th></tr>
<tr><td>mixtral-8x7b tp2 at 32 users</td><td>Data D: {R("d_mix_off")} to {R("d_mix_on")} TPS ({R("d_mix_gain")} %, sd {R("d_mix_sd")} TPS) at 8 users on one engine.</td><td>Parity is measured at the same users per engine the new llama shape uses. Kernel engagement is not measured (no AMX-busy probe, section 2). No visible step expected either way. A {R("a_probe")} s probe on one mixtral cell would settle which hypothesis holds.</td></tr>
<tr><td>qwen-3-4b with CPU attention</td><td>Data E: {R("e_qwen_tp2")} % (tp2) and {R("e_qwen_tp4")} % (tp4) gain, but {R("e_loss_tp2")} % / {R("e_loss_tp4")} % TPS against production FPGA attention.</td><td>Needs USE_HW_ATTN=0 per config. The harness cannot set that today: both provisioning paths carry only the speculation flag (build_explicit_config, testlib/inference_provisioner.py lines {R("line_bec_lo")} to {R("line_bec_hi")}, and _set_speculation, line {R("line_setspec")}). It runs {R("e_loss_tp2_abs")} % below production, and it would need its own goals. See T3.</td></tr>
<tr><td>one engine with 8 users</td><td>Data D: llama-8b {R("d_llama8b")} %.</td><td>The engine count is {R("cards")} // tp in testlib/inference_provisioner.py (line {R("line_engines")}), not a per-config setting. The 32-user shape reaches the same users per engine without a harness change.</td></tr>
<tr><td>{R("users16")} users (4 per engine)</td><td>Data A: {R("a_gain4")} % at 4 users per engine (paired t {R("a_t4")}).</td><td>Visible but small. The 32-user shape gives {R("a_gain8")} % for about the same cost.</td></tr>
<tr><td>longer prompts ({R("prompt4096")} or {R("prompt8192")} tokens)</td><td>Data F (runtron, qwen-3-4b, 8 users, canonical kernel against a binary without AMX code): {R("f_p2048")} % at prompt {R("prompt2048")}, {R("f_p8192")} % at prompt {R("prompt8192")}. Data P (prune probe, 2026-09-19): {R("fail4096")} of {R("seeds80")} conversations fail at prompt_length {R("prompt4096")}, {R("fail8192")} of {R("seeds80")} at {R("prompt8192")}.</td><td>Longer prompts give no larger gain than more users: on qwen-3-4b with runtron (data F, a different model and tool than the llama-8b harness shape) the gain at prompt {R("prompt8192")} is no larger than at prompt {R("prompt2048")}. The plain ShareGPT path cannot reach those lengths: prune_convo cuts a conversation to prompt_length and raises "Prompt length ... too short" when the conversation is shorter (testlib/prompt.py lines {R("line_prune")} to {R("line_prune_raise")}), and it does so for {R("fail4096")} of the {R("seeds80")} conversations of the 8-user config at {R("prompt4096")} and for all {R("fail8192")} at {R("prompt8192")} (data P). The shared-prefix path (shared_prompt_length) runs nightly for llama-3b ({R("shared3b")} shared plus {R("prompt3b")} own tokens) but has not been used at {R("prompt4096")} or {R("prompt8192")}. See T2.</td></tr>
</table></div>

<h2>5. Test plan</h2>
<ul>
<li><b>T1 (required before filing, about {R("t1_hours")} h of whole-machine time on delphi-3bda, needs Bill idle and the CI lease free).</b> The exact proposed shape in the nightly layout: {R("eng_tp2")} tp2 engines behind Caddy, {R("new_users")} users in one client, prompt {R("prompt")}, {R("gen")} tokens, {R("b_rounds")} rounds. Arms: the nightly deb {R("b_deb_base")} against the canonical-AMX deb {R("b_deb_canon")} (both exist). {R("t_reps")} repetitions per arm, interleaved ({R("t1_cells")} cells) [footnote 7]. T1 uniquely tests two things no run has covered: the spread of {R("new_users")} users over the engines through Caddy, and the {R("seeds_new")} ShareGPT conversations (seeds {R("seeds80")} to {R("seed_last")}) no run has used at prompt {R("prompt")} [footnote 12]. The prompt source is not a blocker: prune_convo at prompt_length {R("prompt")} succeeds for all {R("seeds320")} seeds, the shortest conversation being {R("shortest_tokens")} tokens (seed {R("seed_shortest")}, data P). T1 also settles whether the data-A kill-switch arm equals today's deb. Outputs: mean TPS, slowest sample, p05 TPS and TTFT per arm, run-to-run sd, cell duration, per-engine request counts (the Caddy spread), client CPU pressure and the count of anomalous TPS samples per config as the data-B report records them (the existing 32-user config llama-3.2-3b showed {R("b_anom_3b")} anomalous samples in one arm of data B), and the provisional goals for the CI team. Tooling: the exec/canon-ci-20260918/ driver with a configs override (a small patch that appends the new dict). Acceptance, pre-registered here: gain within {R("acc_pts")} points of {R("a_gain8")} % (that is {R("acc_lo")} % to {R("acc_hi")} %) [footnote 8] and run-to-run sd below {R("acc_sd")} TPS. Not measured until T1 runs: the 32-user llama-8b shape through Caddy with one client.</li>
<li><b>T2 (optional, only if a long-context shape is wanted).</b> The first step is already answered (data P): the plain ShareGPT path fails for {R("fail4096")} of {R("seeds80")} conversations at prompt {R("prompt4096")} and for all {R("fail8192")} at {R("prompt8192")}, so a long-context shape needs the shared-prefix path or a new prompt source. Next: the shared-prefix path at {R("prompt4096")} and {R("prompt8192")} (it runs nightly only at {R("shared3b")} plus {R("prompt3b")} tokens). Then llama-8b @8u at those prompts, {R("t_arms")} arms x {R("t_reps")} repetitions.</li>
<li><b>T3 (only if the CI team wants a CPU-attention guard for ingested models).</b> First harness support for a per-config USE_HW_ATTN. In the platformd provisioning mode the harness patches a config payload (patch_config, testlib/inference_provisioner.py line {R("line_patch")}), not environment variables. Whether platformd can pass USE_HW_ATTN to an engine is not known from the local code and must be checked first. Then qwen-3-4b tp2 @8u with CPU attention, {R("t_arms")} arms x {R("t_reps")} repetitions, with its own goals.</li>
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
<li><b>F</b> runtron prompt-length series 2026-08-31: <code>PR3879/make-sense-amx-vs-avx.html</code> (qwen-3-4b, 8 users, canonical kernel against a binary without AMX code).</li>
<li><b>P</b> prune probe 2026-09-19: testlib/prompt.py prune_convo run offline in the systems_test .venv with the tokenizer of llama-3.1-8b good (neuralmagic/Meta-Llama-3.1-8B-Instruct-quantized.w4a16, testlib/hf_models.py) over sharegpt_1000.json, seeds 0 to {R("seed_last")} at prompt_length {R("prompt")} and seeds 0 to 79 at {R("prompt4096")} and {R("prompt8192")}. The token count includes the system line the harness inserts.</li>
<li>Nightly reference: <code>exec/results/ci-mimic-20260918/reference/nightly_stats.json</code> (13-night mean and sd per config) and <code>exec/results/ci-mimic-20260918/report-v4.html</code> (the base arm of data B against the PR #4424 package).</li>
<li>Harness code cited: <code>systems_test/scripts/perf.py</code>, <code>scripts/system_ci.py</code>, <code>thresholds/system_ci_perf.yaml</code>, <code>testlib/inventory.py</code>, <code>testlib/inference_provisioner.py</code>, <code>testlib/prompt.py</code>, <code>testlib/tps.py</code>, <code>testlib/results.py</code>, <code>testlib/perf_metrics.py</code>, <code>testlib/system_ci_thresholds.py</code>, <code>testlib/hf_models.py</code> (checkout fc27f07 of 2026-09-17 at ~/workspace/ai-runs/systems_test).</li>
<li>tron code cited: <code>h/tron/kernels/amx_attn_iface.hpp</code> and <code>h/tron/models/self_attention.hpp</code> at commit {R("tron_head")} (the merged PR #3879 head, worktree ~/workspace/tron-amx).</li>
</ul>

<h2>Footnotes: arithmetic of the derived numbers</h2>
<ol class="fn">
<li>({R("a_off2")} - {R("night13_mean")}) / {R("night13_mean")} = 0.0132 = {R("night13_gap")} %.</li>
<li>{R("eng_tp2")} engines x {R("new_upe")} users per engine = {R("new_users")} users. Engine count: {R("cards")} cards // tp2 = {R("eng_tp2")}.</li>
<li>{R("a_ttft_on8")} ms = {R("ttft_s_lo")} s and {R("a_ttft_off8")} ms = {R("ttft_s_hi")} s (rounded to 0.1 s).</li>
<li>{R("a_on8")} - {R("a_off8")} = {R("step_tps")} TPS. {R("step_tps")} / {R("a_off8")} = 0.1293 = {R("step_pct")} %.</li>
<li>{R("step_tps")} / {R("a_sd_hi")} = 22.7, about {R("step_sd_lo")} sd. {R("step_tps")} / {R("a_sd_lo")} = 41.2, about {R("step_sd_hi")} sd.</li>
<li>{R("b_perf_min")} min + {R("cost_min")} min (est.) = {R("perf_new")} min (est.). The {R("cost_min")} min is the {R("a_cell_lo")} to {R("a_cell_hi")} min per 8-user cell of data A, rounded up.</li>
<li>{R("t_arms")} arms x {R("t_reps")} repetitions = {R("t1_cells")} cells. {R("t1_cells")} x {R("cost_min")} min = {R("t1_bench_min")} min of benchmark time (est.). The rest of the {R("t1_hours")} h is deb installs, engine restarts and provisioning (est.).</li>
<li>{R("step_pct")} - {R("acc_pts")} = {R("acc_lo")} %. {R("step_pct")} + {R("acc_pts")} = {R("acc_hi")} %.</li>
<li>Chart 1 gap: {R("step_pct")} - 0.2 = 12.7 percentage points ({R("gap_pts")} points) between 8 and 2 users per engine (data A).</li>
<li>{R("configs12")} configs - {R("kernel_configs")} with a kernel path by shape (llama-8b, mixtral, qwen-3-4b tp2, qwen-3-4b tp4) = {R("configs_other")} configs without one. {R("models9")} distinct models - 3 with a kernel path by shape (llama-8b, mixtral, qwen-3-4b) = {R("models_other")} models without one.</li>
<li>tp2 configs at {R("night_users")} users: llama-8b, 70b tp2 @8u, mixtral, qwen-2.5, qwen-3-4b tp2, gemma-2, gemma-4 = {R("configs_tp2_8u")}, that is llama-8b and {R("configs_tp2_8u_other")} others. The tp4 configs at 8 users (qwen-3-4b tp4, gpt-oss) run 8 users on {R("eng_tp4")} engines = 4 users per engine. The 70b tp2 @4u and tp4 @4u configs run 4 users. llama-3b runs {R("new_users")}.</li>
<li>ShareGPT seed = round x n_users + user (testlib/tps.py line {R("line_seed")}). {R("b_rounds")} rounds x {R("night_users")} users = {R("seeds80")} seeds (0 to 79) for the 8-user config and for each data-A client. {R("b_rounds")} rounds x {R("new_users")} users = {R("seeds320")} seeds (0 to {R("seed_last")}) for the proposed shape. {R("seeds320")} - {R("seeds80")} = {R("seeds_new")} conversations no run has used at prompt {R("prompt")}.</li>
<li>Run-to-run sd of the 8-user cell means (data A): kernel off {R("a_off8_r1")}, {R("a_off8_r2")}, {R("a_off8_r3")} TPS, sample sd = {R("a_rr_sd_off")} TPS. Kernel on {R("a_on8_r1")}, {R("a_on8_r2")}, {R("a_on8_r3")} TPS, sample sd = {R("a_rr_sd_on")} TPS. {R("step_tps")} / {R("night13_sd")} = 17.4, more than {R("step_night_sd")} night-to-night sd. {R("step_tps")} / {R("a_rr_sd_off")} = 25.2, more than {R("step_night_sd")} run-to-run sd.</li>
<li>{R("step_pct")} / 3.9 = {R("step_vs_gptoss")}: the proposed bar against the longest existing bar (gpt-oss, {R("b_gptoss")} %).</li>
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
