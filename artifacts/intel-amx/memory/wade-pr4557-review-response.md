---
name: wade-pr4557-review-response
description: "2026-10-05 Wade's review 5420005787 of PR 4557 at 96a6220ab6 (7 inline + 4 summary items); page issue4525/status/PR4557-respond-Wade-comments.html (generator exec/wade-20261005/gen_wade.py) with 9 replies <100 words each; jhan answered memory.hpp thread + summary items 1-2 himself; nothing applied or posted"
metadata:
  type: project
---

Wade (Wado-posi) reviewed PR #4557 on 2026-10-05 20:18 UTC after the merge of main (96a6220ab6). jhan: "generate your
responses to PR4557-respond-Wade-comments.html ... I closed 1 comment (memory.hpp 4188336279, resolved) ... I commented
to couple of his points at the leading comment (constant names, unrelated changes; comment 6008399647) ... respond to the
rest. Each response is less than 100 words." Page written 20:08 UTC, plain-English checked (no Words-used-here section by
jhan's instruction; terms defined inline at first use).

Open points and the proposed position (all hold, W4 partly):
- W1 4188336250 t_llama_unit:3575: drop the NaN->+inf row + 3 rounding-sensitive rows (0x3f80ffff, tie 0xbf818000, fp16 65504),
  rename the two sections; keep exact rows + partner-zero + bf16 round trip. NaN->inf is main's shift-by-16 store (follow-up issue).
- W2 4188336256 t_amx_numerics:227: independent-formula byte comparison sits after the available() early return -> move to a new
  t_llama_unit case "append_v_row matches the independent packed-V formula" (heap owner, memcpy compare).
- W3 4188336267 kv_cache_fwd.hpp:43: native_k_view is a plain alias; PR body row "bare pointer is a compile error" overclaims for
  K -> reword body; distinct K type in #4424.
- W4 4188336302 t_llama_unit:419: drop 9 checks (5 trivial-type repeats of kv_cache.hpp:2339/1553/1596, 2 sizeof, no-operator[],
  not-default-constructible); keep kernel probes, pointer ctor, conversions, at(), temporary-owner (lifetime rule v_vnni.hpp:105-106),
  alignof (64-byte loads).
- W5 4188336316 t_llama_unit:3298: poison GENERATE {2,3} duplicates the bit-exact four-parity section -> back to 3 dst tokens.
- W6 4188336324: rename "append_v preserves poison" -> "append_v zeroes the poisoned partner" + file comment 3273-3275.
- L3 squash: propose 3 topical commits (views+kernels+call sites / DMA-creates-blocks / tests), after the test edits; replay the
  2026-10-05 conflict resolution; force-with-lease; re-run tests.
- L4a: body's Words row says required CI builds AMX-off; main's cmake-single-platform.yml:355 passes -DTRON_AMX_DISPATCH=ON (PR 4505).
- L4b: unit rows at 96a6220ab6 already in the body; token identity pre-merge -> re-run on the squashed head, replace all rows.
- L4c: remove assertion arithmetic, timestamps, log paths.

**How to apply:** jhan decides; nothing posted. Order: test edits -> body edits -> squash -> 3bda re-run -> push -> replies.
Related: [[pr4557-ben-review-response]], [[issue4525-implementation]], [[pr-description-no-history]].

APPLIED 2026-10-06 04:1x-04:56 UTC (jhan: "go ahead with what you suggested ... for the rest", with "VNNI packed V"/"VNNI packed-K"
wording in the Short version / Not in this PR): test edits commit 1bdd592ff2 (on jhan-kv-typed-tensors-pre-squash-20261006, pushed =
the full reviewed history incl. the merge of main 96a6220ab6); SQUASH = ONE commit c5d44bd86f on main dd6e85226b (git merge --squash of
the pre-squash branch onto origin/main; TRAP: `git checkout <branch> -- .` onto a newer main reverts main's newer files, caught before
the push); force-with-lease pushed, MERGEABLE. PR body rewritten (Short/Not-in-PR/Words AMX row/kv_cache_fwd bullet/#4424 table row/
new Status 2026-10-06 with labelled pre-squash + pre-merge rows). Replies posted: W1 4191665424, W2 4191665555, W3 4191665706,
W4 4191665855, W5 4191665975, W6 4191666160; summary comment 6009623448 (L3/L4a-c); review re-requested from Wado-posi.
Page regenerated with an Outcome section + posted texts. Deviation from the page: 1 commit not 3 (no file-level split compiles at
every intermediate state). PENDING: 3bda chain exec/i4557squash-20261006/chain.sh (pid 1064620 on 3bda, log
exec/logs/i4557squash-20261006-chain.log, done marker exec/results/i4557squash-20261006/chain.done) waits for the nightly lease
(busy since ~03:3x UTC 10-06), then unit tests in /var/tmp/jhan/tron-issue4525 (gen + gen-amxoff, incl. new "formula" case) +
runtron.main1006 (tron-main0922 at dd6e85226b) vs runtron.squash (tron-i4525rt2 at c5d44bd86f) Step D cpu/fpga p1024. THEN: replace
the Status rows + token-identity paragraph in the PR body with the c5d44bd86f results (re-fetch body first), tell jhan.
2026-10-06 13:31-13:38 UTC: chain.sh unit tests at c5d44bd86f PASSED both trees (t_llama_unit 249115/62, t_amx_numerics 4109/4 = 12301 -
8192 moved REQUIREs, dtype 1612, hetero 2783/3, packed-bits 20751, formula 8192, poison 16385, sliding 53593; lint-notes 0; only
t_rinzler fails = main's defect). GCP Nix + Debian smoke green on c5d44bd86f. TRAP: `--preset cross-avx512` no longer exists on main
(PR 4726 removed it; `native` now = explicit AVX-512 flags, no -march=native) -> build2.sh configure-failed; chain2.sh (steps 3-5,
native preset) launched 13:38 UTC; body patch script scratchpad patch-body3.py waits for the token-identity paragraph.
DONE 2026-10-06 14:12 UTC: chain2 ok (runtron.main1006 = main dd6e85226b in tron-main0922, runtron.squash = c5d44bd86f in tron-i4525rt2,
native preset); Step D cpu p1024 base/head/head2/baseoff/headoff + fpga p1024 base/head = ONE identical 256-token file (sha aa272c0e...);
serving restored, claim released. PR body Status now = c5d44bd86f rows only (unit tests + token identity, 2026-10-06); follow-up PR comment
posted. Results exec/results/i4557squash-20261006/, evidence issue4525/evidence/squash-3bda/. Open: Wade's re-review.
