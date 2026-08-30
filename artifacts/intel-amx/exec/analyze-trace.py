#!/usr/bin/env python3
# Span attribution for the qwen u8/ctx2048 software-attention trace (P0(a) completion).
from perfetto.trace_processor import TraceProcessor
import sys

TRACE = "/home/jhan/workspace/intel-AMX/exec/results/slot1/qwen-u8-ctx2048-swattn.perfetto-trace"
tp = TraceProcessor(trace=TRACE)

def q(sql):
    return list(tp.query(sql))

# 1. trace bounds
b = q("SELECT min(ts) AS t0, max(ts+dur) AS t1 FROM slice")[0]
wall_ns = b.t1 - b.t0
print(f"trace wall: {wall_ns/1e9:.3f} s")

# 2. top slice names by total duration
print("\n== top spans by total duration ==")
for r in q("""SELECT s.name, count(*) n, sum(s.dur) tot
              FROM slice s GROUP BY s.name ORDER BY tot DESC LIMIT 25"""):
    print(f"{r.tot/1e9:10.3f} s  n={r.n:>9}  {r.name}")

# 3. per-thread busy time for attention-related spans
print("\n== attention-related span totals ==")
for r in q("""SELECT s.name, count(*) n, sum(s.dur) tot
              FROM slice s
              WHERE s.name IN ('Attention Ready','Attention Pending','attention: join',
                               'Rope Q','Rope K','Save V','Save K','Free scratchpads')
              GROUP BY s.name ORDER BY tot DESC"""):
    print(f"{r.tot/1e9:10.3f} s  n={r.n:>9}  {r.name}")

# 4. thread inventory: busy vs wall for threads that ran attention spans
print("\n== attention worker threads: busy share ==")
rows = q("""
  SELECT t.utid utid, t.name tname, sum(s.dur) busy, count(*) n
  FROM slice s JOIN thread_track tt ON s.track_id = tt.id
  JOIN thread t ON tt.utid = t.utid
  WHERE s.depth = 0
  GROUP BY t.utid ORDER BY busy DESC LIMIT 12""")
for r in rows:
    print(f"busy {r.busy/1e9:8.3f} s ({100.0*r.busy/wall_ns:5.1f}% of wall) n={r.n:>8} thread={r.tname}")
tp.close()
