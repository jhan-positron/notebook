---
name: pr4737-kvcache-diagram-page
description: "2026-10-01 page VNNIed-K-in-place/issue4500/diagramming-code-changes.html = every logical change PR 4737 makes to kv_cache.hpp (base 30c4ac82cb -> head bb32a80774) beside a diagram; generator exec/pr4737-diagrams-20261001/ (gen_page.py + difflib_units.py + diagrams_*.py + render_check.py); unit ids C0-C8/T1, base diagrams B1-B5, per-change D0-D8; conventions and SVG traps"
metadata:
  node_type: memory
  type: project
  originSessionId: adff9d22-41d8-4f8d-8cda-a9cdd5330731
  modified: 2026-10-02T05:23:39.687Z
---

jhan's request (2026-10-01): "generate diagramming-code-changes.html" for PR 4737, target file
kv_cache.hpp, prompt literal at the top, TOC, base diagrams first (data / function / sequencing /
interaction models), one diagram per logical code change side by side with the code (comments kept
with the code), trivial changes listed, consistent colours per concept.
What exists: the page (374 KB, pure ASCII, light theme, 14 inline SVGs) and its generator folder
~/workspace/intel-AMX/exec/pr4737-diagrams-20261001/: difflib_units.py parses `git diff -U3` of the
file in worktree VNNIed-K-in-place/tron-i4500 and renders a unit = list of HEAD line ranges with
head/base line numbers (deletions anchored at the next new line; parser totals 484/55 = --stat 539);
blame_commits() gives the last commit per added line; diagrams_base.py B1-B4, diagrams_base_b5.py B5,
diagrams_changes.py D0-D8, svg_helpers.py (Okabe-Ito tokens: row-major orange E69F00, VNNI blue
0072B2, complete-waits vermillion D55E00 dashed, k_rows_saved_ green 009E73, k_vnni_blocks_ purple
CC79A7, hardware attention yellow, EAGLE sky blue); render_check.py renders each <svg id> to PNG.
Units: C0 note (653-808), C1 state (members/constants/k_block_bits/k_block_is_vnni/k_vnni_blocks/move
ctor), C2 k_state_ix/eagle_view_active/k_storage_ref/k_storage_of/k_with_storage_geometry, C3
note_k_row_saved/note_k_block_saved, C4 k_block_to_vnni(_at), C5 set_k_row/get_k_row/
k_row_if_row_major, C6 set_k_block (present dropped), C7 clear_kv_complete_at/k_storage_readable/
k_forget_row, C8 copy_storage_slot/copy_from; T1 k_vnni_plane comment. Worked example everywhere:
page 7, slot 5, offsets 0..40 saved (block 0 VNNI, 1 complete-waits, 2 partial, 3 empty).
**Why:** jhan wants code changes explained visually with one colour scheme; the generator keeps the
code excerpts exact (no hand transcription) and makes a re-render after a PR update cheap.
**How to apply:** rerun `python3 gen_page.py` after changing BASE/HEAD or unit ranges in gen_page.py,
then `python3 render_check.py <html> <pngdir>` and LOOK at every PNG (traps found this time: a white
dashed "idle" box drawn after text hides the text -> draw idle boxes first; labels centred on a
vertical arrow x collide -> offset them; inside <pre>, display:block rows must have no newline between
them or every row gets an empty line; 140 px lane-label gutter needs 2-line labels). Not published
as an artifact (jhan asked for the file). Related: [[pr4737-review-response]],
[[issue-4500-fix-implementation]], [[i4500b-policy-campaign]], [[svg-render-check]],
[[plain-english-default]].
