---
name: nightly-amx-check-20260916
description: "2026-09-16/17: why the nightly System CI showed no AMX boost after PR 3879 merged: the apt deb (publish-deb.yml, preset deb) never sets TRON_AMX_DISPATCH, so tron 2026.09.16-f46e48ba has 0 AMX instructions; the 206.81-vs-185.96 TPS comparison was two machines (genoa96 vs 3bda); binary-check recipe with controls; page PR3879/new-PRs/PR1/nightly-amx-check-20260916.html"
metadata:
  type: project
---

Question (jhan 2026-09-16 evening PDT): PR 3879 merged; Hannah says CI compiles AMX
(cmake yaml has the option on); the nightly showed no TPS boost. Was AMX compiled in,
did it run? Page: PR3879/new-PRs/PR1/nightly-amx-check-20260916.html (generator
exec/nightly-amx-check-20260916/gen_page.py + evidence.json + slack-reports.tsv).

Published 2026-09-17 01:5x UTC: https://claude.ai/artifact/M7WV3mLkkAYt8J2GW1piDu (republish same file path or url=).
V2 FOR HANNAH (jhan 2026-09-17 ~02:00 UTC: "remove mentioning the 2 slack lines, it will confuse her; add a
section after Short version: what needs to be done and how"): the page now has NO machine comparison and
section 1 = 8 action steps (deb preset one-liner, no env change, AMD safety, timing 01:17/03:39 UTC, package
checks strings/objdump, runtime check strace arch_prctl 0x1023 at first dispatch, where the gain shows =
llama-3.1-8b-good tp2 [goal 144, nightly ~140 TPS, round-1 +13.9% -> est. ~159], gcp-nix lane gap). v1 with the
Slack/two-machine attribution kept as PR1/nightly-amx-check-20260916.v1-internal-with-slack-comparison.html
(generator gen_page.v1.py). Package builder compiler = Clang 19.1.7 = PR test lane compiler (deb log).
Section 1 verified by wf_5285df32-e6a (4 agents, 0 refuted). Facts learned there: AMX probe runs at the FIRST
software-attention call of an eligible model (amx_attn.cpp:84 static const; header Note says "process start" =
wrong), result cached per process; strace 5.16 prints `arch_prctl(0x1023 /* ARCH_??? */, 0x12) = 0`; the AMX
unit tests DO run in gcp-nix but as placeholder SUCCEED cases without the option; nightly crons 03:30 (3bda) /
03:00 (andoria) UTC, publish-deb cron 01:17 but runs start 01:31-01:40; llama-8b-good tp2 goal = mean 144 AND
min 140 (testlib/tps.py), nightly 139.78/139.98 mean, slowest 136.46/132.70; round-1 numbers came from binary
60d66d9c04 (pre-split) with USE_HW_ATTN=0; qwen-3-4b passes the shape test (only FPGA attention hides it);
deb preset + option combination already compiled (tron-p3879, 173 model variants).
Verified facts (2026-09-17 00:10-01:00 UTC, adversarial workflow wf_39c58401-d26):
- Two nightlies post to Slack #ci-cd-notifications (C06S8PNDBQA) every night: platform
  GRANITE_RAPIDS_72_RINZLER (DUT delphi-3bda, qwen tp2 goal 175/145) and GENOA96_RINZLER
  (DUT andoria-b1a3, AMD "Rinzler 96-core system" workflow, goal 195/170). The threshold
  in the Slack line identifies the machine (systems_test scripts/system_ci.py get_goal()).
  The raw run logs print 195/170 for BOTH machines (testlib/tps.py default goals).
  206.81 TPS = andoria 2026-09-15; 185.96 = 3bda 2026-09-16; 3bda 09-15 = 184.77.
- Merge: PR 3879 mergedAt 2026-09-15T22:54:27Z (Tuesday); merge commit 3fd5edaa66
  committer date 22:19:55Z. 09-15 nightly (03:39Z) ran deb 2026.09.14-875cd228 (ancestor,
  21 merges before the PR); 09-16 nightly ran 2026.09.16-f46e48ba (contains the PR).
- The nightly installs tron via apt-get (workflow lines 46-50; DUT apt pin o=unstable 900).
  The deb comes from tron publish-deb.yml (cron 01:17Z) -> make deb -> GNUmakefile:508
  `cmake --preset deb ...`; preset deb (CMakePresets.json:68-81) has no TRON_AMX_DISPATCH;
  option default OFF (CMakeLists.txt:48); src/tron/CMakeLists.txt:193-198 compiles
  kernels/amx_attn.cpp only when ON. Deb build run 35044660449: no amx_attn anywhere.
  Hannah's link = cmake-single-platform.yml (legacy "CMake and CTest" lane, flag at line
  355 on main; R333 in the PR diff). It compiled amx_attn.cpp.o on the PR's own runs
  (34375107972, 34621722240) but never ships, AND since the GCP Nix cutover (PR #4339,
  2026-09-11) it runs only on workflow_dispatch/workflow_call (publish-deb `test` job for
  tags/feature branches). Default PR/merge-queue lane = gcp-nix.yml, which lacks the flag
  -> TODAY NO DEFAULT CI LANE COMPILES AMX. PR #3879's own merge-queue checks were GCP Nix,
  Nix build validation, Debian smoke.
- BINARY CHECK RECIPE (stripped deb binary => nm is useless, "no symbols"):
  `objdump -d --no-show-raw-insn BIN | grep -c -E '(tdpbf16ps|tileloadd|tilestored|ldtilecfg|tilerelease)'`
  and `strings BIN | grep -c -x TRON_AMX_DISABLE` (the getenv literal survives stripping).
  /opt/positron/bin/rinzler (f46e48ba, 232 MB): 0 / 0 (44.3 M insns, 8784 avx512bf16, 0 AMX).
  Controls: tron-p3879/gen/runtron and tron-p0perf13/gen/rinzler (option ON): 86 / 1 /
  nm 10; tron-pre3879/gen/runtron (no AMX source): 0 / 0 / 0.
  Old debs stay in /var/cache/apt/archives/ on 3bda: extract with
  `dpkg-deb --fsys-tarfile X.deb | tar -xO ./opt/positron/bin/rinzler` (no host write);
  the 09-15 binary 875cd228 (202 MB) = 0 AMX instr, 2868 vdpbf16ps, USE_HW_ATTN string
  present, TRON_AMX_DISABLE absent. Installed rinzler sha256 == rinzler in cached deb.
  35 other TRON_* env literals survive stripping -> absence of TRON_AMX_DISABLE is meaningful.
  PR 3879 adds NOTHING unguarded (3 #include, 1 constant, 2 accessors used by guarded code).
  Runtime detection recipe for the first AMX-enabled nightly: strace -f -e trace=arch_prctl
  on rinzler start (0x1023 = ARCH_REQ_XCOMP_PERM at first dispatch); no log line exists.
- Runtime: journal Version lines prove the deb binary served every engine; zero "amx"
  journal lines but tron has NO AMX log statement, so journal silence is non-diagnostic.
  /etc/rinzler/instance-*.env: no USE_HW_ATTN / TRON_AMX_* / TRON_K_VNNI. Nightly qwen
  engines log "HW attention enabled ... engagement=127" (FPGA attention): even with AMX in
  the deb, the qwen lines will not move; llama-3.1-8b-good tp2 / mixtral tp2 (CPU attention)
  are where it would show.
- Every Slack report is FAILED (3bda 12 nights 09-05..09-16, andoria 11 nights 09-06..);
  3 lines fail every 3bda night (l8b tp2 mean <144, 70b tp2 8u <27, q25-32b slowest <35).
  NEW on 09-16: mixtral slowest user 69.72 (2 of 80 samples slow in round 9; andoria showed
  the same dip with the same deb) -> not AMX. Slack TTFT = round(mean); log prints int().
  MMLU phase: qwen tp4 engines log ~800 HBM-exhaustion warnings/night -> shards fall back to
  CPU attention (so MMLU does exercise CPU attention on qwen; perf test does not).
  Verified by workflow wf_39c58401-d26 (17 agents, 13/16 upheld, 3 partial refutations fixed).

**Why:** the "no boost" question will recur every time the nightly is compared with our
campaigns; the fix is in the deb preset, not in CI yaml.
**How to apply:** to get AMX into the nightly add "TRON_AMX_DISPATCH": "ON" to the deb
preset (or -D in the gen-deb rule); the kernel TU carries its own -mamx flags and probes
CPUID at runtime (AMD falls back, see [[amd-amx-fallback-test]]). Always attribute a Slack
line to its machine by the threshold first. See [[amx-ci-coverage-facts]],
[[nightly-vs-ours-tps-context]], [[p0perf-20260913-campaign]], [[wedperf-20260916-campaign]].
