# Review scope

User clarification recorded at 2026-11-13T01:59:18Z.

- Assigned role: reviewer.
- Initial file: `/home/jhan/workspace/titan/cache-perf/crb/crb-memory-hierarchy.html`.
- Shared review file: `/home/jhan/workspace/titan/cache-perf/crb/crb-memory-hierarchy.html.review.md`.
- Baseline: `/home/jhan/workspace/titan/cache-perf/crb/tmp/crb-memory-hierarchy.before-slc-rename.html`.
- Baseline SHA-256 (the hash identifying the exact file): `36e91c71bc6f4e3c349b24fe18b073515e6231a35e527567e9d27f4c488df5d3`.
- The baseline matches the report version accepted in round 3 of session `20261111T222457Z-33f3e5`. The prior review ended at 2026-11-12T04:30:30Z. Its record is `/home/jhan/tmp/update-crb-memory-hierarchy.md.review.md`.
- Review only the changes between this baseline and the final version submitted after both Claude sessions finish their updates. Do not review the whole file.
- Findings must concern added, changed, or removed content, or a problem caused by those changes. Unchanged content and source files may be read as context or evidence. Independent defects in unchanged content are outside this review.
- Keep this baseline fixed through subsequent correction rounds. Do not treat the current live file as a finished submission while either Claude session is still updating it.

This preamble records the user's requested scope. It is not a worker handoff or a review decision. The worker still owns the START and READY entries required by the review-loop skill. Review begins after a complete READY entry identifies the finished file with its SHA-256 hash.

## session=20261113T033543Z-w7c2 round=1 role=worker status=START digest=- time=2026-11-13T03:36:13Z

- Initial file: `/home/jhan/workspace/titan/cache-perf/crb/crb-memory-hierarchy.html`
- Review file: `/home/jhan/workspace/titan/cache-perf/crb/crb-memory-hierarchy.html.review.md`
- Worker: Claude session "proxy examples" (this session). A second Claude session (crb-af) edited the same report before this one. It reported its last write at 2026-11-13T03:16Z and plans no further writes.

END ENTRY

## session=20261113T033543Z-w7c2 round=1 role=worker status=READY digest=1333e332428d2680fcb2b6ad4ab4f389f628dd299c0a56e3a4e7adab6d4e9248 time=2026-11-13T03:36:13Z

**Short version.** Both Claude sessions have finished. The report has 978 lines, as before. This entry describes the 15 physical lines that this session changed on top of the state of session crb-af (SHA-256 828876847ba931f83a3953c2ec0bd2b5478b77ff8bbbbb00cb2b9f4e32dac6b0, copy at `crb/tmp/agent-scratch/proxy-examples-2026-11-12/worker/report.before-worker.html`).

### Two sets of changes against the reviewer's baseline

- **Session crb-af (earlier today):** the SLC rename and the items P1 to P3. Its record is `/home/jhan/tmp/update-crb-memory-hierarchy.md`. I did not write those changes. I can answer findings on them only after asking that session.
- **This session:** lines 49, 232, 233, 253, 356, 440, 442, 488, 502, 503, 504, 508, 779, 780, 889. The edit script is `crb/tmp/agent-scratch/proxy-examples-2026-11-12/worker/apply.py`. Its inputs are the files sec232.html, sec233.html, sec253.html, fig.js, openitem.html and record.html in the same folder. Every edit stays on its physical line.

### Changes requested by the user (Jibin)

1. **Section "Lines homed on the other mesh are served by a local proxy" (lines 232, 233).** Rewritten as short bullets. New content: the rule on the physical address that picks the home mesh, three example lines with virtual and physical address, the fitted proxy crosspoints, and two figures (svg ids `homeex` and `proxymap`, drawn by the script on line 780).
2. **Latency figure (lines 488, 502, 503, 504, 508).** The label "DRAM: 148 ns (415 cycles)" overlapped the band label "DRAM". The vertical axis now ends at 180 ns (before: 160). Three more labels crossed a line or a marker and were moved: L2, SLC and "5.6x gap". The label "repeated chain: 5.4 ns, every load misses L2" was moved and shortened to "repeated chain: 5.4 ns".
3. **Paragraph under "A first read of lines cached on the other chiplet costs 85 ns, later reads 32 ns" (line 253).** Rewritten as method bullets, one table and caveats. Statements about earlier versions of the report are removed, as the user asked.
4. **Data-path figures (line 889).** The box label is now "64 SLC (System Level Cache) of 1 MiB". The user gave this wording. Note: it differs from the report's term "slice".

### Changes that the user did not name (made so that the new text is not contradicted)

- **Line 49:** the change record lists the changes of this entry.
- **Line 233:** the sentence that withdrew an earlier claim is removed (same instruction as item 3). The take-away now states for which cores counters exist.
- **Line 356:** two sentences stated where the lines are before each walk. The run did not count that. They now state the measured difference and name the slice columns as the expected state.
- **Line 440:** a new open item "Home rule and proxy map" is appended.
- **Line 442:** "2.6 to 4 ns" is now "2.6 to 4.1 ns" (cross.csv gives 2.62 to 4.11). The two explanations of the first walk are marked as expected or as a hypothesis.
- **Line 779:** the foot line of the CPU 0 latency map said that the proxies are "near column 5". The fitted map contradicts that. It now names the lowest cell and its proxy.

### Evidence

- **Home rule:** XOR of the even-numbered PA bits 6 to 36 gives the measured mesh for 524,288 of 524,288 lines (`.../hash/hash2.py` on full/homes.csv and full/chunks.csv). The same rule on the VA is wrong for 262,144 lines (`.../worker/va_rule.py`, output va_rule.out).
- **Proxy map:** least-squares fit of full/latency.csv against hops (`.../proxyfit/proxyfit.py`, report.txt, proxy-positions.json). A second agent tried to refute the map (`.../refute-proxy/refute.py`, out.txt).
- **Bit 6 rule:** 262,144 of 262,144 pairs (`.../worker/bit6_rule.py`, bit6_rule.out).
- **Node id check:** results/sudo-20261102T034539Z/log.txt lines 16 to 18.
- **Cross-chiplet table:** results/followup2-20261031T073513Z/cross.csv, and results/followup3-20261102T031936Z/percore-latency-1.csv for the walkers' own latency.
- **Arm manual:** page texts in `.../trm/pages/pNNNN.txt` (pages 13, 55, 134, 325 to 329, 335, 336, 1038, 1039).
- **Independent recomputation of the final text:** four checker agents read the applied diff. One recomputed the numbers of lines 232, 253, 440, 442, 779 and the map on line 780 with its own scripts (`.../final-numbers/`). They returned 29 findings, some of them twice. All findings on lines of this session were fixed in the submitted file. Three findings on lines 359, 465 and 778 were not fixed: see "Known and left unchanged".
- **Render:** the submitted file was rendered with headless Chrome. No console message and no uncaught error. The figures lat, homeex, proxymap, dist and path-rc were captured and read.
- **Tags:** a parser-based check found the changed lines 49, 232, 233, 253, 356, 440, 442 balanced, with no block element inside a paragraph.

(`...` stands for `crb/tmp/agent-scratch/proxy-examples-2026-11-12`.)

### Checks not run

- No new measurement on CRB. All numbers come from the runs of 2026-10-31 and 2026-11-02.
- The solver result "other choices of bits 21 to 36 fit as well" (`.../refute-hash/refute.out`) was not rerun in the final check.
- The statement on CAP_SYS_ADMIN and /proc/self/pagemap is taken from the Linux documentation. It was not tested on CRB.
- TRM pages 328 to 329 (the example for 2 chips) were read by the first check agents only, not by the final ones.
- The brief (`crb-memory-hierarchy-brief.html`) and `make-brief.py` were not changed and not rechecked against the new text.
- The figures were not checked in a second browser.

### Known and left unchanged (outside the lines of this session)

- Line 778: "19.0 ns at the home crosspoint (1,2)" uses "home crosspoint" for the crosspoint of CPU 0, and the cells of that figure show 20.8 ns.
- Line 465: the word list says that the root run measured CPUs 64 to 127. CPUs 120 to 127 were not measured.
- Line 359: the row label "Built and walked on the same chiplet (core 3 to 3, 67 to 67)" describes controls where one core builds and walks.
- Line 251: one sentence about an earlier version of the report remains in the paragraph above the rewritten one.
- Line 183: the expansions of LCN and LCC were not compared with the new text.

END ENTRY

## session=20261113T033543Z-w7c2 round=1 role=reviewer status=COMMENTS digest=- time=2026-11-13T04:23:46Z

### Short version

Two findings remain in the new explanation of address placement and cache counters. The numerical checks and changed-figure checks below passed.

### Scope confirmed

- Review only the changes from `tmp/crb-memory-hierarchy.before-slc-rename.html` (SHA-256 `36e91c71bc6f4e3c349b24fe18b073515e6231a35e527567e9d27f4c488df5d3`) to the submitted HTML (SHA-256 `1333e332428d2680fcb2b6ad4ab4f389f628dd299c0a56e3a4e7adab6d4e9248`). This includes the changes of both Claude sessions.
- Unchanged passages were read only as context. Independent defects in unchanged content are outside this review. The baseline remains fixed for later rounds.

### Checks

- The submitted hash matches. I read the changed prose, markup and chart code against the fixed baseline.
- Independent calculations reproduce the physical-address rule for all 524,288 measured lines, its failure on 262,144 virtual addresses, the three example addresses, and the 262,144 aligned line pairs. The 32 crosspoint pairs match the map embedded in the figure. These checks use `results/sudo-20261102T054936Z/full/homes.csv`, `chunks.csv` and `nodes.csv`.
- Independent calculations reproduce the new latency-fit table and the four example latencies from `full/latency.csv` and `core-positions.json`. The cross-chiplet table's ranges reproduce from `results/followup2-20261031T073513Z/cross.csv`.
- I checked the changed port-rate statements against the raw bandwidth files and reran `port_counts.py` and `rates.py`. The two added bars reproduce from `results/followup-20261030T194205Z/pair.csv`. The new C listings match `bench/bandwidth.c` after whitespace is removed.
- The HTML structure check reports no tag mismatches or missing anchor targets. The hierarchy-figure geometry check passes. The offline browser reports no script errors. I inspected renders of the latency chart, both new proxy figures, the pair chart, the CPU 0 latency map, and the whole-chip read-path figure. Their text has no clipping or overlap in the checked desktop layout. The repeated arrow-marker ids already exist in the baseline and are outside this diff.
- I checked the cited Arm manual passages on address mapping, local proxy nodes, and cache counter semantics. Review snapshots and browser evidence are under `/tmp/crb-diff-review-20261113/`.

Checks not run: no new benchmark or remote-machine command, no second-browser check, and no review of the brief or its generator. This is not a whole-file approval.

### CRB-D1 — Keep aggregate counter ratios separate from demand-load hit fractions

Location: `crb-memory-hierarchy.html:232`, “Evidence 2”.

The new text says “mesh 0 looked up every load” and “Mesh 0 hit for 0.70 to 0.99 of the loads (1 minus the misses for each load).” Those conclusions do not follow from the aggregate counters. The same paragraph says the accesses above one per load are not attributed.

For example, the row for mesh 1 node `0x218` records 2.045 mesh-0 accesses and 0.304 mesh-0 misses per timed load. Subtracting the latter from one gives 0.696. That is not a measured fraction of demand loads that hit. The counters do not identify which accesses or misses belong to those demand loads. The measurement code subtracts an empty-window baseline and divides whole-mesh totals by the number of timed loads. It does not match transactions to individual loads. Arm defines the cache miss rate as misses divided by cache accesses, which is a different quantity again. [Ref1][Ref2][Ref3]

Requested correction: retain the observed accesses and misses per timed load. Remove the claims that every demand load was looked up and that exactly 0.70 to 0.99 of demand loads hit. Apply the same attribution caveat to “mesh 1 was accessed for at most 0.08 of the loads.” State that the demand-load hit fraction was not measured. The counts can still support a qualified interpretation of local service together with the latency evidence. No new measurement is required for this wording correction.

### CRB-D2 — Keep the alignment condition on the half-and-half address split

Locations: `crb-memory-hierarchy.html:232`, “Every pair of lines splits”, and `crb-memory-hierarchy.html:233`, “Demand”.

The verified claim concerns pairs numbered 2k and 2k+1 in the page-aligned buffer. The new text extends it to “any buffer”. That extension is false for arbitrary subranges, even within the measured buffer.

The recorded lines 3 and 4 are consecutive. Both have mesh 1 as their home. Their home nodes are `0x90` and `0x2a8`. A 128-byte range starting at line 3 therefore has both cache lines homed on mesh 1. These are not one of the aligned pairs used by the check. A range containing one cache line also cannot split equally. [Ref4]

Requested correction: restrict the exact half split to buffers made of complete, physically 128-byte-aligned pairs of cache lines, as in the tested page-aligned buffer. Keep the separate caveat that the hash model was fitted on one allocation. For arbitrary starting addresses or lengths, describe the boundary qualification instead of saying “any buffer”. Make the same correction in the following “Demand” bullet. No new measurement is needed.

### References

- Ref1: `results/sudo-20261102T054936Z/full/verify.csv`, rows for the four mesh-1 home nodes. The node `0x218` row is line 8.
- Ref2: `../bench/homelat.c`, `cstate_baseline()` and `verify_slices()`, especially the pass-B calculation of `a0`, `m0`, `a1` and `m1`. These are baseline-subtracted whole-mesh totals divided by `loads`.
- Ref3: CMN S3 Technical Reference Manual, page 387 (cache miss-rate formula) and pages 390–391 (counter definitions). Available extracted text: `tmp/agent-scratch/proxy-examples-2026-11-12/trm/pages/p0387.txt`, `p0390.txt` and `p0391.txt`.
- Ref4: `results/sudo-20261102T054936Z/full/homes.csv`, lines 5 and 6 (`line=3` and `line=4`). Physical addresses follow from chunk 0 in `full/chunks.csv`.

Please address CRB-D1 and CRB-D2 in the next READY entry. Keep the original scope and baseline.

END ENTRY

## session=20261113T033543Z-w7c2 round=2 role=worker status=READY digest=f45d950cda4cc3bd67d0e87d2fcb25d460d414f764b3acafb7f9563419543a1c time=2026-11-13T04:24:39Z

**Short version.** Both findings are accepted and corrected. Only lines 232 and 233 changed since round 1. The file keeps 978 lines.

### CRB-D1 — accepted

- **Change (line 232, "Evidence 2").** The observed accesses and misses for each timed load stay. The three conclusions are removed: "mesh 0 looked up every load", "mesh 1 was accessed for at most 0.08 of the loads" and "Mesh 0 hit for 0.70 to 0.99 of the loads".
- **New text:** "Each count is the total of a whole mesh, minus the count of an empty window, divided by the number of timed loads. The counters do not match an access or a miss to one load. So the share of the timed loads that hit on mesh 0 was not measured. Together with the latency (evidence 1), the counts support service from mesh 0. They do not prove it for each load, and they do not show which slice [full/verify.csv]."
- **Same caveat applied to three summaries** that said "Counters show this for CPU 0": the Short version of the section (line 232), the bullet "Home on the other mesh" (line 232) and the take-away (line 233). They now say "Counters support this for CPU 0".
- **Check:** the description of the counts follows `verify_slices()` and `cstate_baseline()` in `../bench/homelat.c`, as the reviewer's Ref2 states. I did not rerun any measurement.

### CRB-D2 — accepted

- **Check of the reviewer's example:** `full/homes.csv` gives line 3 on mesh 1 (node 0x90) and line 4 on mesh 1 (node 0x2a8).
- **Change (line 232, "Every pair of lines splits").** "the same is expected for any buffer" is replaced by: "This holds for these pairs only. Example: lines 3 and 4 are neighbours too, and both are homed on mesh 1. Bit 6 is in the mesh rule. So the same half split is expected for any buffer that consists of complete pairs of this kind. Such a buffer starts at a physical address that is a multiple of 128 bytes, and its length is a multiple of 128 bytes. A buffer with another start or length has lines without a pair at its ends, and it need not split in half. Only this buffer was measured."
- **Change (line 233, "Demand").** "The same is expected for any buffer (not measured)." is replaced by: "The same is expected for any buffer that consists of complete pairs of lines, each pair aligned to 128 bytes of physical address (not measured)."
- **Kept:** the caveat that the rule was fitted on one buffer (bullet "Limit of the rule" and the open item on line 440).

### Evidence for this round

- The edit script was rerun on the state before this session's edits (`.../worker/report.before-worker.html`). It reports the same 15 changed lines as in round 1.
- A comparison with the round 1 file shows differences on lines 232 and 233 only.
- Headless Chrome rendered the submitted file with no console message and no uncaught error.

### Checks not run

- The figures were not captured again. No figure code changed in this round.
- The other items under "Checks not run" of round 1 still apply.

END ENTRY

## session=20261113T033543Z-w7c2 round=2 role=reviewer status=REVIEW_COMPLETE digest=f45d950cda4cc3bd67d0e87d2fcb25d460d414f764b3acafb7f9563419543a1c time=2026-11-13T04:25:23Z

No further comments.

- CRB-D1 is resolved. The revised text distinguishes whole-mesh event counts per timed load from the unmeasured share of demand loads that hit. The three summaries now describe the counters as supporting local service.
- CRB-D2 is resolved. The half split is restricted to complete pairs of lines aligned to 128 bytes of physical address. The text gives the measured counterexample for an unaligned range and retains the limitation to one measured allocation.
- I checked the worker's replies and the complete diff from round 1. Only lines 232 and 233 changed. Scripts, styles and SVG markup are unchanged. The structure check reports no tag mismatches, unclosed tags, duplicate source ids or missing anchor targets. The round-1 figure checks remain applicable. No new benchmark, remote command or second-browser check was run.
- The latest READY entry and the file hash match the reviewed version. A copy is saved at `/tmp/crb-diff-review-20261113/round2.html`.
- Scope: only changes from `/home/jhan/workspace/titan/cache-perf/crb/tmp/crb-memory-hierarchy.before-slc-rename.html`, SHA-256 `36e91c71bc6f4e3c349b24fe18b073515e6231a35e527567e9d27f4c488df5d3`, to the final submitted HTML, SHA-256 `f45d950cda4cc3bd67d0e87d2fcb25d460d414f764b3acafb7f9563419543a1c`. Both Claude sessions' changes are included. This does not approve unchanged parts of the report.

END ENTRY
