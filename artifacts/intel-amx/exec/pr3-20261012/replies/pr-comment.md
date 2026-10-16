Reply to the review round of 2026-10-12 (the five passes at `80bce9a08d` and the inline comment on `t/t_llama_unit.cpp`).

**tron-code-review, [P2] "Observe completion when the main save returns": accepted and fixed in `dfafd13dce`.** The three-thread section now reads the window's `finished` count right after the main thread's `save_k` returns, before the test joins its threads, and requires it to equal the helper count (0 with the option off, where no window opens). The last helper starts 20 ms late, so the production join has to wait for it. The mutation check you asked for ran on the Granite Rapids test machine: with the production join removed (its loop condition replaced by `false`), the case fails at `REQUIRE( finished_at_return == n_workers - 1 )`: The run reports 1 of 1 test cases failed and 1 of 2541 assertions failed, at the `REQUIRE` of `t/t_llama_unit.cpp:4028` (2540 earlier assertions passed). With the file restored, the whole binary passes again with 269328 assertions in 66 cases. The fixed test passes in the three builds: 269328 assertions in 66 cases with the option on, the same with the option on and AMX dispatch off, and 269069 assertions in 66 cases with the option off. The description's test bullet and its Verification section say so.

**wade-code-review, [P3] "Calculate the band from unrounded standard deviations": accepted.** The bands are now computed from the full-precision standard deviations of the recorded repetitions. Your nine values are exact: the tp2 prompt-1024 bands are 0.87, 0.43, 0.77 and 0.87 TPS, the tp4 prompt-1024 bands 0.95, 1.25, 0.71, 1.33 and 1.25 TPS, in the pair table and in the prose. The TTFT bands and every inside/beyond classification are unchanged.

**plain-english pass: accepted, with three additions.** The description now is your proposed text with the band correction, plus these three changes.

- The Short version's second sentence keeps the decode-throughput result ("unchanged inside the decision band"), and its third sentence names the fourth PR's row-major tail block. The stack's description rules ask the Short version to carry the measured TPS result and the state of the stack.
- The `t_llama_unit` bullet describes the late helper and the finished count read at return.
- Verification says that the head `dfafd13dce` differs from the measured revision `80bce9a08d` by the test commit alone, and it lists the third mutation check.

**ben-review and the normal review:** nothing to change. The "one unidentified skip" of the host suite is the count the suite summary reports. The description states the count, and it names `t_proxy_lib` only as the skip the acceptance rules permit.

The branch was not rebased: the fix is one commit on top of the reviewed head. The measurements stay at `80bce9a08d`, since the commit changes a test and nothing else.
