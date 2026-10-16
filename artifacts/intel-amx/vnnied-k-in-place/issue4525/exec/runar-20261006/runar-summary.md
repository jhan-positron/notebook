This introduces a typed owner and view for the VNNI packed V plane, names the row-major native K plane at the kernel boundary, and routes the KV book's DMA allocation through an `operator new[]` so the `kv_block` objects actually come into existence. The direction is right, the layout move is faithful, and the evidence behind it does real work: token identity on delphi-3bda, the A/B band, and the per-function instruction comparison. I found nothing blocking and nothing that changes the shape of the code.

What is left is almost entirely comments that claim more than the code proves, plus one repository rule:

- **The one concrete ask**: refresh `config/test-benchmarks.json` for `t_llama_unit` (t/t_llama_unit.cpp:3461). Stated rule, cheap to satisfy, no CI consequence.
- Three comments in `h/tron/tensor/v_vnni.hpp` describe this refactor rather than the system it leaves behind (lines 57, 74, 190), and the one invariant the new row views assert — the `aligned` flag — lives only in prose (line 209).
- Two Notes disagree on who may take the packed plane address (h/tron/models/kv_cache.hpp:2248).
- The description credits two maintainer PRs in a way that reads as "already upstream" for work that is in this diff, including the `scaled_v_expr` tile-addressing rewrite (h/tron/models/kv_cache.hpp:2190).
- One deferrable pointer on the new Note in `h/system/memory.hpp` (line 197).

I have not repeated the points @Wado-posi and @bgamari-positron already raised.
