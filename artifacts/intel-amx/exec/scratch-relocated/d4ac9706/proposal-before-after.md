### line 77
BEFORE:   - `save_k` cuts the pass into work units. It shares the store with the main helpers (`save_k_helper`).
AFTER:    - `save_k` cuts the pass into work units. It shares the store with the main helpers. They call the same `save_k` with their worker index (the main thread is worker 0).

### line 88
BEFORE: - Code generator (`ingest/src/TronCpp.hs`): the generated helpers call `save_k_helper` at the attention statement of every KV-writing operation. `save_k` receives the worker count.
AFTER:  - Code generator (`ingest/src/TronCpp.hs`): the generated helpers call `save_k` at the attention statement of every KV-writing operation. `save_k` receives the worker count and the caller's worker index.

### line 95
BEFORE:   - Checks in `LoopyTronSpec.hs` (the code-generator test suite) on the call text the generator emits for `save_k` and `save_k_helper`.
AFTER:    - Checks in `LoopyTronSpec.hs` (the code-generator test suite) on the call text the generator emits for the two `save_k` calls (main thread and main helpers).

### line 121
BEFORE: The delphi-3bda runs below were taken at 37064d72b2 on 2026-10-08. The head 6b939d25d2 compiles to the same code. The two commits after 37064d72b2 change only comments, one `static_assert` condition and the cost-data file.
AFTER:  The delphi-3bda runs below are from 2026-10-08. The unit-test runs are from 45e6bb266d. The head ba69cb513e differs from it by one comment. The host suite, cost rows, token identity and performance runs are from 37064d72b2. The commits after 37064d72b2 change only comments, one `static_assert` condition, the cost-data file and `save_k` (its worker-index argument, generated calls and tests).

### line 132
BEFORE: | `t_llama_unit` | pass, 251563 / 64 |
AFTER:  | `t_llama_unit` | pass, 251755 / 64 |

### line 142
BEFORE: - `t_llama_unit` 251478 / 64
AFTER:  - `t_llama_unit` 251670 / 64

### line 187
BEFORE: - **Stacked PRs.** PR #4774 (one `save_k` for the main thread and the helpers) and PR #4737 (keeps short K-cache writes row-major, the fix for issue #4500) have this branch as their base. Both need a merge of this head. The `save_k` function and the K-plane helpers they touch are typed here.
AFTER:  - **Stacked PR.** PR #4737 (keeps short K-cache writes row-major, the fix for issue #4500) has this branch as its base. It needs a merge of this head. The `save_k` function and the K-plane helpers it touches are typed here. `save_k` takes a worker index.

