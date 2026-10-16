# Wade review analysis: shard 0

Short version: The useful recurring questions are broader than test cleanup. Wade checks whether names, claims, counters, and interfaces mean the same thing on every relevant path. He distinguishes fixes from optional cleanup and changes his position when context changes.

## Coverage and attribution

- Read every Wade body in the 63 assigned pull requests (PRs), including every approval record and short reply. The source contains 347 records. The companion `classification-0.json` records every assigned ID.
- The classification has 14 PRs with substantive reviewer comments, 18 with approvals only, 29 authored by Wade, and 2 with contributor explanations on another author's PR.
- Author replies provide context and useful corrections. They do not establish independent Wade review demands. Model-generated text is identified below when he relays it.
- Read the surrounding reply threads for the important disputed points in Tron #2176, #3008, #4557, and #4596. A later approval does not prove every earlier premise was correct.

## Recurring review questions

### Does the claim hold on every path that the feature covers?

This is the strongest unifying question in this shard.

- **Tron #4596:** The join-wait counter timed the hardware wait but omitted the software poll. A zero counter therefore did not establish zero waiting. Wade offered two repairs: time the software path or narrow the documentation. The author confirmed the mismatch and added timing. [Review comment](https://github.com/positron-ai/tron/pull/4596#discussion_r4125033634)
- **Tron #3008:** Wade relayed a model finding that a helper returning the first transmit descriptor only set its result inside the metadata loop. Legacy requests had no metadata, so they returned descriptor zero. The author linked a fix. The finding was explicitly labeled low severity. [Review comment](https://github.com/positron-ai/tron/pull/3008#discussion_r3437517809)
- **Tron #4557:** The only independent packed-layout check followed a hardware-availability return. A separate accessor-based test shared the address helper and could agree on the same wrong formula. [Review comment](https://github.com/positron-ai/tron/pull/4557#discussion_r4188336256)

Reusable instruction: trace the actual callers and alternate modes behind a claimed guarantee. Read past compile success and test presence to the assertion or observation that would expose a failure.

### Do identities, dimensions, and categories represent the thing users need?

- **Tron #2176:** Wade questioned using token IDs where the hardware needed token positions. Another reviewer explained that single-user ordering had hidden the distinction. The author reported a fix. [Review comment and replies](https://github.com/positron-ai/tron/pull/2176#discussion_r2948176586)
- **Tron #4596:** Whole-forward classification made any mixed prompt/decode forward belong to `prompt_or_mixed`. Testing only the command-line generator could not show the serving case. Wade accepted deliberate forward-level classification if the documentation stated the limitation. The author kept it and added interpretable counts. [Review comment](https://github.com/positron-ai/tron/pull/4596#discussion_r4125033664)
- **Tron #4596:** Attention-worker indices mapped to different pool threads when the split changed. Per-worker rows therefore mixed thread identities. Wade offered stable pool-worker keys or sufficient configuration metadata. [Review comment](https://github.com/positron-ai/tron/pull/4596#discussion_r4125033686)
- **Tron #2176:** A fixed 8,192-byte page allocation appeared to encode eight key/value heads. Wade asked how larger models would be represented. Replies showed that the real hardware layout was more involved than changing one scalar. [Review comment and replies](https://github.com/positron-ai/tron/pull/2176#discussion_r2947992404)

Reusable instruction: identify the logical unit of each field and counter. Test the assumptions with another supported model, workload, worker split, or caller. Treat these as design questions when more than one representation is valid.

### Is one invariant expressed once and owned across its full lifetime?

- **Tron #4596:** The scheduler wrote forward totals while the model wrote token totals. Other model callers could produce contradictory records. Wade suggested moving ownership into the common path or using one scoped helper. [Review comment](https://github.com/positron-ai/tron/pull/4596#discussion_r4125033653)
- **Tron #4596:** Three paths computed the same worker mapping with two spellings. He suggested one helper to prevent later drift. This was explicitly a nit. [Review comment](https://github.com/positron-ai/tron/pull/4596#discussion_r4147010638)
- **Tron #2176:** A callback lambda did nothing beyond forwarding to a function with the correct signature. He proposed registering the function directly. [Review comment](https://github.com/positron-ai/tron/pull/2176#discussion_r2954613896)
- **Tron #1666:** He asked to centralize repeated hardware/model constants. This supports meaningful shared definitions, not a universal naming syntax. [Review comment](https://github.com/positron-ai/tron/pull/1666#discussion_r2620219338)

### Does defensive handling hide an invalid production state?

- **Tron #4596:** Index guards silently dropped measurements and existed to accommodate incorrectly sized tests. Wade asked for assertions and valid test fixtures. [Review comment](https://github.com/positron-ai/tron/pull/4596#discussion_r4125033677)
- **Tron #2078:** He asked whether self-move was a legitimate operation or an error that should assert. This was a question, not a blanket ban on defensive handling. [Review comment](https://github.com/positron-ai/tron/pull/2078#discussion_r2825119397)

Reusable instruction: distinguish invalid state from a documented sentinel, asynchronous retry, or supported fallback before recommending an assertion.

### Does each test protect an observable contract without accidental restrictions?

- **Tron #4557:** Tests pinned NaN-to-infinity conversion and incidental rounding without a named consumer. Wade requested preserving exact transport and partner-zero checks. [Review comment](https://github.com/positron-ai/tron/pull/4557#discussion_r4188336250)
- **Tron #4557:** He distinguished useful kernel boundary probes from structure checks and duplicated assertions. The author retained alignment and temporary-owner checks with a concrete contract explanation, and Wade later approved. Do not turn the first comment into an absolute prohibition. [Review thread](https://github.com/positron-ai/tron/pull/4557#discussion_r4188336302)
- **Tron #4596:** One test repeated mapping arithmetic already observed by a test checking where counts landed. He called dropping it a nit. [Review comment](https://github.com/positron-ai/tron/pull/4596#discussion_r4146998951)

Reusable instruction: name a failure each test can detect that existing tests cannot. Preserve distinct observations. The corpus does not justify forcing all partially overlapping tests into one case.

### Can a future reader trust the comment, description, and reference?

- **Tron #4596:** He asked to remove references to review-round numbers from production and test comments. [Production comment](https://github.com/positron-ai/tron/pull/4596#discussion_r4146947611), [test comment](https://github.com/positron-ai/tron/pull/4596#discussion_r4146959502)
- **Tron #3738:** He challenged deletion of a hardware compatibility explanation that remained relevant. Concision does not justify removing useful rationale. [Review comment](https://github.com/positron-ai/tron/pull/3738#discussion_r3973917755)
- **Tron #2176:** He asked what `kv_hint` meant. The reply explained a temporary but nontrivial tree/book relationship. [Review thread](https://github.com/positron-ai/tron/pull/2176#discussion_r2948108341)
- **ASIM #244:** He asked where a fixed digest came from and whether it was registered in the evidence document. [Review comment](https://github.com/positron-ai/asim/pull/244#discussion_r4020335622)
- **asimovsw-docs #64:** He asked for a retirement plan for conflicting specifications. He later accepted references to moving documents while the specification itself was moving, provided someone maintained the correspondence. [Spec retirement](https://github.com/positron-ai/asimovsw-docs/pull/64#discussion_r4095262504), [qualified acceptance](https://github.com/positron-ai/asimovsw-docs/pull/64#issuecomment-5818393161)
- **Tron #4557 and #4596:** He called out stale PR descriptions after code changes. #4557 also requested a rerun or pre-merge label for old results. [#4557 review](https://github.com/positron-ai/tron/pull/4557#pullrequestreview-5420005787), [#4596 approval](https://github.com/positron-ai/tron/pull/4596#pullrequestreview-5371062950)

### Does the normal entry point expose the feature?

**Tron #3490:** A new Runtron tracing option needed forwarding through the script developers usually used. Wade also corrected calling it a Perfetto option. The naming point was a nit. [Discussion comment](https://github.com/positron-ai/tron/pull/3490#issuecomment-5106398334)

In the same PR, he relayed optional model-assisted suggestions about copied dependency macros drifting, direct includes bypassing the tracing gate, a single-writer assumption, and per-generation window numbering. He explicitly approved the PR as-is and allowed follow-up work. Preserve this severity. [Approval](https://github.com/positron-ai/tron/pull/3490#pullrequestreview-4800935083)

### Is the change intentional and within the current scope?

- **Tron #1973:** He asked whether temporary debug switches were meant to remain enabled. [Attention debug](https://github.com/positron-ai/tron/pull/1973#discussion_r2759894229), [worker debug](https://github.com/positron-ai/tron/pull/1973#discussion_r2759903853)
- **Tron #2659:** He asked whether an unexpected `.gitkeep` change was intentional. [Review comment](https://github.com/positron-ai/tron/pull/2659#discussion_r3197414598)
- **Tron #4557:** He requested splitting unrelated alignment and tile-name changes, squashing repeated comment commits, and shortening operational details in the description. This supports scope review; it does not support a heuristic that all tests-only or other-author commits are unrelated. [Review summary](https://github.com/positron-ai/tron/pull/4557#pullrequestreview-5420005787)

## Corrections, preferences, and limits

- **The newer naming position is local consistency, not a universal suffix ban or universal suffix exemption.** Wade accepted existing suffix style in AMX kernel files. In shared code, he requested the existing literal-plus-local-name style. He explicitly made this nonblocking. The user's chosen convention still has instruction priority. [Later #4557 comment](https://github.com/positron-ai/tron/pull/4557#issuecomment-6021333114)
- **Placement is negotiable.** In #2176 he first preferred constants at the file top, then accepted another reviewer's suggestion to put them in `config.hpp`. [Original preference](https://github.com/positron-ai/tron/pull/2176#discussion_r2947931435), [revision](https://github.com/positron-ai/tron/pull/2176#discussion_r2949458908)
- **An owner request is contextual.** The #4557 `operator new[]` concern names one widespread header change and a particular missing review context. It does not establish that every hard-to-test header change needs fresh explicit approval. [Comment](https://github.com/positron-ai/tron/pull/4557#discussion_r4188336279)
- **An absence of comments proves little.** Eighteen assigned PRs contain approvals without substantive findings. They do not prove Wade inspected or accepted every conceivable design choice.
- **No assigned review record uses `CHANGES_REQUESTED`.** Preserve explicit nits, design questions, approval, and follow-up language. Do not infer blocking severity merely from `COMMENTED`.

## Author-side technical cases worth retaining as cautions

These are not independent review demands. They are useful examples of how an apparently reasonable finding can be wrong.

- **Tron #3385:** Wade initially relayed a claim that out-of-range layer branches were dead and agreed to remove or assert them. He then found that zero tracked layers is valid for a software-only model and retracted the proposal. [Initial claim](https://github.com/positron-ai/tron/pull/3385#discussion_r3640079711), [retraction](https://github.com/positron-ai/tron/pull/3385#discussion_r3640191012)
- **Tron #3385:** Three capacity replies distinguish a live overflow from a currently safe but implicit bound. `32 queries × 4 subpasses = 128 metadata slots` enforced safety at that revision; a static assertion would protect future changes. [Example response](https://github.com/positron-ai/tron/pull/3385#discussion_r3633154450)
- **Tron #3385:** An empty hardware plan was not a real fallback when earlier classification had already excluded that work from software. Wade reported fixing the common eligibility gate and making the impossible planner state assert. [Response](https://github.com/positron-ai/tron/pull/3385#discussion_r3633330935)
- **Tron #2832:** A CPU mutex cannot synchronize writes from hardware that never takes it. A stale completion read was harmless if it only caused another poll; a false completed result would permit premature reuse. [Response](https://github.com/positron-ai/tron/pull/2832#discussion_r3321715823)

The old skill's exclusion of arithmetic, formatting, or benchmark concerns is unsupported. The corpus instead supports checking concrete evidence, preserving explicit scope, and allowing the reviewer to be corrected.
