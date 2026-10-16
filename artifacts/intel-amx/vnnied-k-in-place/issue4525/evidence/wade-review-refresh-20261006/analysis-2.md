# Wade review evidence: assigned shard 2

Short version: I read all 398 Wade records on the 64 assigned pull requests, including all 189 nonempty bodies. His independent reviews cover correctness, concurrency, performance, tests, and ordinary code clarity. The installed skill is too narrowly centered on PR #4557 and incorrectly excludes several kinds of comments he has actually made.

## Scope and method

- PR means pull request. DMA means direct memory access, where hardware transfers bytes without copying each byte through the CPU. HBM means the device's high-bandwidth memory. GOF means the code's group of four tokens. KV means attention key and value data. CI means automated continuous-integration jobs.
- The source is `/tmp/wade-review-refresh/shard-2.json`, plus full inline threads for ambiguous independent reviews. Dates span 2025-09-25 through 2026-09-23.
- The shard contains 40 PRs authored by others and 24 PRs authored by Wade. Wade's own explanations and replies are classified separately. They do not establish independent reviewer preferences.
- There are 209 empty records. Empty approvals do not establish a preference or demonstrate that all possible concerns were checked. The classification file contains every assigned record ID, including empty records.
- `classification-2.json` has one row per PR. Its `approval_only` field is true for 17 PRs with only empty approval or a generic approval acknowledgement. A `done` reply is classified as an author reply instead.
- I read selected replies and original diff context on PRs #1485, #1920, #2148, #2233, #2287, #2766, #2777, #2903, #4007, and #4128. Where no later reply exists, acceptance is not inferred.

## Independent reviewer rules suitable for the skill

### 1. Follow the actual configuration and geometry

- Model-dependent numbers must come from the model's actual configuration. Wade rejects a hardcoded attention scalar of 1.0 and separately rejects deriving every model's scalar from head size. His second comment points to the existing special-model branch. This is a recurring correctness rule, not a constant-naming preference. [PR #2089](https://github.com/positron-ai/tron/pull/2089#discussion_r2897190682), [PR #2302](https://github.com/positron-ai/tron/pull/2302#discussion_r3036995239).
- Distinguish a software eligibility predicate from a low-level hardware invariant. In #4007, eligibility sends unsupported shapes to software. It does not assert. Wade supports assertions at hardware writers instead of silent truncation. The author then adds corresponding K and V bounds. [Wade](https://github.com/positron-ai/tron/pull/4007#discussion_r3866435051), [author resolution](https://github.com/positron-ai/tron/pull/4007#discussion_r3874221044).
- Separate model-native geometry, hardware layout, and intentionally parameterized test utilities. Wade identifies the production caller that supplies the fixed hardware head width. He explains why the unit-test-only helper still accepts a width parameter. Do not report the test helper's flexibility as a production bug without tracing callers. [PR #4007](https://github.com/positron-ai/tron/pull/4007#discussion_r3866568650), [documentation request](https://github.com/positron-ai/tron/pull/4007#discussion_r3866590750).
- Check alternative feature configurations and device counts. Wade asks whether multi-command code works with its results feature disabled, and questions unconditional device index zero under two-device or four-device tensor parallelism. [PR #2148](https://github.com/positron-ai/tron/pull/2148#discussion_r2915270383), [PR #2287](https://github.com/positron-ai/tron/pull/2287#discussion_r3029339639).

Suggested check: resolve each changed scalar, bound, stride, and mode selector from producer to consumer. Identify the real production callers and supported alternate configurations before reporting a defect.

### 2. Fail loudly when progress is impossible

- Wade asks for a fatal assertion or `debug_exit()` when an unsupported command cannot be processed meaningfully. He also asks for an explicit shard-count bound before indexing bounded arrays. [fatal condition](https://github.com/positron-ai/tron/pull/2233#discussion_r2983787051), [bound](https://github.com/positron-ai/tron/pull/2233#discussion_r3002034511).
- Early exits must update the count consumed by later submission code. Wade endorses the specific finding that an early command-generation release leaves the original command count in place. His agreement establishes the concern. The entire quoted bot report need not become a general rule. [PR #2233](https://github.com/positron-ai/tron/pull/2233#discussion_r2983833171).
- An assertion replaced by an unconditional spin can turn a diagnosable fault into a permanent hang. Wade asks what signal guarantees completion, whether existing ring backpressure already serializes reuse, and whether the real defect is upstream completion signaling. He permits a possible urgent pipeline exception. This is not an absolute prohibition on waiting. [PR #2872](https://github.com/positron-ai/tron/pull/2872#discussion_r3342904643).
- On a different PR he flags unbounded spin loops but explicitly calls the remedy a possible next iteration. His approval says remaining comments are minor. Preserve that severity rather than turning every unbounded wait into a blocker. [PR #2766 concern](https://github.com/positron-ai/tron/pull/2766#discussion_r3307412051), [approval](https://github.com/positron-ai/tron/pull/2766#pullrequestreview-4373886636).

Suggested check: trace every changed early return, wait, failure path, and generated count to the code that consumes it. State the progress condition and how failure becomes observable.

### 3. Protect state where it is owned, at the right concurrency scope

- Wade distinguishes an already locked allocator from an unprotected device DMA queue. He does not prescribe one lock around both operations. [PR #2777](https://github.com/positron-ai/tron/pull/2777#discussion_r3275212298).
- He prefers a mutex owned by the device or queue and used inside its mutator. That prevents future callers from bypassing protection. He separately considers whether waiting can happen after releasing the lock. His claim that concurrent waits may be safe is qualified. He explicitly defers the final boundary to the subsystem owner and allows that the submitted approach may suffice. [PR #2777](https://github.com/positron-ai/tron/pull/2777#discussion_r3277240111).
- Lock or busy-flag granularity must cover the actual shared scratch. In #4128, the busy flag is indexed by layer while scratch is shared across layers. Wade flags the mismatch and explains that a new gather loop widens an existing race window. [PR #4128](https://github.com/positron-ai/tron/pull/4128#discussion_r3907183627).
- Completion state must be reset at the intended lifecycle boundary. Wade asks why the new clear method has no caller between forward passes. [PR #2287](https://github.com/positron-ai/tron/pull/2287#discussion_r3029165954).

Suggested check: list the shared object, every concurrent writer, the lock or ownership scope, and the release/reset event. Do not infer safety from nearby synchronization of a different object or index.

### 4. Centralize repeated safety sequences when copies can diverge

Wade identifies four copies of an ordering-sensitive transfer sequence: commit the reservation, commit the staging guard, then register pending transfer ownership. He also identifies duplicate request representations and grouping predicates. His reason for consolidation is a silent buffer-lifetime failure if one copy changes alone. This is a concrete shared abstraction, not a generic ban on duplicate code. [PR #4128](https://github.com/positron-ai/tron/pull/4128#discussion_r3907214892).

His summary also raises destruction of queued batches and mutually exclusive ownership fields. That summary explicitly presents AI-assisted findings he requested. Treat the proposed destructor change as a candidate remedy requiring validation, not a proven universal rule. [PR #4128 summary](https://github.com/positron-ai/tron/pull/4128#issuecomment-5498556672).

Suggested check: compare every singleton, batch, backfill, and normal-dispatch path that submits the same owned resource. Name the ordering invariant and inspect destruction, cancellation, and completion.

### 5. Count hot-path work and preserve an inexpensive empty case

- Wade asks why a wait now converts nanoseconds to cycles before checking whether the caller requested an indefinite wait. He labels this a possible nit. [PR #2903](https://github.com/positron-ai/tron/pull/2903#discussion_r3350064944).
- In #4128 he counts repeated full-head gathers, redundant buffer clearing, temporary heap allocations, and an avoidable sort. His performance concerns are grounded in the loop structure and existing sibling implementation. The quoted workload totals are estimates in the source, not fresh measurements by this review-refresh task. [PR #4128](https://github.com/positron-ai/tron/pull/4128#discussion_r3907183627).
- Check an often-empty queue before allocating temporary storage. Avoid repeating an identical assertion callback when the assertion executes in release builds. Distinguish prompt processing from decode with a semantic pass-shape signal, not a token-count proxy that also matches many concurrent decode sessions. [PR #4128](https://github.com/positron-ai/tron/pull/4128#discussion_r3907185740).

Suggested check: quantify operations per token, layer, worker, and loop iteration from the code. Distinguish measured timing from computed work counts. Prefer the smallest change that removes verified repeated work.

### 6. Test the real boundary and the real orchestration

- A fake that drops transfer descriptors cannot verify destination addresses, fetcher selection, source offsets, or lengths. Staging content and descriptor counts are insufficient. Wade asks to compare the bytes and destinations of batched versus singleton transfers at the transfer boundary. Include nonzero indices, partial batches, and both sides of a page boundary. [PR #4128](https://github.com/positron-ai/tron/pull/4128#discussion_r3960538177).
- Tests that manually call population and transfer bypass the new dispatch/drain orchestration. Wade asks for mixed shards/layers, a reservation collision creating a gap, branch fanout, exact-once writes, untouched skipped targets, and completion before scheduler storage is rebuilt. He explicitly says he has not observed a lost transfer or early completion. Report this as coverage, not as an established implementation failure. [PR #4128](https://github.com/positron-ai/tron/pull/4128#discussion_r3960538961).
- New queue implementations need ordering, wraparound, and full-state tests. Wade asks for a configurable small capacity to make these cases practical. He also asks why the submission queue differs from the receive-side capacity. The author's answer cites profiling, so do not invent a rule that the two capacities must match. [small queue](https://github.com/positron-ai/tron/pull/2903#discussion_r3350173837), [ordering tests](https://github.com/positron-ai/tron/pull/2903#issuecomment-4614385493), [author capacity rationale](https://github.com/positron-ai/tron/pull/2903#discussion_r3351627430).
- For an uncertain shard-boundary issue generated by an assistant, Wade requests a short diagnostic test to prove or reject it. He does not present the assistant's claim as established fact. [PR #2233](https://github.com/positron-ai/tron/pull/2233#discussion_r3002297607).

Suggested check: for each claimed safety property, name a deliberate defect that the assertion would detect. Follow test calls through fakes and lower-level helpers to ensure the changed production path actually runs.

### 7. Check alignment at the real intrinsic consumer

Wade traces an ordinary stack array through a callback into a 32-byte-aligned vector store. His comment reports compiler inspection and a sanitizer reproducer that fails at the misaligned address and passes with alignment. He asks for explicit alignment and a test that uses the real gather. Optimized instruction fusion can hide the violation. [PR #4128](https://github.com/positron-ai/tron/pull/4128#discussion_r3960506641).

Suggested check: trace newly introduced scratch and subviews through their actual consumers. Verify required alignment and offsets independently of whether the current optimized build happens to run.

### 8. Names, comments, and diagnostics must explain the actual thing

- Prefer domain names over opaque abbreviations. Wade asks for `kv_shard_layers` over `layers`, and `tok_ix_per_q` over `b`/`B`. [PR #2233](https://github.com/positron-ai/tron/pull/2233#discussion_r2982403509), [PR #2287](https://github.com/positron-ai/tron/pull/2287#discussion_r3075717295).
- Document why buffers have their shape and use meaningful geometry constants. Do not replace an existing named bound with its identical literal. [PR #2089 shape](https://github.com/positron-ai/tron/pull/2089#discussion_r2897210663), [PR #2148 constants](https://github.com/positron-ai/tron/pull/2148#discussion_r2915246595), [existing constant](https://github.com/positron-ai/tron/pull/2148#discussion_r2915275194).
- Name functions for actual semantics. Wade questions an `indefinitely` function whose wait is finite. This is a question about terminology, not evidence that the instruction itself is wrong. [PR #1485](https://github.com/positron-ai/tron/pull/1485#discussion_r2380263378).
- Use actual runtime bounds in errors. Wade replaces a hardcoded queue limit in a diagnostic with the configured limit. [PR #2903](https://github.com/positron-ai/tron/pull/2903#discussion_r3350031805).
- Add concise comments where use or intent is unclear. Avoid a large named Note for an ordinary local fix. These are compatible preferences about useful information, not opposing rules about the amount of documentation. [PR #2302 use instructions](https://github.com/positron-ai/tron/pull/2302#discussion_r3036997452), [PR #4007 oversized Note](https://github.com/positron-ai/tron/pull/4007#discussion_r3866668853).

### 9. Remove obsolete scaffolding and avoid duplicated state

- Guard debug-only dumps and their includes. Remove unused includes, declarations, locals, stale comments, unused helpers, and unexplained early test returns when their purpose has disappeared. Wade repeatedly does this in #1920 and #2148. [debug guards](https://github.com/positron-ai/tron/pull/1920#discussion_r2719160746), [unused include](https://github.com/positron-ai/tron/pull/1920#discussion_r2729005716), [unexplained return](https://github.com/positron-ai/tron/pull/1920#discussion_r2737861302), [dead code](https://github.com/positron-ai/tron/pull/2148#discussion_r2915191812).
- If a field is always derivable, ask whether a real transient state justifies storing both. Wade asks this for device identity and shard count. Do not delete the field before tracing writers and legitimate intermediate states. [device identity](https://github.com/positron-ai/tron/pull/2089#discussion_r2913598312), [shard count](https://github.com/positron-ai/tron/pull/2233#discussion_r3010846319).
- Remove parameters always passed as empty when a later stage owns filling the value. [PR #2233](https://github.com/positron-ai/tron/pull/2233#discussion_r3001962017).
- Keep tracing balanced after refactors. Wade catches a stale conditional trace end, and the author confirms it was missed cleanup. [PR #2766](https://github.com/positron-ai/tron/pull/2766#discussion_r3307450424).

## Corrections, scope, and severity controls

- Retracted remedy: Wade first suggests `resize`, then withdraws it after recognizing that newly created `unique_ptr` elements would be null and still need allocation. Never encode the initial `resize` suggestion as a rule. [initial](https://github.com/positron-ai/tron/pull/2461#discussion_r3102140611), [retraction](https://github.com/positron-ai/tron/pull/2461#discussion_r3102275102).
- Explicit initialization is a positive but scoped preference. Wade calls it pedantic and says no consistent project standard is apparent. The skill should not adopt his broad language-law explanation without independently checking it. [PR #2193](https://github.com/positron-ai/tron/pull/2193#discussion_r2941290531), [PR #2438 approval](https://github.com/positron-ai/tron/pull/2438#pullrequestreview-4125818552).
- Naming, smaller scopes, temporary pointer variables, and label case appear as explicit nits. They should not compete with correctness findings. [pointer naming](https://github.com/positron-ai/tron/pull/1877#discussion_r2700506675), [unneeded scope](https://github.com/positron-ai/tron/pull/2223#discussion_r2976643305), [label convention](https://github.com/positron-ai/tron/pull/3302#discussion_r3580238651).
- Passing tests and unrelated intermittent failures do not require blocking the current PR. Wade's #2461 approval separates the suspected multi-user crash from the change and includes a test log with disabled tests explicitly listed. This is evidence of severity calibration, not proof that the earlier causal judgment is universally correct. [approval](https://github.com/positron-ai/tron/pull/2461#pullrequestreview-4131374395).
- His #2565 question asks for multi-user tests to investigate possible duplicates. It does not report an observed duplicate failure. [comment](https://github.com/positron-ai/tron/pull/2565#discussion_r3156090573).

## Author replies retained as context, not independent rules

- #2440 follows the actual `work()` reader to reject a bot claim about a vestigial field. #2442 follows resolved configuration and a real caller to reject other bot findings. These support reading context before attribution, but are Wade defending his own code. [#2440](https://github.com/positron-ai/tron/pull/2440#discussion_r3103228396), [#2442](https://github.com/positron-ai/tron/pull/2442#discussion_r3088444489).
- #2867 proves the suspect hardware path is unreachable at that head and records a follow-up for activation. #2573 similarly distinguishes unreachable staged code. These are author-side scope explanations. [#2867](https://github.com/positron-ai/tron/pull/2867#discussion_r3335737823), [#2573](https://github.com/positron-ai/tron/pull/2573#discussion_r3164044243).
- #2549 explains a producer-count reset violating the plugin's ownership contract. The detailed explanation is AI-assisted author narration. Do not claim it was an independent review finding. [comment](https://github.com/positron-ai/tron/pull/2549#discussion_r3150536661).
- The asim #256 entries report Wade's fixes to other people's findings. They are not reviews by Wade of someone else's implementation.

## Changes needed in the installed skill

- Remove the absolute claim that Wade does not comment on formatting, brace style, benchmark method, or kernel arithmetic. This shard has scope/bracket cleanup and detailed geometry, vector alignment, and hot-path operation analysis. The evidence does not establish a positive rule to criticize all formatting or benchmark methods. Use a narrower direction: prioritize substantive findings and label local style suggestions as nits.
- Add the independent rules above before or alongside the PR #4557 test/description/history checks. The latest, highly specific examples should not erase the earlier recurring concerns.
- Keep citations and exceptions in reference material. Avoid turning one case's exact token threshold, function names, loop arrangement, or proposed remedy into a universal detector.
- Preserve the existing emphasis on final-head claims, meaningful tests, and reviewer-versus-author evidence. Expand it with real-call-path, real-transfer-boundary, lifecycle, geometry, and hot-path checks.
