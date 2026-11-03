## The stack

PR #4424 (VNNI K in place) is split into PRs #4956, #4957, #4958 and #4959. PR #5047 rewrites #4956. In its form the cache owns the K layout. The three draft PRs below re-express the rest of the split on that structure. Each one targets the PR branch it re-expresses. Its diff is only the re-expression. They replace nothing yet: each becomes the PR's new head only if its author takes it.

| Order | PR # | PR branch and base | What it adds | State |
|---|---|---|---|---|
| 1 | #5047 | bgamari/vnnik-1 -> jhan-vnnik-1-layout | the cache hides the K layout (page::score_k, page::try_score_k_amx, set_k_row with an expression) | open, author decides |
| 2 | PR2_URL | jhan-vnnik-2-amx-5047 -> jhan-vnnik-2-amx | the VNNI AMX kernel behind page::try_score_k_amx, and the page chooses the query packer | draft until #5047 is taken |
| 3 | PR3_URL | jhan-vnnik-3-shared-save-5047 -> jhan-vnnik-3-shared-save | one page::set_k_block for every slot, and the shared K store as a tron::barrier phase | draft until PR2_URL is taken |
| 4 | PR4_URL | jhan-vnnik-4-tail-block-5047 -> jhan-vnnik-4-tail-block | the row-major tail block inside the cache: the dense gate and the tail scoring in its scoring operations, the pending block as a page-owned record | draft until PR3_URL is taken |

The option stays off in the released package until the fourth PR merges. The preset commit that turns it on is in PR #4959's own history.
