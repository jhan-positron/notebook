#!/usr/bin/env python3
"""Generate the inline SVG figures for jeremy-tasks-plan.html (light theme, dataviz palette)."""
import json, os, sys
from datetime import datetime, timedelta

OUT = os.path.dirname(os.path.abspath(__file__))
INK, SEC, MUTED, GRID, BASE, SURF = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
ORD = ["#86b6ef", "#3987e5", "#184f95"]  # ordinal blue 250/400/600
GOOD, WARN, SERIOUS, CRIT = "#0ca30c", "#fab219", "#ec835a", "#d03b3b"
BLUE100, ORANGE_WASH = "#cde2fb", "#fbdccd"
FONT = 'font-family="system-ui,-apple-system,Segoe UI,sans-serif"'

def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def text(x, y, s, size=12, fill=INK, anchor="start", weight="normal", extra=""):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" text-anchor="{anchor}" '
            f'font-weight="{weight}" {FONT} {extra}>{esc(s)}</text>')

def svg(w, h, body, label):
    return (f'<svg viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="{esc(label)}" '
            f'style="max-width:100%;height:auto;display:block">'
            f'<rect x="0" y="0" width="{w}" height="{h}" fill="{SURF}"/>{body}</svg>')

# ------------------------------------------------------------------ Fig C: clock by workload pattern
def fig_clock_patterns():
    MU = "\u00b5"
    rows = [
        (["Idle CPU, no task"], "Jeremy, freq.idle.txt (12 samples)", 12, 0, 0),
        (["Sleep, then spin for the last 100 " + MU + "s", "before each deadline (fake-device pattern)"], "Jeremy, freq.sleep.txt (90 samples, hiccup sleep mode)", 89, 1, 0),
        (["Spin without sleeping"], "Jeremy, freq.spin.txt (90 samples, hiccup spin mode)", 14, 1, 75),
        (["Compute loop"], "Jeremy, freq.hot.txt (12 samples, logits bench)", 1, 0, 11),
        (["3 s pinned spin on CPU 121"], "this check, 23:52 UTC (10 samples, 0.3 s apart)", 0, 1, 9),
    ]
    W, LEFT, RIGHT, TOP = 960, 390, 60, 64
    pitch, bh = 58, 18
    H = TOP + pitch * len(rows) + 36
    plot_w = W - LEFT - RIGHT
    b = []
    b.append(text(LEFT, 22, "Share of frequency samples at each level, by what the CPU was doing", 13, INK, weight="600"))
    lx = LEFT
    for name, col in (("1.6 GHz (floor)", ORD[0]), ("between (ramping)", ORD[1]), ("2.8 GHz (maximum)", ORD[2])):
        b.append(f'<rect x="{lx}" y="36" width="12" height="12" rx="2" fill="{col}"/>')
        b.append(text(lx + 17, 46, name, 12, SEC))
        lx += 17 + len(name) * 6.6 + 18
    for i, (name, src, lo, mid, hi) in enumerate(rows):
        y = TOP + i * pitch
        n = lo + mid + hi
        for li, ln in enumerate(name):
            b.append(text(LEFT - 10, y + 12 + li * 14, ln, 12, INK, anchor="end"))
        b.append(text(LEFT - 10, y + 12 + len(name) * 14, src, 10.5, MUTED, anchor="end"))
        x = LEFT
        for val, col in ((lo, ORD[0]), (mid, ORD[1]), (hi, ORD[2])):
            if val == 0:
                continue
            w = plot_w * val / n
            gap = 2 if x > LEFT else 0
            b.append(f'<rect x="{x + gap:.1f}" y="{y}" width="{max(w - gap, 1):.1f}" height="{bh}" fill="{col}"/>')
            pct = f"{100 * val / n:.0f}%"
            if w >= 44:
                tcol = "#ffffff" if col != ORD[0] else INK
                b.append(text(x + w / 2, y + 13, pct, 11, tcol, anchor="middle", weight="600"))
            x += w
        b.append(text(LEFT + plot_w + 6, y + 13, f"n={n}", 10.5, MUTED))
    b.append(f'<line x1="{LEFT}" y1="{TOP - 6}" x2="{LEFT}" y2="{TOP + pitch * len(rows) - 26}" stroke="{BASE}" stroke-width="1"/>')
    b.append(text(LEFT, H - 22, "Each bar is 100% of that pattern's samples. Governor: schedutil in every case.", 10.5, MUTED))
    b.append(text(LEFT, H - 8, "The sampling interval and the CPU of Jeremy's files are not recorded in the files.", 10.5, MUTED))
    return svg(W, H, "".join(b), "Under schedutil a sleeping-then-spinning thread stays at 1.6 GHz almost always, while a continuously spinning thread reaches 2.8 GHz most of the time.")

# ------------------------------------------------------------------ Fig D: tick interrupts on a busy CPU
def fig_ticks():
    rows = [("CPU 121, idle", 10), ("CPU 121, running a pinned spin", 1261), ("CPU 125, running a pinned spin", 1258)]
    W, LEFT, RIGHT, TOP = 880, 250, 70, 48
    pitch, bh = 40, 18
    H = TOP + pitch * len(rows) + 60
    plot_w = W - LEFT - RIGHT
    vmax = 1400
    sx = lambda v: LEFT + plot_w * v / vmax
    b = [text(LEFT, 22, "Timer interrupts (arch_timer, IRQ 12) received by one CPU in 5 seconds", 13, INK, weight="600")]
    for t in range(0, vmax + 1, 250):
        x = sx(t)
        b.append(f'<line x1="{x:.1f}" y1="{TOP - 8}" x2="{x:.1f}" y2="{TOP + pitch * len(rows) - 14}" stroke="{GRID}" stroke-width="1"/>')
        b.append(text(x, TOP + pitch * len(rows) + 2, str(t), 11, MUTED, anchor="middle"))
    ref = sx(1250)
    b.append(f'<line x1="{ref:.1f}" y1="{TOP - 8}" x2="{ref:.1f}" y2="{TOP + pitch * len(rows) - 14}" stroke="{SEC}" stroke-width="1"/>')
    b.append(text(ref, TOP - 12, "1,250 = HZ 250 × 5 s", 11, SEC, anchor="middle"))
    for i, (name, v) in enumerate(rows):
        y = TOP + i * pitch
        b.append(text(LEFT - 10, y + 13, name, 12, INK, anchor="end"))
        w = max(sx(v) - LEFT, 2)
        b.append(f'<path d="M{LEFT},{y} h{w - 4:.1f} a4,4 0 0 1 4,4 v{bh - 8} a4,4 0 0 1 -4,4 h-{w - 4:.1f} z" fill="{BLUE}"/>')
        b.append(text(LEFT + w + 8, y + 13, f"{v:,}", 12, INK, weight="600"))
    b.append(f'<line x1="{LEFT}" y1="{TOP - 8}" x2="{LEFT}" y2="{TOP + pitch * len(rows) - 14}" stroke="{BASE}" stroke-width="1"/>')
    b.append(text(LEFT, H - 22, "Measured 2026-10-21 23:55 UTC from /proc/interrupts deltas, kernel HZ = 250.", 10.5, MUTED))
    b.append(text(LEFT, H - 8, "A busy CPU takes one tick every 4 ms; nohz_full would remove all but about one tick per second.", 10.5, MUTED))
    return svg(W, H, "".join(b), "A busy CPU receives about 1,260 timer interrupts in 5 seconds (the 250 Hz tick); an idle one about 10.")

# ------------------------------------------------------------------ Fig E: CPU allocation
def fig_cpu_alloc():
    W, H = 960, 300
    LEFT, RIGHT = 40, 40
    bw = W - LEFT - RIGHT
    unit = bw / 128
    y0, bh = 60, 30
    b = [text(LEFT, 22, "Split of the 128 CPUs as built on 22 Oct (one core each, no SMT)", 13, INK, weight="600")]
    b.append(text(LEFT, 40, "widths are proportional to CPU count", 11, MUTED))
    # housekeeping
    b.append(f'<rect x="{LEFT}" y="{y0}" width="{unit * 120 - 1:.1f}" height="{bh}" fill="{BLUE100}"/>')
    b.append(text(LEFT + unit * 60, y0 + 19, "CPUs 0–119 · housekeeping: operating system, device interrupts, worker threads · 120 CPUs", 12, INK, anchor="middle"))
    b.append(f'<rect x="{LEFT + unit * 120 + 1:.1f}" y="{y0}" width="{unit * 8 - 1:.1f}" height="{bh}" fill="{ORANGE_WASH}"/>')
    b.append(text(LEFT + unit * 124, y0 + 19, "120–127", 12, INK, anchor="middle", weight="600"))
    for t in (0, 32, 64, 96, 120, 128):
        x = LEFT + unit * t
        b.append(f'<line x1="{x:.1f}" y1="{y0 + bh}" x2="{x:.1f}" y2="{y0 + bh + 6}" stroke="{BASE}" stroke-width="1"/>')
        b.append(text(x, y0 + bh + 19, str(t), 11, MUTED, anchor="middle"))
    # zoom lines
    zx0, zx1, zy = LEFT, W - RIGHT, 150
    b.append(text(zx0, zy - 10, "Zoom on the 8 reserved CPUs and what reached each of them before the reboot:", 11.5, INK, weight="600"))
    cw = (zx1 - zx0) / 8
    for i in range(8):
        c = 120 + i
        x = zx0 + i * cw
        b.append(f'<rect x="{x + 1:.1f}" y="{zy}" width="{cw - 2:.1f}" height="54" fill="{ORANGE_WASH}"/>')
        b.append(text(x + cw / 2, zy + 18, f"CPU {c}", 12, INK, anchor="middle", weight="600"))
        b.append(text(x + cw / 2, zy + 33, f"nvme0q{119 + i}", 10.5, SEC, anchor="middle"))
        b.append(text(x + cw / 2, zy + 46, f"nvme1q{119 + i}", 10.5, SEC, anchor="middle"))
    # pass thread marker on 127
    x = zx0 + 7 * cw + cw / 2
    b.append(f'<circle cx="{x:.1f}" cy="{zy + 68}" r="5" fill="{ORANGE}" stroke="{SURF}" stroke-width="2"/>')
    b.append(text(x - 10, zy + 72, "pass thread pinned to CPU 127 by Jeremy's churn.py in run churn-r1", 11, INK, anchor="end"))
    b.append(text(zx0, zy + 92, "Each reserved CPU carries one managed NVMe queue interrupt per disk (two disks); such an interrupt fires only for I/O issued from that CPU.", 10.5, MUTED))
    b.append(text(zx0, zy + 107, "Before the reboot none of these CPUs was isolated; they were 100% idle in a 5 s sample. The timer tick and function-call IPIs reached them like any other CPU.", 10.5, MUTED))
    for i in (6, 7):
        x = zx0 + i * cw
        b.append(f'<rect x="{x + 1:.1f}" y="{zy}" width="{cw - 2:.1f}" height="54" fill="none" stroke="{BLUE}" stroke-width="2.5"/>')
    b.append(text(zx0 + 7 * cw, zy - 10, "isolated since 22 Oct 05:43 UTC (D3, variant A)", 11, BLUE, anchor="middle", weight="600"))
    b.append(text(zx0, zy + 122, "As built 22 Oct: isolcpus=domain,managed_irq,126-127 and irqaffinity=0-119. CPU 127: pass thread. CPU 126: the fake-device thread once Jeremy's pin lands,", 10.5, MUTED))
    b.append(text(zx0, zy + 137, "idle until then (aim: before Mon 26 Oct). nohz_full needs another kernel build: deferred, not needed for 5 Nov (Jeremy, 22 Oct), plan step P4.", 10.5, MUTED))
    return svg(W, H + 24, "".join(b), "Proposed CPU split: 0 to 119 housekeeping, 120 to 127 reserved for the SDK's timing-sensitive threads; each reserved CPU today carries one NVMe queue interrupt per disk.")

# ------------------------------------------------------------------ Fig F: kernel paths
def fig_kernel_paths():
    W, H = 1000, 372
    b = []
    def box(x, y, w, h, title, lines, fill=SURF, stroke=BASE, tcol=INK, sw=1):
        b.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')
        if title:
            b.append(text(x + 12, y + 20, title, 12.5, tcol, weight="600"))
        for i, l in enumerate(lines):
            b.append(text(x + 12, y + 38 + i * 15, l, 11, SEC))
    b.append('<defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#52514e"/></marker></defs>')
    box(20, 40, 270, 100, "Running now", ["kernel 7.1.3-arm-agi-20260916", "no NO_HZ_FULL, no RCU_NOCB_CPU", "HZ = 250, PREEMPT, isolcpus supported", "governor schedutil, nothing isolated"])
    box(350, 40, 300, 100, "Friday target: same kernel, one reboot", ["isolcpus=domain,managed_irq,126-127", "irqaffinity=0-119", "cpufreq.default_governor=performance", "result: no balancing onto 126-127, 2.8 GHz requested"], fill="#eaf2fc", stroke=BLUE, sw=1.5)
    b.append(f'<line x1="290" y1="90" x2="348" y2="90" stroke="{SEC}" stroke-width="1.5" marker-end="url(#arr)"/>')
    b.append(text(319, 82, "root +", 10.5, SEC, anchor="middle"))
    b.append(text(319, 106, "reboot", 10.5, SEC, anchor="middle"))
    box(710, 40, 270, 100, "Still missing on Friday", ["no nohz_full: a busy isolated CPU still", "takes the 250 Hz tick (one per 4 ms)", "no rcu_nocbs: RCU callbacks stay local", "the SDK perf lane refuses such a host"], fill="#fdf3ee", stroke=SERIOUS, sw=1.5)
    b.append(f'<line x1="650" y1="90" x2="708" y2="90" stroke="{SEC}" stroke-width="1.5" marker-end="url(#arr)"/>')
    b.append(text(20, 176, "Ways to get nohz_full and rcu_nocbs (each needs a second reboot)", 12.5, INK, weight="600"))
    box(20, 190, 300, 90, "A. Rebuild the vendor kernel", ["source: commit 4dbc8bb88858 from Arm (its builder)", "CONFIG_NO_HZ_FULL=y (brings RCU_NOCB_CPU)", "Secure Boot is off: no signing needed"], fill="#eaf2fc", stroke=BLUE)
    box(350, 190, 300, 90, "B. Ask Arm (the kernel's builder) for a build", ["same kernel tree, NO_HZ_FULL enabled", "install as an extra GRUB entry, keep current", "timing depends on Arm's response"], fill="#eaf2fc", stroke=BLUE)
    box(680, 190, 300, 90, "C. Boot the installed 6.8.0-147-generic", ["has NO_HZ_FULL=y and RCU_NOCB_CPU=y", "lacks the vendor-only GIC A0 interrupt quirk", "no evidence it ever booted on this board"], fill="#fdf0f0", stroke=CRIT)
    b.append(text(20, 298, "\u2714 preferred", 11, "#006300", weight="600"))
    b.append(text(350, 298, "\u2714 acceptable", 11, "#006300", weight="600"))
    b.append(text(680, 298, "\u2716 not recommended", 11, CRIT, weight="600"))
    for x in (170, 500, 830):
        b.append(f'<line x1="{x}" y1="306" x2="{x}" y2="326" stroke="{SEC}" stroke-width="1.5" marker-end="url(#arr)"/>')
    box(20, 330, 960, 30, "", [], fill="#eaf2fc", stroke=BLUE)
    b.append(text(500, 350, "Boot with nohz_full=126-127 isolcpus=domain,managed_irq,126-127 rcu_nocbs=126-127 (same lists). dmesg must show \u201cNO_HZ: Full dynticks CPUs: 126-127\u201d", 11.5, INK, anchor="middle"))
    return svg(W, H, "".join(b), "Friday's hand-off runs on the current kernel with isolcpus and a fixed clock; nohz_full needs one of three kernel paths, of which rebuilding the vendor kernel is preferred and booting the stock 6.8 kernel is not recommended.")

# ------------------------------------------------------------------ Fig G: wall-clock lanes (fake device vs tick)
def fig_lanes():
    PX_PER_MS = 100.0
    span_ms = 10.0
    LEFT, RIGHT, TOP = 250, 30, 44
    W = int(LEFT + span_ms * PX_PER_MS + RIGHT)
    lane_h, pitch = 22, 46
    lanes = ["Fake device thread (null_timing backend)", "Scheduler tick, HZ = 250", "Worst late completion in churn-r1", "Lateness band that voids a record"]
    H = TOP + pitch * len(lanes) + 84
    x = lambda ms: LEFT + ms * PX_PER_MS
    b = [text(LEFT, 22, "Who does what, when: 10 ms of wall-clock time on one of the reserved CPUs (1 ms = 100 px, durations to scale)", 13, INK, weight="600")]
    # time axis
    ay = TOP + pitch * len(lanes) + 8
    b.append(f'<line x1="{x(0)}" y1="{ay}" x2="{x(span_ms)}" y2="{ay}" stroke="{BASE}" stroke-width="1"/>')
    for t in range(0, 11):
        b.append(f'<line x1="{x(t)}" y1="{ay}" x2="{x(t)}" y2="{ay + 5}" stroke="{BASE}" stroke-width="1"/>')
        b.append(text(x(t), ay + 18, f"{t} ms", 10.5, MUTED, anchor="middle"))
    for i, name in enumerate(lanes):
        y = TOP + i * pitch
        b.append(text(LEFT - 10, y + 15, name, 11.5, INK, anchor="end"))
        b.append(f'<line x1="{x(0)}" y1="{y + lane_h + 6}" x2="{x(span_ms)}" y2="{y + lane_h + 6}" stroke="{GRID}" stroke-width="1"/>')
    # lane 1: device thread, period 2 ms, spin 100 us before each retirement
    y = TOP
    period, spin = 2.0, 0.1
    t = 0.0
    while t + period <= span_ms + 1e-9:
        r = t + period
        b.append(f'<rect x="{x(t) + 1:.1f}" y="{y + 4}" width="{(period - spin) * PX_PER_MS - 2:.1f}" height="{lane_h - 8}" fill="none" stroke="{MUTED}" stroke-width="1" stroke-dasharray="4 3"/>')
        over = 0.053  # measured mean wake overshoot: 52.7 us (50 us default timer slack plus wake-up latency)
        b.append(f'<rect x="{x(r - spin):.1f}" y="{y}" width="{over * PX_PER_MS:.1f}" height="{lane_h}" fill="{ORANGE_WASH}"/>')
        b.append(f'<rect x="{x(r - spin + over):.1f}" y="{y}" width="{(spin - over) * PX_PER_MS:.1f}" height="{lane_h}" fill="{ORANGE}"/>')
        t = r
    b.append(text(x(0.9), y + 15, "sleeping (nanosleep), CPU idle", 10.5, SEC, anchor="middle"))
    b.append(text(x(2.05), y - 4, "Requested wake 100 µs before the deadline (light bar). The sleep overshoots by 53 µs, so about 47 µs of spin remain (dark bar).", 10, SEC))
    # lane 2: ticks at 0, 4, 8 ms (phase arbitrary)
    y = TOP + pitch
    for t in (0.7, 4.7, 8.7):
        b.append(f'<line x1="{x(t):.1f}" y1="{y}" x2="{x(t):.1f}" y2="{y + lane_h}" stroke="{CRIT}" stroke-width="1.5"/>')
    b.append(text(x(0.9), y + 15, "tick every 4 ms; its own length was not measured (drawn as a line)", 10.5, SEC))
    # lane 3: late completion 220 us after the retirement at 6 ms
    y = TOP + 2 * pitch
    b.append(f'<rect x="{x(6.0):.1f}" y="{y}" width="{0.22 * PX_PER_MS:.1f}" height="{lane_h}" fill="{CRIT}"/>')
    b.append(text(x(6.3), y + 15, "worst late completion, 220 µs (position schematic)", 10.5, SEC))
    # lane 4: band 2.5 us at 4 ms
    y = TOP + 3 * pitch
    b.append(f'<line x1="{x(4.0):.1f}" y1="{y}" x2="{x(4.0):.1f}" y2="{y + lane_h}" stroke="{INK}" stroke-width="1"/>')
    b.append(text(x(4.15), y + 15, "2.5 µs band = 0.25 px at this scale: a mean lateness above it voids the record (churn-r1: 6.2 µs)", 10.5, SEC))
    b.append(text(LEFT, H - 26, "Period 2 ms chosen inside the 1.2–2.6 ms range noted in hiccup.c. Spin window from null_timing.cpp (kSpinNs = 100,000).", 10.5, MUTED))
    b.append(text(LEFT, H - 12, "Overshoot measured with hiccup on 22 Oct (52.7 µs mean). Band and lateness from the churn-r1 record (the void rule uses the mean).", 10.5, MUTED))
    return svg(W, H, "".join(b), "The fake device thread sleeps and then spins for 100 microseconds before each retirement; its sleep overshoots the requested wake by 53 microseconds; a mean lateness above the 2.5 microsecond band voids the record, and the worst single lateness seen was 220 microseconds.")

# ------------------------------------------------------------------ Fig H: churn-r1 per-CPU clock samples and interrupts
def fig_churn_r1():
    cpus = list(range(120, 128))
    clk = {120: (33, 1, 0), 121: (31, 2, 1), 122: (29, 1, 4), 123: (31, 0, 3), 124: (34, 0, 0), 125: (34, 0, 0), 126: (33, 1, 0), 127: (6, 2, 26)}
    irq = {120: 255378, 121: 277078, 122: 1133890, 123: 885004, 124: 1324691, 125: 222394, 126: 871614, 127: 40859}
    secs = 172.9
    seen = {120: "harness 13", 121: "harness 14", 122: "harness 22", 123: "harness 14, scrub 13", 124: "harness 26, scrub 1", 125: "harness 6", 126: "harness 12, scrub 13", 127: "pass thread 27"}
    W = 1000
    TOP, pitch, bh = 90, 36, 16
    L1, PW1 = 92, 290
    L2, PW2 = 585, 290
    H = TOP + pitch * 8 + 112
    b = [text(20, 22, "Jeremy's run churn-r1 (21 Oct 18:32–18:35 UTC): requested clock and interrupts, per reserved CPU", 13, INK, weight="600")]
    b.append(text(20, 40, "Left: share of the 34 isol.py samples (5 s apart) at each requested clock, and in how many samples a harness thread sat on that CPU.", 10.5, SEC))
    b.append(text(20, 54, "Right: interrupts the CPU took during the 172.9 s job, per second.", 10.5, SEC))
    lx = L1
    for name, col in (("1.6 GHz", ORD[0]), ("between", ORD[1]), ("2.8 GHz", ORD[2])):
        b.append(f'<rect x="{lx}" y="{TOP - 18}" width="12" height="12" rx="2" fill="{col}"/>')
        b.append(text(lx + 17, TOP - 8, name, 11, SEC))
        lx += 17 + len(name) * 6.6 + 16
    vmax = 8000
    sx = lambda v: L2 + PW2 * v / vmax
    for t in range(0, vmax + 1, 2000):
        x = sx(t)
        b.append(f'<line x1="{x:.1f}" y1="{TOP - 6}" x2="{x:.1f}" y2="{TOP + pitch * 8 - 12}" stroke="{GRID}" stroke-width="1"/>')
        b.append(text(x, TOP + pitch * 8 + 2, f"{t:,}", 10.5, MUTED, anchor="middle"))
    b.append(text(L2 + PW2 / 2, TOP + pitch * 8 + 18, "interrupts per second during the job (all sources)", 10.5, MUTED, anchor="middle"))
    for i, c in enumerate(cpus):
        y = TOP + i * pitch
        b.append(text(L1 - 10, y + 12, f"CPU {c}", 12, INK, anchor="end", weight="600"))
        lo, mid, hi = clk[c]
        n = lo + mid + hi
        x = L1
        for val, col in ((lo, ORD[0]), (mid, ORD[1]), (hi, ORD[2])):
            if val == 0:
                continue
            w = PW1 * val / n
            gap = 2 if x > L1 else 0
            b.append(f'<rect x="{x + gap:.1f}" y="{y}" width="{max(w - gap, 1):.1f}" height="{bh}" fill="{col}"/>')
            if w >= 44:
                tcol = "#ffffff" if col != ORD[0] else INK
                b.append(text(x + w / 2, y + 12, f"{val} of {n}", 10.5, tcol, anchor="middle", weight="600"))
            x += w
        b.append(text(L1 + PW1 + 8, y + 12, seen[c], 10.5, SEC))
        v = irq[c] / secs
        w = max(sx(v) - L2, 2)
        col = ORANGE if c == 127 else BLUE
        b.append(f'<path d="M{L2},{y} h{w - 4:.1f} a4,4 0 0 1 4,4 v{bh - 8} a4,4 0 0 1 -4,4 h-{w - 4:.1f} z" fill="{col}"/>')
        b.append(text(L2 + w + 6, y + 12, f"{v:,.0f} per s", 11, INK, weight="600"))
    b.append(f'<line x1="{L1}" y1="{TOP - 6}" x2="{L1}" y2="{TOP + pitch * 8 - 12}" stroke="{BASE}" stroke-width="1"/>')
    b.append(f'<line x1="{L2}" y1="{TOP - 6}" x2="{L2}" y2="{TOP + pitch * 8 - 12}" stroke="{BASE}" stroke-width="1"/>')
    yb = TOP + pitch * 8 + 46
    b.append(text(20, yb, "Takeaway: only the pass core (127) requested 2.8 GHz. The CPUs that hosted the other harness threads stayed at 1.6 GHz and took 1,300 to 7,700 interrupts per second,", 11, INK))
    b.append(text(20, yb + 15, "which are those threads' own timed sleeps (fake-device polling, worker idle loops), not host noise. The pass core took 236 per second: the 250 Hz tick while it was busy.", 11, INK))
    b.append(text(20, yb + 34, "Sources: ~/positron/runs/churn-r1/isol.samples.jsonl (khz = scaling_cur_freq, the requested clock; psr = the CPU each thread was on; 28 samples had harness threads),", 10.5, MUTED))
    b.append(text(20, yb + 48, "phoenix-crb-round4.txt irqs_each_watch (/proc/interrupts difference over the job). The harness has four unnamed threads; one of them is the fake device thread.", 10.5, MUTED))
    return svg(W, H, "".join(b), "During churn-r1 only the pass core requested 2.8 GHz; the CPUs hosting the other harness threads stayed at 1.6 GHz and took 1,300 to 7,700 interrupts per second from the threads' own timed sleeps.")

# ------------------------------------------------------------------ Fig H: lateness budget per logits-row pass
def fig_lateness_budget():
    MU = "\u00b5"
    N, LATE, MEAN, BAND, WINDOW = 37275, 2132, 6.25, 2.5, 26.6
    per_late = MEAN * N / LATE                 # mean lateness of one late pass, from Jeremy's counts
    budget = BAND * N / LATE                   # the most each late pass may be late for the mean to stay at the band
    write16 = WINDOW + per_late                # write time at 1.6 GHz, if the window is 26.6 us on Phoenix too
    write28 = write16 * 1.6 / 2.8              # lower bound at 2.8 GHz: the write scales with the clock
    late28 = write28 - WINDOW
    mean28 = late28 * LATE / N
    fix28, fix16 = write28 / 12, write16 / 12  # the 12x faster write, both clock assumptions
    W, H = 1000, 362
    b = [text(20, 22, f"Where churn-r1's {MEAN} {MU}s mean lateness came from, and how late each logits-row pass may be", 13, INK, weight="600")]
    b.append(text(20, 40, "Left: the passes of the 21 Oct run, by whether the fake device completed them late. Right: lateness of one logits-row pass, measured and estimated.", 10.5, SEC))
    L1, PW1, y1, bh = 20, 330, 78, 22
    wl = PW1 * LATE / N
    b.append(f'<rect x="{L1}" y="{y1}" width="{PW1 - wl - 2:.1f}" height="{bh}" fill="{BLUE100}"/>')
    b.append(f'<rect x="{L1 + PW1 - wl:.1f}" y="{y1}" width="{wl:.1f}" height="{bh}" fill="{ORANGE}"/>')
    b.append(text(L1 + (PW1 - wl) / 2, y1 + 15, f"{N - LATE:,} passes on time", 11, INK, anchor="middle", weight="600"))
    b.append(text(L1 + PW1, y1 - 6, f"{LATE:,} late ({100 * LATE / N:.1f}%)", 11, ORANGE, anchor="end", weight="600"))
    lines = [
        (f"Each late pass wrote a logits row and finished 105 to 111 {MU}s", SEC),
        (f"late at 1.6 GHz (Jeremy, 22 Oct). None of the other {N - LATE:,}", SEC),
        ("passes was late.", SEC),
        (f"Mean over all passes: {LATE:,} x {per_late:.0f} {MU}s / {N:,} = {MEAN} {MU}s.", INK),
        (f"The record says 6.246 {MU}s, so the arithmetic matches.", SEC),
        (f"For the mean to stay at the {BAND} {MU}s band, each late pass may be", INK),
        (f"late by at most {BAND} x {N:,} / {LATE:,} = {budget:.1f} {MU}s, if every", INK),
        ("other pass stays on time.", INK),
    ]
    for i, (s_, col) in enumerate(lines):
        b.append(text(L1, y1 + 48 + i * 15, s_, 10.5, col))
    L2, PW2, TOP2, pitch = 420, 440, 78, 60
    vmax = 120
    sx = lambda v: L2 + PW2 * v / vmax
    for t in range(0, vmax + 1, 20):
        x = sx(t)
        b.append(f'<line x1="{x:.1f}" y1="{TOP2 - 8}" x2="{x:.1f}" y2="{TOP2 + pitch * 3 - 20}" stroke="{GRID}" stroke-width="1"/>')
        b.append(text(x, TOP2 + pitch * 3 - 6, str(t), 10.5, MUTED, anchor="middle"))
    b.append(text(L2 + PW2 / 2, TOP2 + pitch * 3 + 10, f"{MU}s late, per logits-row pass", 10.5, MUTED, anchor="middle"))
    rows = [
        ("21 Oct run, 1.6 GHz, measured", per_late, (105, 111), ORANGE, f"{per_late:.0f} {MU}s (105 to 111)", f"mean {MEAN} {MU}s: void"),
        ("performance governor alone, 2.8 GHz, est.", None, (late28, per_late), BLUE100, f"{late28:.0f} to {per_late:.0f} {MU}s est.", f"mean {mean28:.1f} to {MEAN} {MU}s: still void"),
        ("with the 12x faster write (on main, not on Phoenix yet), est.", 0, None, BLUE, f"0 {MU}s: the write takes {fix28:.0f} to {fix16:.0f} {MU}s est., inside its {WINDOW} {MU}s window", "mean from these passes 0: can count"),
    ]
    for i, (name, v, rng, col, lab, verdict) in enumerate(rows):
        y = TOP2 + i * pitch
        b.append(text(L2, y - 8, name, 11, INK, weight="600"))
        if v is not None and v > 0:
            w = sx(v) - L2
            b.append(f'<path d="M{L2},{y} h{w - 4:.1f} a4,4 0 0 1 4,4 v{bh - 8} a4,4 0 0 1 -4,4 h-{w - 4:.1f} z" fill="{col}"/>')
            b.append(f'<line x1="{sx(rng[0]):.1f}" y1="{y + bh / 2:.1f}" x2="{sx(rng[1]):.1f}" y2="{y + bh / 2:.1f}" stroke="{INK}" stroke-width="1.5"/>')
            for r in rng:
                b.append(f'<line x1="{sx(r):.1f}" y1="{y + 4}" x2="{sx(r):.1f}" y2="{y + bh - 4}" stroke="{INK}" stroke-width="1.5"/>')
            b.append(text(sx(rng[1]) + 8, y + 15, lab, 11, INK, weight="600"))
        elif v is None:
            x0, x1 = sx(rng[0]), sx(rng[1])
            b.append(f'<rect x="{x0:.1f}" y="{y}" width="{x1 - x0:.1f}" height="{bh}" rx="4" fill="{col}" stroke="{BLUE}" stroke-width="1.5" stroke-dasharray="4 3"/>')
            b.append(text(x1 + 8, y + 15, lab, 11, INK, weight="600"))
        else:
            b.append(f'<rect x="{L2}" y="{y}" width="3" height="{bh}" fill="{col}"/>')
            b.append(text(L2 + 10, y + 15, lab, 11, INK, weight="600"))
        b.append(text(L2, y + bh + 13, verdict, 10.5, SEC))
    xb = sx(budget)
    b.append(f'<line x1="{xb:.1f}" y1="{TOP2 - 20}" x2="{xb:.1f}" y2="{TOP2 + pitch * 3 - 20}" stroke="{CRIT}" stroke-width="1.5" stroke-dasharray="5 4"/>')
    b.append(text(xb + 5, TOP2 - 24, f"{budget:.1f} {MU}s: budget per late pass", 10.5, CRIT, weight="600"))
    yb = TOP2 + pitch * 3 + 34
    b.append(text(20, yb, f"Takeaway: the host clock alone cannot bring the mean under {BAND} {MU}s ({mean28:.1f} {MU}s est. at best). The SDK-side write fix brings these passes inside their window.", 11, INK))
    b.append(text(20, yb + 15, "The first run with that fix on Phoenix measures it. Until then: insufficient data.", 11, INK))
    b.append(text(20, yb + 34, f"Sources: Jeremy's reply of 22 Oct (pass counts, 105 to 111 {MU}s, the 26.6 {MU}s window, the 12x speed-up measured on LSF hosts); the churn-r1 record (mean 6.246 {MU}s, band 2.502 {MU}s).", 10.5, MUTED))
    b.append(text(20, yb + 48, f"Estimates assume the window is 26.6 {MU}s on Phoenix too. The 2.8 GHz range: lower bound if the write time scales with the clock, upper bound if it does not scale at all.", 10.5, MUTED))
    return svg(W, H, "".join(b), f"The 6.25 microsecond mean lateness of churn-r1 came from 2,132 of 37,275 passes, each about 109 microseconds late. Each may be at most 43.7 microseconds late for the mean to stay at 2.5. The performance governor alone leaves 51 to 109 microseconds (estimate), still void. The 12 times faster write brings them inside the 26.6 microsecond window (estimate).")

# ------------------------------------------------------------------ Fig B: timeline
def fig_timeline():
    d0 = datetime(2026, 10, 21)
    days = 16  # Oct 21 .. Nov 5 inclusive
    LEFT, RIGHT, TOP = 300, 150, 104
    ppd = 40
    W = LEFT + days * ppd + RIGHT
    rows = [
        ("Decide; message to Jeremy; his two replies", 0.75, 1.75, BLUE, "done 22 Oct: sent, answered the same day"),
        ("Live root changes: governor, timers, netperf", 1.226, 1.233, BLUE, "done 22 Oct 05:26-05:36 UTC (Jibin, jhan)"),
        ("Reboot with isolcpus", 1.238, 1.240, BLUE, "done 22 Oct 05:43 UTC, back by 05:44"),
        ("Host validated; reply and note to the arm users", 1.24, 2.0, BLUE100, "checks passed 05:44 and 17:46 UTC; reply to send today"),
        ("Jeremy: new code built on 0-95, smoke runs", 1.68, 1.70, BLUE, "done 22 Oct 16:19-16:48 UTC (commit fa7f715f)"),
        ("Jeremy: first counted block, RUNNING file", 2.54, 2.67, ORANGE, "Fri 23 Oct 13:00-16:00 UTC, CPUs 0-125, then one churn run"),
        ("Jeremy: device thread pinned to 126, 1 \u00b5s slack", 1.75, 5.0, BLUE100, "aim: on Phoenix before Mon 26 Oct"),
        ("Counted blocks, Mon-Fri 13:00-21:00 UTC", 5.0, 15.0, BLUE100, "Jeremy: one block next week, one or two before 5 Nov"),
        ("Jibin away", 2.0, 8.0, BASE, "about 22 to 29 Oct (dates approximate); contact named in the reply"),
        ("nohz_full kernel (deferred)", 8.0, 15.9, ORANGE_WASH, "not needed for 5 Nov (Jeremy, Q2); needs Arm's GitHub access"),
        ("Demo, Thu 5 Nov", 15.0, 15.9, ORANGE, ""),
    ]
    pitch, bh = 34, 16
    timer_y = TOP + pitch * len(rows) + 14
    H = timer_y + 110
    xd = lambda d: LEFT + d * ppd
    b = [text(20, 22, "Timeline, 21 Oct to 5 Nov 2026, revised 22 Oct after Jeremy's replies", 13, INK, weight="600")]
    b.append(text(20, 40, "Day boundaries are midnight UTC, which is 17:00 PDT (Jibin) and 20:00 EDT (Jeremy) of the previous day.", 11, SEC))
    for i in range(days):
        day = d0 + timedelta(days=i)
        if day.weekday() >= 5:
            b.append(f'<rect x="{xd(i):.1f}" y="{TOP - 20}" width="{ppd}" height="{timer_y - TOP + 40}" fill="#f3f3f0"/>')
    for i in range(days + 1):
        x = xd(i)
        b.append(f'<line x1="{x:.1f}" y1="{TOP - 20}" x2="{x:.1f}" y2="{timer_y + 20}" stroke="{GRID}" stroke-width="1"/>')
        if i < days:
            day = d0 + timedelta(days=i)
            b.append(text(x + ppd / 2, TOP - 6, day.strftime("%a"), 9.5, MUTED, anchor="middle"))
            b.append(text(x + ppd / 2, TOP - 24, day.strftime("%-d"), 10.5, SEC, anchor="middle", weight="600"))
    b.append(text(xd(0), TOP - 42, "October", 11, MUTED))
    b.append(text(xd(11), TOP - 42, "November", 11, MUTED))
    for i, (name, s_, e, col, who) in enumerate(rows):
        y = TOP + i * pitch
        b.append(text(LEFT - 10, y + 12, name, 11.5, INK, anchor="end"))
        b.append(f'<rect x="{xd(s_):.1f}" y="{y}" width="{max((e - s_) * ppd, 4):.1f}" height="{bh}" rx="3" fill="{col}"/>')
        if (e - s_) * ppd >= 200:
            b.append(text(xd(s_) + 6, y + 12, who, 10, SEC))
        elif e <= 13.0:
            b.append(text(xd(e) + 5, y + 12, who, 10, MUTED))
        else:
            b.append(text(xd(s_) - 5, y + 12, who, 10, MUTED, anchor="end"))
    # deadlines (labels in the top margin, right of the line)
    for d, label, dy in ((3.0, "Fri 23 Oct: account + isolated core ready", 0), (5.0, "Mon 26 Oct: counted runs start", 0)):
        b.append(f'<line x1="{xd(d):.1f}" y1="{TOP - 20}" x2="{xd(d):.1f}" y2="{timer_y + 20}" stroke="{SEC}" stroke-width="1.5"/>')
    b.append(text(xd(3.0) - 4, timer_y + 34, "Fri 23 Oct: account + isolated core ready (met 22 Oct)", 10.5, SEC, anchor="end"))
    b.append(text(xd(5.0) + 4, timer_y + 34, "Mon 26 Oct: counted runs start", 10.5, SEC))
    # host timers row
    b.append(text(LEFT - 10, timer_y + 12, "Host timers (paused 22 Oct 05:30 UTC)", 11.5, INK, anchor="end"))
    for i in range(days):
        b.append(f'<rect x="{xd(i):.1f}" y="{timer_y}" width="2" height="{bh}" fill="{SERIOUS if i <= 1 else BASE}"/>')
        b.append(f'<rect x="{xd(i + 6 / 24):.1f}" y="{timer_y}" width="{ppd / 24:.1f}" height="{bh}" fill="{WARN if i <= 0 else BASE}"/>')
    b.append(f'<rect x="{xd(5 + 27 / 1440):.1f}" y="{timer_y - 4}" width="3" height="{bh + 8}" fill="{BASE}"/>')
    b.append(text(xd(5 + 27 / 1440) + 6, timer_y - 8, "fstrim Mon 26 Oct (paused)", 10, MUTED))
    b.append(f'<rect x="{xd(12 + 27 / 1440):.1f}" y="{timer_y - 4}" width="3" height="{bh + 8}" fill="{BASE}"/>')
    b.append(text(xd(12 + 27 / 1440) + 6, timer_y - 8, "fstrim Mon 2 Nov (paused)", 10, MUTED))
    b.append(f'<line x1="{xd(11.3):.1f}" y1="{TOP - 20}" x2="{xd(11.3):.1f}" y2="{timer_y + 20}" stroke="{ORANGE}" stroke-width="1.5" stroke-dasharray="5 4"/>')
    b.append(text(xd(11.3) + 4, TOP - 56, "Sun 1 Nov: US clocks change", 10, ORANGE))
    ly = timer_y + 52
    legend = [("00:00 UTC daily: logrotate, dpkg-db-backup", SERIOUS), ("06:00\u201307:00 UTC daily: apt-daily-upgrade (unattended-upgrades)", WARN), ("fstrim, weekly", CRIT), ("paused since 22 Oct 05:30 UTC", BASE)]
    lx = 20
    for name, col in legend:
        b.append(f'<rect x="{lx}" y="{ly}" width="10" height="10" fill="{col}"/>')
        b.append(text(lx + 14, ly + 9, name, 10.5, SEC))
        lx += 14 + len(name) * 6.2 + 18
    b.append(text(20, ly + 28, "Gray marks show when the paused timers would have fired. sysstat still samples every 10 min (kept by decision A8). Restore the timers after 6 Nov (P9).", 10.5, MUTED))
    b.append(text(20, ly + 42, "Sun 1 Nov: Jeremy's clock changes from EDT to EST at 06:00 UTC, Jibin's from PDT to PST at 09:00 UTC. Windows are stated in UTC.", 10.5, MUTED))
    return svg(W, H, "".join(b), "Timeline from 21 October to the 5 November demo: the changes and reboot of 22 October, Jeremy's first counted block on 23 October, his blocks until the demo, Jibin away from 22 to about 29 October, the deferred kernel path, and the host timers, paused on 22 October.")

figs = {
    "fig_timeline": fig_timeline(),
    "fig_clock_patterns": fig_clock_patterns(),
    "fig_ticks": fig_ticks(),
    "fig_cpu_alloc": fig_cpu_alloc(),
    "fig_kernel_paths": fig_kernel_paths(),
    "fig_lanes": fig_lanes(),
    "fig_churn_r1": fig_churn_r1(),
    "fig_lateness_budget": fig_lateness_budget(),
}
for k, v in figs.items():
    with open(os.path.join(OUT, k + ".svg"), "w", encoding="utf-8") as f:
        f.write(v)
with open(os.path.join(OUT, "figs.json"), "w", encoding="utf-8") as f:
    json.dump(figs, f)
prev = "<!doctype html><html><head><meta charset='utf-8'><style>body{background:#fff;margin:24px;font-family:system-ui}figure{margin:0 0 32px}</style></head><body>" + "".join(f"<figure>{v}<figcaption>{k}</figcaption></figure>" for k, v in figs.items()) + "</body></html>"
with open(os.path.join(OUT, "preview.html"), "w", encoding="utf-8") as f:
    f.write(prev)
print("wrote", ", ".join(figs))
