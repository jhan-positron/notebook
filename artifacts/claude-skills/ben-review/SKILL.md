---
name: ben-review
description: Review code changes for missing shared domain abstractions, argument lists longer than four parameters, and representation decisions (a storage layout, an encoding, the reader that fits it) that live outside the type that owns the data. Identify repeated low-level representation details that obscure a meaningful concept. Use during code review or when explaining readability problems in a diff. Preserve existing code outside the change.
---

# Ben-review

Short version: Review the requested code changes and preserve existing code outside the change. Identify repeated representation knowledge that obscures a shared concept. Use more than four parameters as a prompt to investigate the interface. Check that every decision which depends on a representation (how a value is stored, which reader fits it, how a value converts into it) lives in the type that owns the data, and that callers call an operation instead of testing the representation.

## Top priority: focus on the change and preserve existing code

Establish the requested diff before reviewing. Tie findings to added or modified code and problems introduced or materially worsened by that change.

Read unchanged declarations, implementations, and callers for context, existing abstractions, and evidence of the change's effects. Preserve that code. Do not report pre-existing smells as new findings or use this review to recommend unrelated cleanup.

Keep recommendations and any authorized edits within the requested change. Prefer adapting changed code to existing interfaces and helpers. Do not expand the work into redesigning existing interfaces or migrating untouched callers merely for consistency. Broader refactoring requires an explicitly broader user request.

## Recognize the problem

Ask: **Which details are meaningful decisions at this call, and which details must the reader repeatedly decode to understand the operation?**

A domain abstraction is a shared type or operation named for a concept in the program's problem area. Look for callers repeatedly assembling that concept from generic machinery: template arguments, flags, dimensions, strides, or construction steps.

Name the concrete reading cost. Readers may have to reconstruct the same meaning at each occurrence, compare near-identical expressions for intentional differences, or switch between an operation and its representation details. "Messy" or "verbose" alone is not an actionable finding.

## Investigate more than four parameters

Treat a list with more than four parameters as a code smell: a clue to investigate, not an automatic defect. Inspect runtime parameter lists and explicit template argument lists separately. Consider the reading burden of both at the call site. Apply this trigger to the requested changes, not every existing declaration encountered during review.

Ask whether the list reveals:

- Several values describing one concept, such as a buffer's pointer and length.
- Adjacent values of similar types whose meanings or order are hard to distinguish.
- Repeated combinations of fixed properties that a shared abstraction could define once.
- Inputs controlling unrelated activities, suggesting the function has multiple responsibilities.

Explain the specific difficulty before recommending a refactor. Preserve necessary independent inputs. A shorter list is useful when it expresses a meaningful concept or a clearer responsibility. Putting unrelated fields into an arbitrary options object merely relocates the complexity.

This review trigger follows the direction of [C++ Core Guidelines I.23](https://isocpp.github.io/CppCoreGuidelines/CppCoreGuidelines#i23-keep-the-number-of-function-arguments-low). The numeric threshold is a heuristic, not a universal limit. A shorter list may still have the same design problem.

## Establish the shared concept

Read the relevant declarations, implementations, and callers. Compare the base and proposed revisions when reviewing a change. Search nearby utilities, local aliases, and test helpers for vocabulary that already expresses the concept.

Separate the information at each call:

| Information | Treatment |
|---|---|
| Fixed properties required by the shared concept | Define once in the abstraction |
| Properties derivable from supplied values or types | Infer where the language permits |
| Meaningful differences between callers | Preserve explicitly or through a justified default |

Check apparent repetitions for semantic differences before combining them. A non-default flag may encode a necessary buffer property. Similar syntax does not establish a shared contract.

Prefer an existing shared helper. Otherwise, propose the smallest useful alias or construction helper in the layer that owns the concept. Local aliases and test helpers can reveal missing shared vocabulary. Consider promotion only when production callers share their meaning and the move fits the requested change. Keep test-specific conveniences local.

## Where a representation decision lives

These four checks come from [Tron PR 5047](https://github.com/positron-ai/tron/pull/5047), Ben's rewrite of the K-cache layout change of PR 4956. A representation decision is anything that depends on how a value is stored: a layout flag, a layout type, the reader or kernel that fits one layout, the conversion of a value into the storage. The type that holds the data is its owner. Run G1 first. Its count says whether G2 to G4 findings exist. Then G2 on accessors, G4 on call sites, G3 on loops. Tie every finding to added or modified code, as the top priority requires.

### G1. One owner per representation decision

Rule: the owner holds every decision that depends on its representation. Callers call an operation. They never test the representation.

Check: list the identifiers that name the representation (a flag such as `k_vnni::layout_on`, a layout type, an `if constexpr` on either, a pair of accessors chosen by layout). Count them per file in the diff, outside the owner. The target is 0 in every non-owner file. In PR 5047 the count went from 2/1/1 to 0/0/0 in self_attention.hpp, model.hpp and full.hpp, and the owner kv_cache.hpp went from 33 to 24 (it took over the scoring, the AMX attempt and the row conversion).

Finding shape: "This file tests `<representation flag>` at `<site>`. `<owner>` already knows it. Move the branch into `<owner>::<operation>` and call that." Name the operation that should exist: a scoring call, a store from an expression, a try-with-fallback.

Keep: a test file may know the build's representation in its expectation. The owner's own file may branch on it as often as it needs.

### G2. No raw view of owned storage leaves the owner

Rule: a public accessor that returns a pointer or a view into the storage is a second owner. Replace it with element or row operations and make the storage struct private.

Check: for every accessor the diff adds or keeps that returns a view, a raw pointer or a reference to a storage member (in PR 5047: eight `page::k()` overloads, `page::k_packed()`, a `kv_block&`), find its callers and ask whether each call is a row operation (`set_k_row`, `get_k_row`, `set_k_block`). Tests that reach storage through the public accessor are the usual holdout. They move to a test helper header (PR 5047 added t/kv_cache_helpers.hpp with `set_k_tag` and `k_tag`), so the production API stays closed.

Finding shape: "`<accessor>` hands `<caller>` the storage. Its one use is `<what the caller does>`, which is `<row operation>`. Drop the accessor, keep `<storage struct>` private, and give the test a helper."

Keep: a copy out of the storage with a stated contract (PR 5047's FPGA staging copy through `get_k_row` into the caller's scratch) is an operation, not a view. Do not flag it as a leak. Flag its cost only with a measurement.

### G3. One control flow per function

Rule: a loop body does one job. A per-configuration branch inside a loop, a placeholder that stands in for the other configuration, or a `[[maybe_unused]]` local kept alive for one branch means the function carries two control flows. Split the phases: select, then act once after the loop, with the per-configuration part in one call.

Check: inside each loop the diff touches, look for `if constexpr` branches whose bodies do different jobs, lambdas that return a dummy for one configuration, and locals that only one branch reads. PR 5047's first commit turned the token loop into "select into a 64-bit mask", and one `score_k` call after the loop scores for both layouts.

G3 serves G1. The split is what lets the owner's operation take the selection as data in one call (`score_k(slot, kv_head, q, live, scores, stride)`). With in-loop scoring the owner would have to offer a per-call scorer object that the caller holds across the loop, a worse interface. Raise a G3 finding where it enables a G1 operation. On its own, a split of a hot loop is a readability gain against a cost.

Finding shape: "This loop selects tokens and scores them, with the scoring body chosen by `<flag>`. Let the loop select into `<mask>` and call `<owner>::<operation>` once after it."

Keep, and measure: the split changes the shape of a hot loop, and shape changes machine code. PR 5047's split costs +2.9 % of prefill time when every K token takes the software scoring path (issue #5097: the selection pass runs alone where the one-pass loop hid it under the dot products). A G3 finding on a hot loop carries two parts: the split, and the measurement cell that shows the cost is inside the band. Without the measurement it is "should fix", never "would block".

### G4. The call site asks and takes the answer

Rule: when a fast path exists for some representations and not others, the call site calls one operation that returns whether it applied, and falls back on false. The call site never carries the compile-time clause that picks the path.

Check: call sites of the form `if constexpr (<layout>) { kernel A } else { kernel B }` or `if (<layout predicate>) { fast path } else { slow path }`. The owner's operation holds the clause (PR 5047's `try_score_k_amx` returns false for a layout without an AMX reader). Verify two contract points in the owner: a declined call changes nothing (no score written, no storage touched), and a decline that is constant in one build folds at compile time (an `if constexpr` inside the operation), so the always-declined build pays no predicate and no buffer.

Finding shape: "`<call site>` picks `<kernel A>` or `<kernel B>` by `<flag>`. Give `<owner>` one `try_<operation>` that returns false when it does not apply, and let this site fall back on false. A declined call must leave `<state>` untouched."

Keep: a run-time predicate that both paths need anyway (the dense-page test) stays at the call site. The verification to ask for is a dispatch test that counts kernel calls per configuration (`t_amx_dispatch_dtype`).

## Calibrate the recommendation

- Require a concrete concept and a demonstrated reading benefit. Length, template syntax, or repetition alone does not justify another abstraction.
- Preserve the caller's real decisions and obligations. Do not hide meaningful differences or add options for hypothetical callers.
- Prefer a name that explains the object's role. An opaque abbreviation merely shortens the spelling.
- Match the existing codebase's conventions. Keep the proposed refactor within the review's scope.
- Treat this as a readability or maintenance finding unless there is separate evidence of a correctness defect. Do not invent findings to fill a review.

**Judge limitations against the baseline.** Do not describe an unchanged missing check as a weakness introduced by a refactor. Do not append unrelated hardening caveats to a readability improvement. Report a changed guarantee or a newly relevant failure only with evidence. If a broader audit calls for an existing issue, identify it explicitly as pre-existing.

An alias names an existing type. A construction helper may simply wrap a pointer. Credit only the guarantees the implementation provides; a documented precondition is not runtime validation.

## Report an actionable finding

Include the changed source location, the missing concept or mixed responsibilities, the concrete reading cost, and a small proposed improvement. Identify the caller differences that must survive. A parameter-count finding must explain more than the count. Show a short before/after example when it makes the recommendation concrete. Review requests authorize recommendations, not automatic edits or posting comments.

Example wording:

> These callers repeatedly describe an aligned transfer row through generic view parameters. Readers must decode and compare those parameters at each use. A shared row alias and construction helper could define the fixed properties once while preserving the row length, element type, and buffer flags.

## Reference example

In [Tron PR 4697](https://github.com/positron-ai/tron/pull/4697), a V row is one token's attention values for one attention head. The cache transfers it through an aligned, contiguous buffer. Ben gives its read-only view a shared name:

```cpp
// Original parameter spelling
const_view<Source, VIEW_ALIGNED_TRUE, Dma,
           seq<head_size>, sseq<1>> src

// Shared name for the same type
const_v_row_view<Source, head_size, Dma> src
```

Here, `Source` is the element type, `head_size` is the row length, and `Dma` is the direct-memory-access flag. The alignment, one-dimensional shape, and adjacent-element stride are fixed. The `v_source_row` construction helper infers the element type from the pointer. The production caller preserves its buffer's DMA flag.

The source and destination helpers already existed in a test. Moving them into the shared interface lets callers reuse the same definition. Both revisions rely on the caller for alignment and sufficient buffer length. That obligation is unchanged.

The cache's `set_v` and `get_v` functions retain four runtime parameters in both revisions. Ben simplifies the repeated five-argument template spelling of the row type. The improvement is the shared concept and reduced interpretation work.
