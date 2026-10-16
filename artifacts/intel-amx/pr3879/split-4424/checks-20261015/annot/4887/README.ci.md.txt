# PR 4887 file README.ci.md
# format: <new-file line>| <+ added | ' ' context | - removed><text>
     |@@ -594,7 +594,10 @@ of the AMX tile multiply). The option is OFF by default in every other build.
  594|  Note [K VNNI storage] in `h/tron/models/kv_cache.hpp` describes the layout.
  595|  With the option on, the whole test suite runs on the VNNI layout.
  596|  `t_k_vnni_layout` and the `save_k` case of `t_llama_unit` exercise the VNNI
     | -store, the reader and the page copy. The
  597| +store, the reader and the page copy. The VNNI kernel case of `t_amx_numerics`
  598| +exercises the store and the AMX kernel `qk_vnni_128x4`. That case compiles in
  599| +every `TRON_AMX_DISPATCH=ON` build, with or without this option, and executes
  600| +AMX only on a Granite Rapids runner, as above. The
  601|  `coverage` preset (built by the manual-only `cpp-coverage.yml`) sets neither
  602|  option. It keeps the row-major K layout covered. In the legacy CMake workflow
  603|  the bundled `gen/runtron` is built with `TRON_AMX_DISPATCH=ON` and
