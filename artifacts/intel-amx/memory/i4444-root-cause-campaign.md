---
name: i4444-root-cause-campaign
description: "2026-10-16 issue #4444 root-cause campaign (token divergence AMX/VNNI vs row-major): arms, PoC branches, scripts, predictions, deliverables token-divergence-issue4444-report.html (+ fix-design.html if a real problem)"
metadata:
  node_type: memory
  type: project
  originSessionId: 2110147a-d396-4af0-a642-fd0f0d92c2ee
  modified: 2026-10-16T20:17:02.698Z
---

Goal (jhan 2026-10-16): the REAL root cause of the token divergence of issue #4444 with measurement backing,
PoC code fixes if needed; deliverables in ~/workspace/intel-AMX/token-divergence-4444/:
token-divergence-issue4444-report.html and, if the cause is a real problem, token-divergence-issue4444-fix-design.html.

Layout: exec/td-20261016/ (build-clean.sh, build-variant.sh, probe-td.sh = fork of pr4-20261012/probe83.sh with FULL
intermediates kept on /var/tmp/jhan/td/, analyze-td.sh = dd_first_divergence.py per pair, ktest/ = standalone kernel
bit-exactness program, tiestats/ = near-tie flip statistics). Results exec/results/td-20261016/, logs exec/logs/td-*.log.
Predictions written before the runs: token-divergence-4444/predictions.md.

Arms (qwen3-4b tp2, 1 user, prompt 1024, 256 forced tokens = pr4-20261012/smoke/cpu-p1024/new.tokens, CPU attention):
new = /var/tmp/jhan/tron-pr4/gen/runtron.pr4 (ea94e95a4e, PR 4959 probe commit, base = main 72308ec90c),
base = tron-main1010/gen/runtron.main1010 (72308ec90c, AMX on), poc = tron-td-poc/gen/runtron.poc (branch jhan-td-poc
017181c02d: VNNI blocks unpacked + dotter), trunc = tron-td-trunc/gen/runtron.trunc (jhan-td-trunc 3d1426f549: AMX PV
weights truncated like AVX), clean = tron-td-clean/gen/runtron.clean (72308ec90c, TRON_AMX_DISPATCH=OFF); *off = kill switch.
NFS worktrees of the PoC branches: ~/workspace/ai-runs/tron-td-poc, tron-td-trunc (never on the PR branches).

Mechanism facts (code read 2026-10-16): three QK add orders (dotter = 2 accumulators x 16 lanes + halving tree; VNNI
reader = sequential 64 pairs; AMX tile = sequential pairs, within-pair order per SDM may differ from VDPBF16PS); PV: AVX
truncates P (interleave_bf16_ps, kv_cache.hpp ~2996) and AMX rounds P to nearest (cvtne2ps), both sequential over token
pairs. Prefill = 8 passes x 128 tokens; a pass's own pages are never dense (query-mask ranges), so first AMX use = token 128;
first reader-vs-dotter difference = prompt token 1 (token 0 has P = 1 exactly). qwen plugin logs no 'Attn out'; WO is the
first downstream label; Q/K/V replay from 'WQ roped', 'WK roped', 'WV' lines.

Machine coordination: session muse-glimmer-af (Muse Glimmer AMX) shares 3bda tonight; agreed: no hugepage tests
between my first "STATUS run" and probe.done, no runtron of theirs until I report my second round over.

RESULTS 2026-10-16 (first round done 21:03 UTC, all rc=0; records /var/tmp/jhan/td/<arm>.full 20.6 GB each, comparisons
exec/results/td-20261016/layers-*.json + steps-*.json):
- baseoff == pocoff and clean == baseoff: 0 of 416,443 differing records (VNNI layout numerically inert; kill switch on
  row-major = clean binary exactly). base == poc for all 1024 prompt tokens + decode to token 1086; first difference at
  token 1087 = decode page-end step (main scores the just-completed page on AMX, PR 4959 in software because block 3
  converts at the forward end; verified in code; PR 4957/4958 behave like main). Layer-0 WO differs only at 1087/1151/1215.
- base vs new: first record token 1 (WO layer 16, rel 2.6e-4): reader-vs-dotter add order; L0 WO first at token 26.
- new vs newoff and baseoff vs base: first at token 128 L0 WO, rel 1.9e-3, 36 % elements (first AMX visit = pass 2).
- newoff vs trunc (order only, AMX vs AVX): first token 128 layer 2, rel 2.3e-4 (10x smaller than rounding).
- ktest (exec/td-20261016/ktest/results.txt): VDPBF16PS lane = (acc+p_odd)+p_even; dotter = that + halving tree, reader =
  sequential, bit-exact refs; TDPBF16PS = per 16-pair instruction E=chain(even products) O=chain(odd), acc+fl(E+O) (bit
  exact 512k/102k); AMX != reader (49.5 % differ), AMX PV != AVX PV order (72.8 %); truncation bias: weight mass -0.144 %,
  output -0.073 %, RMS 1.8x RNE; T9: AVX kernels in AMX order bit-identical, cost 1.30x (QK) / 1.06x (PV).
- replay (exec/td-20261016/replay/results.md): real Q/K/V layer 0: trunc bias -0.078 % output, mass -0.16 %; RNE ~0;
  order-only differences = one-element events; validated vs logged WO through o_proj.
- logits: flips only at steps 20, 84 (exact tie in base), 248 (1 ulp); every non-identical pair ~80 % entries differ >= 1 ulp.
- tie stats: predicted 0.8-1.5 flips/256 steps vs observed 0-3 (exec/td-20261016/tiestats/).
Pending at 21:10 UTC: td2 (prompt 8192 logits), td3 (attn-stats counters steps 63/64), facts.json, report, design.
Deliverables (21:45 UTC): token-divergence-4444/token-divergence-issue4444-report.html (generator exec/td-20261016/report/
gen_report.py; v1 backup gen_report.v1.bak) revised after an 8-agent verification workflow (first-record rule = earliest WO in
forward order; tie stats section 2; scope note on the AMX shape; FPGA caveat from p83 fnew-vs-fbase); fix-design.html revised
after design-review (option C keyed on the env var only; D2 = round the page's weights once + broadcast dword; D3 safety
argument lists the GOF staging + split-block facts; D4 flips <= 6). Pending: td2 (8192; new run 31 min each), td3 counters,
re-check workflow, final publish + notebook copy, message muse-glimmer-af when td3 done.
DONE 2026-10-16 23:30 UTC. Rounds: td (8 arms, records), td2 (prompt 8192: logits differ at all 256 steps, 81 %; median
margin 19.75 vs 3.91 logit units at 1024, 0 steps <= 2 ulps -> no flips: a prompt property), td3 (off by one: measured the
forward at 1086), td4 (65 tokens: at position 1087 main adds 17 pages AMX / 0 AVX; stack and poc 16 pages AMX + 64 tokens
AVX = cause 3 measured). Verification: 8-agent workflow + 3-agent re-check applied; design-review 2 rounds applied.
Verdict: 3 causes (add orders; AVX truncation of P vs AMX RNE = dominant at the seam, biased -0.08 %, RMS 1.13-1.8x; PR 4959
page-end path choice). Real problem = pre-existing AVX truncation (D2) + kill-switch contract (D1 option C: AVX kernels in the
AMX order, T9 bit-identical, 1.30x/1.06x). Machine released to muse-glimmer-af at 23:25 UTC. Notebook copy NOT made (jhan
did not ask to preserve); artifacts published at the end of the session (see final message).
Artifacts (2026-10-16 23:35 UTC, private): report https://claude.ai/artifact/6eiu3G627dn3zUc4SVQAgx, design
https://claude.ai/artifact/ERuApT9EKqGL6mmvdNvGPV (publish from scratchpad copies without the document skeleton; canonical
files keep the full skeleton in token-divergence-4444/).


Former index hook (moved from MEMORY.md on 2026-10-21 to keep the index under its size limit): 2026-10-16 arms/PoC branches (jhan-td-poc, jhan-td-trunc)/scripts exec/td-20261016/, predictions, deliverables token-divergence-issue4444-re...
