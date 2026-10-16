---
name: pr4958-pr4959-diagram-pages
description: "2026-10-16 the diagramming-code-changes pages of PR 4958 (model.hpp, tensor/k_vnni.hpp, common.hpp) and PR 4959 (kv_cache.hpp, tensor/k_vnni.hpp, model.hpp), built from the notebook prompt with the PR 4956 toolchain copied to exec/pr4958-diagrams-20261016 and exec/pr4959-diagrams-20261016; where they are, how to rebuild, the file-choice reason"
metadata:
  node_type: memory
  type: project
  originSessionId: 6e1ee77b-f9bd-4187-97dd-77321eb2f890
  modified: 2026-10-16T15:35:43.846Z
---

jhan asked (2026-10-16) to execute ~/workspace/notebook/artifacts/ai-prompts/diagramming-code-changes.md on
PR 4958 (branch jhan-vnnik-3-shared-save, head b39765ec29, base = PR 4957 head 26b86a279a, worktree
~/workspace/ai-runs/tron-split-pr3) and PR 4959 (jhan-vnnik-4-tail-block, head 6b081187e1, base = PR 4958 head
b39765ec29, worktree tron-split-pr4), individually (one page set per PR).

Target files. PR 4958: model.hpp (+298/-29), tensor/k_vnni.hpp (+89/-8), common.hpp (+29: k_store_window_t) chosen
over kv_cache.hpp (+42: a Note rewrite and the set_k_block wrapper) because it defines the window data model. PR 4959:
kv_cache.hpp (+474/-50), tensor/k_vnni.hpp (+116/-5), model.hpp (+76/-12), by lines and by mechanism.

Pages in split-4424/: diagramming-code-changes-PR4958-{model.hpp, tensor-k_vnni.hpp, common.hpp}.html and
diagramming-code-changes-PR4959-{kv_cache.hpp, tensor-k_vnni.hpp, model.hpp}.html.

Record and rebuild: exec/pr4958-diagrams-20261016 and exec/pr4959-diagrams-20261016 (README.md, STYLE.md = what the
PR contains / does NOT, the worked example (PR 4958: 3 workers, 41 items, units [0,16) [16,32) [32,41), present
0x01ff for unit 2, token 37 / dim 70 at index 5226; PR 4959: page 7 slot 5 after offset 45, bits 0..45, blocks
0b0011, token 37 row-major at element 3270, VNNI at 5226, the step-47 transition); spec_builder.py <key>;
check_page.py, check_legend.py on the built page; render_one.py -> png/; facts/<basename>.runs.txt). The PR 4958
svg_helpers catalogue adds the key "present" (green, the present mask lanes); the PR 4959 pages draw the live
mask on the query side (q violet) so that green stays k_rows_saved_.

Result (2026-10-16, six forks, one per key, all done): every page passes check_page.py and check_legend.py with 0
problems, is pure ASCII, carries the prompt verbatim and links to its two sibling pages. Figures: 4958 model 14 SVGs
(8 units), tensor 10 (4 units), common 7 (1 unit); 4959 kv_cache 23 (10 units), tensor 11 (5 units), model 9 (4
units). I spot-checked 6 PNGs (model-b3, model-d4b, k_vnni-d2 of 4958; kv_cache-b4, kv_cache-d7, k_vnni-b1 of 4959):
clean. Known caveats on the pages: the claim order in the worked example is one possible order (said on the figure);
wall-clock lanes are schematic, the only numbers are the Note's 0.86 ms / 105 ns and the PR bodies' 80 us and
3.7-4.2 us per block, each with its source; check_page.py's FILES map lacks llama.hpp (a register entry was moved
behind a t_llama_unit.cpp range instead). Not shown to jhan as of writing.

**How to apply:** to change a page, edit figs/*.py or units_<key>.json in the record dir and rebuild; do not
hand-edit the HTML. See [[pr4956-diagram-pages]] (the same toolchain for PR 4956), [[stack-reopened-20261015]].
