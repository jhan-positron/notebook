---
name: fpga-monitoring-reference
description: "How to monitor FPGA internal state/stats in tron (fpga_use_metrics, tracer, crash dump) + doc links"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 453bd91c-e321-4a0b-a7f7-4234acb7f379
  modified: 2026-08-14T03:34:59.553Z
---

Two in-tree FPGA-internal monitoring mechanisms (verified at trunk + 12804a812):
1. fpga_use_metrics_* (h/libpos.hpp:453-468; impl src/pos/device.cpp:479-535): start/stop
   window over 7 on-chip 32-bit counters — hbm_timer/hbm_read (HBM→fetcher0 read cycles),
   mm_timer, mm_in_prog, mm_bp, mm_rmem_bp (results-mem backpressure = stream not
   draining), mm_wmem_bp (weights starvation). MMIO via system_ctrl reg bits
   metrics_clear/start/done; readout 4 reg reads; spdlog::info output. NO flag/env wiring —
   only t/t_metrics.cpp uses it; to use in runtron, add calls + rebuild. start clears chip
   counters (no overlapping windows); timer saturates at 2^32 clocks (~10 s est.).
2. FPGA tracer (--tracer-core N on gen/runtron; forbidden by dice wrapper bin/runtron:82):
   FPGA DMA-writes a state snapshot every ~10 µs to a host mailbox; host thread
   (src/pos/metrics.cpp:124-153) emits perfetto TRACE_COUNTERs on change: rmem_bp,
   inprog_pause, rmem_depth on category "driver"; wmem_loaded, act_pending/inprog,
   fetcher0/16_read_done, mm_results_accum on "driver-detail". Field layout: Notion
   "Tracer" page 143d132d3cfd804fb720e595fca945ba (referenced at metrics.cpp:43).
Also: reg_crash_dump (h/pos/regs.hpp:5787+, one-shot full debug dump incl. hbm_thermal_
north/south + rmem_debug + fetcher_debug); mcnt_mbox results-count mailbox (RX pacing).
Docs: Notion "Datapath Statistics" 112d132d3cfd802d870bcfa08fefb3da (register procedure),
"Giant List of Metrics" 12fd132d3cfd8096a8e3cb88054512a9, "FPGA Debug Snapshot"
6c458fa1d16f421996240ad72975a12b, STORY-655 (HBM thermal→perfetto)
3a3d132d3cfd81808655d8950f35050e. RDL source of truth: llm_fpga repo registers/
(gen_json.py → fpga-reg/regs.json → gen_reg_hpp.py → h/pos/regs.hpp).
Bill's mechanism (per GDrive "Sync up 2026/08/11" 1OLraTfCxKBEBz-hZIR8WNjBMuWLXWjratPnlFIyJZdQ):
his own register-POLLING patch (RM depth, weight fetch status, results FIFO, hw
weight-load toggles) + markdown guide — not in-tree; ask Bill for the patch.
Relevance to fill_logits_buffer jitter: tracer's rmem_depth/rmem_bp at 10 µs answers
"late arrival vs slow consume" directly; wmem_bp relevant because wcls weights race the
launch (Note [Launch-time wcls weight command], model.hpp:3217).
