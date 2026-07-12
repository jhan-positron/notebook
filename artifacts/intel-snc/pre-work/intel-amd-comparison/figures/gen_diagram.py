#!/usr/bin/env python3
"""Generate Intel 6962P system + compute-die-mesh diagram as PNG."""

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch

# -------- styling constants --------
COLOR_BG          = '#fafaf7'
COLOR_PKG_BORDER  = '#2b3a3f'
COLOR_PKG_FILL    = '#e8ecee'
COLOR_COMPUTE_BORDER = '#1a4d63'
COLOR_COMPUTE_FILL   = '#cee4ec'
COLOR_IO_BORDER   = '#5b4636'
COLOR_IO_FILL     = '#e8d9b8'
COLOR_MC_BORDER   = '#1a4d63'
COLOR_MC_FILL     = '#7eb0c7'
COLOR_EMIB_BORDER = '#6b3838'
COLOR_EMIB_FILL   = '#e5c4c4'
COLOR_MS_BORDER   = '#1a4d63'
COLOR_MS_FILL     = '#dbeaef'
COLOR_MESH_LINE   = '#5a6a72'
COLOR_UPI_LINE    = '#8b2e2e'
COLOR_DRAM        = '#404040'

FONT_LARGE  = 13
FONT_MED    = 10
FONT_SMALL  = 8.5
FONT_TINY   = 7.5

# Total figure height reduced; tighter packing
fig = plt.figure(figsize=(16, 18), facecolor=COLOR_BG)

# Three vertical sections:
#   ax_top:    sockets + UPI                    (45% height)
#   ax_mid:    per-socket totals                (10% height)
#   ax_bot:    die mesh + legend                (40% height)
ax_top = fig.add_axes([0.02, 0.55, 0.96, 0.40])
ax_mid = fig.add_axes([0.02, 0.43, 0.96, 0.09])
ax_bot = fig.add_axes([0.02, 0.02, 0.96, 0.40])

for ax in (ax_top, ax_mid, ax_bot):
    ax.set_xlim(0, 100)
    ax.set_axis_off()
    ax.set_facecolor(COLOR_BG)

# Figure title
fig.text(0.5, 0.98, 'Intel Xeon 6962P  —  System Architecture Reference',
         ha='center', va='top', fontsize=18, fontweight='bold',
         color=COLOR_PKG_BORDER)
fig.text(0.5, 0.962, '(Granite Rapids-AP, two-socket, SNC OFF)',
         ha='center', va='top', fontsize=11, style='italic',
         color='#555555')

# ================================================================
# TOP PANEL: SOCKETS
# ================================================================
ax_top.set_ylim(0, 60)
ax_top.text(50, 58, 'Two-Socket System Overview',
            ha='center', va='top', fontsize=14, fontweight='bold',
            color=COLOR_PKG_BORDER)

def draw_socket(ax, x0, y0, w, h, sock_label, numa_label, dies_start_id):
    pkg = FancyBboxPatch((x0, y0), w, h,
                         boxstyle="round,pad=0.4",
                         linewidth=2.2,
                         edgecolor=COLOR_PKG_BORDER,
                         facecolor=COLOR_PKG_FILL)
    ax.add_patch(pkg)
    ax.text(x0 + w/2, y0 + h - 1.6,
            f'{sock_label}  /  {numa_label}',
            ha='center', va='top', fontsize=12, fontweight='bold',
            color=COLOR_PKG_BORDER)

    # IO die (W)
    io_w = 5.0
    io_h = 9.0
    io_w_x = x0 + 1.5
    io_y   = y0 + (h - io_h)/2 - 1
    io_west = Rectangle((io_w_x, io_y), io_w, io_h,
                        linewidth=1.5, edgecolor=COLOR_IO_BORDER,
                        facecolor=COLOR_IO_FILL)
    ax.add_patch(io_west)
    ax.text(io_w_x + io_w/2, io_y + io_h - 0.7, 'IO die (W)',
            ha='center', va='top', fontsize=FONT_SMALL, fontweight='bold')
    ax.text(io_w_x + io_w/2, io_y + io_h/2 - 0.2,
            'PCIe\nDSA / IAA\nQAT / DLB\nUPI ctrl',
            ha='center', va='center', fontsize=FONT_TINY,
            color='#444444', linespacing=1.3)

    # 3 compute dies
    cd_w = 8.5
    cd_h = 10.5
    cd_gap = 1.6
    cd_start_x = io_w_x + io_w + 1.5
    cd_y = y0 + (h - cd_h)/2 - 1

    for i in range(3):
        cd_x = cd_start_x + i * (cd_w + cd_gap)
        cd = Rectangle((cd_x, cd_y), cd_w, cd_h,
                      linewidth=1.8, edgecolor=COLOR_COMPUTE_BORDER,
                      facecolor=COLOR_COMPUTE_FILL)
        ax.add_patch(cd)
        ax.text(cd_x + cd_w/2, cd_y + cd_h - 0.8,
                f'Compute die {dies_start_id + i}',
                ha='center', va='top', fontsize=FONT_SMALL,
                fontweight='bold', color=COLOR_COMPUTE_BORDER)
        # Body text: only the numerical totals
        ax.text(cd_x + cd_w/2, cd_y + cd_h/2 + 0.2,
                '~24 cores\n~36 CHAs\n144 MiB L3\n4 MCs',
                ha='center', va='center', fontsize=FONT_TINY,
                color='#222222', linespacing=1.5)
        # Position label inside the box, at bottom
        pos_label = '(middle die)' if i == 1 else '(end die)'
        ax.text(cd_x + cd_w/2, cd_y + 0.6, pos_label,
                ha='center', va='bottom', fontsize=FONT_TINY,
                style='italic', color='#666666')

        # DDR channels exiting bottom
        n_ch = 4
        for k in range(n_ch):
            ch_x = cd_x + (k+1) * cd_w/(n_ch+1)
            ax.annotate('', xy=(ch_x, cd_y - 3.5), xytext=(ch_x, cd_y),
                       arrowprops=dict(arrowstyle='-', color=COLOR_DRAM,
                                       linewidth=0.9))

        # EMIB bridges between dies
        if i < 2:
            emib_x = cd_x + cd_w
            emib_y = cd_y + cd_h*0.12
            emib_w_local = cd_gap
            emib_h_local = cd_h*0.76
            emib = Rectangle((emib_x, emib_y), emib_w_local, emib_h_local,
                           linewidth=1.0, edgecolor=COLOR_EMIB_BORDER,
                           facecolor=COLOR_EMIB_FILL, alpha=0.85)
            ax.add_patch(emib)
            ax.text(emib_x + emib_w_local/2, emib_y + emib_h_local/2, 'EMIB',
                    ha='center', va='center', fontsize=FONT_TINY,
                    rotation=90, color=COLOR_EMIB_BORDER, fontweight='bold')

    # DDR5 channel summary line under the dies
    chmin_x = cd_start_x
    chmax_x = cd_start_x + 3 * cd_w + 2 * cd_gap
    ch_line_y = cd_y - 4.2
    ax.plot([chmin_x, chmax_x], [ch_line_y, ch_line_y],
            color=COLOR_DRAM, linewidth=1.2)
    ax.text((chmin_x + chmax_x)/2, ch_line_y - 0.6,
            '12 × DDR5-6400 channels (4 per compute die)',
            ha='center', va='top', fontsize=FONT_SMALL,
            color=COLOR_DRAM, style='italic')

    # IO die (E)
    io_e_x = cd_start_x + 3 * cd_w + 2 * cd_gap + 1.5
    io_east = Rectangle((io_e_x, io_y), io_w, io_h,
                       linewidth=1.5, edgecolor=COLOR_IO_BORDER,
                       facecolor=COLOR_IO_FILL)
    ax.add_patch(io_east)
    ax.text(io_e_x + io_w/2, io_y + io_h - 0.7, 'IO die (E)',
            ha='center', va='top', fontsize=FONT_SMALL, fontweight='bold')
    ax.text(io_e_x + io_w/2, io_y + io_h/2 - 0.2,
            'PCIe\nDSA / IAA\nQAT / DLB\nUPI ctrl',
            ha='center', va='center', fontsize=FONT_TINY,
            color='#444444', linespacing=1.3)

    return io_e_x + io_w

SOCK0_X = 1; SOCK0_Y = 17; SOCK_W  = 44; SOCK_H  = 36
SOCK1_X = 55; SOCK1_Y = 17
draw_socket(ax_top, SOCK0_X, SOCK0_Y, SOCK_W, SOCK_H,
            'PACKAGE / SOCKET 0', 'NUMA node 0', dies_start_id=0)
draw_socket(ax_top, SOCK1_X, SOCK1_Y, SOCK_W, SOCK_H,
            'PACKAGE / SOCKET 1', 'NUMA node 1', dies_start_id=3)

# UPI link - now has 10 units of horizontal room (45..55)
upi_y = SOCK0_Y + SOCK_H/2
ax_top.annotate('', xy=(SOCK1_X, upi_y), xytext=(SOCK0_X + SOCK_W, upi_y),
                arrowprops=dict(arrowstyle='<->', color=COLOR_UPI_LINE,
                                linewidth=2.8))
ax_top.text(50, upi_y + 2.2, 'UPI',
            ha='center', va='bottom', fontsize=FONT_LARGE, fontweight='bold',
            color=COLOR_UPI_LINE)
ax_top.text(50, upi_y - 2.3, '(UPI 2.0)',
            ha='center', va='top', fontsize=FONT_SMALL, style='italic',
            color=COLOR_UPI_LINE)

# ================================================================
# MIDDLE PANEL: PER-SOCKET TOTALS BOX
# ================================================================
ax_mid.set_ylim(0, 20)
totals_box = FancyBboxPatch((5, 1), 90, 18,
                            boxstyle="round,pad=0.5",
                            linewidth=1.0, edgecolor='#888888',
                            facecolor='#fcfbf6')
ax_mid.add_patch(totals_box)
ax_mid.text(50, 17.5, 'Per-socket totals',
            ha='center', va='top', fontsize=FONT_MED, fontweight='bold')

per_sock_text = (
    '72 cores enabled  (Redwood Cove, L1d 48 KB, L2 2 MB per core)     '
    '432 MiB L3 total  =  108 CHAs × 4 MiB/slice  =  3 × 144 MiB compute dies\n'
    '12 DDR5-6400 channels (4 controllers per compute die)     '
    '768 GB DRAM populated (12 × 64 GB DIMMs, 1 DPC)\n'
    'ACPI NUMA distance:  local = 10,  remote = 21     '
    'Measured remote/local DRAM latency ratio:  2.01×'
)
ax_mid.text(50, 14, per_sock_text,
            ha='center', va='top', fontsize=FONT_SMALL,
            linespacing=1.6)

# ================================================================
# BOTTOM PANEL: COMPUTE DIE MESH DETAIL
# ================================================================
ax_bot.set_ylim(0, 90)
ax_bot.text(50, 87, 'Compute Die — Internal Layout',
            ha='center', va='top', fontsize=14, fontweight='bold',
            color=COLOR_COMPUTE_BORDER)
ax_bot.text(50, 83.5,
            'Illustrative 6×6 mesh  (real layout not published by Intel)',
            ha='center', va='top', fontsize=10, style='italic',
            color='#555555')

# Compute die outer box - leave room on the right for an MS zoom-in
DIE_X0 = 8; DIE_X1 = 68
DIE_Y0 = 23; DIE_Y1 = 79
die_box = Rectangle((DIE_X0, DIE_Y0), DIE_X1 - DIE_X0, DIE_Y1 - DIE_Y0,
                    linewidth=2.2, edgecolor=COLOR_COMPUTE_BORDER,
                    facecolor=COLOR_COMPUTE_FILL, alpha=0.4)
ax_bot.add_patch(die_box)

# MC strips on top/bottom edges
mc_h = 2.8
mc_w = (DIE_X1 - DIE_X0) / 2 - 6

# Top: MC0, MC1
mc0 = Rectangle((DIE_X0 + 2, DIE_Y1 - mc_h - 0.5), mc_w, mc_h,
                linewidth=1.5, edgecolor=COLOR_MC_BORDER,
                facecolor=COLOR_MC_FILL)
ax_bot.add_patch(mc0)
ax_bot.text(DIE_X0 + 2 + mc_w/2, DIE_Y1 - mc_h/2 - 0.5, 'MC0',
            ha='center', va='center', fontsize=FONT_MED, fontweight='bold')

mc1 = Rectangle((DIE_X1 - 2 - mc_w, DIE_Y1 - mc_h - 0.5), mc_w, mc_h,
                linewidth=1.5, edgecolor=COLOR_MC_BORDER,
                facecolor=COLOR_MC_FILL)
ax_bot.add_patch(mc1)
ax_bot.text(DIE_X1 - 2 - mc_w/2, DIE_Y1 - mc_h/2 - 0.5, 'MC1',
            ha='center', va='center', fontsize=FONT_MED, fontweight='bold')

# Bottom: MC2, MC3
mc2 = Rectangle((DIE_X0 + 2, DIE_Y0 + 0.5), mc_w, mc_h,
                linewidth=1.5, edgecolor=COLOR_MC_BORDER,
                facecolor=COLOR_MC_FILL)
ax_bot.add_patch(mc2)
ax_bot.text(DIE_X0 + 2 + mc_w/2, DIE_Y0 + mc_h/2 + 0.5, 'MC2',
            ha='center', va='center', fontsize=FONT_MED, fontweight='bold')

mc3 = Rectangle((DIE_X1 - 2 - mc_w, DIE_Y0 + 0.5), mc_w, mc_h,
                linewidth=1.5, edgecolor=COLOR_MC_BORDER,
                facecolor=COLOR_MC_FILL)
ax_bot.add_patch(mc3)
ax_bot.text(DIE_X1 - 2 - mc_w/2, DIE_Y0 + mc_h/2 + 0.5, 'MC3',
            ha='center', va='center', fontsize=FONT_MED, fontweight='bold')

# Edge labels
ax_bot.text(50, DIE_Y1 + 0.5, '↑ short edge (top)',
            ha='center', va='bottom', fontsize=FONT_SMALL,
            color='#666666', style='italic')
ax_bot.text(50, DIE_Y0 - 0.5, '↓ short edge (bottom)',
            ha='center', va='top', fontsize=FONT_SMALL,
            color='#666666', style='italic')

# EMIB sites on long edges
emib_w_box = 3.2
emib_h_box = 3.5
emib_labels_left  = ['EMIB-A', 'EMIB-B', 'EMIB-C']
emib_labels_right = ['EMIB-D', 'EMIB-E', 'EMIB-F']

# Span between MC strips
emib_top = DIE_Y1 - mc_h - 1.5
emib_bot = DIE_Y0 + mc_h + 1.5
emib_centers_y = [emib_top - emib_h_box/2 - i*(emib_top - emib_bot - emib_h_box)/2
                  for i in range(3)]

for i, cy in enumerate(emib_centers_y):
    le = Rectangle((DIE_X0 + 0.4, cy - emib_h_box/2), emib_w_box, emib_h_box,
                   linewidth=1.5, edgecolor=COLOR_EMIB_BORDER,
                   facecolor=COLOR_EMIB_FILL)
    ax_bot.add_patch(le)
    ax_bot.text(DIE_X0 + 0.4 + emib_w_box/2, cy,
                emib_labels_left[i],
                ha='center', va='center', fontsize=FONT_TINY,
                fontweight='bold', color=COLOR_EMIB_BORDER, rotation=90)

    re = Rectangle((DIE_X1 - 0.4 - emib_w_box, cy - emib_h_box/2),
                   emib_w_box, emib_h_box,
                   linewidth=1.5, edgecolor=COLOR_EMIB_BORDER,
                   facecolor=COLOR_EMIB_FILL)
    ax_bot.add_patch(re)
    ax_bot.text(DIE_X1 - 0.4 - emib_w_box/2, cy,
                emib_labels_right[i],
                ha='center', va='center', fontsize=FONT_TINY,
                fontweight='bold', color=COLOR_EMIB_BORDER, rotation=90)

# Long-edge labels
ax_bot.text(DIE_X0 - 1.0, (DIE_Y0 + DIE_Y1)/2, 'long edge (left)',
            ha='center', va='center', fontsize=FONT_SMALL,
            color='#666666', style='italic', rotation=90)
ax_bot.text(DIE_X1 + 1.0, (DIE_Y0 + DIE_Y1)/2, 'long edge (right)',
            ha='center', va='center', fontsize=FONT_SMALL,
            color='#666666', style='italic', rotation=270)

# 6x6 mesh
mesh_x0 = DIE_X0 + emib_w_box + 4
mesh_x1 = DIE_X1 - emib_w_box - 4
mesh_y0 = DIE_Y0 + mc_h + 2.5
mesh_y1 = DIE_Y1 - mc_h - 2.5

n = 6
xs = [mesh_x0 + (i + 0.5) * (mesh_x1 - mesh_x0) / n for i in range(n)]
ys = [mesh_y0 + (i + 0.5) * (mesh_y1 - mesh_y0) / n for i in range(n)]
ms_size = min(xs[1]-xs[0], ys[1]-ys[0]) * 0.55

# Mesh lines first
for i in range(n):
    for j in range(n):
        if j < n - 1:
            ax_bot.plot([xs[j], xs[j+1]], [ys[i], ys[i]],
                       color=COLOR_MESH_LINE, linewidth=1.5, zorder=1)
        if i < n - 1:
            ax_bot.plot([xs[j], xs[j]], [ys[i], ys[i+1]],
                       color=COLOR_MESH_LINE, linewidth=1.5, zorder=1)

# Mesh stops on top
for i in range(n):
    for j in range(n):
        cx, cy = xs[j], ys[i]
        ms = Rectangle((cx - ms_size/2, cy - ms_size/2), ms_size, ms_size,
                      linewidth=1.0, edgecolor=COLOR_MS_BORDER,
                      facecolor=COLOR_MS_FILL, zorder=2)
        ax_bot.add_patch(ms)
        ax_bot.text(cx, cy, 'MS', ha='center', va='center',
                    fontsize=FONT_TINY, color=COLOR_MS_BORDER,
                    fontweight='bold', zorder=3)

# Legend BELOW the die diagram
legend_text = (
    'MS  = mesh stop  (= 1 core, possibly fused-off  +  1 CHA: L3 slice 4 MiB + snoop filter + router)\n'
    'MC  = on-die DRAM memory controller   (4 per die, on short edges per Chips and Cheese article)\n'
    'EMIB = embedded silicon bridge to neighbor compute die   (carries cross-die mesh + MDF traffic)\n'
    '\n'
    'Per-die totals (DERIVED, uniform-distribution assumption):  ~24 cores AVG enabled  ·  '
    '36 mesh stops × 4 MiB L3 = 144 MiB L3  ·  4 DRAM controllers\n'
    'NOT published by Intel:  real mesh shape, in-die mesh BW (GB/s), '
    'EMIB/MDF BW (GB/s), number of EMIB sites per long edge'
)
ax_bot.text(50, 17, legend_text,
            ha='center', va='top', fontsize=FONT_SMALL,
            linespacing=1.6, family='monospace')

# ================================================================
#  MS ZOOM-IN INSET (right side of bottom panel)
# ================================================================
# Outline the source MS to make the zoom obvious
src_i = 2  # row of MS to highlight (interior cell)
src_j = 4  # col
src_cx, src_cy = xs[src_j], ys[src_i]

# Highlight box around the source MS
hl = Rectangle((src_cx - ms_size/2 - 0.4, src_cy - ms_size/2 - 0.4),
               ms_size + 0.8, ms_size + 0.8,
               linewidth=2.0, edgecolor='#c46b1a',
               facecolor='none', linestyle='--', zorder=5)
ax_bot.add_patch(hl)

# Zoom inset position (right side of bottom panel) - taller box
ZX0 = 72; ZX1 = 98
ZY0 = 25; ZY1 = 77
zoom_box = FancyBboxPatch((ZX0, ZY0), ZX1-ZX0, ZY1-ZY0,
                         boxstyle="round,pad=0.4",
                         linewidth=1.5, edgecolor='#c46b1a',
                         facecolor='#fdf6ec')
ax_bot.add_patch(zoom_box)

# Zoom title
ax_bot.text((ZX0+ZX1)/2, ZY1 - 1.5, 'Single Mesh Stop (zoom)',
            ha='center', va='top', fontsize=FONT_MED, fontweight='bold',
            color='#c46b1a')

# Connector lines from source MS to zoom box (dashed)
ax_bot.plot([src_cx + ms_size/2 + 0.4, ZX0],
           [src_cy + ms_size/2 + 0.4, ZY1 - 0.4],
           color='#c46b1a', linewidth=1.0, linestyle=':', zorder=4)
ax_bot.plot([src_cx + ms_size/2 + 0.4, ZX0],
           [src_cy - ms_size/2 - 0.4, ZY0 + 0.4],
           color='#c46b1a', linewidth=1.0, linestyle=':', zorder=4)

# Inside zoom: CORE | CHA at top, ROUTER in middle, N/S/E/W arrows extending from router
# Box layout
CORE_W = 9.0; CORE_H = 17
CORE_X = ZX0 + 2.5; CORE_Y = ZY1 - 4 - CORE_H

core_box = Rectangle((CORE_X, CORE_Y), CORE_W, CORE_H,
                    linewidth=1.5, edgecolor=COLOR_COMPUTE_BORDER,
                    facecolor='#dbeaef')
ax_bot.add_patch(core_box)
ax_bot.text(CORE_X + CORE_W/2, CORE_Y + CORE_H - 1.0, 'CORE',
            ha='center', va='top', fontsize=FONT_MED, fontweight='bold',
            color=COLOR_COMPUTE_BORDER)
ax_bot.text(CORE_X + CORE_W/2, CORE_Y + CORE_H - 3.2,
            'Redwood Cove',
            ha='center', va='top', fontsize=FONT_TINY,
            style='italic', color='#444')
ax_bot.text(CORE_X + CORE_W/2, CORE_Y + CORE_H - 5.5,
            '(may be\nfused-off)',
            ha='center', va='top', fontsize=FONT_TINY,
            style='italic', color='#777', linespacing=1.3)
ax_bot.text(CORE_X + CORE_W/2, CORE_Y + 1.5,
            'L1d 48 KB\nL1i 64 KB\nL2 2 MB',
            ha='center', va='bottom', fontsize=FONT_TINY,
            linespacing=1.5, color='#222222')

# CHA on the right of CORE
CHA_X = CORE_X + CORE_W + 2; CHA_Y = CORE_Y
CHA_W = CORE_W; CHA_H = CORE_H
cha_box = Rectangle((CHA_X, CHA_Y), CHA_W, CHA_H,
                   linewidth=1.5, edgecolor=COLOR_MS_BORDER,
                   facecolor='#cee4ec')
ax_bot.add_patch(cha_box)
ax_bot.text(CHA_X + CHA_W/2, CHA_Y + CHA_H - 1.0, 'CHA',
            ha='center', va='top', fontsize=FONT_MED, fontweight='bold',
            color=COLOR_MS_BORDER)
ax_bot.text(CHA_X + CHA_W/2, CHA_Y + CHA_H - 3.2,
            'Caching /\nHome Agent',
            ha='center', va='top', fontsize=FONT_TINY,
            style='italic', color='#444', linespacing=1.3)
ax_bot.text(CHA_X + CHA_W/2, CHA_Y + 1.5,
            'L3 slice 4 MiB\nsnoop filter\ncoherency',
            ha='center', va='bottom', fontsize=FONT_TINY,
            linespacing=1.5, color='#222222')

# Bidirectional arrow between CORE and CHA
ax_bot.annotate('', xy=(CHA_X, CORE_Y + CORE_H/2),
                xytext=(CORE_X + CORE_W, CORE_Y + CORE_H/2),
                arrowprops=dict(arrowstyle='<->', color='#444',
                                linewidth=1.4))

# Router below, centered
RTR_W = 9; RTR_H = 3.2
RTR_X = (ZX0 + ZX1)/2 - RTR_W/2
RTR_Y = ZY0 + 6.5
router = Rectangle((RTR_X, RTR_Y), RTR_W, RTR_H,
                  linewidth=1.5, edgecolor='#5a6a72',
                  facecolor='#dfe5e8')
ax_bot.add_patch(router)
ax_bot.text(RTR_X + RTR_W/2, RTR_Y + RTR_H/2, 'mesh router',
            ha='center', va='center', fontsize=FONT_SMALL, fontweight='bold',
            color='#3a4a52')

# Connectors from CHA/CORE down to router (single combined line)
midpoint_top_y = CORE_Y
midpoint_bot_y = RTR_Y + RTR_H
center_x = (ZX0 + ZX1)/2
ax_bot.plot([center_x, center_x],
           [midpoint_top_y, midpoint_bot_y],
           color='#444', linewidth=1.4)
# Small horizontal tee under CORE+CHA
tee_y = midpoint_top_y
core_center = CORE_X + CORE_W/2
cha_center  = CHA_X + CHA_W/2
ax_bot.plot([core_center, cha_center], [tee_y, tee_y],
           color='#444', linewidth=1.4)

# N/S/E/W arrows OUTSIDE the router box, labels at arrow tips
# West
W_xtip = RTR_X - 4
ax_bot.annotate('', xy=(W_xtip, RTR_Y + RTR_H/2),
                xytext=(RTR_X, RTR_Y + RTR_H/2),
                arrowprops=dict(arrowstyle='->', color=COLOR_MESH_LINE,
                                linewidth=1.5))
ax_bot.text(W_xtip - 0.4, RTR_Y + RTR_H/2, 'W',
            ha='right', va='center', fontsize=FONT_SMALL,
            color=COLOR_MESH_LINE, fontweight='bold')

# East
E_xtip = RTR_X + RTR_W + 4
ax_bot.annotate('', xy=(E_xtip, RTR_Y + RTR_H/2),
                xytext=(RTR_X + RTR_W, RTR_Y + RTR_H/2),
                arrowprops=dict(arrowstyle='->', color=COLOR_MESH_LINE,
                                linewidth=1.5))
ax_bot.text(E_xtip + 0.4, RTR_Y + RTR_H/2, 'E',
            ha='left', va='center', fontsize=FONT_SMALL,
            color=COLOR_MESH_LINE, fontweight='bold')

# South
S_ytip = RTR_Y - 3
ax_bot.annotate('', xy=(RTR_X + RTR_W/2, S_ytip),
                xytext=(RTR_X + RTR_W/2, RTR_Y),
                arrowprops=dict(arrowstyle='->', color=COLOR_MESH_LINE,
                                linewidth=1.5))
ax_bot.text(RTR_X + RTR_W/2, S_ytip - 0.4, 'S',
            ha='center', va='top', fontsize=FONT_SMALL,
            color=COLOR_MESH_LINE, fontweight='bold')

# (North is already going up to CORE/CHA via the existing connector - label it 'N')
N_ytip_label = (RTR_Y + RTR_H + midpoint_top_y) / 2
ax_bot.text(center_x + 0.6, N_ytip_label, 'N',
            ha='left', va='center', fontsize=FONT_SMALL,
            color=COLOR_MESH_LINE, fontweight='bold')

# Footer
ax_bot.text((ZX0+ZX1)/2, ZY0 + 2,
            'Router links the stop to N/S/E/W\nneighbor mesh stops',
            ha='center', va='center', fontsize=FONT_TINY,
            style='italic', color='#666', linespacing=1.4)

# ================================================================
# Legend BELOW the die diagram
# ================================================================
legend_text = (
    'MS  = mesh stop  (= 1 core, possibly fused-off  +  1 CHA: L3 slice 4 MiB + snoop filter + router)\n'
    'MC  = on-die DRAM memory controller   (4 per die, on short edges per Chips and Cheese article)\n'
    'EMIB = embedded silicon bridge to neighbor compute die   (carries cross-die mesh + MDF traffic)\n'
    '\n'
    'Per-die totals (DERIVED, uniform-distribution assumption):  ~24 cores AVG enabled  ·  '
    '36 mesh stops × 4 MiB L3 = 144 MiB L3  ·  4 DRAM controllers\n'
    'NOT published by Intel:  real mesh shape, in-die mesh BW (GB/s), '
    'EMIB/MDF BW (GB/s), number of EMIB sites per long edge'
)
ax_bot.text(50, 17, legend_text,
            ha='center', va='top', fontsize=FONT_SMALL,
            linespacing=1.6, family='monospace')

output_path = '/home/claude/intel_xeon_6962p_architecture.png'
plt.savefig(output_path, dpi=160, facecolor=COLOR_BG,
            bbox_inches='tight', pad_inches=0.3)
print(f"Saved: {output_path}")
plt.close()
