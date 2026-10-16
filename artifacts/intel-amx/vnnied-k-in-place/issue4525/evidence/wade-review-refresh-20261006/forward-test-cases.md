# Frozen review artifacts

Use the provided skill to review each miniature PR from these artifacts. Treat the numbered lines as HEAD locations. There is no repository or network evidence beyond this document. Report supported findings and material missing evidence, with severity. Do not edit anything. The snippets are pseudocode descriptions of the actual behavior, not language syntax exercises.

## PR A: narrower attention dependencies

Metadata: repository positron-ai/example, base branch release, HEAD a1, base r1. The body says: "Only wait for causally visible tokens; numerical behavior remains unchanged."

Changed file dependencies, line 10: readiness waits for tokens 0 through 31 for a first minibatch.
Unchanged consumer vector_reader, line 40: load all 64 value slots in the page; multiply each loaded value by its attention weight; sum the products.
Input contract: two independently scheduled minibatches share a page. The second writes slots 32 through 63. Those slots have zero weights in the first minibatch, but can contain uninitialized values before the second writer completes.
Test file attention_test, line 7: initialize all 64 value slots to finite values before either minibatch runs. Assert output equals the old implementation.
The test report says success on HEAD a1. No concurrent shared-page test exists.

## PR B: grouped transfers

Metadata: HEAD b1, base main. Body: "Grouping preserves exact destinations and lengths, verified in CI."

File grouped_test, line 5: if matrix hardware unavailable, return success.
Line 6: compute the expected address using production helper pair_base.
Line 7: write a packed slot using writer, which also calls pair_base.
Line 8: compare the readback with the expected address.
Line 20: call the low-level transfer helper directly; check fake.submission_count equals 2.
Fake file line 30: submit(descriptor) increments submission_count and ignores all descriptor fields.
Production caller dispatch, line 45: group by shard, reserve destinations, submit groups, hand off buffer ownership to completion tracking. The new test never calls this function.
CI metadata: builds grouped_test and runs it on a host without matrix hardware. All code above uses ordinary host arithmetic; no matrix instruction is needed. The test log reports success without assertion counts.

## PR C: external representation and supported fallback

Metadata: HEAD c1, base main. User instructions: preserve the established value-suffixed constant names in this file.

Format specification: external readers require the high 16 bits of a 32-bit value exactly, with low bits discarded. This includes halfway rounding cases. It is a published compatibility contract.
Test format_test, line 10: check two halfway values against literal expected 16-bit values from the format specification.
Test append_even, line 20: append from an even source, leaving the adjacent odd destination poisoned; immediately verify that partner was cleared by the even-source clearing branch.
Test append_odd, line 30: append from an odd source, leaving the adjacent odd destination poisoned; immediately verify that partner was cleared by the odd-source clearing branch.
No test later overwrites either observed partner before its assertion. The two short tests are intentionally separate to identify which source-parity branch failed.
Constants file, line 40: HEAD_SIZE_64 and PARTNER_MASK_0XFFFF0000 follow this file's established convention and describe distinct roles.
Runtime contract, line 50: zero tracked hardware layers means a supported software-only model. The hardware layer lookup returns no entry in this mode, and all work follows the software path.
All tests compiled and executed in the recorded HEAD c1 run.

## PR D: wait instrumentation

Metadata: HEAD d1, base main. Body: "join_wait measures time waiting for hardware or peer software workers."

File join, line 10: hardware wait is enclosed in the new timer.
Line 20: software-only path polls peer completion without starting a timer.
File stats, line 30: a worker row is keyed by attention-worker index. The same index can refer to a different pool thread after a worker split changes. Documentation promises cumulative totals per thread.
No timing measurement is supplied. The author explicitly allows narrowing documented scope if additional timing or stable row identity is deferred.
