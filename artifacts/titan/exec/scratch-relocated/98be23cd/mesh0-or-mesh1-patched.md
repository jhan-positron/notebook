# Mesh 0 or mesh 1: where a buffer's lines are homed, cached and read on the CRB

Record of a question-and-answer thread between Jibin Han (questions) and Claude (answers) on 2026-11-09, while reviewing Jason DiPietro's deck Phoenix_CRB_Benchmarks_8.pptx for the Propulsion forum. The questions are quoted as asked, lightly trimmed. The answers are condensed from the thread and cite the test data they rest on.

## Short version

Every buffer's 64 B lines are homed on one mesh or the other by an address hash, exactly half and half in every measured 2 MiB chunk. A core reads lines homed on either mesh from slices on its own mesh, because each home node also acts as a proxy for lines homed on the other mesh. Home and proxy lines share each slice's storage under occupancy limits that were not read, so the 64 MiB that one mesh's cores reached in the single-buffer test is measured, and the chip's capacity with both meshes busy is not.

The answers below are recorded as given on 2026-11-09. Codex reviewed them the same day and found eight points to correct or soften. Each affected answer carries a "Correction after review" note, and the full review and responses are at the end.

## Words used here

- **CRB**: the Arm Phoenix Reference Server at 192.168.2.45, 128 Neoverse V3AE cores at 2.8 GHz, 320 GiB DDR5-8000, two meshes.
- **Mesh**: Arm's Coherent Mesh Network (CMN S3), the on-chip interconnect. The CRB has two, which Linux names arm_cmn_0 (CPUs 0 to 63) and arm_cmn_1 (CPUs 64 to 127).
- **XP**: crosspoint, one router of the mesh grid. Each mesh is 9 columns by 8 rows, 72 XPs.
- **Home node (HN-S)**: the mesh node that owns an address range. It keeps the coherence record for its lines and holds one slice of the mesh cache. 64 per mesh, two per XP on 32 XPs.
- **Slice**: the 1 MiB piece of the 128 MiB mesh cache inside one home node. 1 MiB is derived (128 MiB divided by 128 home nodes), not read from the machine.
- **Line**: a 64 B cache line. Every address decision below is made per line.
- **Home of a line**: the home node that owns the line's address, chosen by a hash of the physical address.
- **Proxy (Arm: LCN, LCC)**: the role a home node plays for lines homed on the other mesh. It keeps a copy for the cores of its own mesh. Arm calls the role LCN (local coherency node) and the part of the slice it uses LCC (local coherent cache) [CMN S3 TRM, page 55 and page 1216].
- **Capacity partition**: the configuration setting that divides a slice between the lines it homes and its proxy copies [CMN S3 TRM, pages 335 to 336]. Not read on the CRB.
- **Fresh chain**: a random pointer chain walked once, so the core's prefetcher cannot learn it. A repeated chain reads 5.4 ns instead of about 30 ns.
- **Root run**: the 2026-11-02 run of bench/homelat with root, results in results/sudo-20261102T054936Z/.
- **Brief, full report**: crb-memory-hierarchy-brief.html and crb-memory-hierarchy.html in this directory.

## Test data referenced

All paths are under /home/jhan/workspace/titan/cache-perf/crb/results/.

| File | What it holds |
|---|---|
| sudo-20261102T054936Z/full/homes.csv | the home mesh and home node of each of the 524,288 lines of a 32 MiB buffer |
| sudo-20261102T054936Z/full/chunks.csv | per 2 MiB chunk: virtual address, physical frame, lines homed on mesh 0 and on mesh 1 |
| sudo-20261102T054936Z/full/nodes.csv | the 128 home nodes with their XP, port and how many lines each owns |
| sudo-20261102T054936Z/full/verify.csv | counter checks on 8 slices: accesses and misses at the home while the timed loads ran |
| sudo-20261102T054936Z/full/latency.csv | latency from each of cores 0 to 119 to each of the 128 home nodes, 7 fresh chains each |
| sudo-20261102T054936Z/writebw.csv | home-node counters during one-thread and 14-thread read and write streams |
| sudo-20261102T054936Z/crossmesh.csv | home-node counters during the write-collapse placements |
| followup2-20261031T073513Z/cross.csv | a chain built on one core and walked from a core on the other mesh |
| cmn-map.txt | the Linux mesh driver's map of both meshes, read with root on 2026-11-01 |

## Question 1. The wording "half of every buffer"

> Slide 3 says "Half of every buffer is homed on the other mesh". Why not say "Half of buffers are homed on the other mesh"? Does "half of every buffer" indicate some address scheme?

Answer. Yes, the wording is deliberate, and it states the address scheme.

- The home mesh of each 64 B line is a hash of its physical address: the XOR of address bits 6, 8, 10 ... 20 and some higher bits.
- Within every 2 MiB chunk, exactly half the lines are homed on each mesh. Measured over 16 chunks: 16,384 of 32,768 lines on each mesh, every chunk [chunks.csv].
- So every buffer, whatever its size, is split line by line between the two meshes.
- "Half of buffers are homed on the other mesh" would mean whole buffers live on one mesh. That was the earlier hypothesis in the report, and the root run showed it was wrong [crb-memory-hierarchy.html, section "Lines homed on the other mesh are served by a local proxy"].
- Clearer wording for the slide: "Half the lines of every buffer are homed on the other mesh."

Correction after review (point 3). "Every buffer" is exact for every 2 MiB chunk and close for any large buffer. Small buffers need not split evenly: a 65 B buffer that starts at a line boundary has both of its lines on one mesh in 20 % of the possible starts [homes.csv, first 2 MiB chunk]. Safer wording for the slide: "Home assignment is per 64 B line. Every measured 2 MiB chunk splits evenly between the two meshes."

## Question 2. The next step "read the CMN capacity-partition registers"

> We did not read the registers in any of the tests? What is the purpose of reading them?

Answer. Correct, no test read them. The report lists it as an open item.

- Each 1 MiB slice holds two kinds of lines: lines homed at that node, and proxy copies of lines homed on the other mesh. How the 1 MiB is split between the two is a configuration setting in the mesh registers [CMN S3 TRM, pages 335 to 336]. Perf counters cannot show it.
- Reading it would explain why one core sees exactly 64 MiB, and how home lines and proxy lines compete for space when a core's data is homed on both meshes.
- Cost: root access to the mesh configuration registers, or the settings from the firmware team, plus the manual to decode them.
- Priority: Jibin said in the slide-prep meeting of 2026-11-09 that it is not high on the list.

Correction after review (point 1). The manual does not describe a partition into two parts. Home lines and proxy lines share each slice's storage, and firmware can set a separate maximum occupancy for each class. See the review section, point 1.

## Question 3. "Half the lines of each slice"

> Would it be more accurate to say "Half the lines of each slice are homed on the other mesh"?

Answer. No. That is a different claim, and it was not measured.

- The buffer statement is about addresses. For any buffer, half of its lines have their home node on mesh 0 and half on mesh 1. This was measured over 524,288 lines [homes.csv].
- The slice statement is about what a slice holds: lines it homes, plus proxy copies of lines homed on the other mesh. How much of each is exactly the capacity-partition question. It is unknown.
- Keep "Half the lines of every buffer are homed on the other mesh."

## Question 4. Do consecutive lines really alternate?

> So every consecutive 64 bytes flip between the 2 meshes? Really?

Answer. Nearly. Computed from the 524,288 lines in homes.csv on 2026-11-09:

- 80.0 % of adjacent lines are homed on different meshes.
- The pattern repeats every 16 lines: 0101 1010 0101 1010, then inverted for the next 16.
- No run of consecutive lines on one mesh is longer than 2.
- The XOR rule explains all 16 chunks of 2 MiB with no exception. Chunks 3, 5, 6 and 14 come out inverted, so a higher physical-address bit that user space cannot see also enters the hash.
- Why: bit 6 is the lowest bit of a line address and it is in the XOR, so neighbours usually differ. Bit 8 is also in it, so at every fourth boundary two neighbours land on the same mesh.
- This is normal interconnect design. Arm CMN spreads consecutive lines over home nodes by an address hash so that no home node becomes a hot spot. Which of the 64 home nodes inside a mesh gets a line is a hash too.

Correction after review (point 4). The 16-line pattern does not simply alternate from block to block: the blocks at lines 48 and 64 are identical [homes.csv]. "Every fourth boundary" is also too strong, since the boundary at line 16 changes mesh. The rule that reproduces all 524,288 lines is the XOR of address bits 6, 8, ... 20 plus one inversion per 2 MiB chunk. Also, "software cannot see" the higher bits is wrong for a root process: the root run read each chunk's physical frame from /proc/self/pagemap [chunks.csv, column pfn_hex]. Which higher bits enter the hash was not worked out from those 16 frames.

## Question 5. Is the hash related to the capacity partition?

> Is this related to the CMN capacity-partition registers?

Answer. No. They are two different settings.

- The hash is the system address map. It decides which home node owns each address. It is fixed per line.
- The capacity partition decides how each 1 MiB slice divides its space between the lines it homes and proxy copies of lines homed on the other mesh.
- They interact in one way. Because of the hash, half of what a core caches on its own mesh must sit in proxy space. If the partition gave proxies less than half, a core would reach less than 64 MiB for other-mesh lines. We measured the total, 64 MiB, not the split.

Correction after review (point 1). Replace "the capacity partition decides how each slice divides its space" with: home and proxy lines share each slice's storage, and the registers set a maximum occupancy for each class, which reset to the maximum [CMN S3 TRM, pages 335 to 336 and 1038 to 1041]. The interaction stated here still holds as a conditional: a proxy limit below about half would cap a core's other-mesh lines before 64 MiB.

## Question 6. A 65-byte buffer, and whether the slide numbers are two-mesh numbers

> I am still confused. Each line is 64 B, so when software creates a buffer of 65 B, the buffer splits between 2 meshes? If so, most latency and bandwidth data in the slides are from 2 meshes, not from the local mesh, because most tests used buffers larger than 64 B, right?

Answer. Two different questions hide here: where a line is homed, and where the bytes come from.

- **Homed**: yes. A 65 B buffer covers two lines when it crosses a line boundary, and in 80 % of neighbouring pairs the two homes are on different meshes. "Home" means the node that owns the address, not the slice the core reads from.
- **Served, for cache hits**: from the core's own mesh only. A line homed on the other mesh is held by a proxy slice on the core's own mesh, at the same 19 to 44 ns. The counters confirm it: during an 8 MiB read stream from CPU 0, mesh 0 counted 0.83 slice accesses per line and mesh 1 counted 0.000 [writebw.csv, case asmread-8M-1].
- So the mesh-cache latency (30 ns average), the one-core read (67 GB/s) and the whole-chip read (0.62 TB/s) are own-mesh numbers. Each is averaged over the 64 slices of that mesh, because consecutive lines are spread over all slices.
- The heatmap on slide 3 is the one place where homes were sorted out. Each chain used only lines homed at one XP, chosen from homes.csv. That is how a per-slice latency was isolated [latency.csv].

Where the other mesh does take part:

```
read A, homed on own mesh   -> home slice, own mesh ....... 19 to 44 ns
read B, homed on other mesh -> proxy slice, own mesh ...... 19 to 44 ns
first read of B held only by the other mesh -> cross and back  about 85 ns
write B (stream) -> home node on other mesh -> DRAM ....... crosses link
```

- First touch of a line that only the other mesh holds: 85 to 88 ns per load at 16 MiB, against 29 ns on the same mesh [cross.csv].
- Writes beyond L2 go to the line's home, not to a proxy. The one-thread 8 MiB write stream counted 0.38 accesses per line on the other mesh [writebw.csv, case asmwrite-8M-1]. The 73 GB/s one-core write and the write collapse are two-mesh paths.
- DRAM traffic goes through the home node to memory controllers on both meshes: 1.14 local and 0.51 remote memory requests per line with 64 writers on mesh 0 [crossmesh.csv]. The 148 ns DRAM latency and the 533 GB/s DRAM read are two-mesh numbers by nature.

Corrections after review (points 5, 7 and the smaller items). The 0.62 TB/s whole-chip number combines 32 readers on mesh 0 and 8 on mesh 1, each served from its own mesh; it is not an average over one mesh's slices. The 67 GB/s includes the 17 % of lines served by the core's own L2. The heatmap chains were selected per home node, not per XP. The write sentence should read: the tested stream largely bypassed mesh-cache allocation (0.013 fills per line), and its requests were counted at the local node and at the remote home (0.764 accesses per line on mesh 0, 0.382 on mesh 1), so "not to a proxy" is not shown. The local and remote memory-request counts can count one request at more than one node and are not counts of distinct lines.

## Question 7. A 128-byte buffer at address 0

> Say a buffer of 128 B at address 0x0 to 0x80. It crosses 2 cache lines, so the first 64 bytes are located at mesh 0 and the second 64 bytes at mesh 1. Is this right?

Answer. Almost. Three corrections.

- **Byte ranges.** A 128 B buffer at 0x0 spans 0x00 to 0x7F. The first line is 0x00 to 0x3F, the second is 0x40 to 0x7F.
- **Which mesh is which.** The two lines differ only in address bit 6, and bit 6 is in the hash. So the two lines of any aligned 128 B pair are always homed on different meshes. Whether line 0 goes to mesh 0 or mesh 1 depends on higher bits of the physical address, which software does not see. chunks.csv shows the physical frame of each 2 MiB chunk, and 4 of the 16 chunks came out inverted.
- **"Located at" means homed, not stored.** Where the bytes sit depends on the level:

```
buffer 0x00..0x7F, read by a core on mesh 0
 line 0 (0x00..0x3F)  home: one mesh    copy read from: a mesh 0 slice
 line 1 (0x40..0x7F)  home: other mesh  copy read from: a mesh 0 slice (proxy)
```

- In the mesh cache, both lines are cached on the reader's own mesh, one in its home slice and one in a proxy slice. The remote home only records that mesh 0 holds a copy.
- In L1 and L2, both lines are in the reading core.
- In DRAM, which chiplet's memory channels hold each line is not resolved by our measurements. The home-node counters show memory requests to both local and remote controllers, and the two counts overlap [crb-memory-hierarchy.html, section "Who reads, who provides"].

Correction after review (point 6). The three levels in this answer are not occupied at the same time. For data lines the mesh cache is exclusive of the private caches [CMN S3 TRM, pages 54 to 55], and the report measured it: a read takes the line out of the slice and the L2 eviction puts it back. A line in use sits in L1 or L2, and moves to a slice on the reader's own mesh when L2 evicts it. The table lists where each kind of copy can be, not simultaneous copies.

## Question 8. Is one slice per XP the proxy?

> An XP has two 1 MiB slices, so very likely one slice is for local cores (cores on the same mesh) and the other is the proxy slice, right? Also, each mesh has many proxy slices, correct?

Answer. No, the evidence points the other way.

- **Both slices on an XP are home slices.** Every one of the 128 home nodes owns exactly 4,096 of the 524,288 lines of the test buffer [nodes.csv]. A node that only served as a proxy would own no addresses.
- **Why two per XP.** The mesh has 64 home nodes but only 32 XPs with a home-node port. Arm's CAL block lets two devices share one XP port, the same way two cores share one core port [CMN S3 TRM, section 2.1.1.15, page 63; cmn-map.txt].
- **The proxy role lives inside each slice.** A home node plays both roles. Its slice is divided into a part for the lines it homes and a part for proxy copies of lines homed on the other mesh [CMN S3 TRM, page 55 and page 1216]. The size of that division is the capacity partition, not read.
- **So every one of the 64 slices on a mesh has a proxy part.** There are no slices that are only proxies.
- Which remote home maps to which local proxy looks like a fixed function of position, roughly the mirror image across the chip. From each core, the latency to a remote home's proxy is anti-correlated with the latency to the same-numbered local slice, correlation minus 0.74 [crb-memory-hierarchy.html, section "Lines homed on the other mesh are served by a local proxy"]. It is not read from documentation.
- One detail that is not a role split: the two slices on CPU 0's own XP read 19.2 ns and 22.4 ns [latency.csv, core 0, XP (1,2)]. Both are homes. Hypothesis: port arbitration in the CAL or the physical placement of the two nodes. Not measured.

Correction after review (point 8). That every one of the 64 nodes also serves proxy lines is the design's capability, not a verified configuration on the CRB. The manual has a home-only mode, hnf_mode, in register cmn_hns_lbt_cfg_ctl [CMN S3 TRM, page 1039]. Proxies are active on the CRB, because remote-homed lines were served at own-mesh latency while their home counted 0.000 to 0.003 accesses per load [verify.csv]. Which nodes serve them, and the mirror-image mapping, stay hypotheses.

## Question 9. Is the useful capacity 64 MiB or 128 MiB?

> So even though there are 128 MB in total, it is possible the total cached data is 64 MB because half of the mesh cache is used as proxy, right?

Answer. Half right. Half of the capacity is proxy space, but proxy copies are duplicates only when cores on both meshes use the same lines.

Layout, est.:

```
mesh 0 slices, 64 MiB              mesh 1 slices, 64 MiB
 home part : lines homed on 0       home part : lines homed on 1
 proxy part: lines homed on 1       proxy part: lines homed on 0
 holds what mesh-0 cores use        holds what mesh-1 cores use
```

- Each mesh caches what its own cores use, in home parts or proxy parts. A single buffer starts missing at 64 MiB (11 % of loads) and reaches 81 % misses at 96 MiB, so the two parts together give one mesh's cores about 64 MiB [crb-memory-hierarchy.html, section "Effective capacity is 64 MiB for one buffer"].
- The half-and-half split is an inference, not a register read. A buffer's lines are homed half on each mesh, so its capacity is set by the smaller part. 64 MiB for one buffer means each part is about 0.5 MiB per slice (est.). The partition register would confirm it.

When the chip holds 128 MiB of distinct data:

- If the cores on mesh 0 work on data set A and the cores on mesh 1 on data set B, nothing is duplicated. Each mesh holds 64 MiB of its own set. This is an inference from the design and the test below. It was not measured directly.
- A line is kept in the slices of the mesh whose cores use it, not in both. Core 3 on mesh 0 built and walked a 16 MiB chain. Core 67 on mesh 1 then walked it. The first walk cost 86.1 ns per load, the second 32.1 ns, against 29.0 ns when core 3 walked its own chain [cross.csv]. Half of those lines are homed on mesh 1. If the mesh-1 homes had kept copies of their own lines, half the loads would have hit at about 30 ns and the average would have been about 57 ns (est.). So the remote home kept only the record, not the data.

When the chip holds only 64 MiB of distinct data:

- All cores share one working set. Each line is then cached on both meshes, once in its home part and once in the other mesh's proxy part.
- Only one mesh's cores are active. The other mesh's slices hold nothing useful.

For host software this is one more reason to keep a thread's data on its own mesh.

Corrections after review (points 1 and 2). The half-and-half layout is not a programmed partition: home and proxy lines share each slice, and the single-buffer result only shows that neither occupancy limit was below about half for that workload (est.). The three cases (separate data sets, one shared set, one idle mesh) are hypotheses, not measurements. The 86 ns first walk shows that no line was served from mesh 1's slices in that test. The sentence "the remote home kept only the record" assumes that a retained copy would have been usable without extra coherence work, which was not measured.

## Not yet measured

- The occupancy limits of a slice for home lines and proxy lines: registers cmn_hns_lbt_cfg_ctl at offset 0xA30 and cmn_hns_lbt_aux_ctl at offset 0xA38 [CMN S3 TRM, pages 1038 to 1041]. Access depends on firmware security settings, so root alone may not be enough.
- The distinct capacity of the whole chip. Test: one working set per mesh, each about 40 MiB, walked at the same time by cores of that mesh only, with the miss counters on. More than 64 MiB of distinct data without misses would settle the question for that size. Not run.
- Whether a line read by both meshes stays in both meshes' slices, or moves to the last reader. Test: alternate fresh walks from a core on each mesh over the same lines, with the home-node counters on and the private caches flushed between walks. Not run.
- Which higher physical-address bits enter the home hash. The 16 physical frames in chunks.csv are enough to test candidate bit sets. Not done.

## Review by Codex, 2026-11-09, and responses

Codex reviewed this record against the data files, the benchmark code and the Arm manual, and wrote codex-review-mesh0-or-mesh1.md. I checked each point against the same files and against the manual pages it cites, read from refs/arm-cmn-s3-r2p3-trm-107858.pdf with pypdf on 2026-11-09. I accept all eight points. None of them changes a measured number. They change which statements count as measured and which as hypotheses.

| Point | Codex's finding | Verdict | What I checked |
|---|---|---|---|
| 1 | The 64 MiB result does not show a 50/50 partition. Home and proxy lines share a slice under separate maximum-occupancy limits. | Accept. | Page 55: "The System Level Cache (SLC) is shared between HBT and LBT lines." Page 335: capacity partitioning "defines the percentage of cache that LBT and HBT requests can use." Page 1039: lcc_cmax_allowed and slc_cmax_allowed, 7 bits each, reset 0b1111111. Page 1041: slc_way_reserve_dis lets proxy lines take all ways. A balanced single buffer fills a slice half and half by demand, whatever the limits. The weaker inference that survives: neither limit was below about half for that workload (est.). |
| 2 | Separate sets giving 128 MiB, a shared set being duplicated, and an idle mesh holding nothing useful are hypotheses. The 57 ns counterfactual assumes usable retained copies. | Accept. | cross.csv: 29.277 then 29.034 ns per load for core 3 to core 3, 86.053 then 32.134 ns for core 3 to core 67, 16 MiB. The test did not count hits at the homes and did not return to the builder. |
| 3 | "Half of every buffer" is false for small buffers. | Accept. | homes.csv, first chunk: 20 % of 65 B buffers that start at a line boundary have both lines on one mesh. Every pair that starts at a 128 B boundary has opposite homes: 262,144 of 262,144. A 65 B buffer always spans two lines, so "when it crosses a line boundary" was redundant. |
| 4 | The 16-line pattern does not alternate indefinitely. Physical frames were recorded, so "software cannot see" is wrong for root. | Accept. | homes.csv: blocks at lines 48 and 64 are both 1010 0101 1010 0101. Same-mesh neighbours in the first 128 lines sit at lines 4, 8, 12, 20, 24, 28, 36, ... and 64, but not at 16, 32, 48, 80, 96 or 112. chunks.csv has pfn_hex per chunk. |
| 5 | The 0.62 TB/s whole-chip read combines readers on both meshes. The 67 GB/s includes L2 hits. | Accept. | 40 readers: 32 on mesh 0, 8 on mesh 1 [perthread-asmread-3M-40.csv]. 0.827 slice accesses per line in the 8 MiB one-thread run [writebw.csv]. |
| 6 | Local service does not mean a copy at every level at once. | Accept. | Pages 54 to 55: "The SLC allocation policy is exclusive for data lines." The report measured the same: a read takes the line out of the slice, the L2 eviction puts it back. |
| 7 | Keep the write conclusion specific to the measured stream. Memory-request counts are not distinct lines. | Accept. | writebw.csv, asmwrite-8M-1: 0.764 accesses per line on mesh 0, 0.382 on mesh 1, 0.013 fills. The report's own caveat on local and remote counts overlapping. |
| 8 | Both nodes being homes does not prove every node serves proxy lines. | Accept, with one addition. | Page 1039: hnf_mode, "Can program to 0b1 when HNS only receives HBT". Proxies are active on the CRB: verify.csv shows the 4 remote slices at 0.000 to 0.003 accesses per load at their home while the loads ran at mesh latency. Which nodes served them is not identified. |
| Smaller | "Every core" should be cores 0 to 119. Chains were selected per home node. The full report's map averages the two nodes of a crosspoint, the brief shows the faster one. | Accept. | latency.csv has 120 cores and 128 node rows per core. The report text says "for every core and every home node". make-brief.py takes the smaller of the two medians; the full report's figure data holds the means. |

What stands as measured after the review:

- The home of each 64 B line is set by an address hash. Every measured 2 MiB chunk splits exactly half and half. 80.0 % of neighbouring lines have different homes, and no run on one mesh is longer than 2 lines [homes.csv, chunks.csv].
- All 128 home nodes own addresses, 4,096 lines each [nodes.csv].
- Lines homed on the other mesh are served at own-mesh latency, 19 to 44 ns, with no access counted at their home [latency.csv, verify.csv].
- A single buffer read by one core starts missing in the mesh cache at 64 MiB [crb-memory-hierarchy.html, "Effective capacity is 64 MiB for one buffer"].
- A chain built on a mesh-0 core costs 86 ns per load on its first walk from a mesh-1 core and 32 ns on the second [cross.csv].
- The one-thread 8 MiB write stream allocated almost nothing in the mesh cache, 0.013 fills per line [writebw.csv].

What stands as hypothesis:

- How each slice's storage is split between home and proxy lines on the CRB.
- Whether the chip can hold 128 MiB of distinct data when both meshes are busy, and whether shared lines stay in both meshes or move to the last reader.
- Which local node serves as proxy for which remote home.
- Which higher physical-address bits enter the home hash.
