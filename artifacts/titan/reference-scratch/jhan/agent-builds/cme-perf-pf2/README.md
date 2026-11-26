# cme-perf pf2: how well a CME prefetches from SMS, OCM and SPM (prepared, NOT launched)

Prepared by dev-platform@asimov-stress for orch-lead (decision 63, Jacob 2026-10-23: "how good the CME is at prefetching its memory from SPM and SMS"; the go covers plan, build, gate and enqueue). **The lead enqueues it after the verifier's PASS.** Hashes are in `MANIFEST.md`.

**pf2 against `cme-perf-pf` (gated PASS 19:35Z):** the same rows, run SMS first and SPM last; the stream cleans what RPRFM fetched past each lap; `check_stream.py` also checks the prefetch address (the verifier's open points 1 and 2 and the distance test, lead 19:35Z). Only `cme_perf` and `rows.sh` differ, and with them the rootfs, `linux,initrd-end` and the composite after 0x2000000.

## Why
E9 (#3969) showed that RPRFM saves 7-10% when GDN streams its state from OCM. Bill's stage and the coming DMA work need to know which memory a CME streams from well. No one has measured CME prefetch from SMS (DRAM) or SPM, and no one has run software prefetch outside GDN.

## What the run is
`cme-perf-isa2`'s boot (#4007): `hemi_rtws_tlm`, the same RTL, SCP, BL31, kernel, base rootfs, check data and module. Only `cme_perf`, `rows.sh`, `init.sh` and `cme_perf.rows=pf` change, and with them the rootfs, `linux,initrd-end` and the composite after 0x2000000. Rows, in order:

| Row | CPUs | What |
|---|---|---|
| `e9-sms-pf`, `e9-sms-nopf` | 0,2,4,6,8 | E9 with the state in SMS: 13 blocks, 32 slots per CPU (1.6 MiB; 8.3 MiB in all), cleaned after each call; RPRFM on (`za`), off (`nopf`) |
| `st-sms` | 8 | stream from SMS: 16 MiB, 64 laps of 256 KiB in turn |
| `st-sms-all` | 0,2,4,6,8 | stream from SMS on all five CMEs at once, 8 MiB each |
| `il-e9-sms-pf` | 0,2,4,6,8 | `gdn_rows_il` with RPRFM from SMS |
| `e9-ocm-pf`, `e9-ocm-nopf` | 0,2,4,6,8 | #3969's `e9-pf`/`e9-nopf`, the same arguments (the anchor): 4 slots of the home OCM window, cleaned after each call |
| `st-ocm` | 8 | stream from the home OCM window (window 4), 256 KiB per call |
| `e9-spm-pf`, `e9-spm-nopf` | 0,2,4,6,8 | E9 with the state in SPM: 4 slots in the CPU's SPM extent |
| `il-e9-spm-pf` | 0,2,4,6,8 | `gdn_rows_il` with RPRFM from SPM |
| `st-spm` | 8 | stream from the CPU's SPM extent, 256 KiB per call |

SMS first and SPM last: no CME access to SPM has run on Palladium, and a fault or a hang there would lose every later row; the SMS rows are the ones Jacob and Bill need first.

The stream rows run RPRFM distance 0 (the hardware prefetcher alone), 1, 2, 4 and 16 KiB; `st-sms-all` runs 0 and 4 KiB. Every decode row keeps the digest check of #3969 (`--expect-digest`). Every rep is printed (`CME,r`). No event or stall-counter pass runs.

- **SMS** is the bench's DRAM: Linux RAM is `sms_dram_high` at 0xC0_0000_0000, hashed over all five HN-S (`asimov-address-map` `profiles/sam_map.yaml` lines 131-135 and 245). The SLC is 1 MiB per HN-S, 5 MiB in all. `DC CIVAC` of a dirty line writes it through and does not allocate it in the SLC (measured, `presilicon-perf/acp/latency/README.md` lines 170-171). The case of a clean line is not measured, so every SMS row rotates through more than 5 MiB per CPU set, and each lap is cleaned after its call.
- **SPM** is mapped Normal-NC: the four column windows of the stress app (0x3001_0000 + n × 0x0440_0000, 0x3F_0000 bytes, SRAM quarter n), added to `spm_dma_map` in `init.sh`. CPU 2d uses window d mod 4 from 1 MiB + (d / 4) × 1 MiB, so DSU 4 shares window 0 with DSU 0 without overlap, and no extent reaches SRAM 0x8_0000-0xB_FFFF. SPM is written only with 64 B streaming stores through the CME (`cmp_copy_sm`, the path of the GDN kernel's own state stores): on Normal-NC a CPU store may be split into 8 B beats, which the SPM access-width bench treats as a bus error. SPM is never cleaned.
- **No write-back SPM row.** `sam_map.yaml` lines 163-166 mark spm0-3 `cacheable: false` and say "Non-CHI writers require non-cacheable mappings" (DMA, SVL and SAL write SPM without snooping the CPU caches). The RTL's SPM interface note gives Device-GRE as the target policy and 8/16/32 B accesses (asimov `design/spm/doc/spm-cmn-if.md` lines 81-87 and 296-306). `presilicon-perf/spm-access-width` lists a write-back mapping as an open hardware question, run only on the FVP. The expectation is no prefetch gain from SPM (Normal-NC); the rows measure it.
- **Stream** (`bench/stream.S`): each loop pass reads 1 KiB with four `LD1B` of four vectors and folds them with 16 `EOR`s. `cmp_stream_pf` first issues `RPRFM PSTKEEP` of 1 KiB at the distance ahead (the GDN kernel's form, `Xm` = 1024); `cmp_stream_hw` has a `NOP` in its place, so the two loops differ in that instruction only. Every call's XOR must equal its lap's. After each call the lap is cleaned together with what RPRFM fetched past its end (up to the distance, clipped to the buffer), so the next lap starts cold at every distance; in `cme-perf-pf` RPRFM got up to 6 % of a lap at 16 KiB for free in `st-sms` and `st-sms-all`. GB/s = 256 KiB / median time; CME cycles per 64 B line = median CME cycles / 4096.

## What changes (asimov-bench feature/cme-perf-pr3, local commits, not pushed)
- `94e47c2` cme-perf: measure CME prefetch from OCM, SMS and SPM (stream mode, `--mem spm`, rows `pf`, `fvp-pf`, `fvp-pf-spm`, checker, READMEs).
- `298ba81`: the FVP SPM boot stopped in `f-e9-spm-pf` with `copy16_align` (the check data's start state is not 16 B aligned); only the destination needs alignment. The FVP pf rows also compare with the exact FVP digest, as `fvp-gdn-il` does.
- `9328b56`: SPM is written with 64 B CME stores (`cmp_copy_sm`), not 16 B CPU stores (reason above). `cme-perf-pf` was built here.
- `60a379c` (pf2): the row order above; the overshoot clean; `check_stream.py` checks that the prefetch address is p + distance (x4 = x0 + x2 and x3 = 1024 before the loop, `RPRFM pstkeep, x3, [x4]` in it, x4 and x0 advancing 1 KiB per pass).
- **Checker** (`check_cme_perf.py --rows pf`): per row rc=0, a record per CPU, the kernel its name says (`za`, `nopf`, `il`) and the memory its name says; the digest check of every decode row; one `CME,st` per CPU and distance with `ok=1`; then `CME,done`. It prints E9 per CPU and memory with RPRFM on and off, and the stream's GB/s and CME cycles per line per distance.

## Checks
- **Build and package** (LSF 567831, `fvp-smoke/lsf-build.out`), asimov-bench `60a379c` with no local changes: bench host test PASS (SPM extents inside their windows, no two DSUs on one extent, clear of SRAM 0x8_0000-0xB_FFFF, the lap XOR); `check_stream.py`: the two assembled loops are 4 `LD1B`, 16 `EOR` and the prefetch slot, equal apart from `RPRFM`/`NOP`, and the prefetch address is p + distance; GDN kernel `make test` and `gen_il --check` PASS; isa `make test` PASS; checker selftest PASS; `SHA256SUMS` OK.
- **Tests that can fail** (by hand, not kept): `check_stream.py` fails `RPRFM` → `NOP` in `cmp_stream_pf`, `add x4, x0, x2` → `mov x4, x0` (the verifier's survivor) or `add x4, x0, x1`, x4 advancing 512 B, and a 512 B range. Checker selftests fail a wrong lap XOR, a missing distance, a digest mismatch, the state in the wrong memory, a `nopf` row that ran `za`, and a run cut in the SPM rows.
- **Against `cme-perf-pf`:** `init.sh`, `in.bin`, `expected-*.bin`, `spm_dma_map.ko`, the SMS profile and SCP BL1/BL2 are byte-equal; `rows_pf` holds the same rows in the new order; `ap_composite.bin` is byte-equal up to 0x2000000; the DTS differs only in `linux,initrd-end`. Against `cme-perf-isa2` (#4007's boot) the same holds, with `cme_perf.rows=pf` in the bootargs.
- **FVP smoke** (Terminus FVP 699128b, this rootfs; `fvp-smoke/`):

| Boot | Row set | Result |
|---|---|---|
| pos (LSF 567863) | `fvp-pf` | PASS: the SMS E9 rows (`za`, `nopf`, `il`, 32 slots, cleaned) give the FVP digest exactly; `f-st-sms` and `f-st-sms-all` every lap's XOR at every distance; `CME,done` |
| spm (LSF 567864) | `fvp-pf-spm` | PASS: `f-st-spm` every lap's XOR; `f-e9-spm-pf` (state in SPM, filled by `cmp_copy_sm`) gives the FVP digest exactly. `spm_dma_map` loads all 9 windows (`rc=0`) |
| old (LSF 567865) | `fvp-gdn-il` | PASS: every gdn-il FVP row, digests as before |

- **Not proven before the run:** any timing (the FVP has none and no CME cycle counts); that the OCM, SMS and SPM rows run on Palladium as on the FVP (the FVP has no OCM, so `e9-ocm-*` and `st-ocm` run on Palladium only, as in #3969); CME stores and loads to SPM on `hemi_rtws_tlm` (no earlier row ran them).
- **If an `e9-spm-*` digest fails on Palladium:** suspect SPM write visibility before the CME. The SPM returns `BRESP` before the data reaches SRAM, and "read-after-BRESP is not a supported synchronization pattern" (asimov `design/spm/doc/spm-cmn-if.md`, Write Data Visibility). The E9 SPM rows read state written by the fill and by earlier calls, microseconds earlier; the coalescer drains after 4 idle cycles or its starvation timer (64 cycles by default), so it is expected to hold. The FVP cannot show it.
- **Shared SPM port:** CPUs 0 and 8 share window 0 and one SPM AXI port (64 GB/s); read their SPM numbers with that in mind.

## Reference numbers
| Source | What | Number |
|---|---|---|
| #3969 `e9-pf` / `e9-nopf` (anchor; `e9-ocm-*` repeat it) | GDN state from OCM, CME cycles per block, RPRFM on / off, CPU 0 / 8 | 509.3 / 564.1, 537.4 / 579.5 (15.25 / 13.83 GB/s, 14.45 / 13.45 GB/s) |
| Naveen, boot M3, CPU 2 (`presilicon-perf/asimov-latency/src/asimov_latency/engines/cme.py` lines 150-155, asimov-bench `e7bfd42`) | one FMOPA with one 64 B load, hardware prefetch only, buffer 16 KiB (L1) / 96 KiB (L2) / 192 KiB (L3) / 8 MiB host-model SMS DRAM | 1.017 / 1.186 / 1.578 / 1.745 ns; from SMS 64 B / 1.745 ns = **36.7 GB/s** |

Compare `st-sms` at distance 0 (hardware prefetch alone) with the 36.7 GB/s: both are one CPU's linear 64 B loads from SMS with no software prefetch. Naveen's loop puts one FMOPA beside each load and reads "host-model SMS DRAM"; `st-sms` has no FMOPA, 4 loads of 4 vectors per 1 KiB, and cleans each lap after its call.

## Time budget
- #4007 (this boot, `cme-perf-isa2`): Linux reached the rows at 0.31 s; the 1.0 s bound took 45 min of emulation (02:13 to 02:57 PDT), with a 38 s licence wait.
- #3969: a five-CPU decode row took 0.01-0.09 s of chip time (`e9-pf` 0.01 s, `e9-nopf` 0.08 s), mostly its UART output.
- Here: 8 decode rows at up to about 0.1 s and 4 stream rows at up to about 0.1 s (fill of up to 16 MiB per CPU and its clean, then 34 to 85 calls of about 10 µs, about 2 kB of records per CPU) give about 1.2 s after 0.31 s, so `CME,done` near 1.5-1.8 s (#4007 also had two pauses of about 80 ms). Bound `--run-cycles 5000000000` (2.5 s, approved): about 2 h of emulation at #4007's rate, plus the licence wait, within `--timelimit 18000`.
- #4007 ended with a record cut mid-line at about 0.5 s, cause not established (its RUN-REPORT). If this run stops the same way, the rows already printed stand; the checker names the first row without its records.

## Pass / fail (`check_cme_perf.py <uart> --rows pf`, asimov-bench `60a379c`)
PASS needs, for every row: rc=0; one `CME,s` per CPU (decode) with the kernel and memory of the row, and the digest check `ok=1`; one `CME,st` per CPU and distance (stream) with `ok=1` and the row's memory; then `CME,done`. Read first: E9 per memory with RPRFM on and off, then the stream's GB/s and CME cycles per line per distance.

## Launch
As #4007 (`runcmeperf-isa2.sh`) with `S=<staged cme-perf-pf2>`, `--run-cycles 5000000000` and its own marker: `hemi_rtws_tlm`, clone 2, 4 boards, `emu/common/scripts/run.sh --task emu --test hemi_tlm --rtws --run-only --run-cycles 5000000000 --timelimit 18000`, `LM_LICENSE_FILE=5280@192.168.1.226`, sums checked at submit. Never `--build`. It can run beside the full-`hemi_tlm` #4032.
