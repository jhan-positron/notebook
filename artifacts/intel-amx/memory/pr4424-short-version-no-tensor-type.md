---
name: pr4424-short-version-no-tensor-type
description: "jhan 2026-10-08: the PR 4424 Short version (and the other protected sections) stay as they are; do not add a sentence about the typed tensor owner/view port from PR 4557"
metadata:
  type: feedback
---

jhan, 2026-10-08, on the proposal page status/propose-change-PR4424-description.html (one added sentence
about the typed owner `k_vnni_tensor` / views in the Short version): "no, there is no need to talk about
the new tensor type".

**Why:** the Short version states what the PR does for the reader (VNNI K layout, shared block save,
measured effect). The typed tensors are an implementation detail inherited from PR #4557; they belong in
"The changes", which is not protected.

**How to apply:** the four protected sections of the PR 4424 body (Short version, Background, "Remove the
Score transpose...", "Use shared block in saving K") are final; do not propose typed-tensor wording there
again. Related: [[sync-4424-main-20261007]], [[pr-description-no-history]].
