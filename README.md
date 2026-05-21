# Intel vs AMD CPU/Memory Subsystem Comparison — Deliverable Bundle

This bundle contains the complete writeup, source code, driver scripts,
result CSVs, and system inspection logs from the Intel Xeon 6962P vs
AMD EPYC 9654 memory-subsystem comparison study.

## Contents

```
.
├── pass1_outline.md         Pass 1: outline + tables only (for review)
├── pass2_writeup.md         Pass 2: full prose writeup
├── README.md                this file
│
├── code/                    All source code and scripts
│   ├── Makefile                builds 5 C binaries
│   ├── inspect_pages.c         pinning + NUMA sanity check
│   ├── ptr_chase.c             single-thread load-use latency
│   ├── bw_avx512.c             single-thread AVX-512 bandwidth
│   ├── bw_multi.c              multi-thread aggregate bandwidth
│   ├── c2c_lat.c               core-to-core CAS ping-pong
│   ├── step0_inspect.sh        system characterization (read-only)
│   ├── gpu_topo_inspect.sh     PCIe / accel topology (not used in writeup)
│   ├── sweep_full.sh           ptr_chase size sweep, 32 KiB to 4 GiB
│   ├── sweep_bw.sh             bw_avx512 size + cross-socket sweep
│   ├── sweep_bw_multi.sh       bw_multi thread-count scaling
│   └── sweep_c2c.sh            c2c_lat dense scan
│
├── data/                    Measurement output CSVs
│   ├── ptr_chase_full_delphi-3af6_*.csv   Intel latency sweep
│   ├── ptr_chase_full_andoria-15_*.csv    AMD latency sweep
│   ├── bw_sweep_delphi-3af6_*.csv         Intel single-thread BW
│   ├── bw_sweep_andoria-15_*.csv          AMD single-thread BW
│   ├── bw_multi_delphi-3af6_*.csv         Intel multi-thread BW scaling
│   ├── bw_multi_andoria-15_*.csv          AMD multi-thread BW scaling
│   ├── c2c_lat_delphi-3af6_*.csv          Intel core-to-core scan
│   └── c2c_lat_andoria-15_*.csv           AMD core-to-core scan
│
└── logs/                    System inspection outputs
    ├── inspect_intel_delphi-3af6_*.log    primary Intel test system
    ├── inspect_intelCI_delphi-17cf_*.log  Intel CI/CD reference
    ├── inspect_amd_andoria-15_*.log       AMD system
    └── core_grouping.log                  /sys CPU topology dump (Intel)
```

## Quick reference

To rebuild and run all the tests on a fresh Ubuntu 22.04+ machine:

```bash
cd code/
sudo apt install -y libnuma-dev build-essential numactl
make
bash step0_inspect.sh       # ~30 sec
bash sweep_full.sh          # ~2 min
bash sweep_bw.sh            # ~5 min
bash sweep_bw_multi.sh      # ~10 min
bash sweep_c2c.sh           # ~5-8 min
```

Total wall time per system is about 25 minutes. Each sweep script reserves
hugepages via sudo and restores them on exit, including on Ctrl-C or
crash. CSV output filenames include the hostname and timestamp.

## Where to start reading

- For a quick scan of findings, read the executive summary in
  `pass2_writeup.md` (section 1) followed by the headline tables in
  sections 4.1 and 4.2.
- For the full narrative, read `pass2_writeup.md` end-to-end.
- For just the data structure and tables without prose, read
  `pass1_outline.md`.
- For methodology details and tool design, read sections 3 and 6 of
  `pass2_writeup.md`.
- For the Intel L3 latency validation against external sources, read
  section 5.5 of `pass2_writeup.md`.

## Systems characterized

- `delphi-3af6` — Intel Xeon 6962P, primary test system, sudo access
- `delphi-17cf` — Intel Xeon 6960P, CI/CD reference (read-only inspection)
- `andoria-15` — AMD EPYC 9654 Embedded, AMD comparison system

All three systems are characterized in `logs/`. Only `delphi-3af6` and
`andoria-15` were used for performance measurements.

## External references

Cited inline in `pass2_writeup.md` section 7. The primary external source
is the Chips and Cheese article *A Look into Intel Xeon 6's Memory
Subsystem* (Chester Lam, September 2025) at
<https://chipsandcheese.com/p/a-look-into-intel-xeon-6s-memory>.

---

Bundle created May 21, 2026.
