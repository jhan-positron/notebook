/-
The chunk count of TRON's chunk_evenly, h/tron/models/model.hpp:246
(tron commit 7eddde7895):

    size_t target_n_chunks =
        (n_token_jobs + max_minibatch_size - 1) / max_minibatch_size;

with max_minibatch_size = 128, the value of the llama plugin
(h/tron/plugins/llama.hpp:214).

NOT checked by Lean in the session that wrote it: Lean was not installed.
chunk_count_check.py tests the same two statements for n = 0 .. 1,000,000.
Check this file with Lean 4 (no Mathlib needed):

    lean ChunkCount.lean
-/

/-- The C++ expression, with 128 written out. `/` on Nat rounds down, as in C++. -/
def targetChunks (n : Nat) : Nat := (n + 127) / 128

/-- Enough room: the planned chunks, at 128 token jobs each, hold all n jobs. -/
theorem enough_room (n : Nat) : n ≤ targetChunks n * 128 := by
  unfold targetChunks
  omega

/-- No spare chunk: with one chunk fewer, some job would have no place. -/
theorem no_spare_chunk (n : Nat) (h : 0 < n) : (targetChunks n - 1) * 128 < n := by
  unfold targetChunks
  omega

/- A unit test of the same function checks single inputs, for example: -/
example : targetChunks 300 = 3 := rfl
example : targetChunks 128 = 1 := rfl
example : targetChunks 129 = 2 := rfl
