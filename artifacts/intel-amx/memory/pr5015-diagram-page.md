---
name: pr5015-diagram-page
description: "DONE 2026-10-18 diagramming-code-changes-PR5015-amx_attn.cpp.html (muse-glimmer/) for PR 5015 head 5061623a34 vs base 6198824246; generator exec/pr5015-diagrams-20261018/ (copy of the PR 4424 toolchain, one key amx_attn); units A1-A5 + T1; base diagrams B1 data / B2 function / B3 sequencing / B4 transpose; transpose_sim.py proves the lane/selector mapping; worked example head 9 token 37"
metadata:
  node_type: memory
  type: project
  originSessionId: ff60e929-f850-4014-9494-90108583a1a0
  modified: 2026-10-18T19:46:20.359Z
---

jhan's request (2026-10-18): "Act per ~/workspace/notebook/artifacts/ai-prompts/diagramming-code-changes.md on PR5015,
amx_attn.cpp" (the prompt file = the PR 4424 prompt plus the per-section scheme and the
"diagramming-code-changes-PR123-file1.html" naming; one given file, so one page).

Generator ~/workspace/intel-AMX/exec/pr5015-diagrams-20261018/: copied svg_helpers / difflib_units / page_common /
spec_builder / check_page / check_legend / render_one / render_check from exec/pr4424-diagrams-20261009 and
re-pointed them (WT ai-runs/tron-glimmer-amx, BASE 6198824246, HEAD 5061623a34, OUT_DIR muse-glimmer/, PR 5015
prompt literal, LEGEND catalogue relabelled for this page's concepts). STYLE.md = the binding rules + worked example.
units_amx_attn.json: A1 pack_q_group_128x4 template (130-146), A2 store_transposed_rows<lane> new (148-185),
A3 qk_rowmajor_128x4 template + lanes 1..3 under if constexpr (187-196, 227-261), A4 weights_times_v_128x4 template +
thread_local P per specialization (264-293), A5 explicit instantiations (330-354); T1 file-top comment (34-38).
Colours: q violet (q_group / packed Q), rm orange (K page), vnni blue (V plane), rows green (s_transposed / s /
exp_rows / P), blk purple (o), unit grey-blue (tile registers), pend vermillion (128-bit lanes, selectors),
eagle sky blue (16-heads-only parts), hw yellow (group_heads_ok / GROUP_HEADS_x / requires / instantiations),
empty grey dashed (zero padding), hi (head 9 token 37), gone red dashed (base code).
transpose_sim.py: executes unpacklo/hi_ps, unpacklo/hi_pd, shuffle_f32x4 semantics on a labelled 16x16 tile;
verified lane L of u[row_group][k] = column 4L+k; selectors per lane 0..3 = (88,88) (dd,88) (88,dd) (dd,dd);
head 9 / token 37 -> tile r 2, row_group 1, u[1][1] lane 2 position 1 -> store_transposed_rows<2> k 1 -> s[9][37].
Traps this time: a float viewBox height (715.0) makes render_one/check_page's regex fail silently (20x14 px PNG)
-> int(H); check_page needs an identifier token of the box label inside the cited lines +-3 (cite the line that
holds the name, e.g. the parameter line for exp_rows, not the prose comment); fn_cell strokes must be the
concept colour or the legend catalogue entry does not match.

DONE 2026-10-18 ~20:00 UTC: page 1.73 MB, 10 SVGs (B1-B4, d1, d2, d3, d4 + d4a, d5), check_page 0 problems,
check_legend 0 problems, every PNG inspected. Change figures drawn by 5 parallel general-purpose agents (fig-a1..a5)
from one brief each (STYLE.md + unit facts + the base module's building blocks); each ran render_one, check_legend,
the ASCII check and check_page's rule 5 on its own output before reporting. A5 found the gate tests:
t_amx_numerics.cpp:113-122 (STATIC_REQUIRE eligible for 4 and 16, REQUIRE_FALSE for KV_MUL_8 and head 64),
t_amx_dispatch_dtype.cpp:255-276, 301. Not published as an artifact (the prompt asks for a file).

**Why:** jhan wants every logical change explained visually with one colour scheme and verifiable citations; the
generator keeps the code excerpts exact and makes a re-render after a PR update cheap.
**How to apply:** rerun `python3 spec_builder.py amx_attn` after editing a figure module or units_amx_attn.json,
then `python3 check_page.py <page>`, `python3 check_legend.py <page>`, `python3 render_check.py <page> png/page`
and LOOK at the PNGs. Related: [[pr4424-diagram-pages]], [[glimmer-kvmul16-implementation]], [[svg-render-check]],
[[plain-english-default]].


Former index hook (moved from MEMORY.md on 2026-10-21 to keep the index under its size limit): DONE 2026-10-18 muse-glimmer/diagramming-code-changes-PR5015-amx_attn.cpp.html; generator exec/pr5015-diagrams-20261018/ (PR 4424 toolchain re-pointed); transpose_sim.py; int viewBox trap
