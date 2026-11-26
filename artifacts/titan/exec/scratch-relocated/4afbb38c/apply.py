import sys
p='/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/results.md'
t=open(p).read()
BW='/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx-2026-11-13'
R=[
# 1
('**Irregular interval**: an interval in which a thread started more than 100 µs late, or in which the end skew is above 5 ms.',
 '**Irregular interval**: an interval in which a thread started more than 100 µs late, or, with the common stop time only, in which the end skew is above 5 ms. With whole passes the end skew is reported and does not make an interval irregular (analysis choice A5).'),
('**Resolved**: the median of a difference is larger','**Resolved**: the absolute value of the median of a difference is larger'),
('A change is resolved if it is above its limit','A change is resolved if its absolute value is above its limit'),
('  - **not rejected**: every other outcome of two sessions. The prediction did not fail in at least one session.',
 '''  - **not rejected**: every other outcome of two sessions, for the hypotheses that the function `two_sessions` alone maps (H1, H4, H5, H6, H7a, H7b, H9a and the B5 statement). There the prediction did not fail in at least one session. The script has three more rules [Ref17]:
    - H3a: it also writes "not rejected" when the prediction failed in both sessions and no CPU has a case in both sessions.
    - H8: it writes "not resolved" unless both sessions are "supported" or both are "contradicted".
    - A cell of H11: it writes "not resolved" for every outcome other than both sessions "supported", both "contradicted" or both "not observed".'''),
('(4 loads, the rest `nop`)','(4 load instructions of 32 B each, 9 `nop`, and the 3 instructions that advance and close the loop)'),
('The numbers in this section come from the run of 2026-11-13, which raised the questions [Ref1]. They are not results of Parts A, B and C.',
 'The numbers in this section come from the run of 2026-11-13 at 18:12 UTC, which raised the questions [Ref1]. The one exception is the 71.07 GB/s of Q1c. It comes from a second run of that day, at 06:05 UTC [Ref1]. None of these numbers is a result of Parts A, B and C.'),
('**Run of 2026-11-13**: the earlier benchmark run that raised','**Run of 2026-11-13**: the earlier benchmark run (at 18:12 UTC) that raised'),
('gave 71.07 GB/s in one run and 67.99 GB/s in another.','gave 71.07 GB/s (best rate) in the run at 06:05 UTC and 67.99 GB/s (best rate) in the run at 18:12 UTC.'),
('Q1a. New read was only 0.9 %','Q1a. With the best rates of the run, new read was only 0.9 %'),
('Q1b. New C copy was 2.91 %','Q1b. With the best rates of the run, new C copy was 2.91 %'),
('| B5 | Old read, new read, `read_sparse` and four `nop` variants |','| B5 | Old read, new read, `read_sparse`, four `nop` variants and asm read twice (the A/A pair). 2 processes run this order and 2 run the reversed order |'),
('**Steps** [Ref1][Ref2]\n','**Steps** [Ref1][Ref2]. The thread counts of B8, the settings of C3 and the process counts are those that ran. They are in the `env.txt` and csv files of the result folders [Ref10][Ref11][Ref12].\n'),
('the Linux value for the mean number of runnable tasks over about the last minute.','the Linux value for the average number of tasks that are runnable or in uninterruptible wait (for example for disk I/O) over about the last minute.'),
# q1
('One went from high to low after 17 intervals [Ref8].','One was high in its first 17 intervals (71.56 GB/s in the 17th), then between the two limits for 7 intervals, and first low in its 25th interval (68.93 GB/s) [Ref8].'),
('  - After an old read interval, it is -0.10','  - After an interval of old read at 1 MiB, it is -0.10'),
('- Predicted: no CPU shows both levels with full coverage (case (a)), or both with no huge page (case (b)).',
 '- Predicted: every low interval has less than full coverage, and every high interval has full coverage [Ref1]. The rule of the handoff counts a failure only as case (a) or case (b): at least 10 low and at least 10 high intervals on one CPU in one session, all with full coverage (a) or all with no huge page (b) [Ref2].'),
('The handoff asks for a case "on one CPU in both sessions". The script','The handoff asks for a case "on one CPU in both sessions" [Ref2]. The script'),
('  - The core clock is 2.7998 GHz in all of them.','  - The median core clock is 2.7998 GHz in each of these 4 groups (single intervals: 2.7997 to 2.7999 GHz).'),
('- C2 has counters at the high level for short reference intervals of asm read (0.3 s) [Ref7][Ref21]:','- C2 has counters at the high level for reference intervals of asm read that stand between copy intervals (0.3 s each, the same interval length as in C1) [Ref7][Ref21]:'),
# q2
('- Measured, old read at 64+56 threads, 157 intervals per session [Ref9]:',
 '- Measured, old read at 64+56 threads with one buffer per thread, 157 intervals per session [Ref9]. The raw files give B7 140, B5 4, B8 4 and B9 9 intervals per session [Ref11][Ref12]. The page generator leaves out the 9 intervals of B9 with two buffers per thread [Ref18]. The ranges:'),
('| 157 / 157 intervals of old read |','| 157 / 157 intervals of old read with one buffer per thread |'),
('| H8 | **not resolved** (plan\'s word: "not resolved at this grid") |','| H8 | **not resolved** (user decision 2 [Ref3]. The label rule of the handoff also gives "not resolved", because no bracket formed [Ref2]) |'),
('q is the same with one and with two buffers. [Ref6][Ref9]','The ranges of q with one and with two buffers overlap in both sessions (0.531 to 0.548 against 0.532 to 0.549 over both sessions, no unit). [Ref6][Ref9]'),
('With q, the pattern is the same with one and with two buffers in both sessions. The plan names that outcome "rejected" [Ref1].','The ranges of q with one and with two buffers overlap in both sessions. If the user accepts that as the same pattern, the plan names that outcome "rejected" [Ref1].'),
('- Limit: in each of the two 0.5 s settings with whole passes, 64 of 64 intervals fail the 2 % check, in both sessions. This is expected for the reproduction condition [Ref9].',
 '- Limit: in each of the two 0.5 s settings of B7 with whole passes, 64 of 64 intervals fail the 2 % check, in both sessions. One of the two is the reproduction condition. With one kernel per process, 48 of 48 intervals of the reproduction condition fail it in each session [Ref9].'),
('**Statement of B5 (vector adds are needed for the pattern and total of old read).**','**Statement of B5 (vector adds are needed for the split pattern of old read).**'),
# runs
('No visit ended with one of these [Ref13].','None of the 15 logins with a recorded status (the long Part A login and the 14 visits of Parts B and C) ended with one of these [Ref13]. The short Part A login has no recorded status. Its `env.txt` holds the end line, and its csv files have no `-- killed` line [Ref10]. The script `run_partA.sh` writes the end line only after its last step [Ref19].'),
('**System load.** The run script read the load directly before every launch [Ref19].','**System load.** The two run scripts (`run_partA.sh` for Part A, `run_bwx.sh` for Parts B and C) read the load directly before every launch [Ref19].'),
('run_bwx.sh` and `bwx.c`: the load readings before each launch, and the benchmark.','run_bwx.sh` and `bwx.c`: the load readings before each launch, the sha256 check of `bwx`, and the benchmark. For Part A: `/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/run_partA.sh` (the same load readings, and the end line of `env.txt`).'),
('at 1 of 652 launches. It was `check-new-relea` of root at 90.9 %, at the first launch of C3 in s2 [Ref9].','at 1 of 652 launches (1 of the 244 launches of the steps with 120 threads, and 0 of the 408 launches of the one-thread steps). It was `check-new-relea` of root at 90.9 %, at the first launch of C3 in s2 [Ref8][Ref9].'),
('**Host rules.** Only the lead\'s record holds the three points below. No file of the results holds them [Ref20].',
 '**Host rules.** The lead\'s record holds the three points below [Ref20]. The result files hold two parts of the second point, and no other part of the three points. The setting `STOP_AT=none` of Parts B and C and of the short run is in the settings line of `env.txt` in each of the 28 step folders and in the folder of the short run [Ref11][Ref12][Ref16]. No login with a recorded status ended with status 3, the status after a marker file [Ref13].'),
('- A start time is the time in the name of the first result folder (clock of CRB).','- A start time is the time in the name of the first result folder (clock of CRB). The start time of a build is the first line of its `build.txt` (clock of CRB) [Ref15].'),
('The sha256 of `bwx` is `5b702073...d826f1`, and every visit checked it before its first launch [Ref14][Ref15].',
 'The sha256 of `bwx` is `5b702073...d826f1` [Ref15]. `visit.sh` passes this value to the run script. The run script compares it with the binary before its first launch, and stops with status 2 when they differ [Ref14][Ref19]. The `env.txt` of each of the 28 step folders of Parts B and C records this digest for `bwx` [Ref11][Ref12].'),
('The first build is in `crb-build-1/` of the same folder.','The first build is in `'+BW+'/crb-build-1/` (`build.txt`, `build.out`, `offsets.tsv`, `listing.txt`, and four `selftest-*.txt` files).'),
# changes
('- On CPUs 41 and 94 the median reference rate is 70.12 to 70.46 GB/s, between the two limits [Ref8].',
 '- In the copy steps (B1, B2, B3 and C2) the median reference rate on CPUs 41 and 94 is 70.19 to 70.41 GB/s in s1 and 70.12 to 70.46 GB/s in s2. These values lie between the two limits [Ref8].\n- In step B6 the median reference rate on the same two CPUs is 68.76 to 68.91 GB/s. That is below the low limit [Ref8].'),
('3. B2, B3 and C2 were run although B1 at 8 MiB is not resolved by the rule.','3. B2, B3 and C2 were run although the rule gives no resolved difference for B1 at 8 MiB. The word of the rule is "not observed" [Ref6].'),
('   - The two settings differ by 1.06 GB/s. That is inside the limit of 5.23 GB/s. No result word depends on the choice.','   - The two settings differ by 1.06 GB/s in their median D. That is inside the limit of 5.23 GB/s. Steps B8, B5 and B9 did not run with the offset start. So no file shows whether a result word of these steps depends on the choice.'),
('- A word is final only where no item is marked "Open".','- A word is final only where no item is marked "Open". Five rows without the mark are also not final. Open decision 1 (level limits) can change the words of H4, H5 and H6. Open decision 9 (choice A5) can change the words of H7a for read and of H7a for write.'),
('would be irregular in each session [Ref21]. The reproduction condition would then give no value.',
 'would be irregular in each session [Ref21]. The reproduction condition would then give no value. By choice A26 the script then gives "not observed" for H7a and H7b for read in both sessions [Ref5]. A rerun of the analysis with this one change gives these two words. It also gives "rejected" in place of "not rejected" for H7a for write. It also gives "not observed" in both sessions for 4 cells of H11 (old write and asm write, whole passes, offset start, 0.5 s and 15 s). Three of the 4 supported cell results are in these cells [Ref21].'),
('| Limit | `check_listing.py` checks more than B.7 asks. It does not check the code outside the loop for the 5 kernels that have no reference listing. |',
 '| Limit | `check_listing.py` checks more than B.7 asks. For the 8 kernels that have no reference listing of the whole function (`asmcopy_c`, `asmcopy_c_add`, `asmcopy_c_reg`, the four `nop` variants, `read_sparse`) it checks outside the loop only two points: the function has one backward branch, and d8 to d15 are saved and restored where the kernel uses them. `DEVIATIONS-bwx.md` counts these as five kernels, with the four `nop` variants as one [Ref4]. |'),
('| Limit | The loop of `read_sparse` is at offset 4, the other read variants at offset 20 (measured in `offsets.tsv`) [Ref15]. |',
 '| Limit | The loop of `read_sparse` is at offset 4. The loops of asm read, of its A/A copy and of the four `nop` variants are at offset 20. The loop of new read is at offset 36 and the loop of old read is at offset 40 (measured in `offsets.tsv`) [Ref15]. |'),
('- Limit: the loop of `read_sparse` is at offset 4, and the other asm read loops are at offset 20 [Ref4][Ref15].','- Limit: the loop of `read_sparse` is at offset 4. The loops of asm read and of the four `nop` variants are at offset 20, and the loop of old read is at offset 40 [Ref4][Ref15].'),
('8. The short run was checked by an independent agent before Part B [Ref16].','8. The short run was checked by an independent agent before Part B (lead\'s record) [Ref20]. The raw files of the short run are in its folder [Ref16].'),
('| A14 | B4: level changes with equal coverage and counters are counted as a description. |','| A14 | B4: level changes with equal coverage and equal counts `thp_collapse_alloc` and `pgmigrate_success` are counted as a description. |'),
# Ref21 and Files
('and `check_listing-crb-build-1.txt`, `check_listing-crb-build-2.txt` (output of `check_listing.py` on the two listings, run on the development machine on 2026-11-14 UTC).',
 'and `check_listing-crb-build-1.txt`, `check_listing-crb-build-2.txt` (output of `check_listing.py` on the two listings, run on the development machine on 2026-11-14 UTC). The folder `a5-reversed/` holds the rerun of `analyze_bwx.py` on the 28 step folders with choice A5 reversed: the one changed line (`analyze_bwx-a5-reversed.diff`), its `hypotheses.txt` (`hypotheses-a5-reversed.txt`), and the lines that differ from the delivered `hypotheses.txt` (`hypotheses-change.diff`).'),
('`check_listing-crb-build-1.txt`, `check_listing-crb-build-2.txt`) |','`check_listing-crb-build-1.txt`, `check_listing-crb-build-2.txt`, `a5-reversed/`) |'),
]
bad=0
for a,b in R:
    n=t.count(a)
    if n!=1: print('COUNT',n,a[:70]); bad=1
    t=t.replace(a,b)
if bad: sys.exit(1)
open(p,'w').write(t)
print('applied',len(R))
