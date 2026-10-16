---
name: ci-amx-regression-20261009
description: 2026-10-09 "AMX CI/CD perf regressed" email investigation - prefill/TTFT-only shift of the 32-user llama-3.1-8b row, the 10 merges be0d5565..26b6df7d, evidence that the machine (not the code) may have changed, and the pending A/B
metadata:
  type: project
---

Investigated 2026-10-09 (report: ~/workspace/intel-AMX/CI-test/status/CI-AMX-regression-20261009.html;
generator + numbers in the session scratchpad were not kept; numbers are reproducible from the monitor logs
~/workspace/random/amx-ci-monitor/logs/2026-*-fetch.json and GitHub runs 37724297930 / 37880831014).

- Trigger: the monitor's prefill minimum (353 tok/s = TTFT 11,603 ms at the 4,096-token prompt) fired, not decode.
  AMX row 10-08 -> 10-09: TTFT 11,517 -> 11,931 ms (+3.6 %, 10 sd above the 13-night mean 11,561 +- 37), decode
  32.71 -> 32.56 TPS (inside the 32.40-32.78 range). The CI's own threshold (31.00) passed. Every other row stayed
  inside its range; the same model's 8-user/1,024 row was unchanged (660 ms both nights).
- Signature: sorted per-round TTFTs show the first 9 of 32 users unchanged and a flat +500 ms from the 12th user on
  (mixed prefill+decode phase), not a uniform slowdown.
- Packages: 10-08 = 2026.10.08-be0d5565, 10-09 = 2026.10.09-26b6df7d; 10 first-parent merges between. Only #4366
  (BF16 round-to-nearest stores; llama host kernels + V-cache append on the AMX path) and #4784 (FPGA tx_launch skips
  the wcmd mutex when prepare already posted) touch this test's code; #4709 (rinzler Qwen protocol) is low; the rest
  (#4719/#4723 generated-plugin loop helpers, #4782 MoE, #3906/#3907/#3393 ingest, #4801 nix) do not.
- Machine evidence: jhan's pr4424ci campaign re-ran the OLD package be0d5565 on 10-09 13:51-14:05 UTC with the
  nightly's own client code and got 11,814 ms (+297 vs the 10-08 nightly); on 09-20 the same method read 20-60 ms
  BELOW the nightlies. Everything measured after 10-09 04:00 UTC is 11.79-11.93 s regardless of package. Checks found
  nothing wrong (no reboot, SST verified, EPP performance, no throttling now at 3.9 GHz busy cores, PL1 500 W, PCIe
  x16 Gen4 on all 8 cards, clean kernel log, no other tenants). Not recorded: CPU freq/temps during the 04:19 test.
- Monitor note: the prefill minimum has ~0.1 % headroom over the normal range (10-01 passed only by rounding 352.7->353).

**Why:** the next regression email needs the same split (CI threshold vs monitor threshold; TTFT vs decode; code vs
machine), and the calibration facts above are not stored anywhere else.

**How to apply:** decide code-vs-machine with a back-to-back A/B on delphi-3bda: both debs are saved as
/var/tmp/jhan/pr4424ci-20261009/nightly.deb (be0d5565) and restore.deb (26b6df7d); run the two llama-3.1-8b configs
new/old/new/old with the campaign driver (about 1 h). If code: bisect by reverting #4366 and #4784 on 26b6df7d.
Related: [[ci-merge-audit-0922-0923]], [[3bda-ci-amx-shape-models-2026-09-18]].

UPDATE 2026-10-13: a machine-state change was found between the 10-08 and 10-09 nightlies: John Mark's helper enabled Speed Select core-power (ordered priority) at 2026-10-08 21:56:47 UTC; associations unchanged. Candidate for the TTFT shift; details in [[3bda-platformd-sst-dev-build-2026-10-07]].
