---
name: merge-4737-into-4424
description: "2026-10-08/09: PR 4737 (issue 4500 row-major tail block + hardware-attention policy) merged onto the PR 4424 head ba69cb513e as 9d5c7a389b (was 3723bf601a before the check_marks test fix; typed-owner port of the raw helpers; branch jhan-amx-vnniK-i4500m in ai-runs/tron-vnnik-i4500m); 3bda chain exec/merge4737-20261008/; whole-machine campaign exec/pr4424ci-20261009/ (14 nightly configs + qwen 8k sw-attention cell, base = nightly deb 2026.10.08-be0d5565 vs target deb) after the 2026-10-09 nightly, pre-check exec/merge4737-20261008/precheck.sh; status + traps inside"
metadata:
  node_type: memory
  type: project
  originSessionId: 19680312-df5d-4bfa-9f32-ac8dc69334d0
  modified: 2026-10-08T23:34:07.841Z
---

Request (jhan 2026-10-08 ~23:00 UTC, ultracode, cwd PR3879/new-PRs/merge-4737-2-4424): merge PR 4737 to PR 4424
(save_k_helper calls need replacing), then thorough machine tests (correctness + perf): the 12 nightly CI models plus
qwen3-4b tp2 at prompt 8192 with software attention; A/B = plain main vs the same main + 4424; expect decode TPS and
TTFT gains on llama-3.1 and qwen3-4b (sw attention), no change elsewhere (mixtral maybe a little), no meaningful memory
increase. If results are as expected: update the PR description from "Words used here" onwards; propose changes to the
first 4 sections in chat only.

MERGE (done 2026-10-08 23:5x UTC): worktree ~/workspace/ai-runs/tron-vnnik-i4500m, branch jhan-amx-vnniK-i4500m =
9d5c7a389b (amend of 3723bf601a: the first 3bda chain failed t_llama_unit at the save_k case because 4737's second
check(before) after convert_pending_k_blocks re-ran the fold's mark loop; fixed by a check_marks lambda called once
per section) (first parent ba69cb513e = jhan-amx-vnniK head, second parent bb32a80774 = PR 4737 head; made with
commit-tree so the 4424 line stays first-parent). 28 conflict hunks in 8 files; diff vs ba69cb513e = 10 files
1447+/109-. Port of 4737's raw helpers onto the typed K owner (PR 4557 port): h/tron/tensor/k_vnni.hpp gains
row_major_row (typed row view of a row-major block's token), store_row_major, load_row_major, block_to_vnni,
block_to_rows, PANEL_ROWS_4, BLOCKS_PER_PAGE_MASK_0XF, block_bit, offset_bit and Note [Row-major tail block] (moved from
the kernel header, which keeps only qk_group). page::set_k_row/get_k_row follow the block's recorded layout;
page::set_k_block stores full blocks only (the `present` mask is gone: runs shorter than a block go row-major);
k_row_if_row_major returns k_row_view (invalid = converted block); copy_storage_slot converts through row-major rows;
self_attention keeps page::k_packed in a std::optional (lambda pattern, like `keys`) and scores row-major tail tokens
with the dotter via row_major_row; full.hpp returns the row-major row in place. save_k_helper: 0 mentions (the fold's
save_k(worker_ix) form from the auto-merge). Shared-file spelling kept lower_snake (k_store_block; t_llama_unit
constants pre_saved_rows, no_kv_token, operation_uses_hw, other_operation, /*converted=*/). Tests ported: plane bytes
checked through at() (the VNNI index map is a bijection, so comparing at(tok,d) over all tokens compares all bytes;
block c's panels = at() of tokens 16c..16c+15) and row_major_row; t_llama_unit reads fill_random's bytes through the
inverse index map (`element` lambda) so both builds score the same K instance. Scripts: session scratchpad
resolve.py (steps 1-8) + resolve2.py (kernel header cleanup, the two test files). Verified on claude-box: zig-clang 19
syntax-only (ai-runs/lcheck/lcheck.sh + EXTRA=-DTRON_K_VNNI copy) of t_k_vnni_layout, t_amx_dispatch_dtype,
t_llama_unit in both layouts = 0 errors; clang-format 19.1.7 (uvx) clean on the 10 files (nix is GONE on claude-box
again 2026-10-08).

MACHINE FACTS 2026-10-08 23:0x UTC: installed deb 2026.10.08-be0d5565 = exactly the main commit PR 4424 is synced to
(saved as /var/tmp/jhan/pr4424ci-20261009/nightly.deb, rinzler sha aebe9855...); rinzler@0,1 serving (2 tp4 engines,
one per socket, HugePages_Free 0); Bill marker present, Bill idle; platformd 0.11.0; nightly 03:46-13:30 UTC, failing
daily (conclusion failure 10-05..10-08). The nightly now has 14 perf configs (12 + llama-8b 32u@4096 "AMX benchmark" +
Muse-Glimmer-30B tp4). The PR's deb preset does NOT set TRON_K_VNNI=ON (only TRON_AMX_DISPATCH): the target deb adds it
locally (build-target.sh), and the PR needs a decision (preset line like PR 4505, or the layout never ships).
systems_test checkout ai-runs/systems_test was at e4727d5 (09-21) with an uncommitted prompt.py patch; origin/main
14f0ce4 rewrote prompt handling (prepare/eligible), tps.py worker handling, perf.py (14 configs).

3bda CHAIN exec/merge4737-20261008/build-test.sh (fork of savek2: A VNNI build + 6 tests + kill switch + plugin grep in
/var/tmp/jhan/tron-m4737 -> runtron.m4737; A2 ingest cabal; F clang-format of the 10 files + diff --check; B row-major
build tron-m4737rm) relaunched 23:48 UTC pid 849893 for 9d5c7a389b (first run 23:29 UTC failed-A on the test interaction above), results exec/results/merge4737-20261008/ (all.done), log
exec/logs/merge4737-20261008-build-test.log. PRE-CHECK exec/merge4737-20261008/precheck.sh (launch-precheck.sh,
NOT_BEFORE 2026-10-09T13:00Z): serving-down, host suite (i4525 host-suite.sh), smokes (sync4424-20261002/smoke.sh:
cpu p1024 base/head/new/new2/newoff, fpga p1024, cpu p8192; MUST_MATCH new:new2 newoff:new; head = runtron.savek2
45e6bb266d, base = runtron.main1007 be0d5565b3), serving-up; holds /var/tmp/jhan/pr4424ci-precheck.running, which the
perf campaign's wait loop honours. CAMPAIGN exec/pr4424ci-20261009/ (agent-written: build-target.sh COMMIT, dut.sh,
st_ci_perf.py ported to systems_test 14f0ce4 with memory snapshots, configs.py -> sw8k.json/nightly14.json,
campaign.sh ABBA = base/target/target/base passes x (14 configs + sw8k cell), summarize.py, README.md); results
exec/results/pr4424ci-20261009/<tag>/perf.json.

STATUS 2026-10-08 23:5x UTC: chain all.done = ok at 9d5c7a389b (VNNI: t_k_vnni_layout 1041256/10, t_amx_dispatch_dtype
2137/1, t_amx_numerics 4621/5, t_llama_unit 259020/64, t_heterogeneous_scheduler 2783/3, t_phase1_integration 2124/64,
kill switch ok; ingest rc=0; clang-format/diff-check rc=0; row-major: t_llama_unit 258911/64, t_k_vnni_layout 1039202/10).
PUSHED: jhan-amx-vnniK ba69cb513e -> 9d5c7a389b (PR 4424 head, MERGEABLE, draft) and jhan-amx-vnniK-i4500 -> 9d5c7a389b
(GitHub marked PR 4737 MERGED 23:57:46Z); local worktrees tron-i4500 + tron-VNNIed-K fast-forwarded. Deb build launched
23:58 UTC (pid 1839020, log exec/logs/pr4424ci-20261009-build-target.log, OUT /var/tmp/jhan/pr4424ci-20261009);
precheck launched 23:58 UTC (pid 1839085, sleeps to 13:00Z; log exec/logs/merge4737-precheck-chain.log, results
exec/results/merge4737-precheck/, runtron cells exec/results/m4737-E-cpu/). Deb built 00:14 UTC: tron_2026.10.09-667b2ce5-jhan-pr4424ci-target (head_sha 667b2ce5 = 9d5c7a389b + local preset commit;
rinzler sha 240d9cbc...; 126 AMX tile insns, 4 vnni strings). CAMPAIGN LAUNCHED 00:15 UTC on claude-box (pid 2929924, log
exec/logs/pr4424ci-20261009.log, status exec/results/pr4424ci-20261009/.status; knobs NOT_BEFORE 13:00Z DEADLINE_START 19:00Z
PASS_DEADLINE 2026-10-10T00:30Z DRIVER_END_BY 02:05Z; PASSES base target target base; .done/.done-with-failures at the end;
summary.md by summarize.py). Expected timeline: lease clears ~13:20-13:35 UTC, precheck ~1.5 h (serving-down, host suite,
smokes, runtron cells), campaign ~8 h -> ends ~23:30-00:30 UTC; restore = nightly deb of 10-09 reinstalled, serving up,
Bill marker released (campaign takes it with bill-share take; refused if Bill active).

**How to apply:** check exec/results/merge4737-precheck/precheck.done + steps.txt, then exec/results/pr4424ci-20261009/
.status, summary.md, outcome.txt. Then PR body (re-fetch first, [[pr-body-refetch-before-edit]]; rules
[[pr-description-no-history]], [[pr-body-pending-measurement-subsection]], [[flag-only-decision-changing-facts]]) and
the protected-section proposal in chat (Short version + section 4 describe masked partial-block stores and the 64-line
decode scatter, both gone with 4737). Related: [[pr4812-merge-4774-onto-4424-head]], [[sync-4424-main-20261007]],
[[i4500b-policy-campaign]], [[pr4737-review-response]], [[ci-mimic-20260918-campaign]], [[q4b-fpga-20260921-campaign]],
[[3bda-shared-with-bill]], [[platformd-011-restarts-stopped-units]].

CHECKPOINT 1 (2026-10-09 15:1x UTC): RACE. precheck.sh and campaign.sh both waited for the same lease event; the campaign
tests the pre-check marker once, right after the lease wait, and passed before precheck.sh (lease wait with the same
600 s grace, then a 120 s poll) created it. Campaign: lease ~13:3x, serving-down 13:40, base-pass1 started 13:42 UTC,
10 of 14 configs done at 15:07 (pace ~85 min per full pass). precheck.sh: serving-down failed on the campaign's traffic,
its host-suite.sh is blocked on the campaign flock; the classifier REFUSED pkill ("Interfere With Workloads"), so it
stays: after the campaign it will run the host suite with serving up (expect the 6 heap_setup failures, environmental),
then the smokes (lib-guard takeover takes serving down) and the runtron cells until their 02:00/01:30 UTC deadlines.
precheck2.sh (same steps, order smokes -> cells -> host suite, past_end guards, waits for the campaign end marker and
for precheck.sh to be gone) launched 15:2x UTC with NOT_BEFORE=2026-10-10T13:00Z END_BY=2026-10-11T01:40Z: it completes
whatever tonight leaves missing (smoke.sh skips arms with tokens, the runtron campaign.sh resumes, the host suite reruns
with serving down). LESSON: create a hand-off marker BEFORE waiting for the shared event, not after; or make the waiting
campaign re-test the marker right before its first state change.

CAMPAIGN DONE 2026-10-09 22:02 UTC (8/8 tags, no problems; restore = nightly deb 2026.10.09-26b6df7d, config.env 0, 4 engines up,
Bill marker released; summary exec/results/pr4424ci-20261009/summary.md + summary.json). Results (target vs base, n = 2 pass pairs,
paired t over 20 rounds): llama-8b 32u@4096 +4.8 % TPS (t 39) resolved, TTFT +12 ms n.r.; llama-8b 8u@1024 -0.3 % n.r.; sw8k cell
(qwen3-4b tp2 8u p8192 USE_HW_ATTN=0) +7.6 % TPS (t 39), TTFT -150 ms (-1.2 %, t -9) both resolved; Muse-Glimmer-30B tp4 +2.4 % TPS,
TTFT -118 ms (-3.2 %) resolved; llama-3.2-3b 32u -1.4 % TPS (t -16.6) RESOLVED LOSS (kv_mul 3: VNNI layout on, AMX kernel not
eligible -> AVX reader instead of the dotter = the kv_mul open item); qwen3-4b FPGA tp2 -0.9 % / tp4 -0.4 % n.r. (issue 4500 loss
gone within noise), TTFT -8/-12 ms n.r.; mixtral -0.1 %, 70b/qwen-2.5/gemma-2/gpt-oss/gemma-4 within +-0.8 % n.r.; memory: VmHWM
sum differs by <= 81 MiB (0.3 %) on any config. Base passes within 1.7 % of the same-day nightly (deb 2026.10.09-26b6df7d, run
37880831014) on every config. base-pass1 had 54 "anomalous tps" lines (42 in the 32-user llama-3b config = its per-round ramp,
also in the nightly; both base passes agree within 0.4 TPS).
PR 4424 BODY PATCHED 2026-10-09 22:12:51Z (scratchpad new-body.md = assemble_body.py over live-body-4424.v2.md; protected
lines 1-28 identical after CRLF normalization; stored body differs from the file by gh's trailing newline only): Words rows
(shared block save rewritten; base; dense page; + row-major tail block, converted block, hardware-scored operation, nightly CI /
perf configs, TTFT / paired t / resolved, VmHWM), The changes (tail-block operations, K layout state, save_k row-by-row + pending
queue, dense gate, dotter for tail blocks, staging in place, tests), Measurements (nightly-config table 14 + sw8k, reading;
PENDING subsection "runtron cells against main at this head (running)"; PR #3879 table kept with provenance; the 37064d72b2
runtron rows DELETED), Verification (unit tests at 9d5c7a389b; PENDING subsection "Host test suite and token identity at this
head (running)"), Open items (Stacked PR deleted; kv_mul item carries the llama-3b -1.4 %; kill-switch item + tail-block sentence;
NEW deb-preset item; NEW cost-rows-refresh item). Protected-section proposal (scratchpad protected-proposal.md) given in chat only.
TODO (cron 2026-10-10 16:23 UTC): fill the two pending subsections from exec/results/merge4737-precheck/ (precheck.sh runs
tonight after the campaign: host suite with serving up = heap_setup failures expected, then smokes + cells until 01:30-02:00 UTC;
precheck2 tomorrow 13:00Z+ completes the rest), then drop "(running)". Stray Talos row "Untitled Session"
012d733e-c36e-11f1-9160-7dc18ea6a739 created by the agent's import check (told jhan).

PRECHECK (first chain) DONE 2026-10-09 22:37 UTC, right after the campaign (results exec/results/merge4737-precheck/, cells
exec/results/m4737-E-cpu/): smokes all ok: new==new2, newoff==new; new vs base (main be0d5565b3) IDENTICAL 256/256 under CPU
attention at p1024 and p8192 (the #4444 divergence vs main is gone under CPU attention: decode rows go into a row-major block the
dotter scores, as on main); under FPGA p1024 new vs base differs at token 52 (same as the previous head; new == head there);
new vs head differs at 52 under CPU p1024 (head read the tail block with the VNNI reader). Runtron cells (3 reps, CPU attention,
8 users): p1024 new 83.14 vs base 79.10 TPS (+5.1 %), TTFT 3.133 vs 3.177 s (-45 ms, inside the 0.15 s floor); p8192 18.87 vs
17.10 (+10.3 %), TTFT 52.040 vs 52.584 (-543 ms, beyond band 0.19 s). Host suite ran with serving UP: 87 passed / 1 skipped /
7 failed (t_proxy_llama31 venv + 6 heap_setup: t_pos_lifecycle t_permutation t_bf16 t_safetensors t_alloc t_heap) = environmental;
precheck2 (pid 1297200, NOT_BEFORE 2026-10-10T13:00Z) reruns it with serving down (smokes/cells skip, already done). Machine
restored 22:37 UTC (4 engines up, marker present). PR BODY PATCHED AGAIN 22:4x UTC (new-body-2.md): runtron subsection filled
and dated, token-identity rows filled, host suite row pending, kill-switch item updated (identical to main under CPU attention).
Cron 2026-10-10 16:23 UTC: fill the host suite row from precheck2 and drop "running" from that heading.

DONE 2026-10-09 23:1x UTC: precheck3.sh (precheck2 + Bill marker take/release, NOT_BEFORE now) ran 23:05-23:10 UTC with
serving down: host suite 93 passed / 1 skipped (t_proxy_lib) / 1 failed (t_proxy_llama31, venv) = main's set; chain verdict
"failed" only because test-host rc=2 on that known failure. Machine restored (4 engines, nightly deb 2026.10.09-26b6df7d,
config.env 0, marker present). precheck2 tomorrow instance KILLED (kill -TERM allowed this time). PR BODY PATCHED a third time
23:1x UTC (new-body-3.md): host-suite row + heading filled, no "pending"/"running" left; protected lines 1-28 identical.
Everything of the request is done except the two decisions for jhan (deb preset line; protected-section wording proposal).
Scripts: exec/merge4737-20261008/{build-test.sh,launch.sh,precheck.sh,precheck2.sh,precheck3.sh,launch-precheck*.sh},
exec/pr4424ci-20261009/ (campaign). Results: exec/results/{merge4737-20261008,merge4737-precheck,m4737-E-cpu,pr4424ci-20261009}.

2026-10-09 23:2x UTC (jhan: "yes, add dev preset, and keep reminding me the protected-section wording until I
specifically stop you"): commit 0a5334ccb6 on jhan-amx-vnniK = CMakePresets.json deb preset "TRON_K_VNNI": "ON" after
TRON_AMX_DISPATCH + README.ci.md paragraph (deb preset sets it; layout independent of AMX, only the reader differs); pushed;
PR 4424 head 0a5334ccb6 MERGEABLE. PR body patched (new-body-4.md): setup sentence names the preset line, CMake bullet
mentions the deb preset, the deb-preset open item removed, Verification provenance "head 0a5334ccb6 adds the preset line".
STANDING REMINDER: the protected-section wording proposal (see [[remind-protected-section-proposal]]).
