import sys, pathlib, re
src, dst, tok = sys.argv[1], sys.argv[2], sys.argv[3]   # tok = path to the token-identity paragraph text
s = pathlib.Path(src).read_text()
a = s.index("## Status (2026-10-06)"); b = s.index("## Labels")
status = """## Status (2026-10-06)

The branch is one commit on top of `main` dd6e85226b: c5d44bd86f. The reviewed history (21 commits up to the merge of `main` e5fa372c19, plus the test edits of review round 6) is kept on the branch `jhan-kv-typed-tensors-pre-squash-20261006`, so every commit id named in this description stays reachable.

Unit tests at c5d44bd86f on delphi-3bda (an Intel machine with AMX), 2026-10-06. Two trees: the AMX-on tree (`gen`, AMX kernels compiled in) and the AMX-off tree (`gen-amxoff`, compiled out). Every run has rc (return code) 0 and prints "All tests passed".

| Tree | Test | Result |
|---|---|---|
| gen | t_llama_unit | 249115 assertions in 62 test cases |
| gen | t_amx_numerics | 4109 assertions in 4 test cases, real AMX; 2060 assertions with the kill switch |
| gen | t_amx_dispatch_dtype | 1612 assertions in 1 test case |
| gen | t_heterogeneous_scheduler | 2783 assertions in 3 test cases |
| gen | t_llama_unit, single cases: packed-bits, formula, poison, sliding-chunk | 20751, 8192, 16385 and 53593 assertions |
| gen-amxoff | t_llama_unit | 249115 assertions in 62 test cases |
| gen-amxoff | t_amx_numerics, t_amx_dispatch_dtype | 1 assertion each (compiled out) |
| gen-amxoff | t_heterogeneous_scheduler | 2783 assertions in 3 test cases |
| gen-amxoff | t_llama_unit, single cases: packed-bits, formula, poison, sliding-chunk | 20751, 8192, 16385 and 53593 assertions |

`make lint-notes` (the repo's checker of Note references) rc 0 at c5d44bd86f. CI on c5d44bd86f: GCP Nix and Debian smoke pass.

""" + pathlib.Path(tok).read_text().strip() + "\n\n"
s = s[:a] + status + s[b:]
pathlib.Path(dst).write_text(s)
print("patched; pre-squash markers left:", s.count("96a6220ab6"), "pre-merge markers left:", s.count("predates the merge"))
