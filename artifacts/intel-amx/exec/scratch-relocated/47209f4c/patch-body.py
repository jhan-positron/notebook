import sys, pathlib, re
src, dst, sha, date, rows = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]
s = pathlib.Path(src).read_text()
def rep(old, new):
    global s
    assert s.count(old) == 1, old[:70]
    s = s.replace(old, new)
rep("| packed V, VNNI layout | The V plane's storage order in the 16-lane build. ",
    "| packed V, VNNI layout | The V plane's storage order. ")
rep("| AMX, AVX-512, AVX2 | Intel instruction sets. AMX is the tile matrix unit the attention kernels use for dense (fully filled) 64-token pages. AVX-512 is the 512-bit vector unit of the software path. AVX2 is the older 256-bit vector instruction set. |",
    "| AMX, AVX-512 | Intel instruction sets. AMX is the tile matrix unit the attention kernels use for dense (fully filled) 64-token pages. AVX-512 is the 512-bit vector unit of the software path. |")
rep("| 16-lane build, 8-lane build | `TRON_CHUNK_SIZE` 16 (16 fp32 values per vector register: AVX-512, the production build) or 8 (AVX2). Packed V exists only in the 16-lane build. The 8-lane build keeps row-major V. |",
    "| 16-lane build | `TRON_CHUNK_SIZE` is 16 (16 fp32 values per vector register, AVX-512). Since PR #4726 on `main` (merged 2026-10-01) it is the only build. The 8-lane (AVX2) build, with its row-major V, no longer exists. |")
rep("`scaled_v_expr`, `fill_storage_slot` and the 8-lane V accessors read `bf16` arrays without a cast.",
    "`scaled_v_expr` and `fill_storage_slot` read `bf16` arrays without a cast.")
rep(" The 8-lane build keeps its row-major V path unchanged. |", " |")
rep("## Status (2026-10-01)", "## Status (%s)" % date)
rep("| c12df586b6 | B5 (4134076112) | Drop `v_vnni_row` and the `expr` base of `v_vnni_view` (39 lines added, 139 removed, 4 files). |\n",
    "| c12df586b6 | B5 (4134076112) | Drop `v_vnni_row` and the `expr` base of `v_vnni_view` (39 lines added, 139 removed, 4 files). |\n"
    "| %s | (merge) | Merge of `main` e5fa372c19 into the branch. `main` removed the 8-wide chunk-size branches (commit bbc702251e, PR #4726), so the six conflicting files keep the typed packed-V code and lose every `#if TRON_CHUNK_SIZE == 16` guard with its 8-lane `#else` branch. The `#error` guard in `self_attention.hpp` and the guard plus the 8-lane comment paragraph in `v_vnni.hpp` go too. No production line of the PR changes otherwise. |\n" % sha)
# unit-test rows for the merge commit, appended to the unit test table
rows_text = pathlib.Path(rows).read_text()
rep("| gen-amxoff | t_heterogeneous_scheduler (at faf8ee42ca) | 1900 assertions in 2 test cases |\n",
    "| gen-amxoff | t_heterogeneous_scheduler (at faf8ee42ca) | 1900 assertions in 2 test cases |\n" + rows_text)
pathlib.Path(dst).write_text(s)
print("patched; 8-lane mentions left:", len(re.findall(r'8-lane', s)))
