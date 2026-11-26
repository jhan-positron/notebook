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

1. Read the rows of `full/latency.csv` of the result folder, without the rows of the mixed set, and sort the median latencies by core and home node ({L10-15}).
2. Define the helper `fit`, a least squares fit of a straight line ({L16-20}).
3. For each core and each mesh: reduce the two home nodes of a crosspoint to the smaller latency. Then fit each of the 35 candidates and keep the candidate with a slope above 0 and the smallest error ({L21-34}).
4. Compute for each core the largest latency on its fitted mesh, and write `core-positions.json` ({L35-36}).
5. Print a summary: cores on an unexpected mesh, pairs of CPUs on one crosspoint, the number of crosspoints in use, four named cores, and the range of the slope and of the error ({L37-42}).

## Behavior a reader must know

- The input number is the column `ns_median` of `latency.csv`: the median of the timed passes of `homelat` for one core and one home node, in ns per load.
- The position of a core is a result of a fit. It is not read from the hardware. The output marks every position with `inferred`.
- The mesh of a core is also a result of the fit: the mesh whose best candidate has the smaller error wins.
- The candidates are the columns 1 to 7 and the rows 1 to 5, so 35 positions per mesh.
- The fitted slope is the latency per hop in ns. The intercept is the latency at the distance 0.
- The script writes one file, `core-positions.json`, into the result folder that it reads from. An old file of that name is replaced.
- The script has no check of its input. A missing file or a core without a candidate with a slope above 0 stops it with a Python error.

## References

- [Ref1] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-10-30-memory-hierarchy/report/plan-2026-11-02.md`: the plan note of 2026-11-02. Its section "State at 04:45 UTC" says that the cores 34, 35, 98 and 99 fit the crosspoint (4,5), which has a core port but no slice.
