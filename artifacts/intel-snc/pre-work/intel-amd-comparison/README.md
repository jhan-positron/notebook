# Intel vs AMD CPU/Memory Subsystem Comparison

Comparison study of an Intel Xeon 6962P (Granite Rapids-AP) versus an
AMD EPYC 9654 (Zen 4 Genoa), both two-socket server systems. Built
around the September 2025 Chips and Cheese article *A Look into Intel
Xeon 6's Memory Subsystem* by Chester Lam.

## Documents

- `pass1_outline.md` — Pass 1 outline with tables, bullets, diagrams,
  and citations. The structured form.

- `pass2_writeup.md` — Pass 2 full prose writeup. Same content, prose
  form, ~1700 lines. The narrative form.

Both documents cover the same material; they are alternative
presentations, not sequential parts.

## Directory layout

```
intel-amd-comparison/
├── README.md                this file
├── pass1_outline.md         Pass 1 (outline format)
├── pass2_writeup.md         Pass 2 (prose format)
├── code/                    C source + driver scripts
│   ├── inspect_pages.c
│   ├── ptr_chase.c
│   ├── bw_avx512.c
│   ├── bw_multi.c
│   ├── c2c_lat.c
│   ├── Makefile
│   ├── step0_inspect.sh
│   ├── gpu_topo_inspect.sh
│   ├── load_snapshot.sh
│   ├── sweep_full.sh
│   ├── sweep_bw.sh
│   ├── sweep_bw_multi.sh
│   ├── sweep_c2c.sh
│   ├── sweep_dram_lat.sh
│   └── sweep_dram_bw.sh
├── data/                    CSV results (one round, 2026-05-25)
│   ├── ptr_chase_full_<host>_*.csv
│   ├── ptr_chase_dram_<host>_*.csv
│   ├── bw_sweep_<host>_*.csv
│   ├── bw_dram_<host>_*.csv
│   ├── bw_multi_<host>_*.csv
│   └── c2c_lat_<host>_*.csv
├── figures/                 architecture diagram (PNG + generator)
│   ├── intel_xeon_6962p_architecture.png
│   └── gen_diagram.py
└── logs/                    sidecar logs for each sweep + snapshots
    ├── <sweep>_<host>_*.log
    ├── load_snapshot_<host>_*.log
    ├── inspect_<host>_*.log
    └── core_grouping.log
```

## Build (Ubuntu 22.04+)

```bash
sudo apt install -y libnuma-dev build-essential numactl
cd code/
make
```

## Run

Edit driver scripts to point at the build directory if needed; by
default they use the absolute path
`/scratch/jhan/Intel_vs_AMD/tools/inspect_pages_n_ptr_chase/`.
Then run:

```bash
bash load_snapshot.sh                    # pre-test state snapshot

bash sweep_full.sh                       # ~3-4 min
bash sweep_bw.sh                         # ~5 min
bash sweep_bw_multi.sh                   # ~5-10 min (may fail at high thread)
bash sweep_c2c.sh                        # ~6-8 min
bash sweep_dram_lat.sh                   # ~10 min
bash sweep_dram_bw.sh                    # ~1 min

bash load_snapshot.sh                    # post-test state snapshot
```

Total wall time roughly 30-40 minutes per system.

## Data round used in the writeup

All findings in both `pass1_outline.md` and `pass2_writeup.md` come
from a single test round on 2026-05-25:

```
Host             Run start (UTC)        Sweeps
─────────        ─────────────────      ───────────────────────
delphi-3af6      2026-05-25 01:09-01:45 all 6 sweeps + pre/post snapshots
andoria-15       2026-05-25 01:09-01:37 all 6 sweeps + pre/post snapshots
```

No measurements are mixed across runs. Each CSV in `data/` has a
matching `.log` in `logs/` that documents the run (including any
failures and a per-test pass/fail summary at the end).

## License

Internal study. Not for redistribution.
