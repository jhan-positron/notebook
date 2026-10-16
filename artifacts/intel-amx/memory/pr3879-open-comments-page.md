---
name: pr3879-open-comments-page
description: "2026-09-10/11 page PR3879/PR-open-comments.html: status + draft reply per open review thread on #3879 (4 still open after jhan closed 2,3,7,8 on 09-10 evening), Ben's review body, Wade's evaluation; T1 bound correction (63 ns pack) + lazy-pack sketch; head 524c510609"
metadata: 
  node_type: memory
  type: project
  originSessionId: a32b231a-3e77-4d83-a47b-e3c9f7bd7660
  modified: 2026-09-10T18:46:00.065Z
---

Page: ~/workspace/intel-AMX/PR3879/PR-open-comments.html (generator gen_page.py + per-item final-*.json in the
session scratchpad). v1 2026-09-10 18:30 UTC at head 26a0338c3b; v2 2026-09-11 at head 524c510609 after jhan
replied on threads 2 (attn_accum, landed 752e9f571a), 3 (range_hint, comment 524c510609), 7 (#4265) and resolved 2,3,7,8.
Still open: 1 (Jeremy), 4 (mask_t), 5 (two paths), 6 (syscall comment). Item 5 is SETTLED by the 2026-09-09 walkthrough transcript
(Google Doc 1S-vphIbaMq0oVNNGto3XwafFVagWNENTwFxH0-ZJUQA, 00:50:49-00:52:19: Ben compared apply_page_tok/apply_dense_amx_page side by
side, 'not as bad as I thought', 'no, that's fine, I'm okay with this'); the Gemini 'Next steps' item 'Refactor duplicated code' overstates
his worry at 00:45-00:47, not his conclusion. Item 8: uint16_t -> tron::bf16 everywhere (iface :185/:218/:229, slot :283, amx_qp :1384,
apply_page_tok param :1563, call sites cast-free); old-vs-new table on the page. jhan asked (2026-09-10) for item 1 to be SHORT
(the correction is understood) plus a subsection on the lazy pack: what changes are needed -> sketch in item 1's extra_html
(~15 lines at the pack site :1384-1392 + lazy region flag + dispatch test :152/:200 + comment :1321-1327 + PR-body clause).

Open threads on #3879 at that time (8): Jeremy 3858305362 (lazy region/pack); Ben 3936949728+3973410716
(thread_local -> attn_accum), 3936963481+3973407196 (helper; range_hint), 3936968255 (mask_t),
3936986164 (two paths), 3937013971 (syscall comment), 3937077542 (memory order), 3937239431 (tron::bf16).
Resolved: env var (jhan 2026-09-10, issue #4338), inline globals, Jeremy aligned buffer.

Findings that change what jhan posts:
- T1: the 2026-08-31 reply's 0.5-0.8 % waste bound used the MIRROR build's 6.3 ns pack; PR 1's only
  packer costs 63 ns/pack (bench-qpack.txt lines 8-10, same loop body at head, not re-measured), so the
  same arithmetic gives 3.2-4.7 % of a decode step's CPU (est.), ~0.3-0.4 % of wall-clock decode, below
  the 0.6 % same-code spread of the 2026-09-09 round. Needs a public correction either way; keep-eager (a)
  vs lazy pack (b) is jhan's call.
- T2: agrees with [[qpack-attn-accum-investigation]]: recommend B (vector member, 5b5eeca67f); reply is
  written for AFTER the cherry-pick + push (fill the hash). Array costs 27.5 MiB / 220 MiB per model state.
- T3: agrees with [[range-hint-audit]]: hint returned unchanged = dotter's value; measured range_cut
  60.0/9.09/2.33 % prefill page visits at prompt 256/2048/8192, 0 % decode (mirror arm, inferred for PR 1).
- T7: #4265 MERGED 2026-09-10 17:45 UTC (47760c7533); PR 1 inherits on rebase; resolve now.
- W-items: LANDED 2026-09-11 02:3x UTC as 4290402491 on jhan-amx-p0 (pushed, fast-forward from 524c510609): s_pages static_assert,
  tron::finally tile-region guard (capture [&], not [amx_on]: with a constant-false amx_eligible the const bool amx_on is a constant
  expression and clang's -Wunused-lambda-capture fires on an explicit capture; found by a review agent, not compile-verified), and the
  = nullptr default removed. 3bda: ON build 132 s, 4109/4 + 1559/1 + 120054/27; OFF t_llama_unit 120054/27 (exec/logs/split-w3edits*-*.txt).
  PR description now stale: 'Verification of this tip' + 'four topical commits' (jhan edits bodies himself). Bundle (2026-09-11, on hold): + drop the = nullptr default on apply_page_tok's amx_q_packed (item 13), optional doc line adding
  delphi-3af6 to the AMX-runner list; one commit, one 3bda test round, then post items 11-13 as one PR comment. Still open: numerics sentence. delphi-3af6 (CI
  test host) IS a 6962P with AMX flags but not in README.ci.md's runner list; CI keeps no test output.

**Why:** Ben's CHANGES_REQUESTED stands on the old head; the re-review request needs every open thread
answered at the current head with consistent line numbers.
**How to apply:** follow the page's "Suggested order of work" (resolve 7,4,6,8 first; 3 keep open; 2 and 1
need decisions; 9-13 go into one PR comment). Trap: shared facts files go stale mid-session (PR 4265
merged while agents ran); re-check PR states with gh before posting. Related: [[pr3879-split-progress]].
