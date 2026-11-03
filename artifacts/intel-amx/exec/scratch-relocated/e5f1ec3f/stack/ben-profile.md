# Ben's review taste, from his record (evidence-based)

Ben = Ben Gamari (GitHub bgamari-positron), the main reviewer of jhan's VNNI K stack (PRs 4956-4959).
Every item below cites the evidence: a PR 5047 commit, or a review comment id in ben-corpus.md (same folder).

## What PR 5047 (his rewrite of PR 4956) shows he wants

- P1. One owner of the K layout: the cache (kv_cache.hpp). Commit ade89a9d9c "kv_cache: hide K layout behind row and
  scoring operations": page::score_k (software scoring of selected tokens, both layouts inside), page::try_score_k_amx
  (returns false when the layout has no AMX reader), set_k_row(expr) (conversion of activation rows inside the cache).
  Count of `k_vnni::layout_on` uses: BASE kv_cache 19 / self_attention 2 / model 1 / full 1 -> HEAD 13 / 0 / 0 / 0.
- P2. No public raw K views: the 8 page::k() overloads and page::k_packed removed; page::kv_block is private; tests use
  t/kv_cache_helpers.hpp (set_k_tag / k_tag through set_k_row / get_k_row). Commit message: "remove the public raw K views".
- P3. One control flow per function: commit e17a12ff09 "self_attention: Make token selection logic a bit more obvious":
  the loop only selects tokens into a 64-bit `live` mask; scoring happens once after the loop. The placeholder lambdas
  (`dot_q` returning 0 for one layout, `keys` returning 0 for the other, `[[maybe_unused]]`) are gone.
- P4. A call site asks the cache and takes the answer: apply_dense_amx_page returns bool; the AMX gate is a run-time
  "declined" instead of a compile-time clause at the call site (`&& !k_vnni::layout_on<...>` removed).
- P5. His own words (PR body): "The previously-proposed implementation was a bit spaghetti for my liking."

## What his comments on jhan's PRs show (ids in ben-corpus.md)

- C1. Names must be specific and forward-looking; a reader new to the code must not be confused (5116532748: "really a
  kernel implementing one very specific attention shape"; "amx_k_mirror or similar"; "nearly impossible for a newcomer").
- C2. Environment variables must be documented centrally or replaced by flags (3936807517: "my usual complaint").
- C3. Functions near 200 lines: move code out into a helper (3936963481). Two distinct control-flow paths inside one
  function -> two functions with shared helpers (3936986164: "The surgery in this function is quite brutal").
- C4. Use the existing types: mask_t instead of a hand-rolled uint64_t bitmap (3936968255); tron::bf16 instead of
  uint16_t (3937239431).
- C5. Representation must be typed: "a lot of pointers floating around currently that provide no hints as to the layout
  of the data to which they point"; views that carry the layout; kernels whose signatures state what they accept; misuse
  = compile error (5270587330 and the straw-man in issue comment 5765866077).
- C6. No parallel entry points: "Why do we need to introduce a new function for this? Why not simply extend save_k itself
  with a worker_ix argument and call it consistently from both the main thread and the helpers?" (4065141577).
- C7. Named bool constants are a smell; proper enums are better (4133613638, "good follow-up").
- C8. Note names say what they are: Note [VNNI Packed V layout] (4133643149).
- C9. A comment he cannot follow gets sent back (4133772400 "I'm not sure I understand what Claude is trying to say").
- C10. Reads outside ISO C++ get a ticket (4134028988).
- C11. Code without users is questioned (4134076112: "100 LoC without any obvious users").
- C12. A subtle pattern repeated several times gets deduplicated, and he will open the PR himself (4134925164 -> PR 4697).
- C13. Intermediates belong with the other per-worker state (attn_accum), std::array when the size is static, a single
  amortized allocation is acceptable (3936949728, 3973410716, 3991475816).
- C14. He does not review kernel arithmetic ("I trust that the AMX kernel itself is sound"); he reviews structure,
  names, ownership and comments.
- C15. Syscall or magic constants deserve a short comment (3937013971); a misused memory order gets called out even in
  code jhan did not write (3937077542).
- C16. Pre-existing code: he notes "I know you didn't write this" and still asks; he distinguishes blocker from follow-up.

## How to use this profile in a review

Report a finding only when one of P1-P5 or C1-C16 supports it, and cite that item. Tie the finding to a line the PR adds
or changes (not pre-existing code). State what Ben would write in his own register (short, direct, a question), the
reading cost, and the smallest remedy.
