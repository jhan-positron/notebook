---
name: wade-code-review
description: Review Positron pull requests using patterns from Wade's review history. Check runtime correctness, asynchronous ownership, hardware bounds, hot-path costs, test contracts and execution, instrumentation semantics, and PR claims. Use for a Wade-style review, before requesting his review, or when addressing his feedback. Treat preferences and staged follow-ups separately from defects.
---

# Wade code review

Short version: Trace what the changed code actually reads, owns, waits for, and measures. Check whether the tests can observe a failure in that behavior. Compare the pull request description with the revision being reviewed, and distinguish defects from coverage gaps, design questions, and preferences.

## Scope and evidence

This skill draws on the accessible review history of GitHub user `Wado-posi`, collected on 2026-10-06. Most independent review evidence comes from `positron-ai/tron`. Related repository discussions provide context, but do not establish universal rules.

- Read [review-history.md](references/review-history.md) when a finding depends on Wade's precedent, severity, or a disputed preference. It records the corpus boundary and representative sources.
- Read [procedures.md](references/procedures.md) for targeted checks on ownership, tests, build configuration, measurements, or history.
- Read [pr4557-misses.md](references/pr4557-misses.md) for packed-layout tests, typed views, or the qualified disagreements in that review. Its historical facts are tied to a particular revision.

Wade sometimes posts analysis from an AI assistant. Treat it as attributed review material, not independent verification. Author replies, quoted third-party comments, empty approvals, and a lack of objections do not establish Wade's review rules. Read later replies before using an early objection as precedent.

Words used here: PR means pull request. HEAD is the reviewed commit. BASE is its comparison commit against the PR's actual target branch. CI means continuous integration, the automated build and test jobs. DMA means direct memory access, a hardware transfer that can outlive its submitting function. An oracle is the independent source of a test's expected result.

## Establish the review boundary

1. Record the repository, PR number, HEAD, actual base branch, and merge base. Respect supplied limits on network access and worktree changes.
2. Read the PR description, diff, branch history, applicable repository instructions, and existing review threads. Read complete changed tests and the immediate production callers and consumers.
3. Start with the paths affected by the change. Expand into shared helpers, ownership, build settings, and hardware configuration when those paths require it. Separate existing problems from new defects or newly exposed risks.
4. After a later push, recheck findings and claims affected by the change. Do not present an earlier review or test run as evidence for a different revision without explaining why it applies.

## Review priorities

### 1. Runtime behavior and asynchronous ownership

- Follow every physical read and write. A logically masked token can still be read by a vectorized kernel. A zero weight does not make an unfinished or invalid value safe to read.
- Identify who owns each buffer, reference, queue entry, and completion signal from submission through completion, cancellation, and reuse. Check container reallocation and scheduler storage rebuilds while references remain live.
- Match completion checks to the device, queue, descriptor range, and generation that received the work. Trace the ordering that permits release or reuse.
- Check whether the lock protects the actual shared state at its mutation boundary. A caller-side lock may miss another caller or serialize an independent wait. Ask for evidence before changing lock placement.
- Do not accept an unbounded wait as proof that a race is fixed. Identify the event that ends the wait and whether the failure being handled prevents that event. Preserve actionable diagnostics.
- Separate model dimensions from hardware storage dimensions. Trace bounds, padding, alignment, and unsupported-model fallback through the production caller. Do not infer production behavior from a test-only helper.

### 2. Repeated work and performance evidence

- Multiply a new operation by its real frequency: per element, token, layer, worker, submission, or polling iteration. Inspect allocation before an empty-queue check, redundant zeroing, repeated gathers, extra passes, and unnecessary sorting.
- Check that batching or fanout does not repeat a whole gather for each fragment or rebuild the same staging data for each consumer. Use an explicit workload classification when a count threshold confuses decode work with prefill work.
- Separate a computed work count from a measured time cost. Request comparable before-and-after measurements when the performance tradeoff matters. Label an unmeasured slowdown as a hypothesis and name the measurement that would decide it.
- For numerical comparisons, compare old and new implementations against the same reference on the same inputs. Separate the new change's added error from existing error, including exceptional values.
- Check how numerical comparisons handle not-a-number and infinite values. A tolerance check must not silently treat an invalid result as a successful comparison.
- Consider the cost of diagnostics too: enabled trace categories, buffer capacity, polling, assertions, and aggregation can affect the path they measure.

### 3. Tests that protect the intended contract

- Name the production behavior each assertion protects. A round trip, documented format, real regression, type boundary, or ownership invariant can justify exact values. Today's incidental rounding, structure, or helper arithmetic may not.
- Do not change production numerical behavior merely to satisfy or remove a test. Report an unsupported new test expectation separately from a pre-existing numerical defect.
- Check the oracle. Two accessors sharing the same address helper can agree while both are wrong. A fake that drops transfer arguments cannot prove correct destinations or lengths.
- Exercise the production entry point when the change is orchestration. Direct helper calls do not establish grouping, reservation handoff, completion, or drain behavior.
- Choose boundary cases from the failure mechanism: nonzero offsets, partial windows, page boundaries, queue wrap and full states, competing producers, branch fanout, and unsupported shapes. Do not add a generic matrix unrelated to the change.
- Trace compilation, test selection, assertion reachability, and recorded execution separately. Move hardware-independent checks outside unnecessary hardware gates where practical. Apply the current repository's CI policy.
- Before calling tests duplicates, identify a plausible defect that one observes and the other misses. Include write order and overwritten observations. Consolidate only if the distinct protection survives and the result is clearer.
- Keep test names, setup, comments, and passing assertions consistent. Fix an invalid test fixture instead of adding production guards that silently hide bad state.
- Prefer the closest existing test suite. A temporary workaround's regression test needs a documented reason and a replacement condition; do not remove protection before the underlying failure is understood.

### 4. Instrumentation that describes real work

- Map each counter or timer to all promised execution paths, including software-only, hardware, mixed, and alternate callers. A zero can mean an uninstrumented path rather than no work.
- Give one place responsibility for a complete operation record, or prove the split producers stay paired on every call path. Check begin/end, reset, aggregation, and publication together.
- Define the unit being counted and the classification granularity. A forward containing prefill and decode work cannot establish decode-only behavior unless that limitation is explicit.
- Use stable worker or device identity for cumulative rows. Distinguish a pool thread from its temporary role. Verify exported names, debug strings, and documentation against the actual index.
- Do not silently discard impossible indices to accommodate a test. Distinguish internal invariant failures from intentionally supported external inputs and optional features.

### 5. Maintainability, scope, and claims

- Prefer one implementation of a safety-critical ordering, grouping rule, or index convention when copies can diverge. Use the nearest suitable helper without adding speculative infrastructure.
- Reuse existing configuration accessors and model parameters instead of copying environment reads or deriving a setting from a correlated dimension. Check that the normal wrapper or entry point exposes the feature.
- Trace each changed area to the stated behavior or an explicitly requested bundled change. Suggest splitting unrelated cleanup. A missing body sentence alone does not make a necessary regression test unrelated.
- Compare guarantees with enforcing declarations. Direct pointer rejection, explicit wrapping, distinct types, alignment, ownership, and lifetime are separate properties. Narrow an overclaim without inventing a stronger implementation requirement.
- Name the actual CI workflow, trigger, effective configuration, and runner when claiming coverage. A packaging or manually invoked workflow may not gate the PR.
- Label results with their tested revision and relevant configuration. Keep usable artifact references and outcomes. Remove obsolete arithmetic and local bookkeeping that do not help a reviewer assess the change.
- Keep comments about lasting behavior and rationale. Remove review-round labels, story narration, stale questions, and debug residue. A large explanatory Note is useful only when the mechanism needs it.
- Follow current repository and user conventions. Wade's naming and formatting preferences are usually nits. His later acceptance of value suffixes in established kernel code does not prescribe them for shared code.
- Treat commit cleanup as reviewability and history hygiene. Repeated fixups or unrelated commits can justify a suggestion. Commit count alone does not. Do not invent an owner-approval gate from file authorship; report an explicit unresolved request or repository requirement when one exists.

## Findings and completion

Lead with the concrete fact at a HEAD location. State the consequence and the smallest supported remedy. For a coverage gap, say what wrong behavior would still pass. For a performance concern, distinguish measurement from hypothesis. For a design question, state the tradeoff and preserve a deliberate staged limitation.

Separate correctness defects, coverage gaps, inaccurate claims, design questions, and nonblocking nits. Do not turn an approved follow-up into a blocker. Do not copy a reviewer's remedy when it removes distinct protection or rests on an incorrect premise.

Report the reviewed revision, relevant checks performed, and missing evidence. Use `Insufficient data` with the source or measurement needed to resolve a material gap. A review request authorizes analysis; it does not authorize posting comments, editing source, or rewriting history.
