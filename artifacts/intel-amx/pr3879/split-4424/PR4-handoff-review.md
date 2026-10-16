**Short version:** Five findings need correction before executing this handoff. Two concern shared-machine cleanup in the inherited campaign script. The branch recipe reproduces the documented tree exactly and passes the local formatting, whitespace, and 22-cell syntax checks.

Reviewed `PR4-handoff.md`, SHA-256 `401d2b1017b408093dfbe604e9d7574999b08be4f2ce1ca0481f66c9f116a5a1`, against parent commit `dfafd13dce74376ebc762eafa9763684dd021d03`, the saved patches, the resolver, and the referenced local scripts. The source document still had this hash at the final check. [Verification record](/tmp/pr4-handoff-review.d1he2l9w/verification.json).

Words used here:

- PR means pull request. PR-3 is the parent change. PR-4 is the change this handoff constructs.
- W is the separately launched whole-machine package benchmark. The chain is the build-and-test script that runs before W.
- Bill's marker grants a colleague access to half of the shared test machine when present. The pre-check marker tells W that the chain is still using the machine.
- CI means continuous integration. Its lease records whether nightly testing owns the machine.
- P1 means fix before machine execution. P2 means a correction needed for reliable execution or reporting.

**1. [P1] W must release Bill's marker only when it owns that responsibility.**

The proposed schedule starts W while the chain still holds the machine. W waits for the pre-check marker to disappear. If W receives SIGTERM during that wait, its signal handler calls `restore_and_release`. That function unconditionally calls `bill release`, even though W has not reached its marker-acquisition step. The release recreates Bill's marker while the chain can still be running whole-machine tests. An early abort during this wait has the same problem. [Handoff: campaign and schedule](PR4-handoff.md:402), [signal handler](/home/jhan/workspace/intel-AMX/exec/pr4424ci-20261009/campaign.sh:257), [unconditional release](/home/jhan/workspace/intel-AMX/exec/pr4424ci-20261009/campaign.sh:251), [release semantics](/home/jhan/workspace/intel-AMX/exec/bill-share.sh:49).

```text
Chain holds machine → W waits → W stops → W releases marker
```

- **Evidence:** I extracted the actual restore function into a local fixture. With no restore target recorded, it still called `bill release`. All external actions were logging stubs. [Fixture results: `waiting-for-precheck`](/tmp/pr4-handoff-review.d1he2l9w/cleanup-results.json).
- **Fix:** Add marker ownership tracking to the W fork. Set it only after W has acquired the machine through the intended protocol. Gate release on that state. The chain already has a separate ownership flag, but W does not use the chain's handler.
- **Acceptance check:** Interrupt W while it waits for the chain. Require no marker release and no machine mutation. Also test normal completion after W acquires ownership, with exactly one release.

This is an inherited script defect that becomes directly relevant to the handoff's concurrent launch schedule.

**2. [P1] W's restore path must respect a CI takeover.**

W detects a busy CI lease between passes and treats driver exit status 9 as a takeover. Both paths then reach `restore_and_release`. That function performs package restoration, configuration changes, and serving restarts without checking the lease. The corresponding `dut.sh` operations also lack a lease check. A detected takeover can therefore be followed by changes to the machine that CI now owns. [Handoff: lease rule](PR4-handoff.md:394), [takeover exits](/home/jhan/workspace/intel-AMX/exec/pr4424ci-20261009/campaign.sh:458), [driver takeover](/home/jhan/workspace/intel-AMX/exec/pr4424ci-20261009/campaign.sh:472), [restore path](/home/jhan/workspace/intel-AMX/exec/pr4424ci-20261009/campaign.sh:217), [package installation helper](/home/jhan/workspace/intel-AMX/exec/pr4424ci-20261009/dut.sh:113).

- **Evidence:** In a local fixture with busy-lease stubs available, the actual restore function called configuration clearing, package installation, serving-down, and serving-up. It consulted neither lease stub. No remote action occurred. [Fixture results: `ci-busy-after-driver`](/tmp/pr4-handoff-review.d1he2l9w/cleanup-results.json).
- **Fix:** Add an explicit CI-takeover cleanup path to W. Stop its own workload, record deferred restoration, and avoid package, serving, configuration, and sharing-marker changes while CI owns the machine. Recheck ownership before later restoration, including after reconnecting to an unreachable machine.
- **Acceptance check:** Exercise a takeover between passes, driver exit status 9, and reconnection while the lease is busy. Require no shared-machine mutation in those paths. Retain normal restoration when the lease remains free.

The existing chain handler checks the lease before restoring serving. That protection does not extend to W, which has its own restore function. [Chain handler](/home/jhan/workspace/intel-AMX/exec/pr3-20261012/chain-finish.sh:29).

**3. [P2] Make W's retry policy and acceptance criteria agree.**

The schedule allows time for one failed pass to succeed on retry. Section 5.4 then requires a successful campaign outcome. The inherited script increments `fails` on the first unsuccessful attempt and never clears that count after a successful retry. It consequently creates `.done-with-failures` even when every final pass succeeds and no incomplete pass remains. Following the schedule can produce results that the acceptance criteria reject. [Handoff: retry allowance](PR4-handoff.md:405), [acceptance criteria](PR4-handoff.md:421), [failure counter](/home/jhan/workspace/intel-AMX/exec/pr4424ci-20261009/campaign.sh:475), [successful retry](/home/jhan/workspace/intel-AMX/exec/pr4424ci-20261009/campaign.sh:494), [final verdict](/home/jhan/workspace/intel-AMX/exec/pr4424ci-20261009/campaign.sh:507).

The same acceptance paragraph says `outcome.txt` must say `done`. That file never contains the completion marker. It records incomplete passes, stop reason, problems, and known systematic failures. The successful October 9 record follows that format. [Recorded outcome](/home/jhan/workspace/intel-AMX/exec/results/pr4424ci-20261009/outcome.txt).

- **Evidence:** A local fixture executing the script's retry block produced `repeat ok`, followed by `.done-with-failures: fails=1`, with empty incomplete-pass, stop-reason, and problem fields. [Fixture result](/tmp/pr4-handoff-review.d1he2l9w/retry-verdict-result.json).
- **Fix:** Define whether a successful retry is acceptable. If it is, distinguish recovered attempts from unresolved failures in the W fork. Preserve the failed attempt's record. Define acceptance using the actual marker files, `outcome.txt` fields, complete final pass data, and successful restoration. If retries remain disqualifying, say so in the schedule.
- **Acceptance check:** A first-attempt failure followed by a complete successful retry must receive the documented verdict. Two failed attempts, an incomplete cell, and failed restoration must remain failures.

**4. [P2] Match the plugin-verification claim to the check that actually runs.**

Step 6 retains the generated-plugin check and includes it in the required build verdict. Section 6 instead instructs the body to say that this check was not repeated. It also claims that every generated plugin is byte-identical to PR-3 and that the chain verifies that identity. The copied `plugin-calls.py` only counts selected call forms in one directory. It neither reads the parent directory nor compares file bytes. [Handoff: retained check](PR4-handoff.md:288), [body instruction](PR4-handoff.md:456), [checker implementation](/home/jhan/workspace/intel-AMX/exec/pr3-20261012/plugin-calls.py:15).

- **Evidence:** I ran the actual checker on two local fixture directories. One fixture passed the correct K buffer to both store calls. The other passed a different buffer. Both returned exit status 0 with identical call counts. This establishes the check's limits, not a defect in the generated product plugins. [Fixture results](/tmp/pr4-handoff-review.d1he2l9w/plugin-check-results.json).
- **Fix:** Say that the Haskell test suite is skipped and the plugin call-form check is repeated. Remove the byte-identity claim unless the chain also compares the complete filename sets and bytes of the parent and candidate plugin directories.
- **Acceptance check:** If byte identity is retained as a requirement, changing a buffer argument, adding a file, or removing a file must fail that comparison.

**5. [P2] The two AMX-disabled arms change scoring as well as storage.**

Section 5.5 describes `newoff` and `headoff` as both using the packed reader for converted blocks and the row-major dotter for the tail. Here AMX is Intel's matrix instruction set, `newoff` is PR-4 with AMX disabled, and `headoff` is PR-3 with AMX disabled. The packed reader scores interleaved key data with vector instructions. The row-major dotter scores one contiguous key row at a time. PR-3 has no row-major tail path for the enabled packed layout. It scores every relevant token through the packed reader. PR-4 adds the row-major dotter for unconverted blocks. [Handoff: comparison interpretation](PR4-handoff.md:431), [parent scoring path](/tmp/pr4-handoff-review.d1he2l9w/parent-self_attention.hpp:1939), [reconstructed scoring path](/tmp/pr4-handoff-review.d1he2l9w/tree-final-parent/h/tron/models/self_attention.hpp:2020).

```text
headoff: every relevant packed-layout token → packed reader
newoff:  converted block → packed reader
         unconverted block → row-major dotter
```

The proposed investigation measures only `Save K` and `convert_k_blocks`, which time storage and conversion. Those spans cannot distinguish a scoring-cost change. Calling this pair “the store change under the reader path” overstates what the comparison isolates.

- **Evidence strength:** The different execution paths are established by source inspection. **Insufficient data:** their timing effect at the constructed PR-4 revision.
- **Replacement text:** “Both arms disable AMX. PR-4 changes storage, conversion, and the scoring of unconverted blocks. Report their combined effect. Investigate a difference using storage, conversion, and software-attention timings for the same workload.”
- **Related correction:** Keep the next bullet's expected kill-switch effect explicitly provisional. An unchanged store within PR-4 does not establish that its kill-switch effect equals PR-3's effect, since PR-4 changes the scoring paths.

**Smaller consistency corrections**

- Choose one base-package build mode. Step 6 and section 5.3 put both package builds on named local branches. Section 8 says the base is detached. Section 7 requires every package version to contain the branch name. The detached recipe cannot satisfy that condition. Follow the detailed named-branch recipe and remove the detached-base instruction. [Build recipe](PR4-handoff.md:400), [stop condition](PR4-handoff.md:476), [contradictory instruction](PR4-handoff.md:489).
- Section 3's deviation 7 calls the mutation checks “hardware-attention policy” and “dense gate.” The actual rows test page-state completion and the hardware-attention policy. Update the overview so the executor does not report an unperformed dense-gate mutation check. [Overview](PR4-handoff.md:139), [actual checks](PR4-handoff.md:308).
- Section 3, deviation 1 describes a five-commit split. Step 3 has three initial commits plus one cost-row commit. Use the four-commit total throughout. [Deviation 1](PR4-handoff.md:133), [commit recipe](PR4-handoff.md:240).

**Verified construction and review limits**

- Reconstructed the change in an isolated repository under `/tmp`, starting at `dfafd13dce`. The tail patch produced the documented five conflicting files and five conflict blocks. The current resolver applied every resolution and both test additions successfully. The preset patch applied cleanly. [Apply record](/tmp/pr4-handoff-review.d1he2l9w/apply-final-parent.txt), [resolver record](/tmp/pr4-handoff-review.d1he2l9w/resolve-final-parent.txt).
- Applied and staged the specified `<cstring>` edit. The result has 12 changed files, 1,476 added lines, and 120 removed lines. Its diff against reference merge `c4bf86005a` matches the saved probe diff byte for byte. [Change counts](/tmp/pr4-handoff-review.d1he2l9w/numstat-final.txt), [reference comparison](/tmp/pr4-handoff-review.d1he2l9w/reference-final.patch).
- Clang-format 19.1.7 passed on all 10 changed C++ files. `git diff --cached --check` passed. [Formatting result](/tmp/pr4-handoff-review.d1he2l9w/format-final.txt).
- All 22 syntax-matrix cells returned exit status 0 with no compiler errors. The check used the cached Zig 0.14.0 / Clang 19.1.7 compiler and the existing header mirror. It establishes parsing and template instantiation only. [Matrix result](/tmp/pr4-handoff-review.d1he2l9w/syntax/matrix.log).

The 38-cell extension, product builds, runtime mutation checks, hardware tests, package builds, cost measurements, and performance campaigns were not run during this review. **Insufficient data:** runtime correctness, token identity, and performance of the constructed PR-4 tree. The corrected handoff's machine runs must establish them. The source handoff and working branches were left unchanged. No remote workload or GitHub write was performed.
