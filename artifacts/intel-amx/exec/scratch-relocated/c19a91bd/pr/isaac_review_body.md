The shape here is right: one predicate shared by the gate and the kernel signature, the 4-head object code unchanged, and the kernel-case skip now visible instead of a WARN that passed. What holds it up is that none of it runs in CI at this head: no PR lane sets `TRON_AMX_DISPATCH`, so both AMX binaries run as their stubs, the 16-head epilogue has no assertion on its softmax state, and the new transpose lanes have no host-testable path. Details inline.

Not verified: none.

Coverage gaps:
- **Real-AMX execution of `check_qk<16>` and `check_pv<16>` at `4c4b7b8864`.** No CI lane compiled the option on; every review host lacked AMX; the author's record is `round3.log` on delphi-3bda, outside the repository. The reported assertion counts (17,425 with AMX, 4,111 with the kill switch) reconcile exactly to every section running, which corroborates but does not replace in-repo evidence. Still needed: per-section Catch2 output from a Granite Rapids host at this head, or a CI run with the option on landing on a delphi runner. Hand derivations and AVX-512 probes by eleven reviewers cover the transposing store only.
- **AMX-on compile and link at this head.** No CI run; four reviewers' local syntax-only compiles of the kernel TU, both test TUs and `t_llama_unit.cpp` under `-DTRON_AMX_DISPATCH` pass. Still needed: one linked build of both binaries, for example a manual `cmake-single-platform.yml` dispatch at the head.
- **Closed: `TRON_AMX_DISPATCH=OFF` build at the head.** Build Tron job 117831672410 compiled both test TUs with the option off and Test host ran them. This closes the OFF-build gaps raised by sequence/security@fable, full/tests@fable, sequence/denotational@fable, sequence/doctrine@glm and units/correctness@fable.
- **Reports resting on a false CI premise.** full/denotational@glm, units/haskell@glm, units/ponytail@glm, units/security@glm, units/doctrine@glm, sequence/ponytail@glm and sequence/denotational@glm stated that CI built with the option on and that the 16-head sections executed. The build log contradicts this. Their execution-evidence claims count for nothing; their code reading and probes stand.
- **Granite Rapids timing for the 16-head pack and transpose.** Findings 5 and 13 were measured on Zen 4 and via instruction counts. The PR-level Glimmer A/B exists in the author's record only.

Purpose: Justified. Next decision: whether any served head-128 model with kv_mul 8 runs CPU attention in production (if so, add 8 here rather than in a follow-up), and whether to close the benchmark provenance gap with an object compare of the `<16>` instantiation between `5061623a34` and head or one Glimmer rerun.

## Architecture

Ideal.

Approach: the three AMX attention kernels become function templates on `group_heads`, constrained by one constexpr predicate `group_heads_ok` ({4, 16}) that `shape_ok` also uses for the dispatch gate; the bodies stay in the single `-mamx` TU, are explicitly instantiated for both sizes, and the call sites pass the constexpr `geometry.kv_mul()`, with head size honestly fixed at 128 since the tile math is 128-specific.

Ideal: this is the shape I would pick; the gate and the kernel signature share one predicate, so a `kv_mul` that passes `eligible` can only name an instantiable kernel, enforced by the compiler rather than a caller remembering, and a miss in the instantiation list fails loudly at link.

Gaps:
1. `follow-up`: the set {4, 16} is a decision without a written reason. The kernels as written serve any multiple of 4 up to 16 (`amx_attn.cpp:215-216`, `:245-253`; pack and PV are plain loop bounds), so refusing kv_mul 8 (`t/t_amx_numerics.cpp:117-120`, whose comment about "above 16" does not explain 8) is a choice -- unvalidated on hardware? Either instantiate 8 or write why not, in `group_heads_ok`. While there, the first `static_assert` at `amx_attn.cpp:213` is a third copy of the set; the real transpose constraint is `% 4 == 0 && <= 16`, which the second one half-states. Replace the copy with the constraint.
2. `follow-up`: `amx_attn_h128g4` and `_128x4` now lie about the shape they serve, and `amx_attn_iface.hpp:14-16` says "kept" without a why. Comments describe what is. Rename to `amx_attn_h128` / `_128` in a separate mechanical PR.
3. `accepted`: two homes for the group set (predicate plus instantiation list) is the floor for out-of-line template bodies in a single `-mamx` TU; a single-home spelling via an `index_sequence` and odr-use is reachable but buys little over a link error. Note `README.ci.md:586-587` still says "skip with a warning" after the CMake comment moved to "reported as skipped" -- same sentence, two homes, already drifted.

Event: REQUEST_CHANGES, at least one confirmed finding is blocker or major.
