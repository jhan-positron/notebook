# Figure Manifest

Generated: 2026-06-05 on `delphi-3af6`

Generator: `make_figures.py`, copied from `input-2-ai/util/make_figures_csv_reference.py`
and locally adjusted to exclude Test12 rows whose notes contain
`background_finished_during_probe` from `fig9`.

Source data:

- SNC3: `claude-workspace/results/snc3/*.csv`
- SNC-OFF: `claude-workspace/results/snc-off/*.csv`
- AMD reference values: pre-work writeup values embedded in the input-provided
  figure script because no usable AMD raw CSV is present in this artifact set.

Files:

- `fig1_working_set_latency.png`: local pointer-chase working-set curve.
- `fig2_latency_levels.png`: latency levels derived from pointer-chase rows.
- `fig3_dram_bandwidth.png`: single-thread DRAM read bandwidth.
- `fig4_c2c.png`: cache-to-cache round-trip latency.
- `fig5_multithread_l3_bw.png`: peak aggregate L3 read bandwidth.
- `fig6_thread_scaling.png`: L3 and DRAM thread scaling.
- `fig7_loaded_latency.png`: loaded victim latency.
- `fig8_socket_saturation.png`: whole-socket DRAM saturation.
- `fig9_latency_vs_socket_bw.png`: Test12 victim latency during socket
  bandwidth load, using clean numeric Test12 rows only and plotting `none` and
  `1g` victim hugepage modes as separate series.
- `figure_data.csv`: source values used by the figures.
