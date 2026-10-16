# Review history and source map

Short version: The 2026-10-06 refresh examined every Wade record returned by two complete GitHub PR searches. The wider history supports review guidance on runtime paths, ownership, geometry, performance, tests, and instrumentation. Preserve the distinction between his independent reviews, assisted reviews he posts, author replies, and later corrections.

## Corpus boundary

Reviewer: `Wado-posi`. Search queries: `is:pr reviewed-by:Wado-posi` and `is:pr commenter:Wado-posi`, across repositories accessible to the authenticated account.

- The reviewed-by search returned 182 PRs. The commenter search returned 191 PRs. Their union contained 191 PRs. Both searches reported complete results, below GitHub's search cap.
- All review, inline-comment, and conversation-comment endpoints were fetched with pagination: 573 endpoint collections, with no fetch errors.
- The corpus contains 1,134 Wade-authored records: 600 submitted reviews, 509 inline comments, and 25 conversation comments. Of those records, 549 have text and 585 have empty bodies. These are record counts, not unique findings.
- Wade authored 76 of the PRs. Other people authored 115. Author and integration replies can occur on either group, so substantive attribution was also checked in context.
- Wade's record dates run from 2025-09-25 through 2026-10-06. All 191 PRs and all 1,134 record identifiers are accounted for in the per-PR reading ledger saved with the refresh evidence.

| Repository | PRs examined | PRs by other authors | Review records | Inline comments | Conversation comments |
|---|---:|---:|---:|---:|---:|
| positron-ai/tron | 167 | 102 | 558 | 480 | 16 |
| positron-ai/aps-claude-files | 6 | 6 | 6 | 0 | 0 |
| positron-ai/asim | 5 | 2 | 20 | 18 | 3 |
| positron-ai/asimov-interpreter | 3 | 0 | 3 | 3 | 1 |
| positron-ai/asimov-os | 6 | 2 | 4 | 2 | 4 |
| positron-ai/asimovsw-docs | 2 | 2 | 6 | 4 | 1 |
| positron-ai/terminus | 2 | 1 | 3 | 2 | 0 |

This is all accessible history returned by those searches for that account at collection time. It cannot establish deleted material, inaccessible repositories, unsubmitted reviews, other accounts, or later activity. Empty approvals establish no new preference. PR counts do not measure how often a particular concern occurred.

## Representative evidence by review question

### Does the actual read or wait match the dependency?

Wade caught a completion wait using device zero instead of the device that received the transfer. He also questioned references held across vector growth. In a later review, he endorsed an assisted finding that a vectorized reader still consumed masked values from an unfinished shared page. These support tracing physical reads, storage lifetime, and the exact completion object. [Device wait, #2011](https://github.com/positron-ai/tron/pull/2011#discussion_r2789792758), [reference lifetime, #2499](https://github.com/positron-ai/tron/pull/2499#discussion_r3120788282), [endorsed shared-page finding, #4191](https://github.com/positron-ai/tron/pull/4191#discussion_r3970590653).

### Who owns shared state and guarantees progress?

He distinguished an allocator's existing lock from an unprotected transfer queue. He suggested placing protection with the state, while explicitly qualifying the safest lock interval. He challenged replacing a diagnostic assertion with a blind wait whose completion might never arrive. An earlier wait-related comment allowed a later follow-up. Do not turn these examples into universal lock placement or blocker rules. [Lock ownership, #2777](https://github.com/positron-ai/tron/pull/2777#discussion_r3277240111), [wait failure, #2872](https://github.com/positron-ai/tron/pull/2872#discussion_r3342904643), [follow-up allowed, #2766](https://github.com/positron-ai/tron/pull/2766#discussion_r3307412051).

### Are configuration, geometry, and alignment real production assumptions?

He asked for the model's actual attention scalar rather than a hardcoded or universally derived value. He distinguished hardware storage width from model width and a test-only helper's parameters. He reported a misaligned scratch buffer by following it into the real vector store and checking a sanitizer reproducer. [Model configuration, #2302](https://github.com/positron-ai/tron/pull/2302#discussion_r3036995239), [production geometry, #4007](https://github.com/positron-ai/tron/pull/4007#discussion_r3866568650), [alignment, #4128](https://github.com/positron-ai/tron/pull/4128#discussion_r3960506641).

### What work repeats on a frequently executed path?

He identified repeated gathers, redundant zeroing, temporary allocations, avoidable sorting, and allocating before an empty-queue check. He separately requested before-and-after traces for a change that exchanged memory use for reconstruction work. A later eviction concern was explicitly a possible follow-up, not a measured regression. [Batch work, #4128](https://github.com/positron-ai/tron/pull/4128#discussion_r3907183627), [empty queue and pass classification, #4128](https://github.com/positron-ai/tron/pull/4128#discussion_r3907185740), [measurement request, #2898](https://github.com/positron-ai/tron/pull/2898#issuecomment-4607543703), [nonblocking reconstruction concern, #2906](https://github.com/positron-ai/tron/pull/2906#issuecomment-4674512577).

These source comments contain workload arithmetic. The refresh did not rerun those workloads. Do not repeat their counts as newly measured performance.

Numerical comparisons also need an explicit policy for not-a-number and infinite values. Wade questioned a comparison that omitted them and distinguished an intermediate accumulator from the normalized output. [Exceptional values, #1997](https://github.com/positron-ai/tron/pull/1997#discussion_r2771743559), [result identity, #1997](https://github.com/positron-ai/tron/pull/1997#discussion_r2771718489).

### Can the tests observe the changed contract?

He identified fakes that discarded transfer descriptors and tests that bypassed the changed dispatch path. He requested small-capacity queue tests for full and wrap states. These are coverage findings unless an implementation failure has also been established. [Transfer arguments, #4128](https://github.com/positron-ai/tron/pull/4128#discussion_r3960538177), [production orchestration, #4128](https://github.com/positron-ai/tron/pull/4128#discussion_r3960538961), [queue capacity, #2903](https://github.com/positron-ai/tron/pull/2903#discussion_r3350173837).

He also challenged tests that froze incidental numeric policies, checks that shared the implementation's helper, and duplicated arithmetic already covered by an observable outcome. He preferred extending an existing suite. A temporary workaround test needed a tracking and replacement plan. [Numerical policy, #4557](https://github.com/positron-ai/tron/pull/4557#discussion_r4188336250), [independent oracle, #4557](https://github.com/positron-ai/tron/pull/4557#discussion_r4188336256), [duplicate mapping check, #4596](https://github.com/positron-ai/tron/pull/4596#discussion_r4146998951), [existing suite, #4265](https://github.com/positron-ai/tron/pull/4265#discussion_r3970127694), [workaround test, #2713](https://github.com/positron-ai/tron/pull/2713#discussion_r3227468540).

### Do metrics describe every promised path and stable identity?

He found a timer covering hardware joins while its documentation included software waits. He questioned operation records split across callers, mixed-workload classification tested only in a simpler generator, and worker rows whose identities changed with worker allocation. He objected to bounds guards that silently lost counts to accommodate malformed tests. [Missing timing path](https://github.com/positron-ai/tron/pull/4596#discussion_r4125033634), [split record ownership](https://github.com/positron-ai/tron/pull/4596#discussion_r4125033653), [mixed workload](https://github.com/positron-ai/tron/pull/4596#discussion_r4125033664), [worker identity](https://github.com/positron-ai/tron/pull/4596#discussion_r4125033686), [silent drops](https://github.com/positron-ai/tron/pull/4596#discussion_r4125033677).

He also warned that enabling high-volume traces could fill the capture buffer and lose later events. Instrumentation cost and useful output belong in the same review. [Trace volume, #3016](https://github.com/positron-ai/tron/pull/3016#discussion_r3456320516).

### Is an invariant duplicated or an integration path missing?

He identified repeated ownership-transfer ordering whose copies could diverge into a lifetime error. He suggested sharing a worker-index mapping and reusing an existing configuration accessor. He asked for a new option to reach the wrapper developers normally used. These are reasons to reuse concrete existing responsibilities, not a general instruction to add abstractions. [Ordering copies, #4128](https://github.com/positron-ai/tron/pull/4128#discussion_r3907214892), [worker helper, #4596](https://github.com/positron-ai/tron/pull/4596#discussion_r4147010638), [configuration accessor, #3016](https://github.com/positron-ai/tron/pull/3016#discussion_r3454460758), [normal wrapper, #3490](https://github.com/positron-ai/tron/pull/3490#issuecomment-5106398334).

### Can a reader trust the explanation and result?

He requested removal of review-round narration, retention of useful compatibility rationale, clearer origins for fixed reference data, and a plan for conflicting specifications. He asked for current or explicitly labeled older results and a description matching the final code. [Review narration, #4596](https://github.com/positron-ai/tron/pull/4596#discussion_r4146947611), [useful rationale, #3738](https://github.com/positron-ai/tron/pull/3738#discussion_r3973917755), [reference-data origin, asim #244](https://github.com/positron-ai/asim/pull/244#discussion_r4020335622), [conflicting specifications](https://github.com/positron-ai/asimovsw-docs/pull/64#discussion_r4095262504), [results and scope, #4557](https://github.com/positron-ai/tron/pull/4557#pullrequestreview-5420005787).

## Counterexamples that constrain the guidance

- **Read later replies.** Wade withdrew a zero-initialization suggestion after learning the type supplied its own defaults. He reconsidered a tracing-name preference when the existing name preserved behavior for current callers. [Initialization retraction](https://github.com/positron-ai/tron/pull/2011#discussion_r2790148917), [naming reconsideration](https://github.com/positron-ai/tron/pull/3733#discussion_r3769729340).
- **A sentinel may be valid.** In an author-side discussion, he retracted a proposed assertion after finding that zero tracked layers represented a software-only model. This is context for avoiding a false positive, not an independent review demand. [Author-side correction, #3385](https://github.com/positron-ai/tron/pull/3385#discussion_r3640191012).
- **Local naming wins over a global preference.** The later #4557 reply accepts value suffixes in existing kernel style and asks for local consistency in shared code. It is explicitly nonblocking. [Qualified naming reply](https://github.com/positron-ai/tron/pull/4557#issuecomment-6021333114).
- **Style and performance are in scope when evidenced.** The old claim that Wade never reviews formatting or benchmark methods is contradicted by his line-length nits and measurement requests. This does not make every style preference a finding. [Line-length nit, #3386](https://github.com/positron-ai/tron/pull/3386#discussion_r3778051701), [measurement request, #2898](https://github.com/positron-ai/tron/pull/2898#issuecomment-4607543703).
- **Assisted reviews remain attributed.** The #3879 summary was explicitly presented as an AI review. It included CI reachability, memory budgeting, consumer-backed layout assertions, and an old/new numerical baseline request. Verify each concern at the relevant revision before using it. [Posted assisted review](https://github.com/positron-ai/tron/pull/3879#issuecomment-5544513215).
- **Approval can coexist with follow-ups.** Wade approved #3490 as-is while relaying optional tracing improvements. Preserve the stated severity. [Approval with follow-ups](https://github.com/positron-ai/tron/pull/3490#pullrequestreview-4800935083).
