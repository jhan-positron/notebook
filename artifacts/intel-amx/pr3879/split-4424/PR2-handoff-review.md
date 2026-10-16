**Short version:** Four findings need correction before executing this handoff. The branch-construction instructions reproduce the intended change, including preservation of PR-1's review fixes. The findings concern experiment configuration, incomplete smoke results, interpretation of timings, and measurement provenance after a parent update.

Reviewed `PR2-handoff.md`, SHA-256 `96cc7fc1d97aff40c8939153565e02167699bf56ec22054ee37f7c755c77d3af`, against PR-1 commit `82d05e94bea0dda172c9d23a7b5f58e90a7d7f49` and the referenced local scripts. PR means pull request. AMX is Intel's matrix instruction set. An arm is one binary with one environment setting. All four findings are P2: corrections needed for reliable execution or reporting.

**1. Set the summarizer's arm list as well as the campaign's arm list.**

Step 6 E specifies `ARMS="base new newoff head"` and the comparison pairs, but omits `WEDPERF_ARMS`, the separate list used by the result summarizer. The prescribed source script, `chain3.sh`, sets that list to `base new newoff baseoff`. Keeping that setting drops `head`, the PR-1 binary, from the summary. Removing the setting instead selects the summarizer's default list, which drops `new` and `newoff`. Neither produces the requested comparisons. [Handoff: step 6 E](PR2-handoff.md:243), [source chain](/home/jhan/workspace/intel-AMX/exec/pr1-20261010/chain3.sh:145), [summarizer](/home/jhan/workspace/intel-AMX/exec/sync4424-20261002/summarize.py:25).

- **Evidence:** A local parser check used historical logs with one arm renamed as a fixture. The inherited setting produced 6 arm rows and 4 comparison rows. The default setting produced 4 arm rows and no comparison rows. The corrected setting produced the required 8 arm rows and 8 comparison rows. These are parser checks, not PR-2 performance measurements. [Results](/tmp/pr2-handoff-review.nv3jNe/script-checks.json).
- **Fix:** Add `WEDPERF_ARMS="base new newoff head"` to step 6 E. Require the summary to contain all four arms and all four requested pairs for each prompt length. Check at least 3 usable repetitions for each metric and pair before filling the body.

**2. Require complete token files before accepting a smoke verdict.**

The reused smoke checker compares only the shorter of two token sequences. It reports success when that common prefix matches, even if the lengths differ or both runs ended early. Its success marker therefore does not establish the handoff's requirement of 256 matching generated tokens. [Handoff: smoke setup](PR2-handoff.md:242), [handoff: pass criteria](PR2-handoff.md:292), [checker](/home/jhan/workspace/intel-AMX/exec/sync4424-20261002/smoke.sh:75).

- **Evidence:** I executed the checker extracted from `smoke.sh` against synthetic token files. Five files containing only 1 token each returned `SMOKE-VERDICT ok`. A second fixture with 255 tokens in `new2` and 256 tokens in every other arm also returned `SMOKE-VERDICT ok`. [Short-file result](/tmp/pr2-handoff-review.nv3jNe/smoke-short/verdict.txt), [unequal-length result](/tmp/pr2-handoff-review.nv3jNe/smoke-unequal/verdict.txt).
- **Fix:** Require successful process exits and exactly 256 generated tokens in every requested arm before accepting a cell. Add this check to the PR-2 script fork or a separate validator. Verify that both incomplete fixtures fail and that a complete matching fixture passes. Do not treat `smoke.done=ok` alone as proof.

**3. Do not classify a disabled-AMX timing difference as measurement error in advance.**

Section 5.5 says a difference between `newoff` and `head` beyond the decision band is “a finding about the measurement, not about the code.” Those arms perform different work. PR-1 with AMX enabled still allocates query-packing storage, enters an AMX region, and packs queries before its temporary gate sends pages to the software reader. PR-2 with `TRON_AMX_DISABLE=1` skips that preparation. Using the same score reader does not make these execution paths identical. [Handoff](PR2-handoff.md:307), [PR-1 region setup](/home/jhan/workspace/ai-runs/tron-split-pr1/h/tron/models/self_attention.hpp:1539), [PR-1 pack call](/home/jhan/workspace/ai-runs/tron-split-pr1/h/tron/models/self_attention.hpp:1631), [PR-1 dispatch-test contract](/home/jhan/workspace/ai-runs/tron-split-pr1/t/t_amx_dispatch_dtype.cpp:11).

- **Evidence strength:** The execution-path difference is established by code inspection. **Insufficient data:** its timing contribution at the PR-2 head.
- **Fix:** Replace the sentence with: “Both arms use the software reader. PR-1 with AMX enabled also prepares queries for an unused AMX path. Investigate any difference beyond the decision band before attributing it to measurement variation.”
- **Discriminating measurement:** Add a diagnostic `headoff` arm, meaning PR-1 with AMX disabled, if this discrepancy occurs. Compare `head` with `headoff` to measure the preparation difference within PR-1. Compare `newoff` with `headoff` to check the two binaries with AMX disabled in both. This remains a diagnostic proposal, not a measured explanation.

**4. Refresh performance evidence when a parent code update changes the measured tree.**

Step 8 tells the executor to merge a new PR-1 head, rerun local checks, unit tests and possibly smokes, then update the body's commit identifiers and date. It omits performance step E. An attention or cache change can alter performance while preserving tokens and passing unit tests. Updating the measurement provenance after those checks would associate old timings with an unmeasured revision. This conflicts with section 6's requirement to report the final head against the specified base and parent. [Parent-update procedure](PR2-handoff.md:263), [measurement provenance rule](PR2-handoff.md:315).

- **Fix:** For a parent update affecting measured code, rebuild the parent comparator and rerun E on the merged PR-2 head. Update each measurement's provenance only after that run. Until then, keep the actual measured identifiers and mark final-head performance as pending. A comment-only update may retain prior measurements if the report explicitly identifies the measured revision.
- **Acceptance check:** Every published performance table must map to result files recording the displayed PR-2, PR-1 and base revisions. Syntax checks and token comparisons do not satisfy this requirement.

**Verified construction and review limits**

- Applied the saved patch in an isolated repository under `/tmp`. Eight files applied cleanly. The only conflict was the documented dispatch diagram.
- Applied the five comment replacements directly from the handoff. Each old text matched exactly once. The resulting diff contains 10 files, 285 added lines and 72 removed lines. These measured counts can replace the estimate in section 3.
- Compared the reconstructed files with probe commit `4d3a042225`. Differences remain only in the documented files: the permanent CMake-option wording, token-index checks, conditional test tolerances, and tests inherited from main. The other seven files match the probe.
- Clang-format 19.1.7 passed on all 9 changed C++ files. `git diff --check` passed.
- All 22 syntax-matrix cells returned exit status 0 with no compiler errors. The matrix used the existing flags and cached Zig 0.14.0 / Clang 19.1.7 directly, avoiding a package download. This checks parsing and template instantiation, not linking or runtime behavior. The 38-cell extension and failure controls were not run during this document review. [Matrix log](/tmp/pr2-handoff-review.nv3jNe/syntax/matrix.log), [cell results](/tmp/pr2-handoff-review.nv3jNe/syntax/out/review/summary.txt).

No product build, AMX runtime test, remote workload, or GitHub write was performed. **Insufficient data:** runtime correctness and performance of the final PR-2 branch. The corrected handoff's build and machine tests must establish those results. The source handoff and working branches were left unchanged.
