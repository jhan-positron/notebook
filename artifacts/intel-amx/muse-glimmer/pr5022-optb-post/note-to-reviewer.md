I am requesting your review again for one reason: commit `e863b27272` changes the `s_pages` line that came from your suggestion, and it landed after your approval.

**What changed**, in `apply_dense_amx_page` (`h/tron/models/self_attention.hpp`):

- Before: `tensor<operation_kv_mul, page::page_size> s_pages{uninitialized};`
- Now: `auto s_pages = make_array_of<tensor<page::page_size>, operation_kv_mul>(uninitialized);`

**Why.** Note [Uninitialized Weight Tensors] on main says that the tag is well-defined for a one-dimensional tensor only. A tensor of two or more dimensions keeps its rows in a union that the tag constructor never constructs, so access to the rows is undefined. Bugbot flagged the line for this in [this thread](https://github.com/positron-ai/tron/pull/5022#discussion_r4687860178). The new form builds each row as a one-dimensional tensor with the tag. It keeps what your suggestion was for: the buffer is not zero-filled.

**One point for your judgment.** The Note's last sentence says that a function which fills a multi-dimensional tensor itself default-constructs it and pays one zero fill. Here `s_pages` is an array of 4 or 16 one-dimensional tensors, so every row is constructed and no fill is paid.

**Evidence.** Two builds of `187da02163` are compared on delphi-3b35 (Xeon 6962P, `TRON_AMX_DISPATCH` ON), one without and one with the new declaration:

- `t_amx_dispatch_dtype`, `t_amx_numerics` and `t_llama_unit` pass in both builds.
- The generated tokens are identical for Muse Glimmer 30B and for llama-3.1-8b-instruct-good (tp4, 1 user, temperature 0, seed 1, 256 tokens).
- With 8 users and a 1024-token prompt, the decode speed differs by +0.16% on Glimmer and by −0.01% on llama. Both differences are inside the run-to-run spread of 4 repetitions per build.

The branch is also rebased onto main `cef7aab2f9`. The rebased tree equals a merge of `90a9110be5` with main. CI_SENTENCE
