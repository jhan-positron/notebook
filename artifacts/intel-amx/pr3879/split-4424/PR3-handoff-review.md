**Short version:** Four P2 findings need correction before executing this handoff. The construction recipe reproduces the stated change and passes the local syntax and formatting checks. The findings concern mutation-test selection, machine cleanup, repairs after publication, and performance attribution.

Reviewed `PR3-handoff.md`, SHA-256 `317bea32e3c9c97bcc2aeda16dc858fedd915341f444fb68be214cb9fb43c6c9`, against parent commit `0ee8671d355863658bbf292a12e04a566ac1af29`, the saved patch, and the referenced local scripts. P2 means a correction needed for reliable execution or reporting. PR means pull request. AMX is Intel's matrix instruction set. A mutation check deliberately breaks code to verify that a test detects the break.

**1. Escape the commas in both mutation-test filters.**

The M1 and M2 commands pass test names containing literal commas to Catch2, the C++ test framework. Shell quotation preserves each command-line argument, but Catch2 then interprets its commas as separators between filters. Neither command selects its intended case. The required mutation failure therefore cannot be established by these commands. [Handoff: M1 and M2](PR3-handoff.md:257).

Use these filters:

```bash
./gen/t_k_vnni_layout --skip-benchmarks \
  "VNNI K block save equals the per-token row store\, bit for bit"

./gen/t_llama_unit --skip-benchmarks \
  "save_k stores every token's K row once\, grouped by page block\, alone or with helper threads"
```

- **Evidence:** I compiled a small fixture containing the two exact test names with Catch2 3.7.1, the version pinned by this tree. Both original filters returned exit status 2 and printed `No tests ran`. Each corrected filter executed its single intended fixture case and returned exit status 0. This verifies filter selection, not the product's mutation behavior. [Fixture results](/tmp/pr3-handoff-review.t0c2og3n/catch-filter/results.json), [version pin](/tmp/pr3-handoff-review.t0c2og3n/tree/cmake/versions.cmake:26).
- **Acceptance check:** Before changing production code, list the selected tests on each actual binary and require exactly the intended case. After mutation, require the specified assertion failure. An unsuccessful command that ran no tests is not a successful mutation check.

**2. Add serving restoration to the chain's early-exit cleanup.**

Step 6 directs the executor to copy the PR-2 chain. That chain's exit handler only releases the shared-machine marker and prints machine status. Serving restarts in the normal execution path near the end of the script. An exit after serving has stopped but before that point leaves serving down while releasing the marker. This is an inherited script defect that the PR-3 instructions do not address. [Handoff: chain source](PR3-handoff.md:249), [source exit handler](/home/jhan/workspace/intel-AMX/exec/pr2-20261011/chain.sh:86), [normal restoration](/home/jhan/workspace/intel-AMX/exec/pr2-20261011/chain.sh:222).

The child campaign does not provide a fallback. The chain exports `SKIP_SERVING_UP=1`, which tells the campaign that its parent will restore serving. [Chain setting](/home/jhan/workspace/intel-AMX/exec/pr2-20261011/chain.sh:66), [campaign behavior](/home/jhan/workspace/intel-AMX/exec/sync4424-20261002/campaign.sh:127).

- **Evidence:** I extracted the existing exit handler and ran it in a local shell fixture with external actions replaced by logging stubs. Exiting with status 17 invoked marker release and no serving restoration. No test-machine action occurred. [Fixture](/tmp/pr3-handoff-review.t0c2og3n/cleanup-fixture.sh), [result](/tmp/pr3-handoff-review.t0c2og3n/cleanup-fixture.txt).
- **Fix:** Require one cleanup function for normal completion and early exits. It should stop this chain's remaining workload and wait for it to exit, restore serving when the chain owns that responsibility, and release the marker. Preserve the lease checks that prevent interference when nightly testing has taken the machine. Record restoration failure explicitly.
- **Acceptance check:** With local stubs, exercise normal completion, an explicit failure after serving stops, and termination. Check that restoration precedes marker release when the lease remains free. Also check the path where nightly testing has taken the lease.

**3. Keep the three-commit reconstruction procedure limited to unpublished work.**

Step 7 says to repair a published lint failure through the reconstruction script, rerun step 4, and push. Step 1.5 defines that script as resetting the branch to its parent and recreating the three commits. A repair made this way replaces published history. A normal push cannot publish it, and section 9 forbids force-pushing. The executor cannot satisfy all three instructions. [Reconstruction procedure](PR3-handoff.md:185), [post-publication repair](PR3-handoff.md:288), [push restriction](PR3-handoff.md:407).

- **Evidence:** A local Git fixture recreated three commits from their original parent. The published head was not an ancestor of the replacement head: `git merge-base --is-ancestor` returned exit status 1. This is the condition that prevents a normal push from extending the published branch. [Fixture result](/tmp/pr3-handoff-review.t0c2og3n/history-check.json).
- **Fix:** Keep reconstruction for steps before the first push. After publication, preserve existing commits and append a focused repair commit. Update step 5's commit-count restriction accordingly. Run the checks required by the repair, and retain the actual measured revisions in the body until any required new measurements finish.
- **Acceptance check:** Before each post-publication push, require the fetched published head to be an ancestor of the proposed head.

**4. Do not exclude the store itself when investigating a decode difference.**

Section 5.5 says a decode-throughput difference between `newoff` and `headoff` beyond the decision band (the handoff's threshold for run-to-run variation) means the trees differ in work “outside the store.” These arms are PR-3 and PR-2 with AMX disabled. The store's execution changes even when a decode batch is too small to use helper threads. The same scatter operation does not establish identical work around that operation. [Handoff: performance interpretation](PR3-handoff.md:347).

PR-2 stores and marks each token in one loop. PR-3 first calls `store_k_block`, which discovers token groups even for single-token stores. It then traverses the batch again to mark completed tokens. The new helper calls also evaluate whether sharing applies before returning. These are changes inside the store path. [Parent store](/home/jhan/workspace/ai-runs/tron-split-pr2/h/tron/models/model.hpp:3091), [reconstructed grouping](/tmp/pr3-handoff-review.t0c2og3n/tree/h/tron/models/model.hpp:3230), [reconstructed completion loop](/tmp/pr3-handoff-review.t0c2og3n/tree/h/tron/models/model.hpp:3367).

```text
PR-2: [store token → mark token] × batch
PR-3: [group and store all tokens] → [mark all tokens]
```

- **Evidence strength:** The execution-path difference is established by code inspection. **Insufficient data:** its timing effect at the final PR-3 revision.
- **Replacement text:** “Both arms disable AMX. Decode throughput is expected to remain within the decision band. A difference beyond that band needs investigation, including the changed store grouping and completion loop.”
- **Discriminating measurement:** Compare the final binaries in the prescribed matched campaign. If a difference persists, measure the `Save K` spans, which time the store operation, for the same decode workload. Treat unchanged throughput in the body outline as an expectation until the measurements support it.

**Two smaller factual corrections**

- M2's final sentence says neither mutation changes behavior in the option-off build. M1 still changes the direct packed-storage test there. That test calls `store_block` independently of the option. Replace the sentence with: “Run both checks in the option-on worktree. M1 also affects the direct block-store test with the option off. M2 requires the option-on shared-store path.” [Handoff](PR3-handoff.md:258), [direct test call](/tmp/pr3-handoff-review.t0c2og3n/tree/t/t_k_vnni_layout.cpp:256).
- The requested continuous integration (CI) paragraph says both new cases run on the row-major path when the option is off. The direct block-save case still tests packed storage. Only the `save_k` case selects the row-major store. Section 1 already states this correctly. Reuse that distinction in the body instructions. [Body outline](PR3-handoff.md:370), [correct earlier explanation](PR3-handoff.md:78).

**Verified construction and review limits**

- Applied the saved patch in an isolated repository under `/tmp`. The three conflicting files and four conflict blocks matched the handoff.
- Ran the supplied exact-text resolver successfully. Applied both conversion edits exactly once. The result contains 9 changed files, 678 added lines, and 78 removed lines. [Measured counts](/tmp/pr3-handoff-review.t0c2og3n/numstat.txt).
- Compared the result with the tested source tree `ba69cb513e`. The changed-file totals match the documented residual differences, including the two conversion edits in `model.hpp`. [Comparison](/tmp/pr3-handoff-review.t0c2og3n/diff-vs-ba69-after-edit.patch).
- Clang-format 19.1.7 passed on all 7 changed C++ files. `git diff --cached --check` passed. [Formatting result](/tmp/pr3-handoff-review.t0c2og3n/format.txt).
- All 22 syntax-matrix cells returned exit status 0 with no compiler errors. The matrix used the cached Zig 0.14.0 / Clang 19.1.7 compiler and the existing header mirror. It checks parsing and template instantiation. [Matrix result](/tmp/pr3-handoff-review.t0c2og3n/syntax/matrix.log).

The 38-cell extension, Haskell compilation, product builds, runtime mutation checks, and remote measurements were not run during this document review. **Insufficient data:** runtime correctness and performance of the final PR-3 branch. The corrected handoff's build and machine tests must establish those results. The source handoff and working branches were left unchanged. No GitHub write or remote workload was performed.
