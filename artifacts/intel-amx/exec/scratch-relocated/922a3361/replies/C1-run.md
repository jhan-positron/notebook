Run done: the work of the Test host job, by hand, with `TRON_K_VNNI` on, at bb32a80774, on delphi-3bda (our Intel test machine). Commands: `make build-test-host`, then `make test-host` (= `bin/slice run --filter=host --exclude-tag=slow`), inside `nix develop`, on one socket.

| suite | result |
|---|---|
| head, as is | 89 passed, 1 skipped, 0 failed (makespan 106 s) |
| head with the row-major tail dispatch broken (the tail-row scores set to 0 in self_attention.hpp) | 86 passed, 1 skipped, 3 failed: `t_llama_unit` "apply and join page ranges" (t_llama_unit.cpp:2143), `t_generate_host`, `t_generate_host_2-fast` |
| head again, break reverted | 89 passed, 1 skipped, 0 failed |

So the host suite with the option on passes, and it fails when the tail dispatch is broken. A first pass of the head suite, started 10 minutes after the nightly CI released the machine, had 6 failures of unrelated tests (`t_alloc`, `t_heap`, `t_bf16`, `t_permutation`, `t_safetensors`, `t_pos_lifecycle`) with "heap_setup failed" on a hugepage file that was still held; the rerun in the last row is the clean one.

Not the exact CI recipe: the nix sandbox build with the plugin bundle was not reproduced. Same compiler, same CMake options (RelWithDebInfo, BUILD_NATIVE=OFF, AVX512=ON, test and ingest models), same slice filter. Records: `intel-AMX/exec/results/pr4737-ci-sim-20261002/host-suite-{head,break,restored}.txt` in the development workspace.

Resolving this thread per the author's decision. Turning the option on in the nix test lane stays a CI change outside this PR.
