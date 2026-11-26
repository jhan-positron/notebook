# `fitpos.py` explained, line by line

- Source file: `bench/fitpos.py` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Python script, 42 lines, 3043 bytes).
- sha256 of the source when this page was built: `b38a39ea158ee2df7171a53ea6f1aadd9d6b5130d20949cebfef4500f8605691`.

## Short version: purpose

`fitpos.py` reads the latency matrix that `homelat` wrote and infers at which crosspoint of the mesh each core sits. For each core it tries 35 candidate positions on each of the two meshes and keeps the one for which the latency grows most exactly as a straight line with the distance to the home nodes. It writes the positions to the file `core-positions.json` and prints a summary.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0 to 63 sit on mesh 0. CPUs 64 to 127 sit on mesh 1.
- **Mesh**: the network inside one half of the chip. It connects the cores, the SLC and the memory.
- **SLC**: the system level cache, the last cache level (L3) of the chip. All cores of a mesh share it.
- **Crosspoint**: a junction of the mesh, named by its column `x` and its row `y`. Cores and home nodes are connected to the ports of a crosspoint.
- **Home node**: a node of the mesh that owns a part of the memory addresses and holds one part of the SLC.
- **Slice**: the part of the SLC that one home node holds.
- **`homelat`**: the program built from `homelat.c`. Its file `latency.csv` holds one row per core and home node, with the median latency in ns per load.
- **Latency matrix**: the rows of `latency.csv`: for each core, the latency to each home node.
- **Mixed set**: a set with lines of every home node. Its rows in `latency.csv` have `mixed` in the column `node_id_hex`.
- **Manhattan distance**: the difference of the columns plus the difference of the rows of two crosspoints, both taken without a sign.
- **Hop**: one step from a crosspoint to a neighbour crosspoint.
- **Least squares fit**: the straight line for which the sum of the squared differences to the points is smallest.
- **Intercept, slope**: the two numbers of a straight line: its value at the distance 0, and its rise per unit of distance.
- **Root-mean-square error**: the square root of the mean squared difference between the measured latencies and the line.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **JSON**: a text format for structured data.

## Main flow

1. Read the rows of `full/latency.csv` of the result folder, without the rows of the mixed set, and sort the median latencies by core and home node (lines 10 to 15).
2. Define the helper `fit`, a least squares fit of a straight line (lines 16 to 20).
3. For each core and each mesh: reduce the two home nodes of a crosspoint to the smaller latency. Then fit each of the 35 candidates and keep the candidate with a slope above 0 and the smallest error (lines 21 to 34).
4. Compute for each core the largest latency on its fitted mesh, and write `core-positions.json` (lines 35 to 36).
5. Print a summary: cores on an unexpected mesh, pairs of CPUs on one crosspoint, the number of crosspoints in use, four named cores, and the range of the slope and of the error (lines 37 to 42).

## Behavior a reader must know

- The input number is the column `ns_median` of `latency.csv`: the median of the timed passes of `homelat` for one core and one home node, in ns per load.
- The position of a core is a result of a fit. It is not read from the hardware. The output marks every position with `inferred`.
- The mesh of a core is also a result of the fit: the mesh whose best candidate has the smaller error wins.
- The candidates are the columns 1 to 7 and the rows 1 to 5, so 35 positions per mesh.
- The fitted slope is the latency per hop in ns. The intercept is the latency at the distance 0.
- The script writes one file, `core-positions.json`, into the result folder that it reads from. An old file of that name is replaced.
- The script has no check of its input. A missing file or a core without a candidate with a slope above 0 stops it with a Python error.

## Source and explanation, line by line

- Text shown: the file `bench/fitpos.py` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (42 lines, 3043 bytes, sha256 `b38a39ea158ee2df7171a53ea6f1aadd9d6b5130d20949cebfef4500f8605691`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### Description text and imports (lines 1 to 9)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env python3` | Tells Linux to run this file with `python3`. The tool `env` finds `python3` in the search path of the user. |
| 2 | `"""fitpos.py - infer each core's crosspoint from homelat's latency matrix.` | Starts the description text of the file. The script infers the crosspoint of each core from the latency matrix of `homelat`. A crosspoint is a junction of the mesh, the network that connects the cores, the last cache level and the memory. The matrix is the file `latency.csv` with one row per core and home node. |
| 3 | `For each core and each candidate core-port crosspoint (every crosspoint with an RN-F port in the` | Text of the description: the fit runs for each core and each candidate crosspoint. A candidate is a crosspoint with a core port. `RN-F` is the Arm name of the node type of a core. The sentence goes on in line 4. |
| 4 | `map: rows 1 to 5, columns 1 to 7, including the three without slices), fit` | Text of the description: by the map of the mesh these are the rows 1 to 5 and the columns 1 to 7. Three of them have no slices. A slice is the part of the last cache level that a home node holds. |
| 5 | `  latency(slice) = intercept + slope * manhattan(candidate, slice)` | Text of the description: the model of the fit. The latency to a slice is an intercept plus a slope times the Manhattan distance from the candidate to the slice. |
| 6 | `over the 64 slices of each mesh (the smaller of the two slice medians per crosspoint), slope > 0,` | Text of the description: the fit runs over the 64 slices of each mesh. For each crosspoint it takes the smaller one of the two slice medians. The slope must be above 0. |
| 7 | `and keep the candidate and mesh with the smallest root-mean-square error. The result is an` | Text of the description: the script keeps the candidate and the mesh with the smallest root-mean-square error. The next sentence starts here: the result is an ... |
| 8 | `inferred position. Usage: fitpos.py <results dir with full/latency.csv> -> core-positions.json"""` | Text of the description: ... inferred position. The usage: the argument is a result folder that holds `full/latency.csv`. The output is the file `core-positions.json`. This line ends the description text. |
| 9 | `import csv, json, sys, statistics as st, collections` | Loads five standard modules: `csv` (read CSV files), `json` (write JSON), `sys` (arguments), `statistics` under the short name `st` (the median) and `collections` (`defaultdict` and `Counter`). |

### The input and the function `fit` (lines 10 to 20)

| Line | Source | Explanation |
|---:|---|---|
| 10 | `R = sys.argv[1]` | `R`: the result folder, the first argument of the script. |
| 11 | `CANDIDATES = [(x, y) for y in range(1, 6) for x in range(1, 8)]` | `CANDIDATES`: the 35 candidate positions: every pair of a column `x` from 1 to 7 and a row `y` from 1 to 5. The list expression builds them row by row. |
| 12 | `rows = [r for r in csv.DictReader(open(f'{R}/full/latency.csv')) if r['node_id_hex'] != 'mixed']` | `rows`: the rows of the file `full/latency.csv` in the result folder. `csv.DictReader` gives each row as a dictionary by column name. The rows of the mixed set (`mixed` in the column `node_id_hex`) are left out. |
| 13 | `L = collections.defaultdict(dict)` | `L`: a dictionary that holds one inner dictionary per core. |
| 14 | `for r in rows:` | Loop over the rows. |
| 15 | `    L[int(r['core'])][(int(r['mesh']), int(r['x']), int(r['y']), int(r['dev']))] = float(r['ns_median'])` | Stores the median latency of the row (column `ns_median`, in ns per load) for its core. The key is the home node: its mesh, its column `x`, its row `y` and its device number. |
| 16 | `def fit(pts):` | Starts the function `fit`. It fits a straight line through a list of points by least squares. A point is a pair of a distance and a latency. |
| 17 | `    n = len(pts); mx = sum(p[0] for p in pts) / n; my = sum(p[1] for p in pts) / n` | `n`: the number of points. `mx`: the mean of the distances. `my`: the mean of the latencies. |
| 18 | `    sxx = sum((p[0] - mx) ** 2 for p in pts); sxy = sum((p[0] - mx) * (p[1] - my) for p in pts)` | `sxx`: the sum of the squared differences between each distance and `mx`. `sxy`: the sum of the products of the difference of the distance and the difference of the latency. |
| 19 | `    b = sxy / sxx; a = my - b * mx` | `b`: the slope of the line, `sxy / sxx`, in ns per unit of distance. `a`: the intercept, the latency of the line at the distance 0. |
| 20 | `    return a, b, (sum((v - (a + b * d)) ** 2 for d, v in pts) / n) ** 0.5` | Returns the intercept, the slope and the root-mean-square error: the square root of the mean squared difference between a measured latency and the line. |

### Fit every candidate crosspoint for every core (lines 21 to 34)

| Line | Source | Explanation |
|---:|---|---|
| 21 | `pos = {}` | `pos`: the result: one entry per core. |
| 22 | `for core, d in L.items():` | Loop over the cores. `d` holds the latencies of the core to all home nodes. |
| 23 | `    best = None` | `best`: the best candidate of this core so far. |
| 24 | `    for m in (0, 1):` | Loop over the two meshes. The core is fitted against the home nodes of mesh 0 and against those of mesh 1. |
| 25 | `        v = {}` | `v`: one latency per crosspoint of this mesh. |
| 26 | `        for (mm, x, y, dv), val in d.items():` | Loop over the home nodes of the core. |
| 27 | `            if mm == m: v[(x, y)] = min(v.get((x, y), 99), val)` | For a home node of this mesh: keeps under its crosspoint `(x, y)` the smaller value. A crosspoint holds two home nodes (device 0 and device 1), so the smaller one of their two medians remains. The start value is 99. So a latency above 99 ns would enter as 99. |
| 28 | `        for (cx, cy) in CANDIDATES:` | Loop over the 35 candidates. |
| 29 | `            pts = [(abs(x - cx) + abs(y - cy), val) for (x, y), val in v.items()]` | `pts`: the points for the fit: for each crosspoint with home nodes, the Manhattan distance to the candidate and the latency. The Manhattan distance is the difference of the columns plus the difference of the rows, both taken without a sign. It is the number of steps between two crosspoints of the mesh, which the script calls hops. |
| 30 | `            a, b, res = fit(pts)` | Fits the line (`fit`): `a` is the intercept, `b` the slope and `res` the error. |
| 31 | `            if b <= 0: continue` | Skips a candidate whose slope is 0 or below: the latency must grow with the distance. |
| 32 | `            if best is None or res < best[0]: best = (res, m, cx, cy, a, b, min(v.values()))` | Keeps the candidate when it is the first one or has a smaller error than the best so far. It keeps the error, the mesh, the position, the intercept, the slope and the smallest latency of this mesh. |
| 33 | `    res, m, cx, cy, a, b, near = best` | Takes the values of the best candidate of the core, over both meshes. |
| 34 | `    pos[core] = dict(mesh=m, x=cx, y=cy, nearest=near, per_hop=b, intercept=a, resid=res, inferred=True)` | Stores the result of the core: the mesh, the position `x` and `y`, the smallest latency (`nearest`), the slope (`per_hop`, in ns per hop), the intercept, the error (`resid`, in ns) and the flag `inferred`. |

### Write the JSON file and print a summary (lines 35 to 42)

| Line | Source | Explanation |
|---:|---|---|
| 35 | `far = [max(val for k, val in d.items() if k[0] == pos[c]['mesh']) for c, d in L.items()]` | `far`: for each core, the largest median latency among the home nodes of the mesh that the fit chose for the core. |
| 36 | `json.dump(dict(method=__doc__, candidates=CANDIDATES, pos={str(c): p for c, p in pos.items()}, far=far), open(f'{R}/core-positions.json', 'w'), indent=1)` | Writes the file `core-positions.json` into the result folder: the description text of this file as `method`, the candidates, the results by core number, and the list `far`. `indent=1` puts every entry on a line of its own. |
| 37 | `print('cores', len(pos), 'mesh disagrees with 0-63 split:', [c for c, p in pos.items() if (c < 64) != (p['mesh'] == 0)])` | Prints the number of cores. Then prints the list of the cores whose fitted mesh does not follow the rule that the CPUs below 64 sit on mesh 0 and the others on mesh 1. |
| 38 | `print('pairs on one crosspoint:', sum(1 for c in range(0, 120, 2) if c + 1 in pos and (pos[c]['mesh'], pos[c]['x'], pos[c]['y']) == (pos[c + 1]['mesh'], pos[c + 1]['x'], pos[c + 1]['y'])), 'of 60')` | Prints how many pairs of neighbour CPUs were fitted to the same crosspoint of the same mesh, of 60. A pair is an even CPU from 0 to 118 and the next CPU. |
| 39 | `cnt = collections.Counter((p['mesh'], p['x'], p['y']) for p in pos.values())` | `cnt`: for each fitted crosspoint, the number of cores on it. |
| 40 | `print('crosspoints used', len(cnt), 'max cores per crosspoint', max(cnt.values()))` | Prints the number of different crosspoints in use and the largest number of cores on one crosspoint. |
| 41 | `for c in (34, 35, 98, 99): print(' core', c, (pos[c]['x'], pos[c]['y']), 'resid %.3f' % pos[c]['resid'])` | Prints, for the cores 34, 35, 98 and 99, the fitted position and the error with 3 decimals. The plan note of 2026-11-02 names these four cores as a special case: they fit a crosspoint that has a core port and no slice [Ref1]. |
| 42 | `print('per hop ns min/med/max: %.2f %.2f %.2f; resid med/max: %.2f %.2f' % (min(p['per_hop'] for p in pos.values()), st.median(p['per_hop'] for p in pos.values()), max(p['per_hop'] for p in pos.values()), st.median(p['resid'] for p in pos.values()), max(p['resid'] for p in pos.values())))` | Prints the smallest, the median and the largest slope in ns per hop, and then the median and the largest error, each with 2 decimals. |

## References

- [Ref1] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-10-30-memory-hierarchy/report/plan-2026-11-02.md`: the plan note of 2026-11-02. Its section "State at 04:45 UTC" says that the cores 34, 35, 98 and 99 fit the crosspoint (4,5), which has a core port but no slice.
