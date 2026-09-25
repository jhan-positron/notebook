---
name: amx-vs-avx-sense
description: "2026-08-31 brainstorm page PR3879/make-sense-amx-vs-avx.html: measured boost-vs-ctx data, Q1/Q2 answers, Sol-reviewed campaign plan; key numbers and denominator trap"
metadata:
  type: project
---

Built 2026-08-31 for input-2-ai/make-sense-amx-vs-avx.md (page PR3879/make-sense-amx-vs-avx.html,
artifact https://claude.ai/code/artifact/db6b18c8-0696-417a-ad22-21efa86544b7; draft + sol-reply archived in PR3879/make-sense-amx-vs-avx/).
Key verified facts (all cited on the page):

- Headline (clean-binary, chart-check.csv): arena-mirror +4.5%/+19.6%/+22.8%/+28.1% at
  1u2K/1u8K/8u2K/8u8K; canonical +3.8/+15.2/+19.0/+17.5. DENOMINATOR TRAP: the kill-switch arm
  (TRON_AMX_DISABLE=1) runs 2-5pp slower than a clean AVX binary (code layout; p2-inc2b-decomp, run 2026-08-19 on the retired
  K-mirror LAYOUT_ONLY build; CORRECTION 2026-09-23: NOT true on the canonical-kernel code, where the kill switch = no-kernel speed,
  14.745 vs 14.650 tok/s over 16 requests, exec/results/qwen8u8k-pr1-half-20260909T1704.txt; see [[ci-amx-row-20260923]]),
  so same-binary A/B overstates the boost - always label which denominator.
- Q1 answer: attention share of the token grows ~14/30/64% at ctx 256/2K/8K (est.) and AMX page
  coverage 64.4/92.2/97.8% at ctx 32/2K/8K (measured, counter-summary 20260831); per-ctx share
  caps the gain, asymptote = 1 - a_amx/a_avx (Sol: two different statements).
- Decode-width reality: 4/16 tile rows used -> kernel gain 1.53x at M=4, not 8x (microbench-quiet);
  decode sharing width 1.022 (p1-sharing) so M>=8 unreachable in private decode.
- AMX freq license measured 3.59 vs 3.89 GHz single-core synthetic (p0c-freq-power); serving
  impact unmeasured (hypothesis). No AMX-ON perf-stat exists anywhere yet; no fence data on any
  AMX binary (fences F1/F3 are from tron-perf-fluctuation, NOT definitive-decode; probe recipe
  tags 7601/7600; legs overlap - next extend enqueued before F3, Sol S6).
- Campaign agreed on page: ctx-axis fill with clean pairs, first AMX-ON perf-stat - THREE arms
  per jhan 2026-08-31 (canonical AMX, arena-mirror AMX, kill switch; mirror-vs-canonical isolates
  the K-mirror layout incl. dTLB 4K-vs-1G, canonical-vs-kill-switch isolates AMX execution) (GNR events:
  AMX_OPS_RETIRED.BF16, CORE_POWER.LVL*_TURBO_LICENSE, DTLB WALK_COMPLETED_4K/_1G,
  PAGE_WALKER_LOADS, per-IMC bytes, UPI), fence campaign with sequence-id stamps, did_amx counters
  into perf-round harness, decode-order (scattered) microbench, optional THP-on-arena experiment.

FENCE CAMPAIGN ROUND 1 DONE (2026-08-31 19:49Z, marker ok, exec/results/fence-20260831/,
branch jhan-amx-fence 245502cb88 + gen stamps, binary runtron.fence 6b1fead791):
1u, mirror vs same-binary kill switch, ctx 256/2048/8192, medians over ~759 tokens/cell.
Findings: fence period matches runtron ms/tok <=0.4%; [F1->F3] flat 358-363 us everywhere ->
100-104% of the AMX delta in [F3->F1]; next-extend submitted only 4-6 us before F3 (1u overlap
negligible, phase split readable as ownership at 1u); same-binary boost +1.3/+5.6/+15.0%
(AVX arm faster than 08-19 inc2: 109.4 vs 100.5 tok/s at 8K - branch drift, spread narrowed);
7603->7604 span = whole 36-layer pipeline (88-94% of token), NOT attention-compute share.
Bring-up trap hit: [[nfs-attr-cache-build-trap]]. Follow-ups: canonical arm, per-layer split.

jhan preference (2026-08-31, stronger than the CLAUDE.md "label estimates" rule): when a real
measurement is planned, do not publish derived interim numbers at all - state the gap and the
planned measurement instead (removed the derived per-layer x from the page on request).

PERF-STAT ROUND 2 DONE (2026-08-31 23:25Z, exec/results/perfstat2-20260831/; round 1 failed:
3bda runs perf_event_paranoid=4 - jhan approved a sysctl 4->0->restore-4 lift, logged in OUT).
Measured, 12s windows on 28 app cores, 1u/8K->16K: EXE.AMX_BUSY 29-30e9 cyc AMX arms / 0 disabled
(kill switch hardware-verified); instructions AVX 3.9x AMX arms; MIRROR dTLB TAX QUANTIFIED:
~80M 4K walks/window vs ~0.2M canonical (arena on base pages, no THP; 5.3e9 walk-active cyc =
~1.6% of cycles); busy clocks 3.52-3.55 GHz AMX vs 3.75 AVX (-5.5% serving, less than -7.7%
synthetic); AMX unit only ~2.4% busy (decode width). IMC unsettled (47-76 GiB/s phase variance;
EOS early-stops move windows - fix: --ignore-eos equivalent or phase-locked windows). GNR has no
AMX_OPS_RETIRED / CORE_POWER.LVL* events; EXE.AMX_BUSY=0xb7/0x02 from intel/perfmon GNR JSON;
turbostat is passwordless-sudo on 3bda.

FENCE ROUND 2 / STAMP 7605 DONE (2026-09-01 02:12Z, exec/results/fence2-20260901/): pure
attention wall per pass (tron attn_elapsed, worker-0, 36 ops, no FFN/norm/rope), 510 windows/cell:
mirror 602/1288/4468 us vs AVX 654/1542/5691 us at ctx 256/2K/8K -> x = 51.5/254.4/1222.9 us/pass
(1.43/7.07/33.97 us/layer); attention delta = 100-104% of period delta; serving attention speedup
1.09/1.20/1.27x (vs kernel 1.5-2.4x - tail pages + softmax + joins dilute); measured attention
share 16/31/62% of token (AVX) RETIRES the 14/30/64% estimate. Plan step 1 closed.

SOL CAMPAIGN REVIEW (2026-09-01, archived PR3879/make-sense-amx-vs-avx/sol-review-campaigns.md):
NO-GO on queued scripts as first written. Standing lessons for ANY 3bda campaign script:
(1) observability must fail CLOSED (sudo journalctl/ss rc checked BEFORE counting; "|| true" on
a pipeline that ends in grep -c/wc silently converts sudo failure into 0 = fail-open);
(2) campaign_guard_acquire --allow-serving BEFORE inspecting/stopping rinzler (lock-then-stop);
(3) cleanup traps kill tracked PIDs only, never broad pkill -f patterns;
(4) stop_now truncation -> marker stopped-early, never ok;
(5) headline binaries: build all arms fresh from one pinned commit in separate build dirs;
(6) counter groups: NMI watchdog owns 1 of 4 GP counters (HT on) -> brace groups <=3 GP + group
smoke rejecting <not counted>; (7) phase-lock counter windows to a token index (poll stamp
records; 7602 count = decode token index). ctxfill v2 relaunched 06:00Z (sleeps to 09:15Z);
perfstat3 v2 ready. SYSCTL LIFT IS STANDING APPROVAL (jhan 2026-09-01: "Remove this sysctl gate, proceed whenever you need to") - lift perf_event_paranoid 4->0 without asking, ALWAYS with the verified-restore-to-4 pattern and set/restore lines logged in the results file.

CTXFILL DONE (2026-09-01 12:32Z, exec/results/ctxfill-20260901/, Sol-reviewed v2 script,
commit-pinned pair 60d66d9c04, 8 reps, spreads <=2%): deployable boost clean-vs-mirror 1u =
+0.6/+1.9/+1.7/+14.9/+26.0% at ctx 256/512/1024/4096/16384 (clean 250.4/241.9/230.9/152.4/64.4
tok/s). Knee between 1K and 4K; STILL RISING at 16K (no asymptote yet). Remaining holes: no
commit-pinned 2048/8192 pair (08-21 vintage only), nothing >16K, no 4u. Plan items 1,2,3 and
stamp-7605 all closed; open: perfstat3 (ready, per-round sysctl ask), canonical fence arm,
per-cause fallback split, scattered-address microbench, THP experiment, 8u.

DIRECTIVES (jhan 2026-09-01 evening): (1) 8u stays HELD until he lifts it; (2) raw data policy:
retain by pushing to github.com/jhan-positron/notebook artifacts/intel-amx/ (kvwait bins are
SPARSE - gzip them; amx-decode-boost-202608/ pushed a71201e, then local bins deleted);
(3) measurement branch jhan-amx-fence pushed to origin. Chain perfstat3->fence3 running; its raw
data goes to the same notebook dir when done.

ROUND 3 DONE (2026-09-01 18:13Z perfstat3 phase-locked; 18:19Z fence3 three arms; raw in notebook
artifacts/intel-amx/amx-decode-boost-202608/). Counters (12s @ token 400, 28 app cores): AVX 2x L1
and demand-L3 misses, 3.3x L2 misses of AMX arms; AMX arms 1.8x MORE total L3 misses (prefetched
tile streams) with half the demand misses; DRAM 50-58 GiB/s both sockets = NO bandwidth wall at 1u
(latency/MLP-bound); 99.999% L3 misses local (NUMA clean); mirror dTLB 72.7M 4K walks vs canon
0.11M (680x) + 2.1M extra store walks; clocks 3.53-3.55 AMX vs 3.74 AVX GHz; AMX busy 2.4%; uops
AVX 3.2x. Fence3: canonical alone +0.2/+3.9/+10.8% vs kill switch; mirror +1.6/+5.5/+16.2%;
mirror beats canonical by 7-10% of attention (570/1276/4428 vs 631/1375/4790 us) = 1.4/1.5/4.8%
of the token - the transpose removal outweighs the base-page arena costs. BRING-UP TRAP: runtron
RUNPATH is $ORIGIN-relative - binaries must run from gen/ (copies elsewhere die rc=127
libfuse3/libversion not found); scripts now pre-flight --help before guarding.

CURVE COMPLETE (ctxfill2 2026-09-01 19:5xZ, pinned pair, 8 reps, spreads <=1.1%): +5.0% @2048
(clean 204.3 / mirror 214.6 tok/s), +18.0% @8192 (107.0 / 126.3), +27.6% @32768 (36.0 / 45.9).
Full pinned curve 256..32K: 0.6/1.9/1.7/5.0/14.9/18.0/26.0/27.6% - FLATTENS between 16K and 32K
(asymptote ~28-30%). 08-21 vintage points (+4.5/+19.6) sit within ~1.5pp of the pinned ones.
Queued tonight after this: THP experiment, fallback-cause counters, then peer session
intel-amx-26's single-attention phase-timer round (its probe gated by TRON_ATTN_PHASE=1).

THP EXPERIMENT DONE (2026-09-01 20:45Z, results/thp-20260901, notebook-archived): same binary,
TRON_AMX_MIRROR_THP=1 -> 4K walks 86.9M->1.80M (-98%), walk-active -93%, BUT period/attention
unchanged within 0.4% (765 windows/cell, ctx 2K/8K). VERDICT: the mirror dTLB tax is costless in
wall time; no allocation change warranted. Trap: sampling /proc/$!/smaps after `env ... timeout
BIN &` reads the timeout wrapper - use the runtron child pid (script fixed).

FALLBACK CAUSES DONE (2026-09-01 21:00Z, results/fallback-20260901): decode fallback = partial
tail page ONLY (72,576 visits = 252 tok x 36 layers x 8 heads at every ctx; decode coverage
84.8/97.1/99.2% = (pages-1)/pages ceiling); prefill fallback = causal range_cut ONLY (60/9.1/2.3%
at 256/2K/8K). Whole-run 92.19% @2K and 97.77% @8K reproduce the 08-31 counter-summary exactly.
Plan status: every measurement item closed except the scattered-address microbench (deferred) and
8u (held). Peer session intel-amx-26 runs its single-attention phase-timer round after my
fallback marker (exec/logs/single-attn-20260901.done); do not take the lock before it exists.

SHARED-WORKTREE STATE after 2026-09-01 21:20Z (from peer intel-amx-26): jhan-amx-fence HEAD
8fd1e7798d = its phase-timer probe (inert unless TRON_ATTN_PHASE=1) on top of my 3cd2670df1;
tron-fence-amx/gen configured K_MIRROR=OFF, CMAKE_CXX_FLAGS empty; gen/ holds runtron.fence
(mirror-stamped, pre-probe), runtron.fcanon, runtron.fthp, runtron.ffb (fallback counters build),
runtron.samirror / runtron.sacanon (peer); gen header stamped 7601-7627 (patcher v2). Any new
fence round: reconfigure explicitly (flags + K_MIRROR), re-run patch-gen-stamps.py, log the branch
commit in the results header. 3bda lock free; nothing of mine queued.

**Why:** next perf sessions should execute this campaign and must not mix denominators or claim
"bandwidth-bound" without IMC bytes (Sol correction). **How to apply:** numbers above are the
2026-08-31 state; re-check exec/results for newer rounds first. Related:
[[amx-tron-softattn-project]], [[pal-bridge]], [[delphi-3bda-hardware]], [[slack-chart-data-lineage]].
