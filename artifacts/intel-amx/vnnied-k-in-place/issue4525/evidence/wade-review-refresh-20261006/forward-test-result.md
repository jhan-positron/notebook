# Frozen miniature pull request reviews

Short version: PR A permits reads before the producing work has completed. PR B's tests do not establish the transfer guarantees in its description. PR C has no supported findings, and PR D can resolve its reporting defects by narrowing the documented scope.

PR means pull request. HEAD means the reviewed revision. CI means continuous integration, the automated build and test jobs. Severity P1 means a high-priority correctness defect, and P2 means a normal-priority defect or coverage gap.

## PR A — HEAD a1

Review boundary: repository `positron-ai/example`, target branch `release`, supplied base revision `r1`.

### P1 — Correctness: preserve readiness for every value physically loaded

The changed dependency waits for only the first 32 value slots. [dependencies:10] The consumer still loads all 64 slots. [vector_reader:40] The other minibatch can be writing slots 32 through 63 when those loads occur. Zero attention weights do not establish readiness or prevent those reads. An unfinished value can therefore enter the multiplication and reduction. A not-a-number value multiplied by zero can also contaminate the result.

Restore the dependency on the writers of every loaded slot. Alternatively, make the consumer avoid loads from unfinished slots. The existing test initializes every slot to a finite value before execution. It cannot expose this failure. [attention_test:7] Add a shared-page case that delays the second writer and verifies the required ordering. The recorded success at `a1` does not establish unchanged numerical behavior under that input contract.

## PR B — HEAD b1

Review boundary: supplied target branch `main`. The artifacts do not identify a repository or base commit.

### P2 — Coverage and inaccurate claim: execute the host-only assertions in CI

The test returns success before its assertions when matrix hardware is unavailable. [grouped_test:5] The supplied CI host lacks that hardware. Its successful run therefore does not verify the assertions in this test. All the supplied checks use ordinary host arithmetic.

Move these checks outside the hardware gate. Record a run in which the assertions execute before claiming CI verification. Compilation and a successful early return do not establish destination or length correctness.

### P2 — Coverage: use an independent expected address

The expected address uses `pair_base`, the production address helper. [grouped_test:6] The writer uses the same helper. [grouped_test:7] A shared address error can satisfy the readback comparison. [grouped_test:8]

Derive the expected address independently from the required layout. Include a boundary case that distinguishes the intended mapping from a plausible wrong mapping. Removing the hardware gate alone would leave this coverage gap.

### P2 — Coverage: check transfer destinations and lengths

The transfer fake discards every descriptor field and records only the submission count. [fake:30] The test checks only that there are two submissions. [grouped_test:20] Two transfers with incorrect destinations or lengths would still pass.

Have the fake retain the relevant descriptor fields. Assert their destinations and lengths against independent expectations. The supplied evidence establishes a test limitation, not an implementation error in the transfer helper.

### P2 — Coverage: exercise the production grouping and ownership route

The test calls the low-level transfer helper directly. [grouped_test:20] Production grouping, destination reservation, and transfer of buffer ownership to completion tracking occur in `dispatch`, the production orchestration function. [dispatch:45] Incorrect shard grouping or an omitted ownership handoff in that caller could leave the new test passing.

Exercise `dispatch` with inputs that require grouping. Observe the reserved destinations and ownership through completion. This protection is distinct from checking descriptors at the low-level helper.

Insufficient data to conclude that production transfers are correct: the supplied run skips the assertions, the expected address shares the production helper, and the fake discards the claimed properties. An executed production-route test with independent expectations and descriptor observations would resolve those gaps. No production transfer defect is established by these artifacts.

## PR C — HEAD c1

Review boundary: supplied target branch `main`. The artifacts do not identify a repository or base commit. No supported findings.

- The literal halfway-value expectations protect a published external format. They are justified compatibility checks. [format_test:10]
- The even-source test observes its clearing branch before any later write can hide a failure. [append_even:20] The odd-source test independently observes the other clearing branch. [append_odd:30] Removing either test would lose distinct protection.
- The value-suffixed constants follow the explicit user instruction and the established file convention. Their roles are distinct. No naming change is warranted. [constants:40]
- Zero tracked hardware layers is a supported software-only mode. The absent hardware lookup entry is valid in that mode. No assertion or rejection is warranted from the supplied evidence. [runtime contract:50]

The supplied execution record states that all tests compiled and ran at `c1`. This review does not claim an independent rerun.

## PR D — HEAD d1

Review boundary: supplied target branch `main`. The artifacts do not identify a repository or base commit.

### P2 — Inaccurate metric scope: account for or exclude software waits

The software-only path polls peer completion without starting `join_wait`, the new waiting-time metric. [join:20] Only the hardware wait is timed. [join:10] The description promises both kinds of wait. A reported zero therefore cannot establish that no peer-software waiting occurred.

The smallest accepted remedy is to document hardware waits as the metric's current scope. Measuring peer-software waits can remain deferred under the author's stated allowance. Implementing that additional timing is not required if the claim is narrowed.

### P2 — Inaccurate row identity: do not describe changing worker roles as threads

The cumulative row uses an attention-worker index whose pool-thread assignment can change after a worker split. [stats:30] Contributions from different threads can therefore accumulate in the same row. The documentation's promise of totals per thread is unsupported.

Narrow the documentation to cumulative totals by attention-worker index. State that thread assignment can change. Stable thread identity can remain deferred under the author's allowance. If per-thread totals are retained as the contract, the row key must instead identify the thread consistently.

No timing measurement was supplied. These findings concern demonstrated scope and identity mismatches. They do not establish the number of missing wait milliseconds or any instrumentation slowdown.

## Completion and evidence limits

- Applied the staged `wade-code-review` skill and its three linked references. Used the frozen cases as the sole evidence for these miniature PRs. Historical examples did not substitute for evidence at the supplied HEAD locations.
- Traced physical reads and readiness in A. Checked assertion reachability, expected-value independence, descriptor observations, and production entry points in B. Checked format contracts, distinct observations, naming instructions, and supported fallback in C. Compared instrumentation paths and row identity with the promises in D.
- No executable repository, actual PR numbers, branch histories, or merge-base records were supplied. Insufficient data to verify those metadata or extend this review beyond the frozen artifacts. PR A's `r1` is recorded as its supplied base, without asserting that it is a verified merge base.
- Ran no tests and made no network requests. The outcomes described above are the supplied records, not newly measured results. No source or skill files were edited. This report is the only output file written.
