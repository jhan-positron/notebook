**Short version:** I support the proposed four-PR split in principle. The fully packed intermediate cache makes it reasonable to defer the mixed-layout machinery to PR-4. Correct the state invariant, automated test coverage, dependency claims, and construction recipe before treating the plan as ready to execute.

Reviewed `split-plan.md` as written in its initial 244 lines, SHA-256 `8691d6e261e6696123ddcda4b525c057de80021c6d90fb6352a1b4eeec387794`. Source review used base `be0d5565b355a90b6018529d3310565c3f5909cb`, head `0a5334ccb69d038d6bbe3d76ddc77c6b1a2d1a8f`, and the two probe commits `3c56db9a95` and `76a0160b72`.

Terms used below:

- VNNI K is the pair-interleaved layout of the saved key vectors. AMX is the CPU tile instruction set. AVX-512 is the CPU vector instruction set used by the software reader.
- A, S, and T retain the plan's names: the new AMX reader, shared block saving, and mixed row-major/packed blocks.
- CI means continuous integration, the automated checks required for a pull request. A converted-block bit records the actual stored layout. Saved-row bits record which rows have been written.

The proposed merge order remains reasonable:

```mermaid
flowchart LR
  P1["1: Packed cache and readers"] --> P2["2: AMX reader"]
  P2 --> P3["3: Shared block save"]
  P3 --> P4["4: Tail blocks and release enablement"]
```

These arrows show the recommended merge order. PR-2 and PR-3 each need PR-1, but neither fundamentally needs the other.

The first boundary is coherent. Probe `76a0160b72` stores every supported K row directly in the packed layout. Its software reader, row extraction, and cache copies agree on that layout. There is no intermediate conversion to synchronize. The temporary compile-time gate also prevents the existing row-major AMX reader from consuming packed pages. This supports keeping the storage, software reader, and hardware staging together in PR-1. Keeping the release preset disabled until PR-4 is sensible given the performance issue recorded in the plan. [Plan lines 84–106 and 124–131](/home/jhan/workspace/intel-AMX/PR3879/new-PRs/split-4424/split-plan.md:84)

1. **Correct the PR-4 invariant.**

   “Block VNNI iff its 16 bits are set” is false. A short run can complete all saved-row bits while conversion remains queued. The block still contains row-major data until the forward pass ends. Readers must use the converted-block bit to choose the layout. The implementation explicitly represents this state in `note_k_row_saved`, and conversion occurs after outstanding hardware staging finishes. [Plan line 155](/home/jhan/workspace/intel-AMX/PR3879/new-PRs/split-4424/split-plan.md:155); [saved-row completion](https://github.com/positron-ai/tron/blob/0a5334ccb69d038d6bbe3d76ddc77c6b1a2d1a8f/h/tron/models/kv_cache.hpp#L2157); [conversion ordering](https://github.com/positron-ai/tron/blob/0a5334ccb69d038d6bbe3d76ddc77c6b1a2d1a8f/h/tron/models/model.hpp#L1836)

   Suggested replacement: “The converted-block bit selects the layout. A converted block has all 16 rows saved. A complete block may remain row-major while conversion is pending.” Keep the existing test of the states before and after conversion with PR-4. [Existing test](https://github.com/positron-ai/tron/blob/0a5334ccb69d038d6bbe3d76ddc77c6b1a2d1a8f/t/t_llama_unit.cpp#L3931)

2. **Name the required CI configuration that exercises the enabled feature.**

   The cited `cmake-single-platform.yml` workflow runs through manual dispatch or package publication. Default PR CI uses the Nix workflow. Its test build passes neither feature option, so the K-layout and AMX options remain disabled. Some new low-level tests still run, but the cache tests take their row-major branches. Local runs in section 5 do not establish required CI coverage. This is an inherited coverage gap that the split plan should carry explicitly. [Plan line 127 and section 5](/home/jhan/workspace/intel-AMX/PR3879/new-PRs/split-4424/split-plan.md:127); [legacy workflow scope](https://github.com/positron-ai/tron/blob/0a5334ccb69d038d6bbe3d76ddc77c6b1a2d1a8f/.github/workflows/cmake-single-platform.yml#L3); [Nix test configuration](https://github.com/positron-ai/tron/blob/0a5334ccb69d038d6bbe3d76ddc77c6b1a2d1a8f/nix/cmake-tron-test-build.nix#L79)

   Add the existing required suite/configuration that will run the enabled storage paths. Preserve disabled-option coverage. For PR-2, distinguish fake dispatch tests from the numerical test that executes real AMX instructions. The numerical test returns early when AMX is unavailable. Name how it will meet the repository's requirement that committed tests execute in required CI. [Repository test policy](https://github.com/positron-ai/tron/blob/0a5334ccb69d038d6bbe3d76ddc77c6b1a2d1a8f/AGENTS.md#L20); [AMX availability check](https://github.com/positron-ai/tron/blob/0a5334ccb69d038d6bbe3d76ddc77c6b1a2d1a8f/t/t_amx_numerics.cpp#L208)

3. **Construct and check the recommended PR-2 tree; qualify the final-tree comparison.**

   The probe validates PR-1, PR-1 plus S, and PR-1 plus S plus A. The recommended order also needs PR-1 plus A without S. That exact intermediate is absent from the recorded matrix. I checked the stated A patch against the clean PR-1 tree in a scratch directory. `git apply --check` exited with status 1 for `h/tron/models/kv_cache.hpp:666` and `h/tron/tensor/k_vnni.hpp:29`. Both failures involve comment context changed by S. This is a small repair, but the recipe's claim that no hunk reconstruction is needed is too strong. [Plan lines 63–82 and 171–175](/home/jhan/workspace/intel-AMX/PR3879/new-PRs/split-4424/split-plan.md:171)

   Extend the recipe to repair those two headers as well as `amx_attn_iface.hpp`. Record the resulting PR-2 commit and run the syntax matrix on that tree. Keep the full configure, generated-model build, link, and runtime checks already scheduled in section 5. The syntax-only probe does not validate CMake configuration after removing its AMX requirement.

   The final comparison also needs an explicit list of allowed differences. Section 4 merges newer `main` and removes the CMake requirement, but then permits only comment differences from `0a5334ccb6`. Compare against the original head integrated with the same newer `main`, and account separately for CMake decoupling and intentional documentation changes. Every other residual difference needs explanation. [Plan lines 173–176 and decision D2](/home/jhan/workspace/intel-AMX/PR3879/new-PRs/split-4424/split-plan.md:173)

4. **Separate technical dependencies from convenient historical patch order.**

   T needs the block-store operation, consistent readers and writers, and safe conversion timing. It does not intrinsically need helper-thread sharing. The current serial save branch already uses the same storage operation and subsequent layout bookkeeping. Likewise, the dense-layout gate is an adaptation of the AMX path, rather than a prerequisite for the tail-layout mechanism itself. Before A lands, PR-1 already excludes packed pages from AMX dispatch. [Plan lines 51, 120, and 219](/home/jhan/workspace/intel-AMX/PR3879/new-PRs/split-4424/split-plan.md:51); [conversion's block-store call](https://github.com/positron-ai/tron/blob/0a5334ccb69d038d6bbe3d76ddc77c6b1a2d1a8f/h/tron/tensor/k_vnni.hpp#L508); [serial save and bookkeeping](https://github.com/positron-ai/tron/blob/0a5334ccb69d038d6bbe3d76ddc77c6b1a2d1a8f/h/tron/models/model.hpp#L3417)

   Keep the proposed order as the practical choice for reusing historical changes. Describe “T after A and S” as a constraint of that extraction method. The underlying dependency is on the block-store primitive, not the entire shared-worker feature. There is no need to create another PR just to expose this distinction.

5. **Limit token-identity and performance claims to the measured configurations.**

   PR-4 does not establish general token identity with `main` under CPU attention. Converted blocks still reach the packed software reader on fallback paths. That reader documents a different floating-point accumulation order from the row-major reader. Keep the specific successful precheck result, but replace “PR-4 removes [the divergence] under CPU attention” with the measured model, prompts, and run settings. The table should not imply a general numerical guarantee. [Plan lines 153–165 and 206](/home/jhan/workspace/intel-AMX/PR3879/new-PRs/split-4424/split-plan.md:153); [remaining packed-reader path](https://github.com/positron-ai/tron/blob/0a5334ccb69d038d6bbe3d76ddc77c6b1a2d1a8f/h/tron/models/self_attention.hpp#L2024); [different accumulation order](https://github.com/positron-ai/tron/blob/0a5334ccb69d038d6bbe3d76ddc77c6b1a2d1a8f/h/tron/kernels/k_vnni.hpp#L52)

   Likewise, an AMX-disabled run on an AMX-capable host does not establish a gain on other hosts without AMX. Treat the historical measurements as evidence for the proposed order. **Insufficient data:** performance and token behavior of the newly constructed PR heads against current `main`; the runs in section 5 would resolve this. [Plan lines 98–106 and 128](/home/jhan/workspace/intel-AMX/PR3879/new-PRs/split-4424/split-plan.md:98)

Smaller corrections:

- Use one size metric throughout. The probe's C++ test sources contain 964 added lines and 90 removed lines. That is 52.22% of the PR's 1,846 added lines, rather than 57%. `t_llama_unit.cpp` is `+469/-78`; its 547 changed lines are not 547 added lines. The overall 4,264-addition stack sum is correct. These counts come from `git diff --numstat be0d5565b3 76a0160b72`. [Plan lines 7, 78, and 126](/home/jhan/workspace/intel-AMX/PR3879/new-PRs/split-4424/split-plan.md:126)
- When removing the CMake requirement, update the top-level option description too. It still says “requires TRON_AMX_DISPATCH.” Preserve both the library and generated-model compile definitions for the K layout. [Option description](https://github.com/positron-ai/tron/blob/0a5334ccb69d038d6bbe3d76ddc77c6b1a2d1a8f/CMakeLists.txt#L47); [generated-model definition](https://github.com/positron-ai/tron/blob/0a5334ccb69d038d6bbe3d76ddc77c6b1a2d1a8f/src/tron/CMakeLists.txt#L342)
- Section 5 should place builds on `sw-dev-01`, as requested in the workspace instructions. Reserve `delphi-3bda` for real tests. Campaign scheduling must use the live CI lease and `campaign_guard_acquire`, with `ci_took_dut` checks between long runs. “After a nightly” is not the availability test. [Plan lines 183–195](/home/jhan/workspace/intel-AMX/PR3879/new-PRs/split-4424/split-plan.md:183)

Verification for this review: inspected the pinned source and probe trees, checked the saved syntax-matrix summaries, recomputed the size counts, and ran the scratch patch-applicability check described above. The saved [A-off summary](/tmp/claude-0/-home-jhan-workspace-intel-AMX-PR3879-new-PRs-split-4424/8147fd4d-377d-40bd-ae3a-3103383074b7/scratchpad/probe-verify/out/A-off/summary.txt) and [S-off summary](/tmp/claude-0/-home-jhan-workspace-intel-AMX-PR3879-new-PRs-split-4424/8147fd4d-377d-40bd-ae3a-3103383074b7/scratchpad/probe-verify/out/S-off/summary.txt) each contain 22 successful syntax checks. I did not rerun compilation, link, runtime tests, or benchmarks. The four-PR proposal has source-level support; its actual final intermediate revisions still need the verification listed in the plan.
