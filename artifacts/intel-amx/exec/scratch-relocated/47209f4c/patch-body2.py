import sys, pathlib, re
src, dst = sys.argv[1], sys.argv[2]
s = pathlib.Path(src).read_text()
def rep(old, new):
    global s
    assert s.count(old) == 1, old[:80]
    s = s.replace(old, new)
rep("This PR (part of #4525) adds typed views to KV cache, instead of bare `bf16` pointers: a typed owner and view for the packed V plane, and a typed view for the native row-major K plane. Stored bytes, conversions, and cache behavior stay unchanged.",
    "This PR (part of #4525) adds typed views to the KV cache, instead of bare `bf16` pointers: a typed owner and view for the VNNI packed V plane, with no public pointer constructor, and a named alias for the existing row-major view of the native K plane. The alias names the layout at the kernel boundary but does not enforce it. Stored bytes, conversions, and cache behavior stay unchanged.")
rep("PR #4424 (the packed-K child) is unchanged. After merging this PR, we will rebase PR #4424 and update its code to use the new tensor data type. The public API in `h/libtron.hpp` is untouched.",
    "PR #4424 (the VNNI packed-K child) is unchanged. After merging this PR, we will rebase PR #4424 and update its code to use the new tensor data type. A distinct, enforced type for the K plane comes with that PR, where K gets its VNNI packed layout. The public API in `h/libtron.hpp` is untouched.")
rep("| AMX-on build, AMX-off build | Configured with `TRON_AMX_DISPATCH=ON` (the AMX kernels are compiled in) or `OFF` (they are not; the configuration the required CI builds). The kill switch below is a run-time setting inside an AMX-on build. |",
    "| AMX-on build, AMX-off build | Configured with `TRON_AMX_DISPATCH=ON` (the AMX kernels are compiled in) or `OFF` (they are not). CI builds AMX-on since PR #4505. Its runners have no AMX, so the kernels execute only on delphi-3bda. The AMX-off tree is a local build that checks the code compiles without the kernels. The kill switch below is a run-time setting inside an AMX-on build. |")
rep("for the existing row-major `view` / `const_view` types. The header holds no vector intrinsics.",
    "for the existing row-major `view` / `const_view` types. The aliases name the layout at the kernel signature but do not enforce it: the type is the generic row-major view, and a pointer still constructs it. The header holds no vector intrinsics.")
rep("| No bare `bf16_t*` (tron's `bf16`) values without an indication of the layout. | The packed V plane (16-lane build) and the native K plane cross the cache and kernel boundaries as typed views. A bare pointer or the other plane's view is a compile error (tested with `STATIC_REQUIRE`). |",
    "| No bare `bf16_t*` (tron's `bf16`) values without an indication of the layout. | The VNNI packed V plane crosses the cache and kernel boundaries as a typed view with no public pointer constructor. A bare pointer or the K view is a compile error (tested with `STATIC_REQUIRE`). The native K plane reaches the QK kernel through `native_k_view`, an alias of the existing row-major view that names the layout but does not enforce it. A distinct K type comes with #4424. |")
# Status section rewrite
a = s.index("## Status (2026-10-05)"); b = s.index("## Labels")
rows = re.findall(r"^\| gen(?:-amxoff)? \| .*\(at 96a6220ab6.*\n", s[a:b], flags=re.M)
assert len(rows) == 10, len(rows)
status = """## Status (2026-10-06)

The branch is one commit on top of `main` dd6e85226b: c5d44bd86f. The reviewed history (21 commits up to the merge of `main` e5fa372c19, plus the test edits of review round 6) is kept on the branch `jhan-kv-typed-tensors-pre-squash-20261006`, so every commit id named in this description stays reachable.

Unit tests on delphi-3bda (an Intel machine with AMX). Two trees: the AMX-on tree (`gen`, AMX kernels compiled in) and the AMX-off tree (`gen-amxoff`, compiled out). Every run has rc (return code) 0 and prints "All tests passed". The rows are from 96a6220ab6 (the merge of `main`, before the squash and the round-6 test edits). The same runs on c5d44bd86f are scheduled after the nightly CI of 2026-10-06 and replace these rows.

| Tree | Test | Result |
|---|---|---|
""" + "".join(rows) + """
`make lint-notes` (the repo's checker of Note references) rc 0 at 96a6220ab6.

Token identity (runtron, qwen3-4b tp2, one user, temperature 0, seed 1, `--pay-for-determinism`, prompt 1024, 256 generated tokens) at c12df586b6 against `main` 996f58ec82 on delphi-3bda, 2026-10-01: CPU attention with the AMX kernels (head, a second head run, base), CPU attention with the kill switch `TRON_AMX_DISABLE=1` (head, base), and FPGA attention (head, base) all produced the same 256 tokens. That run predates the merge of `main`. The same check of c5d44bd86f against `main` dd6e85226b is scheduled with the unit tests above.

"""
s = s[:a] + status + s[b:]
pathlib.Path(dst).write_text(s)
print("patched; stale phrases left:", sum(s.count(x) for x in ["required CI builds", "8196", "19:10:53", "tron-issue4525-final.log"]))
