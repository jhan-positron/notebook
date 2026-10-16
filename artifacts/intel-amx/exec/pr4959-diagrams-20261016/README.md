# pr4959-diagrams-20261016

The three "diagramming-code-changes" pages of tron PR 4959 ("Keep short K writes row-major; enable
VNNI K in the deb preset", branch jhan-vnnik-4-tail-block, head 6b081187e1, base b39765ec29 = the
head of PR 4958), built 2026-10-16 from the prompt
~/workspace/notebook/artifacts/ai-prompts/diagramming-code-changes.md.

Toolchain copied from exec/pr4956-diagrams-20261015 (the PR 4956 set) and adapted: constants in
difflib_units.py / check_page.py / spec_builder.py / page_common.py point at PR 4959; STYLE.md lists
what PR 4959 contains and what it does not, and the worked example.

Target files (the three largest non-test changes of the 14 changed files, which are also the three
that carry the mechanism) and their pages in PR3879/new-PRs/split-4424/:
- h/tron/models/kv_cache.hpp -> diagramming-code-changes-PR4959-kv_cache.hpp.html       (key kv_cache)
- h/tron/tensor/k_vnni.hpp   -> diagramming-code-changes-PR4959-tensor-k_vnni.hpp.html  (key k_vnni)
- h/tron/models/model.hpp    -> diagramming-code-changes-PR4959-model.hpp.html          (key model)

Rebuild: python3 spec_builder.py <key>; check: python3 check_page.py <page>, python3 check_legend.py <page>.
Figures: figs/base_<key>*.py (base diagrams), figs/d_<key>_<unit>.py (one per code change).
Specs: units_<key>.json. PNG renders: png/. Diff runs: facts/<basename>.runs.txt.
