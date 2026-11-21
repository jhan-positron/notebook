# Mesh 0 or mesh 1: where a buffer's lines are homed, cached and read on the CRB

Record of a question-and-answer thread between Jibin Han (questions) and Claude (answers) on 2026-11-09, during the review of Jason DiPietro's deck Phoenix_CRB_Benchmarks_8.pptx for the Propulsion forum. The questions are quoted as asked, lightly trimmed. The answers are not the ones given live. Codex reviewed the first record of the thread the same day and found eight points to correct [codex-review-mesh0-or-mesh1.md]. This version was written again on 2026-11-09 with those corrections built in, and every number was recomputed from the data files.

## Short version

Each 64 B line of a buffer is homed on mesh 0 or mesh 1 by a hash of its physical address, and every measured 2 MiB chunk splits exactly half and half. A core reads a warmed line from a slice on its own mesh whichever mesh homes it, because each home node can also keep copies of lines homed on the other mesh. The 64 MiB that one core reaches is measured, but how a slice divides its space between the two kinds of line, and whether both meshes together hold 128 MiB of distinct data, are not.

## Words used here

- **CRB**: the Arm Phoenix Reference Server at 192.168.2.45, 128 Neoverse V3AE cores at 2.8 GHz, 320 GiB DDR5-8000, two meshes.
- **Mesh**: Arm's Coherent Mesh Network (CMN S3), the on-chip interconnect. The CRB has two. Linux names them arm_cmn_0 (CPUs 0 to 63) and arm_cmn_1 (CPUs 64 to 127).
- **XP**: crosspoint, one router of the mesh grid. Each mesh is 9 columns by 8 rows, 72 XPs.
- **Home node (Arm: HN-S)**: the mesh node that owns an address range. It keeps the coherence record for its lines and holds one slice of the mesh cache. 64 per mesh, two per XP on 32 XPs.
- **Slice**: the 1 MiB piece of the 128 MiB mesh cache inside one home node. 1 MiB is derived (128 MiB divided by 128 home nodes), not read from the machine.
- **Line**: a 64 B cache line. Every address decision below is made per line.
- **Home of a line**: the home node that owns the line's address, chosen by a hash of the physical address.
- **Home line, proxy line**: a home line is a line the node owns (Arm: home-bound transaction, HBT). A proxy line is a copy, kept by a node on the reader's own mesh, of a line homed on the other mesh (Arm: LCN-bound transaction, LBT). The node's proxy role is called the LCN (local coherency node), and the part of a slice holding proxy lines is called the LCC (local coherent cache) [CMN S3 TRM, page 55].
- **Occupancy limit**: a register field that caps the share of a slice that one kind of line may occupy. There is one for home lines and one for proxy lines, and both reset to the maximum [CMN S3 TRM, pages 335 to 336 and 1039]. The deck and the report call it the "capacity partition". Not read on the CRB.
- **Warmed**: a line that an earlier pass left in the mesh cache, so the timed load finds it there.
- **Fresh chain**: a random pointer chain walked once, so the core's prefetcher cannot learn it. A repeated chain reads 5.4 ns per load instead of about 30 ns.
- **Root run**: the 2026-11-02 run of bench/homelat with root. Results in results/sudo-20261102T054936Z/.
- **Brief, full report**: crb-memory-hierarchy-brief.html and crb-memory-hierarchy.html in this directory.
- **CMN S3 TRM**: Arm's Technical Reference Manual for CMN S3, document 107858 issue 05, at refs/arm-cmn-s3-r2p3-trm-107858.pdf. Page numbers below are PDF page numbers.

## Test data referenced

All result paths are under /home/jhan/workspace/titan/cache-perf/crb/results/. The benchmark sources are in /home/jhan/workspace/titan/cache-perf/bench/.

| File | What it holds |
|---|---|
| sudo-20261102T054936Z/full/homes.csv | the home mesh and home node of each of the 524,288 lines of a 32 MiB buffer |
| sudo-20261102T054936Z/full/chunks.csv | per 2 MiB chunk: virtual address, physical frame, lines homed on mesh 0 and on mesh 1 |
| sudo-20261102T054936Z/full/nodes.csv | the 128 home nodes with their XP, port, device and how many lines each owns |
| sudo-20261102T054936Z/full/verify.csv | counter checks on 8 home nodes: accesses and misses at the home while core 0's timed loads ran |
| sudo-20261102T054936Z/full/latency.csv | latency from each of cores 0 to 119 to each of the 128 home nodes, median of 7 fresh chains of 2,048 lines, plus one mixed chain per core |
| sudo-20261102T054936Z/writebw.csv | home-node counters during 1-thread, 4-thread and 14-thread read and write streams |
| sudo-20261102T054936Z/crossmesh.csv | home-node counters during the write-collapse placements |
| followup2-20261031T073513Z/cross.csv | a chain built on one core and walked from a core on the other mesh |
| followup3-20261102T031936Z/perthread-asmread-3M-40.csv | CPU and bandwidth of each of the 40 threads of the whole-chip read |
| followup3-20261102T031936Z/writegrid.csv | DRAM write bandwidth for each count of writers on each mesh |
| cmn-map.txt | the Linux mesh driver's map of both meshes, read with root on 2026-11-01 |

Counter rates per line come from bench/subtract.py. It takes the long run minus the short run, divides by the lines moved, and subtracts the idle background. Both counter files pass its checks ("checks failed: 0", run on 2026-11-09). The chain selection, the eviction and the physical-frame read are in bench/homelat.c, lines 1 to 24 and 176 to 190.

## Two different questions

Most of the confusion in the thread came from mixing two questions.

```
physical address --hash--> home node, fixed per line

load --> where is a usable copy now?
         --> L1 or L2, a slice on the own mesh,
             a slice on the other mesh, or DRAM
```

- The first question has one answer per line. It never changes.
- The second question depends on what happened to the line before. The home address alone does not answer it.

## Question 1. The wording "half of every buffer"

> Slide 3 says "Half of every buffer is homed on the other mesh". Why not say "Half of buffers are homed on the other mesh"? Does "half of every buffer" indicate some address scheme?

Answer. The wording points at the address scheme, but it is too strong for small buffers.

- The home of a line is chosen per 64 B line, by a hash of the physical address.
- Within every 2 MiB chunk, exactly half the lines are homed on each mesh. Measured over 16 chunks: 16,384 of 32,768 lines on each mesh, in every chunk [chunks.csv]. Over the whole 32 MiB buffer: 262,144 of 524,288 lines on each mesh [homes.csv].
- "Half of buffers are homed on the other mesh" says something different. It would mean that each buffer sits on one mesh as a whole, and that the other mesh gets every second buffer.
- The measurements rule that out. Every 2 MiB chunk of the test buffer put 16,384 lines on each mesh, so no chunk sat on one mesh as a whole [chunks.csv].
- "Half of every buffer" fails for small buffers. A 65 B buffer always covers two lines. In 20.0 % of the line positions in the measured buffer, those two lines have the same home mesh. Example: lines 3 and 4 of the buffer, byte offsets 0xC0 and 0x100, are both homed on mesh 1 [homes.csv]. A 65 B buffer at offset 0xC0 is entirely on mesh 1.
- Lines are not bytes. A 65 B buffer at offset 0 puts 64 B in its first line and 1 B in its second.
- Suggested wording for the slide: "Home assignment is per 64 B line. Every measured 2 MiB chunk splits evenly between the two meshes."

## Question 2. The next step "read the CMN capacity-partition registers"

> We did not read the registers in any of the tests? What is the purpose of reading them?

Answer. Correct, no test read them. The report lists it as an open item.

What the registers hold:

- Each slice is one storage shared by two kinds of lines: home lines and proxy lines [CMN S3 TRM, page 55].
- The manual does not describe a split into two parts. It describes a maximum occupancy for each kind, as a 7-bit fraction of the slice, in steps of 0.78 % [CMN S3 TRM, pages 335 to 336].
- The two fields are slc_cmax_allowed for home lines and lcc_cmax_allowed for proxy lines, in register cmn_hns_lbt_cfg_ctl at offset 0xA30. Both reset to 0b1111111, the maximum [CMN S3 TRM, pages 1038 to 1039].
- The same register has hnf_mode (home-only mode) and lcn_mode (proxy-only mode). Both reset to 0b0, the dual-role mode [CMN S3 TRM, page 1039].
- A related bit, slc_way_reserve_dis in register cmn_hns_lbt_aux_ctl at offset 0xA38, controls whether proxy lines may use every way of a set [CMN S3 TRM, pages 1040 to 1041].

Why reading them matters:

- They would show whether the 64 MiB that one core sees (Question 9) comes from a limit or from demand.
- They would show whether every home node is in the dual-role mode on the CRB (Question 8).
- Performance counters cannot show either.

Cost and priority:

- The register is in the Root security space. Root on Linux is not enough on its own, and firmware settings decide whether it can be read [CMN S3 TRM, page 1038]. The firmware team can supply the values instead.
- Jibin said in the slide-prep meeting of 2026-11-09 that this item is not high on the list.

## Question 3. "Half the lines of each slice"

> Would it be more accurate to say "Half the lines of each slice are homed on the other mesh"?

Answer. No. That is a different claim, and it was not measured.

- The buffer statement is about addresses. Half of a large buffer's lines have their home on mesh 0 and half on mesh 1. This was measured over 524,288 lines [homes.csv].
- The slice statement is about contents. A slice holds some home lines and some proxy lines at any moment. The mix depends on the workload and on the occupancy limits. No test counted the contents of a slice.
- Keep the per-line wording from Question 1.

## Question 4. Do consecutive lines really alternate?

> So every consecutive 64 bytes flip between the 2 meshes? Really?

Answer. Nearly. All numbers below were computed from homes.csv on 2026-11-09.

- 80.0 % of neighbouring lines have different home meshes: 419,430 of 524,287 pairs.
- No run of neighbouring lines on one mesh is longer than 2.
- Every pair of lines that starts at a 128 B boundary has opposite homes: 262,144 of 262,144 pairs.
- The rule that reproduces all 524,288 lines with no exception: the home mesh is the XOR of physical address bits 6, 8, 10, 12, 14, 16, 18 and 20, inverted in 4 of the 16 chunks (chunks 3, 5, 6 and 14).
- The first 32 lines read 0101 1010 0101 1010 1010 0101 1010 0101. This is not a 16-line pattern that repeats or alternates. The blocks starting at lines 48 and 64 are identical, both 1010 0101 1010 0101. A carry into a higher address bit flips the parity.
- Why neighbours usually differ: bit 6 is the lowest bit of a line address, and it is in the XOR. Why some neighbours match: when a carry also flips bit 8, or bit 8 and bit 10, the two flips cancel.
- The inversions come from physical address bits above bit 20. A user process cannot see them. A root process can: the root run read the physical frame of each 2 MiB chunk from /proc/self/pagemap and recorded it [chunks.csv, column pfn_hex; bench/homelat.c, function pfn_of]. Which higher bits enter the hash was not worked out from those 16 frames, and 16 samples may not determine it.
- This is normal interconnect design. Spreading neighbouring lines over home nodes keeps any one node from being overloaded. Which of the 64 nodes inside a mesh homes a line is a hash too: each of the 128 nodes owns exactly 4,096 of the 524,288 lines [nodes.csv].

## Question 5. Is the hash related to the capacity partition?

> Is this related to the CMN capacity-partition registers?

Answer. No. They are two different settings.

- The hash is the system address map. It decides which home node owns each line. It is fixed per line.
- The occupancy limits decide how much of a slice each kind of line may fill. They are set by firmware.
- They meet in one place. Half of a large buffer's lines are proxy lines on the reader's mesh. If the proxy limit were below about half a slice, one core would reach less than 64 MiB for one buffer. The measured 64 MiB (Question 9) only shows that neither limit was below about half for that workload (est.). It does not show that the limits are set to half.

## Question 6. A 65-byte buffer, and whether the slide numbers are two-mesh numbers

> I am still confused. Each line is 64 B, so when software creates a buffer of 65 B, the buffer splits between 2 meshes? If so, most latency and bandwidth data in the slides are from 2 meshes, not from the local mesh, because most tests used buffers larger than 64 B, right?

Answer. Two different questions hide here: where a line is homed, and where its bytes come from.

Where it is homed:

- A 65 B buffer always covers two lines. In 80 % of neighbouring pairs the two homes are on different meshes, in 20 % on the same mesh (Question 1).
- "Home" means the node that owns the address. It does not say where the data is read from.

Where a warmed line is read from: a slice on the reader's own mesh, whichever mesh homes it.

- For each of the 120 measured cores, the mean latency to the 64 homes on the other mesh is within 0.44 ns of the mean latency to the 64 homes on its own mesh. The median difference over cores is 0.01 ns [latency.csv].
- While core 0 walked chains of lines homed on mesh 1, those homes counted 0.000 to 0.003 accesses per load. Chains of lines homed on mesh 0 counted 1.00 to 1.04 accesses per load at their homes [verify.csv].
- During an 8 MiB read stream from one core on mesh 0, the mesh 0 home nodes counted 0.827 slice accesses per line and 0.000 misses. The mesh 1 home nodes counted 0.000 [writebw.csv, case asmread-8M-1].

So the cache-hit numbers in the deck are own-mesh numbers, with two qualifications:

- The 30 ns mesh-cache latency and the 67 GB/s one-core read are one core served by its own mesh. The 67 GB/s counts all bytes the core read, and 17 % of its lines came from its own L2, not from a slice [writebw.csv, case asmread-8M-1].
- The whole-chip read of 1.38 TB/s used 40 cores: CPUs 0, 2, ..., 78, that is 32 on mesh 0 and 8 on mesh 1, 3 MiB each. Each core was served by its own mesh, and the total combines both meshes [perthread-asmread-3M-40.csv]. The counters attribute 0.45 slice accesses per line, so about 0.62 TB/s came from slices (est. from counters) with 2.9 % misses, and the rest came from each core's L2 [crb-memory-hierarchy.html, whole-chip read row].
- The heatmap on slide 3 is the one test that separated homes. Each chain used only lines homed at one home node, picked from homes.csv [bench/homelat.c, lines 16 to 22].

Where the other mesh takes part, measured:

```
warmed read, homed on own mesh   -> own-mesh slice      19 to 44 ns
warmed read, homed on other mesh -> own-mesh slice      19 to 44 ns
first read of lines held only by the other mesh         85 to 88 ns
streaming write -> half the requests reach the other mesh's homes
DRAM read or write -> memory requests counted on both meshes
```

- First touch of lines that only the other mesh's slices hold: 84.9 to 88.5 ns per load at 16 MiB in the four cross placements, against 29.0 to 29.3 ns when a core walks a chain built on its own mesh [cross.csv]. Question 9 has the detail.
- The one-thread 8 MiB write stream: the mesh 0 home nodes counted 0.764 slice accesses, 0.753 misses and 0.013 fills per line. The mesh 1 home nodes counted 0.382 accesses and 0.377 misses per line [writebw.csv, case asmwrite-8M-1]. So the tested stream was not kept in the mesh cache, and about half of its requests reached homes on the other mesh. The counts are events, not distinct lines. A request can be counted at a node on the writer's mesh and again at its home.
- A DRAM-bound read: 14 cores on mesh 0 reading 1 GiB each. Mesh 0 home nodes received 1.000 read requests per line and mesh 1 home nodes 0.499 [writebw.csv, case asmread-1G-14]. Every line was requested at a node on the readers' mesh, and the lines homed on mesh 1 were requested again at their home.
- DRAM writes: with 64 writers on mesh 0, the mesh 0 home nodes counted 1.142 memory-request events per line to local memory and the mesh 1 home nodes 0.512 to remote memory [crossmesh.csv, case cross-asmwrite-0-63]. The 394 GB/s of that placement fell to 173 GB/s with 32 writers on each mesh [writegrid.csv]. These counts are events, not distinct lines, for the same reason as above.

In short: the mesh-cache hit numbers are own-mesh numbers. First touches, streaming writes and DRAM traffic involve both meshes.

## Question 7. A 128-byte buffer at address 0

> Say a buffer of 128 B at address 0x0 to 0x80. It crosses 2 cache lines, so the first 64 bytes are located at mesh 0 and the second 64 bytes at mesh 1. Is this right?

Answer. Almost. Three corrections.

Byte ranges:

- A 128 B buffer at 0x0 spans 0x00 to 0x7F. The first line is 0x00 to 0x3F, the second is 0x40 to 0x7F.

Which mesh is which:

- The two lines differ only in address bit 6, and bit 6 is in the hash. So the two lines of any pair that starts at a 128 B boundary are homed on different meshes: 262,144 of 262,144 pairs in the measured buffer [homes.csv].
- Which of the two goes to mesh 0 depends on higher bits of the physical address. In 4 of the 16 measured chunks the assignment was inverted [chunks.csv]. A user process cannot see those bits. A root process can read them from /proc/self/pagemap, as the root run did.

"Located at" means homed, not stored:

```
buffer 0x00..0x7F, read by a mesh 0 core, after L2 evicts it

line 0 (0x00..0x3F)  home: one mesh    copy: a mesh 0 slice
line 1 (0x40..0x7F)  home: other mesh  copy: a mesh 0 slice (proxy)
```

- A line the core is using sits in its L1 or L2.
- The mesh cache does not usually hold a copy at the same time. Arm's allocation policy is exclusive for data lines: a line goes into a slice when L2 evicts it [CMN S3 TRM, pages 54 to 55]. The counters agree: the 8 MiB read stream counted 0.828 fills per 0.827 accesses, so each slice read took the line out and the following L2 eviction put it back [writebw.csv, case asmread-8M-1].
- After eviction, both lines sit in slices on the reader's own mesh: line 0 in its home slice if its home is mesh 0, otherwise in a proxy slice, and the opposite for line 1. This is measured for warmed reads (Question 6).
- The home on the other mesh keeps the coherence record for its line. Whether it also keeps the data is not measured (Question 9).
- Which chiplet's DRAM channels hold each line was not resolved by our counters. Memory-request events appear on both meshes, and one request can be counted at more than one node [crb-memory-hierarchy.html, section "Who reads, who provides"].

## Question 8. Is one slice per XP the proxy?

> An XP has two 1 MiB slices, so very likely one slice is for local cores (cores on the same mesh) and the other is the proxy slice, right? Also, each mesh has many proxy slices, correct?

Answer. No. Both slices on an XP are homes, and the proxy role lives inside each home node. Whether every node plays that role on the CRB is not verified.

What is measured:

- Every one of the 128 home nodes owns exactly 4,096 of the 524,288 lines of the test buffer [nodes.csv]. A node that only served as a proxy would own no addresses.
- Proxies are active on the CRB. Lines homed on the other mesh were read at own-mesh latency, 19 to 44 ns, while their homes counted 0.000 to 0.003 accesses per load [latency.csv, verify.csv].
- The two slices on CPU 0's own XP read 19.18 ns and 22.39 ns [latency.csv, core 0, XP (1,2), devices 0 and 1]. Both are homes. The difference is unexplained. Hypothesis: port arbitration in the shared XP port, or the physical placement of the two nodes. Not measured.

What the manual says:

- A mesh has 64 home nodes but only 32 XPs with a home-node port. Arm's Component Aggregation Layer (CAL) lets two identical devices share one XP port, as two cores share one core port [CMN S3 TRM, section 2.1.1.15, page 63; cmn-map.txt].
- Each home node has a dual function: home (Arm: HN-F) for addresses it owns, and proxy (Arm: LCN) for addresses homed on the other chip. One slice serves both roles [CMN S3 TRM, page 55].
- The dual role is the reset state, and a node can be put into home-only mode with hnf_mode or proxy-only mode with lcn_mode [CMN S3 TRM, page 1039].

What stays a hypothesis:

- That all 64 nodes of a mesh serve proxy lines on the CRB. The counters identified which homes were not accessed, not which local nodes served the lines. A test would need proxy-request counters per node, or the configured mapping from the firmware team.
- Which local node serves which remote home. The latency data shows a spatial pattern: for each core, the latency to a home on the other mesh is anti-correlated with the latency to the same-numbered node on its own mesh, median correlation over the 120 cores minus 0.74, range minus 0.83 to plus 0.20 [latency.csv]. That fits a mirror-image mapping between two identical chiplets. It does not identify any proxy directly.

## Question 9. Is the useful capacity 64 MiB or 128 MiB?

> So even though there are 128 MB in total, it is possible the total cached data is 64 MB because half of the mesh cache is used as proxy, right?

Answer. One core sees 64 MiB, and that is measured. The rest of the statement is a hypothesis.

What is measured:

- One core reading one buffer starts missing in the mesh cache at 64 MiB (11 % of loads) and misses 81 % at 96 MiB [crb-memory-hierarchy.html, section "Effective capacity is 64 MiB for one buffer"].
- Half of that buffer's lines are homed on the other mesh (Question 1). They were served from the reader's own mesh (Question 6). So the 64 MiB is one mesh's 64 slices holding both home lines and proxy lines for that core, at 1 MiB per slice (est.).

What the 64 MiB does not show:

- It does not show a fixed half-and-half split of each slice. Home and proxy lines share a slice under separate occupancy limits (Question 2). A buffer whose lines are half and half fills a slice half and half by demand, whatever the limits allow. The only inference: neither limit was below about half for that workload (est.).
- It does not show the capacity of the whole chip. That needs cores on both meshes working at the same time, which the single-buffer test did not do.

Hypotheses about the whole chip, with the test that would settle each:

- Separate working sets on the two meshes could reach up to 128 MiB of distinct data, because each mesh would cache only what its own cores use. Test: two working sets of about 40 MiB, one per mesh, walked at the same time by cores of that mesh only, with the miss counters on. More than 64 MiB of distinct data without misses would confirm it for that size. Larger sets would be needed to approach 128 MiB. Not run.
- A working set shared by both meshes may be held twice, once per mesh, or may move to the mesh that read it last. Test: alternate fresh walks from a core on each mesh over the same lines, with the home-node counters on and the private caches flushed between walks. Not run.
- With only one mesh's cores active, the other mesh's slices may hold nothing useful. Same test as above, from the other side: whether the home-side slices keep data for lines that only the other mesh reads.

What the cross-mesh test does and does not show:

- Core 3 on mesh 0 built and walked a 16 MiB chain: 29.277 ns per load, then 29.034 ns on a second fresh walk. Core 67 on mesh 1 then walked the same lines: 86.053 ns per load on the first walk and 32.134 ns on the second [cross.csv]. The other three cross placements (67 to 3, 64 to 3, 3 to 119) gave 84.9 to 88.5 ns, then 31.7 to 33.2 ns.
- Shown: on the first cross walk, no usable copy was found on the reader's mesh. Half of those lines are homed on mesh 1, so their homes did not supply them at own-mesh speed.
- Not shown: what the mesh 1 homes held. Hits at the homes were not counted, and the test did not return to core 3. About one eighth of the lines were also still in core 3's L2, and the 86 ns mixes two cases: a proxy miss with the data at the remote home, and a home miss with the data in the remote proxy [crb-memory-hierarchy.html, section "A first read of lines cached on the other chiplet costs 85 ns"].

What follows for host software: keep a thread's data on its own mesh. A first touch of data held by the other mesh costs about 57 ns more per load (86 against 29 ns, measured), and writers spread over both meshes halve the DRAM write bandwidth (394 to 173 GB/s, measured).

## Not yet measured

- The occupancy limits and mode bits of the home nodes: register cmn_hns_lbt_cfg_ctl at offset 0xA30 and cmn_hns_lbt_aux_ctl at offset 0xA38 [CMN S3 TRM, pages 1038 to 1041]. They are in the Root security space, so root on Linux may not be enough. The firmware team can supply them.
- The distinct capacity of the whole chip: the two-working-set test of Question 9.
- Whether a line read by both meshes stays in both or moves: the alternating-walk test of Question 9.
- Which local node serves as proxy for which remote home: proxy-request counters per node, or the configured mapping.
- Which physical address bits above bit 20 enter the home hash: fit candidate bit sets to the 16 recorded physical frames [chunks.csv]. More chunks may be needed.
- Why the two slices on one XP differ by 3 ns from the core on that XP.

## What stands as measured, and what as hypothesis

Measured:

- The home of each 64 B line is set by an address hash. Every measured 2 MiB chunk splits exactly half and half. 80.0 % of neighbouring lines have different homes, and no run on one mesh is longer than 2 lines [homes.csv, chunks.csv].
- All 128 home nodes own addresses, 4,096 lines each [nodes.csv].
- Warmed lines homed on the other mesh are read at own-mesh latency, 19 to 44 ns, with 0.000 to 0.003 accesses per load counted at their home [latency.csv, verify.csv].
- One core reading one buffer starts missing in the mesh cache at 64 MiB [crb-memory-hierarchy.html].
- The first walk from the other mesh over a 16 MiB chain costs 85 to 88 ns per load, the second 32 to 33 ns [cross.csv].
- The one-thread 8 MiB write stream kept almost nothing in the mesh cache, 0.013 fills per line, and about half of its requests were counted at homes on the other mesh [writebw.csv].
- The whole-chip read combined 32 readers on mesh 0 and 8 on mesh 1, each served by its own mesh [perthread-asmread-3M-40.csv].

Hypothesis:

- How each slice's space is divided between home and proxy lines on the CRB.
- Whether the chip holds 128 MiB of distinct data when both meshes work, and whether shared lines stay in both meshes or move to the last reader.
- That every home node serves proxy lines, and which local node serves which remote home.
- Which physical address bits above bit 20 enter the home hash.

## Review history

- 2026-11-09, first record: the answers as given live in the thread.
- 2026-11-09, Codex review [codex-review-mesh0-or-mesh1.md]: eight points, all accepted.
  - The occupancy limits are not a fixed half-and-half split.
  - The 128 MiB distinct capacity and the duplication of shared lines are hypotheses.
  - "Half of every buffer" fails for small buffers.
  - The 16-line pattern does not repeat, and root can read physical frames.
  - The whole-chip read combines both meshes.
  - Local service does not mean a copy at every level.
  - The write conclusion holds only for the tested stream.
  - Both nodes on an XP being homes does not prove that every node serves proxy lines.
- 2026-11-09, this version: written again from the corrected reasoning. Every number recomputed from the files in the table above and checked against the manual pages cited.
