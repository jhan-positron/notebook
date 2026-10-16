---
name: jeremy-comments-replies
description: "RESOLVED 2026-08-31: Jeremy/codex PR3879 comments - alignment fixed in 60d66d9c04 (unpushed), eager-setup closed with measured data; final replies on the page, NOT posted"
metadata: 
  node_type: memory
  type: project
  originSessionId: bb3bc4a6-4892-4bf2-a666-8725f6917ff6
  modified: 2026-08-31T15:56:27.124Z
---

2026-08-31: both Jeremy/codex comments on PR3879 are CLOSED OUT (jhan approved):
60d66d9c04 pushed to origin jhan-amx-p0 (new PR head); plain-English replies
posted as r3896108314 (thread r3858305362, closes with data, no code change) and
r3896108631 (thread r3858305367, fix + measured penalty); triage.json entries
GH-3858305362 (ignore) and GH-3858305367 (done, commit 60d66d9c04) written.
The record page is PR3879/jeremy_comments.html (posted replies verbatim).

Measured (exec/results/jeremy-measure-20260831, campaign script
exec/jeremy-measure-20260831.sh, delphi-3bda after CI):
- r3858305367 (alignment): FIXED in tron-amx commit 60d66d9c04 (alignas(64)
  amx_qpack_slot vector; 5 test binaries pass incl. t_llama_unit 144875
  asserts). Split-row penalty measured: +9.3 ns/page (+10.6%) L1-hot,
  +3.2 ns (+0.5%) L2 ring, noise at RAM.
- r3858305362 (eager region+pack): pack_q_rows 6.3 ns / pack_q_group 63 ns on
  the 6962P; zero-AMX-page calls = 20.6/23.2/24.0% of amx_on calls (qwen 2K-u1
  /2K-u8/8K-u8), 36.7% at ctx32; waste <=0.5-0.8% of a step's CPU across 12
  workers -> per jhan's rule, NO code change; reply closes with data.
- Per-call counters live on jhan-dd-debug @ 8d02eaba8c (calls_total/amx_on/
  amx_zero/q_packs + thread-local did_amx delta); AMX-DEBUG exit line extended.

Campaign traps learned (fold into next perf round):
- The reviewed rinzler idle check false-positives on idle heartbeats
  (#EVT# SYSTEM_STATS / Harvester stats match the keyword grep at Open=0
  Busy=0); exclude those two line types and treat Busy>0 heartbeats as in-use.
- Right after CI releases, the 10-min journal window still holds CI's request
  storm (~60K lines): retry the idle check, don't bail on first look.
- CI on 2026-08-31 held the lease ~6.5 h past the usual 09:30Z; wait 12 h.
- rinzler serving on 3bda was stopped per policy at ~12:19Z on 2026-08-31 and
  NOT restarted (jhan's never-restart rule).
Related: [[reviewer-personas]], [[amx-tron-softattn-project]], [[perf-round-20260830]].
