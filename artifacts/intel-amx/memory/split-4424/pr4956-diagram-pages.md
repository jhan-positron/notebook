---
name: pr4956-diagram-pages
description: "2026-10-15 the three \"diagramming-code-changes\" pages of PR 4956 (PR-1 of the split), built from the notebook prompt with the PR 4424 toolchain copied to exec/pr4956-diagrams-20261015; where they are, how to rebuild"
metadata:
  node_type: memory
  type: project
  originSessionId: a48fe469-84d7-4bc1-86bc-64ec51f6b6be
  modified: 2026-10-16T00:17:27.047Z
---

jhan asked (2026-10-15) to execute ~/workspace/notebook/artifacts/ai-prompts/diagramming-code-changes.md on PR 4956
(= #4868 re-opened, branch jhan-vnnik-1-layout, head a5697f86d3, merge base 76bb0bf3f4).

Target files (top 3 non-test files by added lines): h/tron/tensor/k_vnni.hpp (299 new), h/tron/models/kv_cache.hpp
(+220/-38), h/tron/kernels/k_vnni.hpp (99 new). Pages in split-4424/: diagramming-code-changes-PR4956-tensor-k_vnni.hpp.html,
-PR4956-kv_cache.hpp.html, -PR4956-kernels-k_vnni.hpp.html.

Record and rebuild: /home/jhan/workspace/intel-AMX/exec/pr4956-diagrams-20261015 (README.md, STYLE.md = what PR 4956
contains / does NOT contain, the worked example; spec_builder.py <key> with keys k_vnni / kv_cache / kernels;
check_page.py and check_legend.py on the built page; render_one.py -> png/). The toolchain is the PR 4424 one
(exec/pr4424-diagrams-20261009) with constants repointed; figures are Python modules in figs/.

Built by three forks (one per key) 2026-10-15 ~17:45 UTC. Final checks on all three pages: check_page.py 0 problems,
check_legend.py 0 problems, pure ASCII, prompt verbatim, cross-page links resolve. Figures: tensor 16 SVGs (B1-B5 + B1A,
K0-K6 + T1), kv_cache 13 SVGs (B1-B5, C0-C6 + T1/T2), kernels 11 SVGs (B1-B5, Q0-Q4 + T1). Spot-checked PNGs myself
(k_vnni-b3, k_vnni-d6a, kv_cache-b1, kv_cache-d5, kernels-b3, kernels-d3a): clean. Not shown to jhan yet as of writing.

**How to apply:** to change a page, edit figs/*.py or units_<key>.json in the record dir and rebuild; do not hand-edit the
HTML. See [[pr-walkthrough-diagram-pages]] (the per-PR walk-through pages, a different set), [[stack-reopened-20261015]].
