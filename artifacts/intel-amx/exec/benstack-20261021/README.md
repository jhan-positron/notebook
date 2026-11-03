# benstack-20261021: build and test the three re-expressed branches on delphi-3bda

Words used here: the stack = PRs 4957, 4958, 4959 (branches jhan-vnnik-2-amx, -3-shared-save, -4-tail-block); the
re-expressed branches = the same content merged with PR 5047 (Ben's rewrite of PR 4956) and restructured so that the
cache (kv_cache.hpp) alone knows the K layout: jhan-vnnik-2-amx-5047, jhan-vnnik-3-shared-save-5047,
jhan-vnnik-4-tail-block-5047 (worktrees ~/workspace/ai-runs/tron-ben-pr2/3/4); the option = TRON_K_VNNI.

Scripts (forks of exec/pr5047-20261020/build2.sh and tests.sh):
- build.sh: one tag = one commit + one option value; tags bp2/bp2v, bp3/bp3v, bp4/bp4v (OFF/ON). Targets: runtron,
  t_amx_numerics, t_amx_dispatch_dtype, t_llama_unit, t_k_vnni_layout, t_heterogeneous_scheduler (all gating).
- tests.sh: the five test binaries per built tag with the fake device, plus two kill-switch runs.
- run-all.sh: builds two tags at a time, then tests.sh. Launch on 3bda:
  `setsid nohup env SHA2=... SHA3=... SHA4=... bash ~/workspace/intel-AMX/exec/benstack-20261021/run-all.sh >/dev/null 2>&1 </dev/null &`
Results: exec/results/benstack-20261021/ (build-<tag>.txt/.done, tests.txt, tests/<tag>-<name>.log, run-all.done).
Logs: exec/logs/benstack-20261021-*.log. Production serving and the FPGA cards are not touched (no runtron runs here).
