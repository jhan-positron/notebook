# cme-perf pf2 RUN-REPORT: GA13 #4045, run 2026-1023_125129 (decision 63, CME prefetch from SMS, OCM and SPM)

**Result: `check_cme_perf.py uartout/uart_1.log --rows pf` (asimov-bench 60a379c): `cme-perf: PASS`, rc 0.** All 12 rows ended `rc=0`, every decode digest matched (`ok=1`), every stream lap's XOR checked (`ok=1`, `bad=0`), and `CME,done` printed at about 1.03 s chip. The watcher then stopped the run.

**First CME access to SPM on Palladium:** the four SPM rows ran without a hang, an SError or a digest failure.

| Row | Start `up` (s) | rc | Kind |
|---|---|---|---|
| `e9-sms-pf` | 0.31 | 0 | decode, `za`, SMS |
| `e9-sms-nopf` | 0.35 | 0 | decode, `nopf`, SMS |
| `st-sms` | 0.44 | 0 | stream, CPU 8, SMS |
| `st-sms-all` | 0.48 | 0 | stream, 5 CPUs, SMS |
| `il-e9-sms-pf` | 0.51 | 0 | decode, `il`, SMS |
| `e9-ocm-pf` | 0.60 | 0 | decode, `za`, OCM |
| `e9-ocm-nopf` | 0.69 | 0 | decode, `nopf`, OCM |
| `st-ocm` | 0.74 | 0 | stream, CPU 8, OCM |
| `e9-spm-pf` | 0.75 | 0 | decode, `za`, SPM |
| `e9-spm-nopf` | 0.81 | 0 | decode, `nopf`, SPM |
| `il-e9-spm-pf` | 0.87 | 0 | decode, `il`, SPM |
| `st-spm` | 0.93 | 0 (ended 1.03) | stream, CPU 8, SPM |

## E9 decode: CME cycles per block (GB/s), CPUs 0, 2, 4, 6, 8

13 blocks per call, 16 reps, median. SMS and the `il` rows use 32 slots; OCM uses 4.

| Memory | CPU | RPRFM on (`za`) | RPRFM off (`nopf`) | on − off | `il` (RPRFM on) |
|---|---|---|---|---|---|
| SMS | 0 | 620.8 (12.594) | 673.5 (11.677) | −7.8% | 490.8 (15.754) |
| SMS | 2 | 617.4 (12.648) | 683.4 (11.493) | −9.7% | 502.2 (15.412) |
| SMS | 4 | 634.0 (12.346) | 691.2 (11.361) | −8.3% | 505.4 (15.314) |
| SMS | 6 | 630.1 (12.450) | 703.1 (11.182) | −10.4% | 508.9 (15.214) |
| SMS | 8 | 634.8 (12.332) | 708.5 (11.103) | −10.4% | 518.7 (14.941) |
| OCM | 0 | 512.2 (15.102) | 552.3 (14.079) | −7.3% | — |
| OCM | 2 | 536.0 (14.470) | 582.1 (13.396) | −7.9% | — |
| OCM | 4 | 540.2 (14.372) | 583.7 (13.359) | −7.5% | — |
| OCM | 6 | 532.8 (14.569) | 586.2 (13.305) | −9.1% | — |
| OCM | 8 | 534.2 (14.529) | 573.9 (13.577) | −6.9% | — |
| SPM | 0 | 1549.7 (5.185) | 1552.2 (5.179) | −0.2% | 1673.2 (4.811) |
| SPM | 2 | 1437.0 (5.586) | 1433.7 (5.599) | +0.2% | 1612.6 (4.988) |
| SPM | 4 | 1455.8 (5.515) | 1456.2 (5.514) | −0.0% | 1615.4 (4.980) |
| SPM | 6 | 1436.0 (5.590) | 1432.3 (5.604) | +0.3% | 1611.8 (4.991) |
| SPM | 8 | 1618.4 (4.969) | 1618.5 (4.971) | −0.0% | 1725.8 (4.667) |

- **SMS:** RPRFM saves 7.8–10.4% of cycles per block. `il` takes 18–21% fewer cycles than `za` on every CPU, about 503 against 627 on average.
- **OCM against #3969:** this run gives 512–540 with prefetch and 552–586 without. #3969 gave 509–539 with prefetch and 564–580 without. The prefetch rows agree within 1 cycle per block at both ends, and RPRFM saves 6.9–9.1%.
- **SPM:**
  - RPRFM changes nothing (within ±0.3%).
  - SPM takes about 2.3–2.6× the SMS cycles per block (`za`).
  - `il` is 6.6–12.2% *slower* than `za` here, the opposite of SMS.
- **SPM, CPUs 0 and 8:** they are slower than CPUs 2, 4 and 6 in every SPM row. In `za` and `nopf`, CPU 0 is 6.5–8.4% slower and CPU 8 is 11.1–13.0% slower (1550/1618 against about 1436–1456 for `za`). In `il`, CPU 0 is 3.6–3.8% slower and CPU 8 is 6.8–7.1% slower. The verifier noted that CPUs 0 and 8 share SPM window 0, one SPM AXI port. So a shared port is the likely cause (inference).

## Streams: GB/s (CME cycles per 64 B line)

| Memory, CPU | pf 0 (HW only) | 1 KiB | 2 KiB | 4 KiB | 16 KiB |
|---|---|---|---|---|---|
| SMS, CPU 8 (16 MiB) | 34.520 (3.62) | **36.891 (3.38)** | 36.228 (3.44) | 36.178 (3.45) | 36.638 (3.40) |
| OCM, CPU 8 | 22.083 (5.71) | **23.306 (5.41)** | 23.211 (5.43) | 22.821 (5.53) | 22.651 (5.57) |
| SPM, CPU 8 | 14.583 (8.69) | 14.581 (8.69) | 14.581 (8.69) | 14.581 (8.69) | 14.581 (8.69) |

- **SMS:** hardware prefetch alone gives 34.52 GB/s, 0.94× Naveen's boot M3 SMS 36.7 GB/s (1.745 ns per FMOPA + 64 B). With RPRFM at any distance it is 36.2–36.9 GB/s, 0.99–1.01× his figure. The best distance is 1 KiB (+6.9% over HW only); longer distances add nothing.
- **OCM:** at 1 KiB it reaches +5.5% over HW only, and the gain shrinks at longer distances.
- **SPM:** flat at 14.58 GB/s (8.69 cycles per line) at every distance, so software prefetch has no effect on SPM.

### `st-sms-all`: five CPUs streaming SMS at once (8 MiB each)

| CPU | pf 0 | pf 4 KiB |
|---|---|---|
| 0 | 39.255 (3.17) | 37.702 (3.31) |
| 2 | 33.970 (3.68) | 34.456 (3.63) |
| 4 | 31.436 (3.98) | 32.813 (3.82) |
| 6 | 34.575 (3.62) | 32.929 (3.80) |
| 8 | 31.211 (4.01) | 33.669 (3.72) |
| **sum** | **170.45** | **171.57** |

- With all five streaming, each CPU gets 31–39 GB/s, against 34.5 GB/s for CPU 8 alone (`st-sms`). So five CPUs reach about 5× one CPU, and the per-CPU spread is 26%.
- 4 KiB RPRFM changes the sum by +0.7%. It helps CPUs 2, 4 and 8 and costs CPUs 0 and 6.
- The rows ran in sequence, but these streams overlapped across CPUs. Each figure is a per-CPU median over its own laps; the sum is not a measured aggregate.

## Flags

| Flag | Decode rows, SMS and OCM | Decode rows, SPM | Stream rows |
|---|---|---|---|
| `unclean` | 16 of 16 reps, every CPU | 0 | 0 |
| `ssve` | 0 | 0 | 0 |
| `disturbed` | 0 | 0 | 0 (`CME,stend`) |

- **`unclean`, my reading:** `rep_clean()` (`bench/cme_perf.h:150` at 60a379c) fails a decode rep when CME cycles are under 95% of CPU cycles. On `e9-sms-pf` CPU 0 that ratio is 8071 / 8717 = 92.6%. On the SPM rows the CME is the bottleneck and every rep is clean. So `unclean` here marks CPU-side time in the decode loop, not a disturbed rep (inference; the dev seat should confirm). The checker does not gate on it.
- No rep is flagged `ssve` or `disturbed`.

## Health

- **Uarts:**
  - uart_1 has no panic, Oops, Unhandled, SError or `CME,fatal` lines; the only `panic` match is `panic=0` on the command line.
  - uart_0 has no error or CRIT lines.
- **M7:** this run has no M7 probe readings. `PROBE_TIMES_NS` is unset in the script, as on #4007, and the run was stopped before the final probe. So M7 health is not recorded here.
- **Bring-up:** wmem preload PASS.
- **Release check:** `RELEASE_WRITES=0 VIA_FARM_LINKS=0` (82 farm link targets).

## Run

- **Host:** GA13 ga13pd01, 4 boards. Build: clone 2 farm `dpa/asimov-a10181848-cme`, `hemi_rtws_tlm.z3` (a10181848).
- **Script:** `runcmeperf-pf2.sh` (md5 a6e2f17c) = `runcmeperf-isa2.sh` with `S=dpa/cme-perf-pf2`, `--run-cycles 5000000000` (2.5 s bound) and the `cmeperfpf2-release` marker.
  - `--rtws --run-only --timelimit 18000`, `EMU_VDEBUG_PORT=8293`, `LM_LICENSE_FILE=5280@192.168.1.226`. No `--build`.
- **Package:** GA13 `dpa/cme-perf-pf2` (new dir), sums verified at stage and at submit (SHA256SUMS sha256 a21e07cb).
  - Boot args `cme_perf.rows=pf` (`CME,boot,rows=pf`).
  - `cme_perf` src `src-06121737e30e`, from asimov-bench feature/cme-perf-pr3 60a379c.
- **Licences:**
  - xmsim env: `LM_LICENSE_FILE=5280@192.168.1.226:5280@ga13ut01`.
  - AVIP BFMs initialised with 0 checkout failures.
  - `Xcelium_Single_Core` wait about 6 min.
- **Module warning:** run.sh printed `Unable to locate a modulefile for 'verisiumdebug/2603/26.03.001'`, as on #4001 and #4007. It had no effect.

### Timeline (PDT, 10-23)

| Time | Event |
|---|---|
| 12:51:29 | submitted (decision 63, on receipt); boards acquired at once |
| 12:57:39 | xmsim log started (licence wait about 6 min) |
| ~13:12 | Linux booting on uart_1 |
| 13:31 | `e9-sms-pf` started (up=0.31 s) |
| 13:52 | `e9-spm-pf` started (up=0.75 s), the first SPM row |
| 14:00 | `st-spm` started (up=0.93 s) |
| 14:01:35 | watcher saw `CME,done` and TERMed the timeout wrapper |
| 14:01:39 | `RUNSH_EXIT=1`; queue row `failed` (not `quarantined`), so no `--release` |

## Files

RUN-REPORT.md, check_cme_perf.txt, uartout/ (uart_0, uart_1, debug), emu.log, xrun_stdout.log, MANIFEST, run.tcl, hemi_sys_mem.log, gc_wmem_preload.log, fw_build.log, vdebug.env, runcmeperf-pf2.sh, runcmeperf-pf2.log, release-writes-cmeperfpf2.txt(.farm-link-targets, .via-farm), tool/check_cme_perf.py (60a379c extract), SHA256SUMS.
