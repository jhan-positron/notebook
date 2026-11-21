# Review record for asimov-mesh-map.html

## session=20261112T181253Z-6ba4b8 round=1 role=worker status=START digest=- time=2026-11-12T18:12:53Z

- Initial file: /home/jhan/workspace/titan/cache-perf/asimov/asimov-mesh-map.html
- Review file: /home/jhan/workspace/titan/cache-perf/asimov/asimov-mesh-map.html.review.md
- Scope: the page asimov-mesh-map.html (the mesh latency map of the Asimov emulator, run 8). It is written by gen_mesh_map.py, which reuses gen_run8_report.py and gen_run8_boots.py.
- The worker is checking the page before the first READY entry. The reviewer should wait for READY.

END ENTRY

## session=20261112T181253Z-6ba4b8 round=1 role=worker status=READY digest=ba394b3603ba34c9199c3be304407e305c3a1e3f89d0dbdde9f1308a60b7df9d time=2026-11-12T18:22:43Z

### What is submitted

- asimov-mesh-map.html, written by gen_mesh_map.py (python3 gen_mesh_map.py). The script imports the data layers and figures of gen_run8_report.py and gen_run8_boots.py. Those two scripts and their pages (run8-meshmap-boot1.html, run8-meshmap-3boots.html) were not changed.
- Raw data: results/membench-jibin-013 to 016 (run 8), plus sysinfo.txt and README.md of folder 011 and README.md of folder 004 for platform facts.

### Checks run before this entry

- Eight checker agents each took one part of the first version of the page (digest 44456663...daa4). They recomputed its numbers from the raw CSV and text files with their own scripts. They also read meshmap.c, run_map.sh, the READMEs and the two source pages.
- Their findings were applied in gen_mesh_map.py. Main changes:
  - Short version: the 0.32 ns bound was the pair-agreement number, not the model error. It now states the largest error against the printed formula (0.34 ns, rounded up from 0.334 ns).
  - Section 3: the model column now uses the printed formula (20.6 + 2.0 X + 1.0 Y), and the unrounded fit is printed beside it. Legend ends print one decimal (21.5 to 29.7 ns, 50.0 to 57.3 ns).
  - Section 4: "all three series lie on one line" became "same slope"; the boot 2 flushed series lies about 0.4 ns above the line. The 2.000 GHz clock has a reference [Ref11]. The parts of the base are marked as a hypothesis.
  - Section 5: the "right node" check is limited to boot 1, CPUs 2 to 9, and the three kinds that have mesh counts (1.2 to 1.3 requests per load above the other nodes).
  - Section 6: the fit cannot tell a memory point at (0,3) from one at (1,3) (rms 0.089 ns for both). The page now says so and takes (0,3) from the mesh map. Costs are given per step, one way, for both boots. The figure legend is no longer clipped.
  - Section 7: the table order of the hash is taken from the data, not from the manual. It equals the order of home node numbers #0 to #4 on the mesh map. The check covers classified lines only (10, 4 and 2 lines were left out).
  - Section 8: the missing note on check 8 was added. Table terms are defined. The 8.4 table names its counters and says that a dash means not measured. The sentence "88 of 113 claims" was removed: no file in the folder records those counts.
  - Section 9: the mix model's third term (passes 4 to 6) and its higher base are stated. Boot 3 flushed OCM lines still rise with distance (0.67 and 0.26 ns per step); the earlier text said they did not.
  - Section 10: "every best value is a lower-half value" is limited to the kinds where it holds (asserted in the script).
  - References: Ref5 and Ref10 are now cited in the body; Ref11 and Ref12 are new. The run date is 2026-11-12 UTC, as the four READMEs say.
- After the fixes: the script ran without error. Its asserts passed (no "hop"; the (0,3)/(1,3) tie on both boots; (0,3) best of the ten bridges; best pass is one of passes 0 to 3 in the four cache kinds named in section 10). Every [Ref1] to [Ref12] is cited at least once in the body.
- Rendered sections 1, 2, 3, 6 and 9 with headless Chromium at 1400 px and looked at the images: no clipped or overlapping labels.

### Checks not run

- The page was not looked at as a whole at 700 px width after the fixes. Hover tooltips were not inspected.
- [Ref7]: the Arm manual PDF was not opened. One checker compared the formula with a text copy of the manual outside this folder.
- The firmware state of each boot and the trial run's exit status are taken from the operator's READMEs [Ref6].
- The places of CPUs 4-5 and 6-7 on the mesh have no primary source in the folder. The page says so in section 1.
- SHA256SUMS of folders 013 to 016: one checker was asked to run sha256sum -c; I did not rerun it myself.

END ENTRY
## session=20261112T181253Z-6ba4b8 round=1 role=reviewer status=COMMENTS digest=- time=2026-11-12T18:27:29Z

Short version: the checked numbers agree with the raw files. Three corrections remain in the explanation of the measurements and the chart.

### R1 — Qualify the intended path of an evicted line

- Location: “Words used here,” the Evictor definition; section 2, steps 2 and 3 and the “Who answers the load” table. Generator: gen_mesh_map.py:217 and 245–248.
- Problem: “They push the chain lines out of the cluster's caches” and “Every load of a pass therefore travels the same distance” describe eviction as guaranteed on all three boots. The table also names the home node as the answerer without a boot condition. The boot 2 counters contradict this: the median l3d_refill_rd count is 0.29 per load for ocm-evict and 0.32 for slc. Most loads stayed in the cluster. Section 9 correctly explains this, but the method section teaches the opposite.
- Requested correction: define the evictor as an attempt to remove the chain lines. Say that loads which reach the selected home node have the same CPU-to-node distance. Label the table's final column as the intended source, or explicitly restrict its asserted sources to boot 1 on CPUs 2 to 9. Point to sections 8.4 and 9 for the measured paths.
- Evidence: boot 2 latency-map.csv, all 280 passes per kind on CPUs 2 to 9; independently reproduced section 8.4 counter table. This does not require changing any numerical result.

### R2 — Disclose the artificial horizontal offsets in the step-cost chart

- Location: section 4, the paragraph introducing the scatter plot and the plot caption. Generator: gen_mesh_map.py:104–108 and 275–278.
- Problem: the text says that horizontal position is distance, but the three series use offsets of -0.16, 0 and +0.16 distance units. A cell at distance 1 is drawn at 0.84, 1.00 or 1.16. The model line has no offset. This changes the apparent gap from the line in a figure intended to explain a roughly 0.4 ns difference between boots.
- Requested correction: either draw every point at its true distance or explicitly label the horizontal shifts as display offsets used to separate overlapping series. If retained, state the offsets and tell the reader to compare vertical values at the original integer distance. Do not describe the shifted horizontal positions as measured distances.
- Evidence: the SVG coordinates generated at gen_mesh_map.py:108; rendered screenshot /tmp/asimov-mesh-review-browser/1400-section-4.png. The data tooltips correctly report the integer distances.

### R3 — Exempt the completeness table from the CPU exclusion statement

- Location: section 2, “CPU 0's 20 cells are not distance numbers.” Generator: gen_mesh_map.py:254.
- Problem: “Every table and figure below uses CPUs 2 to 9 only” is false for section 8.2. Its 180 cells and 1,269 rows include CPU 0. CPUs 2 to 9 alone contribute 160 cells and 1,120 timed passes.
- Requested correction: limit the exclusion statement to latency comparisons and fits. Explicitly say that the completeness table counts the full files, including CPU 0. Keep the correct full-file totals.

### Checks completed by the reviewer

- Confirmed the submitted SHA-256 digest before reading and before this entry.
- Regenerated the page to /tmp/asimov-mesh-review-regenerated.html. Its SHA-256 digest matches the submitted HTML exactly.
- Ran sha256sum -c for folders 013–016: all 40 listed files passed (7, 11, 11 and 11 files).
- Independently parsed the raw CSV files. Checked all 20 distance rows, all 4 fit rows, all 12 control rows, all 12 counter rows, and all 660 numerical SVG tooltips. All agree at the printed precision.
- Recomputed the maximum error against the printed formula: 0.334 ns. The printed upper bound of 0.34 ns is correct. Recomputed the maximum cache-pair difference: 0.318 ns.
- Recomputed the 36 candidate memory-point fits for each of boots 1 and 2. The two best positions are (0,3) and (1,3). Their equal errors and the reported costs agree with the page.
- Read the matching Arm manual text in /home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/cmn-s3.txt (document 107858_0203_05_en, page 142). Independently checked its formula against every classified line in all three map-homes.txt files. Counts match the report: 10,245, 10,251 and 10,253 classified lines; 10, 4 and 2 unused lines.
- Compared the mesh drawing with the cited sysinfo map. Read meshmap.c and run_map.sh for the measurement recipe.
- Rendered the page with Chromium at 1,400 px and 700 px. Neither viewport has page-wide horizontal overflow. No SVG text extends beyond its viewBox. Inspected screenshots of the mesh, latency maps, step-cost chart, memory path and boot comparison. Inspected tooltip contents through the rendered SVG titles and raw-data comparison; no manual tooltip interaction was performed.
- Validation scripts and results: /tmp/asimov-mesh-review-data.py, /tmp/asimov-mesh-review-data.json, /tmp/asimov-mesh-review-browser.py, /tmp/asimov-mesh-review-browser/results.json.
- No hardware tests were run. Firmware state remains operator-reported, as the page states. No independent primary source was found for the CPU 4–5 and 6–7 placements; the page already identifies that limitation.

END ENTRY


## session=20261112T181253Z-6ba4b8 round=2 role=worker status=READY digest=9b81ce8297505186af98684e131faee025020ee2bb11071a908a3703eb219918 time=2026-11-12T18:28:11Z

All three findings are accepted. The changes are in gen_mesh_map.py, and the page was regenerated. No number on the page changed.

### R1 - accepted, corrected

- "Words used here", Evictor: "They are meant to push the chain lines out of the cluster's caches. On boot 2 most chain lines stayed in the cluster (section 9)."
- Section 2, step 2: "Every load that reaches the home node therefore travels the same distance."
- Section 2, step 3: "Step 3 is meant to decide who answers the load."
- Kinds table: the last column is now headed "Intended source of the data".
- New bullet under the table: "The last column is the intended source. The counters show that it was the real source on boot 1 for CPUs 2 to 9 (section 8.4). On boot 2 only about 0.3 of the loads of the two evicted kinds left the cluster (section 9)."

### R2 - accepted, corrected (offsets kept and disclosed)

- The intro of section 4 no longer calls the horizontal position the distance. It says that every cell has a whole number of units (1, 2, 4, 5, 6, 8 or 9).
- New bullet: the dots of the three series are shifted by -0.16, 0 and +0.16 units so that they do not cover each other. The shift is for display only and is not a measured distance.
- The chart has a new mark: a short black horizontal line at the model value of each whole distance, 0.3 units to each side. A shifted dot can now be compared with a level mark. New bullet: "Compare the height of a dot with the mark of its group, not with the sloped line beside it."
- Check: rendered section 4 with headless Chromium at 1400 px and looked at the image. The seven marks sit at 1, 2, 4, 5, 6, 8 and 9 units on the sloped line, and the dots do not hide them.

### R3 - accepted, corrected

- Section 2 now reads: "Every latency comparison, fit and figure below uses CPUs 2 to 9 only. The completeness table of section 8.2 counts the full files, including CPU 0." The totals of section 8.2 are unchanged.

### Checks

- python3 gen_mesh_map.py ran without error; all asserts in the script passed.
- Not run: the full page at 700 px width was not looked at again after these edits.

END ENTRY
## session=20261112T181253Z-6ba4b8 round=2 role=reviewer status=COMMENTS digest=- time=2026-11-12T18:29:30Z

Short version: R1, R2 and R3 are resolved. One new sentence added for R1 overstates what the counters prove.

### Resolved findings

- R1: the glossary and method now distinguish intended eviction from the observed path. The table is explicitly about intended sources.
- R2: the display offsets are disclosed. All seven new horizontal marks match the printed model at distances 1, 2, 4, 5, 6, 8 and 9. I checked their SVG coordinates and the rendered chart at 700 px.
- R3: the exclusion statement now correctly exempts the completeness table.

### R4 — Preserve the missing-counter qualification in the new source-validation sentence

- Location: section 2, the new bullet beginning “The last column is the intended source.”
- Problem: the new sentence “The counters show that it was the real source on boot 1 for CPUs 2 to 9” covers all four table rows. For ocm-flush, no home-node or memory-request counter was measured. The core counter confirms that demand reads left the cluster. It does not identify their source node. Section 5 already states this limitation correctly: those cells have no mesh counts, and their timing is the only check of their node.
- Requested correction: state that the core counters show that loads left the cluster on boot 1. Limit the additional mesh-counter check of the source to the three kinds with mesh counts. Keep the ocm-flush exception visible, or replace the new proof sentence with a link to the qualified evidence in sections 5 and 8.4. No new measurement is requested.
- Evidence: boot 1 latency-map.csv has “-” in every mesh-counter field for all 280 ocm-flush passes on CPUs 2 to 9. The new blanket sentence conflicts with the existing qualification in section 5.

### Revision checks

- Submitted digest matches the HTML.
- The independent numerical checks still pass, including all 660 data tooltips. The existing numerical values are unchanged.
- Chromium at 1,400 px and 700 px: no page-wide horizontal overflow and no SVG text outside a viewBox. The seven new model marks are also checked against their expected coordinates.
- No hardware test or manual hover interaction was run. The scope and evidence limits recorded in round 1 still apply.

END ENTRY


## session=20261112T181253Z-6ba4b8 round=3 role=worker status=READY digest=59b9335c96fc08d09e2a41a7d22795624ba9e55a10ec404206fcb705e28812a7 time=2026-11-12T18:29:55Z

### R4 - accepted, corrected

- Section 2, the bullet "The last column is the intended source." now reads: "On boot 1 the core counters show that every load of CPUs 2 to 9 left the cluster, in all four kinds (section 8.4). The mesh counters also confirm the source for ocm-evict, slc and dram-flush (section 5). The ocm-flush cells have no mesh counts, and their timing is the only check of their node. On boot 2 only about 0.3 of the loads of the two evicted kinds left the cluster (section 9)."
- This is the only change of this round. It is one string in gen_mesh_map.py; the page was regenerated. No number changed.

### Checks

- python3 gen_mesh_map.py ran without error; all asserts in the script passed.
- Not run: no new rendering, since only one sentence of body text changed.

END ENTRY
## session=20261112T181253Z-6ba4b8 round=3 role=reviewer status=REVIEW_COMPLETE digest=59b9335c96fc08d09e2a41a7d22795624ba9e55a10ec404206fcb705e28812a7 time=2026-11-12T18:30:42Z

No further comments.

- R4 is resolved. The method now separates core-counter evidence from mesh-counter evidence and explicitly states the ocm-flush limitation.
- R1, R2 and R3 remain resolved. No open findings remain.
- Confirmed that the latest complete submission is round 3 and that its SHA-256 digest matches the reviewed HTML.
- Regenerated the final page to /tmp/asimov-mesh-review-final.html. It is byte-identical to the submitted page. The generator's assertions passed.
- Compared the final numerical tables and existing data tooltips with the independently checked round 1 version. They are unchanged. The seven model marks were checked in round 2.
- Round 2 rendering checks at 1,400 px and 700 px passed. Round 3 changes only the explanatory source-validation bullet. No new rendering was run for that prose change.
- No hardware tests or manual tooltip interaction were run. Firmware state remains operator-reported. The CPU 4–5 and 6–7 placements remain an explicitly stated assumption in the report.
- Initial file: /home/jhan/workspace/titan/cache-perf/asimov/asimov-mesh-map.html
- Review file: /home/jhan/workspace/titan/cache-perf/asimov/asimov-mesh-map.html.review.md

END ENTRY

