# Reader report: the measurement records and bodies behind PR-4's claims

## Short version

Every record the task names exists and was read, except that q4b-fpga-20260921 holds no VNNI arm and i4500c-20260930 holds no TPS table. The "-3.8 % / -11.8 %" loss of split-plan.md comes from i4500fix-20260928 (one rinzler engine, 2 users at tp2 and 4 users at tp4, not 8 users on one engine), and the "-0.9 % / -0.4 %" recovery comes from pr4424ci-20261009 (whole machine, 8 users spread over 4 tp2 engines or 2 tp4 engines), so the two halves of that claim have different setups, bases and dates. The unit-test deltas of T (the tail-block patch) are measurable per binary for t_k_vnni_layout (+5 cases), t_amx_dispatch_dtype and t_llama_unit, but the t_llama_unit sum is an estimate because T adds sections to a test case that PR-3 rewrote.

## Words used here

- PR 4424: positron-ai/tron pull request "store the K cache of 128-dimension heads in the AMX VNNI layout", branch jhan-amx-vnniK, head 0a5334ccb6. tron = the inference program. runtron = its command-line tool. rinzler = the production server.
- The stack: PR-1 #4868 (jhan-vnnik-1-layout, 82d05e94be), PR-2 #4887 (jhan-vnnik-2-amx, 0ee8671d35), PR-3 #4898 (jhan-vnnik-3-shared-save, 80bce9a08d), PR-4 (jhan-vnnik-4-tail-block, to be built).
- T: the patch handoff-material/ref/T-4737-merge.diff (ba69cb513e..9d5c7a389b, the content of PR 4737: the row-major tail block and the hardware-attention policy). B: handoff-material/ref/B-preset.diff (9d5c7a389b..0a5334ccb6, the deb preset line and the README paragraph).
- K cache: the stored key vectors of past tokens. VNNI layout: the pair-interleaved operand layout of the AMX tile multiply. Row-major K: one row of 128 values per token. Block: 16 consecutive tokens of a 64-token KV page. Plane: the packed K storage of one page and one KV head.
- Scatter store (the per-row store): the pre-T decode store that writes one token's 64 dimension pairs into 64 different 64-byte cache lines. Row-major tail block: a block whose 16 rows are not all saved yet; it holds its rows row-major, so a row store writes 4 whole 64-byte lines. Hardware-attention policy: the rows of an operation scored on the FPGA (the attention accelerator card) are not recorded, so their blocks are never converted to the VNNI layout.
- FPGA attention (hardware attention): attention scored on the FPGA card (USE_HW_ATTN unset, the default for ingested models). CPU attention (software attention): USE_HW_ATTN=0.
- AMX: Intel Advanced Matrix Extensions. Kill switch: TRON_AMX_DISABLE=1. The option: the CMake switch TRON_K_VNNI. AMX dispatch: the CMake switch TRON_AMX_DISPATCH.
- tp2 / tp4: tensor parallelism over 2 / 4 slices (one slice = one FPGA card with its share of CPU cores and memory). qwen3-4b: the model ingested-qwen-3-4b-instruct-2507-tp2 / -tp4.
- TPS: decode tokens per second per user. TTFT: time to first token. sd: sample standard deviation over repetitions. Paired t: the mean of per-repetition (or per-round) differences divided by its standard error. Resolved (pr4424ci): |paired t| >= 2.26 and |delta| >= 1 % (TTFT also >= 1 ms). n: repetitions.
- Nightly layout: 8 users through the Caddy proxy over 4 tp2 engines (2 users per engine) or 2 tp4 engines (4 users per engine) [issue #4500 body, Words table]. Nightly client: systems_test testlib/tps.py, prompt 1024 (sharegpt), generate 1536, 10 rounds, TPS captured over generated tokens 896 to 1024 [issue #4500 body, Words table].
- deb: the Debian package the nightly installs. Canonical AMX deb: main 3faba6d0fd with TRON_AMX_DISPATCH on in the deb preset, row-major K [exec/i4500fix-20260928/campaign.sh:9].
- Catch2: the C++ test framework; it runs a test case once per leaf SECTION, so assertions outside the sections are counted once per section.
- delphi-3bda: the Intel Granite Rapids test machine (Xeon 6962P). Our half: socket 1 and the cards 90/93/b9/bc.
- est.: an estimate, not a measurement.

## 1. The FPGA-attention decode loss of issue #4500

### 1.1 The issue body (gh issue view 4500)

The issue is OPEN, created 2026-09-18T20:36:51Z, and has 0 comments [gh issue view 4500 --json state,createdAt,comments]. Its title: "qwen-3-4b with FPGA attention loses 5 to 11 % decode TPS under the VNNI K layout of PR #4424". Its Measurements table (all on delphi-3bda, USE_HW_ATTN unset, prompt 1024; "without PR #4424" against "with PR #4424"):

| date | driver, layout | config | without | with | change | evidence named in the issue |
|---|---|---|---|---|---|---|
| 2026-09-15 | runtron, 1 engine, 8 users, 256 tokens, n = 1 | tp2 | 125.39 TPS | 123.62 TPS | -1.4 % | PR #4424 description |
| 2026-09-16 | runtron, 1 engine, 8 users, 256 tokens, n = 6 | tp2 | 125.41 | 122.61 | -2.2 % (paired t -6.5) | exec/results/wedperf-attr-20260916 block D (main c7844ca2ce vs head ff680c8020) |
| 2026-09-16 | same | tp4 | 129.65 | 117.12 | -9.7 % (t -2.9) | same |
| 2026-09-18 | CI harness, nightly layout, whole machine, 10 rounds, 1 run per arm | tp2 @8u | 186.13 | 176.75 | -5.0 % (t -7.5 over rounds) | exec/results/ci-mimic-20260918 (nightly deb 2026.09.18-3faba6d0 vs main 3faba6d0 + PR #4424 30c4ac82cb as deb 2026.09.18-29a8a547) |
| 2026-09-18 | same | tp4 @8u | 149.94 | 133.44 | -11.0 % (t -10.2); CI threshold 135 TPS: the PR package fails | same |

The issue's hypothesis is the gather of one token's K row out of the VNNI layout in gof::populate (64 cache lines per (token, KV head) instead of 4), not measured [issue #4500 body, "Hypothesis for the cause (not measured)"]. The issue's option 1 is "Keep a row-major staging copy of K for the FPGA path"; option 3 is "Gate the layout off for models that run FPGA attention" [issue #4500 body, "Options"]. Token output under FPGA attention was identical between the two binaries in one smoke (128 of 128 tokens, 2026-09-15, exec/results/vnnik4-models-20260915) [issue #4500 body, "Measurements"].

### 1.2 exec/results/issue4500-20260918/summary.md (runtron, our half, 8 users on one engine, FPGA attention)

Arms: base = runtron.main0916 c7844ca2ce (main, row-major K); headoff = runtron.headoff0916 ff680c8020 with TRON_K_VNNI=OFF; vnni = runtron.pr4424 ff680c8020 with TRON_K_VNNI=ON; vnni2 = the same binary (A/A); vnnikill = vnni + TRON_AMX_DISABLE=1; head30 = 30c4ac82cb (1 repetition) [exec/results/issue4500-20260918/rt-results.txt:2]. Every run: FPGA attention (USE_HW_ATTN unset), prompt 1024, 256 generated tokens, --dont-stop; started 2026-09-18T21:50:30Z, the m1 runs from 2026-09-19 00:22 UTC [rt-results.txt:1-4]. This tree (ff680c8020) carries no block save and no tail block: it is the pre-S, pre-T per-row scatter store.

Block m1 (8 users), TPS mean (sd), n [summary.md "Cells"]:

| tp | arm | n | TPS | sd | TTFT s |
|---|---|---|---|---|---|
| 2 | base | 3 | 124.90 | 0.34 | 3.189 |
| 2 | headoff | 3 | 124.82 | 0.31 | 3.207 |
| 2 | vnni | 3 | 122.56 | 0.57 | 3.189 |
| 2 | vnni2 | 3 | 122.62 | 0.60 | 3.161 |
| 2 | vnnikill | 3 | 122.13 | 0.65 | 3.205 |
| 2 | head30 | 1 | 123.82 | - | 3.155 |
| 4 | base | 3 | 135.55 | 7.11 | 2.333 |
| 4 | headoff | 3 | 132.62 | 8.39 | 2.347 |
| 4 | vnni | 3 | 111.73 | 5.32 | 2.260 |
| 4 | vnni2 | 3 | 118.39 | 4.55 | 2.227 |
| 4 | vnnikill | 3 | 120.74 | 2.52 | 2.192 |
| 4 | head30 | 1 | 125.37 | - | 2.199 |

Paired (a minus b, per repetition, on step ms) [summary.md "Paired comparisons"]: vnni vs base tp2 -1.88 % TPS (t +4.80, TTFT +0 ms); vnni vs headoff tp2 -1.81 % (t +10.23); vnni vs base tp4 -17.57 % (t +5.61, sd of the step delta 0.485 ms); vnni2 vs base tp4 -12.66 % (t +2.66); vnni vs headoff tp4 -15.76 % (t +2.84); vnni2 vs vnni tp2 +0.05 % (t -0.32, the A/A), tp4 +5.97 % (t -1.23: the tp4 cell's A/A pair differs by 6 % with sd 0.719 ms). Block m1b (per-engine load) vnni vs base: tp2 2 users -3.82 % (t +6.21, n 2), tp2 4 users -0.79 %, tp4 2 users -6.40 % (t +0.99), tp4 4 users -13.34 % (t +2.34) [summary.md "Paired comparisons", m1b rows]. Blocks m2 (launch-phase knob), m3 (traces) and m4 (perf) are not the loss claim and are omitted here.

### 1.3 exec/results/i4500fix-20260928/summary.md (rinzler, one engine on our half, the nightly's client; the tail block WITHOUT the policy)

Arms [exec/i4500fix-20260928/campaign.sh:9-12]: base = the canonical AMX deb (main 3faba6d0fd + deb preset AMX ON, row-major K); vnni = the ci-mimic-20260918 target deb (main 3faba6d0fd + PR #4424 30c4ac82cb, AMX + VNNI K: the per-row scatter store, the package that showed the loss on 2026-09-18); fix = vnni + the fix commit (the row-major tail block; deb 98a5accb8b, fix commit 78e2da7511 on the PR head, branch jhan-amx-vnniK-i4500 head f34b0fe2ec) [exec/results/i4500fix-20260928/manifest.json; exec/i4500fix-20260928/README.md]; nightly = the installed nightly of 2026-09-29 (today's main, for reference). Cells: qwen3-4b tp2 with 2 users per engine and tp4 with 4 users per engine at prompt 1024 (FPGA attention, the nightly's per-engine loads), plus llama-8b tp2 8 users prompt 4096 (CPU attention); n = 3, binaries interleaved; client = the nightly's own (generate 1536, 10 rounds, TPS between generated tokens 896 and 1024) [README.md "Cells of step D"]. Date: the chain ran after the nightly of 2026-09-29 (smoke 13:25-13:35 UTC, cells after) [exec/results/i4500fix-20260928/smoke.log:1; status.txt].

| model | tp | users/engine | prompt | binary | n | TPS mean | sd | TTFT ms |
|---|---|---|---|---|---|---|---|---|
| qwen3-4b | 2 | 2 | 1024 | base | 3 | 193.46 | 1.63 | 707 |
| qwen3-4b | 2 | 2 | 1024 | vnni | 3 | 186.18 | 1.77 | 709 |
| qwen3-4b | 2 | 2 | 1024 | fix | 3 | 188.98 | 1.23 | 697 |
| qwen3-4b | 2 | 2 | 1024 | nightly | 3 | 194.44 | 0.32 | 705 |
| qwen3-4b | 4 | 4 | 1024 | base | 3 | 156.82 | 2.14 | 865 |
| qwen3-4b | 4 | 4 | 1024 | vnni | 3 | 138.30 | 17.30 | 817 |
| qwen3-4b | 4 | 4 | 1024 | fix | 3 | 142.99 | 14.11 | 821 |
| qwen3-4b | 4 | 4 | 1024 | nightly | 3 | 177.12 | 0.53 | 818 |

Paired (t threshold 4.30 at n = 3) [summary.md "Paired"]: vnni vs base tp2 -3.77 % (t +6.49); vnni vs base tp4 -11.81 % (t +1.68, below the threshold); fix vs base tp2 -2.32 % (t +3.17); fix vs base tp4 -8.82 % (t +1.62); fix vs vnni tp2 +1.50 % (t -1.62); fix vs vnni tp4 +3.39 % (t -1.81); nightly vs base tp4 +12.94 % (t -12.32). These -3.77 % and -11.81 % are the "-3.8 % (tp2) / -11.8 % (tp4)" of split-plan.md [split-plan.md:154]. They are at 2 and 4 users on one engine, not 8 users, and the tp4 value has sd 17.30 TPS on the vnni arm and a paired t below the threshold.

### 1.4 exec/results/i4500b-20260930/summary.md (the tail block WITH the policy, the T content)

Arms [exec/i4500b-20260930/campaign.sh:9-14]: base = the canonical AMX deb (as 1.3); fix = the 2026-09-29 fix deb 98a5accb8b (tail block only); fixS1 = the fix deb line + the policy commit (452b2052c9 on jhan-amx-vnniK-i4500, cherry-picked as 2fd11e32ca: "blocks completed under hardware attention stay row-major") [exec/i4500b-20260930/README.md; build-deb.sh:2-3]; basekill / fixS1kill = the same with TRON_AMX_DISABLE=1 (tp4 only). Cells as 1.3; n = 4; the nightly's client; date 2026-09-30 (smoke 13:28-13:38 UTC, traces 13:38-13:44 UTC, cells after) [exec/results/i4500b-20260930/smoke.log; traces.log; status.txt].

| model | tp | users/engine | prompt | binary | n | TPS mean | sd | TTFT ms |
|---|---|---|---|---|---|---|---|---|
| qwen3-4b | 2 | 2 | 1024 | base | 4 | 193.08 | 1.14 | 709 |
| qwen3-4b | 2 | 2 | 1024 | fix | 4 | 189.83 | 0.76 | 706 |
| qwen3-4b | 2 | 2 | 1024 | fixS1 | 4 | 193.90 | 0.77 | 704 |
| qwen3-4b | 4 | 4 | 1024 | base | 4 | 145.24 | 13.50 | 882 |
| qwen3-4b | 4 | 4 | 1024 | basekill | 4 | 146.05 | 11.25 | 871 |
| qwen3-4b | 4 | 4 | 1024 | fix | 4 | 144.00 | 5.37 | 835 |
| qwen3-4b | 4 | 4 | 1024 | fixS1 | 4 | 149.35 | 9.31 | 826 |
| qwen3-4b | 4 | 4 | 1024 | fixS1kill | 4 | 149.85 | 7.75 | 830 |
| llama-8b | 2 | 8 | 4096 | base | 4 | 39.60 | 0.05 | 13409 |
| llama-8b | 2 | 8 | 4096 | fixS1 | 4 | 42.95 | 0.16 | 13455 |

Paired [summary.md "Paired"]: fixS1 vs base tp2 +0.43 % (t -2.02); fixS1 vs base tp4 +2.83 % (t -1.62); fix vs base tp2 -1.68 % (t +3.45); fix vs base tp4 -0.86 % (t +0.05); fixS1 vs fix tp2 +2.15 % (t -6.15); fixS1 vs fix tp4 +3.72 % (t -0.91); fixS1kill vs fixS1 tp4 +0.33 % (t -0.10); llama-8b fixS1 vs base +8.44 % (t -54.05). The tp4 base arm's sd is 13.50 TPS here (2.14 TPS the day before), so the tp4 cell is not stable between days.

### 1.5 i4500c-20260930 and q4b-fpga-20260921

i4500c-20260930 is a perf-record chain, not a TPS campaign: status "perf finished: incomplete (2 reports missing, gaveup=0)" [exec/results/i4500c-20260930/status.txt]. Its README gives a decode Save K span comparison from the i4500b traces: the policy build's main-thread Save K is about 105 us per pass against 58 us for the canonical build at tp2 with 2 users, and 171 us against 111 us at tp4 with 4 users, "although both write the same 4 cache lines per (token, KV head)" [exec/i4500c-20260930/README.md:3-6]. TPS: Insufficient data in that folder.

q4b-fpga-20260921 holds no VNNI arm. Its arms are fpgabase (the nightly deb 2026.09.18-3faba6d0, FPGA attention), fpgacanon (the canonical-AMX deb, FPGA attention) and canon (the canonical-AMX deb, CPU attention), 9 prompt lengths 1024 to 8192, nightly layout, 8 users [exec/results/q4b-fpga-20260921/RUNBOOK.md "Words used here"; base-identity.txt; configs-used.json]. It has no summary.md; each pass has a summary.txt. The qwen3-4b tp2 8-user prompt-1024 rows: fpgabase pass1/2/3 185.79 / 185.41 / 184.03 TPS (sd 6.81 / 7.27 / 7.47), TTFT 555 / 554 / 553 ms; fpgacanon pass1/2/3 184.61 / 188.60 / 185.54 TPS (sd 7.32 / 23.79 / 15.95), TTFT 520 / 513 / 504 ms; canon pass1 (CPU attention) 152.17 TPS (sd 7.51), TTFT 518 ms [exec/results/q4b-fpga-20260921/<tag>/summary.txt, RESULT lines]. No tp4 cell exists there.

### 1.6 Which record backs "8 users, prompt 1024, FPGA attention" with and without the tail block

- WITHOUT the tail block at 8 users on one engine: only issue4500-20260918 block m1 (runtron, ff680c8020, 2026-09-19): vnni vs base -1.88 % at tp2 and -17.57 % at tp4 (section 1.2). In the nightly layout (8 users over 4 or 2 engines): the 2026-09-18 CI-harness run of the issue body, -5.0 % / -11.0 %.
- WITH the tail block and the policy at 8 users on one engine under FPGA attention: Insufficient data. No record runs the T content at 8 users on one engine with FPGA attention. The T content was measured at 2 users per tp2 engine and 4 users per tp4 engine (i4500b, section 1.4) and in the nightly layout on the whole machine (pr4424ci, section 2: -0.9 % at tp2 and -0.4 % at tp4, both not resolved).
- The m4737-E-cpu cells of the 9d5c7a389b tree are CPU attention, not FPGA (section 3).

## 2. The whole-machine table: exec/results/pr4424ci-20261009/summary.md

Identities: base = the nightly deb 2026.10.08-be0d5565, sha256 aebe98551e873219b7ff8dcf25f2cf9a35ebee01e660d6b71b042f48819cd123 (nightly.deb); restore = 2026.10.09-26b6df7d, sha256 0e25909c47bb... (restore.deb) [exec/results/pr4424ci-20261009/base-identity.txt]. Target = PR 4424 at commit 9d5c7a389b23078398028bce0d1fe1a6c5c64e31 plus one local preset commit (TRON_K_VNNI ON in the deb preset), branch jhan-pr4424ci-target, head 667b2ce5e87e8e61d223ce50bcd380a215963ac3, never pushed; deb tron_2026.10.09-667b2ce5-jhan-pr4424ci-target_amd64.deb, sha256 8e81110a...; rinzler sha256 240d9cbc...; built 2026-10-09T00:14:47Z in /var/tmp/jhan/tron-pr4424ci; options TRON_AMX_DISPATCH ON, TRON_K_VNNI ON; package checks: TRON_AMX_DISABLE literal 1, AMX tile instructions 126, VNNI strings 4 [preflight.txt, "target build" block]. Preflight at 2026-10-09T13:36:30Z: installed tron 2026.10.09-26b6df7d, platformd 0.11.0+sst.88b2d3da, rinzler@0 and @1 active, no lease file, Bill's marker absent, hugepages 512 total 0 free, config.env 0 bytes, engine env AMX/HW_ATTN vars 0, Intel Speed Select two-tier policy clos0=224 clos3=64, load 126.70 [preflight.txt]. Configs: full = the harness scripts.perf.configs of systems_test at 14f0ce4; sw8k = exec/pr4424ci-20261009/sw8k.json (ingested-qwen-3-4b-instruct-2507-tp2, 8 users, prompt 8192, generate 1536, capture 896 to 1024, sharegpt) [configs-used.txt; configs-used-sw8k.json]. Passes in the order base, target, target, base, started 2026-10-09T00:15:16Z with NOT_BEFORE 13:00Z, campaign done 2026-10-09T22:02:47Z, restore ok [status-history.log first and last lines; .status]. Run durations: base-pass1 109.6 min, target-pass1 106.25 min, base-pass2 109.04 min, target-pass2 108.91 min; the sw8k passes 7.85 / 7.53 / 7.76 / 7.7 min [summary.md "Runs found"]. Outcome: "incomplete passes: none; stop reason: none; problems: none; known systematic failures: none" [outcome.txt]. Per-provisioning checks: all ok [summary.md last line].

Resolution rule: resolved = |paired t| >= 2.26 AND |delta| >= 1 % (TTFT also |delta| >= 1 ms); the paired t pools the per-round differences (target - base, round means) of the two pass pairs, n = 20 rounds. Memory = mean over passes of the sum over engine pids of VmHWM (peak resident set) and VmRSS read right after the benchmark, in MiB; 1 GiB hugepages are not in these sums [summary.md "Resolution rule"].

The 15 rows (TPS mean over 2 passes, sd over passes in parentheses; TTFT ms; memory = VmHWM sum MiB) [summary.md]:

| cell | base TPS | target TPS | delta % | paired t | resolved | base TTFT | target TTFT | TTFT delta | TTFT resolved | base VmHWM | target VmHWM | delta MiB (%) | RSS delta MiB |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| llama-3.2-3b-instruct-fast-tp2@32u-p200 | 198.26 (0.40) | 195.56 (0.44) | -1.4 % | -16.56 | YES | 74 | 58 | -15 ms (-20.8 %) t -1.47 | no | 8,714 | 8,719 | +6 (+0.1 %) | +4 |
| llama-3.1-8b-instruct-good-tp2@8u-p1024 | 143.03 (0.55) | 142.58 (0.57) | -0.3 % | -1.35 | no | 586 | 585 | -0 ms (-0.1 %) t -0.05 | no | 21,926 | 21,930 | +5 (+0.0 %) | +1 |
| llama-3.1-8b-instruct-good-tp2@32u-p4096 | 32.62 (0.02) | 34.20 (0.03) | +4.8 % | +39.40 | YES | 11,821 | 11,833 | +12 ms (+0.1 %) t +0.66 | no | 21,926 | 21,930 | +5 (+0.0 %) | +14 |
| llama-3.3-70b-instruct-good-tp2@8u-p1024 | 17.01 (0.01) | 17.00 (0.01) | -0.0 % | -2.11 | no | 9,382 | 9,393 | +11 ms (+0.1 %) t +0.98 | no | 151,916 | 151,918 | +2 (+0.0 %) | +6 |
| llama-3.3-70b-instruct-good-tp2@4u-p1024 | 28.46 (0.00) | 28.68 (0.04) | +0.8 % | +13.14 | no | 4,086 | 4,457 | +371 ms (+9.1 %) t +1.05 | no | 151,916 | 151,918 | +2 (+0.0 %) | +7 |
| llama-3.3-70b-instruct-good-tp4@4u-p1024 | 31.71 (0.00) | 31.67 (0.09) | -0.1 % | -0.77 | no | 4,875 | 4,874 | -1 ms (-0.0 %) t -0.16 | no | 75,903 | 75,903 | -0 (-0.0 %) | +4 |
| mixtral-8x7b-instruct-v0.1-tp2@8u-p1024 | 80.68 (0.31) | 80.62 (0.23) | -0.1 % | -0.16 | no | 1,259 | 1,264 | +5 ms (+0.4 %) t +2.24 | no | 356,379 | 356,363 | -16 (-0.0 %) | +6 |
| qwen-2.5-32b-it-fast-tp2@8u-p1024 | 36.06 (0.04) | 36.02 (0.01) | -0.1 % | -2.60 | no | 3,946 | 3,939 | -7 ms (-0.2 %) t -1.11 | no | 73,832 | 73,838 | +6 (+0.0 %) | +3 |
| ingested-qwen-3-4b-instruct-2507-tp2@8u-p1024 | 189.13 (1.04) | 187.38 (0.68) | -0.9 % | -2.19 | no | 502 | 494 | -8 ms (-1.6 %) t -1.01 | no | 16,457 | 16,457 | +0 (+0.0 %) | -3 |
| ingested-qwen-3-4b-instruct-2507-tp4@8u-p1024 | 181.01 (0.44) | 180.30 (0.55) | -0.4 % | -0.42 | no | 557 | 545 | -12 ms (-2.1 %) t -0.76 | no | 8,140 | 8,132 | -8 (-0.1 %) | +25 |
| gemma-2-9b-it-fast-tp2@8u-p1024 | 104.03 (0.12) | 104.84 (1.06) | +0.8 % | +0.97 | no | 856 | 852 | -5 ms (-0.5 %) t -1.73 | no | 23,678 | 23,597 | -81 (-0.3 %) | -0 |
| ingested-gpt-oss-120b-tp4@8u-p1024 | 122.38 (0.05) | 121.83 (1.34) | -0.5 % | -1.28 | no | 966 | 944 | -22 ms (-2.3 %) t -1.93 | no | 128,490 | 128,492 | +2 (+0.0 %) | -4 |
| ingested-gemma-4-31b-it-tp2@8u-p1024 | 38.21 (0.02) | 38.23 (0.04) | +0.1 % | +0.70 | no | 5,456 | 5,448 | -8 ms (-0.1 %) t -1.57 | no | 92,586 | 92,603 | +17 (+0.0 %) | +1 |
| ingested-meta-models--Muse-Glimmer-30B-tp4@8u-p1024 | 74.72 (0.02) | 76.53 (0.15) | +2.4 % | +24.35 | YES | 3,720 | 3,602 | -118 ms (-3.2 %) t -25.90 | YES | 46,420 | 46,428 | +8 (+0.0 %) | +2 |
| extra: ingested-qwen-3-4b-instruct-2507-tp2@8u-p8192, USE_HW_ATTN=0 | 59.84 (0.20) | 64.41 (0.26) | +7.6 % | +39.27 | YES | 12,957 | 12,807 | -150 ms (-1.2 %) t -8.97 | YES | 16,451 | 16,475 | +24 (+0.1 %) | +41 |

Per-pass qwen3-4b values (TPS mean (sd over the 80 samples, min), TTFT) [<pass>/driver.log RESULT lines]: tp2@8u-p1024 base-pass1 189.87 (12.12, 181.21) 492 ms, target-pass1 187.85 (5.30, 177.99) 495 ms, target-pass2 186.90 (5.65, 166.65) 493 ms, base-pass2 188.39 (12.18, 141.51) 511 ms; tp4@8u-p1024 base-pass1 181.32 (6.19, 173.78) 559 ms, target-pass1 180.69 (8.37, 140.92) 533 ms, target-pass2 179.91 (5.54, 173.96) 557 ms, base-pass2 180.70 (22.64, 172.25) 555 ms; tp2@8u-p8192 software attention base-pass1 59.70 (0.62) 12970 ms, target-pass1 64.23 (0.81) 12816 ms, target-pass2 64.59 (6.84) 12798 ms, base-pass2 59.98 (0.69) 12944 ms.

## 3. The token-identity record and the m4737-E-cpu cells

### 3.1 exec/results/merge4737-precheck/

Steps [steps.txt]: 2026-10-09T13:48:21Z STEP 1 serving units active, hp_free 0; 22:10:28Z STEP 2 host suite "failed build-test-host rc=0 ... heap_setup failed" (a first attempt while serving was up: the heap_setup exception); 22:17:58Z cpu p1024 ok; 22:19:54Z fpga p1024 ok; 22:22:13Z cpu p8192 ok; 22:37:09Z m4737-E-cpu ok; 22:37:55Z end "failed host=failed smoke=ok/ok/ok"; a second run at 23:06:50Z with units inactive and hp_free 512 skipped the finished smokes and cells and re-ran the host suite at 23:09:44Z ("failed build-test-host rc=0 passed t_tokenizers-fast ..."); 23:10:30Z end "failed host=failed smoke=ok/ok/ok". precheck.done = "failed host=failed smoke=ok/ok/ok"; host-suite-m4737.done = "failed" [precheck.done; host-suite-m4737.done].

Host suite counts [host-suite-m4737.txt]: build-test-host rc=0; 93 passed, 1 skipped, 1 failed; the failure is t_proxy_llama31 (returncode 4, "ERROR: t/proxy/.venv missing — run make proxy-test-deps"); makespan 125.8 s, expected 131.4 s; test-host rc=2. t_k_vnni_layout (0.8 s), t_amx_dispatch_dtype (0.7 s) and t_amx_numerics (0.8 s) are among the passed tests. The skipped test is not named in the txt (PR 4424's body names t_proxy_lib).

Smokes [smoke/<cell>/smoke.txt]: arms base = /var/tmp/jhan/tron-main1007/gen/runtron.main1007 (main be0d5565b3, version 2026.10.08-be0d5565); head = runtron.savek2 (45e6bb266d, the shared-save tree without the tail block); new, new2, newoff = runtron.m4737 (9d5c7a389b, version 2026.10.09-9d5c7a38; newoff with TRON_AMX_DISABLE=1); model ingested-qwen-3-4b-instruct-2507-tp2, 1 user, 256 tokens, temperature 0, pay-for-determinism, seed 1; 2026-10-09 22:14 to 22:22 UTC.

| cell | pair | result |
|---|---|---|
| CPU p1024 | new vs new2 | identical, 256 of 256 |
| CPU p1024 | newoff vs new | identical, 256 of 256 |
| CPU p1024 | new vs base | identical, 256 of 256 |
| CPU p1024 | new vs head | first difference at generated token 52 (9396 vs 198) |
| CPU p1024 | head vs base | first difference at generated token 52 (198 vs 9396) |
| CPU p8192 | new vs base, new vs head, head vs base | identical, 256 of 256 (arms base, head, new only) |
| FPGA p1024 | new vs head | identical, 256 of 256 |
| FPGA p1024 | new vs base | first difference at generated token 52 (198 vs 9396) |
| FPGA p1024 | head vs base | first difference at generated token 52 (198 vs 9396) |

The must-match pairs were new:new2 and newoff:new; SMOKE-VERDICT ok in all three cells. The FPGA and CPU-8192 cells had no new2 and no newoff arm.

### 3.2 exec/results/m4737-E-cpu/summary.md

The summary.md header text ("base = PR #4557 head c12df586b6, head = PR #4424 head 30c4ac82cb, new = the synced branch (PR #4746)") is inherited from the sync4424 script and does not describe this run; the arms of this run are in rt-results.txt: base = runtron.main1007 (be0d5565b3, sha256 1fa183b0...), new = runtron.m4737 (9d5c7a389b, sha256 3fdf6aa4...) [rt-results.txt:2,11-14]. Cells: qwen3-4b tp2, 8 users, CPU attention (USE_HW_ATTN=0), prompt 1024 and 8192, 256 generated tokens (--dont-stop), 3 repetitions, our half, placement --instance 2,4 with cards 90:00.0 and 93:00.0 and 128 hugepages; started 2026-10-09T22:22:13Z [rt-results.txt:1-9].

| cell | arm | n | TPS/user | sd | TTFT s | sd |
|---|---|---|---|---|---|---|
| tp2 p1024 | base | 3 | 79.10 | 0.29 | 3.177 | 0.004 |
| tp2 p1024 | new | 3 | 83.14 | 0.47 | 3.133 | 0.002 |
| tp2 p8192 | base | 3 | 17.10 | 0.03 | 52.584 | 0.096 |
| tp2 p8192 | new | 3 | 18.87 | 0.02 | 52.040 | 0.045 |

Paired new vs base [summary.md second table]: p1024 TPS +5.1 % (+4.04 TPS, sd 0.20, t +35.2), TTFT -45 ms (-1.4 %, sd 2, t -36.9); p8192 TPS +10.3 % (+1.77 TPS, sd 0.02, t +157.6), TTFT -543 ms (-1.0 %, sd 64, t -14.8). Excluded, failed, early-stop and duplicate records: 0 each.

## 4. Unit-test counts and the arithmetic for PR-4's three builds

### 4.1 The two 2026-10-08 trees

Both chains used the same recipe: preset native, clang 19, BUILD_INGEST_MODELS ON / AMX dispatch ON / option ON for the VNNI build; BUILD_INGEST_MODELS OFF / AMX dispatch ON / option OFF for the row-major build; tests without --skip-benchmarks on cpus 72-143,216-287 [exec/results/savek2-20261008/build-savek2.txt; build-savek2rm.txt; exec/results/merge4737-20261008/build-m4737.txt; build-m4737rm.txt].

45e6bb266d ("VNNI K: one save_k for main and the main helpers (merge of PR 4774)", 2026-10-08 12:16 -0700; VNNI build 774 s, row-major build 284 s) [savek2-20261008/steps.txt; tests-savek2.txt; tests-savek2rm.txt]:

| binary | VNNI build (assertions / cases) | row-major build |
|---|---|---|
| t_k_vnni_layout | 1011650 / 5 | 1011650 / 5 |
| t_amx_dispatch_dtype | 1612 / 1 | 1612 / 1 |
| t_amx_numerics | 4621 / 5 | 4621 / 5 |
| t_llama_unit | 251755 / 64 | 251670 / 64 |
| t_heterogeneous_scheduler | 2783 / 3 | 2783 / 3 |
| t_phase1_integration | 2124 / 64 | not built |
| t_amx_numerics, kill switch | 2060 / 5, 3 "AMX unavailable" lines (QK precision, VNNI QK identity, PV precision) | not run |

9d5c7a389b ("VNNI K: keep short K-cache writes row-major, on the typed K owner (merge of PR 4737)", 2026-10-08 16:45 -0700; VNNI build 127 s incremental, row-major build 291 s) [merge4737-20261008/steps.txt; tests-m4737.txt; tests-m4737rm.txt]:

| binary | VNNI build | row-major build |
|---|---|---|
| t_k_vnni_layout | 1041256 / 10 | 1039202 / 10 |
| t_amx_dispatch_dtype | 2137 / 1 | 2137 / 1 |
| t_amx_numerics | 4621 / 5 | 4621 / 5 |
| t_llama_unit | 259020 / 64 | 258911 / 64 |
| t_heterogeneous_scheduler | 2783 / 3 | 2783 / 3 |
| t_phase1_integration | 2124 / 64 | not built |
| t_amx_numerics, kill switch | 2060 / 5, 3 "AMX unavailable" lines | not run |

Neither 2026-10-08 chain ran t_llama_unit with the kill switch, and neither built the AMX-off configuration [steps.txt of both]. The merge4737 chain's first STEP A line, at tip 3723bf601af4 (2026-10-08T23:43:29Z), reads "tests-failed-1": t_llama_unit rc=42 with "t/t_llama_unit.cpp:3890: FAILED" and t_k_vnni_layout 1041256 / 10 already; the passing STEP A at 9d5c7a389b followed at 23:48:37Z [merge4737-20261008/steps.txt:1-2]. What changed between 3723bf601a and 9d5c7a389b: Insufficient data in the record (only the two STEP lines exist). A2 (Haskell suite) rc=0 in 112 s and F (clang-format, fourmolu, diff-check) rc=0 at 9d5c7a389b [steps.txt:3-4; tests-m4737.txt last line]. The generated-plugin grep found main-side 0, helper-side 0, save_k_helper 0 for all 19 plugins at both trees (the grep pattern of that script matched neither call form) [tests-m4737.txt; tests-savek2.txt].

### 4.2 T's measured delta per binary (9d5c7a389b minus 45e6bb266d)

| binary | VNNI build delta | row-major build delta | cases delta |
|---|---|---|---|
| t_k_vnni_layout | +29606 | +27552 | +5 (5 to 10) |
| t_amx_dispatch_dtype | +525 | +525 | 0 |
| t_amx_numerics | 0 | 0 | 0 |
| t_llama_unit | +7265 | +7241 | 0 |
| t_heterogeneous_scheduler | 0 | 0 | 0 |
| t_phase1_integration | 0 | not built | 0 |
| t_amx_numerics kill switch | 0 | - | 0 |

T touches three test files: t/t_amx_dispatch_dtype.cpp (+34/-5 lines), t/t_k_vnni_layout.cpp (+490/-2) and t/t_llama_unit.cpp (+136/-4); its other 7 files are headers (amx_attn_iface.hpp +8/-5, kernels/k_vnni.hpp +13/-10, kv_cache.hpp +475/-52, model.hpp +76/-12, self_attention.hpp +68/-17, scheduler/full.hpp +8/-2, tensor/k_vnni.hpp +109/-4) [T-4737-merge.diff, diff --git lines and added/removed line counts]. The names t_amx_numerics, t_heterogeneous_scheduler and t_phase1_integration do not occur in the T diff (0 matches), and their counts are equal at both trees in both builds, so T does not touch those three binaries' assertions; they still recompile, because T changes headers they include. T adds 5 TEST_CASEs to t_k_vnni_layout ("row-major tail block converts to the VNNI layout and back, bit for bit"; "page K blocks turn VNNI at the 16th saved row and back when a row is ..."; "the EAGLE storage view keeps its own K layout state"; "forgetting a row acts on every slot's own block"; "page append carries the K layout state with the rows") and removes only two comment lines from that file, so PR-3's block-save case is untouched by T [T-4737-merge.diff, t_k_vnni_layout.cpp hunk]. T adds one SECTION to the single case of t_amx_dispatch_dtype ("host_bf16, full page with unrecorded rows: one pack, and under TRON_K_VNNI no kernel call (the blocks are row-major)"), inside the #ifdef TRON_AMX_DISPATCH branch; the #else placeholder case is unchanged [T diff hunk; probe t/t_amx_dispatch_dtype.cpp:310-344]. T adds two SECTIONs to the save_k case of t_llama_unit ("hardware attention scores the operation: the completed block stays ..." and "hardware attention scores another operation: this one still converts") and removes 4 comment lines [T diff, t_llama_unit.cpp hunk].

### 4.3 PR-3's head 80bce9a08d (2026-10-12, --skip-benchmarks)

[split-status.md:355-366; exec/results/pr3-20261012/tests-pr3.txt; tests-pr3nd.txt; tests-pr3rm.txt]

| binary | VNNI build (A) | AMX-off, option on (A3) | row-major build (B) |
|---|---|---|---|
| t_k_vnni_layout | 1011585 / 5 | 1011585 / 5 | 1011585 / 5 |
| t_amx_dispatch_dtype | 1618 / 1 | 1 / 1 (placeholder) | 1618 / 1 |
| t_amx_numerics | 6669 / 5 (0 "AMX unavailable" lines) | 1 / 1 (placeholder) | 6669 / 5 (0 lines) |
| t_llama_unit | 269326 / 66 | 269326 / 66 | 269067 / 66 |
| t_heterogeneous_scheduler | 2783 / 3 | 2783 / 3 | 2783 / 3 |
| t_phase1_integration | 6220 / 64 | 6220 / 64 | not built |
| t_llama_unit, kill switch | 269326 / 66 | - | - |
| t_amx_numerics, kill switch | 4108 / 5, 3 "AMX unavailable" lines | - | - |

PR-3's block-save case has 153 assertions (the 2026-10-08 trees' 218 minus a removed section) [split-status.md, "PR-3 Step 5" item 5]. PR-3's three-thread section of the save_k case was rewritten with two windows [split-status.md, "PR-3 Step 5" item 6]. The differences 4621 -> 6669 (t_amx_numerics), 2124 -> 6220 (t_phase1_integration) and 1612 -> 1618 (t_amx_dispatch_dtype) between the 2026-10-08 trees and PR-3 come from main's drift and PR-2's edits, not from T.

### 4.4 Expected counts of PR-4's three builds (PR-3 + T's delta), with the arithmetic

VNNI build (option on, AMX dispatch on):
- t_k_vnni_layout: 1011585 + 29606 = 1041191 assertions in 5 + 5 = 10 cases. Additive, because T's 5 cases are separate TEST_CASEs and T leaves the block-save case alone.
- t_amx_dispatch_dtype: 1618 + 525 = 2143 (est.) in 1 case. The case has 6 leaf sections after T (5 before) [probe t/t_amx_dispatch_dtype.cpp:314-336]; if the 6 assertions by which PR-3's 1618 exceeds the 2026-10-08 trees' 1612 lie outside the sections, Catch2 counts them once more under the new section, so the exact value may be 2143 to 2149. Record it.
- t_amx_numerics: 6669 in 5 cases (T delta 0). Kill switch: 4108 in 5 cases with 3 "AMX unavailable" lines.
- t_llama_unit: 269326 + 7265 = 276591 (est.) in 66 cases. Not reliable: T's two new sections join a case whose three-thread section PR-3 rewrote; Catch2 re-runs the case's top-level assertions once per leaf section (the probe's case has 4 sections at t/t_llama_unit.cpp:4063, 4082, 4098 and 4118 [probe worktree]), and the +7265 was measured on the old three-thread section. Record the count, as PR3-handoff.md step 6 did for this binary. The kill-switch run of t_llama_unit should match the AMX-on run (it did at PR-3: 269326 both).
- t_heterogeneous_scheduler: 2783 in 3 cases. t_phase1_integration: 6220 in 64 cases.

Row-major build (option off):
- t_k_vnni_layout: 1011585 + 27552 = 1039137 in 10 cases (T's new cases are gated by #ifdef TRON_K_VNNI at five places and by nothing else, so they count less with the option off) [probe t/t_k_vnni_layout.cpp:528,643,698,771,790].
- t_amx_dispatch_dtype: 1618 + 525 = 2143 (est., same caveat). t_amx_numerics: 6669 / 5. t_llama_unit: 269067 + 7241 = 276308 (est., same caveat). t_heterogeneous_scheduler: 2783 / 3.

AMX-off build (option on, AMX dispatch off), no 2026-10-08 reference exists:
- t_k_vnni_layout: 1041191 in 10 cases (the option-on delta; the file has no TRON_AMX_DISPATCH gate).
- t_amx_dispatch_dtype: 1 / 1 (the placeholder; T's section is inside the #ifdef TRON_AMX_DISPATCH branch). t_amx_numerics: 1 / 1.
- t_llama_unit: 276591 (est.) in 66 cases (the same value as the VNNI build, as at PR-3). t_heterogeneous_scheduler 2783 / 3. t_phase1_integration 6220 / 64.

## 5. The 2026-09-14/15 trace records

Both analysis files share the header "Per trace and pass kind: mean over passes. Rows = tokens x 8 KV heads." and give prefill and decode tables with pass ms, Save K ms/pass, Save K us/layer, ns/row, Save V, and busy fractions [exec/results/vnnik-trace-20260914/analysis.md; vnnik2-trace-20260915/analysis.md]. Neither file uses the words "64 lines" or "scatter"; the decode Save K rows are the per-token store cost.

vnnik-trace-20260914 arms: base = runtron.p0perf13 at 544ca05c7a (version 2026.09.13-544ca05c, the PR 3879 binary, row-major K); vnni = runtron.vnnik at 5e45ae55 (2026.09.14-5e45ae55, the per-row scatter store); qwen3-4b tp2 and tp4, 8 users, prompt 1024, 32 generated tokens, passes 1-16 traced, CPU attention ("HW attention disabled ... USE_HW_ATTN=0"), 2026-09-14 22:29 to 22:33 UTC [vnnik-trace-20260914/runs.txt "### trace" and "Version:" lines].

| trace | kind | pass ms | Save K us/layer | ns/row |
|---|---|---|---|---|
| base-tp2 | prefill | 392.7 | 273.6 | 33.4 |
| vnni-tp2 | prefill | 402.4 | 859.4 | 104.9 |
| base-tp4 | prefill | 274.0 | 281.3 | 34.3 |
| vnni-tp4 | prefill | 294.3 | 861.7 | 105.2 |
| base-tp2 | decode | 13.6 | 4.6 | 72.2 |
| vnni-tp2 | decode | 12.7 | 28.4 | 444.5 |
| base-tp4 | decode | 10.9 | 5.8 | 90.9 |
| vnni-tp4 | decode | 10.8 | 34.5 | 539.8 |

vnnik2-trace-20260915 arms: one binary runtron.vnnik2 at 9928cb28 (2026.09.14-9928cb28) with environment switches: vnni0 = TRON_K_VNNI_BLOCK=0 TRON_K_VNNI_STRIPE=0 (the scatter store), a = BLOCK=1 STRIPE=0 (the block save alone), b = BLOCK=0 STRIPE=1 (the sharing alone), ab = both; same cells; recorded 2026-09-14 23:05 to 23:12 UTC [vnnik2-trace-20260915/runs.txt "### trace" lines].

| trace | kind | pass ms | Save K us/layer | ns/row |
|---|---|---|---|---|
| vnni0-tp2 | prefill | 400.9 | 857.7 | 104.7 |
| a-tp2 | prefill | 390.2 | 346.2 | 42.3 |
| b-tp2 | prefill | 389.1 | 175.2 | 21.4 |
| ab-tp2 | prefill | 385.4 | 79.7 | 9.7 |
| vnni0-tp4 | prefill | 293.8 | 862.9 | 105.3 |
| a-tp4 | prefill | 274.2 | 352.9 | 43.1 |
| b-tp4 | prefill | 266.5 | 109.7 | 13.4 |
| ab-tp4 | prefill | 265.8 | 59.7 | 7.3 |
| vnni0-tp2 | decode | 12.7 | 28.6 | 447.4 |
| a-tp2 | decode | 12.7 | 28.5 | 446.1 |
| b-tp2 | decode | 12.6 | 28.3 | 441.7 |
| ab-tp2 | decode | 12.9 | 28.9 | 452.3 |
| vnni0-tp4 | decode | 11.3 | 36.3 | 567.3 |
| a-tp4 | decode | 10.9 | 35.1 | 548.5 |
| b-tp4 | decode | 10.8 | 35.4 | 553.7 |
| ab-tp4 | decode | 11.3 | 34.2 | 535.1 |

Reading for PR-4: in decode (8 tokens x 8 KV heads = 64 rows per layer) the Save K span is 28 to 29 us per layer (about 445 ns per row) under every 2026-09-15 arm, against 4.6 us per layer (72 ns per row) with row-major K; the block save and the sharing do not change it, because a one-token run keeps the scatter store. This is the pre-T decode cost. No trace of a T tree under CPU attention exists in these two folders; the i4500b traces (section 1.5) are the T-era decode traces, under FPGA attention. Threads: main 1, attention workers 20 (tp2) or 47 (tp4), main helpers 7 (tp2) or 8 (tp4) [both analysis.md "threads"].

## 6. The PR 4424 live body and the PR 4737 body

### 6.1 Section headings of pr4424-body-live.md (37,778 bytes)

"## Short version" (line 1); "### Background" (7); "### Remove the Score transpose by saving VNNI layout and transposed K" (16); "### Use shared block in saving K" (21); "## Words used here" (29); "## The changes" (62); "## Measurements" (107); "### Nightly CI perf configs, whole machine, this branch against `main` (2026-10-09)" (109); "### runtron cells against `main` at this head (2026-10-09)" (142); "### Against the PR #3879 binary (runtron, our half of delphi-3bda, qwen3-4b, 8 users, software attention with AMX)" (159); "## Verification" (175); "### Host test suite and token identity at this head (2026-10-09)" (207); "## Open items" (230).

### 6.2 Sentences that describe the T and B content (reusable where they hold)

Row-major tail block:
- Words row "row-major tail block": "A 16-token block of a VNNI K plane whose 16 rows are not all saved yet. It holds its rows row-major (one contiguous 256-byte row per token) inside the block's own 4 KiB. A row store into such a block writes 4 whole 64-byte lines, as the row-major layout does. Note [Row-major tail block] in `h/tron/tensor/k_vnni.hpp`."
- Words row "converted block": "A block whose 16 rows are saved and whose bytes were transposed in place into the VNNI layout: by the whole-block save at once, or at the end of the forward pass that saved the 16th row. The page records per storage slot which rows are saved and which blocks are converted (Note [K VNNI storage])."
- Words row "shared block save", last two sentences: "A unit that fills its whole block is written with 16 rows transposed in registers, one 64-byte line at a time. A shorter unit is written row by row into the block's row-major form: 4 whole 64-byte lines per token (see row-major tail block)."
- The changes, tensor/k_vnni.hpp: "the row-major tail block operations: `row_major_row` (a token's row inside a row-major block, as a typed row view), `store_row_major`, `load_row_major`, and `block_to_vnni` / `block_to_rows` (the in-place conversion of one 16-token block, 4 KiB read and 4 KiB written), with Note [Row-major tail block]."
- The changes, kv_cache.hpp: "The K layout state per page and storage slot: the saved-row bits and the converted-block bits (one extra entry for the EAGLE storage), with `note_k_row_saved`, `note_k_block_saved`, `k_block_to_vnni` / `k_block_to_vnni_at`, `k_vnni_blocks`, `k_storage_ref` / `k_storage_of`, `k_row_if_row_major` and `k_forget_row` (a new token at a page offset drops the bits at and above it and converts the offset's block back to row-major)."; "Layout-independent `set_k_row`, `get_k_row` (typed row views) and `set_k_block` serve both layouts. `set_k_row` and `get_k_row` follow the block's recorded layout (packed column or row-major row). `set_k_block` stores whole blocks."; "Other ranges are copied token by token through row-major rows: the converted destination blocks the range touches are made row-major first, and a block whose 16 rows are saved after the copy is converted. The bits travel with the rows."
- The changes, model.hpp: "A unit that fills a whole block takes the block save; a shorter unit is stored row by row into the row-major block."
- The changes, self_attention.hpp: "The dense AMX path takes a page only when its 4 blocks are converted (`k_layout_dense`)"; "The software path scores the live tokens (the tokens present in the page) of the converted blocks in one AVX-512 loop over the page (`k_vnni::qk_group`), and the tokens of a row-major tail block with the row-major dotter through `row_major_row`."
- The changes, FPGA staging: "`k_head_fn` returns a row of a row-major block in place (`k_row_if_row_major`) and writes the row of a converted block into a scratch buffer (temporary memory) that the caller owns, through a typed destination row. `v_head_fn` already worked that way. `gof::populate` allocates the scratch. The `k_head_fn` lambdas of `t_gof_dma`, `t_gof_staging_leaks` and `t_phase1_integration` gain the scratch-buffer parameter."
- The changes, Tests: t_k_vnni_layout "... the tail-block conversion (bit for bit against `store_row`, no other block touched), and the page state: the block turns VNNI at the 16th saved row and back when a row is forgotten, a row saved again, the EAGLE storage view, forgetting a row in several slots, and page appends that carry the state."; t_amx_dispatch_dtype "... a case where a full page with unrecorded rows takes the software loop under `TRON_K_VNNI`."; t_llama_unit "a model-level shared-save case (the queued block and its forward-end conversion; with a hardware-scored operation, no conversion; with another operation hardware-scored, conversion), an apply-and-join case that scores a page with converted and row-major blocks".
- Verification: "Under CPU attention this head reproduces the tokens of `main` in both cells: the rows of a decode step land in a row-major block that the row-major dotter scores, as on `main`. Under FPGA attention the difference from `main` at generated token 52 is the same as the previous head's."

The hardware-attention policy:
- Words row "hardware-scored operation": "An attention operation whose scores come from the FPGA (the model's hardware attention). Its K blocks are never converted: the FPGA staging reads the rows in place, and the CPU scores only the tail the FPGA has not processed. Note [Row-major blocks under hardware attention] in `kv_cache.hpp` (the fix of issue #4500)."
- The changes, model.hpp: "After the join, `save_k` records the saved rows of a software-scored operation. A block that is complete because of this pass is queued (`pending_k_blocks_`) and converted at the forward end (`convert_pending_k_blocks`, after the cooperative GOF staging drained). The rows of a hardware-scored operation are not recorded, so their blocks stay row-major."
- Measurements reading: "The two qwen3-4b configs with FPGA attention are inside the noise (-0.9 % and -0.4 %, not resolved). They are the configs of issue #4500. The blocks of a hardware-scored operation stay row-major."
- Open items, kill switch item, last sentence: "The tokens of a row-major tail block are scored by the row-major dotter in both the AMX-on and the kill-switch run of this binary, so those two runs stay identical."

The conversion at the forward end: the model.hpp sentence above ("queued (`pending_k_blocks_`) and converted at the forward end (`convert_pending_k_blocks`, after the cooperative GOF staging drained)") and the Words row "converted block" ("or at the end of the forward pass that saved the 16th row").

The deb preset:
- The changes, CMake: "The `deb` preset (`CMakePresets.json`, the released package) sets it ON next to `TRON_AMX_DISPATCH`, so the package stores K in the VNNI layout on every host." The same bullet also says "CMake option `TRON_K_VNNI` (default OFF, requires `TRON_AMX_DISPATCH`, ...)"; the "requires" clause does not hold for the stack (D2 removed it) and must not be carried.
- Measurements: "This branch = 9d5c7a389b built with the `deb` preset and `TRON_K_VNNI=ON`, the preset line that the head 0a5334ccb6 carries (the same package the head builds)."
- Verification: "The head 0a5334ccb6 adds the `deb` preset line and a `README.ci.md` paragraph to it."
- The B patch itself: CMakePresets.json adds `"TRON_K_VNNI": "ON"` after `"TRON_AMX_DISPATCH": "ON"` in the deb preset; README.ci.md replaces "The option is OFF by default in every other build." by "The `deb` preset also sets the option ON, next to `TRON_AMX_DISPATCH`, so the released package stores K in that layout on every host: the layout does not depend on AMX, only the reader does (the AMX kernel on hosts with AMX, the AVX-512 reader of the layout elsewhere). Every other preset leaves it at its default OFF." [handoff-material/ref/B-preset.diff].

### 6.3 Sentences that describe the pre-T state (the 64-line decode scatter and the masked partial block): must NOT be carried into PR-4's body

- Short version, sentences 2 to 4: "For passes of more than 16 tokens, the store uses a shared block save: runs of 2 to 16 tokens are transposed in registers and written as 64-byte cache lines by the main thread and its idle helper threads. A single token, as in every decode step, does not form a block. Its 64 dimension pairs are written one by one into 64 cache lines." [pr4424-body-live.md:3]
- "Use shared block in saving K", items 2 and 3: "2 to 15 tokens (prefill edges): the same, but each line store is masked to the run's tokens." and "1 token (decode): no transpose. Each of the 4 steps loads 64 bytes of the row into one register and scatters its 16 pairs into 16 cache lines, 4 bytes each: 4 scatters, 64 cache lines." [pr4424-body-live.md:22-25]
- Open items, kv_mul item: "The decode store also scatters into cold lines (64-byte cache lines not yet present in the CPU cache)." [pr4424-body-live.md:233]
- The live body is inconsistent with itself: its Short version and "Use shared block in saving K" describe the pre-T store, while its Words rows ("shared block save", "row-major tail block") and "The changes" describe the T store.

### 6.4 The Open items of the PR 4424 body (titles)

"genoa96 cost row for `t_k_vnni_layout`"; "128-dimension heads with kv_mul (the number of query heads that share one KV head) other than 4"; "Benchmark binary mismatch (reviewers decide)"; "Kill switch and token divergence (tracked in issue #4444, reviewers decide)"; "A `main` test tolerance is widened"; "Cost rows refresh" [pr4424-body-live.md:230-238]. The cost-rows item says: the granite_rapids_6962p rows for t_llama_unit, t_k_vnni_layout and t_amx_numerics were measured at 6b939d25d2 (2026-10-08), the tail-block cases make t_k_vnni_layout and t_llama_unit longer, and `bin/slice bench --update` of the three tests on the whole machine refreshes them. The Verification section gives those rows: t_llama_unit 28.1 / 28.3 / 28.3 s, t_k_vnni_layout 0.90 / 0.91 / 0.91 s, t_amx_numerics 0.81 / 0.83 / 0.74 s (run time at 1, 2 and 4 slices).

### 6.5 Words rows of the PR 4424 body that PR-4's body can reuse (row names)

AMX, VNNI; VNNI layout; row-major K; page; prefill, decode; KV head; plane; tp2, tp4; TPS; PR #4557, typed KV-cache tensors; owner, view; row view; main thread, main helpers; save_k, Save K; shared block save (its T-state wording); dotter; row-major tail block; converted block; hardware-scored operation; nightly CI, perf configs; TTFT, paired t, resolved; VmHWM; kill switch; base (needs rewriting: PR-4's base is PR-3's head and main at 72308ec90c, not be0d5565b3); greedy run, A/A repeat; slot; dense page; slice check, cost data [pr4424-body-live.md:29-60].

### 6.6 The PR 4737 body (pr4737-body.md, 3,162 bytes)

It has no markdown headings; its parts are "Short version:", "**Behavior**", "**Validation**" and "Related:". Base jhan-amx-vnniK at 30c4ac82cb, head jhan-amx-vnniK-i4500 at bb32a80774. Its behaviour bullets: "A write covering fewer than 16 tokens stores contiguous rows inside the block's existing storage. A full 16-token write still stores the VNNI layout directly."; "For software attention, completed row-major blocks convert in place after the model execution joins its workers and drains cooperative staging work."; "For operations configured to use FPGA attention (...), short writes leave the blocks row-major. This avoids conversions and later gathers that the hardware path does not need."; "Each cache page records saved rows and converted blocks. Readers select the matching layout. Page copies and token reuse preserve that state."; "Hardware staging reads a row-major key directly. Converted keys still use the existing gather into temporary storage."; "Tests cover mixed layouts, conversion, copying, token reuse, attention dispatch, model saves, and the separate storage view used by EAGLE speculative decoding." Validation: tests at 452b2052c9 on 2026-09-30 (records exec/results/i4500b-20260930/build-fixS1.txt, build-fixS1rm.txt, tests-fixS1.txt, tests-fixS1rm.txt) and at 9e813a8ce5 on 2026-10-01 (exec/results/pr4737-review-20261001/tests-r1.txt, tests-r1rm.txt); "Hardware measurements (TPS, TTFT, generated tokens) are from 452b2052c9."; "The full host suite was not run." [pr4737-body.md].

## 7. The PR-3 body (exec/pr3-20261012/pr-body.md, 61,262 bytes)

Section headings [pr-body.md line numbers]: "## Short version" (1); "### Background" (5); "## Words used here" (19); "## The changes" (66); "## Measurements" (118); "### The TTFT gain of the block save (new vs head)" (182); "### Decode TPS against the kernel PR (new vs head)" (193); "### This PR against `main` (new vs base)" (204); "### The store under the reader (newoff vs headoff)" (217); "### The kill switch inside this PR (newoff vs new)" (232); "### The kernel PR against `main` in this session (head vs base)" (247); "## Verification" (262); "### Host test suite and token identity (2026-10-12)" (348); "### CI coverage" (398); "## Open items" (409); "## The stack" (464).

Words rows (42, names only): PR, main, stack, the layout PR, the kernel PR; tron, runtron; token, generated token, layer; attention, head, Q, K, V; CPU, FPGA; AMX, AVX-512, VNNI; VNNI layout, packed; row-major K; plane, panel, token block, dimension step; line, dword, scatter, masked store; the kernel, the reader, the dotter; store_row, the per-row store, the scatter store; store_block, the block save, transpose; present mask, masked partial block; set_k_row, set_k_block; run, work unit, unit table; minibatch, item, KV-write flag; main thread, main helpers, worker index, n_workers; window, claim counter, join, watchdog; generated plugin, handwritten plugin, code generator, attention statement; LoopyTronSpec, cabal, Sydtest, fourmolu, lint-notes; the option, CMake, preset; AMX dispatch; kill switch, AMX-on, AMX-off; KV page, slot, geometry; KV head, kv_mul; prefill, decode, pass; owner, view; completion marks, dispatch credits; bf16, fp32; Catch2, REQUIRE, SECTION, CAPTURE, SUCCEED; mutation check; poison pattern; tp2, tp4, slice; TPS, TTFT; base, new, new2, newoff, head, headoff; greedy run, A/A repeat; cell, band, standard deviation, paired t; CI, GCP Nix, legacy CMake lane; runner, Granite Rapids; slice check, cost data; worktree, translation unit [pr-body.md:19-64].

The stack table's PR-4 row, verbatim [pr-body.md:473]: "| 4 | `jhan-vnnik-4-tail-block`, based on this PR | A row-major tail block: a 16-token block with unsaved rows stays row-major. It converts to the packed layout when all 16 rows are saved. A row-major policy under hardware attention (FPGA attention) addresses issue #4500. The `deb` package-build preset enables the option in the released package. | to follow as a draft |". The sentence after the table: "The option stays off in every preset until PR 4. Intermediate states therefore do not enter production through those presets." [pr-body.md:475]

Open items titles, verbatim [pr-body.md:411-461]: "The masked partial-block path."; "The single-token store of decode steps."; "The join watchdog and the worker cap."; "128-dimension heads with kv_mul other than 4 query heads."; "Kill switch and token divergence. Reviewers decide. [Issue #4444]"; "A control difference beyond the band."; "Cost data of t_k_vnni_layout and t_llama_unit."; "Benchmark binary mismatch, inherited from PR #3879. Reviewers decide."; "CI coverage gap. [Issue #4865]". Two of them bind PR-4: the masked-path item says "The fourth PR of the stack replaces it with the row-major tail block: a run shorter than a block is stored row by row into a row-major block. That block converts to the packed layout when all 16 rows are saved. The fourth PR also removes the present mask parameter of `set_k_block`."; the single-token item says "A run of one token, as in every decode step, keeps the per-row scatter store: 4 scatters that touch 64 lines per (token, KV head) row. Under FPGA attention that per-token column access is the decode loss of issue #4500. The fourth PR's row-major tail block is its subject."; the cost-data item says "The refresh is planned with the fourth PR's cost-row update."

Measurements table form [pr-body.md:140-181]. A "Configurations" list defines the arms (`base`: `main` at `72308ec90c`, row-major K, AMX dispatch on; `new`: this branch; `head`: the kernel PR; `newoff` and `headoff`: with the kill switch), then an experiment list (model, load, attention, cells, repetitions, allocation), then the band rule ("twice the larger of the two binaries' standard deviations ... never smaller than 0.4 TPS for throughput or 0.15 s for TTFT"). Table 1 headers: "| Cell | Binary | TPS (tokens/s/user) | TTFT (s) |", one row per cell x arm (15 rows), values as "mean (sd)". Table 2 headers: "| Cell | Pair | TPS difference (paired t) | TTFT difference (paired t) | Band (TPS / TTFT) |", one row per cell x pair (15 rows), values as "+5.1 % (+4.16 TPS, t +14.6), beyond" and "-57 ms (-1.8 %, t -22.5), inside". Cells are written "tp2, 1,024 tokens". The PR-3 numbers in those tables are in split-status.md:370-386 and section 4.3 above does not repeat them.

--- concerns ---
- The "-3.8 % / -11.8 % to -0.9 % / -0.4 %" claim of split-plan.md:154 joins two setups: the loss is from i4500fix-20260928 (one rinzler engine on our half, 2 users at tp2 and 4 users at tp4, base = the canonical AMX deb of main 3faba6d0fd, 2026-09-29, n = 3, tp4 paired t 1.68 below the 4.30 threshold, vnni-arm sd 17.30 TPS), and the recovery is from pr4424ci-20261009 (whole machine, nightly layout, base = the nightly deb 2026.10.08-be0d5565, n = 2 passes). PR-4's body must state both setups or measure one setup at PR-4's head.
- No record measures the T content (tail block + policy) at 8 users on one engine under FPGA attention; the only 8-user one-engine FPGA record (issue4500-20260918, m1) is the pre-S scatter tree ff680c8020. The PR-4 chain's E row in split-handoff.md 5.3 lists CPU-attention cells only; if PR-4's body wants an FPGA-attention qwen3-4b claim at its own head, the chain needs FPGA cells (runtron, our half) or the W campaign (nightly layout, whole machine).
- The t_llama_unit and t_amx_dispatch_dtype expected counts for PR-4 are estimates: T adds SECTIONs to existing cases (two to the save_k case that PR-3 rewrote, one to the single t_amx_dispatch_dtype case), and Catch2 re-runs top-level assertions once per leaf section, so the 2026-10-08 deltas (+7265 / +7241 and +525) need not add exactly. Only t_k_vnni_layout (+5 separate cases, 10 total) is additive. The handoff should say "record the count" for those two binaries.
- The merge4737-20261008 chain's first test run (tip 3723bf601a, 2026-10-08T23:43:29Z) failed t_llama_unit at t/t_llama_unit.cpp:3890 (rc 42) before the passing run at 9d5c7a389b five minutes later; the record does not say what changed. The probe's conflict resolution of T onto PR-3's rewritten save_k case could reproduce a similar failure; the executor should expect to debug t_llama_unit's save_k case.
- The PR 4424 live body contradicts itself: its Short version and "Use shared block in saving K" describe the pre-T store (64-line scatter per decode token, masked 2-to-15-token stores), while its Words rows and "The changes" describe the T store (row-major tail block, 4 whole lines per token). PR-4's body must take only the T-state sentences, and its "CMake option" bullet's "requires TRON_AMX_DISPATCH" clause does not hold for the stack (D2).
- The m4737-E-cpu summary.md header names the wrong arms (inherited from the sync4424 script: "base = PR #4557 head c12df586b6, head = PR #4424 head 30c4ac82cb, new = the synced branch (PR #4746)"); the true arms are in rt-results.txt (base = main be0d5565b3, new = 9d5c7a389b). Cite rt-results.txt, not the summary header, for the arm identities.
- Neither 2026-10-08 chain ran t_llama_unit with the kill switch nor built the AMX-off (option on, dispatch off) configuration, so PR-4's AMX-off expected counts rest on PR-3's A3 record plus the VNNI-build deltas, not on a measured AMX-off reference.
- The 2026-09-14/15 trace analyses do not name a "64-line scatter"; they give the decode Save K span (28 to 29 us per layer at tp2, about 445 ns per (token, KV head) row, against 4.6 us and 72 ns with row-major K). Any PR-4 sentence that quotes "64 lines" from those records is an interpretation, and the trace folder's name date (20260915) differs from the recording date in runs.txt (2026-09-14 UTC).
- i4500c-20260930 (perf record) is incomplete ("2 reports missing") and its README states a remaining decode Save K gap of the policy build against the canonical build (105 vs 58 us per pass at tp2 2 users; 171 vs 111 us at tp4 4 users) that is not explained; PR-4's body should not claim the tail block makes the decode store equal to row-major K's cost without a measurement at PR-4's head.
- The q4b-fpga-20260921 folder has no summary.md and no VNNI arm; it cannot back a VNNI claim. Its only use for PR-4 is as a reference of the nightly-layout qwen3-4b tp2 FPGA numbers of 2026-09-21/22 (fpgabase 184.03 to 185.79 TPS across three passes).
