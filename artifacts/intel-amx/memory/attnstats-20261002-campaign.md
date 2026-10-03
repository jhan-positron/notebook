---
name: attnstats-20261002-campaign
description: "2026-10-02 campaign (jhan request 2026-10-01 23:5x UTC): tron main + TRON_AMX_DISPATCH=ON, TRON_ATTN_STATS=1, arms amxon / amxoff (TRON_AMX_DISABLE=1), llama-3.1-8b-good tp2 (CPU attention), gpt-oss-120b tp4 + qwen3-4b tp2 (FPGA attention) + the other attention mode as controls, prompts 1024/8192, 8 users; chain exec/attnstats-20261002/ waits NOT_BEFORE 13:00Z then the lease; output attn-stats-compare.md (gen_compare.py first version, plain-English pass after)"
metadata:
  node_type: memory
  type: project
  originSessionId: 81e65d05-6ef1-4e3c-ada7-bca5950d03db
  modified: 2026-10-02T00:11:58.744Z
---

Request (jhan 2026-10-01, ultracode): queue a machine test on delphi-3bda after the nightly CI of 2026-10-02:
TRON_ATTN_STATS=1; llama-3.1-8b-instruct-good-tp2, gpt-oss-120b-tp4, qwen-3-4b tp2; main latest with AMX enabled
(build option TRON_AMX_DISPATCH, env TRON_AMX_DISABLE unset) and disabled (TRON_AMX_DISABLE=1); generate
attn-stats-compare.md (plain English, verbose) comparing the AMX/AVX/FPGA attention stats between the arms, to
summarize the AMX involvement in attention for: AoF (gpt-oss, qwen3), pure software attention (llama-3.1),
fitting shape (llama, qwen3) vs non-fitting shape (gpt-oss: 64 query heads / 8 KV heads / head size 64).

Decisions taken (assumptions stated to jhan):
- ONE build of main (TRON_AMX_DISPATCH=ON, cross-avx512, ingest models ON) in /var/tmp/jhan/tron-main1002,
  runtron.main1002; arms differ only by TRON_AMX_DISABLE=1. Not built: a TRON_AMX_DISPATCH=OFF binary.
- runtron cells on our half (not the rinzler + CI harness): the exit report prints at process end; runtron names:
  llama-3.1-8b-instruct-good-tp2, ingested-gpt-oss-120b-tp4 (placement tp4 = --instance 1,2, 4 cards),
  ingested-qwen-3-4b-instruct-2507-tp2. Prior runtron runs of all three exist (wedperf-20260916: gpt-oss tp4 both
  attention modes, ~100 s per run at prompt 1024; load ~80 s).
- Attention mode per the request's situations: llama cpu (USE_HW_ATTN=0), gpt-oss + qwen fpga (USE_HW_ATTN unset);
  controls = the other mode for each model (gpt-oss cpu, qwen cpu, llama fpga). Prompts 1024 and 8192, 8 users,
  256 tokens, --dont-stop, REPS 1 (counters are position-determined; TPS single-rep = informational).
- main at script time: 9c88327931 (contains PR #4596 attn_stats.hpp at 441e81178b); chain step F fetches
  origin/main on 3bda at 13:00Z (ls-remote works there) and falls back to 9c88327931.

Scripts: exec/attnstats-20261002/{chain.sh, campaign.sh (fork of attnstats-20260924/campaign.sh: attn+len per cell,
one binary, arms = environments, per-run FUSE leaf snapshots in leaves/<run>/), gen_compare.py, launch.sh, README.md}.
Results: exec/results/attnstats-20261002/; logs exec/logs/attnstats-20261002-chain.log, attnstats-20261002.log.
Report: RES/attn-stats-compare.md copied to PR3879/new-PRs/new-counters/attn-stats-compare.md by step R.
Kill-switch header fact: amxoff runs print "amx_available":false in the [attn-stats] model line (09-25 sample).

**How to apply:** after the chain (expect done ~15:30-16:00 UTC 2026-10-02): read exec/logs/attnstats-20261002-chain.log,
exec/results/attnstats-20261002/{rt-results.txt,exit-reports.txt}; regenerate with gen_compare.py if runs were resumed;
then the plain-English pass on attn-stats-compare.md (facts, definitions, one claim per sentence) and the memory update.
Related: [[attn-stats-pr-implementation]], [[aof-amx-question-20260925]], [[attention-stats-claude-page]],
[[3bda-shared-with-bill]], [[platformd-011-restarts-stopped-units]], [[3bda-nightly-rinzler-cleanup]].

STATE 2026-10-02 01:0x UTC: build-only pass launched on 3bda (chain pid 2347828, STEPS="F A", fetched main 9c88327931,
building /var/tmp/jhan/tron-main1002 with `--preset native -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON`; the
cross-avx512 preset was REMOVED from main 2026-09-30 by 8d64eeed81, so every old CONF string with it fails to configure).
Session crons: 01:55Z check the build and launch the morning chain (`NOT_BEFORE=2026-10-02T13:00:00Z STEPS="F A D R"
bash exec/attnstats-20261002/launch.sh`); 16:07Z report pass. If the session died, jhan runs launch.sh by hand.
Verified facts for the report (fact sheet in the session scratchpad, 83 claims survived 2 refuters): shape_ok = head 128
AND kv_mul 4 [amx_attn_iface.hpp:148-150]; gpt-oss = 64/8/64, 36 layers, 18 full-attention FPGA layers (hw_slots 18) +
18 sliding-window (128) software layers; llama has no force_hw_attn -> USE_HW_ATTN unset = CPU attention (control cell
uses USE_HW_ATTN=1 = attn fpga1); exit report = 7 lines per model state (header, 2 classes x totals/forwards/per-layer);
per-layer FPGA field is per query (x n_kv_heads for the software scale); nightly lease cleared 12:56/13:00/13:27Z on
09-29/09-30/10-01; HugePages_Free = 0 while production engines run (campaign's hugepage wait sits after the takeover).
Review (wf_0fd83adc-336, 35 confirmed + critic) applied: exact `ok` resume compare, POLL_S 1 s, serving-taken-down.marker +
chain serving_restore, build pgid killed on TERM/EXIT, step A retry on lease kill, objdump to file + TRON_ATTN_STATS gate,
stale FUSE unmount before each run, hugepage wait, report wording (avx_full_page, fitting shape, T2/T4, card layers).
UPDATE 2026-10-02 01:55 UTC: build pass DONE (01:00-01:15Z, 14 min fresh build of 9c88327931, runtron.main1002 has 86 AMX
tile instructions and the TRON_ATTN_STATS strings). Morning chain LAUNCHED (pid 2482707, STEPS="F A D R", waiting for
NOT_BEFORE 13:00Z, then the lease; step A rebuilds only if main moved overnight). Report pass cron at 16:07Z (session-only).
UPDATE 2026-10-02 02:4x UTC (jhan): gpt-oss always runs AoF -> cells gptoss-8u-p1024-cpu and gptoss-8u-p8192-fpga DROPPED
(10 cells, 20 runs). The waiting chain was stopped (TERM is honoured only after the current `sleep 60`) and relaunched.
Open with jhan: gptoss-8u-p8192-cpu falls under the same rule; kept until jhan says.
FINAL CELLS (jhan 2026-10-02 02:5x UTC): 6 cells x 2 arms = 12 runs: l8b-8u-p1024-cpu, gptoss-8u-p1024-fpga, q3-4b-8u-p1024-fpga,
q3-4b-8u-p1024-cpu (control), l8b-8u-p8192-cpu, q3-4b-8u-p8192-fpga. Dropped by jhan: all gpt-oss CPU cells ("we always use AoF
for gptoss"), gpt-oss p8192, llama USE_HW_ATTN=1 cells ("llama is not AoF"), qwen CPU p8192. Chain relaunched after the edit.
RESULTS 2026-10-02 (chain DONE 14:15Z, main dd0f942c75, 12/12 runs, 0 HBM warnings, serving restored 14:12Z; report
PR3879/new-PRs/new-counters/attn-stats-compare.md = prose + gen_compare tables; generator-only copy in .gen-v1.bak):
- CPU attention (fitting shapes): AMX scores 96.5 % (llama p1024) / 97.3 % (qwen p1024) / 98.9 % (llama p8192) of decode
  K tokens; kill switch: TPS -2.8 % / -10.4 % / -13.8 %, TTFT +4.7 % / +25 % / +128 % (34.6 -> 78.8 s at p8192).
- FPGA attention: 0 AMX visits in decode for gpt-oss and qwen (both arms identical, TPS within +0.2..+0.9 %); qwen p8192
  prefill 7,077,888 AMX visits = 0.6 % (copy-lag state 6, same as 09-25).
- gpt-oss (64/8/64, non-fitting): 0 AMX by construction; CPU scores 10.2 % of decode K tokens: 18 sliding-window layers
  2,097,152 per layer (= 2048 jobs x 8 heads x 128 window), card layers 40,960 per layer (= 2.5-token tail); 299,520
  full-page AVX visits per decode run are what a 64/8 kernel could take (25 % of its AVX visits, ~50 % of its AVX K tokens).
- Kill-switch identity holds in all 12 class rows. Only cross-arm counter difference: gpt-oss prefill empty visits 16,218 vs 16,362.
REPORT REVISION 2 (2026-10-02 17:4x UTC): verification wf_ae2765d2-062 (177 claims, 2 verifiers each, critic): 6 wrong + 30
imprecise applied; report rebuilt by exec/attnstats-20261002/assemble.py from final_prose.md + the generator tables (previous
revision kept as .prev, generator-only as .gen-v1.bak). Facts corrected there worth remembering: binary has 98 AMX tile
instructions (chain.sh regex counts 86: no tilezero); llama/gpt-oss tokenizers add a BOS token -> 1,025-token prompts, a
one-token 9th prompt forward classed decode_like (256 forwards, 2,048 jobs) and 7 prefix-cache-reused BOS tokens (8,185
prompt jobs); llama kill-switch runs record 4-11 % MORE attn_jobs than amxon (cause unmeasured); gpt-oss prefill empty visits
sit only in the sliding-window layers (901 per even layer, 896 consistent with a window-gate off-by-one at
self_attention.hpp:1612 vs :1927); under AoF qwen's card scores exactly the K tokens the kernel scored under CPU attention
(1,056,964,608 prefill, 675,357,696 + 1,465,344 tail decode); llama ready-pass AVX component (1 visit per job/head/layer,
8.9 keys) unexplained; the campaign waited 13:45-13:59Z on another session's campaign lock after the takeover.
REPORT REVISION 3 (2026-10-02 18:4x UTC, FINAL): second verification wf_b8d75c26-c80 (175 claims on the changed prose, 45 disputed,
critic): applied. New verified facts: (1) under AoF qwen's card scores 2.5 % MORE decode K tokens than the kernel did under CPU
attention (675,357,696 vs AMX 658,243,584): the partial pending page down to the last complete GOF moves from the AVX loop to the
card; prefill is an exact swap. (2) llama amxoff runs have more attn_jobs because recommend_n_main_helpers() picked 24 attention
workers in 255/256 forwards vs 13/256 in amxon (model.hpp:2068-2103) - a split effect, not more work. (3) llama's 1-key ready AVX
visits = users 2-8 scoring the shared BOS page (prefix cache, token-level), their branch pages off the 64-token grid but dense;
predicts ready AMX 9,102,336 = 256 x (4,224 + 7 x 4,476) exactly. (4) llama decode p1024 absorbs ~2/3 of the extra attention time
outside the critical path (two minibatches per forward, max_minibatches=-1 llama.hpp:183) while qwen (one minibatch) passes it 1:1.
(5) qwen p64 AoF (09-25) put 8.5 % of decode K tokens through the kernel: "AoF = 0 AMX" holds for prompt >= 1024, cold cache.
(6) T4/T1 = 83-96 % (not 88-95 everywhere). TRAP: assemble.py replaced a literal "GEN_TABLE_1" inside section 9 prose -> now
whole-line placeholders only. Short version cut to 3 sentences + a detail list (rule 5). Files: attn-stats-compare.md (final),
.gen-v1.bak (generator only); prose source final_prose.md (+ .rev2 = before pass 2).
