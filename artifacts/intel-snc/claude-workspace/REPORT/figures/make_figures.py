#!/usr/bin/env python3
"""Generate report figures from checked-in result CSVs.

Intel SNC/3 and SNC-OFF values are derived from results/snc3/*.csv and
results/snc-off/*.csv. AMD EPYC 9654 remains a pre-work reference because this
artifact set does not include usable AMD raw CSVs for the plotted values.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
RESULTS = ROOT / "results"
OUT = HERE
FIGURE_DATA = OUT / "figure_data.csv"

C = {"snc3": "#2E86C1", "pre": "#7F8C8D", "amd": "#C0392B"}
L = {
    "snc3": "Intel 6962P SNC/3",
    "pre": "Intel 6962P SNC-OFF",
    "amd": "AMD EPYC 9654",
}
ORDER = ["amd", "pre", "snc3"]
MODE_DIR = {"snc3": "snc3", "pre": "snc-off"}


@dataclass(frozen=True)
class Table:
    path: Path
    rows: list[dict[str, str]]


SOURCE_NOTES: list[tuple[str, str, Path, str, int]] = []
FIG_ROWS: list[dict[str, object]] = []


def to_float(value: str) -> float:
    return float(value.strip())


def to_int(value: str) -> int:
    return int(value.strip())


def read_table(path: Path) -> Table:
    with path.open(newline="") as f:
        rows = list(csv.DictReader(f))
    return Table(path=path, rows=rows)


def has_failed_rows(table: Table) -> bool:
    return any(row and next(iter(row.values()), "") == "FAILED" for row in table.rows)


def positive_column(table: Table, column: str) -> bool:
    vals = [to_float(row[column]) for row in table.rows if row.get(column, "")]
    return bool(vals) and all(v > 0 for v in vals)


def latest_table(mode: str, prefix: str, *, positive: str | None = None) -> Table:
    paths = sorted((RESULTS / MODE_DIR[mode]).glob(f"{prefix}_*.csv"))
    if not paths:
        raise FileNotFoundError(f"no {prefix}_*.csv under {RESULTS / MODE_DIR[mode]}")
    rejected: list[str] = []
    for path in reversed(paths):
        table = read_table(path)
        if has_failed_rows(table):
            rejected.append(f"{path} has FAILED rows")
            continue
        if positive is not None and not positive_column(table, positive):
            rejected.append(f"{path} has non-positive {positive}")
            continue
        return table
    raise RuntimeError(f"no usable {prefix} CSV for {mode}; rejected: {rejected}")


TABLES: dict[tuple[str, str], Table] = {}


def table(mode: str, prefix: str, *, positive: str | None = None) -> Table:
    key = (mode, prefix)
    if key not in TABLES:
        TABLES[key] = latest_table(mode, prefix, positive=positive)
    return TABLES[key]


def optional_table(mode: str, prefix: str) -> Table | None:
    try:
        return table(mode, prefix)
    except FileNotFoundError:
        return None


def maybe_float(value: str | None) -> float | None:
    if value is None:
        return None
    text = value.strip()
    if not text or text.upper() in {"NA", "N/A", "NONE"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def source_label(path: Path) -> str:
    if path.is_absolute():
        try:
            return str(path.relative_to(ROOT))
        except ValueError:
            return str(path)
    return str(path)


def record_source(fig: str, series: str, path: Path, selector: str, count: int) -> None:
    SOURCE_NOTES.append((fig, series, Path(source_label(path)), selector, count))


def add_fig_rows(fig: str, series: str, mode: str, rows: list[dict[str, object]]) -> None:
    for row in rows:
        item = {"figure": fig, "series": series, "mode": mode}
        item.update(row)
        FIG_ROWS.append(item)


def select_rows(table: Table, predicate, *, fig: str, series: str, selector: str) -> list[dict[str, str]]:
    rows = [row for row in table.rows if predicate(row)]
    if not rows:
        raise RuntimeError(f"{table.path}: no rows for {selector}")
    record_source(fig, series, table.path, selector, len(rows))
    return rows


def mean(values: list[float]) -> float:
    if not values:
        raise RuntimeError("mean() of empty list")
    return sum(values) / len(values)


def nearest_point(points: list[tuple[int, float]], size: int) -> float:
    for x, y in points:
        if x == size:
            return y
    raise RuntimeError(f"missing size {size}")


def bars(ax, cats, data, ylabel, title, logy=False, fmt="%.0f", note=None):
    x = np.arange(len(cats))
    w = 0.26
    for i, k in enumerate(ORDER):
        vals = data[k]
        b = ax.bar(
            x + (i - 1) * w,
            vals,
            w,
            label=L[k],
            color=C[k],
            edgecolor="black",
            linewidth=0.4,
        )
        for rect, v in zip(b, vals):
            ax.annotate(
                fmt % v,
                (rect.get_x() + rect.get_width() / 2, v),
                ha="center",
                va="bottom",
                fontsize=7,
                xytext=(0, 1),
                textcoords="offset points",
            )
    ax.set_xticks(x)
    ax.set_xticklabels(cats, fontsize=8)
    ax.set_ylabel(ylabel, fontsize=9)
    ax.set_title(title, fontsize=11, fontweight="bold")
    if logy:
        ax.set_yscale("log")
    ax.legend(fontsize=7.5, framealpha=0.9)
    ax.grid(axis="y", alpha=0.3, linewidth=0.5)
    if note:
        ax.text(0.5, -0.22, note, transform=ax.transAxes, ha="center", fontsize=6.5, color="#555")


def ptr_ws(mode: str) -> list[tuple[int, float]]:
    t = table(mode, "ptr_chase", positive="median_ns")
    rows = select_rows(
        t,
        lambda r: r["phase"] == "T1"
        and r["pattern"] == "read"
        and r["cpu"] == "0"
        and r["mem_node"] == "0",
        fig="fig1/fig2",
        series=f"{mode} local pointer-chase",
        selector='phase=="T1" pattern=="read" cpu==0 mem_node==0',
    )
    points = sorted((to_int(r["size_bytes"]), to_float(r["median_ns"])) for r in rows)
    add_fig_rows(
        "fig1",
        "working_set_latency",
        mode,
        [
            {
                "x": size,
                "x_label": f"{size} bytes",
                "value": value,
                "unit": "ns",
                "source": str(t.path.relative_to(ROOT)),
                "selector": 'phase=="T1" pattern=="read" cpu==0 mem_node==0',
            }
            for size, value in points
        ],
    )
    return points


def ptr_remote_dram(mode: str) -> float:
    t = table(mode, "ptr_chase", positive="median_ns")
    mem_nodes = {"pre": {"1"}, "snc3": {"3", "4", "5"}}[mode]
    rows = select_rows(
        t,
        lambda r: r["phase"] == "T2"
        and r["pattern"] == "read"
        and r["cpu"] == "0"
        and r["mem_node"] in mem_nodes
        and r["size_bytes"] == "4294967296",
        fig="fig2",
        series=f"{mode} remote DRAM latency",
        selector=f'phase=="T2" pattern=="read" cpu==0 mem_node in {sorted(mem_nodes)} size==4GiB',
    )
    return mean([to_float(r["median_ns"]) for r in rows])


def bw_value(mode: str, mem_nodes: set[str]) -> float:
    t = table(mode, "bw_avx512", positive="median_GBps")
    rows = select_rows(
        t,
        lambda r: r["pattern"] == "read" and r["mem_node"] in mem_nodes,
        fig="fig3",
        series=f"{mode} mem_nodes {sorted(mem_nodes)} single-thread read BW",
        selector=f'pattern=="read" mem_node in {sorted(mem_nodes)}',
    )
    return mean([to_float(r["median_GBps"]) for r in rows])


def c2c_groups(mode: str) -> tuple[float, float, float]:
    t = table(mode, "c2c", positive="median_ns_rt")
    rows = t.rows
    vals = [(to_int(r["cpu_b"]), to_float(r["median_ns_rt"])) for r in rows]
    if mode == "pre":
        same_socket = [v for cpu, v in vals if cpu < 72]
        cross = [v for cpu, v in vals if cpu >= 72]
        near = same_far = same_socket
        selector = "cpu_b < 72 for same-socket smear; cpu_b >= 72 for cross-socket"
    else:
        near = [v for cpu, v in vals if cpu < 24]
        same_far = [v for cpu, v in vals if 24 <= cpu < 72]
        cross = [v for cpu, v in vals if cpu >= 72]
        selector = "cpu_b < 24 near die; 24 <= cpu_b < 72 same socket far; cpu_b >= 72 cross-socket"

    if not near or not same_far or not cross:
        raise RuntimeError(f"{t.path}: incomplete c2c groups for {mode}")

    record_source("fig4", f"{mode} c2c", t.path, selector, len(rows))
    return mean(near), mean(same_far), mean(cross)


def thread_rows(mode: str) -> list[dict[str, str]]:
    return table(mode, "thread_scaling", positive="median_GBps").rows


def thread_series(mode: str, regime: str) -> list[tuple[int, float]]:
    rows = thread_rows(mode)
    chosen: dict[int, float] = {}
    if regime == "L3":
        # The script intentionally repeats L3/read as L3p2 for variance. Prefer
        # the repeat at duplicate thread counts because that is what the report used.
        for label in ("L3", "L3p2"):
            for r in rows:
                if r["regime"] == label and r["pattern"] == "read":
                    chosen[to_int(r["nthreads"])] = to_float(r["median_GBps"])
    else:
        for r in rows:
            if r["regime"] == regime and r["pattern"] == "read":
                chosen[to_int(r["nthreads"])] = to_float(r["median_GBps"])
    if not chosen:
        raise RuntimeError(f"no {mode} thread_scaling {regime} read rows")
    t = table(mode, "thread_scaling")
    selector = f'regime=="{regime}" pattern=="read"' if regime != "L3" else 'regime in ["L3","L3p2"] pattern=="read"; prefer L3p2 duplicates'
    record_source("fig5/fig6", f"{mode} {regime} read", t.path, selector, len(chosen))
    points = sorted(chosen.items())
    add_fig_rows(
        "fig6",
        f"{regime}_read",
        mode,
        [
            {
                "x": n,
                "x_label": f"{n} threads",
                "value": value,
                "unit": "GB/s",
                "source": str(t.path.relative_to(ROOT)),
                "selector": selector,
            }
            for n, value in points
        ],
    )
    return points


def loaded_series(mode: str, victim_ws: str) -> list[tuple[int, float]]:
    t = table(mode, "loaded_lat", positive="median_ns")
    rows = select_rows(
        t,
        lambda r: r["victim_ws"] == victim_ws,
        fig="fig7",
        series=f"{mode} {victim_ws}",
        selector=f'victim_ws=="{victim_ws}"',
    )
    points = sorted((to_int(r["bg_threads"]), to_float(r["median_ns"])) for r in rows)
    add_fig_rows(
        "fig7",
        victim_ws,
        mode,
        [
            {
                "x": k,
                "x_label": f"{k} bg threads",
                "value": value,
                "unit": "ns",
                "source": str(t.path.relative_to(ROOT)),
                "selector": f'victim_ws=="{victim_ws}"',
            }
            for k, value in points
        ],
    )
    return points


def socket_series(mode: str) -> list[tuple[int, float]]:
    t = table(mode, "socket_sat", positive="agg_GBps")
    rows = select_rows(
        t,
        lambda r: r["pattern"] == "read",
        fig="fig8",
        series=f"{mode} socket-saturation read",
        selector='pattern=="read"',
    )
    points = sorted((to_int(r["nthreads"]), to_float(r["agg_GBps"])) for r in rows)
    add_fig_rows(
        "fig8",
        "socket_saturation_read",
        mode,
        [
            {
                "x": n,
                "x_label": f"{n} threads",
                "value": value,
                "unit": "GB/s",
                "source": str(t.path.relative_to(ROOT)),
                "selector": 'pattern=="read"',
            }
            for n, value in points
        ],
    )
    return points


def latency_vs_socket_bw_series(
    mode: str,
    victim_role: str,
    bg_pattern: str = "read",
    hugepage: str | None = None,
) -> list[tuple[int, float]]:
    t = optional_table(mode, "latency_vs_socket_bw")
    if t is None:
        return []
    rows = []
    for r in t.rows:
        value = maybe_float(r.get("median_ns"))
        nthreads = maybe_float(r.get("bg_nthreads"))
        if value is None or nthreads is None:
            continue
        if r.get("victim_role") != victim_role:
            continue
        if r.get("bg_pattern", bg_pattern) != bg_pattern:
            continue
        if hugepage is not None and r.get("hugepage") != hugepage:
            continue
        if "background_finished_during_probe" in r.get("notes", ""):
            continue
        rows.append((int(nthreads), value, r))
    if not rows:
        return []
    hp_selector = f' hugepage=="{hugepage}"' if hugepage is not None else ""
    selector = f'bg_pattern=="{bg_pattern}" victim_role=="{victim_role}"{hp_selector} median_ns numeric; exclude background_finished_during_probe'
    series_name = f"{mode} {victim_role}" if hugepage is None else f"{mode} {victim_role} {hugepage}"
    record_source("fig9", series_name, t.path, selector, len(rows))
    points = sorted((n, value) for n, value, _ in rows)
    add_fig_rows(
        "fig9",
        f"latency_vs_socket_bw_{victim_role}" if hugepage is None else f"latency_vs_socket_bw_{victim_role}_{hugepage}",
        mode,
        [
            {
                "x": n,
                "x_label": f"{n} bg threads",
                "value": value,
                "unit": "ns",
                "source": str(t.path.relative_to(ROOT)),
                "selector": selector,
            }
            for n, value in points
        ],
    )
    return points


def xs(points: list[tuple[int, float]]) -> list[int]:
    return [p[0] for p in points]


def ys(points: list[tuple[int, float]]) -> list[float]:
    return [p[1] for p in points]


# AMD reference values from the pre-work writeup. No usable AMD source CSV is
# present in this artifact set, so keep these explicit and label them as such.
ws_amd = [
    (32768, 1.085),
    (65536, 3.803),
    (131072, 3.807),
    (262144, 3.814),
    (524288, 5.06),
    (1048576, 8.622),
    (2097152, 13.002),
    (4194304, 12.789),
    (8388608, 13.978),
    (16777216, 15.758),
    (33554432, 22.392),
    (50331648, 62.087),
    (67108864, 77.631),
    (100663296, 87.703),
    (134217728, 93.393),
    (268435456, 103.121),
    (536870912, 107.806),
    (1073741824, 108.517),
    (4294967296, 109.78),
]
record_source("all", "amd reference", Path("pre-work writeup"), "hard-coded because AMD CSV is absent/empty in artifact set", len(ws_amd))

ws_pre = ptr_ws("pre")
ws_snc3 = ptr_ws("snc3")


# ---- Figure 1: working-set latency curve ----
fig, ax = plt.subplots(figsize=(9, 5.2))
for k, d in [("amd", ws_amd), ("pre", ws_pre), ("snc3", ws_snc3)]:
    ax.plot([p[0] / 1048576 for p in d], ys(d), marker="o", ms=3.5, lw=1.8, color=C[k], label=L[k])
ax.set_xscale("log", base=2)
xticks_mib = [0.03125, 0.125, 0.5, 2, 8, 32, 128, 512, 2048, 4096]
xtick_lab = ["32KB", "128KB", "512KB", "2MB", "8MB", "32MB", "128MB", "512MB", "2GB", "4GB"]
ax.set_xticks(xticks_mib)
ax.set_xticklabels(xtick_lab, fontsize=8)
ax.minorticks_off()
ax.set_xlim(0.025, 5200)
ax.set_xlabel("Working-set size", fontsize=10)
ax.set_ylabel("Single-thread load-use latency (ns)", fontsize=10)
ax.set_title("Memory-hierarchy latency vs working-set size (local node, random pointer chase)", fontsize=11, fontweight="bold")
ax.grid(alpha=0.3, linewidth=0.5)
ax.legend(fontsize=9)
for xv in [0.03125, 1, 32, 2048]:
    ax.axvline(xv, color="#ccc", ls=":", lw=0.7)
ax.annotate(
    "SNC/3 L3 plateau 36 ns to 144 MiB (die quota)",
    (8, nearest_point(ws_snc3, 8388608)),
    (0.3, 20),
    fontsize=7,
    color=C["snc3"],
    arrowprops=dict(arrowstyle="->", color=C["snc3"], lw=0.8),
)
ax.annotate(
    "SNC-OFF 60 ns plateau to ~256 MiB\n(whole 432 MiB socket L3) - CROSSOVER:\nSNC-OFF 62 < SNC/3 101 ns @256 MiB",
    (256, nearest_point(ws_pre, 268435456)),
    (20, 150),
    fontsize=6.8,
    color=C["pre"],
    arrowprops=dict(arrowstyle="->", color=C["pre"], lw=0.8),
)
ax.text(
    0.5,
    -0.13,
    "Intel curves are parsed from results/*/ptr_chase_*.csv. AMD: pre-work reference (raw AMD CSV absent here).",
    transform=ax.transAxes,
    ha="center",
    fontsize=6.5,
    color="#555",
)
fig.tight_layout()
fig.savefig(OUT / "fig1_working_set_latency.png", dpi=150, bbox_inches="tight")
plt.close(fig)


# ---- Figure 2: latency at each hierarchy level ----
cats2 = ["L1d\n(32 KiB)", "L2\n(256 KiB)", "L3 hit", "DRAM\nlocal", "DRAM\nremote"]
d2 = {
    "amd": [1.08, 3.80, 12.8, 109.8, 198.7],
    "pre": [
        nearest_point(ws_pre, 32768),
        nearest_point(ws_pre, 262144),
        nearest_point(ws_pre, 4194304),
        nearest_point(ws_pre, 4294967296),
        ptr_remote_dram("pre"),
    ],
    "snc3": [
        nearest_point(ws_snc3, 32768),
        nearest_point(ws_snc3, 262144),
        nearest_point(ws_snc3, 4194304),
        nearest_point(ws_snc3, 4294967296),
        ptr_remote_dram("snc3"),
    ],
}
for mode, vals in d2.items():
    add_fig_rows(
        "fig2",
        "latency_levels",
        mode,
        [{"x": i, "x_label": cat, "value": val, "unit": "ns", "source": "derived", "selector": "see printed sources"} for i, (cat, val) in enumerate(zip(cats2, vals))],
    )
fig, ax = plt.subplots(figsize=(8.5, 5))
bars(
    ax,
    cats2,
    d2,
    "Latency (ns, log scale)",
    "Latency by hierarchy level - three-way",
    logy=True,
    fmt="%.1f",
    note="Discrete view of fig1. L3 is the SNC differentiator. Remote DRAM: SNC-OFF node 1; SNC/3 mean of cross-socket nodes 3-5.",
)
fig.tight_layout()
fig.savefig(OUT / "fig2_latency_levels.png", dpi=150, bbox_inches="tight")
plt.close(fig)


# ---- Figure 3: single-thread DRAM read bandwidth ----
cats3 = ["DRAM local", "DRAM remote"]
d3 = {
    "amd": [38.46, 30.42],
    "pre": [bw_value("pre", {"0"}), bw_value("pre", {"1"})],
    "snc3": [bw_value("snc3", {"0"}), bw_value("snc3", {"3", "4", "5"})],
}
for mode, vals in d3.items():
    add_fig_rows(
        "fig3",
        "single_thread_bw",
        mode,
        [{"x": i, "x_label": cat, "value": val, "unit": "GB/s", "source": "derived", "selector": "see printed sources"} for i, (cat, val) in enumerate(zip(cats3, vals))],
    )
fig, ax = plt.subplots(figsize=(7, 5))
bars(
    ax,
    cats3,
    d3,
    "Single-thread read BW (GB/s)",
    "Single-thread DRAM read bandwidth - three-way",
    fmt="%.1f",
    note="Intel values parsed from results/*/bw_avx512_*.csv. AMD: pre-work reference.",
)
fig.tight_layout()
fig.savefig(OUT / "fig3_dram_bandwidth.png", dpi=150, bbox_inches="tight")
plt.close(fig)


# ---- Figure 4: core-to-core coherence latency ----
cats4 = ["near\n(same die/CCD)", "same-socket\nfar", "cross-socket"]
pre_near, pre_far, pre_cross = c2c_groups("pre")
snc3_near, snc3_far, snc3_cross = c2c_groups("snc3")
d4 = {
    "amd": [55.6, 365.0, 639.0],
    "pre": [pre_near, pre_far, pre_cross],
    "snc3": [snc3_near, snc3_far, snc3_cross],
}
for mode, vals in d4.items():
    add_fig_rows(
        "fig4",
        "c2c_latency",
        mode,
        [{"x": i, "x_label": cat, "value": val, "unit": "ns_rt", "source": "derived", "selector": "see printed sources"} for i, (cat, val) in enumerate(zip(cats4, vals))],
    )
fig, ax = plt.subplots(figsize=(7.5, 5))
bars(
    ax,
    cats4,
    d4,
    "c2c round-trip latency (ns)",
    "Cache-coherence (c2c) latency - three-way",
    fmt="%.0f",
    note="Intel values parsed from results/*/c2c_*.csv. AMD: pre-work reference.",
)
fig.tight_layout()
fig.savefig(OUT / "fig4_c2c.png", dpi=150, bbox_inches="tight")
plt.close(fig)


# ---- Figure 5: multi-thread aggregate L3 read BW ----
l3_pre = thread_series("pre", "L3")
l3_snc3 = thread_series("snc3", "L3")
pre_peak = max(l3_pre, key=lambda p: p[1])
snc3_peak = max(l3_snc3, key=lambda p: p[1])
fig, ax = plt.subplots(figsize=(7, 5))
labels = [L["amd"], L["pre"], L["snc3"]]
vals = [5200, pre_peak[1], snc3_peak[1]]
thr = ["~96T (writeup)", f"{pre_peak[0]}T peak", f"{snc3_peak[0]}T peak"]
cols = [C["amd"], C["pre"], C["snc3"]]
add_fig_rows(
    "fig5",
    "l3_read_peak",
    "pre",
    [{"x": pre_peak[0], "x_label": "peak threads", "value": pre_peak[1], "unit": "GB/s", "source": str(table("pre", "thread_scaling").path.relative_to(ROOT)), "selector": "max L3/L3p2 read"}],
)
add_fig_rows(
    "fig5",
    "l3_read_peak",
    "snc3",
    [{"x": snc3_peak[0], "x_label": "peak threads", "value": snc3_peak[1], "unit": "GB/s", "source": str(table("snc3", "thread_scaling").path.relative_to(ROOT)), "selector": "max L3/L3p2 read"}],
)
b = ax.bar(labels, vals, color=cols, edgecolor="black", linewidth=0.4, width=0.6)
for rect, v, t in zip(b, vals, thr):
    ax.annotate(f"{v:.0f} GB/s\n{t}", (rect.get_x() + rect.get_width() / 2, v), ha="center", va="bottom", fontsize=8)
ax.set_yscale("log")
ax.set_ylabel("Aggregate L3 read BW (GB/s, log)", fontsize=9)
ax.set_title("Multi-thread aggregate L3 bandwidth - dominant AMD advantage", fontsize=10.5, fontweight="bold")
ax.set_ylim(top=9000)
ax.grid(axis="y", alpha=0.3, linewidth=0.5)
ax.tick_params(axis="x", labelsize=8)
ax.text(
    0.5,
    -0.18,
    "Intel peaks parsed from results/*/thread_scaling_*.csv. AMD from pre-work writeup (raw CSV absent/empty).",
    transform=ax.transAxes,
    ha="center",
    fontsize=6.0,
    color="#555",
)
fig.tight_layout()
fig.savefig(OUT / "fig5_multithread_l3_bw.png", dpi=150, bbox_inches="tight")
plt.close(fig)


# ---- Figure 6: thread-count scaling ----
dram_off = thread_series("pre", "DRAM")
dram_snc3 = thread_series("snc3", "DRAM")
fig, ax = plt.subplots(figsize=(8.8, 5.2))
ax.plot(xs(dram_off), ys(dram_off), marker="^", ms=5, lw=2.2, color=C["pre"], label="SNC-OFF - DRAM 64M/thr")
ax.plot(xs(dram_snc3), ys(dram_snc3), marker="^", ms=5, lw=2.2, color=C["snc3"], label="SNC/3 - DRAM 64M/thr")
ax.plot(xs(l3_pre), ys(l3_pre), marker="o", ms=3.5, lw=1.3, ls="--", color=C["pre"], label="SNC-OFF - L3 4M/thr")
ax.plot(xs(l3_snc3), ys(l3_snc3), marker="o", ms=3.5, lw=1.3, ls="--", color=C["snc3"], label="SNC/3 - L3 4M/thr")
ax.axhline(204, color="#ddd", ls=":", lw=0.9)
ax.text(2, 212, "one die = 4 ch (~204)", fontsize=6.5, color="#999")
ax.set_xlabel("Thread count (cpus 0..N-1 -> mem-node 0, 1 thread/core)", fontsize=9)
ax.set_ylabel("Aggregate read BW (GB/s)", fontsize=9)
ax.set_title("Thread-count scaling (Test 9) - the single-node-bind throughput trap", fontsize=11, fontweight="bold")
ax.grid(alpha=0.3, lw=0.5)
ax.legend(fontsize=7.5, loc="upper left")
ax.annotate(
    "DRAM, single-node bind:\nSNC-OFF -> 596 (node = 12 ch)\nSNC/3 capped 204 (node = 4 ch)\n= 2.9x throughput trap",
    (24, 204),
    (30, 470),
    fontsize=7.2,
    color="#333",
    arrowprops=dict(arrowstyle="->", color="#999", lw=0.8),
)
ax.text(
    0.5,
    -0.14,
    "Parsed from latest clean results/*/thread_scaling_*.csv; failed superseded SNC/3 run is rejected.",
    transform=ax.transAxes,
    ha="center",
    fontsize=6.0,
    color="#555",
)
fig.tight_layout()
fig.savefig(OUT / "fig6_thread_scaling.png", dpi=150, bbox_inches="tight")
plt.close(fig)


# ---- Figure 7: loaded latency ----
dram_s3 = loaded_series("snc3", "DRAM_1G")
dram_off7 = loaded_series("pre", "DRAM_1G")
l3_s3 = loaded_series("snc3", "L3_16M")
l3_off7 = loaded_series("pre", "L3_16M")
fig, ax = plt.subplots(figsize=(8.3, 5))
ax.plot(xs(dram_s3), ys(dram_s3), marker="o", ms=5, lw=2.0, color=C["snc3"], label="SNC/3 DRAM victim (1 GiB)")
ax.plot(xs(dram_off7), ys(dram_off7), marker="o", ms=5, lw=2.0, color=C["pre"], label="SNC-OFF DRAM victim (1 GiB)")
ax.plot(xs(l3_s3), ys(l3_s3), marker="s", ms=4, lw=1.2, ls="--", color=C["snc3"], label="SNC/3 L3 victim (16 MiB)")
ax.plot(xs(l3_off7), ys(l3_off7), marker="s", ms=4, lw=1.2, ls="--", color=C["pre"], label="SNC-OFF L3 victim (16 MiB)")
ax.set_xlabel("Background streaming threads on same node (cpus 1..K)", fontsize=9)
ax.set_ylabel("Victim single-thread latency (ns)", fontsize=9)
ax.set_title("Loaded latency (Test 10) - SNC/3 vs SNC-OFF, victim on cpu 0 -> node 0", fontsize=11, fontweight="bold")
ax.grid(alpha=0.3, lw=0.5)
ax.legend(fontsize=7.5, loc="upper left")
ax.annotate(
    "DRAM victim degrades far LESS under SNC-OFF:\n12-channel node has more headroom",
    (xs(dram_off7)[-1], ys(dram_off7)[-1]),
    (7, 185),
    fontsize=6.8,
    color="#333",
    arrowprops=dict(arrowstyle="->", color=C["pre"], lw=0.8),
)
ax.text(
    0.5,
    -0.14,
    "Parsed from latest clean results/*/loaded_lat_*.csv.",
    transform=ax.transAxes,
    ha="center",
    fontsize=6.0,
    color="#555",
)
fig.tight_layout()
fig.savefig(OUT / "fig7_loaded_latency.png", dpi=150, bbox_inches="tight")
plt.close(fig)


# ---- Figure 8: saturated whole-socket DRAM throughput ----
read_snc3 = socket_series("snc3")
read_off = socket_series("pre")
fig, ax = plt.subplots(figsize=(8.8, 5.2))
ax.axhline(614, color="#aaa", ls="--", lw=1.0, label="12-channel DDR5-6400 theoretical (614)")
ax.plot(xs(read_off), ys(read_off), marker="s", ms=5, lw=2.1, color=C["pre"], label="SNC-OFF read (smooth rise)")
ax.plot(xs(read_snc3), ys(read_snc3), marker="o", ms=5, lw=2.1, color=C["snc3"], label="SNC/3 read (204 plateau, then steps)")
ax.axhline(204, color="#ddd", ls=":", lw=0.9)
ax.text(2, 211, "one die = 4 ch (~204)", fontsize=6.5, color="#999")
ax.set_xlabel("Threads (cores), socket 0 - each streaming LOCAL memory (--local)", fontsize=9)
ax.set_ylabel("Aggregate DRAM read BW (GB/s)", fontsize=9)
ax.set_title("Saturated whole-socket DRAM throughput (Test 11) - SNC/3 vs SNC-OFF", fontsize=11, fontweight="bold")
ax.grid(alpha=0.3, lw=0.5)
ax.legend(fontsize=7.8, loc="lower right")
ax.set_ylim(0, 680)
ax.annotate(
    "SAME ceiling ~600 GB/s (98% of theoretical):\nSNC/3 partitioning is FREE at peak socket BW",
    (64, 600),
    (20, 650),
    fontsize=7,
    color="#333",
    arrowprops=dict(arrowstyle="->", color="#999", lw=0.8),
)
ax.annotate(
    "SNC/3 sits at one-die 204 plateau (12-24T)\nthen steps up; SNC-OFF interleaves from core 1",
    (16, 210),
    (22, 300),
    fontsize=6.6,
    color=C["snc3"],
    arrowprops=dict(arrowstyle="->", color=C["snc3"], lw=0.7),
)
ax.text(
    0.5,
    -0.14,
    "Parsed from results/*/socket_sat_*.csv. Equal endpoint, different path.",
    transform=ax.transAxes,
    ha="center",
    fontsize=6.0,
    color="#555",
)
fig.tight_layout()
fig.savefig(OUT / "fig8_socket_saturation.png", dpi=150, bbox_inches="tight")
plt.close(fig)


# ---- Figure 9: Test 12 latency while Test-11-style socket BW is active ----
test12_series = []
for mode in ("pre", "snc3"):
    for role, hugepage, linestyle, marker in (
        ("saturated_core", "none", "-", "o"),
        ("saturated_core", "1g", "-.", "^"),
        ("remote_unused_core", "none", "--", "s"),
        ("remote_unused_core", "1g", ":", "D"),
    ):
        points = latency_vs_socket_bw_series(mode, role, hugepage=hugepage)
        if points:
            test12_series.append((mode, role, hugepage, linestyle, marker, points))

if test12_series:
    fig, ax = plt.subplots(figsize=(8.8, 5.2))
    for mode, role, hugepage, linestyle, marker, points in test12_series:
        role_label = role.replace("_", " ")
        ax.plot(
            xs(points),
            ys(points),
            marker=marker,
            ms=5,
            lw=2.0,
            ls=linestyle,
            color=C[mode],
            label=f"{L[mode]} - {role_label}, hp={hugepage}",
        )
    ax.set_xlabel("Test-11-style background threads (socket 0, --local)", fontsize=9)
    ax.set_ylabel("Victim DRAM pointer-chase median latency (ns)", fontsize=9)
    ax.set_title("Test 12: latency while whole-socket DRAM bandwidth is active", fontsize=11, fontweight="bold")
    ax.grid(alpha=0.3, lw=0.5)
    ax.legend(fontsize=7.5, loc="upper left")
    ax.text(
        0.5,
        -0.16,
        "Parsed from results/*/latency_vs_socket_bw_*.csv. Rows marked background_finished_during_probe are excluded. "
        "saturated_core includes core scheduling contention; remote_unused_core is closer to memory-system interference.",
        transform=ax.transAxes,
        ha="center",
        fontsize=6.0,
        color="#555",
    )
    fig.tight_layout()
    fig.savefig(OUT / "fig9_latency_vs_socket_bw.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
else:
    print("skipping fig9_latency_vs_socket_bw.png: no results/*/latency_vs_socket_bw_*.csv data found")


def write_figure_data() -> None:
    fields = ["figure", "series", "mode", "x", "x_label", "value", "unit", "source", "selector"]
    with FIGURE_DATA.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(FIG_ROWS)


write_figure_data()

print("sources:")
for fig, series, path, selector, count in SOURCE_NOTES:
    print(f"  {fig}: {series}: {path} [{selector}] rows={count}")

print("wrote:")
for f in sorted(OUT.iterdir()):
    if f.name.endswith(".png") or f.name == "figure_data.csv":
        print(" ", f.name, f.stat().st_size, "bytes")
