---
name: l8b-levers-20260919-campaign
description: "T0 llama-8b levers campaign (users x prompt grid, CI harness, nightly layout, whole 3bda, base vs canon deb, 3 passes) run 2026-09-19 per CI-test/status/Saturday-plan.md; scripts, results paths, verified machine facts and traps"
metadata: 
  node_type: memory
  type: project
  originSessionId: d663273f-b92f-4151-8123-4162a86b1dbe
  modified: 2026-09-19T07:52:37.130Z
---

Campaign = test T0 of PR3879/new-PRs/PR1/CI-AMX-test-shapes.html (v2): AMX gain on llama-3.1-8b vs users per engine
(1, 2, 4, 8) and prompt length (1024 to 8192), CI harness in the nightly layout, whole delphi-3bda, nightly deb
2026.09.18-3faba6d0 (clean) vs tron_2026.09.18-0594dc54-jhan-ci-canon (canonical AMX), 3 interleaved passes, 10 configs.
Handoff/plan: ~/workspace/intel-AMX/CI-test/status/Saturday-plan.md (sections 2a = standing decisions, 7 = decision rule).
Scripts: exec/l8b-levers-20260919/ (campaign.sh, launch.sh, dut.sh copy, st_ci_perf.py, configs*.json, prompt_check.py,
analyze.py). Results: exec/results/l8b-levers-20260919/ (<arm>-pass<k>/perf.json, check-32u-p8192/, prompt-check/,
summary.json). Report target: CI-test/status/Saturday-llama-3.1-8b.html; results feed gen_ci_shapes.py as source tag H.
Prompt-source change lives UNCOMMITTED in ~/workspace/ai-runs/systems_test/testlib/prompt.py (patch saved next to the
scripts); the nightly's own checkout is untouched.

**Verified 2026-09-19 (machine facts, reuse):**
- platformd v0.10.7 -> the harness takes the LEGACY posadm provisioning path; a same-model provision does NOT restart
  engines, so after every package switch the engines must be restarted (dut.sh serving-down then serving-up) or they keep
  running the deleted old binary.
- The rinzler journal has NO per-request line; the dut.sh idle-test request grep always counts 0. The idle test is decided
  by the #EVT# SYSTEM_STATS line (every ~5-6 min: Open/Closed/Busy/Total). Per-engine request counts come from the FUSE
  stats /var/run/rinzler/N/rinzler/stats/prompts_total (admitted requests since process start, readable as jhan, no
  sudo); monitor/cumulative/{completed_sessions,tokens_generated,tokens_prompted,...} also exist.
- ShareGPT conversations with the llama-3.1-8b tokenizer: min 1511, median 2045, max 21126 tokens; 501 of 1000 shorter
  than 2048. Concatenating following conversations (seed+k) fixes "Prompt length too short"; prompt-1024 output unchanged.
- Bash trap: `if run_pass; then ...; fi; rc=$?` gives the if-statement's status (0), never the command's. Capture rc first.
- Bash trap: a retry helper that prints its messages with `say` (stdout) pollutes `$(helper | awk ...)` captures; send
  them to stderr and validate captured values (a sha must match ^[0-9a-f]{64}$).
- Review traps (two adversarial rounds, 35 confirmed findings, files review-findings.txt / review2-findings.txt): the
  restore path must wait for the DUT and retry ssh-level failures (the outage that stops a campaign also breaks the
  restore); a check-cell timeout is evidence only if 'Running round' appears in driver.log; harness 'anomalous tps='
  lines are printed in the worker processes (count them from the talos-stub samples in the parent); after a failed
  cell the ProcessPool workers block forever, so exit with os._exit after killing multiprocessing.active_children().
- KEY FINDING 2026-09-19 13:3x UTC: rinzler on the nightly deployment TRUNCATES chat prompts above 4096 tokens for
  llama-3.1-8b-instruct-good (check cell 32u x 8192: harness sent 8192-token prompts, every SESSION_OPEN said
  "prompt 4096 tokens", usage prompt_tokens=4096; FUSE config max_prompt_tokens = max_total_tokens = 131072, so the cap
  is elsewhere). ROOT CAUSE (verified 13:5x UTC): the deployed weights cache
  /opt/positron/weights_cache/cached/neuralmagic/Meta-Llama-3.1-8B-Instruct-quantized.w4a16/tokenizer.json carries
  "truncation": {direction Right, max_length 4096, strategy LongestFirst}; the stock HF file has truncation null; tron's
  rust tokenizer (rust/tokenizers/src/lib.rs encode) never calls with_truncation(None), so the first 4096 tokens are kept
  and the rest silently dropped for llama-3.1-8b-instruct-good/-best (same weights dir). The 70b w4a16 cache
  (llama-3.1-70b-instruct-good) has the same block with max_length 8192; all other cached models have none.
  PROVENANCE (verified 2026-09-19 16:0x UTC via the HF commit history): NOT a Positron edit and NOT in any Positron
  GitHub repo. Weights live on the fleet NFS store /opt/positron/weights/huggingface/<org>/<model> (downloaded by hfget,
  copied to /opt/positron/weights_cache/cached by cache_weights.sh cron); tron config/models.yaml only names
  default_weights. Neural Magic's own upload carried the block from the first commit (8b: 822ee826a7 2024-07-26, max 4096;
  70b: b74ae47a31 2024-07-31, max 8192; their calibration code `tokenizer(text, max_length=max_seq_len, truncation=True)`
  mutates the tokenizer state and save_pretrained serialized it). They re-uploaded tokenizer.json on 2024-09-30
  (8b 1455f0f5f7 20:40 UTC, 70b 5ce1373819 20:41 UTC, author alexmarques): truncation null and a new post_processor.
  Positron downloaded both models on 2024-09-10 (70b .cache metadata: commit 8c670bcdb2, ts 1725930963; 8b file
  sha 4a49a5d5 == revision 8ecfb5aa0d exactly), 20 days before the fix, and never refreshed (`hfget outdated` would show it).
  Same bug class hit Positron's paibaker later (PR #153, 2026-04-10: callable check truncation=10 shipped in 59 artifacts).
  jhan's DECISION 2026-09-19: do NOTHING about the truncation (no repair, no report to the CI team, no issue); the
  finding stays documented in the report page only. Fix path if he ever changes his mind: hfget repair/re-download of the two neuralmagic dirs on the NFS store, then the cache cron;
  the fixed file also changes post_processor (ByteLevel -> Sequence with the BOS template); tron encodes with
  add_special_tokens=false so token ids are unchanged, but verify with VALIDATE_TOKENIZERS=true before rollout. Consequence: the 7168/8192 cells were dropped (7-config grid),
  the 16K pair is lost, and a long-prompt CI shape (T2) above 4096 is impossible without changing the server.
- Run history: first launch 09:29 UTC waited for the lease (free 13:14), check cell 32u x 8192 passed (12 min, 32.25 TPS,
  TTFT 11.5 s, AMX-busy 30.7e9), then STOPPED by me at 13:35 (truncation) and restored cleanly; relaunched 13:43 UTC
  (pid 2152762, CHECK=0, configs-no7168.json) gated on the peer session's issue4500 runtron work (our half, ends ~15:00).
- RESULTS (final, 3 pairs, all 7 cells complete; report CI-test/status/Saturday-llama-3.1-8b.html; page v3 has data H):
  gain canon vs nightly deb: 2u x 1024 +0.21 % (t 0.5, n.r.), 2u x 2048 +1.55, 2u x 3000 +7.30, 2u x 4096 +8.19,
  4u x 1024 +4.75, 8u x 1024 +10.79 (T1; 67.03 -> 74.26 TPS, slowest 60.13/66.06, TTFT 738/683 ms, 5.3 min per cell),
  8u x 2048 +13.99; all resolved except 2u x 1024. Both pre-registered bands hold (+0.2..1.2 and 9.9..15.9). 16K pair
  lost (7168 truncated); 8K triple undecided (1-user cell dropped; the two 2-minibatch cells differ by 2.55 points).
  Even Caddy spread in every run, 0 Caddy health events, AMX-busy 0 (base) / 29-30e9 (canon) in every probe,
  measured server overhead 34 tokens (plan assumed 31). Passes 28-31 min each; whole campaign 14:26-17:55 UTC.
- Peer coordination trap: another session's campaign may hold the campaign flock only per runtron run; gate on
  `pgrep -f '[r]untron[. ]|[i]ssue4500.*campaign[.]sh'` (self-match-proof pattern), not on `flock -n`.

**Why:** the plan pre-decides everything so the agent runs the campaign without jhan; these facts were not written anywhere.
**How to apply:** for any later campaign on 3bda reuse the FUSE counters, the restart-after-switch rule and the driver
copies here; check the plan file's section 2a before deviating. Related: [[canon-ci-20260918-campaign]], [[ci-amx-test-shapes-recommendation]],
[[3bda-shared-with-bill]], [[nfs-attr-cache-build-trap]].
