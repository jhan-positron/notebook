# pr4956-diagrams-20261015

The three "diagramming-code-changes" pages of tron PR 4956 ("Add the VNNI K layout and its
readers", branch jhan-vnnik-1-layout, head a5697f86d3, merge base 76bb0bf3f4), built 2026-10-15
from the prompt ~/workspace/notebook/artifacts/ai-prompts/diagramming-code-changes.md.

Toolchain copied from exec/pr4424-diagrams-20261009 (the PR 4424 set) and adapted: constants in
difflib_units.py / check_page.py / spec_builder.py / page_common.py point at PR 4956; STYLE.md lists
what PR 4956 contains and what it does not.

Target files (the three most important of the 23 changed files, by added lines among the
non-test files) and their pages in PR3879/new-PRs/split-4424/:
- h/tron/tensor/k_vnni.hpp   -> diagramming-code-changes-PR4956-tensor-k_vnni.hpp.html  (key k_vnni)
- h/tron/models/kv_cache.hpp -> diagramming-code-changes-PR4956-kv_cache.hpp.html       (key kv_cache)
- h/tron/kernels/k_vnni.hpp  -> diagramming-code-changes-PR4956-kernels-k_vnni.hpp.html (key kernels)

Rebuild: python3 spec_builder.py <key>; check: python3 check_page.py <page>, python3 check_legend.py <page>.
Figures: figs/base_<key>*.py (base diagrams), figs/d_<key>_<unit>.py (one per code change).
Specs: units_<key>.json. PNG renders: png/.
