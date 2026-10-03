#!/usr/bin/env python3
"""Build final-pr-body.md from pr-body-live.md (the live PR #4557 body as gh
prints it, CRLF line ends) by replacing the listed lines and inserting the
Status section before "## Labels". Every other byte is kept, CRLF included.
Usage: python3 gen-final-body.py   (run inside exec/ben-20260930)
"""
import pathlib
E = pathlib.Path(__file__).resolve().parent
raw = (E / 'pr-body-live.md').read_bytes().decode('utf-8')
assert '\r\n' in raw, 'expected CRLF line ends in the live body'
NL = '\r\n'
body, tail = raw.rsplit(NL, 1)          # tail = the final "\n" gh adds
live = body.split(NL)
L = {i + 1: l for i, l in enumerate(live)}
new = dict(L)

def rep(n, old, newtxt):
    assert old in new[n], (n, old)
    new[n] = new[n].replace(old, newtxt)

rep(3, "This PR addresses Ben's review comments at PR #4424", "This PR addresses the maintainer's review comments at PR #4424")
rep(3, "a typed owner, view and row for the packed V plane", "a typed owner and view for the packed V plane")
assert L[19].startswith('| owner, view, row |')
new[19] = "| owner, view | `v_vnni_tensor` owns one aligned V plane. `v_vnni_view` is a non-owning matrix view (rows are tokens, columns are dimensions) that holds the address formula. One element is reached through `at(token, dim)`. Whole token rows move through the bulk operations (`append_v_row`, `load_row`, `copy_token`). |"
assert L[36].startswith('  - `v_vnni_view<T, Rows, Cols>`')
new[36] = "  - `v_vnni_view<T, Rows, Cols>`: the address formula, a private pointer constructor, conversion from writable to const only, bounds-checked `at(token, dim)` for one element."
assert L[37].startswith('  - `v_vnni_row<T, Cols>`')
new[37] = "  - No row type and no `expr` base. The first revision had a row expression type `v_vnni_row` and an `operator[]` that returned it. No production code used them. They were removed at the reviewer's request (review thread 4134076112, commit faf8ee42ca)."
rep(40, "Note [Packed V layout]", "Note [VNNI Packed V layout]")
rep(43, "`k_view` now builds its views from this array with no `reinterpret_cast`.", "`k_view` now builds its views from this array with no `reinterpret_cast`. The V reads do the same since the maintainer's PR #4698 (merge commit 8e0cf77bed): `scaled_v_expr`, `fill_storage_slot` and the 8-lane V accessors read `bf16` arrays without a cast.")
rep(44, "(`const_view<Source, true, Dma, seq<head_size>, sseq<1>>` and `view<Destination, ...>`)", "(`const_v_row_view<Source, head_size, Dma>` and `v_row_view<Destination, head_size, Dma>`, the aliases from the maintainer's PR #4697, defined in `v_vnni.hpp`)")
rep(61, "reached only through an owner, a view and a row type with no public pointer.", "reached only through an owner and a view with no public pointer.")
assert L[62].startswith('| Follow the `tensor` / `dtensor` precedent')
new[62] = "| Follow the `tensor` / `dtensor` precedent: one interface built on `expr`, so code can convert, slice and compute on any tensor type. | Dropped by agreement. The first revision gave `v_vnni_view` an `expr` base and a row expression `v_vnni_row`, so that a host tensor could be built from a packed view. No production code read the plane that way: the AMX kernel and `scaled_v_expr` read it in place, and the page methods move whole rows. The reviewer asked why the code exists (thread 4134076112). Commit faf8ee42ca removes the row and the `expr` base. `v_vnni_view` is a plain struct with `at()` and the bulk operations. |"
rep(64, "Element reads go through `expr`.", "Single elements go through `at(token, dim)`.")
rep(67, "Summary: the review's five points are addressed for the planes this PR covers.", "Summary: four of the review's five points are addressed for the planes this PR covers. The `expr` point was dropped by agreement with the reviewer.")
rep(106, " The next section checks the allocation path of the current code.", "")

status = """## Status (2026-10-01)

Commits on top of c73e7fb2f9 (the head the review 5352791816 was made on), oldest first:

| Commit | Review thread | What |
|---|---|---|
| 8bbbb7c82d | B6 (4134925164) | The maintainer's PR #4697 (shared KV row view helpers), taken by fast-forward. His commit id and authorship are kept. |
| 8e0cf77bed | B4 (4134028988) | Merge of the maintainer's PR #4698 (commit 63df10cf90). It removes the three non-ISO reads from `kv_cache.hpp`. Issue #4588 is closed with it. |
| 76502ce5b2 | B2 (4133643149) | Rename Note [Packed V layout] to Note [VNNI Packed V layout] at 16 lines in 7 files. Comment only. |
| a52ce4db25, 55f0068cbf, 34b157326f | B3 (4133869073) | Reword Note [DMA allocation creates objects] in `h/system/memory.hpp`. Comment only. |
| faf8ee42ca | B5 (4134076112) | Drop `v_vnni_row` and the `expr` base of `v_vnni_view` (33 lines added, 140 removed, 4 files). |

Review comments and their outcome:

| Id | Comment | Outcome |
|---|---|---|
| B1 | `aligned` / `dma` as enum types instead of two bool constants (4133613638, not a blocker) | Deferred to issue #4732. The enum change touches three `main` headers and 80 call sites. |
| B2 | Rename the Note to say VNNI (4133643149) | Done, commit 76502ce5b2. |
| B3 | Note [DMA allocation creates objects] is hard to follow (4133869073) | Reworded, commits a52ce4db25, 55f0068cbf, 34b157326f. |
| B4 | Three non-ISO reads need a ticket (4134028988) | Issue #4588 already tracked them. The maintainer's fix PR #4698 is merged as 8e0cf77bed, and #4588 is closed. |
| B5 | `v_vnni_row` has no obvious user (4134076112) | Dropped, commit faf8ee42ca. Element access is `at()`. |
| B6 | Deduplicate the spelled-out row views, PR #4697 (4134925164) | Taken by fast-forward, commit 8bbbb7c82d. |

Unit tests at faf8ee42ca on delphi-3bda (Intel, AMX kernels compiled in), AMX-on tree (`gen`) and AMX-off tree (`gen-amxoff`), every run rc 0 and "All tests passed":

| Tree | Test | Result |
|---|---|---|
| gen | t_llama_unit | 244522 assertions in 44 test cases |
| gen | t_amx_numerics | 12301 assertions in 4 test cases (real AMX) |
| gen | t_amx_dispatch_dtype | 1559 assertions in 1 test case |
| gen | t_heterogeneous_scheduler | 1900 assertions in 2 test cases |
| gen | t_llama_unit, packed-bits case alone ("packed V rows keep their bits through set_v, get_v and at()") | 20755 assertions |
| gen | t_llama_unit, sliding-chunk case alone | 53593 assertions |
| gen-amxoff | t_llama_unit | 244522 assertions in 44 test cases |
| gen-amxoff | t_amx_numerics | 1 assertion (AMX cases compiled out) |
| gen-amxoff | t_amx_dispatch_dtype | 1 assertion (compiled out) |
| gen-amxoff | t_heterogeneous_scheduler | 1900 assertions in 2 test cases |

`make lint-notes` (the repo's checker of Note references) rc 0. Builds: gen 19:10:53 to 19:15:22 UTC, gen-amxoff 19:15:22 to 19:20:07 UTC, both rc 0. Log: /var/tmp/jhan/tron-issue4525-final.log on delphi-3bda.

`t_llama_unit` has 8198 fewer assertions than at c73e7fb2f9 (252720). Commit faf8ee42ca removed 6 row-only static checks (net) and two of the three per-element checks of the packed-bits case (2 x 64 tokens x 64 dims = 8192). That matches the count exactly. No production assertion was removed.
"""
assert L[109] == "## Labels"
out = []
for i in range(1, len(live) + 1):
    if i == 109:
        out.extend(status.split('\n'))
    out.append(new[i])
(E / 'final-pr-body.md').write_bytes((NL.join(out) + NL + tail).encode('utf-8'))
print('wrote final-pr-body.md', len(out), 'lines')
