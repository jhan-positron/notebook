# Plan: PR #4424 open item "128-dimension heads with kv_mul other than 4" (2026-09-16)

Short version. One run showed qwen-3-30b-a3b (kv_mul 8) losing 5.4% decode TPS with the VNNI K
layout. This campaign repeats that cell with 6 repetitions against a `main` binary, adds a third
binary that is the PR head with the layout compiled off, and traces one run per binary to
attribute the loss to the reader or to the decode store. The report goes to
VNNIed-K-in-place/status/Wednesday-morning-report.html.

Words used here: tron = the inference program under test; runtron = its command-line tool;
VNNI layout = the pair-interleaved K layout of PR #4424; kv_mul = query heads per KV head
(qwen-3-30b-a3b: 32 query heads / 4 KV heads = 8); AMX = Intel Advanced Matrix Extensions, the
tile-multiply instruction set; the AMX kernel serves head size 128 with kv_mul 4 only; TPS =
generated tokens per second per user in decode; TTFT = time to first token (runtron's "Parsing
the prompt took"); cell = one (model, tp, prompt length, binary) combination run with 8 users
and 256 generated tokens; smoke = 1-user greedy run of 128 tokens whose token ids are saved;
A/A = the same binary run twice as the noise control; our half = socket 1 + FPGA cards
90/93/b9/bc of delphi-3bda (tron `--instance 1,2`; tp2 uses `--instance 2,4`).

## 1. What the open item claims and what decides it

| claim in the PR item | how this campaign tests it |
|---|---|
| decode TPS loss (-5.4%, one run) | 6 interleaved repetitions per binary at tp2 prompt 1024, 4 at tp4; A/A noise from the repetitions; paired per-repetition deltas |
| TTFT gain (-369 ms, one run) | the same cells (TTFT is read from the same runs) |
| cause = the AVX-512 reader of the layout (every page, kv_mul 8) | the loss should grow with the prompt length (more pages per step): cells at prompt 1024, 2048, 8192; traces show the attention workers' time per decode step |
| cause = the decode store scattering into cold lines | the store cost is per token, not per page: constant across prompt lengths; the traces show the "Save K" span per layer in decode |
| remedy (a): gate the layout on kv_mul 4 | the binary `headoff` (PR head built with TRON_K_VNNI=OFF) is what a gated build would run for this model; its cells show whether that gives `main`'s numbers back |
| remedy (b): reader work for larger groups | code analysis (workflow): instruction mix, access pattern, register use of `k_vnni::qk_group<8>` versus the dotter |

## 2. Binaries

| binary | commit | CMake options (all with preset cross-avx512, BUILD_INGEST_MODELS=ON) | role |
|---|---|---|---|
| runtron.main0916 | c7844ca2ce (origin/main at the rebase = merge base of the PR) | TRON_AMX_DISPATCH=ON | base: row-major K, the dotter |
| runtron.headoff0916 | ff680c8020 (PR #4424 head) | TRON_AMX_DISPATCH=ON, TRON_K_VNNI off | the PR's code with the layout off = what a kv_mul gate would run for this model |
| runtron.vnnik5 (exists) | 65a1c41d72 (= PR head minus the cost-data JSON commit; same C++) | TRON_AMX_DISPATCH=ON, TRON_K_VNNI=ON | the PR: VNNI layout on for this model, AVX-512 reader on every page |

For qwen-3-30b-a3b the AMX kernel is not eligible in any of the three (kv_mul 8), so AMX on/off
arms are not run: the kill switch would change nothing for this shape.

## 3. Cells (model ingested-qwen-3-30b-a3b-instruct-2507, CPU attention USE_HW_ATTN=0, 8 users, 256 tokens)

| order | cell | repetitions per binary | why |
|---|---|---|---|
| 1 | smoke tp2 prompt 1024 (1 user, greedy, 128 tokens): base, base2, headoff, vnni, vnni2 | 1 each | token identity: base == headoff expected; base vs vnni diverged at token 5 before; A/A pairs |
| 2 | tp2 prompt 1024 | 6 | the reported cell; primary decision data |
| 3 | tp4 prompt 1024 | 4 | the store showed most at tp4 for qwen3-4b |
| 4 | traces tp2 + tp4 prompt 1024, 32 generated tokens, passes 1-24 | 1 | attribution: Save K per layer, attention time per decode step |
| 5 | tp2 prompt 2048 | 3 | prompt-length trend |
| 6 | tp2 prompt 8192 | 3 | prompt-length trend, TTFT at long prompts |
| 7 | tp4 prompt 8192 | 2 | same at tp4 |

Binaries interleave inside every repetition (base, headoff, vnni, base, headoff, vnni, ...).
One tp2 run at prompt 1024 took about 40 s in the 2026-09-15 cell (25 s model load, 5 s prefill,
7 s decode), so the whole list is about 100 min after the two builds (about 20 min).

## 4. Machine rules

- Everything runs on our half. Bill's marker is present (2026-09-16 03:59 UTC), so the first half is his.
- Nothing heavy starts before the nightly CI releases the lease (/run/lock/systems-test-ci.lease).
  The run 35052594106 started 03:39 UTC; the lease cleared at 11:30 to 13:20 UTC on recent days.
- Leftover rinzler@N units after the nightly: wait_clear calls rinzler_takeover_if_idle
  (lib-guard.sh; stops them after 10 idle minutes, outside the 01:40-04:30 UTC hold).
- Guards per run: campaign_guard_acquire (lease, other persons, blackout, flock, no runtron of ours),
  a 10-s watcher that kills our runtron if the lease turns busy, `env -u SYSTEM_CONFIG` on every
  tron process, hugepage slice files removed after each run.

## 5. Deliverables

- exec/results/vnnik6-20260916/ (build-*.txt, smoke/, rt/, rt-results.txt, summary.json, summary.md),
  exec/results/vnnik6-trace-20260916/ (traces, analysis.json, analysis.md).
- VNNIed-K-in-place/status/Wednesday-morning-report.html (generator exec/vnnik6-20260916/gen_report.py):
  Short version, words, the question, what was run, results (dot plots + tables), attribution
  (traces, prompt-length trend), what each remedy takes (code analysis), recommendation, raw data
  for a reviewing agent, traps.
- PR #4424 body: the open item updated with the measured numbers (jhan decides the wording).

## 6. Decision rule (pre-registered)

- "Loss confirmed" = the mean decode TPS of vnni is below base at tp2 prompt 1024 by more than
  two standard deviations of the per-repetition paired difference, with 6 repetitions.
- "headoff == base" = their means differ by less than one standard deviation of the paired
  difference. If headoff is slower than base, the PR's row-major path itself costs something for
  this model, and a gate alone will not give main's numbers back.
- Attribution: if the vnni loss grows from prompt 1024 to 8192 (in ms per step), the reader is the
  main cause; if it stays flat in ms per step, the store is.
