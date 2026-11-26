# API of the cme_page package

## Short version

- `data.py` parses the raw files of boot F1 and boot F2 once and returns one object `D` with generic row access and named derived tables.
- `viz.py` (imported as `V`) builds charts as SVG strings, and `shell.py` gives the page object `S`, which numbers sections, figures, tables and references and checks the page text.
- `gen_cme_perf.py` in the project folder builds the sections in page order and writes `asimov-cme-perf.html`.

## How the page is built

- `python3 gen_cme_perf.py` (from the project folder) writes `asimov-cme-perf.html`. It prints the size and the counts of figures, tables, references and terms.
- Order of the calls: `refs.install(S, D)` and `words.install(S, D)` first (Part 3), then `sec_setup.short_version(D, V, S)`, then `build(D, V, S)` of `sec_setup`, `sec_glance`, `sec_latency`, `sec_l3`, `sec_bandwidth`, `sec_callcost`, `sec_ocm`, `sec_open`.
- A section module exposes `KEY`, `TITLE` and `build(D, V, S)`. `build` returns the section body without the `h2`. `sec_l3.build` returns its own `h2` too.
- `python3 -m cme_page.data` runs the self-test of the data layer.
- The page has no time stamp. Two builds give the same bytes.

## Part 1: the data layer `data.py`

### Short version

- `from cme_page import data; D = data.load()` parses the raw files of boot F1 and boot F2 once (about 0.06 s) and returns one cached object `D`.
- `D` gives generic row access (`D.lat`, `D.latrow`, `D.bw`, `D.cmn`) and 58 named derived tables (listed in `data.TABLES`).
- `python3 -m cme_page.data` (from the project folder) runs `selftest()`, which asserts 190 values against `critic.md` and prints `selftest OK: 190 checks`.

### Words used here

- Boot F1: `results/membench-jibin-011/results/bootF1/` (prefetchers on). Boot F2: `results/membench-jibin-012/results/bootF2/` (prefetchers off). `D.boot_name[b]` gives the page name of a boot.
- Rep row: one timed measurement (one CSV data row). Best row: the program's own `-best` row.
- Bracket: time between two clock reads in C. Span: time between the two counter reads inside the kernel. Outside-span: bracket minus span.
- `src`: the base name of the file a value comes from. Every row carries `boot` and `src`, so a caption can cite the file.

### Rules that hold for every table

- Best value: the program's `-best` row (latency: lowest bracket ns, bandwidth: highest bracket GB/s).
- Span, cycles and counters of a latency row: the first rep whose bracket ns equals the best row (`best_rep`, `best_mode`).
- Span rate of a bandwidth row: the `span_GBps` of the program's best row (the same rep as the best bracket rate).
- Units: latency in ns per load, counters in events per load, rates in GB/s (GB = 1e9 bytes), sizes in bytes, percentages in percent.
- 1 GB/s equals 1 byte per ns. So time per pass in ns = bytes per pass / GB/s.
- Bandwidth bracket time of a rep = `total_bytes / aggregate_GBps` (the `elapsed_s` column has only 1 us steps). Bandwidth span time of a rep = `span_s` (1 ns steps).
- Bytes per cycle = GB/s / `D.cycles_per_ns`. `D.cycles_per_ns` is the median measured ratio rounded to 2 decimals (2.0).
- Spread in percent = (highest - lowest) / lowest over the reps. `spread_ns` = highest - lowest.
- Floats are not rounded. Round when formatting. A difference such as `above_rt` can show 0.010000000000001563.

### Module-level names

| Name | Meaning |
|---|---|
| `load()` | returns `D` (cached with `functools.lru_cache`) |
| `selftest(verbose=False)` | asserts and prints `selftest OK: N checks`. `python3 -m cme_page.data -v` prints each check |
| `TABLES` | dict: name of every derived table -> one line |
| `BOOTS`, `BOOT_NAME`, `RUN`, `BOOTDIR`, `ROOT` | boot keys `('F1','F2')`, page names, run folders, boot folders, project folder |
| `KIB`, `MIB`, `LINE` (64), `REGION_BYTES` (262144), `REGION_LINES` (4096) | constants |
| `REGION_NODE` | `(88, 160, 216, 288, 344)`: OCM region -> home node id. Typed fact from `lib_run.sh` line 39. Checked against the mesh counters at load |
| `DSU1_XY` | `(2, 3)`: crosspoint of CPUs 2 and 3. A hypothesis. Say so on the page |
| `SHORT` | CSV column name -> short key (below) |
| `fmt_size(bytes)` | `'4 KiB'`, `'1.5 MiB'` |
| `linfit(xs, ys)` | `(intercept, slope, residuals)` |
| `pearson(xs, ys)`, `lstsq(A, y)`, `cond_number(A)` | pure Python linear algebra. `lstsq` returns `coef, res, rms, max_res, cond_raw, cond_unit` |
| `parse_latency`, `parse_bandwidth`, `parse_cmn`, `parse_log`, `parse_mesh_map`, `verify_sha256(run_dir)` | the parsers |
| `best_rep(entry)` | the first rep equal to the best row |

Short keys of the counter columns (`SHORT`):

| Short key | CSV column | Event |
|---|---|---|
| `ns`, `span` | `ns_per_load`, `ns_per_load_span` | bracket and span ns per load |
| `cycles`, `cme_cycles` | `cycles_per_load`, `cme_cycles_per_load` | core cycles, CME cycles (0x3246) |
| `inner`, `outer` | `cme_l1d_refill_inner/outer_per_load` | 0x327D, 0x327E |
| `rd`, `hwprf`, `wr` | `cme_l1d_refill_rd/hwprf/wr_per_load` | 0x3280, 0x32B2, 0x3281 |
| `hit`, `miss`, `refill` | `cme_l3d_hit/miss/refill_per_load` | 0x328E, 0x328F, 0x3290 (the two `-l3` files) |
| `l1d`, `l2d`, `l3d_rd`, `l1d_hwprf`, `l2d_hwprf`, `l2d_l1dhwprf` | the core columns | core rows on boot F1 |
| `perf_cov` | `perf_cov` | counter running time / enabled time |

### Generic access

| Call | Returns |
|---|---|
| `D.files[boot]` | `{'latency': [file names], 'bandwidth': [file names]}` that were parsed |
| `D.latblocks(boot, file)` | list of latency blocks, one per command (the control file has two) |
| `D.lat(boot, file, size, block=0)` | one footprint entry. `size=0` returns `{'rt': entry, 'call': entry}` |
| `D.latrow(boot, file, size, block=0)` | the derived "chain row" of that footprint |
| `D.bw(boot, file, kernel=None, size=None)` | list of bandwidth rows. With `kernel` and `size`: the one row or `None` |
| `D.bw_table(group, boot=None, kernel=None)` | DRAM-backed CME bandwidth rows of a file group |
| `D.bw_row(boot, group, kernel, size)` | one DRAM-backed CME bandwidth row |
| `D.cmn(boot, label=None, event=None, node=None)` | rows of `cmn-counts.csv` |
| `D.cmn_nodes(boot, label)` | `{node id: requests received}` |
| `D.log[boot]` | `{'commands': [...], 'notes': [...], 'done': [...]}` from `log.txt` |
| `D.log_lines(boot, file)` | log line numbers of the commands that wrote a CSV file |
| `D.verify_sha(boot)` | `{'ok', 'total', 'bad', 'entries', 'src'}` computed with hashlib |
| `D.chain_row(boot, size, kind=None)`, `D.chain_sweep(boot)`, `D.core_row(size, kind=None)`, `D.l3_row(boot, size)` | row lookups |
| `D.l1_form(boot, form, kernel)`, `D.l1_fit(boot, form, kernel, clock)` | row lookups |
| `D.outside(boot, key)`, `D.mesh_row(boot, label)` | row lookups |

Latency block: `boot, src, path, index, line` (line of the `# latency:` comment), `header` (dict of the `key=value` fields: `cpu, mem, cntfrq_hz, loads, reps, fresh, flush, sparse, seq, cme, events`), `header_text, columns, bracket_overhead_ns, bracket_overhead_line, sizes` (dict size -> entry), `order` (sizes in file order), `rt`, `call` (entries of the round-trip baseline and the cme-call rows, or `None` for a core file), `perf_lines` (count of `# perf:` lines), `raw`.

Footprint entry: `size, lines, backing, segments, sparse, line, reps` (list of rep rows), `best, best_line`.

Rep row: `mem, size, mode, rep, loads, line` plus the short counter keys.

Bandwidth row (one per command and kernel): `boot, src, block, line, header` (dict: `threads, bytes_per_thread, passes, reps, mem, flush_before, flush_after, cme, asm_passes, dsb_st, no_fold, cntfrq_hz`), `backing, mem, kernel_csv, kernel, form, group, size, label, passes, segments, n_reps, log_line`, and:

| Key | Unit | Meaning |
|---|---|---|
| `kernel` | - | `read, write, copy, read64, write64` for `cme-read, cme-write, cme-copy, cme-ldr16, cme-str16`. Core rows keep `read, write, copy, ldr16, str16` |
| `form` | - | `looped`, `single-call`, `looped, no fold`, `looped, DSB ST` (from the header flags) |
| `group` | - | `sweep` (cme-bandwidth-dram-1core.csv), `sweep-single` (-dram-1core-asmpasses), `l1-looped` (-l1-passes), `l1-single` (-l1-asmpasses), `l1-nofold`, `l1-dsb`, `call-cost`, `ocm`, `core` |
| `best`, `best_span` | GB/s | the program's best row: bracket rate and span rate (`None` for core rows) |
| `bytes_per_cycle`, `span_bytes_per_cycle` | B per cycle | rate / `D.cycles_per_ns` |
| `bytes_per_pass` | bytes | `total_bytes / passes` (a copy counts read plus written bytes) |
| `ns_per_pass`, `ns_per_pass_span` | ns | `bytes_per_pass / best`, `bytes_per_pass / best_span` |
| `ns_per_line` | ns | 64 / `best` |
| `segments`, `calls_per_pass` | count | OCM buffers: size / 256 KiB (one kernel call per region). DRAM: 1 |
| `calls_per_rep` | count | 1 for the single-call form, else `passes x segments` |
| `reps` | list | per rep: `rep, total_bytes, elapsed_s, gbps, span_s, span_gbps, bracket_ns, bracket_ns_per_pass, span_ns, span_ns_per_pass, outside_ns, outside_ns_per_pass, outside_ns_per_call` |
| `reps_gbps`, `reps_span_gbps`, `spread_pct`, `spread_span_pct` | GB/s, % | rep values and spread |
| `best_rep`, `best_rep_index`, `best_bracket_ns` | - | the first rep equal to the best row |
| `outside_ns_per_call`, `outside_ns_per_pass` | ns | of the best rep |
| `outside_reps`, `outside_lo`, `outside_hi` | ns per kernel call | over the reps |
| `outside_pass_lo`, `outside_pass_hi` | ns per pass | over the reps |

### Derived tables

#### Platform, commands, integrity (outline section 2)

- `D.platform`: dict. Keys `timer_F1, timer_F2, sched_clock_*, bogomips_*, sme_vl_max_*, sme_vl_min_*, sme_vl_default_*, sve_vl_max_*, sme2_*` (from `dmesg.txt` of each run), `hugepages_total, hugepagesize, cmn_events, mesh_map` (from boot F1 `sysinfo.txt`). Each value: `{boot, src, line, text, value}`. `caches`: list of 4 rows `{boot, src, line, text, level, type, size, size_bytes, shared_cpu_list}` (lines 101 to 104). `ocm_iomem`: list of 5 rows `{line, text, base}`. `mesh_map` also has `last_line`. The BogoMIPS line is kept only so the page can say it is derived from the timer. Do not cite it as evidence of the core clock.
- `D.dmesg_ocm_maps[boot]`: `n, first_line, last_line, all_len_256k, all_single_4k, bases`.
- `D.commands[boot]`: `n_commands, n_cme, n_core, n_cme_latency, n_cme_bandwidth, n_cmn, n_cme_cmn, cme_first_line, cme_last_line, cme_first_uptime, cme_last_uptime` (s of chip time), `done` (list of `{line, script, failed, text}`), `failed` (sum), `cme_done, cpu3` (list of `{line, text}`), `cpu3_offline_line, cpu3_online_line, clusterpwrstat, l3_lines, cme_labels, cme_commands, commands`. A command: `{boot, src, line, text, raw, uptime, wrapper, label, program, args, cme}`. `D.commands['same_cme_commands']`: True when both boots ran the same 70 command lines.
- `D.cmd_lines[boot][(file, block)]`: log line of the command that wrote a CSV block. Matched through `all.txt` (same command order as `log.txt`).
- `D.integrity[boot]`: `sha` (`{ok, total, bad, entries}`), `n_cme_latency_files, n_cme_bandwidth_files, latency_rep_rows, perf_cov_min, perf_cov_max, perf_lines, missing_counter_fields, bandwidth_rep_rows, bandwidth_best_rows, bandwidth_reps_with_span, cmn_rows, cmn_labels, cmn_cme_labels, cmn_multiplexed_rows, cntfrq_hz` (list of distinct values), `cpus`.

#### Round-trip baseline, cme-call, clock

- `D.baseline`: 24 rows, one per CME latency file and boot. `boot, src, mem, events, bracket_overhead_ns, rt_best, rt_span, rt_cycles, rt_cme_cycles, rt_loads, rt_reps, rt_span_reps, rt_cycles_reps, rt_cme_cycles_reps, rt_outside_ns_per_call, rt_counters_zero, call_best, call_span, call_outside` (ns per call, best rep), `call_calls` (64), `call_cycles, call_cme_cycles, call_reps, call_span_reps, call_outside_reps, call_cycles_reps, call_cme_cycles_reps, call_span_minus_rt_span`.
- `D.baseline_summary['F1' | 'F2' | 'all']`: `n_files, rt_best_lo/hi, rt_reps_lo/hi, rt_span_lo/hi, rt_cycles_lo/hi, rt_cme_cycles_lo/hi` (over all reps), `rt_counters_zero, call_best_lo/hi, call_span_n, call_span_mode, call_span_n_mode, call_span_lo/hi, call_outside_lo/hi` (ns per call), `call_outside_64_lo/hi` (ns per 64 calls), `overhead_common, overhead_n_common, overhead_other` (list of `(file, value)`).
- `D.rt_ns` (21.005), `D.rt_span_ns` (21.001): the round-trip baseline, lowest over the 24 files.
- `D.clock['min_loads']`: 8,192, the least number of loads of a rep row that enters the clock ratio (`data.CLOCK_MIN_LOADS`).
- `D.clock[boot]`: `n_rows` (rep rows of 8,192 loads or more in the 12 CME latency files, cme-call rows left out), `core_lo, core_hi, core_median` (`cycles / ns`), `cme_lo, cme_hi, cme_median` (`cme_cycles / span`), `short` (dict `'64 loads' | '320 loads' | 'cme-call'` -> `{n, lo, hi}`: the counting window is wider than the bracket there). `D.clock['cycles_per_ns']`, `['ns_per_cycle']`, `['timer_hz']`.

#### Chain load by footprint (outline sections 3 and 4)

- `D.chain[boot]`: 24 chain rows: 12 from `cme-latency-dram-small.csv`, 11 from `-large.csv`, 1 from `-flushed.csv`. `D.chain_sweep(boot)` leaves the flushed row out.

Chain row keys:

| Key | Unit | Meaning |
|---|---|---|
| `boot, src, block, line` | - | source |
| `size, label, lines, backing, segments, mem` | bytes, -, count | footprint, its label, members of the chain |
| `kind` | - | `walked many times`, `walked once`, `every line flushed first`, `address order` (from `fresh`, `flush`, `seq` of the header) |
| `shape` | - | `one line per 4 KiB page` or `every line` |
| `loads, walks_per_rep` | count | loads of the best rep, loads / lines |
| `best` | ns | the program's best row (bracket) |
| `best_mode, best_rep, best_rep_line` | - | the rep the other columns come from |
| `span, bracket_minus_span` | ns | span of the best rep |
| `best_span` | ns | lowest span over the reps (used for the OCM rows) |
| `rt, rt_span` | ns | round-trip baseline of the same file (best, span of its best rep) |
| `above_rt, span_above_rt, best_span_above_rt` | ns | `best - rt`, `span - rt_span`, `best_span - rt_span` |
| `cycles, cme_cycles, cyc_per_ns` | cycles per load, - | of the best rep |
| `inner, outer, rd, hwprf, wr` (or `hit, miss, refill`, or the core keys) | per load | of the best rep. `counter_keys` names them |
| `<k>_reps, <k>_min, <k>_max, <k>_mean` | per load | each counter over the reps |
| `refills, above_rt_per_refill` | per load, ns | `inner + outer`, `above_rt / refills` |
| `refills_per_line` | list | per rep: `inner x loads / lines` |
| `counter_sum_diff` | list | per rep: `inner + outer - rd - hwprf - wr` |
| `demand_only` | bool | every rep counts 0 prefetch refills |
| `reps` | list | the rep rows |
| `reps_ns, reps_span, n_reps, median_ns, median_span` | ns | rep values |
| `spread_ns, spread_pct, spread_span_pct` | ns, % | rep spread |
| `outside_reps, outside_lo, outside_hi` | ns per call | `(ns - span) x loads` per rep (one kernel call per rep) |
| `bracket_overhead_ns` | ns | the file's empty-bracket value |

- `D.core_chain`: the same row form with the core counters and no span or baseline keys. Rows: 2 control blocks (`control=True`, `latency-control-cpu2.csv`), 12 + 11 + 1 rows of `latency-dram-small/large/flushed.csv`.
- `D.chain_pairs`: 24 rows. `size, label, kind, src, f1, f2, f1_minus_f2, f1_over_f2, f2_over_f1, f1_hwprf, f1_refills, f2_refills, f1_rd, f2_rd, f1_inner, f1_outer, f2_inner, f2_outer, f1_spread_ns, f2_spread_ns, reps_apart, core, core_src, f1_minus_core, f1_over_core, f2_minus_core, f1_above_rt_minus_core, f2_above_rt_minus_core`. The `f2_*_core` keys cross two boots.
- `D.chain_steps` (G10): `steps` (3 rows: `series, boot, from_size, to_size, from_ns, to_ns, step_ns, from_kind, to_kind, from_src, to_src, from_hwprf, to_hwprf, walked_once_8m, flushed_8m, flushed_minus_walked_once`), `kinds_by_size`, `sizes_with_both_sweep_kinds` (empty list), `largest_walked_many`, `smallest_walked_once`.
- `D.refills_per_line` (G5): rows of the walked-many-times footprints of both boots. `boot, src, size, label, lines, loads, walks_per_rep, inner_per_line_reps, rd_per_line_reps, inner, refills, above_rt, above_rt_per_refill, in_l1`.
- `D.refills_per_line_summary`: boot F2, 4 KiB to 64 KiB. `n_rep_rows, per_line_lo/hi, l1_above_rt_lo/hi, l1_ns_per_refill_lo/hi, cluster_ns_per_refill_lo/hi` (96 KiB to 384 KiB).
- `D.bracket_minus_span[boot]`: `all_lo, all_hi` (all rep rows), `best_lo, best_hi` (best reps), ns per load.
- `D.address_order`: one chain row from `results/membench-jibin-010/results/bootE/cme-latency-dram-seq.csv` (no span column in that file). Extra key `conditions`. This is the one permitted earlier-boot row.

#### L3-event rows (outline section 5)

- `D.chain_l3[boot]`: 23 chain rows from the two `-l3` files, plus `miss_minus_refill, hit_plus_miss, hit_share` (`hit / (hit + miss)`, `None` when hit + miss is below 0.5 per load), `plain, plain_src, diff` (`best - plain`), `ratio, plain_inner, plain_outer, plain_reps_ns`.
- `D.l3_reps[boot]`: every rep row. `boot, src, size, label, kind, mode, rep, loads, ns, span, inner, outer, hit, miss, refill, mms` (miss minus refill), `hit_share`.
- `D.l3_repeat[boot]`: `n, n_within_1pct, ratio_lo/hi, diff_lo/hi, worst_pct, worst_size, worst_label, worst_l3, worst_plain, worst_l3_reps, worst_plain_reps, outside_1pct` (list of rows).
- `D.l3_checks[boot]`: `rep_rows, chain_rep_rows, refill_differs_from_outer, max_hit_miss_minus_refills` (per load), `max_hit_miss_minus_refills_counts, hit_plus_miss_lo/hi`.
- `D.l3_fits[name]` (boot F2 rep rows, model `ns = hit x a + mms x b + outer x c`): names `A1, A2, A3, B2, B1, C1, C2, C3, E1, D1`. Keys: `desc, n, cols, intercept_fitted, subtracted, ok, hit, mms, outer, intercept` (ns), `rms, max_res` (ns), `cond_raw, cond_unit` (condition number of the design matrix, raw and with unit-length columns), `res, src`. Binding: these may appear only inside a Hypothesis block. A2 and C1 are the well-conditioned ones.
- `D.l3_line`: `n, intercept, slope, at_hit_1, rms, r, ns_lo/hi, hit_lo/hi, outer_lo/hi, mms_lo/hi` (15 rep rows, 96 KiB to 384 KiB).
- `D.l3_loo`: `n_fits, hit_lo/hi, mms_lo/hi, outer_lo/hi` (C1 with one footprint left out).
- `D.l3_outer_cost`: rows `size, label, src, outer, ns_per_outer_est` (512 KiB to 32 MiB, est.).
- `D.l3_large`: `n, ns_lo/hi, r_outer, r_hit` (512 KiB to 3 MiB rep rows), `above_3m` (rows `size, label, best, hit, outer, mms`).

#### Bandwidth (outline sections 6 and 7)

- `D.bw_rows`: 134 bandwidth rows (67 per boot), DRAM-backed CME files only. Use `D.bw_table(group, boot, kernel)`.
- `D.core_bw`: the 18 rows of `bandwidth-dram-1core.csv` (boot F1). No span keys.
- `D.l1_sizes`: `[4096, 8192, 16384, 24576]`.
- `D.l1_forms`: 12 rows (boot x form x kernel: looped read, looped write, single-call read, single-call write, looped no fold read, looped DSB ST write). `boot, form, kernel, group, src, sizes, passes, ns_bracket, ns_span` (ns per pass, lists over the 4 sizes), `gbps, span_gbps, outside` (ns per call of the best rep), `spread_max, spread_span_max, rows`.
- `D.l1_fits`: 24 rows (each form with `clock` = `bracket` or `span`). `intercept_ns, rate_gbps, rate_bytes_per_cycle, res, max_res_ns, max_res_size` (largest absolute residual and its own size), `smallest_pass_ns, max_res_pct` (largest residual / smallest pass time, the plan rule), `verdict` (`void` when `max_res_pct` is over 2, else `pass`), `max_rel_res_pct, max_rel_res_size, max_rel_res_ns` (largest relative residual, for reference), `ns_per_pass`. Binding: never quote the intercept or the rate of a `void` fit as a result.
- `D.l1_diffs`: 8 rows. `boot, size, label, fold_ns, fold_span_ns` (looped read minus no-fold read, ns per pass), `dsb_ns, dsb_span_ns` (DSB ST write minus looped write).
- `D.looped_vs_single`: 32 rows (boot x read/write x 8 sizes, 4 KiB to 256 KiB). `looped_src, single_src, looped_ns, single_ns, diff_ns, looped_gbps, single_gbps, looped_span_gbps, single_span_gbps`.
- `D.call_cost`: 10 rows. `boot, src, kernel, size, label, passes, bracket_ns, span_ns, outside_ns` (ns per call, best rep), `outside_lo, outside_hi, outside_reps, gbps, span_gbps, reps_bracket_ns, reps_span_ns, best_rep`.
- `D.forms64`: 12 rows. `boot, src, kernel` (`read64`, `write64`), `size, label, passes, gbps, span_gbps, bytes_per_cycle, spread_pct, gbps_256, span_gbps_256, ratio_to_256`.
- `D.core_vs_cme_bw`: 18 rows (boot F1). `kernel, size, label, core_src, cme_src, core, core_bytes_per_cycle, core_spread_pct, cme_looped, cme_looped_span, looped_over_core, looped_span_over_core, cme_single, cme_single_span, single_over_core, single_src` (single-call keys are `None` where no single-call row exists). G3 is the 16 KiB read and write rows.
- `D.bw_f1_vs_f2`: 67 rows. `group, form, kernel, size, label, src, f1, f2, f2_over_f1, f1_span, f2_span, f2_over_f1_span, f1_spread_pct, f2_spread_pct, reps_apart` (every rep of one boot above every rep of the other).
- `D.store_vs_load`: 2 rows. `boot, src, size, read_span_gbps, write_span_gbps, ratio, write_cycles_per_64b, read_cycles_per_64b`.
- `D.limits[boot]` (G2, single-call form, 4 KiB to 48 KiB): `read_gbps_lo/hi, read_bpc_lo/hi, read_vec_per_cycle_lo/hi, read_cycles_per_kib_lo/hi, write_gbps_lo/hi, write_bpc_lo/hi, write_cycles_per_vec_lo/hi`. `D.limits['doc']`: the typed documented limits with their sources.
- `D.outside_span`: 22 rows (11 per boot). `boot, key, label, src, per, n, lo, hi, median` (ns per call). Keys: `cme-call`, `ocm-64`, `ocm-320`, `ocm-20480` (one call alone in its bracket), `looped-l1`, `looped-sweep-small` (16 KiB to 256 KiB), `looped-sweep-large` (1 MiB to 32 MiB), `single-first-read`, `single-later-read`, `single-first-write`, `single-later-write`.
- `D.outside_check[boot]`: `lone_call_ns` (median of `ocm-64`), `calls64_ns` (lowest cme-call outside-span x 64), `later_call_est_ns` (`(calls64 - lone) / 63`, est.), `extra_alone_ns`.
- `D.lines_in_flight` (G4, est.): 6 rows. `boot, size, label, chain_src, read_src, chain_ns, read_gbps, ns_per_line, ratio_est, ratio_above_rt_est`.

#### OCM and the mesh (outline section 8)

- `D.ocm_lat[boot]`: 7 chain rows in the order `region0 .. region4, all5, all5-dense`, plus `name, region, row_label, node, steps, passes_ns, passes_span`. `best_span` is the lowest span over the passes. `demand_only` is True for all 7 rows on boot F2 and for none on boot F1.
- `D.ocm_core`: the 7 core twins (`latency-ocm-*-cpu2.csv`, boot F1), core counters.
- `D.ocm_pairs`: 7 rows. `name, row_label, region, shape, steps, node, f1_src, f2_src, core_src, f1, f1_span, f1_best_span, f2, f2_span, f2_best_span, core, core_median, core_spread_pct, core_demand_only, f2_over_f1, f2_over_f1_span, f2_all_above_f1, f1_span_minus_core, f1_span_over_core, f1_minus_core, f1_over_core, f2_span_minus_core, f2_span_over_core`.
- `D.ocm_stats[boot]` (the five one-region rows, best span): `near_lo/hi, far_lo/hi, near_mean, far_mean, far_minus_near, extra_steps, ns_per_extra_step, near_pass_lo/hi, far_pass_lo/hi, far_all_above_near, mean_of_five, spread_lo/hi, spread_span_lo/hi, demand_only_rows, n_passes`. Boot F1 also has `rd_fit_intercept, rd_fit_slope, rd_fit_r, rd_fit_at_1` (span ns against read refills per load over the 35 passes). "near" = 1 step, "far" = 3 steps from crosspoint (2,3), which is a hypothesis.
- `D.ocm_bw[boot]`: 7 bandwidth rows in the order `region0 .. region4, all5, write`, plus `name, region, row_label, lines, kernel_calls_per_pass, best_bracket_us`. Per critic W5: an all-five pass is 5 kernel calls, and a write rep is 40. `outside_lo/hi` are per kernel call. `outside_pass_lo/hi` are per pass.
- `D.ocm_bw_core`: the 7 core twins (`bandwidth-ocm-*.csv`, boot F1).
- `D.ocm_bw_pairs`: 7 rows. `name, row_label, kernel, region, f1, f1_span, f2, f2_span, core, f1_over_core, f2_over_core, f2_over_f1, f2_all_below_f1, f1_ns_per_line, f2_ns_per_line, core_ns_per_line` and the three `*_src` keys.
- `D.mesh_cells`: 40 device cells of the mesh map. `x, y, xp, port, type, index, line`.
- `D.mesh_layout` (G9): 5 rows. `region, node, x, y, hns_index, xp, base, base_line, steps, map_has_hns, map_line, src, boot`. x = node >> 6, y = (node >> 3) & 7.
- `D.mesh_rnf_steps`: 5 rows, one per cluster port. `x, y, xp, steps` (list to regions 0 to 4), `is_dsu1_hypothesis`.
- `D.mesh_summary`: `grid_x, grid_y, device_counts, dsu1_xy, dsu1_is_hypothesis, rnf_cells_matching_1_1_1_3_3, map_first_line, map_last_line, intended_ok, intended_n, region_nodes_from_counts`.
- `D.mesh_requests[boot]`: 15 rows, one per CME label. `label, nodes` (dict), `counts` (list in region order), `sum, lifetime_ms, mc_reqs_local, cache_miss, program, region, top_node, lowest_node, ocm, line, spread_pct, timed` (timed loads or timed lines of the command). One-region rows add `own_node, own, other_lo, other_hi, other_mean, excess` (own minus the mean of the other four), `excess_per_line` (/ 4,096), `own_over_largest_other, intended_ok, excess_per_timed`. All-five rows add `baseline` (median of `other_mean` over the five one-region commands of the same program), `net, net_per_line, net_per_line_lo/hi, lowest_over_mean_others, net_sum, net_per_timed`. The counts cover the whole command, not only the timed passes.
- `D.mesh_control['F1']`: the idle control `control-cpu2` (`nodes, counts, lo, hi, lifetime_ms, what`). `D.mesh_control['F2']` is `None`: boot F2 has no control row.
- `D.mesh_g7` (G7): `['F1' | 'F2']` -> `sum, lines, per_line, lifetime_ms, node_lo, node_hi, node_spread_pct, mc_reqs_local, cache_miss`. `['f1_over_f2']`.

#### Tables that cross sections (outline sections 3, 7, 9)

- `D.cycle_gap` (G6): 6 rows. `boot, key` (`ocm-64, ocm-320, cme-call`), `label, src, n, calls_per_window, lo, hi, median` (core cycles minus CME cycles per counting window = `(cycles - cme_cycles) x loads`), `lo_ns, hi_ns, median_ns`.
- `D.g1[boot]` (G1): 7 rows with `key` in `l1, cluster, outside-1m, outside-3m, ocm, dram, dram-32m`. `where, conditions, src, n_rows, bracket_lo/hi, span_lo/hi, above_rt_lo/hi, outer_lo/hi, inner_lo/hi, hwprf_lo/hi, demand_only, backing`. A single-row entry has `lo == hi`.
- `D.g1_notes`: `ocm_minus_outside_lo, ocm_minus_outside_hi, dram_minus_ocm` (ns, boot F2).
- `D.repeatability` (G8): `['F1' | 'F2']` -> `rt_files, rt_lo, rt_hi, call_lo, call_hi, sweeps_n, sweeps_within_1pct, sweeps_worst_pct, sweeps_worst_label, read16_sweep, read16_l1, read16_diff_pct, write4_span_l1, write4_span_callcost, write4_span_diff_pct, write4_bracket_l1, write4_bracket_callcost`. `['all']` -> `rt_files, rt_lo, rt_hi, call_lo, call_hi, boots_repeated` (0). Units: `read16_*` are bracket rates in GB/s. `write4_span_*` and `write4_bracket_*` are times in ns per pass of 4 KiB (span time and bracket time), not rates. The page divides 4,096 bytes by them to print a rate.
- `D.quote` (G20): `rt_ns, rt_files, l1_f2, cluster_f2, outside_f2, ocm_near_f2_span, ocm_far_f2_span` (tuples `(lo, hi)`), `ocm_all5_f2_span, dram_f2, l1_read_single_F1, l1_read_single_F2, write_single, read_cluster_f1, read_cluster_f2, read_large_f1, read_32m_f1, read_32m_f2, write_large, ocm_read_F1, ocm_read_F2, ocm_write_F1, ocm_write_F2`.

### Example

```python
import sys; sys.path.insert(0, '/home/jhan/workspace/titan/cache-perf/asimov')
from cme_page import data
D = data.load()
r = D.chain_row('F2', 256 * data.KIB)
text = f"The chain load is {r['best']:.3f} ns at {r['label']} ({r['src']})."
fit = D.l1_fit('F1', 'looped', 'read', 'bracket')      # intercept 186.23 ns, verdict 'pass'
```

### Differences from the fact sheets

Each item was settled from the raw file. The data layer follows the "Right" column.

| # | Fact sheet | Data layer | Right, and why |
|---|---|---|---|
| 1 | ocm.md T5: outside-span time of the OCM read calls, for example 342.0 to 465.8 ns (F1 region 0) and 677.2 to 775.7 ns per pass (F1 all five) | 342.1 to 466.0 ns and 677.7 to 776.1 ns per pass | Data layer. The sheet derived the span time as `total_bytes / span_GBps` (a rate rounded to 3 decimals). The data layer reads `span_s`, which the file prints to 1 ns. Example, F1 `cme-bandwidth-ocm-all5.csv` rep 0: `1310720 / 34.356 - 37375 = 776.1 ns`. The per-kernel-call values of critic W5 (135.5 to 155.2 ns) agree with the data layer |
| 2 | ocm.md section 6: an all-five read pass is "one kernel call" | 5 kernel calls per pass, 40 per write rep (`calls_per_rep`) | Data layer (critic W5, `bandwidth.c` lines 314 to 323) |
| 3 | bandwidth.md table 6: the percent column is residual / value at that point, and "At" names that point | `max_res_pct` = largest absolute residual / smallest pass time, `max_res_size` = the size of that residual. The sheet's form is kept as `max_rel_res_pct` | Data layer (critic items 4 and 5, plan line 271). The pass or void verdict is the same in all 24 fits |
| 4 | bandwidth.md table 9: F1 and F2 2 KiB write call, outside-span 76.13 ns | 76.12 ns (76.123 ns before rounding) | Data layer, by 0.01 ns. The sheet took the span time from the rounded `span_GBps`. The data layer reads `span_s` |
| 5 | latency.md section 2: "bracket minus span is 0.001 to 0.041 ns in all F2 footprint rows" | all rep rows 0.000 to 0.041 ns, best reps 0.001 to 0.041 ns (`D.bracket_minus_span`) | Data layer (critic W6) |
| 6 | open.md A6: `bracket_overhead_ns` is 39.0 in each CME latency file | 39.0 ns in 23 files, 40.0 ns in boot F2 `cme-latency-ocm-region1.csv` | Data layer (critic W4) |
| 7 | open.md A2: a store takes "2.4 times" a load | 2.31 times (F1) and 2.33 times (F2), span rates at 16 KiB (`D.store_vs_load`) | Data layer (critic W2) |
| 8 | platform.md section 2: BogoMIPS as evidence of the 2 GHz clock | `D.clock`: 1.9999 to 2.0019 (F1) and 1.9994 to 2.0016 (F2) cycles per ns over 156 rep rows per boot | Data layer (critic item 1) |

No other difference was found. The values checked against the sheets beyond the self-test: the ten L3 fits with their condition numbers, the straight line and its correlation, the leave-one-out ranges, the 24 fit intercepts and rates, table 5, table 8, table 9, the OCM tables T2 to T7, the mesh tables T6 and T7, and the F2-over-F1 list of bandwidth.md table 4.

### Notes for section authors

- `D.limits['doc']`, `REGION_NODE` and `DSU1_XY` are typed facts or hypotheses, not measurements. Cite their documents with a `[RefN]`. `D.limits['doc']` also holds `read_load_instructions_per_iter` (4), `vectors_per_load` (4) and `llvm_ld4_release_cycles` (2).
- The legend of `line_chart` draws the swatch of a series with `dash=True` as a dashed segment.
- The L3 hit and miss columns are exploratory. `D.l3_fits`, `D.l3_line`, `D.l3_loo` and `D.l3_outer_cost` belong inside a Hypothesis block.
- `steps`, `near` and `far` depend on the hypothesis that CPUs 2 and 3 sit at crosspoint (2,3).
- Mesh counts cover the whole command. `excess_per_timed` and `net_per_timed` are not a property of one load.
- A value missing here: write it in the section module and report it.

## Part 2: `viz.py` and `shell.py`

### Short version

- `viz.py` (imported as `V`) builds charts. Every builder takes plain Python lists and returns one SVG string.
- `shell.py` gives the page object `S`. It numbers sections, figures, tables and references, and `S.render()` checks the page text (the lint) before it returns the HTML.
- A section module only concatenates the strings that `S.*` and `V.*` return.

### Words used here

- Builder: a function of `viz.py` that returns an SVG string.
- Series: one line or one set of points of a chart. It is a dict with `name`, `color`, `points`.
- Series color key: `'f2'` (boot F2, blue `#2a78d6`), `'f1'` (boot F1, orange `#eb6834`), `'core'` (the core on boot F1, aqua `#1baf7a`), `'alt'` (a fourth series, violet `#6250d6`). A hex string is also accepted.
- Tip: the text of the hover tooltip. Every data mark carries it in `data-tip`. A `\n` in a tip starts a new line.
- Lint: the check that `S.render()` runs over the visible text of the page.

### Rules that hold for every builder

- All text must be ASCII. A non-ASCII label raises `ValueError`. Write "us", "x", "-".
- Default width is 1040 px (the content column). Pass `width=` for a narrower chart.
- Every builder returns `<div class="figwrap"><svg class="viz" ...></svg></div>`. The chart shrinks with the page down to `MIN_SCALE` (0.92) of its drawn width. On a narrower screen the chart keeps that width and its `.figwrap` box scrolls sideways, so a 10 px label is never drawn below 9.2 px. Print removes the minimum width.
- Text is drawn in ink colors. Only marks carry a series color.
- Labels do not overlap. A label that finds no free place next to its point moves away and gets a leader line.
- A y axis (line chart) or x axis (dumbbell) that does not start at 0 prints "axis starts at N" on the chart.
- Use the violet fourth series only when unavoidable. Violet and blue are hard to tell apart (see "Palette check"). The builders draw violet points as diamonds for that reason.

### Format helpers

```python
V.ns(21.0051)            # '21.005 ns'      V.ns(v, digits=1)
V.gbps(52.34)            # '52.3 GB/s'
V.ratio(2.142)           # '2.14 x'
V.pct(12.34)             # '12.3 %'  (the value is already in percent)
V.signed(12.3, 1, 'ns')  # '+12.3 ns'
V.size_label(1536*1024)  # '1.5 MiB'   also '64 B', '4 KiB', '2 GiB'
V.num(1234567.891, 1)    # '1,234,567.9'
V.color('f1')            # '#eb6834'
V.tw('some text', 12)    # estimated width in px, for your own layout
V.wrap('a long text', 120, 11)   # list of lines no wider than 120 px
```

`None` gives `'n/a'` in every number helper.

### line_chart

```python
K = 1024
svg = V.line_chart(
    [dict(name='CME, boot F2 (prefetchers off)', color='f2',
          points=[(4*K, 21.0), (64*K, 21.2), (256*K, 32.8)], label='last'),
     dict(name='CME, boot F1 (prefetchers on)', color='f1',
          points=[(4*K, 21.0), (64*K, 21.2), (256*K, 51.1)])],
    x='log2',                       # or 'linear'
    xticks=None,                    # None, [x, ...] or [(x, 'label'), ...]
    xlabel='footprint', ylabel='chain load, ns', yunit='ns',
    hlines=[(21.005, 'round-trip baseline')],        # (y, label)
    vlines=[(64*K, 'CME L1 64 KiB')],                # (x, label): capacity markers
    labels=[(0, 256*K), (1, 256*K, 'custom text')],  # (series index, x[, text])
    gaps=[dict(x=256*K, y0=32.8, y1=51.1, text='+18.3 ns')],
    annotations=[dict(x=64*K, y=21.2, text='line one\nline two')],
    yrange=None,                    # None = from 0, (lo, hi), (lo, None), or 'fit'
    height=380)
```

- Series fields: `name`, `color`, `points` `[(x, y)]`. A `y` of `None` breaks the line. Optional: `size` (marker radius in px, default 4.0: a larger first series shows as a ring where two series coincide), `label` (`'last'`, `'first'`, `'max'`, `'min'`, `'all'` or a list of x values), `tips` (one extra tip line per point), `marker` (`'circle'`, `'square'`, `'triangle'`, `'diamond'`), `markers=False`, `dash=True`.
- `gaps` draws a bracket between two y values at one x and writes the difference beside it. `dx` moves the bracket sideways in px.
- `annotations` finds a free place for the text and draws a leader line. `dx` and `dy` (px from the point) fix the place by hand.
- `xtick_mode`: `'auto'` (thin out, then rotate), `'thin'`, `'rotate'`. Labels change only when they would collide.
- `yfmt`, `xfmt`: functions that format a value in tips and labels. `ytickfmt` formats the y ticks.
- Hover: one band per x value. Its tip lists every series at that x.
- The legend appears for two or more named series.

### small_multiples

```python
svg = V.small_multiples(
    [dict(ylabel='inner read refills per load',
          series=[dict(name='boot F2 (prefetchers off)', color='f2', points=[(4*K, 0.0), (256*K, 1.0)])]),
     dict(ylabel='outer read refills per load', yrange=(0, 1.2), hlines=[(1.0, 'one per load')],
          series=[dict(name='boot F2 (prefetchers off)', color='f2', points=[(4*K, 0.0), (256*K, 0.003)])])],
    x='log2', xlabel='footprint', vlines=[(64*K, 'CME L1 64 KiB')], panel_height=150)
```

- The panels share the x axis and are stacked vertically. Each panel has its own y axis and y label.
- Panel fields: `ylabel`, `series`, and optionally `yunit`, `yrange`, `hlines`, `labels`, `annotations`, `gaps`, `yfmt`, `height`.
- The marker labels are printed on the first panel, the x tick labels on the last panel.

### scatter_fit

```python
svg = V.scatter_fit(
    [dict(name='looped read, boot F2', color='f2',
          points=[(1024, 30.5, '1 KiB'), (4096, 55.0), (24576, 216.0, '24 KiB')],
          fit=(0.00786, 23.0),                  # (slope, intercept) in axis units
          fit_label='fit: 23.0 ns + 7.86 ns per KiB')],
    x='linear', xticks=[(1024, '1 KiB'), (24576, '24 KiB')],
    xlabel='bytes per pass', ylabel='time per pass, ns', yunit='ns', xfmt=V.size_label)
```

- A point is `(x, y)` or `(x, y, label)`. The label is printed beside the point.
- `fit` draws the straight line over the x range of the points. `fit_range=(x0, x1)` gives another range.
- It takes the other arguments of `line_chart` (`hlines`, `vlines`, `annotations`, `yrange`, `xrange`).

### dumbbell

```python
svg = V.dumbbell(
    [dict(header='DRAM-backed rows'),
     dict(label='Inside the cluster (256 KiB)', sub='walked many times', a=32.779, b=51.100),
     dict(label='read, 16 KiB', a=56.1, b=120.1, gap='2.14 x')],
    a_name='boot F2 (prefetchers off)', b_name='boot F1 (prefetchers on)',
    a_color='f2', b_color='f1', unit='ns', xlabel='chain load, ns',
    fmt=lambda v: V.num(v, 3),
    refs=[(21.005, 'round-trip baseline')],     # grey vertical reference lines
    xrange=None)                                # (lo, None) truncates the axis and says so
```

- Each row draws two dots joined by a line. The values are printed beside the dots. The gap text is printed in bold at the end of the row.
- Without `gap` the builder writes `b - a` with a sign and the unit. `gap_fmt=lambda a, b: ...` gives another default.
- `a` or `b` may be `None` (one dot). Two dots closer than 9 px are set apart vertically so that both show.
- `{'header': text}` is a group heading. A long label wraps (`label_w`, default 300 px).

### hbar

```python
svg = V.hbar(
    [dict(label='single-call read', sub='4 to 48 KiB', value=131.6, note='span'),
     dict(label='single-call write', value=53.7)],
    unit='GB/s', fmt=lambda v: V.num(v, 1), xlabel='rate, GB/s',
    refs=[(128.0, 'documented limit 128 GB/s')])

svg = V.hbar(                                   # grouped
    [dict(header='Read'), dict(label='region 0', values=[33.9, 39.8]),
     dict(label='region 4', values=[27.7, None])],
    series=[('boot F2 (prefetchers off)', 'f2'), ('boot F1 (prefetchers on)', 'f1')],
    unit='GB/s', xlabel='rate, GB/s', width=760)
```

- Bars start at 0 always. A negative value raises.
- Row fields: `label`, `value` or `values`, and optionally `sub`, `color`, `note` or `notes` (text after the value), `tips`.
- `None` in `values` prints "n/a" and draws no bar.

### lanes (wall-clock lanes)

```python
svg = V.lanes(
    [dict(name='core', blocks=[(0, 18, 'clock read', 'work'), (18, 20.5, 'call', 'work'),
                               (20.5, 106, 'waits for the CME', 'wait')]),
     dict(name='CME', blocks=[(30, 42, 'streaming entry', 'critical'),
                              (42, 103, '16 vector loads', 'work')])],
    unit='ns',
    spans=[(42, 103, 'span time 61.0 ns'), (20.5, 42, 'outside-span time 21.5 ns', 'critical')])
```

- One lane per actor. The x axis is time, to scale.
- Block kinds: `'work'` (solid), `'wait'` (dashed outline), `'critical'` (red, the serial slice). Write the cost of the critical slice in its label.
- A label that does not fit in its block is printed above the lane with a leader line. A tiny block stays tiny (at least 0.75 px wide).
- `spans` draws dimension lines under the lanes, one row each: `(start, end, text)` or `(start, end, text, 'critical')`.
- A block may be a dict (`start`, `end`, `label`, `kind`, `color`, `tip`).
- State any simplification in the caption (for example "durations to scale, interleaving schematic").

### boxes (box-and-arrow diagram)

```python
svg = V.boxes(
    [dict(id='cme', x=0, y=30, w=160, h=90, title='CME', lines=['C1-SME2'], tag='on disk', kind='accent'),
     dict(id='l1', x=230, y=30, w=150, h=90, title='CME L1', lines=['64 KiB'],
          tag='document not on disk', tag_style='outline')],
    [dict(src='cme', dst='l1', label='load')],
    groups=[dict(x=220, y=4, w=170, h=130, label='cluster')])
```

- Coordinates are px. Lay the boxes out left to right. The height of the SVG follows the lowest box.
- Node fields: `id`, `x`, `y`, `w`, `h`, `title`, and optionally `lines` (wrapped to the box), `tag` (a pill at the bottom), `tag_style` (`'solid'` or `'outline'`), `kind` (`'plain'`, `'accent'`, `'soft'`, `'dashed'`), `tip`. `'accent'` is an ink outline of 1.5 px on a grey fill: no box uses a boot colour. A box grows downwards when its text needs more than `h`.
- Arrow fields: `src`, `dst`, and optionally `label`, `dashed`, `both`, `shift` (px, to separate two arrows between the same boxes), `route='hv'`, `via=[(x, y), ...]`, `label_dy`.
- Boxes side by side or one above the other get a straight arrow. A diagonal pair gets an L-shaped arrow. Use `via` when that arrow would cross a box.

### mesh_map

```python
svg = V.mesh_map(
    6, 6,
    [(1, 3, 'HN-S 0\nregion 0\nid 88', 'hn'), (2, 3, 'DSU 1\n(CME)', 'hyp'), (0, 0, 'DSU 0', 'port')],
    highlights=[(2, 3)],
    steps=[dict(src=(2, 3), dst=(1, 3), label='1 step')])
```

- `cells`: `(x, y, label, kind)`. Kinds: `'hn'` (home node), `'port'` (cluster port), `'mem'` (bridge to memory), `'hyp'` (dashed outline: the position is a hypothesis), `'plain'`.
- `highlights`: crosspoints that get a ring. `highlight_label` is the legend text of the ring (default "highlighted").
- `steps`: a route drawn along the mesh links, X first. `order='yx'` goes Y first. Optional `color`, `label_dx`, `label_dy`, `label_below`, `tip`.
- `y_up=True` puts y = 0 at the bottom. `kinds={'hn': 'home node (HN-S)'}` renames a legend entry.

### legend

```python
svg = V.legend([('boot F2 (prefetchers off)', 'f2'), ('boot F1 (prefetchers on)', 'f1')], width=480)
```

- An item is `(name, color)`, `(name, color, shape)` or `(name, color, shape, line)`. Shapes: the marker names, `'swatch'`, `'dashed'`.
- Every chart with two or more series draws its own legend. Use this builder only for a legend that stands alone.

### shell.py: the page object

```python
from cme_page import shell, viz as V
S = shell.Page('Asimov CME Memory Performance', 'subtitle line (html)')

body  = S.h2('latency', 'Latency by footprint')          # numbered by render: 2, 3, ...
body += S.takeaways(['First point.', ('Second point', ['a nested point'])])
body += S.h3('latency-chart', 'Chain load against footprint')   # 2.1, 2.2, ...
body += S.p('A claim %s.' % S.ref('lat-small', 'File <code>cme-latency-dram-small.csv</code>, lines 5 to 60.'))
body += S.fig(svg, 'Caption with the file name in <code>code</code>.', 'One-line takeaway.')
body += S.table(['Row', 'Bracket', 'Span'],
                ['Boot F2 (prefetchers off)',            # a plain text row is a group heading
                 ['CME L1', V.ns(21.015), V.ns(21.011)]],
                caption='Exact numbers.', note='Best rows.', highlight=[0])
body += S.bullets(['one', 'two', ['nested under two']])
body += S.hyp('The cause is X.', 'A run with Y would confirm or reject it.')
body += S.insufficient('No boot was repeated. A second boot would give the spread.')
body += S.callout('The DRAM level is an emulator memory model.', title='Note')
body += S.cols(left_html, right_html)                    # two parts side by side
S.term('CME', 'the Arm C1-SME2 matrix engine unit')      # returns 'CME'

html = S.render('<p>At most three sentences.</p>', [body])
```

| Method | Returns | Notes |
|---|---|---|
| `S.h2(id, title)`, `S.h3(id, title)` | html | `render` fills in the numbers. A duplicate id raises. |
| `S.p(text)` | html | One paragraph. |
| `S.bullets(items, ordered=False)` | html | An item is a text, `(text, [sub items])`, or a list right after a text. |
| `S.takeaways(items, title='Key points')` | html | The list at the top of a section. |
| `S.fig(svg, caption, takeaway=None, id_=None, note=None)` | html | "Figure N." above, the takeaway line below, then the optional `note` in the small style of a table note. Keep the caption to what the figure shows and how to read it (about three sentences). Files, references and simplifications go in `note`. |
| `S.next_fig()`, `S.next_table()` | int | The number the next figure or table gets. |
| `S.table(headers, rows, caption, note, highlight, align, id_)` | html | Numeric columns are right-aligned. A column whose header starts with "Footprint" is a row label and stays left-aligned. `align='lrrc'` forces it. `highlight` is a list of row indexes (group rows not counted) or a function `(index, row) -> bool`. |
| `S.ref(key, text=None)` | `[RefN]` link | N is given at first use. After `refs.install` the key is mapped to the canonical entry of its file or document (Part 3), so the text of the section is not shown. A key that names two files returns two links. `S.render()` renumbers all links by first use in reading order (Short version, then the sections), because the sections are built before the page is put together. Inside a run of links the numbers are put in rising order. So never type a reference number in text. |
| `S.term(name, definition='')` | the name | After `words.install` the definition of `words.py` is shown (Part 3). Without it the first definition wins. The list is sorted by name. |
| `S.xref(id, text=None, cap=False)` | link | Cross-reference to a heading id. `render` writes the real number: "section 7" or "section 7.3" ("Section" with `cap=True`). With `text` it reads "section 7 (text)". An id that is no heading raises at render. Never type a section number. |
| `S.hyp(text, test)` | html | Block labelled "Hypothesis". `test` is required. |
| `S.insufficient(text)` | html | Block labelled "Insufficient data". |
| `S.callout(text, title='Note')` | html | A plain note block. |
| `S.cols(*parts)` | html | Parts side by side. |
| `S.render(short_version_html, sections, lint_page=True)` | page html | `sections` holds html strings (each begins with `S.h2`) or `(key, title, body)` tuples. |
| `shell.esc(text)` | text | Escapes `<`, `>`, `&`. |

Order of the page: title, Short version, Contents, "1 Words used here", the sections from 2, "References" last.

Build the sections in page order. Figure, table and reference numbers are given at the call, not at render.

#### The lint in S.render

`render` raises `shell.LintError` on these:

- A forbidden word in the visible text: hop, chase (all forms), "register control", "run 3", "run 4", "run 6", "boot A" to "boot E" (capital letter only), sparse, dense, "asm form", previously, "no longer". Whole words, any letter case.
- A non-ASCII character inside an `<svg>` element.
- A `[RefN]` in the text with no entry, or a key passed to `S.ref` that never got a text.
- A link `href="#x"` to an id that is not on the page, an id that is used twice, or an `S.xref` to an id that is no heading.

`render` only warns (on stderr, and in `S.warnings`) on these:

- A semicolon in prose outside `code`, `pre`, table cells and SVG.
- "fresh", "the flushed", "flushed row", "floor", and the history words earlier, now, changed, settled, "was thought", "new in".

Text inside `<code>` and `<pre>` is not checked for words. So put every file name in `<code>`: several file names contain "dense" or "sparse".

`shell.lint(page_html, n_refs)` returns `(errors, warnings)` without raising.

### Palette check

Validator of the dataviz skill, light mode, white surface.

- Three colors (blue, orange, aqua): all checks pass. Worst pair aqua and orange, color-blind distance 9.2 (target 8 or more). Aqua has contrast 2.82 to 1 against white (under 3 to 1), so aqua marks need a visible label or a table. Every chart here has a legend and the page has tables.
- Four colors in the fixed order (blue, orange, aqua, violet), neighbors only: all checks pass.
- Four colors, every pair: FAIL. Violet against blue has color-blind distance 4.5 and normal-vision distance 10.5 (limit 15). Do not put violet and blue lines in one chart unless the lines are labelled directly.

### Test

`scratchpad/cme/scripts/viz_demo.py` builds a page with one of every chart from made-up data and checks that the lint raises. `scratchpad/cme/scripts/viz_shot.sh 5` rebuilds it and takes five screenshots.

## Part 3: one reference list and one glossary (`refs.py`, `words.py`)

### Short version

- Each section module calls `S.ref(key, text)` and `S.term(name, definition)` with its own keys and wording.
- `refs.install(S, D)` maps every section key to one canonical entry per file or document. So the References hold each file once.
- `words.install(S, D)` gives every term one definition. So "Words used here" shows the same wording whichever section names the term first.

### refs.py

- `refs.canonical(D)` returns `{canonical key: entry text}`. The line numbers of result files come from the data layer. The line numbers of source files and documents are typed there, once.
- Canonical keys:
  - `file:<boot>:<name>`: one result file of a boot. The entry is built on demand: path, line count, and the `log.txt` lines of its commands.
  - `file:<boot>:log.txt`, `file:<boot>:cmn-counts.csv`, `file:F1:sysinfo.txt`, `run:<boot>:dmesg.txt`, `run:<boot>:SHA256SUMS`: one entry each, with the cited lines listed.
  - `ocm-lat:<boot>`, `ocm-bw:<boot>`, `ocm-core-lat-F1`, `ocm-core-bw-F1`: the seven OCM files of one kind as one entry.
  - `files:cme-lat`, `files:cme-bw`: the 12 CME latency files and the 14 CME bandwidth files of each boot.
  - `readme:F1`, `readme:F2`: the operator's READMEs.
  - `src:cme_kern.S`, `src:bandwidth.c`, `src:latency.c`, `src:common.h`, `src:cmncount.c`, `src:lib_run.sh`, `src:run_cme.sh`: the benchmark sources.
  - `doc:plan`, `doc:cme-plan`, `doc:project-readme`, `doc:sog`, `doc:llvm`, `doc:trm`: documents.
- `refs.resolve(key)` returns the canonical keys of a section key, or `None` for a key it does not know. `refs.ALIAS` holds the explicit mappings. Four patterns cover the rest: `file:<boot>:<name>[:<lines>]`, `run:<boot>:<name>`, `l3:<boot>:<name>`, `<boot>/<name>`, `csv:<name>` (both boots for a `cme-` file, boot F1 for a core file) and `file:<name>:F1+F2`.
- A section may pass a canonical key with no text: `S.ref('file:F1:cme-bandwidth-dram-1core.csv')`.
- A key that `resolve` does not know stays as the section wrote it. `gen_cme_perf.py` prints a note for each such key. Two keys are kept on purpose: `addr-file` and `addr-readme` (the one row of a third boot).
- In a run of `[RefN]` links, `render` keeps each number once.

### words.py

- `words.WORDS` is the list of `(name, definition)`. A definition is one or more full sentences.
- `words.ALIAS` maps a section name to one or more terms of `WORDS` (for example "prefetchers" to "prefetcher").
- `words.ALWAYS` lists terms that the page text uses and no section registers.
- Only terms that a section registers (or that `ALWAYS` names) are listed on the page.
- A term that is not in `WORDS` is kept with the wording of the section. `gen_cme_perf.py` prints a note for each such term. Add it to `WORDS`.

### Terms and labels that the sections share

- "stamp": one read of the timer register inside a kernel. Use "the two stamps of a span", not "counter reads".
- "CME L1", not "the L1" or "the L1 cache of the CME".
- "rep spread" for the spread over reps or timed passes. Say whether it is in ns or in percent.
- A timed pass of a walked-once chain is one rep.
- Row labels of the outside-span charts: "cme-call rows: 64 calls that follow each other", "looped bandwidth calls, 4 to 24 KiB", "OCM latency pass of 64 loads", "single-call read, reps after the first", "single-call read, first rep".
- The core series is "aqua" in the prose.
