#!/usr/bin/env python3
"""Per-window coverage/gap analysis for a pfgate draw (§5.4 of the runbook).

For every window: merge all named-span intervals across all threads (capped
at window edges, 'forward' excluded) and measure the uncovered time — moments
where NO tron thread had a named span open. Also record the largest single
gap and the span names immediately before/after it, and the position of the
last 'data ready' marker relative to the repaired fill end.

Usage: window_gaps.py <slices_csv> <out_csv>
Reads the cached <draw>.slices.csv produced by pfgate_windows.py.
"""

import csv
import statistics
import sys

GAP_NS = 1_500_000

# Spans that are (mostly) WAITING, not host work. They may legitimately span
# the whole step (RX loops) or contain long blocking waits (tx act_ready,
# stream wait inside fill). They count as "wait coverage", never as work,
# and are excluded from the window-extent computation.
WAIT_SPANS = {
    "rx collecting results",
    "waiting_for_logits",
    "fill_logits_buffer",   # stream wait + consume (B); mostly wait per kvprobe4
    "notify_listener",      # wrapper around fill + callback; classified wait to
                            # avoid double-count with fill (callback part ~12us)
    "legacy tx_launch",     # slot/cmd/act_ready waits + ring writes
    "attn tx_launch",
    "tx waiting for slots",
    "waiting for mbox",
    "Attention Pending",
    "Attention Ready",
    "work_queue::do_work get_work",  # job-fetch spin/park loop
    "poll_dma_completions",          # DMA completion poll loop
}


def load(path):
    rows = []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            try:
                ts, dur = int(r["ts"]), int(r["dur"])
            except (ValueError, KeyError):
                continue
            rows.append((ts, dur, r["name"], r["thread_name"]))
    rows.sort(key=lambda x: x[0])
    return rows


def segment(rows):
    win, prev = [], None
    for row in rows:
        if prev is not None and row[0] - prev > GAP_NS:
            yield win
            win = []
        win.append(row)
        prev = row[0]
    if win:
        yield win


def main():
    slices_csv, out_csv = sys.argv[1], sys.argv[2]
    rows = load(slices_csv)
    wins = list(segment(rows))
    out = []
    for wi, win in enumerate(wins):
        w0 = win[0][0]
        cap = wins[wi + 1][0][0] if wi + 1 < len(wins) else None
        work, wait = [], []
        last_dr, fill_end = None, None
        # Window extent from plausibly-window-local spans only (see
        # pfgate_windows.py: step-spanning artifacts from unmatched ENDs).
        EXTENT_BOUND_NS = 2_500_000
        wend = w0
        for ts, dur, name, thr in win:
            if name in ("forward", "data ready") or dur < 0 or dur >= EXTENT_BOUND_NS:
                continue
            e = min(ts + dur, cap) if cap is not None else ts + dur
            if name in ("fill_logits_buffer", "notify_listener") or name not in WAIT_SPANS:
                wend = max(wend, e)
        listener_start, drs = None, []
        for ts, dur, name, thr in win:
            if name == "forward":
                continue
            raw_end = ts + max(dur, 0)
            e = min(raw_end, cap) if cap is not None else raw_end
            if name == "data ready":
                last_dr = ts
                drs.append(ts)
                continue  # instant; no interval
            if name in ("fill_logits_buffer", "notify_listener"):
                fill_end = max(fill_end or 0, min(e, wend))
                listener_start = ts if listener_start is None else min(listener_start, ts)
            if name in WAIT_SPANS:
                wait.append((ts, e, name, thr))
            else:
                work.append((ts, e, name, thr))

        def merge(ivs):
            ivs = sorted((s, min(e, wend)) for s, e, *_ in ivs if s < wend)
            m = []
            for s, e in ivs:
                if m and s <= m[-1][1]:
                    m[-1][1] = max(m[-1][1], e)
                else:
                    m.append([s, e])
            return m

        m_work = merge(work)
        m_all = merge(work + wait)
        span = wend - w0
        work_cov = sum(e - s for s, e in m_work)
        all_cov = sum(e - s for s, e in m_all)
        # biggest all-idle gap (no span of any kind open), within window extent
        biggest, b_at, b_before, b_after = 0, None, "", ""
        for i in range(len(m_all) - 1):
            g = m_all[i + 1][0] - m_all[i][1]
            if g > biggest:
                biggest, b_at = g, m_all[i][1]
        if b_at is not None:
            for ts, dur, name, thr in win:
                if name in ("forward", "data ready"):
                    continue
                raw_end = ts + max(dur, 0)
                e = min(raw_end, min(cap, wend) if cap else wend)
                if e == b_at:
                    b_before = f"{name}@{thr.strip()}"
                if ts == b_at + biggest:
                    b_after = f"{name}@{thr.strip()}"
        out.append({
            "window": wi,
            "start_ts": w0,
            "span_us": round(span / 1000, 1),
            "work_cov_us": round(work_cov / 1000, 1),
            "wait_cov_us": round((all_cov - work_cov) / 1000, 1),
            "idle_us": round((span - all_cov) / 1000, 1),
            "biggest_gap_us": round(biggest / 1000, 1),
            "gap_at_off_us": round((b_at - w0) / 1000, 1) if b_at else "",
            "gap_before": b_before,
            "gap_after": b_after,
            "last_dataready_off_us": round((last_dr - w0) / 1000, 1) if last_dr else "",
            "fill_end_off_us": round((fill_end - w0) / 1000, 1) if fill_end else "",
            "listener_start_off_us": round((listener_start - w0) / 1000, 1) if listener_start else "",
            # data-ready instants split by the listener-job end: before it =
            # the wcls (lm-head) burst, after it = the next step's first dispatch
            "wcls_last_dr_off_us": round((max((t for t in drs if fill_end and t <= fill_end), default=0) - w0) / 1000, 1) if fill_end and drs else "",
            "dispatch_first_dr_off_us": round((min((t for t in drs if fill_end and t > fill_end), default=0) - w0) / 1000, 1) if fill_end and any(t > fill_end for t in drs) else "",
        })
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)
    spans = [o["span_us"] for o in out]
    idle = [o["idle_us"] for o in out]
    big = [o["biggest_gap_us"] for o in out]
    def p90(v):
        s = sorted(v)
        return s[int(0.9 * (len(s) - 1))]
    print(f"windows={len(out)} span med={statistics.median(spans):.0f} p90={p90(spans):.0f} | "
          f"idle med={statistics.median(idle):.0f} p90={p90(idle):.0f} | "
          f"biggest-gap med={statistics.median(big):.0f} p90={p90(big):.0f} (us)")


if __name__ == "__main__":
    main()
