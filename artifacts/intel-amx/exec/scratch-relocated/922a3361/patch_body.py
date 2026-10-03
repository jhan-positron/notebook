import pathlib, sys
p = pathlib.Path(sys.argv[1]); s = p.read_text()
def rep(old, new):
    global s
    assert s.count(old) == 1, old[:80]
    s = s.replace(old, new)
rep("its head is `jhan-amx-vnniK-i4500` at `452b2052c9a130311c1b13c75ad546c34dd35536`.",
    "its head is `jhan-amx-vnniK-i4500` at `9e813a8ce56b7589440902056c31a6f5aae0a100`.")
rep("Existing results inspected for this exact head, recorded on September 30, 2026:",
    "Results for commit 452b2052c9, recorded on September 30, 2026:")
rep("The compiled tests and hardware measurements were not rerun during this review. The full host suite was not run during this review.",
    "Results for commit 9e813a8ce5 (the head), recorded on October 1, 2026, on delphi-3bda (our Intel test machine; fake device; socket 1):\n\n"
    "- With `TRON_K_VNNI=ON`: `t_k_vnni_layout`, `t_amx_dispatch_dtype`, `t_amx_numerics`, `t_llama_unit`, and `t_phase1_integration` all passed, with the same assertion counts as at 452b2052c9.\n"
    "- With `TRON_K_VNNI=OFF`: `t_k_vnni_layout`, `t_amx_dispatch_dtype`, and `t_llama_unit` all passed.\n"
    "- Source records: `intel-AMX/exec/results/pr4737-review-20261001/tests-r1.txt` and `tests-r1rm.txt` in the development workspace.\n\n"
    "Hardware measurements (TPS, TTFT, generated tokens) are from 452b2052c9. The three commits after it change a parameter type, comment passages, and literal spellings with the same values; they were not re-measured. The full host suite was not run.")
p.write_text(s); print("body patched")
