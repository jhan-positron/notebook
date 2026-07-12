# TRON Performance Prediction Under SNC3

Date: 2026-06-08  
Host context: `delphi-3af6` SNC3/SNC-OFF measurements plus TRON Perfetto report  
TRON source report:
`/home/jhan/workspace/intel-vs-amd/tron-atlas-perfetto/output-from-codex/TRON_PERFETTO_ANALYSIS.md`

## Short Prediction

SNC3 is likely **better for compact, correctly placed Llama steady decode**, but
**worse for a naive port** and risky for wider Qwen/prefill/model-load phases.

The decisive condition is placement. If TRON keeps app workers, TX/RX driver
threads, DMA/KV/descriptor memory, hugepages, and PCIe-local Positron devices
inside the same SNC node, SNC3 should help the latency-sensitive CPU
orchestration path. If TRON simply flips the machine to SNC3 while preserving
the current Intel Llama `NUMA set 0` with CPUs `25-46`, performance is likely
to get worse because those CPUs map to SNC3 node1 while memory would be placed
on node0.

## Evidence

### From The SNC3 Measurements

| Measured property | SNC-OFF | SNC3 | Meaning for TRON |
|---|---:|---:|---|
| Local L3 latency, 4 MiB | 60.535 ns | 35.892 ns | Hot queues, descriptors, mailboxes, callbacks, and metadata can improve if local. |
| Local DRAM latency, 4 GiB | 137.696 ns | 112.751 ns | DMA/KV/logit metadata touched by local CPU threads can improve if allocated local. |
| Same-socket remote DRAM | n/a single node | 138.891-165.982 ns from cpu0 to nodes1/2 | Wrong SNC node placement gives back much of the latency gain. |
| Cross-socket DRAM | 276.871 ns | 249.856-321.351 ns | Cross-socket placement remains expensive and must be avoided. |
| Single-node DRAM peak | 596.319 GB/s | 204.238 GB/s | Binding a many-thread phase to one SNC node can be much worse. |
| Whole-socket local DRAM read | 593.863 GB/s | 608.882 GB/s | SNC3 does not lose peak socket bandwidth if memory is placed local per die. |
| Loaded L3 victim, 23 bg threads | 103.832 ns | 221.242 ns | One full SNC die can get latency-hostile under local contention. |

### From The TRON Perfetto Report

| TRON property | Evidence | SNC3 implication |
|---|---|---|
| TRON is device-offload driven | CPU constructs requests, descriptors, launches hardware matmul, waits on mailboxes, collects completions, stages logits/KV metadata. | CPU is mostly orchestration; local latency matters more than raw CPU FLOPS for steady decode. |
| Intel Llama placement is compact | App CPUs `27-36,37-46`, driver CPUs `25,26`, RX siblings `169,170`, NUMA set `0`. | The physical footprint is likely cores `25-46`, 22 physical cores, which fits inside one 24-core SNC die. |
| Current CPU list maps to SNC3 node1 | Our SNC3 topology: node0 `0-23`, node1 `24-47`, node2 `48-71`. | Keeping `NUMA set 0` with CPUs `25-46` would allocate memory on the wrong SNC node. |
| Intel Llama steady decode is stable | 8.992-8.996 ms/tok on Intel, with repeated TX/RX and launch/prepare slices. | Expect small end-to-end gains only; the accelerator still does the heavy tensor work. |
| Qwen worker counts are wider | 15 workers for 512p/1024l, 34 workers for 2kp/20l, 54 workers for Qwen 27B model-load/quantization. | Wider phases often exceed one 24-core SNC node and need multi-node sharding. |
| Qwen model-load/quantization is memory sensitive | Qwen 27B dominated by `Quantize supertile`, `Construct model`, `Load tensor`, `Quantize and load weights`. | Naive single-node SNC3 can be substantially slower due to the 204 GB/s node cap. |

## Phase-Specific Prediction

| TRON phase | If SNC-aware | If naive / current binding copied |
|---|---|---|
| Intel Llama steady decode | Slightly better to neutral. Predicted end-to-end change: **0% to +5% tok/s**, likely +1% to +3%. | Slightly worse. Predicted end-to-end change: **-2% to -10% tok/s** if CPUs `25-46` keep allocating on NUMA node0. |
| Llama TTFT / short prompt setup | Neutral to slightly better if DMA/KV metadata is node-local. | Worse if descriptors/KV books/logit staging are remote to the worker die. |
| Qwen 512p/1024l steady generation, 15 workers, 8 devices | Neutral to slightly better if per-device queues and memory are local to their TX/RX/device group. | Worse if a central queue or DMA heap on one SNC node serves workers/devices across nodes. Estimate **-5% to -20%** in bad placement. |
| Qwen 2kp/20l, 34 workers | Needs at least two SNC nodes or a changed worker split. Could be neutral if sharded. | Likely worse if treated as one memory node: **-5% to -25%**, because 34 workers exceed one 24-core die and will create cross-node traffic/contention. |
| Qwen 27B model-load/quantization, 54 workers | Comparable or slightly better only if first-touch/local allocation spreads streams across all relevant SNC nodes. | Likely worse: **-15% to -45%** for the CPU/memory-heavy part if bound to one SNC node. Worst-case memory-bound slowdown approaches the measured `596/204 = 2.9x` bandwidth loss for single-node binding. |

## Mechanism

For compact Llama decode, SNC3 helps the right thing:

```text
Local hot metadata / queue / descriptor access:
SNC-OFF L3 ~= 60.5 ns
SNC3 local L3 ~= 35.9 ns
latency ratio = 35.9 / 60.5 = 0.59
```

That is a large local-latency win, but it applies only to the CPU
orchestration fraction of the token path. Since TRON is device-offload driven,
the end-to-end token improvement should be modest unless CPU launch/queue
latency is already on the critical path.

For a naive port, SNC3 can hurt the exact same path:

```text
Current Intel Llama CPUs: 25-46
SNC3 mapping: node1 = 24-47
Current TRON NUMA setting: 0

If unchanged:
workers/driver on node1, memory on node0
local L3 opportunity: 35.9 ns
adjacent-node L3-like path observed in T3: ~60.4 ns
local DRAM opportunity: 112.8 ns
adjacent-node DRAM: ~138.9-166.0 ns depending path
```

That converts SNC3 from a locality win into a remote-node penalty.

For wide Qwen/model-load phases, the danger is bandwidth partitioning:

```text
SNC-OFF single NUMA node represented whole socket: ~596 GB/s DRAM read peak
SNC3 one NUMA node is one die: ~204 GB/s DRAM read peak
Bandwidth ratio = 204 / 596 = 0.34
```

SNC3 recovers whole-socket bandwidth only when memory is placed local per die:

```text
SNC3 socket --local read endpoint = 608.882 GB/s
```

So wide TRON phases need explicit per-SNC-node placement, not a single
`numactl -m 0` style binding.

## Porting Guidance

For the current Intel Llama CPU layout, choose one of these:

1. Keep CPUs `25-46`, `169-170`, and driver CPUs `25,26`; change memory/hugepage
   binding from NUMA node0 to SNC3 node1.
2. Keep memory on SNC3 node0; move app and driver CPUs into node0, e.g. physical
   cores inside `0-23`, and use the corresponding SMT siblings if needed.

Before choosing, verify PCIe locality for Positron BDFs `17:00.0` and `18:00.0`.
The right placement is CPU node, memory node, DMA heap, TX/RX threads, and
device-local PCIe root locality together.

For Qwen/wide phases:

- Split workers by SNC node instead of using one global worker pool.
- Allocate DMA rings, descriptor queues, KV metadata, and staging buffers by
  first-touch on the same SNC node as the corresponding TX/RX/device group.
- Avoid one central hot work queue spanning SNC nodes; shard or replicate small
  read-mostly control structures.
- For model-load/quantization, parallel first-touch across nodes is required if
  the code expects whole-socket memory bandwidth.

## Validation Plan

Minimum data needed to confirm the prediction:

- Perfetto scheduler capture with nonzero `sched_slice` and `thread_state`.
- `numactl --hardware`, `lscpu -e`, `lspci -tv`, PCIe BDF-to-NUMA sidecars.
- `numastat -p <tron_pid>` and `/proc/<pid>/numa_maps` during decode and
  model-load.
- Perf counters or sidecars for LLC misses and local-vs-remote memory traffic.
- TRON TrackEvents carrying byte sizes for KV, DMA rings, descriptors, logits,
  and staging buffers.

Pass criteria for "SNC3 helps TRON":

- Llama decode ms/tok improves or stays within noise while TTFT does not regress.
- TX/RX launch and collection slice averages do not increase.
- Device act-slot occupancy does not drop.
- `numa_maps` shows hot DMA/KV/descriptor pages local to the CPU/device group.
- Wide Qwen/model-load phases do not collapse to the 204 GB/s single-node
  bandwidth limit unless that is intentionally accepted.

Falsification triggers:

- Llama steady decode loses more than 3% tok/s after corrected local placement.
- `numastat` shows high remote accesses for TX/RX or app workers.
- Qwen/model-load gets slower while memory pages are concentrated on one SNC
  node.
- PCIe BDF locality shows the chosen CPU node is not near the Positron devices.

## Final Verdict

Use SNC3 for TRON only as an explicit locality port, not as a BIOS-only switch.

Expected result:

- **Llama steady decode:** slightly better or neutral if placed on one SNC node;
  worse if current CPU list and `NUMA set 0` are copied unchanged.
- **Qwen long-prefill/model-load/quantization:** likely worse by default; can be
  recovered only by sharding workers, memory, and device queues across SNC
  nodes.

The first port target should therefore be Intel Llama decode with corrected
node1 placement, because it fits one SNC die and is the cleanest case for SNC3
to win.
