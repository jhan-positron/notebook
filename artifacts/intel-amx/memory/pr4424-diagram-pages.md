---
name: pr4424-diagram-pages
description: "DONE 2026-10-09: three diagramming-code-changes-<file>.hpp.html pages for PR 4424 (kv_cache.hpp, tensor/k_vnni.hpp, model.hpp) at head 9d5c7a389b vs main be0d5565b3, output in PR3879/new-PRs/merge-4737-2-4424/; generator exec/pr4424-diagrams-20261009/ (svg_helpers + difflib_units + page_common + spec_builder + check_page + figs/); verified facts in facts/<key>.json (554 claims, 0 refuted); unit partition in units_<key>.json; conventions + traps inside"
metadata:
  node_type: memory
  type: project
  originSessionId: daed4d8b-e695-45e4-a9c9-1635c10014f7
  modified: 2026-10-09T17:02:31.779Z
---

jhan's request (2026-10-09, ultracode, cwd PR3879/new-PRs/merge-4737-2-4424): the PR 4737 diagram-page prompt
again, now for PR 4424 and with four new rules: no invented shorthand + cite the comment/line that defines each
box; every function cell carries a one-line description; every arrow between data-model boxes says how many;
pick the 3 most important files, one page each (diagramming-code-changes-<file>.html).

Files picked (by changed lines and role): h/tron/models/kv_cache.hpp (749), h/tron/tensor/k_vnni.hpp (526, new),
h/tron/models/model.hpp (379); runner-up self_attention.hpp (153) not drawn. Pages:
PR3879/new-PRs/merge-4737-2-4424/diagramming-code-changes-{kv_cache,k_vnni,model}.hpp.html.

Generator ~/workspace/intel-AMX/exec/pr4424-diagrams-20261009/: STYLE.md (binding drawing rules, worked examples:
page 7 slot 5 offsets 0..40; token 37 dim 70; 40-item window with 3 workers), svg_helpers.py (Okabe-Ito tokens C,
cite(), fn_cell(), card_arrow(), figure(boxes=[...]) prints "Boxes and their sources"), difflib_units.py
(DiffFile(file); coverage() ignores blank added lines), page_common.py (CSS + skeleton + PROMPT literal),
spec_builder.py <key> (builds a page from units_<key>.json + figs/base_<key>.py + figs/d_<key>_<unit>.py whose
BASE string = "Updates B<n>: ..."), render_one.py (one module -> png/), render_check.py (whole page -> png dir),
check_page.py (ASCII, unique ids, markers, unit has svg, caption + box register, box cite resolves to a head line
containing the label, anchors, text width est.). units_draft.json = my first partition; units_<key>.json = the
corrected one (6 must-fix range cuts in kv_cache found by the facts workflow).

Facts workflow wf_3b54a6c7-ec4 (51 agents): 4 lenses x 3 files -> 2 refuters each -> judge; facts/<key>.json =
191/183/180 claims (data_box, cardinality, function, sequence_step, thread_rule, unit_issue, glossary), 0 refuted.
Drawing workflow wf_da468e5c-c77 launched ~2026-10-09 (base agent -> per-unit agents -> builder -> 3 reviewers ->
fixer -> round 2 + completeness critic -> final build), per file in a pipeline.

**Why:** jhan wants code changes explained visually with one colour scheme and verifiable labels; the generator
keeps code excerpts exact and makes re-rendering after a PR update cheap.
**How to apply:** rerun `python3 spec_builder.py <key>` after editing a figure module or units_<key>.json, then
`python3 check_page.py <page>` and `python3 render_check.py <page> png/page_<key>` and LOOK at the PNGs. Traps from
the PR 4737 page still apply ([[pr4737-kvcache-diagram-page]], [[svg-render-check]]). Related:
[[merge-4737-into-4424]], [[vnni-k-terminology]], [[plain-english-default]].

DONE 2026-10-09 (~22:xx UTC): pages built, check_page 0 problems each (kv_cache 26 svgs / 11 units + 3 trivial;
k_vnni 23 svgs / 10 units + 1 trivial; model 15 svgs / 8 units + 2 trivial), all 64 figures inspected by me after
the two review rounds. Drawing workflow wf_da468e5c-c77 (62 agents, 2.5 h): per file base agent -> unit agents ->
builder -> 3 reviewers (visual / requirements / facts+English) -> fixer -> round 2 + completeness critic -> final
build; 243 + 147 findings applied. Fixes I made in the shared files afterwards: C['unit'] grey-blue #4C6A8F
(was the k_rows_saved_ green), C['new'] = ink (bold word, not a colour), C['hi_fill'] worked-example cell,
C['crit'] thick solid red = critical path (removed = red dashed), figure() escapes captions, legend chips, header
"N hunks at zero context (M with -U3)", blank added lines tolerated by coverage; check_page: any identifier token
of a label, continuation ranges "f.hpp:12-20, 30-31", "base f.hpp:N" against be0d5565b3, "#anchor" sources, more
FILES. State name unified on all pages: "complete, may wait" (kv_cache.hpp:684-685). Not drawn:
self_attention.hpp (runner-up, 153 lines). The model B4 lanes say the new split's duration is unmeasured
(Insufficient data); the 0.86 ms/layer figure is the comment's 2026-09-14 measurement.

SECOND REQUEST 2026-10-09 (jhan): (1) repeat "Colour and font scheme" at each section/diagram with only the
styles used there, including figure-specific styles such as the white "token block c" box; (2) a hierarchy
travel diagram (K page -> plane -> panel -> pairs, with dimension step and token block marked) as a new
sub-section B1a of the k_vnni page, nothing deleted; (3) both requests appended to the verbatim prompt (the
hierarchy line is MY wording, flagged to jhan). DONE: svg_helpers.LEGEND catalogue + figure(legend=[...]) renders
a chips row under every SVG (data-style keys); check_legend.py (page or module mode, --show) compares the
declaration with the SVG's rect/arrow/text styles: MISSING/UNUSED; forms: key, (key, label), (label, fill,
stroke, dashed, thick[, opacity]), (label, "arrow"|"text"|"line", colour), ("label", "multi", [...]);
page_common.code_legend() emits a section scheme for the code excerpts of sections 2 and 3 (row kinds really
present) + XREF/METHOD legends. Workflow wf_e8254699-076 (44 agents) declared legends for 32 modules, reviewed
and fixed them (kv_cache 42 findings applied). B1a = figs/base_k_vnni_b1a.py (own module; spec_builder resolves
base_<key>_<name>), 5 levels + index-formula travel + row-major-form note; worked example token 37 / dim 70.
Final: check_page + check_legend 0 problems on all three pages (26 / 24 / 15 figures).
