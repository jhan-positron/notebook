# i5097-20261021: does the dense-page live-mask fast path remove the kill-switch prefill cost of PR 5047 (issue #5097)?

Short version. Issue #5097: PR 5047's two-pass software K scoring loop costs +2.25 s (+2.9 %) of prefill on llama-3.1-8b at
prompt 8192 under the AMX kill switch. The fix candidate F2 (commit b79dfb9fed on top of PR 5098's head, local branch
jhan-vnnik-1-5047-fixes-f2, not pushed) builds the live mask arithmetically on a dense page. These scripts build that binary and
PR 5047's commit 1 alone, then compare four binaries on our half of delphi-3bda, after tonight's nightly CI.

## Words used here

- the fix = commit b79dfb9fed (PR 5098 head db76973fdd + the fast path), option TRON_K_VNNI OFF, tag b47f -> /var/tmp/jhan/tron-b47f/gen/runtron.b47f.
- c1 = PR 5047 commit 1 alone (e17a12ff09 on PR 4956's head: the loop split without the cache move), tag b47c1. It attributes the cost to commit 1.
- base / head = the pr5047-20261020 binaries b47b (a5697f86d3) and b47h (ade89a9d9c), reused when present at those shas.
- <arm>off = the same binary under the kill switch TRON_AMX_DISABLE=1. The band, our half, the lease, the takeover: as in pr5047-20261020/README.md.

## Files (every one a fork of pr5047-20261020's, with NAME i5097-20261021)

- build3.sh = build2.sh. chain2.sh step B runs it for b47f and b47c1 (and for b47b/b47h only when their binaries are missing or at another sha).
- campaign2.sh = campaign.sh + arms fix/c1 (and fixoff/c1off), RT_FIX/RT_C1, the cell table below.
- smoke2.sh = smoke.sh sourcing campaign2.sh. tests2.sh = tests.sh for b47f (three test binaries, plus t_amx_numerics and t_llama_unit under the kill switch).
- chain2.sh = chain.sh: waits for NOT_BEFORE (default 2026-10-22T04:00:00Z, after the nightly) and a free slot before anything, then B I D T R.
- gen_report2.py = gen_report.py with the arms and pairs below. launch2.sh = launch.sh.

## Cells

Identity (1 user, temperature 0, pay-for-determinism, 256 tokens): l8b-tp2-cpu-p1024 arms head fix fix2, must match fix:fix2 and fix:head.
l8b-tp2-cpu-p1024-off arms headoff fixoff, must match fixoff:headoff. The fast path selects the same tokens, so the tokens must be identical.

Perf (key|model|tp|users|prompt|attn|len|arms), REPS 4:

    l8b-tp2-8u-p8192-off  llama-3.1-8b-instruct-good-tp2  2 8 8192 cpu 256  baseoff headoff fixoff c1off   (the issue's cell)
    l8b-tp2-8u-p8192-cpu  llama-3.1-8b-instruct-good-tp2  2 8 8192 cpu 256  base head fix                  (the shipped configuration, AMX on)
    l8b-tp2-8u-p1024-cpu  llama-3.1-8b-instruct-good-tp2  2 8 1024 cpu 256  head fix                       (no regression at a short prompt)

Pairs in the report: head:base, fix:head, fix:base, headoff:baseoff, fixoff:headoff, fixoff:baseoff, c1off:baseoff.

Expected: fixoff:headoff prefill -2 s or more (the fast path removes the selection pass on dense pages), fixoff:baseoff inside the
band, c1off:baseoff about +2.2 s (the cost is commit 1's), fix:head inside the band with the +0.138 s gone, identical tokens.

## Launch (from claude-box)

    bash exec/i5097-20261021/launch2.sh check
    NOT_BEFORE=2026-10-22T04:00:00Z bash exec/i5097-20261021/launch2.sh chain

Log exec/logs/i5097-20261021-chain.log, status exec/logs/i5097-20261021-chain.status, results exec/results/i5097-20261021/.
Stop: on 3bda, `pkill -f i5097-20261021/chain2.sh` then `pkill -f i5097-20261021/campaign2.sh` (the chain's EXIT trap restores serving).
