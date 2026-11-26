Thanks for reviewing this again, and for writing the change as code. I took both commits of #5606 unchanged. The branch is fast-forwarded to `90a9110be5`.

- In run [RUN_ID_NIX](https://github.com/positron-ai/tron/actions/runs/RUN_ID_NIX) of the required lane (GCP Nix), the jobs Build Tron and Test host pass. The Test host log lists `t_amx_dispatch_dtype` as passed.
- In run [RUN_ID_CMAKE](https://github.com/positron-ai/tron/actions/runs/RUN_ID_CMAKE) of the CMake workflow (`cmake-single-platform.yml`), test-host passes N_PASS of N_TOTAL tests on RUNNER_NAME, a Granite Rapids runner. That workflow builds with `TRON_AMX_DISPATCH` ON.
- On a Granite Rapids host (delphi-3b35), with `TRON_AMX_DISPATCH` OFF, `t_amx_dispatch_dtype` passes 30,747 assertions in 1 test case. When the registration loses the define, 5 of its 9 sections fail.
- The Verification section of the description now describes the new head.
- The rows of `t_amx_dispatch_dtype` in `config/test-benchmarks.json` still record the placeholder case, 8 MB. On delphi-3b35 the test now peaks at 96.75 to 99.0 MiB. I did not run `bin/slice bench --update`, and the description lists the rows under Open items.
- The current values of both rows come from the weekly refresh (`bench-refresh.yml`). It measures main on both machine classes.

Slice plans the schedule and the memory budget from these rows, and it sets no limit from them.
