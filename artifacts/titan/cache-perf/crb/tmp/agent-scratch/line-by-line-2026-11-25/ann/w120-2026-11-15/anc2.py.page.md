## Short version: purpose

`anc2.py` reads one result folder of the counter script `rc2.sh`, taken with the event sets of `sets2.txt`. Its first part prints, per process and per 64 B line read, the request, data and response flits at the 24 memory ports. Its second part prints the scan of the event numbers 0 to 39 of the 48 memory controller counters.

## Words used here

- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0 to 63 sit on mesh 0. CPUs 64 to 127 sit on mesh 1.
- **Runner**: a benchmark program that times a sequence of kernels in one process and prints one row per thread. The versions are named `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12` and `bwx13`.
- **Process**: one start of a benchmark binary.
- **Interval**: one timed measurement inside a process.
- **Rate**: bytes divided by time, in GB/s.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **`arm_cmn_0`, `arm_cmn_1`**: the counter devices of mesh 0 and of mesh 1. The digit in the name is the mesh number.
- **Event set**: one line of `sets2.txt`: a set name and the events that one counter window counts together.
- **Counter window**: the time for which one `perf stat` command of `rc2.sh` counts one event set. Its counts stand in one file `TAG.SET.perf`.
- **Tag**: the name of a process in the spec file. It is the first part of the names of its output files.
- **`I` row**: the row that the runner prints for one interval. Its last field is the total rate in GB/s: the bytes of all threads divided by the longest thread time.
- **Flit**: one unit of traffic on the mesh. The mesh moves requests, responses and data as flits.
- **Memory port**: a place where a mesh hands requests to the memory and takes data back. `sets2.txt` names 12 of them per mesh.
- **Watchpoint**: a counter event that counts the flits of one channel at one device port. Its text holds `wp_chn_sel=` with the channel number.
- **Memory controller counters**: the 48 counter devices `arm_cspmu_mc_0` to `arm_cspmu_mc_47`.
- **Line**: one cache line, 64 B.

## Main flow

1. Take the folder from the argument, the tags from the `launch` lines of `launches.txt`, and the rate of each process from the `I` rows of its CSV file ({L4-9}).
2. Define the function `rows`, which reads the data rows of one `.perf` file ({L10-14}).
3. Part 1: for each of the five memory port sets and each process, read the counter file. Divide each count by the number of lines of the process in the run time of the counter, and sum per event and per mesh ({L16-28}).
4. Print one line per set and process ({L29}).
5. Part 2: for each event number from 0 to 39 and each process, read the file of the set `mcKK` and sum the counts per line over the 48 devices ({L30-39}).
6. Print the line of an event number when a process has a sum above 0 ({L40}).

## Behavior a reader must know

- The script times nothing. The rate comes from the last field of an `I` row. The count, the run time of the counter and the percentage come from a row of a `.perf` file.
- The number of lines is an estimate: the mean rate of the whole interval times the run time of the counter. The script does not know how many bytes were read inside the window.
- Every count is divided by the lines of all threads of the process, on both meshes.
- The set names are fixed in the script: `snreq`, `snwdat`, `snrdat`, `snmesh`, `snrsp` and `mc00` to `mc39`. A folder without one of these files stops the script with an error.
- A row that `perf` could not count is not added to a sum. Part 1 shows the number of such rows under a name with `_NS`. Part 2 shows it after `ns`.
