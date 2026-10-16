#!/usr/bin/env python3
"""Assemble the new PR 4424 body: lines 1..28 (the four protected sections) verbatim from the live copy,
then the rewritten sections. Writes new-body.md next to the live copy and prints a line diff summary."""
import re, sys, difflib

S = "/tmp/claude-0/-home-jhan-workspace-intel-AMX-PR3879-new-PRs-merge-4737-2-4424/19680312-df5d-4bfa-9f32-ac8dc69334d0/scratchpad/"
live = open(S + "live-body-4424.v2.md").read()
lines = live.split("\n")
assert lines[28] == "## Words used here", lines[28]
protected = "\n".join(lines[:28]) + "\n"          # lines 1..28 (28 = the blank line before Words)
assert protected.count("## Short version") == 1 and protected.endswith("\n\n")

# ---------------------------------------------------------------- Words used here
words_start = 28
changes_start = lines.index("## The changes")
words = lines[words_start:changes_start]
text_words = "\n".join(words)

def row(term):
    m = [l for l in words if l.startswith("| " + term + " |")]
    assert len(m) == 1, (term, len(m))
    return m[0]

old = row("shared block save")
new = ("| shared block save | The K store of this branch. The pass's tokens are cut into work units (runs of consecutive tokens "
       "inside one 16-token block of a page). The main thread and the idle main helpers claim the units from one counter. "
       "A unit that fills its whole block is written with 16 rows transposed in registers, one 64-byte line at a time. "
       "A shorter unit is written row by row into the block's row-major form: 4 whole 64-byte lines per token "
       "(see row-major tail block). |")
text_words = text_words.replace(old, new)
old = row("base")
new = ("| base | Two comparators are called base. In the Background section and in the PR #3879 table of the Measurements "
       "section, base is the PR #3879 binary (commit 544ca05c7a). Everywhere else base is `main` at be0d5565b3, the commit "
       "this branch is synced to: as the nightly package 2026.10.08-be0d5565 in the nightly-config measurements, and as a "
       "`runtron` build without `TRON_K_VNNI` (row-major K, AMX dispatch on) in the runtron cells and the token-identity check. |")
text_words = text_words.replace(old, new)
old = row("dense page")
new = ("| dense page | A full 64-token page, all of it visible to the query, with its 4 blocks converted: the case the AMX QK "
       "kernel (the kernel that multiplies the query by the K rows to produce the attention scores) handles. |")
text_words = text_words.replace(old, new)
# new rows after "dotter"
anchor = row("dotter")
new_rows = anchor + "\n" + "\n".join([
    "| row-major tail block | A 16-token block of a VNNI K plane whose 16 rows are not all saved yet. It holds its rows row-major "
    "(one contiguous 256-byte row per token) inside the block's own 4 KiB. A row store into such a block writes 4 whole 64-byte "
    "lines, as the row-major layout does. Note [Row-major tail block] in `h/tron/tensor/k_vnni.hpp`. |",
    "| converted block | A block whose 16 rows are saved and whose bytes were transposed in place into the VNNI layout: by the "
    "whole-block save at once, or at the end of the forward pass that saved the 16th row. The page records per storage slot "
    "which rows are saved and which blocks are converted (Note [K VNNI storage]). |",
    "| hardware-scored operation | An attention operation whose scores come from the FPGA (the model's hardware attention). "
    "Its K blocks are never converted: the FPGA staging reads the rows in place, and the CPU scores only the tail the FPGA has "
    "not processed. Note [Row-major blocks under hardware attention] in `kv_cache.hpp` (the fix of issue #4500). |",
    "| nightly CI, perf configs | The nightly System CI run of positron-ai/systems_test on delphi-3bda (the Intel Xeon 6962P test "
    "machine, two CPU sockets, eight FPGA cards). Its perf phase measures 14 configs (model, tensor-parallel degree, user count, "
    "prompt length), 10 rounds of one request per user each, through platformd (the service that starts the rinzler engines) "
    "and the Caddy proxy, with the tron package installed from apt. A pass = one run of the 14 configs with one package. |",
    "| TTFT, paired t, resolved | TTFT = time to first token. The paired t statistic is computed over the per-round differences "
    "(this branch minus base, round means) of the pass pairs. A difference is resolved when the paired t is at least 2.26 in "
    "magnitude and the difference is at least 1 % (TTFT: also at least 1 ms). |",
    "| VmHWM | The peak resident memory of a process since it started (`/proc/PID/status`). The memory column sums it over the "
    "rinzler engine processes of a config. |",
])
text_words = text_words.replace(anchor, new_rows)
words_block = text_words + "\n"

# ---------------------------------------------------------------- The changes
meas_start = next(i for i, l in enumerate(lines) if l.startswith("## Measurements"))
changes = "\n".join(lines[changes_start:meas_start])

def sub(text, old, new):
    assert text.count(old) == 1, old[:70]
    return text.replace(old, new)

changes = sub(changes,
    "  - the typed operations `store_row` (the per-token scatter store), `load_row` (the gather load: many small loads, each from a separate address, into one row), `store_block` (the 16-token block save: transpose in registers, full cache line stores) and `copy_token`.\n",
    "  - the typed operations `store_row` (the per-token scatter store), `load_row` (the gather load: many small loads, each from a separate address, into one row), `store_block` (the 16-token block save: transpose in registers, full cache line stores) and `copy_token`.\n"
    "  - the row-major tail block operations: `row_major_row` (a token's row inside a row-major block, as a typed row view), `store_row_major`, `load_row_major`, and `block_to_vnni` / `block_to_rows` (the in-place conversion of one 16-token block, 4 KiB read and 4 KiB written), with Note [Row-major tail block].\n")
changes = sub(changes,
    "  - Note [K VNNI storage] (a named comment block in the header that documents the layout).\n",
    "  - Note [K VNNI storage] (a named comment block in the header that documents the layout) and Note [Row-major blocks under hardware attention].\n"
    "  - The K layout state per page and storage slot: the saved-row bits and the converted-block bits (one extra entry for the EAGLE storage), with `note_k_row_saved`, `note_k_block_saved`, `k_block_to_vnni` / `k_block_to_vnni_at`, `k_vnni_blocks`, `k_storage_ref` / `k_storage_of`, `k_row_if_row_major` and `k_forget_row` (a new token at a page offset drops the bits at and above it and converts the offset's block back to row-major).\n")
changes = sub(changes,
    "  - Layout-independent `set_k_row`, `get_k_row` (typed row views) and `set_k_block` serve both layouts.\n",
    "  - Layout-independent `set_k_row`, `get_k_row` (typed row views) and `set_k_block` serve both layouts. `set_k_row` and `get_k_row` follow the block's recorded layout (packed column or row-major row). `set_k_block` stores whole blocks.\n")
changes = sub(changes,
    "  - Other ranges are copied token by token with `copy_token`.\n",
    "  - Other ranges are copied token by token through row-major rows: the converted destination blocks the range touches are made row-major first, and a block whose 16 rows are saved after the copy is converted. The bits travel with the rows.\n")
changes = sub(changes,
    "  - `save_k` cuts the pass into work units. It shares the store with the main helpers. They call the same `save_k` with their worker index (the main thread is worker 0).\n",
    "  - `save_k` cuts the pass into work units. It shares the store with the main helpers. They call the same `save_k` with their worker index (the main thread is worker 0). A unit that fills a whole block takes the block save; a shorter unit is stored row by row into the row-major block.\n"
    "  - After the join, `save_k` records the saved rows of a software-scored operation. A block that is complete because of this pass is queued (`pending_k_blocks_`) and converted at the forward end (`convert_pending_k_blocks`, after the cooperative GOF staging drained). The rows of a hardware-scored operation are not recorded, so their blocks stay row-major.\n")
changes = sub(changes,
    "  - The dense AMX page reads the VNNI plane (the K storage in the VNNI layout) as its B operand (`qk_vnni_128x4`).",
    "  - The dense AMX path takes a page only when its 4 blocks are converted (`k_layout_dense`); it reads the VNNI plane (the K storage in the VNNI layout) as its B operand (`qk_vnni_128x4`).")
changes = sub(changes,
    "  - The software path scores the live tokens (the tokens present in the page) in one AVX-512 loop over the page.\n",
    "  - The software path scores the live tokens (the tokens present in the page) of the converted blocks in one AVX-512 loop over the page (`k_vnni::qk_group`), and the tokens of a row-major tail block with the row-major dotter through `row_major_row`.\n")
changes = sub(changes,
    "`k_head_fn` writes a token's K row into a scratch buffer (temporary memory) that the caller owns, through a typed destination row.",
    "`k_head_fn` returns a row of a row-major block in place (`k_row_if_row_major`) and writes the row of a converted block into a scratch buffer (temporary memory) that the caller owns, through a typed destination row.")
changes = sub(changes,
    "  - `t_k_vnni_layout` (new, registered in `t/CMakeLists.txt`). It runs on real owners: poison (a fill of the plane with a known marker pattern before each check) through 64 typed row stores, layout checks on the owner's bytes, the index anchors (hand-computed offsets of chosen token and dimension pairs, compared against the index map), an `at()` section, a `copy_token` section, and the reader check for 4, 20 and 32 query heads with bf16, float and fp16 (16-bit IEEE half float) queries.\n",
    "  - `t_k_vnni_layout` (new, registered in `t/CMakeLists.txt`). It runs on real owners: poison (a fill of the plane with a known marker pattern before each check) through 64 typed row stores, layout checks on the owner's bytes, the index anchors (hand-computed offsets of chosen token and dimension pairs, compared against the index map), an `at()` section, a `copy_token` section, the reader check for 4, 20 and 32 query heads with bf16, float and fp16 (16-bit IEEE half float) queries, the tail-block conversion (bit for bit against `store_row`, no other block touched), and the page state: the block turns VNNI at the 16th saved row and back when a row is forgotten, a row saved again, the EAGLE storage view, forgetting a row in several slots, and page appends that carry the state.\n")
changes = sub(changes,
    "  - Fakes (stand-in implementations used only by the test) in `t_amx_dispatch_dtype` that take the typed view.\n",
    "  - Fakes (stand-in implementations used only by the test) in `t_amx_dispatch_dtype` that take the typed view, and a case where a full page with unrecorded rows takes the software loop under `TRON_K_VNNI`.\n")
changes = sub(changes,
    "  - In `t_llama_unit`: a model-level shared-save case, a software-attention case for 32 query heads on one 128-dimension K/V head, layout-independent accessors, and the K typed-boundary contracts.",
    "  - In `t_llama_unit`: a model-level shared-save case (the queued block and its forward-end conversion; with a hardware-scored operation, no conversion; with another operation hardware-scored, conversion), an apply-and-join case that scores a page with converted and row-major blocks, a software-attention case for 32 query heads on one 128-dimension K/V head, layout-independent accessors, and the K typed-boundary contracts.")
changes_block = changes + "\n"

# ---------------------------------------------------------------- Measurements
ver_start = lines.index("## Verification")
meas_old = "\n".join(lines[meas_start:ver_start])
# keep the PR #3879 table and its two reading bullets verbatim
i3879 = meas_old.index("Against the PR #3879 binary (544ca05c7a), tp2 and tp4.")
pr3879_part = meas_old[i3879:].rstrip("\n")
assert pr3879_part.count("| 8192 | this branch vs base |") == 1

meas_block = """## Measurements

### Nightly CI perf configs, whole machine, this branch against `main` (2026-10-09)

Setup: the nightly's own client (systems_test at 14f0ce4, `scripts/perf.py`, 10 rounds per config) against rinzler engines provisioned by platformd 0.11 in the nightly layout (4 tp2 engines or 2 tp4 engines behind the Caddy proxy, the same 8 users spread over them). Two packages: base = the nightly package 2026.10.08-be0d5565 (`main` at be0d5565b3). This branch = 9d5c7a389b built with the `deb` preset plus `TRON_K_VNNI=ON` (the preset itself does not set it; see Open items). Four passes in the order base, this branch, this branch, base. `USE_HW_ATTN` as shipped: FPGA attention for the ingested models, CPU attention for the handwritten ones. One extra cell per pass: qwen3-4b tp2, 8 users, prompt length 8192 tokens, 1536 generated tokens, with `USE_HW_ATTN=0` (software attention on the CPU).

All configs have 8 users, prompt length 1024 and 1536 generated tokens unless the row says otherwise. The base passes are within 1.7 % of the nightly's own run of the same day (package 2026.10.09-26b6df7d) on every config.

| config | base TPS | this branch TPS | TPS difference (paired t) | base TTFT | this branch TTFT | TTFT difference | peak memory difference |
|---|---|---|---|---|---|---|---|
| llama-3.2-3b tp2, 32 users, prompt 200 plus 800 shared | 198.26 | 195.56 | -1.4 % (-16.6), resolved | 74 ms | 58 ms | -15 ms (t -1.5) | +6 MiB (+0.1 %) |
| llama-3.1-8b tp2 | 143.03 | 142.58 | -0.3 % (-1.4) | 586 ms | 585 ms | 0 ms | +5 MiB |
| llama-3.1-8b tp2, 32 users, prompt 4096 (the "AMX benchmark" row) | 32.62 | 34.20 | +4.8 % (+39.4), resolved | 11.82 s | 11.83 s | +12 ms (t +0.7) | +5 MiB |
| llama-3.3-70b tp2 | 17.01 | 17.00 | 0.0 % (-2.1) | 9.38 s | 9.39 s | +11 ms (t +1.0) | +2 MiB |
| llama-3.3-70b tp2, 4 users | 28.46 | 28.68 | +0.8 % (+13.1) | 4.09 s | 4.46 s | +371 ms (t +1.1) | +2 MiB |
| llama-3.3-70b tp4, 4 users | 31.71 | 31.67 | -0.1 % (-0.8) | 4.88 s | 4.87 s | -1 ms | 0 MiB |
| mixtral-8x7b tp2 | 80.68 | 80.62 | -0.1 % (-0.2) | 1.26 s | 1.26 s | +5 ms (t +2.2) | -16 MiB |
| qwen-2.5-32b tp2 | 36.06 | 36.02 | -0.1 % (-2.6) | 3.95 s | 3.94 s | -7 ms (t -1.1) | +6 MiB |
| qwen3-4b tp2 (FPGA attention) | 189.13 | 187.38 | -0.9 % (-2.2) | 502 ms | 494 ms | -8 ms (t -1.0) | 0 MiB |
| qwen3-4b tp4 (FPGA attention) | 181.01 | 180.30 | -0.4 % (-0.4) | 557 ms | 545 ms | -12 ms (t -0.8) | -8 MiB |
| gemma-2-9b tp2 | 104.03 | 104.84 | +0.8 % (+1.0) | 856 ms | 852 ms | -5 ms (t -1.7) | -81 MiB (-0.3 %) |
| gpt-oss-120b tp4 | 122.38 | 121.83 | -0.5 % (-1.3) | 966 ms | 944 ms | -22 ms (t -1.9) | +2 MiB |
| gemma-4-31b tp2 | 38.21 | 38.23 | +0.1 % (+0.7) | 5.46 s | 5.45 s | -8 ms (t -1.6) | +17 MiB |
| Muse-Glimmer-30B tp4 | 74.72 | 76.53 | +2.4 % (+24.4), resolved | 3.72 s | 3.60 s | -118 ms (-3.2 %, t -25.9), resolved | +8 MiB |
| extra cell: qwen3-4b tp2, prompt 8192, software attention | 59.84 | 64.41 | +7.6 % (+39.3), resolved | 12.96 s | 12.81 s | -150 ms (-1.2 %, t -9.0), resolved | +24 MiB (+0.1 %) |

Reading:

- The AMX kernel's share of a decode step grows with the users per engine and the prompt length. The two configs where the CPU scores long attention ranges gain: llama-3.1-8b at 32 users and prompt 4096 (8 users per engine) +4.8 % TPS, and qwen3-4b with software attention at prompt 8192 +7.6 % TPS and -150 ms TTFT. At 2 users per engine and prompt 1024 (llama-3.1-8b, 8 users) nothing changes.
- The two qwen3-4b configs with FPGA attention are inside the noise (-0.9 % and -0.4 %, not resolved). They are the configs of issue #4500. The blocks of a hardware-scored operation stay row-major.
- llama-3.2-3b loses 1.4 % TPS (resolved, both pass pairs). Its 128-dimension heads have kv_mul 3, so the VNNI layout is on but the AMX kernel is not eligible, and the AVX-512 reader scores its pages instead of the row-major dotter (see the kv_mul open item).
- Muse-Glimmer-30B tp4 gains 2.4 % TPS and 118 ms TTFT (resolved). The attention shape of that model was not examined here.
- Every other config is within 0.8 % (not resolved). mixtral shows no change.
- Memory: the peak resident memory of the engines differs by at most 81 MiB (0.3 %) on any config. The K cache occupies the same bytes in both layouts.

### runtron cells against `main` at this head (running)

Question: the decode TPS and TTFT of this head against `main` at 8 users on one engine with software attention, the cells of the PR #3879 table below.

Comparator: `main` at be0d5565b3 built as runtron without `TRON_K_VNNI` (row-major K, AMX dispatch on). This branch at 9d5c7a389b.

Cells: qwen3-4b tp2, 8 users, 256 generated tokens, CPU attention, prompt 1024 and prompt 8192, 3 repetitions, binaries interleaved, our half of delphi-3bda.

Verdict rule: band = the larger of 2 x the largest standard deviation of the two binaries and a floor of 0.4 TPS or 0.15 s. A difference beyond the band counts as a change.

Status: scheduled on delphi-3bda after the 2026-10-10 nightly.

| cell | base TPS / TTFT | this branch TPS / TTFT | band | result |
|---|---|---|---|---|
| prompt 1024 | | | | pending |
| prompt 8192 | | | | pending |

### Against the PR #3879 binary (runtron, our half of delphi-3bda, qwen3-4b, 8 users, software attention with AMX)

""" + pr3879_part + "\n"

# ---------------------------------------------------------------- Verification
open_start = lines.index("## Open items")
ver_old = "\n".join(lines[ver_start:open_start])
itol = ver_old.index("One `main` test, `t_llama_unit`")
tol_sentence = ver_old[itol:ver_old.index("\n", itol)]
icost = ver_old.index("Cost rows (`config/test-benchmarks.json`")
cost_sentence = ver_old[icost:ver_old.index("\n", icost)]

ver_block = """## Verification

The delphi-3bda runs below are from 2026-10-08 and 2026-10-09 at 9d5c7a389b.

Setup: `nix develop` (the project's pinned build shell), clang 19, preset `native` (explicit AVX-512 flags), `TRON_AMX_DISPATCH=ON`, `BUILD_INGEST_MODELS=ON` (the CMake option that builds the generated model plugins).

Unit tests, VNNI build (`TRON_K_VNNI=ON`), real AMX, our half of the machine:

| test | result (assertions / test cases) |
|---|---|
| `t_k_vnni_layout` | pass, 1041256 / 10 |
| `t_amx_dispatch_dtype` | pass, 2137 / 1 |
| `t_amx_numerics` | pass, 4621 / 5 (the AMX cases ran: no "AMX unavailable" line) |
| `t_llama_unit` | pass, 259020 / 64 |
| `t_heterogeneous_scheduler` | pass, 2783 / 3 |
| `t_phase1_integration` | pass, 2124 / 64 |
| `t_amx_numerics` with the kill switch (`TRON_AMX_DISABLE=1`) | pass, 2060 / 5, the three AMX cases report "AMX unavailable" |
| Haskell code-generator suite (`bin/ingest-cabal test`) | pass |

The generated plugins carry no `save_k_helper` call (grep over the generated sources). clang-format 19.1.7 and `git diff --check` pass on the changed files.

Row-major build (`TRON_K_VNNI=OFF`), all pass (assertions / test cases):
- `t_k_vnni_layout` 1039202 / 10
- `t_amx_dispatch_dtype` 2137 / 1
- `t_amx_numerics` 4621 / 5
- `t_llama_unit` 258911 / 64
- `t_heterogeneous_scheduler` 2783 / 3

""" + tol_sentence + "\n\n" + cost_sentence + """ The test binaries grew with the row-major tail block cases since that measurement (see Open items).

### Host test suite and token identity at this head (running)

Question: does the whole host test suite pass at this head, and does this binary reproduce its own tokens.

Comparator: `main` at be0d5565b3 built as runtron without `TRON_K_VNNI` (row-major K, AMX dispatch on). The previous head of this branch (45e6bb266d, before the row-major tail block) as a second reference.

Cells: `make build-test-host` and `make test-host` (fake device, our half) at 9d5c7a389b. Token identity with runtron: qwen3-4b tp2, 1 user, temperature 0, pay-for-determinism (the runtron flag that selects deterministic reductions), seed 1, 256 generated tokens; CPU attention at prompt 1024 (this branch, its A/A repeat, its kill-switch run, `main`, the previous head), FPGA attention at prompt 1024 and CPU attention at prompt 8192 (this branch, `main`, the previous head).

Verdict rule: the host suite passes with the same pass and skip set as `main` on this machine (`t_proxy_lib` skipped and `t_proxy_llama31` failing for the Python venv the machine lacks). Token identity: this branch equals its A/A repeat and its kill-switch run for 256 tokens. The runs against `main` and the previous head are informational: `main` is expected to differ from generated token 52 (issue #4444), and the previous head scores the row-major tail block with the VNNI reader where this head uses the dotter.

Status: scheduled on delphi-3bda after the 2026-10-10 nightly.

| check | result |
|---|---|
| host test suite | pending |
| this branch vs its A/A repeat (CPU, prompt 1024) | pending |
| this branch, AMX on vs kill switch (CPU, prompt 1024) | pending |
| this branch vs `main` (CPU 1024, FPGA 1024, CPU 8192) | pending |
| this branch vs the previous head (CPU 1024, FPGA 1024, CPU 8192) | pending |
"""

# ---------------------------------------------------------------- Open items
open_old = "\n".join(lines[open_start:])
items = [l for l in lines[open_start + 1:] if l.startswith("- **")]
def item(prefix):
    m = [l for l in items if l.startswith("- **" + prefix)]
    assert len(m) == 1, (prefix, len(m))
    return m[0]
it_genoa = item("genoa96")
it_kvmul = item("128-dimension heads with kv_mul")
it_bench = item("Benchmark binary mismatch")
it_kill = item("Kill switch and token divergence")
it_tol = item("A `main` test tolerance")
# kv_mul item: add the llama-3.2-3b measurement; drop the 'need a repeat at this head' sentence
it_kvmul = sub(it_kvmul, " The cells need a repeat at this head.", "")
it_kvmul = sub(it_kvmul,
    " If the prompt 2048 loss repeats, the layout gate",
    " In the nightly configs of 2026-10-09 (Measurements) llama-3.2-3b (kv_mul 3) loses 1.4 % TPS at 32 users, resolved in both pass pairs. So the layout gate")
it_kill = sub(it_kill,
    " Under FPGA attention the software path still scores the pages the FPGA does not process.",
    " Under FPGA attention the software path still scores the pages the FPGA does not process. The tokens of a row-major tail block are scored by the row-major dotter in both the AMX-on and the kill-switch run of this binary, so those two runs stay identical.")
it_preset = ("- **The `deb` preset does not compile the layout.** The `deb` configure preset (the package the nightly installs and "
             "the release builds use) sets `TRON_AMX_DISPATCH=ON` and not `TRON_K_VNNI=ON`. With this PR as it is, the production "
             "package keeps row-major K, and none of the nightly-config results above reaches production. The package of those "
             "measurements adds the line locally. Decision: add `\"TRON_K_VNNI\": \"ON\"` to the `deb` preset in this PR (as PR #4505 "
             "did for the kernels), or leave it off and switch the layout on later.")
it_cost = ("- **Cost rows refresh.** The granite_rapids_6962p rows of `config/test-benchmarks.json` for `t_llama_unit`, "
           "`t_k_vnni_layout` and `t_amx_numerics` were measured at 6b939d25d2 (2026-10-08). The tail-block cases added since "
           "make `t_k_vnni_layout` and `t_llama_unit` longer. A `bin/slice bench --update` of the three tests on the whole "
           "machine refreshes the rows.")
open_block = "## Open items\n\n" + "\n".join([it_genoa, it_kvmul, it_bench, it_kill, it_tol, it_preset, it_cost]) + "\n\n🤖 Generated with [Claude Code](https://claude.com/claude-code)"

rest = words_block + "\n" + changes_block + "\n" + meas_block + "\n" + ver_block + "\n" + open_block
rest = re.sub(r"\n{3,}", "\n\n", rest)
new_body = protected + rest
assert "Stacked PR" not in new_body and "37064d72b2" not in new_body and "k_vnni_plane" not in new_body
assert new_body.startswith(protected), "protected prefix changed"
open(S + "new-body.md", "w").write(new_body)
old_lines = live.split("\n"); nl = new_body.split("\n")
d = list(difflib.unified_diff(old_lines, nl, lineterm="", n=0))
print(len(old_lines), "->", len(nl), "lines;", sum(1 for l in d if l.startswith("-") and not l.startswith("---")), "removed,",
      sum(1 for l in d if l.startswith("+") and not l.startswith("+++")), "added")
for l in d:
    if l.startswith("-") and not l.startswith("---"):
        print("REMOVED:", l[1:90])
