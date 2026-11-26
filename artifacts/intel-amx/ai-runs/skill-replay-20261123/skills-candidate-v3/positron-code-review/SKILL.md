---
name: positron-code-review
description: Review comments in Positron code changes for temporary pull-request review narration. Replace review-round references and comment labels with lasting technical rationale. Use during code review or requested comment cleanup.
---

# Positron code review

Keep code comments understandable without the review conversation. Explain the current design, contract, or failure mode instead of the process that produced the code.

This skill supplies one focused comment-quality check. It does not prescribe a broader correctness review.

## Identify temporary review narration

Read the comments in the requested change and enough surrounding code to understand their purpose. Flag references whose meaning depends on a particular review exchange, such as:

- Pull-request review rounds or numbered review passes.
- Reviewer-specific comment labels.
- Statements that a reviewer requested the code, without the technical reason.

For example, a reference to “review round 4, comment W2” does not explain the code to a future reader.

## Preserve the technical reason

Remove the review-process reference while retaining the useful explanation. State the invariant, ownership rule, ordering requirement, or failure mode that motivates the implementation. An invariant is a condition the code must maintain.

If the surrounding comment already explains the reason, delete only the historical reference. Do not expand or rewrite a clear explanation unnecessarily. If the reason is missing, establish it from the code or supplied discussion before proposing wording.

Example:

> Before: One scope keeps the operation's counters and elapsed time together, as requested in review pass 4.

> After: One scope keeps the operation's counters and elapsed time together for every caller.

Keep explanations of why a tempting alternative fails. Avoid replacing review narration with a comment that merely restates the code.

## Keep the check proportional

Apply the same principle to explanatory comments in production code and tests within the requested scope. A comment cleanup should preserve runtime behavior and test coverage.

Do not treat every issue, pull-request, or design-note link as a defect. Keep a reference when it adds durable technical context. The inline explanation should still make sense on its own. Review history belongs in the pull-request or commit discussion when it has no lasting technical value in the source.

For a review, report the location, the temporary reference, and a concise proposed correction. Treat this as comment maintenance unless there is separate evidence of a correctness problem. When edits are requested, make the smallest change that preserves the rationale.

## Source

This check is derived only from [Wade's linked comment on Tron pull request 4596](https://github.com/positron-ai/tron/pull/4596#discussion_r4146947611). He objected to a source comment that cited a pull-request review round and comment label. The guidance above generalizes that specific observation.
