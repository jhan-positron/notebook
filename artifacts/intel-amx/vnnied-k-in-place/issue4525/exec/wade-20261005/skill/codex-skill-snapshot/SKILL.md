---
name: wade-code-review
description: Review code changes for unjustified test contracts, shared test oracles, skipped CI assertions, overstated type guarantees, stale validation claims, and unrelated scope. Use for Wade-style review or review of refactors with new tests and safety claims.
---

# Wade-code-review

Short version: Check whether the tests protect the intended contract and whether the review claims follow from the evidence. Passing tests and faithful implementation of a plan do not establish that the plan chose the right contract.

## Establish the review boundary

Identify the base and head commits, or the local revision and working-tree diff. Read applicable repository instructions and available review discussion within the requested scope. Verify that the source you inspect belongs to that revision. If the user limits the evidence supplied, respect that boundary and report the resulting limits.

Read relevant unchanged callers, helpers, test registration, and build configuration. Keep findings tied to the requested change. Distinguish a pre-existing behavior from a new test or description that endorses it.

Treat the design, existing tests, prior reviews, and this skill's source review as claims to check. A reviewer can identify the right concern and still propose a remedy that removes useful protection.

## 1. Separate preservation evidence from lasting contracts

For each important new or changed test, identify:

- The incorrect behavior it should detect.
- The consumer, compatibility rule, or safety requirement that makes this behavior important.
- The observation that would distinguish correct behavior from that failure.
- Why existing coverage does not already protect it.

In a refactor, preserving current behavior may be the correct implementation scope. A temporary comparison against the old implementation can establish that preservation. It does not automatically justify a committed assertion that requires the old behavior forever.

Check numerical cases against project policy. NaN means a floating-point value representing an invalid result. A new assertion that requires converting NaN to infinity can make loss of error information a contract. Likewise, bit truncation or a rounding choice needs a named requirement before a test should forbid changing it. Preserve exact bits when the interface actually promises exact copying.

Do not silently change numerical behavior during a review or a behavior-preserving refactor. Report the new contract problem separately from any pre-existing numerical issue.

## 2. Trace the expected result independently

An oracle is the source of a test's expected result. Trace how both the actual result and the oracle are computed, including shared helpers.

A write/read round trip can pass when the writer and reader share the same wrong address formula. For a layout contract, compare raw storage with an independently specified mapping, or exercise a consumer that interprets the storage independently. A second accessor is insufficient if it calls the same helper.

Name a concrete semantic mutation, such as swapping token partners or using the wrong stride. Explain which assertion would fail. If this is uncertain and a cheap isolated check is available, try the mutation in a disposable workspace. Do not add permanent tests merely to reproduce the review exercise.

## 3. Prove that the important assertion executes

CI means the repository's automated build and test jobs. Trace the path from a required job to the important assertion:

```text
Required job -> build flags -> test selection -> guards -> assertion
```

Inspect compile-time conditions, registration and tag filters, hardware checks, runtime switches, early returns, and skips. Separate these facts:

- The target compiles.
- The test case is selected.
- The assertion is reachable on the runner.
- Available logs show that the assertion's path executed.

Feature compilation and feature execution are separate. An AMX build (Intel's CPU matrix instructions compiled into the binary) may run on a host where those instructions are unavailable. A passing placeholder or an early return proves no feature behavior.

Move hardware-independent contract checks outside hardware gates when the change needs that coverage. Prefer the smallest suitable existing suite. If runner capability or execution evidence is missing, state `Insufficient data` and name the missing configuration or run evidence. Do not assume that every CI runner has the same hardware.

## 4. Check the exact guarantee of each type boundary

Inspect aliases, constructors, conversions, factories, ownership, and immediate consumers. A descriptive alias is still the underlying type. An explicit constructor can reject an unwrapped pointer at a call while allowing the same pointer after explicit construction.

Distinguish guarantees about direct argument matching, layout, ownership, lifetime, alignment, and provenance (where the underlying memory came from). Do not infer any one from another.

Try the smallest counterexample to each material claim: an unrelated view with the same shape, an explicitly wrapped pointer, a forbidden const conversion, or a view made from a temporary owner. Choose only counterexamples relevant to the claimed contract. Report documentation overclaims separately from implementation defects. Preserve deliberate staged limitations.

## 5. Review tests as a set

Compare tests by protected failure, input dimensions, production branch, and observation. Different section names do not establish different coverage. Matching even/odd combinations alone does not establish duplication either.

Before proposing a removal, check whether another test observes the same failure at the same point. A full-page copy can overwrite a temporarily poisoned partner before checking it. A partial-page test can expose that error. Separate source-parity branches can each need a zero-padding observation even when both run in another test. Prefer small cases that retain these observations over either a redundant matrix or an unjustified deletion.

Check test names and comments against the assertions. A test that zeroes poisoned padding must not claim to preserve the poison.

Find repeated production assertions before recommending more type-trait checks. Judge structural checks by their consumer:

- Lifetime restrictions can prevent views from outliving their owner.
- Alignment can be required by a vector load.
- Size can be required by a storage or binary interface.
- Absence of an unused operator or an arbitrary default constructor may only describe the current implementation.

Keep checks with a concrete failure mode. Prefer an existing authoritative check when the test merely repeats it. Do not delete safety assertions just because they concern structure. Review recommendations must respect any repository restriction on weakening existing tests.

## 6. Match validation and approval claims to their evidence

For each important result, establish the tested commit, configuration, executed path, and evidence source. After a merge, rebase, or code edit, identify what remains covered. Mark old results as historical unless relevant source equivalence is established. Recommend only the reruns needed to resolve the gap within the user's authorized scope.

Read the actual workflow before describing its flags. Do not copy a previous PR description's configuration claim without checking it. Keep assertion totals, build timestamps, and raw log paths in supporting evidence when they do not help assess the change. Counts alone do not measure test quality.

Some contracts are not observable through the existing fake or runtime test. For example, a fake allocator can provide object-lifetime behavior that the production allocator lacks. State what the tests cannot prove. Use the relevant language rule, implementation trace, or compile-time constraint as appropriate. Do not present a passing smoke test as proof of language validity.

Inspect existing discussion before treating specialist approval as absent. Distinguish a request to clarify a comment from approval of a design. Recommend targeted maintainer review when a specific unresolved concern warrants it. Do not make every low-level change require new approval, and do not contact reviewers unless authorized.

## 7. Check scope and the final review description

Account for each changed area against the requested behavior. Separate required migration from unrelated naming, formatting, allocator, or test changes. A personal style rule does not automatically justify rewriting adjacent code. Surface instruction conflicts and honor the user's explicit choices.

Value-suffixed constant names are not automatically defects. Check whether the name explains a role, and preserve an explicitly chosen naming convention. Keep readability judgment separate from whether the change belongs in this PR.

Review the final diff and description after responding to comments. Look for stale claims, removed features still advertised, and unnecessary review chronology. Assess whether commit organization helps a reviewer understand the final change. Suggest consolidation when useful, without making a fixed commit count a requirement or rewriting history during a review.

## Report the result

Give each finding a changed location, concrete trigger, consequence, evidence, and the smallest justified remedy. Distinguish correctness, coverage, documentation, and preference findings. If a point is only a hypothesis, name the check that would resolve it.

State the revision reviewed, checks actually performed, skipped or unreachable paths, and unresolved evidence gaps. Do not infer the identity of an earlier model from its wording. A review request authorizes analysis, not source edits, comment posting, or history rewriting.

For the originating examples and qualifications, read [the PR #4557 case notes](references/pr4557.md) when reviewing similar changes or explaining this skill's rules.
