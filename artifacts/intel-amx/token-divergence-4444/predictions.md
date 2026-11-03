# Issue #4444 root-cause probe: predictions written before the runs (2026-10-16, ~20:10 UTC)

Campaign: exec/td-20261016/probe-td.sh (forced runs, full per-layer records) + analyze-td.sh (record-for-record comparison).
Cell: qwen3-4b, tp2, 1 user, prompt 1024 tokens, 256 generated tokens forced to the same sequence, CPU attention, delphi-3bda.

Arms: new (PR #4959 probe commit ea94e95a4e, VNNI K + AMX), base (main 72308ec90c, row-major K, AMX on),
poc (ea94e95a4e + VNNI blocks unpacked and scored by the row-major dotter, commit 017181c02d),
newoff (new + kill switch), trunc (ea94e95a4e + AMX PV weights truncated like AVX, commit 3d1426f549),
baseoff (base + kill switch), pocoff (poc + kill switch), clean (main 72308ec90c built with TRON_AMX_DISPATCH=OFF).

Mechanism hypotheses (from the code read today):
- H1. Three fp32 add orders for the QK score exist: the dotter (two lane-split accumulators + a 16-lane halving tree),
  the VNNI reader (sequential over the 64 dimension pairs), the AMX tile (sequential over the 64 dimension pairs).
- H-A. The AMX QK score equals the VNNI reader's score bit for bit (same sequential pair order).
- H2. Two PV paths: AVX (P truncated to bf16, sequential over token pairs), AMX (P rounded to nearest even, sequential over token pairs).
- H-B. For bf16-exact P the AMX PV output equals the AVX PV output bit for bit (same pair order).
- H3. In the CPU cell, `new` and `base` differ only where a partial page is scored: the reader (new) vs the dotter (base).
  Dense pages take the same AMX kernel in both (AMX from VNNI K == AMX from row-major K, the identity case of t_amx_numerics).

Predictions (P = must hold if the hypotheses are right; a failure means a cause not yet named):
- P1. poc == base: 0 differing records over all labels and tokens (H3). Tokens identical.
- P2. pocoff == baseoff: 0 differing records. baseoff == clean: 0 differing records (kill-switch contract on row-major K).
- P3. base vs new: first differing record at prompt token 1, layer 0 (token 0 attends to itself only: P = 1 exactly, so the
  score cannot change the output). The seam's relative change is of the order 1e-5 (add order only).
- P4. newoff vs new: first differing record at the first query that sees a dense page from an earlier prefill pass
  (expected prompt token 128 with 128-token prefill passes), layer 0.
- P5. trunc == newoff: 0 differing records IF H-A and H-B both hold (then the AMX path differs from the AVX path only by the P
  rounding). If records differ, the remaining difference is the AMX-vs-AVX add-order component, and its size is measured.
- P6. new vs trunc: P rounding only; the seam at prompt token 128, layer 0, with a relative change of the order 1e-3 and a
  systematic sign (the truncated weights sum to less than the exact ones: the AVX-style output is smaller in magnitude).
- P7. At the logits every non-identical pair shows the same saturated per-step statistics (median mean|delta| about 0.035,
  about 80 % of entries changed by >= 1 ulp), whatever the seam size; the top token changes only at steps whose margin is
  within the pair movement (near ties): step 84 for base vs new (2 ulps, exact tie in base) and step 248 for new vs newoff (1 ulp).
