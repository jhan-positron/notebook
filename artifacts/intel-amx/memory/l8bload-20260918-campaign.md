---
name: l8bload-20260918-campaign
description: "DONE 2026-09-18 21:08 UTC: AMX gain on llama-3.1-8b vs load per engine (rinzler + CI harness on our half, same target binary, kill switch vs on): +0.2 % at 2 users/engine, +3.9 % at 4, +12.9 % at 8; hypothesis confirmed; report status/llama8b-AMX-gain-vs-load.html; scripts exec/l8bload-20260918/; traps"
metadata: 
  node_type: memory
  type: project
  originSessionId: cfafa211-4409-4b46-a9f5-c701b81efeba
  modified: 2026-09-18T21:09:54.650Z
---

Question (jhan 2026-09-18 19:5x UTC, "Let's do it. Go ahead."): does the AMX kernel's gain on llama-3.1-8b grow with the
load per engine? (Hypothesis from the ci-mimic report: the kernel speeds up only attention, whose share of a decode step
grows with users x context; nightly layout = 2 users per 28-CPU engine gave +0.8 %, runtron 8 users/1 engine gave +17 %.)

Setup (exec/l8bload-20260918/{campaign.sh, rz.sh, summarize.py, gen_report.py, launch.sh}; results
exec/results/l8bload-20260918/cells/<U>u__<arm>__rep<N>/; log exec/logs/l8bload-20260918.log):
- rinzler (NOT runtron) from the ci-mimic target deb, extracted with dpkg-deb -x to /var/tmp/jhan/ci-mimic-20260918/root
  (RUNPATH $ORIGIN resolves libversion.so; libfuse3 from /opt/positron/lib), sha 3ee9c8f0 = the deb's rinzler. Not installed.
- 2 engines on socket 1 with the EXACT platformd RZ_CLI_ARGS of instance-2/3 (snapshot 09-18 16:28): a = --instance 2,4
  cards 90/93 app-cores 223-224,96-101,120-125,225-226,102-107,126-131 dev 75,76 launcher 73,217; b = --instance 3,4 cards
  b9/bc app-cores 227-228,108-113,132-137,229-230,114-119,138-143 dev 77,78 launcher 74,218; 128 hugepages each; ports 13100/1.
- CI harness (exec/more-testing-r1/st_perf.py, venv /var/tmp/jhan/st-venv) one client per engine on cores 87-95,231-239,
  --users U, U in {2,4,8} (8 added by Claude; jhan approved 2 and 4). Arms: off = TRON_AMX_DISABLE=1, on = unset;
  USE_HW_ATTN untouched (llama = CPU attention by default); TRON_USE_SPECULATION=0. Odd reps off->on, even on->off.
- Production engines (idle leftovers) taken down via `curl -X POST localhost:8080/api/inference/down` after a 10-min
  journal idle test, positron's slice files removed (jhan is in group positron), brought back with /api/inference/up at
  the end (also on abort). Per-cell proof: 20 s EXE.AMX_BUSY perf stat on both engine pids 75 s into the benchmark.

RESULT (3 clean pairs per level; paired t over reps, t975 = 4.303):
| users/engine | off TPS | on TPS | gain | t | AMX-busy on (20 s) |
| 2 | 141.57 | 141.81 | +0.2 % | +0.5 (not resolved) | 40 G |
| 4 | 122.93 | 127.69 | +3.9 % | +5.8 (resolved) | 68 G |
| 8 | 70.08 | 79.14 | +12.9 % | +38.7 (resolved) | 92 G |
Off arm = 0 AMX cycles in every cell. Off arm at 2 users (141.6) = nightly 13-night mean 139.7 within 1.4 % -> the VNNI
layout alone changes nothing at that load, and hand-started engines reproduce the nightly without the proxy hop.
Hypothesis confirmed: the lever for llama-8b in CI is users per engine (or context), not USE_HW_ATTN.

ANOMALY: cell 2u on rep3 (20:42 UTC) = 130.1 TPS, both engines identical per-round 119-135 in rounds 1-8 then 141 in
rounds 9-10, TTFT normal; nothing else in the journal (only our sudo perf/prlimit); cause unknown; excluded via a
cells/<cell>/ANOMALY marker file (summarize.py + gen_report.py skip marked cells from the pairing, list them) and replaced
by a 4th repetition at level 2 (relaunch with LEVELS=2 REPS=4; done cells are skipped).

TRAPS: (1) Monitor tool tail -F on the NFS copy of a log written on 3bda delivers nothing; run tail over ssh on the writer
host. (2) A trailing `cut` in a Monitor pipeline block-buffers -> zero events; end the pipe with stdbuf -oL grep, no cut.
(3) pgrep -c -f "<pattern>" inside an ssh bash -c matches the bash itself -> filter "bash -c|pgrep". (4) cairosvg renders a
blank PNG when the <svg> root carries style="...height: auto"; put font attrs on the root and sizing in page CSS.
(5) platformd v0.10.7 has affinity 0-287 and ~34 % CPU while its engines are down (failing health checks) -> jitter source.

Report: VNNIed-K-in-place/status/llama8b-AMX-gain-vs-load.html (copy exec/results/l8bload-20260918/report.html), ASCII,
2 SVG charts (gain vs load dots + TPS dumbbells). Related: [[ci-mimic-20260918-campaign]], [[p0perf-20260913-campaign]],
[[amx-busy-perf-counter]], [[issue-4500-fpga-attention-vnni-tps]].

Report verification (2026-09-18 21:1x UTC): 3-lens workflow found 30 issues in v1 (4-sentence Short version, mechanism
stated as fact, chart-2 caption trend inverted [share recovered falls 26 % -> 13 %], undefined arm/level/cell/PR/FPGA/tp2,
stale ANOMALY counts, semicolons); all applied in gen_report.py (page section rewritten). ANOMALY evidence saved:
cells/2u__on__rep3/journal-2042-2045.txt (only other event: tailscaled reconfig + DNS cache flush 20:44:36 UTC, 10 s after
round 9 began; relation unknown). Second verification pass wf_9dd184c5-0a5.
