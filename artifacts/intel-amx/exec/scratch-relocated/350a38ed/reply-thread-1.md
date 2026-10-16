Done. The counting method in the script was wrong, not the generated code. The pattern `k, *0, *n_workers` assumed the K variable is named `k` (as in the generator test). The real plugins name it `rope_N`, so every count came out 0.

Corrected count at 45e6bb266d (VNNI build, plugin headers under `gen/src/tron/h/tron/plugins/`): every `save_k<...>(...);` call is classified by its last two arguments. The count of `save_v<...>(...);` calls gives the number of KV-writing operations (the generator emits one `save_v` per KV-writing operation, on the main side only). Result for each of the 19 plugins:

- main-side `save_k` calls (`0, n_workers`) = helper-side `save_k` calls (`worker_ix, n_workers`) = `save_v` calls. Examples: qwen3-4b 36 / 36 / 36, qwen3-30b-moe 48 / 48 / 48, gpt-oss-120b 36 / 36 / 36.
- no `save_k` call has any other last two arguments.
- no plugin names `save_k_helper`.

The PR description records the per-plugin counts (Test section: the "generated plugin text" row and the table under the results). The raw table is `exec/results/savek2-20261008/plugin-calls.txt` in jhan's intel-AMX workspace.
