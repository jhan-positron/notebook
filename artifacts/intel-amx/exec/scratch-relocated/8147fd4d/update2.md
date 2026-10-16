
---

## Update 2 (2026-10-10, facts from the seam checks that Update 1, U1.9 and the addendum do not carry)

Short version: three facts from the seam checks change the plan text. None changes the recommendation of section 3. They add one decision (D9), one line to PR-4's construction, and two test runs to PR-1's verification. The token-identity cells, the build-location point and the PR-2 tree check are already in U1.9 and the addendum (U1A.1 to U1A.5) and are not repeated here.

### U2.1 PR-3 carries a masked partial-block path that PR-4 deletes (new decision D10)

At the S stage of the probe (3c56db9a95, the tree of PR-1 + S), a run of 2 to 15 consecutive tokens of one block goes through a masked block store. The code: `k_scatter_run_len = 1` [h/tron/models/model.hpp:3141 at 3c56db9a95], the branch test `if (n == k_scatter_run_len)` [:3260], the call `set_k_block(slot, kv_head, c, present, rows)` with a 16-bit present mask [:3292], and page::set_k_block with its `__mmask16 present` parameter [h/tron/models/kv_cache.hpp:2040-2046 at 3c56db9a95].

PR 4737 replaced that path. A run shorter than a block is stored row by row into the row-major tail block, the branch test is `n < k_store_block`, and set_k_block has no mask [head h/tron/models/model.hpp:3300, h/tron/models/kv_cache.hpp:2277-2284]. So with the recommended order PR-3 ships about 15 lines of partial-block logic that PR-4 removes. The reviewer of PR-3 reads them once for nothing. At the head, store_block's masked branch is reached only by the test t_k_vnni_layout [h/tron/tensor/k_vnni.hpp:410-416; the two production callers kv_cache.hpp:2283 and tensor/k_vnni.hpp:508 pass the full mask].

Decision D10, two options:

- (a) Keep PR-3 as the tested tree (the content of 3c56db9a95, re-based on PR-2). The masked path is live production code in PR-3 and PR-4 replaces it. PR-3's body says so. Cost: about 15 lines of review churn.
- (b) Pre-simplify PR-3: a run shorter than a block takes the per-row store (set_k_row), only a whole block takes set_k_block, and the mask parameter goes. Est. 10 to 15 changed lines in model.hpp and kv_cache.hpp plus the mask rows of the block-save test [t/t_k_vnni_layout.cpp:237-261]. Cost: PR-3's tree then differs from the tested 3c56db9a95, the T diff needs a hand repair at those lines, and the 2026-09-15 TTFT numbers were measured with the masked path.

Recommended: (a). Reason: every stack tree stays equal to a tested tree, and the per-PR re-measurement of section 5 costs the same either way.

### U2.2 PR-4 construction: keep `#include <cstring>` in h/tron/kernels/k_vnni.hpp

The 4737 merge diff removes `#include <cstring>` from h/tron/kernels/k_vnni.hpp. Both endpoints of PR 4737 keep the line, so the removal is an artifact of the conflict resolution in the merge [ba69cb513e has it at h/tron/kernels/k_vnni.hpp:15; the head 0a5334ccb6 has it only in h/tron/tensor/k_vnni.hpp:46]. The header still calls std::memcpy [h/tron/kernels/k_vnni.hpp:104 at the head] and reaches it through the tensor header. PR-4 keeps the line (1 line); that is one hunk of the T diff to drop.

### U2.3 PR-1 verification: two test runs that have never happened

In every t_llama_unit run with TRON_K_VNNI=ON so far, AMX was available (delphi-3bda). So a full VNNI page was scored by the AMX kernel of concern A. In PR-1 that kernel does not exist. A full VNNI page then takes the AVX-512 reader k_vnni::qk_group. No t_llama_unit run of that path exists. The kill-switch step of the earlier chains ran t_amx_numerics only [exec/sync4424b-20261007/chain.sh:78, exec/merge4737-20261008/build-test.sh:42].

Section 5, PR-1 column, gains two runs: t_llama_unit on the PR-1 tree with TRON_K_VNNI=ON, and the same binary with TRON_AMX_DISABLE=1. The widened tolerance of the "apply and join page ranges" case reached 0.022 of its 0.05 bound with the AMX kernel present [commit 37064d72b2, message]. Where the reader path lands inside that bound is Insufficient data until the run.

### U2.4 Changes to the decisions list

- New D10 (U2.1; D9 is the "Run CI" label of U1A.2): keep the masked partial-block path in PR-3 (a), or pre-simplify it (b). Recommended (a).
- Sizes: the StructuredOutput of the planner uses U1.9's figures (PR-3 re-based on PR-2 = +678/-75; stack sum 4,267 added lines).
