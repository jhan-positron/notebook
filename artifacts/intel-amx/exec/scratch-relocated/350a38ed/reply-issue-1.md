The results for 45e6bb266d are in the description now (Test section). Both builds, all unit tests in both K layouts, the ingest tests and the format checks pass. Status line: done 2026-10-08 19:39 UTC.

The generated-code count is corrected. The script's pattern matched nothing because the real plugins name the K variable `rope_N`, not `k`. The corrected method and the per-plugin counts are in the inline thread on `ingest/src/TronCpp.hs` and in the description's table: in each of the 19 plugins the main-side and the helper-side `save_k` call counts equal the `save_v` call count (one per KV-writing operation).

Token identity and performance are not run at this head. The description's second Test subsection states that.
