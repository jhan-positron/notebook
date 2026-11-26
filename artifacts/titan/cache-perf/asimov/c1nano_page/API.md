# API of the c1nano_page package

## Short version

- `data.py` parses the raw files of six boots once and returns one object `D` with generic row access and named derived tables. This file documents it (Part 1).
- `viz.py`, `shell.py`, `refs.py` and `words.py` are documented in `API_part23.md` (Parts 2 and 3) in the same folder. The fixed ids of the page are in `IDS.md`.
- `python3 gen_c1nano_perf.py --out <file>` (from the project folder) builds the page. `python3 -m c1nano_page.data` runs the self-test of the data layer.

## Part 1: the data layer `data.py`

### Short version

- `from c1nano_page import data; D = data.load()` parses the core files of boots F1, E, B, C, D and R3 once (about 0.3 s) and returns one cached object `D`.
- `D` gives generic row access for every latency, bandwidth and mesh-counter file of the six boots, and 41 named derived tables (listed in `data.TABLES`), which include every table of section 6 of the critic sheet.
- `python3 -m c1nano_page.data` asserts 434 values (418 against sections 1 and 7 of the critic sheet, 16 on the reps of the shared rows and on the builds and command lists of two boots) and prints `selftest OK: 434 checks`. Add `-v` to print each check.

### Words used here

- Boot key: one of `'F1', 'E', 'B', 'C', 'D', 'R3'` (`data.BOOTS`). `D.boot_name[b]` is the page name ("boot F1"). `D.boot_first_use[b]` is the wording for the first use in a section ("boot B (prefetchers off, the L3 holds no data)").
- Timed row: one CSV data row (one rep). Best row: the row that the program prints with `best` in it.
- Chain row: the derived row of one footprint of a latency file. Bandwidth row: the derived row of one command and kernel of a bandwidth file.
- `file`: the base name of the CSV file (or `cmn-counts.csv`, `log.txt`, `sysinfo.txt`, `dmesg.txt`). `line`: a 1-based line number in that file.

### Rules that hold for every table

- Best value. Latency: the program's best row, which equals the smallest timed row. Bandwidth: the program's best row, which equals the largest rep. The self-test asserts both on every row of the six boots.
- `line` is the first timed row whose value equals the best value. It carries the counters and the per-thread columns. `best_line` is the program's best row. Cite `line`. `data.cite(row)` returns `'F1 latency-dram-small.csv:5'`.
- Counters of a row are those of the timed row at `line`. `<k>_reps` lists the counter over all timed rows.
- Spread (one definition): `(largest - smallest) / best`, in percent. Best is the smallest for latency and the largest for bandwidth. Function `data.spread_pct(vals, best)`.
- Rep time of a bandwidth rep: `total_bytes / aggregate_GBps` in ns (1 GB/s is 1 byte per ns). The `elapsed_s` column is never used for a derived value.
- Clock: `data.CYCLES_PER_NS` = 2.0 (`D.cycles_per_ns`). The measured pooled ratio is in `D.clock`.
- Units: latency in ns per load, counters in events per load (latency files) or per 64 bytes transferred (bandwidth files), rates in GB/s (1e9 bytes per second), sizes in bytes, percentages in percent.
- No value is rounded. Round when formatting. A difference can show `0.9215000000000001`.
- Every row of a derived table carries `boot`, `file`, `line`, `best_line`. A row that compares two boots carries the boot F1 (or boot E, or boot D) side in those four keys and the other side under a prefix (`b_`, `e_`, `r3_`, `c_`). A mesh-counter row has `best_line = None`.
- Typed facts (not measured): `BOOT_COND`, `REGION_NODE`, `PORT_XY`, `FIFTH_PORT_XY`, `DOC`. Cite their document with a `[RefN]`.

### Module-level names

| Name | Meaning |
|---|---|
| `load()` | returns `D` (cached) |
| `selftest(verbose=False)` | asserts, prints `selftest OK: N checks`, returns N |
| `TABLES` | dict: name of every derived table -> one line |
| `BOOTS`, `BOOT_NAME`, `BOOT_FIRST_USE`, `FOLDER`, `RUN`, `BOOTDIR`, `ROOT` | boot keys, page names, first-use wording, run folder name (`membench-jibin-011`), run folder path, boot folder path, project folder |
| `BOOT_COND[b]` | typed: `l3` (`'on'` or `'no data'`), `prefetchers` (`'on'` or `'off'`), `ocm_mapping` (`'4 KiB entries'` or `'64 KiB translations'`), `script` |
| `KIB`, `MIB`, `LINE` (64), `CYCLES_PER_NS` (2.0), `CLOCK_MIN_LOADS` (4096), `REGION_BYTES` (262144), `REGION_LINES` (4096) | constants |
| `REGION_NODE` | `(88, 160, 216, 288, 344)`: OCM region -> home node id (typed, `lib_run.sh` line 39) |
| `PORT_XY` | `{2: (2,3), 4: (3,2), 6: (4,3), 8: (5,2)}`: CPU -> mesh coordinates of its cluster port (typed, operator's README of `membench-jibin-004`, line 36) |
| `FIFTH_PORT_XY` | `(1, 2)`: the cluster port that no test CPU uses (node id 80) |
| `CPUS` | `(2, 4, 6, 8)` |
| `DOC` | typed documented instruction throughput: `read_bytes_per_cycle` 32.0, `write_bytes_per_cycle` 16.0, `read_gbps` 64.0, `write_gbps` 32.0, `l1_hit_cycles` (2, 4), `l2_hit_cycles` (10, 12), `source`. Also `D.doc` |
| `SHORT`, `COUNTER_KEYS`, `PF_KEYS` | CSV column -> short key, the counter keys, `('l1pf','l2pf','l2byl1pf')` |
| `KERNEL_LABEL` | kernel -> page wording (`'read-pf4'` -> `'software prefetch 4 lines ahead'`, `'read-2s'` -> `'two streams'`, `'read'` -> `'plain read'`) |
| `VAR_KERNELS`, `L1_SIZES`, `WRITER_LISTS` | `('read','read-pf4','read-pf8','read-pf16','read-2s')`, `(4096, 8192, 16384, 24576)`, `('2-4','2-8','2-3','2-4-6-8','2-3-4-5','2-3-8-9')` |
| `fmt_size(bytes)` | `'4 KiB'`, `'1.5 MiB'`, `'1.25 MiB'` |
| `spread_pct(vals, best)`, `geomean(vals)` | the page's spread, geometric mean |
| `lstsq(A, y)` | least squares: dict `coef, res, rms, max_res` (or `None`) |
| `two_pct_rule(max_res, smallest)` | dict `limit` (0.02 x smallest), `pct`, `valid` (`max_res <= limit`) |
| `node_xy(node)`, `steps_xy(cpu, region, ports=None)`, `mean_steps(cpu)` | `(x, y)` of a node id (id = 64 x + 8 y), `(X steps, Y steps)`, mean over the five regions |
| `chain_kind(header)`, `chain_shape(sparse)` | the page wording of a chain |
| `cite(row)` | `'<boot> <file>:<line>'` |
| `parse_latency`, `parse_bandwidth`, `parse_cmn`, `parse_log`, `parse_mesh_map`, `verify_sha256(run_dir)` | the parsers |

Short keys of the counter columns (the `_per_load` or `_per_line` ending is dropped):

| Short key | CSV column | Event | Page name |
|---|---|---|---|
| `ns` | `ns_per_load` | - | chain load |
| `cycles`, `cyc_line` | `cycles_per_load`, `cycles_per_line` | cycle counter | cycles per load, cycles per 64 bytes transferred |
| `l1` | `l1d_refill` | 0x03 | L1 refills |
| `l2` | `l2d_refill` | 0x17 | L2 refills |
| `a2` | `l3d_refill_rd` | 0xA2 | L3 read refills |
| `l1pf` | `l1d_refill_hwprf` | 0x81BC | L1 prefetch refills |
| `l2pf` | `l2d_refill_hwprf` | 0x81BD | L2 prefetch refills |
| `l2byl1pf` | `l2d_refill_l1dhwprf` | 0x0111 | L2 refills by the L1 prefetcher |
| `l2hit`, `l3acc`, `l3hit` | `l2d_hit_rd`, `l3d_access_rd`, `l3d_hit_rd` | 0x81C5, 0xA0, 0x81C6 | L2 hits, L3 accesses, L3 hits (the hit set) |
| `l1tlb`, `l2tlb`, `walk`, `walk_block`, `walk_page` | `l1d_tlb_refill`, `l2d_tlb_refill`, `dtlb_walk`, `dtlb_walk_block`, `dtlb_walk_page` | 0x05, 0x2D, 0x34, 0x8188, 0x818A | TLB set, walk set |
| `perf_cov` | `perf_cov` | - | counter running time / enabled time |

Boot R3 has `l1`, `l2`, `a2` only. Its chain rows have `l1pf = l2pf = l2byl1pf = None` and `unacc_l2 = None`.

### Generic access

| Call | Returns |
|---|---|
| `D.files[boot]` | `{'latency': [...], 'bandwidth': [...], 'all': [...], 'cme': [...]}` file names. Core files only are parsed (no `cme-` file) |
| `D.has(boot, file)` | True when the boot has that core CSV file |
| `D.latblocks(boot, file)` | list of latency blocks, one per command (`latency-control-cpu2.csv` of F1 and R3 has two) |
| `D.lat(boot, file, size=None, block=0)` | one footprint entry. `size=None` takes the first footprint |
| `D.latrow(boot, file, size=None, block=0)` | the chain row of that footprint |
| `D.latrows(boot, file, block=0)` | the chain rows of every footprint of the block, in file order |
| `D.sweep(boot)` | 24 chain rows: 12 of `latency-dram-small.csv`, 11 of `latency-dram-large.csv`, then the row of `latency-dram-flushed.csv` |
| `D.sweep_row(boot, size, kind=None)` | one row of the sweep. Without `kind` the flushed row is skipped |
| `D.bw(boot, file, kernel=None, size=None)` | bandwidth rows of a file. With `kernel` and `size`: the one row or `None` |
| `D.one_core(kernel, size)` | one row of `D.bw_1core` or `None` |
| `D.var(boot, kernel, size)` | one row of `D.bw_var` (boot E, C or B) |
| `D.l1_rows(boot)` | the 16 L1-form rows of boot `'E'` or `'C'` |
| `D.mc(group, kernel, size)` | one row of `D.mc_rows` |
| `D.cmn(boot, label=None, event=None, node=None)` | rows of `cmn-counts.csv`: `boot, file, line, label, event, node, count, enabled_ns, running_ns, scaled_count` |
| `D.cmn_labels(boot)`, `D.cmn_nodes(boot, label)`, `D.cmn_value(boot, label, event)` | labels in file order, `{node id: requests received}`, the count of a one-row event |
| `D.mesh_row(label, boot='F1')` | one row of `D.mesh_cmd` by label. `boot='R3'` builds the same row form from boot R3 (without the net keys) |
| `D.log[boot]` | `commands, starts, done, exits, pwrstat, cpu3, flags, commit, n_lines` from `log.txt` |
| `D.log_lines(boot, file)`, `D.log_line(boot, file, block=0)` | line numbers in `log.txt` of the commands that wrote a CSV file (matched through `all.txt`: all 564 core blocks of the six boots match) |
| `D.text(boot, name)`, `D.text_line(boot, name, n)` | lines, or line n, of `log.txt`, `sysinfo.txt`, `all.txt` (boot folder) or `dmesg.txt`, `README.md`, `SHA256SUMS` (run folder). `None` when the file is absent (boot R3 has no `dmesg.txt`) |
| `D.verify_sha(boot)` | `ok, total, bad, missing, entries, file`, computed with hashlib |
| `D.fit_pred(steps_x, steps_y, boot='B')` | value of a route fit at a step count, ns per load |
| `D.unacc_ocm(boot)` | `{cpu: largest "L2 refills not accounted for" over every pass of the OCM latency files}` (files of the TLB and walk sets left out). `None` for R3 |
| `D.step(cpu, region)` | `(dx, dy)` |

Latency block: `boot, file, path, index, line` (line of the `# latency:` header), `header` (dict: `cpu, mem, cntfrq_hz, loads, reps, fresh, flush, sparse, seq, cme, events`. Boot R3 lacks `seq` and `events`: they are filled with `0` and `'refill3'`), `header_text, columns, bracket_overhead_ns, bracket_overhead_line, sizes` (dict size -> entry), `order` (sizes in file order), `perf_lines` (count of `# perf:` lines).

Footprint entry: `size, lines` (chain members), `backing, segments, sparse, line` (line of `# size=`), `reps` (list of timed rows), `best, best_line`.

Timed row of a latency file: `mem, size, mode, rep, loads, line, ns, cycles` plus the short counter keys that the file has, and `perf_cov`.

Chain row (returned by `D.latrow`, and the row form of every latency table):

| Key | Unit | Meaning |
|---|---|---|
| `boot, file, block, line, best_line, size_line, header_line` | - | source. `line` = the timed row that carries the best value |
| `cpu, mem, events` | - | from the header (`mem` is `dram` or `ocm`) |
| `size, label, lines, backing, segments` | bytes, -, count | footprint, its label (`'384 KiB'`), chain members, `hugetlb` / `4k` / `ocm`, OCM regions |
| `kind` | - | `walked many times`, `walked once`, `every line flushed first`, `address order` |
| `shape` | - | `every line`, `one line per 4 KiB page`, `one line per page at varied offsets` (the last is not used on the page) |
| `loads, passes` | count | loads of the timed row, `loads / lines` (walks per timed row) |
| `best`, `best_ns` | ns per load | the best value (two names for one number) |
| `best_mode` | - | CSV `mode` of the timed row at `line` |
| `reps`, `n_reps`, `rep_rows` | ns, count, - | every timed value in file order, their count, the timed rows as dicts |
| `spread_pct`, `median`, `max` | %, ns, ns | over `reps` |
| `cycles`, `cyc_per_ns` | cycles per load, - | of the timed row at `line` |
| `l1, l2, a2, l1pf, l2pf, l2byl1pf` | per load | of the timed row at `line` (`None` where the file has no such column) |
| `<k>_reps` | per load | each counter over all timed rows |
| `l2hit, l3acc, l3hit` / `l1tlb, l2tlb, walk` / `walk_block, walk_page` | per load | only in files of the hit, TLB or walk set |
| `unacc_l2` | list, per load | "L2 refills not accounted for" per timed row: `l2 - l2pf - l2byl1pf - a2`. A difference of counters |
| `bracket_overhead_ns` | ns | the command's empty-bracket value. Not subtracted from any row |

Bandwidth row (returned by `D.bw`, and the row form of every bandwidth table):

| Key | Unit | Meaning |
|---|---|---|
| `boot, file, block, header_line, line, best_line` | - | source. `line` = the rep that carries the best value |
| `header` | dict | `threads, bytes_per_thread, passes, reps, mem, flush_before, flush_after, cme, asm_passes, dsb_st, no_fold, cntfrq_hz` (missing keys of older builds are filled with 0) |
| `mem, backing, kernel, kernel_label, threads, size, label, passes` | - | `size` = bytes per thread, `passes` = passes per rep |
| `form` | - | `looped` or `single-call` (header `asm_passes`) |
| `flush_before`, `has_counters`, `perf_lines` | - | header flag, True when the file has counter columns, count of `# perf:` lines of the block |
| `best` | GB/s | the best value (aggregate of all threads) |
| `reps`, `reps_gbps`, `n_reps`, `rep_rows`, `best_rep` | GB/s | every rep value, the same list, the count, the reps as dicts, the rep at `line` |
| `spread_pct` | % | over `reps` |
| `total_bytes`, `bytes_per_pass` | bytes | of the best rep, `total_bytes / passes` (a copy counts read plus written bytes) |
| `ns_rep`, `ns_pass` | ns | `total_bytes / best`, `ns_rep / passes` |
| `thr_min`, `thr_max` | GB/s | per-thread columns of the best rep |
| `per_thread` | GB/s | `best / threads` |
| `ns_per_64` | ns | `64 / per_thread`: elapsed ns per 64 bytes transferred by one thread. Loop throughput |
| `bytes_per_cycle` | bytes | `per_thread / 2.0` |
| `eff_cycles_64` | cycles | `ns_per_64 x 2.0`: effective cycles per 64 bytes transferred (`128 / best` for one thread) |
| `cyc_line, l1, l2, a2, l1pf, l2pf, l2byl1pf`, `<k>_reps` | per 64 bytes | only when `has_counters` |

A rep dict (`rep_rows`): `rep, total_bytes, elapsed_s, gbps, thr_min, thr_max, line, ns, ns_pass` and the counters.

### Derived tables

Each table of section 6 of the critic sheet is here under its name. Tables that the sheet lists as one row per boot are dicts keyed by the boot key.

#### Boots, platform, integrity (section 1 of the page)

- `D.boots`: 6 rows in the order F1, E, B, C, D, R3. `D.boot[b]` is the row of one boot.

| Key | Meaning |
|---|---|
| `key, name, first_use, main` | `'F1'`, `'boot F1'`, the first-use wording, True for F1 |
| `folder, path` | `membench-jibin-011`, `results/membench-jibin-011/results/bootF1` |
| `l3, prefetchers, ocm_mapping, script` | typed conditions (`BOOT_COND`) |
| `scripts, commit` | script names of the `start` lines of `log.txt`, the short commit of line 1 |
| `n_cmd, n_core, n_cme, n_failed` | commands (`log.txt` lines that start with `+ `), without and with `--cme`, failed (sum of the `done` lines plus `(exit` lines) |
| `sha_ok, sha_total` | checksums that match, lines of `SHA256SUMS` |
| `cov_rows, cov_min, cov_max` | core timed rows with `perf_cov`, their smallest and largest value |
| `pwrstat_lines, pwrstat_values, l3_from_log` | the `# box clusterpwrstat` lines (`line, when, value, text`), distinct values, `'on'` for 0x70, `'no data'` for 0x0, `None` when the log has no such line (R3) |
| `map_lines, map_first_line, map_last_line, map_cont` | count, first and last line of the `membench_ocm: map` lines of `dmesg.txt`, and `{'0/64': 109}` or `{'64/64': 115}`. All `None` for R3 |
| `n_core_csv, done_lines, log_lines` | core CSV files, line numbers of the `done` lines, lines of `log.txt` |

- `D.commands[b]`: `n_cmd, n_core, n_cme, n_core_latency, n_core_bandwidth, n_core_other` (the eight commands of two older programs on E, B, C, D), `n_core_wrapped` (`{'cmn', 'cmn0', 'xp'}` -> count), `n_exit_lines, done` (list of `line, script, failed, text`), `n_failed, first_uptime, last_uptime` (s of chip time), `commands, core` (lists), `log_lines`. A command: `boot, file, line, text, uptime, wrapper, label, program, args, cme, threads, cpus`.
- `D.integrity[b]`: `sha` (dict of `verify_sha256`), `n_core_csv, n_latency_files, n_bandwidth_files, n_cme_csv, latency_timed_rows, bandwidth_timed_rows, timed_rows, lat_best_n, lat_best_ok, bw_best_n, bw_best_ok` (best rows, and how many equal the min or the max), `cov_rows, cov_min, cov_max, cov_none, perf_lines, bw_blocks_with_counters, cmn_rows, cmn_labels, cmn_core_labels, cmn_events` (list), `cmn_multiplexed`.
- `D.dmesg_maps[b]` (`None` for R3): `boot, file, n, first_line, last_line, cont, aligned_64k` (map lines with `va - pa` a multiple of 64 KiB), `all_len_256k, module_line, module_text`.
- `D.platform`: dict of facts of boot F1. Each fact: `boot, file, line, text, value`. Keys: `kernel, cmdline, online_cpus, cpu_part, hugepages_total, hugepages_free, hugepagesize_kb, memtotal_kb, spm_missing, ocm_device, cmn_events` (`sysinfo.txt`), `timer` (value 1000.0 MHz), `sched_clock, nohz, pmu` (with `counters`) (`dmesg.txt`), `log_flags` (`log.txt` line 3, value dict with `spm`), `mesh_map` (`line`, `last_line`). Lists: `caches` (4 rows `boot, file, line, text, level, type, size, size_bytes, shared_cpu_list`, lines 101 to 104), `ocm_iomem` (5 rows `line, text, region, base, bytes`), `cpu3` (rows `line, online, text`). Plain values: `n_cpus` (10), `cache_bytes` (`{'L1': 32768, 'L2': 131072, 'L3': 262144}`), `cntfrq_hz` (per boot, list of distinct header values).
- `D.clock[b]`: `boot, pooled` (sum of cycles over sum of ns), `n_rows, min, min_file, min_line, max, max_file, max_line, median, min_loads` (4096), `n_short_rows, short_median, short_max` (rows under 4,096 loads, kept apart). Boot F1: pooled 2.00025 over 79 rows.
- `D.bracket` (boot F1) and `D.bracket_by_boot[b]`: `boot, n_cmd, min, median, max, max_file, max_line, file, line, n_at_median, per_load_64_est, per_load_320_est, per_load_4096_est` (median / loads, est.).
- `D.mesh`: `grid_x, grid_y, device_counts` (`{'HN-S': 5, 'RN-F': 5, 'SBSX': 10, ...}`), `home_nodes` (5 rows: `region, node, x, y, hns_index, xp, map_has_hns, line, boot, file, base, base_line`), `ports` (5 rows: `cpus, cpu, x, y, node, map_has_port, line, xp, used`. The fifth has `cpu = None`, `used = False`, node 80), `rnf_xy, hns_xy, map_first_line, map_last_line, ports_ok, homes_ok`. `D.mesh_cells`: every device cell `x, y, xp, port, type, index, node, line`.
- `D.steps`: 20 rows `cpu, region, dx, dy, steps, node, port_xy, hn_xy`. `D.steps_mean[cpu]`: `x, y, total`.
- `D.headline`: 6 rows for figure H1: `key` (`l1, l2, l3, home-nodes, ocm, dram-model`), `level, ns, cycles, size, label, kind, boot, file, line, best_line, row`. Use the label of critic C10 for the `l3` bar.

#### Latency (sections 2 and 3)

- `D.lat_sweep`: 24 chain rows of boot F1 (`D.sweep('F1')`). `D.lat_flushed`: the last one (the DRAM-model row). `D.lat_sweep_summary`: `n, n_spread_under_0_7` (21), `spread_over_0_7` (list of `(label, spread)`).
- `D.lat_bands`: 7 rows. `key` (`l1, l1-edge, l2, cluster, mixed, home-nodes, rising`), `lo, hi` (bytes), `label, n, ns` (`(lo, hi)` of the best values), `kinds, rows`, and for `k` in `l1, l2, a2, l1pf, l2pf, l2byl1pf`: `<k>` = `(min, max)` over all timed rows of the band, `<k>_best` = `(min, max)` over the rows at `line`. `unacc_l2` = `(min, max)` over all timed rows. Bands: 4 to 24 KiB, 32 KiB, 48 to 128 KiB, 192 to 384 KiB, 512 KiB to 1 MiB, 1.5 to 3 MiB, 4 to 32 MiB.
- `D.lat_hit`: 7 chain rows of boot E `latency-dram-small-l3.csv` (64 KiB to 512 KiB, all walked many times), plus `<k>_rng` = `(min, max)` over the reps for `l1, l2, l2hit, l3hit, l3acc, a2`, `id_access` (largest `|l3acc - a2 - l3hit|`), `id_l1` (largest `|l1 - l2hit - l3acc|`), `majority_l3`. `D.lat_hit_check`: `id_access_max, id_l1_max, boots` (`{'E','B','C','D'}` -> `n_rows, l3hit_max, l3hit_min, file`).
- `D.l3_est`: 4 rows (192, 256, 384, 512 KiB): `boot, file, line, best_line, size, label, kind, est` (list per rep, ns), `est_lo, est_hi, tL1, tL2, tOUT, l3_share` (`(min, max)` L3 hits per load), `majority_l3, reps`. Formula per rep: `(ns - (1 - l1) x tL1 - l2hit x tL2 - a2 x tOUT) / l3hit`. `D.l3_est_summary`: `lo, hi` (over the rows with `majority_l3`: 256 and 384 KiB), `sizes, tL1, tL1_row, tL2, tL2_row, tOUT, tOUT_row, direct_row` (the 384 KiB hit row), `direct_ns` (`(min, max)` of its reps), `est_192k, est_512k`. Inputs: `tL1` = boot E 4 KiB row, `tOUT` = boot E 2 MiB row, `tL2` = smallest `(ns - (1 - l1) x tL1) / l1` over the reps of the 96 KiB hit row (est.).
- `D.lat_cluster`: dict. `'control'`: 5 chain rows (CPU 2 counted, CPU 2 without counters, CPUs 4, 6, 8) plus `counted, ns, label`. `'chain2m'`: 4 chain rows (CPU 2 from `latency-dram-large.csv`, CPUs 4, 6, 8 from `latency-dram-slc-cpu<c>.csv`) plus `cpu, same_command` (False for CPU 2), `mean_steps_x, mean_steps_y, fit_pred` (boot B's fit at the mean steps), `diff_cpu2` (best minus CPU 2's best), `fit_diff_cpu2, fit_plus_offset` (the grey tick of figure L4), `ratio_cpu2, a2_rng`. `'control_ns'`: `(min, max)` of the four counted controls.
- `D.lat_seq`: 3 chain rows of `latency-dram-seq.csv` in the order E, C, B, plus `conditions` (`'L3 on, prefetchers on'`), `l3, prefetchers, random_ns` (the same boot's 8 MiB row with every line flushed first), `random_file, random_line, random_best_line, random_cycles, ratio` (`random_ns / best`). `D.lat_seq_cmp`: `pf_effect` (B over C, 7.63), `l3_effect` (C over E, 2.78), `b_over_e` (21.17, two conditions differ), `fetches_in_flight_est` (E: random over address order, est.), `d_ns`.
- `D.lat_pfoff`: 18 rows (4 to 128 KiB, 1.5 to 32 MiB, the flushed row): `boot, file, line, best_line, b_boot, b_file, b_line, b_best_line, size, label, kind, f1_ns, b_ns, ratio` (B over F1), `callout` (True for 32 KiB and 4 MiB), `f1_l1, f1_l1pf, b_l1, b_l1pf, f1_a2, b_a2`. `D.lat_pfoff_summary`: `small, large` (`(min, max)` without the callout rows), `r32k, r4m, flushed, ns32k, ns4m` (dict boot -> ns), `ns32k_pf_on, ns32k_pf_off` (`(min, max)` over the boots of that state), `left_out` (sizes).
- `D.repeat`: 34 rows: `id, group, label, unit, boot, file, line, best_line, e_boot, e_file, e_line, e_best_line, f1, e, ratio` (E over F1), `size`, and the reps of the row itself on each boot: `f1_reps, e_reps, f1_lo, f1_hi, e_lo, e_hi, f1_spread_pct, e_spread_pct, gap` (distance between the two rep ranges, positive when they do not overlap), `disjoint`. Groups in order: `walked many times` (12), `walked once` (11), `every line flushed first` (1), `background control` (2), `OCM, every line, all five` (2), `OCM, one line per page, all five` (2), `plain read` (2), `looped 16 KiB` (2). `D.repeat_groups`: 8 rows `group, n, lo, hi, lo_label, hi_label`. `D.repeat_summary`: `n, small, walked_once, flushed, r768k, r4m, n_within_2pct, all`.
- `D.spread_groups`: 15 rows of boot F1: `group, n, boot, file, line, best_line, min, max` (spread in %), `max_label, reps, kind` (`latency` or `bandwidth`). The source keys name the row with the largest spread.

#### One-core bandwidth (section 4)

- `D.bw_1core`: 18 bandwidth rows of boot F1 `bandwidth-dram-1core.csv` (6 sizes x read, write, copy, in file order), plus `pct_doc` (best over the documented rate in %, `None` for copy). `D.bw_steps`: `read_16k_to_48k_pct, read_48k_to_32m_pct, read_eff_cycles_48k_up` (`(min, max)`), `write_48k_up, write_16k`.
- `D.bw_l1`: 16 bandwidth rows of boot E (looped then single-call, each 4 sizes x read, write), plus `l1_refills_pass` (L1 refills per pass), `diff_ns` (looped minus single-call ns per pass of the same kernel and size: the measured difference between two loops), `pct_doc`. `D.bw_l1_c`: the same for boot C. `D.bw_l1_summary`: `diff_read, diff_write` (`(min, max)`), `best_single_read, best_single_write` (rows), `looped_read_4k` (`{'E': 40.910, 'C': 46.180}`).
- `D.bw_fit`: 7 rows: F1 looped write (16 to 256 KiB), E looped read, E looped write, E single-call read, E single-call write, C looped write, C single-call write. `D.bw_fit_extra`: the two read fits of boot C (both void). Keys: `boot, form, kernel, file, line, best_line, lines, sizes, ns_pass, gbps, intercept_ns, rate` (GB/s = 1 / slope), `rate_bytes_per_cycle, residuals, max_res` (ns), `max_res_pct` (largest residual over the smallest pass time), `limit` (2 % of the smallest pass time, ns), `valid, verdict` (`'valid'` or `'void'`), `smallest_pass_ns, role` (`'quote'` or `'caveat'`). Binding: never print `intercept_ns` or `rate` of a row with `valid == False`.
- `D.bw_var`: 30 bandwidth rows of `bandwidth-read-prefetch.csv` (boots E, C, B x 2 sizes x 5 kernels), plus `ratio_plain` (best over the plain read of the same boot and size), `change_pct, l3, prefetchers`. `D.bw_var_cmp` (plain read, 32 MiB): `pf_effect` (C over B, 3.87), `l3_effect` (E over C, 2.67), `e_over_b, d_vs_b_max_pct, e_vs_f1_pct` (dict size -> %).
- `D.stream_chain`: 2 rows (2 MiB, 32 MiB), boot F1 read: `boot, file, line, best_line, chain_file, chain_line, chain_best_line, size, label, chain_ns, read_gbps, ns_per_line, ratio_est` (chain ns over stream ns per 64 bytes, est.).

#### Multi-core bandwidth (section 5)

- `D.mc_rows`: 21 bandwidth rows of boot F1 (pair 9, one core per cluster 6, all eight cores 6), plus `group` (`'pair'`, `'one core per cluster'`, `'all eight cores'`), `cpus` (from the command in `log.txt`), `log_line, agg` (= `best`), `clusters, cores_per_cluster, one_core` (the one-core rate of the same kernel and size, or `None`), `scaling` (`agg / one_core`), `efficiency` (`scaling / threads`), `per_cluster` (`agg / clusters`). Spread, `thr_min`, `thr_max` are bandwidth-row keys.
- `D.mc_second_core`: 6 rows: `boot, file, line, best_line, kernel, size, label, one_per_cluster, all_eight, gain_pct`.
- `D.mc_writers`: 6 bandwidth rows (order of `WRITER_LISTS`), plus `cpus, cpus_label` (`'2,3,4,5'`), `list, mesh_label, agg, clusters, cores_per_cluster, per_cluster, control` (`'2-4'` or `'2-4-6-8'`), `ratio_control, is_control, nodes` (dict node -> requests received, whole command), `node_counts` (list in region order), `node_sum, shares` (% per node), `mc` (requests sent on to memory, whole command), `mc_net_per_line_pass_est, mesh_line, mesh_node_lines`. `D.mc_writers_summary`: `r2389_over_2345, per_cluster_two_writers` (`'one cluster busy'`, `'two clusters busy'` (tuple), `'four clusters busy'`), `per_cluster_one_writer`.

#### OCM (section 6)

- `D.ocm_all5`: 8 chain rows of boot F1: every line on CPUs 2, 4, 6, 8, then one line per page on the same CPUs. Extra keys: `mean_steps_x, mean_steps_y, mean_steps, fit_pred, above_fit` (best minus boot B's fit at the mean steps), `n_passes, l1_rng, l2_rng, a2_rng, l2pf_rng, unacc_l2_max`. `D.ocm_all5_summary`: `l1, l2, a2` (`(min, max)` over all passes of the four every-line rows), `pf_max, above_fit, every_line, one_line_per_page` (`(min, max)` of the bests), `cpu8_minus_cpu2, fit_cpu8_minus_cpu2, minus_2m_chain` (dict cpu -> ns). `D.ocm_all5_by_boot[b][cpu]`: every-line all-five best for CPUs 2 and 8 on each boot.
- `D.ocm_cells`: 20 chain rows of boot F1 (one line per page, one region; CPU 2 regions 0 to 4, then CPUs 4, 6, 8), plus `region, node, steps_x, steps_y, steps, a2_rng, l2pf_rng, unacc_l2_max, n_passes, every_line_ns` (that CPU's every-line all-five best), `residual`. `median`, `max`, `spread_pct`, `reps` are chain-row keys. `D.ocm_cells_summary`: `best, spread, a2, l2pf` (`(min, max)`, the counter ranges over all 140 passes), `a2_mean, n_passes, unacc_by_cpu, unacc_max, unacc_by_boot` (dict boot -> `D.unacc_ocm`), `unacc_max_bcd` (0.0156), `bracket_per_load_est` (0.61).
- `D.ocm_route[b]` for `b` in `'B', 'D', 'E'`: 20 chain rows of `latency-ocm-region<r>-route-cpu<c>.csv`, plus `region, node, steps_x, steps_y, steps, other` (the other pass), `pf_max` (largest prefetch refill count over the passes), `l1_rng, l2_rng, a2_rng, residual` (from that boot's fit).
- `D.ocm_fit`: dict.
  - `'B'`, `'D'`, `'E'` (route rows) and `'F1'` (the 20 one-line-per-page cells): `a, bx, cy` (ns, ns per X step, ns per Y step), `rms, max_res, pct_of_smallest, limit, valid, n, smallest, largest, res, boot, rows, file`. The route fits also have `l1, l2, a2, l2pf` (`(min, max)` over all passes), `pf_max, spread_lo, spread_hi`. Only `'B'` is valid. Never print `a, bx, cy` of the others.
  - `'B_one_slope'`: `a, per_step, rms, max_res, pct_of_smallest, valid`.
  - `'ports'`: `n_perm` (120), `rank` (1), `best_rms, best_ports, second_rms, second_ports, documented_is_best`.
  - `'flits'`: `{'B', 'E'}` -> `boot, file, n, cluster_ok, node_ok` (20 of 20 each).
  - `'by_steps'`: 7 rows `steps_x, steps_y, n, lo, hi` (boot B).
  - `'mean_steps'`: cpu -> `x, y, pred, f1, diff`.
  - `'all5_vs_cells'`: cpu (2, 8) -> `boot, file, line, best_line, all5, mean_cells` (mean of that CPU's five route cells), `diff`.
- `D.ocm_pagemap`: 4 rows, boot D over boot B: `group` (`'every line, one region'`, `'one line per page, one region'`, `'every line, all five'`, `'one line per page, all five'`), `key` (`route, page, all5-every, all5-page`), `boot, b_boot, file, line, best_line, n, min, max, geo, n_faster_d, mean_diff` (ns), `b, d` (`(min, max)` ns), `cells` (list of `file, b, d, ratio, diff, b_line, d_line, b_best_line, d_best_line, cpu`). `D.ocm_tlb[shape][b]` for shape `'every line'`, `'one line per page'` and `b` in `'B', 'D'`: `boot, file, min, max, mean` (L1 TLB refills per pass, exploratory), `n_passes, l2tlb_max, walk_max`.
- `D.ocm_bw`: 8 bandwidth rows of boot F1: regions 0 to 4, all five (read), all five (write), four cores. Extra keys: `name, region, reps_n, dram_2m` (the DRAM-backed 2 MiB rate of the same kernel), `ratio_dram` (`per_thread / dram_2m`, not like for like), `ratio_sum` (four-core row only: best over the sum of regions 1 to 4). `D.ocm_bw_summary`: `region` (`(min, max)`), `region_apart_pct, read_ratio, write_ratio, four_core_ratio_sum, dram_read_2m, dram_write_2m, counted_2m_read`.

#### Mesh counters (section 7)

- `D.mesh_cmd`: 51 rows, one per core label of boot F1 `cmn-counts.csv`, in file order.

| Key | Meaning |
|---|---|
| `boot, file, line, last_line, node_lines, best_line` | first and last row of the label, `(first, last)` of the five node rows, `None` |
| `label, group, csv, cpu` | group is one of `control`, `control, no counters`, `OCM chain, one region`, `OCM chain, one line per page, all five`, `OCM chain, every line, all five`, `2 MiB chain`, `2 MiB read`, `OCM read, one region`, `OCM read, all five`, `OCM write, all five`, `16 MiB writes`, `OCM read, four cores`. `csv` = the CSV file of the command |
| `nodes, counts, sum` | requests received per home node (dict, list in region order, sum). Whole command |
| `mc, miss` | requests sent on to memory, SLC misses (sums over all nodes, exploratory) |
| `child_ns, helper_ns, multiplexed, counted` | lifetimes, rows with `running_ns != enabled_ns`, False for the uncounted control |
| `dram_backed, ocm` | True for the 10 DRAM-backed commands, True for labels that start with `ocm` |
| `region, own_node, own, others_mean, others_max, ratio, ratio_next, own_highest` | one-region commands only: `ratio` = own node over the mean of the other four |
| `shares, share_spread` | % per node, `(max - min) / mean` in % |
| `control, mc_net, miss_net, sum_net` | the control label of the same CPU (CPU 2 for bandwidth commands), value minus the control |
| `lines, passes_cmd, mc_net_per_line_pass_est` | bandwidth commands only: buffer lines of all threads, passes of the whole command (`1 + reps x (1 + passes)`, from the source), `mc_net / (lines x passes_cmd)`, est. |

- `D.mesh_ctrl`: the 5 control rows of `D.mesh_cmd`, plus `lo, hi` (smallest and largest node count, `None` for the uncounted one).
- `D.mesh_share`: 10 rows (the DRAM-backed commands): `boot, file, line, best_line, label, group, shares, share_lo, share_hi, spread, sum, mc, mc_net_per_line_pass_est`.
- `D.mesh_summary`: `n_labels` (66), `n_core_labels` (51), `n_rows` (587), `n_counted_core` (50), `multiplexed, multiplexed_core, ctrl, ctrl_mc, ctrl_miss` (`(min, max)` over the four counted controls), `helper_cost_ns, child_diff_ns, n_one_region` (25), `own_highest` (25), `ratio_lat, ratio_bw, ratio_next_lat, n_ocm` (35), `ocm_mc, ocm_miss, n_dram` (10), `dram_mc, share` (10 commands), `share_bw` (7 bandwidth commands), `mc_est_read, mc_est_writes, four_core` (the row).
- Binding (critic C12): the counts cover the whole command. Do not divide them by timed loads or timed lines.

#### Open items (section 8)

- `D.open_l3`: 14 rows, boot F1 against boot R3: `id, group, label, unit, boot, file, line, best_line, r3_boot, r3_file, r3_line, r3_best_line, f1, r3` (per reader where `threads` > 1), `f1_agg, r3_agg, threads, ratio` (F1 over R3), `lower_is_better`. Ids: `read-49152, read-98304, read-262144, read-2097152, read-33554432, write-32m, chain-32m, four-readers-2097152, four-readers-16777216, eight-readers-2097152, eight-readers-16777216, ocm-read-all5, ocm-read-4core, mesh-read-2m`. `D.open_l3_regions`: 5 rows `region, boot, file, line, best_line, r3_line, f1, r3, ratio`. `D.open_l3_1core`: 18 rows `kernel, size, label, boot, file, line, best_line, r3_line, f1, r3, ratio`. `D.open_l3_summary`: `read` (list of 5 ratios), `write_32m, chain_32m, four_readers, eight_readers, ocm_regions` (`(min, max)`), `ocm_all5, writers, mesh_f1, mesh_r3, mesh_ratio, child_ns_f1, child_ns_r3, r3_columns, commit_f1, commit_r3`.
- `D.open_ec`: 3 rows (`read-2097152`, `read-33554432`, `seq-8m`): `id, label, unit, boot` (`'E'`), `file, line, best_line, c_boot, c_file, c_line, c_best_line, e, c, l3_gain` (E over C for the reads, C over E for the chain), `e_ctr, c_ctr` (dicts: `cyc_line` or `cycles`, `l1, l1pf, l2, l2pf, l2byl1pf, a2`).
- `D.cmd_cmp[(a, b)]` for the boot pairs `(E, C), (D, B), (C, D), (C, B), (E, B), (F1, R3), (F1, E)`: `n_a, n_b` (commands in `log.txt`), `same` (equal command lists, folder names left out), `extra` (1-based positions of the commands of `a` that `b` does not have, when the list of `b` is the list of `a` without them, else `None`), `commit_a, commit_b, same_commit`.
- `D.not_measured`: `states` (4 dicts `l3, prefetchers, label, boots` in the order L3 on and prefetchers on, L3 on and prefetchers off, no data and on, no data and off), `rows` (15 dicts `family, probe, cells` (list of 4: boot keys or `None`), `by_state`), `f2_non_cme_files`.

### Example

```python
import sys; sys.path.insert(0, '/home/jhan/workspace/titan/cache-perf/asimov')
from c1nano_page import data
D = data.load()
r = D.sweep_row('F1', 384 * data.KIB)
text = (f"The 384 KiB chain reads {r['best']:.3f} ns per load "
        f"({r['cycles']:.2f} cycles, spread {r['spread_pct']:.2f} %).")   # cite data.cite(r)
f = D.ocm_fit['B']                      # a 20.752, bx 1.994, cy 0.952, valid True
w = next(x for x in D.bw_fit if (x['boot'], x['form'], x['kernel']) == ('E', 'looped', 'read'))
assert not w['valid']                   # print only w['max_res_pct']
```

### Differences from the fact sheets and from the critic sheet

| # | Sheet | Data layer | Why |
|---|---|---|---|
| 1 | critic section 6: `bw_fit` "5 + 2" | `D.bw_fit` has those 7 rows. The two read fits of boot C are in `D.bw_fit_extra` | C14 needs "read fits are void on both boots" |
| 2 | critic section 6: `clock`, `bracket` as rows | `D.clock[b]` is a dict per boot. `D.bracket` is boot F1, `D.bracket_by_boot[b]` every boot | one row per boot |
| 3 | critic section 6: `lat_cluster` "5 + 4" | `D.lat_cluster['control']` (5) and `D.lat_cluster['chain2m']` (4) | two row forms |
| 4 | critic section 6: `ocm_route` "20 (B) + 20 (D)" | `D.ocm_route` also has `'E'` | S7b needs one sentence on boot E |
| 5 | critic section 6: `spread_groups` "about 10" | 15 groups | every row group of boot F1 |
| 6 | critic S7b: boot E "prefetch refills 0.16 to 0.65 per load" | `D.ocm_fit['E']['l2pf']` = (0.1594, 0.6526) | the range is of the L2 prefetch refills over all 40 passes |
| 7 | ocm_bw_mesh.md: `ns/64B` of the four-core row | `ns_per_64 = 64 / per_thread` (3.187 ns) | per thread, so the four-core row compares with the one-core rows |
| 8 | critic D5 "4.50 to 6.05 times the next node" | `ratio` = own over the mean of the other four. `ratio_next` holds the other form | the page uses `ratio` |

No value of the critic sheet differs from the data layer.

### Notes for section authors

- A value missing here: compute it in the section module from the generic access and report it.
- `kind` and `shape` already use the page wording. `kernel_label` gives the wording of the read variants.
- Boot conditions for a caption: `D.boot[b]['l3']`, `['prefetchers']`, `['ocm_mapping']`, or `D.boot_first_use[b]`.
- Counts of the mesh events and the events `l2hit, l3acc, l3hit, l1tlb` are exploratory (critic C20).
- `est` keys (`l3_est`, `ratio_est`, `mc_net_per_line_pass_est`, `per_load_64_est`, `fetches_in_flight_est`) are estimates. Print "est." next to them.

## Options added for the page-wide review fixes

- `V.line_chart(..., right_room=px)`: keeps `px` free right of the plot, so that the direct labels of the last points do not cover the lines.
- Series option `top=True`: the line of this series is drawn last. Series option `dash='7 4'`: a dash pattern (a plain `True` keeps `6 4`). Series option `legend='text'`: the legend text when it differs from the name in the tip.
- Gap option `center=True` (`gaps=[dict(x, y0, y1, text, center=True)]`): the range bar stands on its own point and its label goes right above it.
- `V.hbar` row option `hollow=True`: white fill with an outline in the colour (the hollow mark of a second boot).
- `V.lanes`: block kind `'est'` (an estimated interval, a dashed line, legend text `est_name`), `crit_name` (legend text of the red slice), lane option `stagger=n` with `row_h` (block i is a thin bar on row i mod n, clipped at the time axis) and lane option `note` (a text above the lane).
- `words.py`: new entries `bridge`, `clock-read cost`, `contiguous hint`, `control row`, `demand read`, `DRAM-backed`, `fit`, `geometric mean`, `L2 prefetch refills`, `L2 refills by the L1 prefetcher`, `line`, `read stream`, `void`, `way`.
