# PR 4868 file README.ci.md
# format: <new-file line>| <+ added | ' ' context | - removed><text>
     |@@ -564,7 +564,8 @@ pinned test runner.
  564|  cmake -B gen --preset native \
  565|    -DBUILD_TEST_MODELS=ON \
  566|    -DBUILD_INGEST_MODELS=ON \
     | -  -DTRON_AMX_DISPATCH=ON
  567| +  -DTRON_AMX_DISPATCH=ON \
  568| +  -DTRON_K_VNNI=ON
  569|  ```
  570|  
  571|  The build job leaves `TRON_PAGE_SHARE_COUNTERS` at its default (OFF), so the
     |@@ -587,6 +588,22 @@ at its default OFF. The kernel cases of `t_amx_numerics` execute AMX only when
  588|  the test job lands on a Granite Rapids runner; elsewhere they skip with a
  589|  warning.
  590|  
  591| +`TRON_K_VNNI=ON` stores the K cache of 128-dim heads in the AMX VNNI layout
  592| +(VNNI = Vector Neural Network Instructions: the pair-interleaved operand layout
  593| +of the AMX tile multiply). The option is OFF by default in every other build.
  594| +Note [K VNNI storage] in `h/tron/models/kv_cache.hpp` describes the layout.
  595| +With the option on, the whole test suite runs on the VNNI layout.
  596| +`t_k_vnni_layout` and the `save_k` case of `t_llama_unit` exercise the VNNI
  597| +store, the reader and the page copy. The
  598| +`coverage` preset (built by the manual-only `cpp-coverage.yml`) sets neither
  599| +option. It keeps the row-major K layout covered. In the legacy CMake workflow
  600| +the bundled `gen/runtron` is built with `TRON_AMX_DISPATCH=ON` and
  601| +`TRON_K_VNNI=ON`. So its benchmark job measures the VNNI K layout when it uses
  602| +the artifact. When it falls back to the local rebuild (`make gen/config/test`
  603| +sets neither option) it measures the row-major layout. The GCP Nix benchmark
  604| +runtime (`nix/cmake-tron-test-build.nix`) sets neither option and measures the
  605| +row-major layout.
  606| +
  607|  `BUILD_INGEST_MODELS=ON` enables the ingest pipeline integration in the C++
  608|  build. GCP Nix also requires the complete test model profile. Developers can
  609|  still opt out for a specialized local configuration with
