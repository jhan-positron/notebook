Replies to the non-inline items (items 1 and 2 are answered above).

**Commits.** Squashed: the branch is one commit on top of `main`, c5d44bd86f, including the test edits from this review. The reviewed history is kept on `jhan-kv-typed-tensors-pre-squash-20261006`, so the commit ids in the description stay reachable.

**CI builds AMX-off.** Correct, that sentence was stale since PR #4505. The Words row now says: CI builds with the AMX kernels compiled in, its runners have no AMX, and the kernels run only on delphi-3bda.

**Results before the merge.** The unit-test rows now carry the merge commit 96a6220ab6 and are labelled pre-squash. The token-identity rows are labelled pre-merge. Both are re-run on c5d44bd86f on delphi-3bda after tonight's nightly CI, and the rows get replaced then.

**Arithmetic, timestamps, log paths.** Removed.
