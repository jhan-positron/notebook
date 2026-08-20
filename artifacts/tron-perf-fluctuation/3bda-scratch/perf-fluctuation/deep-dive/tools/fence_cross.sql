CREATE PERFETTO TABLE fence_seq AS
SELECT ts, name,
       LEAD(ts) OVER (ORDER BY ts) AS next_ts,
       LEAD(name) OVER (ORDER BY ts) AS next_name
FROM slice WHERE name IN ('fence 1','fence 3');
CREATE PERFETTO TABLE win AS
SELECT ROW_NUMBER() OVER (ORDER BY ts) AS win_ix,
       ts, next_ts - ts AS dur
FROM fence_seq WHERE name = 'fence 1' AND next_name = 'fence 3';
SELECT s.name,
       SUM(s.ts < w.ts AND s.ts + s.dur <= w.ts + w.dur) AS f1_cross_end_inside,
       SUM(s.ts + s.dur > w.ts + w.dur) AS f3_cross,
       COUNT(*) AS crossing_pairs
FROM win w JOIN slice s
  ON s.dur > 0
 AND s.ts + s.dur >= w.ts
 AND s.ts < w.ts + w.dur
 AND (s.ts < w.ts OR s.ts + s.dur > w.ts + w.dur)
GROUP BY s.name ORDER BY crossing_pairs DESC;
