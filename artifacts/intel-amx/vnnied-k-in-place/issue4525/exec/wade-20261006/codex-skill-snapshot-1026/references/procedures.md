# Targeted review procedures

Short version: Use the procedure that matches the changed behavior. Record the evidence needed to distinguish a defect from a missing test or an unsupported claim. These are investigation aids, not automatic finding rules.

## Revision and source setup

Read the PR metadata with `gh pr view N --repo OWNER/REPO --json title,body,headRefOid,baseRefName,baseRefOid,commits,reviews`. Here `gh` is the GitHub command-line tool. Resolve the comparison from the actual target branch and reviewed commit, including stacked PRs. Do not hardcode `origin/main`.

Read the complete discussion, including later replies. The following API paths have separate pagination:

- `repos/OWNER/REPO/pulls/N/reviews`: submitted review summaries and states.
- `repos/OWNER/REPO/pulls/N/comments`: inline comments, locations, original commits, and reply identifiers.
- `repos/OWNER/REPO/issues/N/comments`: PR conversation comments.

Use `gh api --paginate` or equivalent connector pagination. A single page is not a complete history. A review location can refer to an earlier commit; map the concern to HEAD before reporting it. Use a temporary evidence directory when saving bodies, diffs, and complete files. Create parent directories before redirecting nested paths.

## Ownership and progress

For each changed asynchronous path, write the sequence from creation to release. Include submission failure, cancellation, shutdown, and repeated use when supported. At every step record:

| Question | Evidence to inspect |
|---|---|
| Who can still read this memory? | Kernel loads, DMA descriptors, callbacks, queued jobs, retained references |
| What permits reuse or release? | Completion record, counter transition, reservation handoff, ownership transfer |
| Which operation does completion identify? | Device, queue, descriptor range, wrap generation |
| What protects concurrent mutation? | Lock owner, atomic ordering, callers, queue producer/consumer contract |
| What guarantees progress? | Producer of the awaited state, error path, timeout or existing failure diagnostic |

Do not infer safety from a buffer being logically unused. Follow the real read width and address range. Do not infer a reference stays valid from an initial `reserve`; follow every operation that can exceed capacity.

When several sites repeat an ownership handoff, compare the full ordering and failure cleanup. A helper is useful when it keeps the invariant in one place. Similar spelling alone is not enough reason to refactor.

## Hardware geometry and boundaries

Trace dimensions from model configuration through hardware eligibility, packing, transfer construction, and consumption. Keep the model's logical shape separate from the hardware's stored shape. Check padding and alignment against the instructions actually used.

Compare singleton, batched, partial, and fallback routes that the change affects. Distinguish a production route from a test utility or an inactive debug file. Recheck current hardware and build constraints instead of assuming those in an old review still hold.

## Test adequacy

For each material test, record the production entry point, stimulus, asserted observation, oracle, and execution gates.

- **Contract:** Name the consumer, documented interface or format, reported regression, or repository rule. The implementation's present behavior is not by itself a reason to freeze that behavior.
- **Independence:** Follow the expected-value helpers. Two wrappers around one address formula are not independent layout evidence.
- **Fake boundary:** List the arguments the fake records, checks, or discards. Checking a submission count cannot prove the address, destination, contents, or length of the transfer.
- **Real route:** Compare the tested call with production. Direct population and transfer calls can bypass grouping, reservation collisions, queue draining, and lifetime handoff.
- **Observation:** Follow write order. A later write can overwrite the state that an earlier operation was meant to validate.
- **Execution:** Establish that the code compiled, the case was selected, the assertion was reachable, and a run recorded its execution. State missing evidence separately.

Use the smallest boundary cases that distinguish plausible failures. For a queue, a smaller injectable capacity can exercise wrap, full, and empty transitions. For grouped transfers, nonzero starts, partial windows, gaps, and page boundaries can expose errors that an index-zero case misses.

Before removing overlap, name a plausible defect caught only by each test. Separate tests may remain useful when they expose distinct failures or explain intent more clearly. Respect repository restrictions on weakening tests. Keep an exact numerical or structural assertion when it protects a documented format, supported compatibility promise, or production boundary. Remove or revise it only with evidence that it protects an incidental detail.

## Performance and instrumentation

Compute operation counts from loops and actual inputs. Keep units explicit: allocations per poll, bytes cleared per submission, gathers per token, or rows folded per forward. Do not translate these into elapsed time without measurement.

For before-and-after runs, record revisions, build settings, model, workload, device, and relevant environment settings. Inspect comparable trace regions. A memory-saving change can add repeated reconstruction work; distinguish the measured tradeoff from a possible workload-dependent regression.

For every metric, write its intended unit and scope, then locate all writers and readers. Check software, hardware, mixed, and alternate entry paths. Trace reset, begin, end, aggregation, and publication. Check whether row identity remains stable when workers change roles. Verify that trace categories and event rates fit the capture buffer.

If the code measures a narrower scope than the documentation promises, offer either implementing the missing measurement or narrowing the claim. Do not require a new instrumentation design when the author explicitly accepts the narrower scope.

## Claims, CI, and result provenance

For a type-safety claim, distinguish:

1. Direct implicit conversion from a pointer is rejected.
2. Explicitly wrapping a pointer is also prevented.
3. A same-shaped generic view is a different type.

Resolve aliases and constructors. An `explicit` constructor can establish the first property while leaving the second open. None of these properties alone establishes lifetime or alignment.

For CI, follow the workflow trigger and any reusable-workflow caller. Trace its effective build options through presets, build recipes, and defaults. Use `gh pr checks N --required` and the run metadata to identify the relevant required checks. Do not equate a workflow's existence with a required check. Do not equate compilation with execution.

For a result, resolve its commit and compare changed paths against HEAD. Label an older run and explain its relevance. If a commit cannot be resolved, report missing provenance; do not invent a rebase or amendment history. Ask for the correct commit or build artifact when that matters.

## Scope, history, and ownership requests

Use the diff and dependencies to decide whether a hunk belongs. Commit subjects, authors, matching identifiers, and text similarity are search aids, not proof. Necessary tests and adaptations remain in scope even if the description needs improvement.

Use commit history to identify repeated fixups. Current blame output cannot show all superseded edits. Consider the intended merge method and an author's stated cleanup plan. Do not require squashing solely because there are many commits.

Check explicit repository ownership rules and actual review requests. A past contributor is not automatically the present owner. If a review asks for a specific person's acceptance, record whether that request was answered at the relevant revision. Surface an unresolved request without adding a new approval requirement or contacting anyone.
