# pr4958-diagrams-20261016

The three "diagramming-code-changes" pages of tron PR 4958 ("Save K in 16-token blocks, shared
with idle worker threads", branch jhan-vnnik-3-shared-save, head b39765ec29, base 26b86a279a =
the head of PR 4957), built 2026-10-16 from the prompt
~/workspace/notebook/artifacts/ai-prompts/diagramming-code-changes.md.

Toolchain copied from exec/pr4956-diagrams-20261015 (the PR 4956 set) and adapted: constants in
difflib_units.py / check_page.py / spec_builder.py / page_common.py point at PR 4958; STYLE.md lists
what PR 4958 contains and what it does not, and the worked example.

Target files (the three most important of the 9 changed files; model.hpp and tensor/k_vnni.hpp are
the two largest non-test changes; common.hpp (29 lines) was chosen over kv_cache.hpp (42 lines)
because it defines the window data model k_store_window_t that the whole protocol runs on, while
the kv_cache.hpp change is a comment rewrite and the one-call wrapper set_k_block) and their pages
in PR3879/new-PRs/split-4424/:
- h/tron/models/model.hpp   -> diagramming-code-changes-PR4958-model.hpp.html          (key model)
- h/tron/tensor/k_vnni.hpp  -> diagramming-code-changes-PR4958-tensor-k_vnni.hpp.html  (key k_vnni)
- h/tron/models/common.hpp  -> diagramming-code-changes-PR4958-common.hpp.html         (key common)

Rebuild: python3 spec_builder.py <key>; check: python3 check_page.py <page>, python3 check_legend.py <page>.
Figures: figs/base_<key>*.py (base diagrams), figs/d_<key>_<unit>.py (one per code change).
Specs: units_<key>.json. PNG renders: png/. Diff runs: facts/<basename>.runs.txt.
