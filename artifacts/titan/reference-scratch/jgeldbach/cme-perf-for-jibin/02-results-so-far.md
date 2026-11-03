# 02: CME results so far

All runs: Cadence Palladium Z3 at GA13, asimov RTL release `a10181848`, CME and cores at 2 GHz
(CME cycles / 2000 = µs), Linux 6.18.36 from asimov-os. Bench rows (cme-perf) ran on
`hemi_rtws_tlm`; the stress-app GDN rows ran on `hemi_notws_tlm`.

**Verification key.** ✔ = recomputed on 2026-11-02 from the raw UART log of that run. R = taken from
the run's report and not recomputed.

## 1. CME load latency (`chase`, #3969) ✔

Dependent 64 B loads in streaming mode (`LD1D` then `LASTB` to the next address), 4096 hops per call.

| Ring | ns per hop |
|---|---|
| CME L1 (16 KiB) | 21.56 |
| DSU L3 (128 KiB) | 26.60 |
| OCM, idle (256 KiB, cleaned before each call) | 34.80 |
| OCM, 3 other CMEs streaming the same window | 46.06 (R) |

## 2. Stream bandwidth, one CME and five (#4045, #4065) ✔

A linear read through the CME: four 4-register `LD1B` per KiB. "HW" = hardware prefetcher only;
"RPRFM" = plus `RPRFM` 1 KiB ahead.

| Case | HW | RPRFM 1 KiB | Run |
|---|---|---|---|
| One CME (CPU 8) from SMS | 34.5 GB/s | 36.9 GB/s | #4045 |
| One CME from its OCM window | 22.1 | 23.3 | #4045 |
| One CME from SPM (uncached) | 14.6 | 14.6 | #4045 |
| One CME from SMS, synchronized start | 36.6 | 36.5 | #4065 |
| **Five CMEs from SMS at once, measured combined** | **95.8** | **96.6** | #4065 |

- Combined = total bytes / (last end − first start). Per CPU in that row: 20.1 / 29.9 / 19.2 / 26.5 /
  20.3 GB/s (CPUs 0/2/4/6/8). CPUs 2 and 6 finish first. We haven't found out why.
- Prefetch distance barely matters: 1, 2, 4 and 16 KiB give 36.2-36.9 GB/s from SMS.
- From SMS a raw stream beats OCM by about 58 %: one OCM window sits behind one HN-S, while SMS is
  spread over all five.

## 3. Prefetch

| Finding | Run | Check |
|---|---|---|
| `RPRFM` saves 7-10 % per GDN block streaming from SMS or OCM (one user per call, state cleaned each call), nothing on SPM | #4045 | R |
| Hardware prefetcher, OCM-fed GDN: accuracy 0.98-0.99, coverage 0.97-0.98, timeliness 0.81-0.87, the same in fast and slow cases. So the prefetcher isn't what separates them | #4422, #4423 | ✔ (#4422 CPU 0 row: 0.992 / 0.975 / 0.822) |
| Stress app, SMS- and OCM-fed: L1 refills from software prefetch (`0x32B1`) are 0 in every case; all L1 refills come from the hardware prefetcher. `RPRFM` on, off or further ahead: 151.3-151.9 K tok/s OCM-fed | #4323 | ✔ (counter); R (rates) |

## 4. Compute per block (GDN decode kernel, state already in the CME L1; #3983, #3969) R

| Kernel | One CME | Five CMEs |
|---|---|---|
| `gdn_rows` (Bill's, 446 instructions per 16-row block) | 441.7 cycles per block | 395-454 |
| `gdn_rows_il` (Jacob's reschedule, 335 instructions, bit-equal output) | 371.2 | 353-415 |

Per-instruction costs measured on the CME (#4007): `fdot`/`fmlal` ×4, `fmopa` and `mova` 2 cycles
each; `fcvtn` 1; `fadd` 0.5; back-to-back `st1h` ×2 about 3 (expected 1 from the RTL; open). Detail:
`/scratch/jgeldbach/gdn-cme-results-2026-10-23/README.md`.

## 5. Five CMEs computing at once (bench, `il-sync5`, #4065) ✔

`gdn_rows_il` on all five CMEs, state streamed from SMS, 64 users per CME per rep, synchronized start.

| Measure | Value |
|---|---|
| Per token (8 value heads, 256 KiB of state, split over 5 CMEs) | 2.978 µs |
| Per head, CPUs 0/2/4/6/8 | 1.75 / 1.73 / 1.78 / 1.76 / 1.80 µs |
| State read, combined | 87.2 GB/s (about 90 % of the 96 GB/s stream ceiling) |
| The same with each slot cleaned (`DC CIVAC`) inside the window | 6.126 µs per token |
| One CME doing all five pieces | 13.06 µs per token; 1.62 µs per head |

## 6. Example workload: GDN decode in the stress app

This is one CME workload, not the only one. Its results show what limits the CMEs once they all
stream continuously. Each CME runs `gdn_rows_il_oop` on its own 53,248 B slot per call (one token's
share) and writes the result out of place to Normal non-cacheable SMS. System tok/s = 1 / the
slowest CME's µs per call.

| Run | Feed | Window | System tok/s | µs per call, CPU 0 / 2 / 4 / 6 / 8 | Check |
|---|---|---|---|---|---|
| #4292 case 0 | SMS | 100 ms | **174.9 K** | 5.16 / 5.13 / 5.72 / 5.19 / 5.54 | ✔ |
| #4480 case 0 | SMS | 1 s | **175.6 K** | 5.16 / 5.15 / 5.69 / 5.23 / 5.58 | ✔ |
| #4292 case 1 | OCM, bit 47 at its reset value (1) on all 5 HN-S | 100 ms | 151.6 K | 4.59 / 6.59 / 5.52 / 6.60 / 6.56 | ✔ |
| #4478 case 0 | OCM, bit 47 = 1 at HN-S 88 only, 0 elsewhere | 100 ms | **175.1 K** | 5.52 / 5.42 / 5.71 / 5.37 / 5.41 | ✔ |
| #4479 case 0 | OCM, bit 47 = 1 on all 5 | 100 ms | 151.3 K | 4.61 / 6.61 / 5.54 / 6.60 / 6.52 | ✔ |

"Bit 47" = HN-S `cmn_hns_cfg_ctl[47]` `rd_migrate_on_sfmiss`, set by SCP at boot. OCM-fed: DMA-357
fills CPU 0's ring in OCM0 (HN-S 88); SPM-DMA engines 0-3 fill CPUs 2/4/6/8's rings in OCM1-4.

**Per-CME reads, SMS-fed, 1 s window (#4480 case 0)** ✔

| CPU | µs per call | GB/s of state | Read residence (CME cycles a read is outstanding) | Reads in flight (Little's law) |
|---|---|---|---|---|
| 0 | 5.16 | 10.31 | 327 | 27.4 |
| 2 | 5.15 | 10.34 | 296 | 24.8 |
| 4 | **5.69** | 9.35 | **392** | 29.8 |
| 6 | 5.23 | 10.18 | 314 | 26.0 |
| 8 | 5.58 | 9.55 | 379 | 29.4 |

Residence = `CME_BUS_REQ_RD_PERCYC` (`0x3266`) / `CME_BUS_REQ_RD` (`0x3268`). The SMS side carries
49.7 GB/s of reads plus 50.1 GB/s of result writes; 97 % of HN-S lookups miss, so every read goes to
DRAM.

**Two different "per token" numbers.** The bench's 2.98 µs (section 5) leaves state write-back out of
the timed window. The bench's 6.13 µs cleans every call inside it. The stress app's ~5.2 µs per call
includes the non-cacheable write-back to SMS. Compare like with like.

## 7. What limits throughput

- **Per-CME read latency × reads in flight.** Each call does the same non-stalled work (about 2,510
  CME cycles; R, #4422/#4423). The difference between a fast and a slow call is backend stall, and it
  tracks read residence. An SMS-fed CME keeps about 25-30 reads outstanding and waits on their
  latency. Its reads come back faster than OCM-fed reads (296-392 against 403-479 cycles), so
  bandwidth isn't what starves it (inference, #4480 vs #4478).
- **CPU 4 sets the system rate** in every best case: 5.69 µs SMS-fed (#4480), 5.71 µs OCM-fed (#4478).
  Its reads take longer whatever the source. The extra latency appears to be between its cluster
  and the home nodes, where no counter we've run can see it (inference). CPU 8 is the second
  slowest SMS-fed.
- **HN-S request-queue (POCQ) retries.** The retries are class-credit retries (CME class 1 against
  DMA class 3), not address collisions: class 1 + class 3 = all retries within 2 %, and address
  hazards are under 2 % of retries (R, #4478/#4479). SMS-fed with no DMA, HN-S 88 takes 29 % of all
  requests and retries 42 % of them (#4480 case 1: 862.9 M requests, 363.1 M retries over 1.04 s ✔).
  That falls on all five CMEs alike, so it doesn't explain CPU 4.
- **Not ruled out:** queueing at the SMS side raising every CME's latency together. A run with 3
  SMS-fed CMEs instead of 5 would separate latency from bandwidth.

## 8. What didn't help

| Try | Result | Run | Check |
|---|---|---|---|
| A C1 "helper" core prefetching each CME's state into the DSU L3 (`PRFM PLDL3KEEP`, 1-2 users ahead; or `LDNP`) | **18-22 % slower**: 2.975 µs per token without the helper, 3.511-3.630 µs with it. Only DSU 0's prefetches showed up as CME L3 hits (0.30 per line) | #4180 | ✔ (per token); R (L3 hits) |
| DSU `CLUSTERECTLR.DCC = 0b00` (clean evictions dataless) | **Slower**: 5-CME stream 94.6 → 86.2 GB/s (HW) and 96.2 → 84.9 (RPRFM); GDN 2.961 → 2.989 µs per token. The SLC fills went to 0 but HN-S misses doubled | #4187 | ✔ |
| `RPRFM` variants in the stress app | No change (section 3) | #4323 | ✔ / R |
| Reserving 8 POCQ entries for the CME class | No change (151.8 K tok/s OCM-fed) | #4325 | R |

## Where the raw data is

| Run | Folder under `/scratch/jgeldbach/asimov-dpa-stress/palladium/` (`uart_1.log` = AP console) |
|---|---|
| #4045 | `cme-perf-pf2/results/run-4045/` |
| #4065 | `cme-perf-sync/results/run-4065/` |
| #4180 | `cme-perf-helper/results/` |
| #4187 | `cme-perf-dcc/results/` |
| #4292 | `dma-ocm-gdn-nc/results/b1/` |
| #4323 | `dma-ocm-gdn-rd/results/` |
| #4422, #4423 | `dma-ocm-gdn-split1/results/`, `dma-ocm-gdn-split0/results/` |
| #4478, #4479 | `dma-ocm-gdn-b47mix/results/`, `dma-ocm-gdn-b47all1/results/` |
| #4480 | `dma-gdn-smsfed-long/results/` |
| #3969, #3983, #4007 | `/scratch/jgeldbach/gdn-cme-results-2026-10-23/runs/<id>/` |

Each folder has a `RUN-REPORT.md` with the full analysis. Those reports are working notes and use
our internal labels.
