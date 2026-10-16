# Wade review corpus: shard 1

Short version: This shard adds concurrency, performance, observability, and maintainability concerns to the existing skill. It also contains explicit retractions and many comments Wade wrote as an author. The updated skill must preserve those distinctions.

## Coverage and evidence roles

- Read all 389 Wade-authored records on all 64 assigned pull requests (PRs). Of those records, 186 have nonempty bodies.
- 23 PRs have Wade as their author. Their comments mostly explain changes or answer other reviewers. These do not independently establish Wade's review rules.
- The remaining 41 PRs have other authors. Some Wade comments on the branch-integration PRs still act as coauthor replies. These are marked separately in `classification-1.json`.
- PR #3879 is a Claude review Wade posted under his account. PR #4191 explicitly endorses a GPT analysis. They are evidence of reviews Wade chose to present, with assisted provenance. Their individual facts must still be checked against the relevant revision.
- Empty approvals and brief approvals such as “looks good to me” supply no new rule. Every record ID remains in the classification file for completeness.

## Strong additions to the skill

### Trace actual memory reads and completion ownership

- Check the actual device and queue passed to a completion wait. Wade noticed that a loop kept the last transfer state but waited on device zero. The author acknowledged the issue and said a later pass would make the calls device specific. This is a concrete correctness question, not a mandate to block every staged migration. [tron #2011, exact wait object](https://github.com/positron-ai/tron/pull/2011#discussion_r2789792758)
- Capacity reserved in a vector does not protect references when the capacity is exceeded. Check references held across insertion, and test beyond any assumed depth. Wade first asked why the reserve was 64 entries, then explained the reference invalidation risk. [tron #2499, reserve rationale](https://github.com/positron-ai/tron/pull/2499#discussion_r3120756577), [reference lifetime](https://github.com/positron-ai/tron/pull/2499#discussion_r3120788282)
- Dependency removal must match every physical read, including masked data. Wade endorsed the finding that one minibatch can read unfinished values in a shared page. A zero attention weight does not make a concurrent or uninitialized read safe. Zero multiplied by not-a-number (NaN) can still corrupt the output. The author later added real minibatch tests with poisoned unwritten values and verified that restoring the old dependency predicate fails those tests. [tron #4191, endorsed correctness finding](https://github.com/positron-ai/tron/pull/4191#discussion_r3970590653), [author validation of the fix](https://github.com/positron-ai/tron/pull/4191#discussion_r3993927154)
- Numerical comparisons must account for NaN and infinity. Wade questioned a hardware-versus-software comparison that did not do so. He also required the printed label to distinguish an intermediate accumulator from the normalized result. [tron #1997, exceptional values](https://github.com/positron-ai/tron/pull/1997#discussion_r2771743559), [result naming](https://github.com/positron-ai/tron/pull/1997#discussion_r2771718489)

Procedure: trace producer, storage, reader, completion event, and lifetime. State the reachable sequence before assigning severity. Test a boundary that exposes the missing synchronization or invalidated reference. A diagram can show ordering, but do not invent timing measurements.

### Measure the cost moved or added by an optimization

- Ask for before-and-after trace measurements when a memory optimization introduces reconstruction work. Wade requested Perfetto traces to measure rebuilding the staging buffers. Perfetto is the repository's execution trace system. [tron #2898](https://github.com/positron-ai/tron/pull/2898#issuecomment-4607543703)
- Track repeated eviction and reconstruction separately from a single successful offload. Wade warned that unconditional eviction after each completion might repeatedly rebuild the same group during speculation or fanout. He explicitly framed this as a possible later optimization, not an observed regression or a blocker. [tron #2906](https://github.com/positron-ai/tron/pull/2906#issuecomment-4674512577)
- Remove duplicate traversals when the same pass list is already available and a single utility can do both jobs. [tron #4258](https://github.com/positron-ai/tron/pull/4258#discussion_r4029533521)
- For numerical comparisons against an external reference, report the old implementation against the same reference too. Otherwise the new implementation's added error cannot be isolated. This came from the Claude review Wade posted, rather than independent handwritten analysis. [tron #3879](https://github.com/positron-ai/tron/pull/3879#issuecomment-5544513215)

Procedure: identify the moved cost, number of repetitions, and workload that exercises reuse. Request a focused measurement only when it resolves the concern. Label unmeasured performance effects as hypotheses. Do not turn these comments into a requirement to run a full benchmark campaign for every PR.

### Make observability useful without obscuring the run

- Keep high-frequency tracing in the intended detailed category. Wade warned that moving an event to the hardware-attention category could fill the Perfetto buffer and discard later events. [tron #3016](https://github.com/positron-ai/tron/pull/3016#discussion_r3456320516)
- Add new device state to the existing debug display when operators need it. Use the right log category for new weight-reuse messages. [tron #2980, debug display](https://github.com/positron-ai/tron/pull/2980#discussion_r3405051930), [log category](https://github.com/positron-ai/tron/pull/2980#discussion_r3405973171)
- Check the thread that reads counters. Wade asked whether atomics were required because a FUSE reader runs on another thread. FUSE is the filesystem interface used to read live device statistics. This was a question about the design, not a demand that all statistics become atomic. [tron #2980](https://github.com/positron-ai/tron/pull/2980#discussion_r3406007619)
- Consider existing live statistics infrastructure for counters that users might sample over chosen intervals. Wade approved the original implementation and presented FUSE as an option. [tron #4267](https://github.com/positron-ai/tron/pull/4267#pullrequestreview-5156698046)
- Request a sample trace or screenshot when a tracing feature is the change. [tron #3733](https://github.com/positron-ai/tron/pull/3733#issuecomment-5271922621)

Procedure: follow enablement, event frequency, buffer capacity, readers, and interpretation. Keep optional operational improvements separate from data races or broken measurements.

### Reuse existing structure and remove real duplication

- Prefer extending an existing unit-test module when it already constructs, exercises, and destroys the affected object. Wade asked to use the existing book-append tests for a memory-order check. [tron #4265](https://github.com/positron-ai/tron/pull/4265#discussion_r3970127694)
- Remove duplicated logging branches when the formatting already selects the request type. Check the enclosing condition: Wade later observed one copy was unreachable. [tron #2980, duplicate stanza](https://github.com/positron-ai/tron/pull/2980#discussion_r3405150087), [enclosing condition](https://github.com/positron-ai/tron/pull/2980#discussion_r3405963004)
- A large function with growing parallel branches may benefit from helpers. Wade accepted doing this in the next iteration. This is not permission to refactor unrelated code. [tron #2980](https://github.com/positron-ai/tron/pull/2980#discussion_r3405172585)
- Reuse the existing configuration accessor instead of duplicating an environment read, while respecting dependency layers. Wade corrected an implementation that moved the declaration instead of declaring the existing function in the intended source file. [tron #3016, original request](https://github.com/positron-ai/tron/pull/3016#discussion_r3454460758), [clarification](https://github.com/positron-ai/tron/pull/3016#discussion_r3463077403)
- Put declarations near their actual responsibility. This was an explicit nit about placing an unrelated function in the allocation header. [tron #2980](https://github.com/positron-ai/tron/pull/2980#discussion_r3405003751)

### Match words to executable contracts

- Explain a newly introduced mode at first mention, including how it is enabled and disabled. [asimovsw-docs #51](https://github.com/positron-ai/asimovsw-docs/pull/51#discussion_r3855274893)
- A multi-chunk claim must agree with functions that only inspect the first chunk. The author showed the current public entry point only expands once and added an explicit one-chunk assertion. The right remedy was to expose the current invariant, not demand unsupported runtime growth. [tron #2713, mismatch](https://github.com/positron-ai/tron/pull/2713#discussion_r3227529208), [author context and remedy](https://github.com/positron-ai/tron/pull/2713#discussion_r3228805183)
- Explain unexplained divisors and reserved capacities. [tron #3016](https://github.com/positron-ai/tron/pull/3016#discussion_r3454926024), [tron #2499](https://github.com/positron-ai/tron/pull/2499#discussion_r3120756577)
- Name a sentinel for its meaning rather than overloading a count, when the current spelling is misleading. Wade marked this as a nit. [tron #2713](https://github.com/positron-ai/tron/pull/2713#discussion_r3235796275)
- Match filesystem paths in comments to the identifier used in code. Wade corrected a comment that said device bus address while the implementation used device index. [tron #2980](https://github.com/positron-ai/tron/pull/2980#discussion_r3405930260)
- Remove comments that narrate a story number or incorrectly couple a general trace event to one feature. [tron #2906, story number](https://github.com/positron-ai/tron/pull/2906#discussion_r3350285744), [unrelated explanatory comment](https://github.com/positron-ai/tron/pull/2906#discussion_r3350412400)
- Avoid references to an author's private log path. [tron #2713](https://github.com/positron-ai/tron/pull/2713#discussion_r3227565141)

### Verify tests and track real workarounds

- Run a representative set of relevant unit tests before merge. Wade's approval was conditional on this validation, and he later posted the named passing tests. [tron #2698, request](https://github.com/positron-ai/tron/pull/2698#pullrequestreview-4265644124), [results](https://github.com/positron-ai/tron/pull/2698#issuecomment-4422833076)
- Ask whether disabling a test or leaving a debug macro enabled was intentional. [tron #2011, disabled test](https://github.com/positron-ai/tron/pull/2011#discussion_r2790161683), [tron #2499, debug macro](https://github.com/positron-ai/tron/pull/2499#discussion_r3124878965)
- Track a temporary workaround and explain why its regression test should eventually be replaced. Wade questioned a test that permanently asserted allocation order to avoid an unexplained first-transfer hang. The author created a follow-up and agreed to replace it when the real cause was understood. Do not delete a necessary regression guard merely because its mechanism is temporary. [tron #2713, tracking](https://github.com/positron-ai/tron/pull/2713#discussion_r3227447122), [test concern](https://github.com/positron-ai/tron/pull/2713#discussion_r3227468540), [author response](https://github.com/positron-ai/tron/pull/2713#discussion_r3228745782)
- A successful test process does not prove optional code ran. The posted assisted review distinguished compiled-out stubs from hardware-independent tests that could run in continuous integration (CI). [tron #3879](https://github.com/positron-ai/tron/pull/3879#issuecomment-5544513215)

## Corrections, limits, and contradictions to the old skill

1. **Remove the categorical statement that Wade does not review formatting or benchmark method.** He asked for long Markdown lines to be formatted in #3386, suggested include grouping in #2980, called redundant `public` a nit in #2906, and requested before-and-after tracing in #2898. These are small preferences and focused evidence requests, not universal blockers. [long lines](https://github.com/positron-ai/tron/pull/3386#discussion_r3778051701), [include grouping](https://github.com/positron-ai/tron/pull/2980#discussion_r3405979630), [redundant access label](https://github.com/positron-ai/tron/pull/2906#discussion_r3391446464)
2. **Do not convert suggestions into language rules.** Wade suggested C-style zero initialization in #2011, then explicitly retracted it after learning the struct supplied member defaults. The author also corrected his proposal to repeat default argument values in the implementation. Read the entire thread before prescribing a remedy. [retraction](https://github.com/positron-ai/tron/pull/2011#discussion_r2790148917), [default argument correction](https://github.com/positron-ai/tron/pull/2011#discussion_r2790104144)
3. **Caller migration can justify a name that first looks backwards.** Wade initially wanted a `_traced` wrapper name, then acknowledged that preserving the public function name makes all existing callers gain tracing. Do not turn the first comment into a fixed naming rule. [initial preference](https://github.com/positron-ai/tron/pull/3733#discussion_r3769684790), [acknowledgment](https://github.com/positron-ai/tron/pull/3733#discussion_r3769729340)
4. **Retracted questions supply no settled design rule.** Wade asked whether a DMA completion change was about correctness rather than performance, then withdrew the question after a call. [withdrawal](https://github.com/positron-ai/tron/pull/1860#discussion_r2709806008)
5. **A local-path problem is broader than one PR-body section.** #2713 points to a private log inside a header comment. The old rule's section-limited trigger misses this case.
6. **Static assertions are appropriate when they guard a real consumer assumption.** The assisted #3879 review asks for an array-layout assertion because a kernel directly relies on the row stride. This supports the existing consumer-based exception, not a ban on structural assertions.
7. **Evidence must be tied to the reviewed revision.** The #3879 author reply describes which blocking findings were fixed, which left the PR with the mirror feature, and which CI limitation remained. Do not repeat those original findings on the narrower later PR. [later scope and validation](https://github.com/positron-ai/tron/pull/3879#issuecomment-5628338318)
8. **Severity depends on reachability.** Wade's author replies in #2796 reject several bot findings after tracing callers, supported hardware dimensions, queue ordering, or shutdown-only usage. They also merge duplicate reports of one root cause. These replies corroborate the need to verify findings, but are not counted as independent reviewer rules. [caller preconditions](https://github.com/positron-ai/tron/pull/2796#discussion_r3290347024), [unsupported dimensions](https://github.com/positron-ai/tron/pull/2796#discussion_r3291461089), [duplicate root cause](https://github.com/positron-ai/tron/pull/2796#discussion_r3291538124)

## Suggested concise core checklist

- What real caller reaches the issue, and what state makes it fail?
- Do waits, readers, and object lifetimes refer to the same device, storage, and operation?
- What work or memory cost is added, and what focused measurement can establish its effect?
- Can the feature be observed without flooding logs or changing normal execution?
- Does an existing accessor, loop, test, or header already own this responsibility?
- Do names, comments, tests, and public claims describe the same behavior at this revision?
- Do CI and unit tests execute the changed path, including its relevant boundary?
- Is the point a blocker, a coverage gap, a preference, a tracked follow-up, or a retracted concern?

Keep the existing detailed #4557 procedures as case-specific examples. They should not crowd out the earlier and broader technical review patterns above.
