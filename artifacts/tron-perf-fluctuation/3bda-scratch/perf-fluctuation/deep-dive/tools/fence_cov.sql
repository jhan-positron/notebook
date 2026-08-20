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
       COUNT(DISTINCT w.win_ix) AS windows_with_it,
       (SELECT COUNT(*) FROM win) AS total_windows
FROM win w JOIN slice s
  ON s.ts >= w.ts AND s.ts < w.ts + w.dur
WHERE s.name NOT IN ('fence 1','fence 3')
GROUP BY s.name ORDER BY windows_with_it ASC;
