# Lineage inventory: mirror-vs-VNNI-K.html

Written 2026-09-20 by the handoff run (Step 4b, Computed-from files). One line per file the page's input cites, with the decision taken. Sizes in bytes. Paths are relative to the canonical root `claude-agentsrv:/home/jhan/workspace/intel-AMX`. A per-repetition log is a duplicate when the proposed compact text holds every cited line that carries a measured number (checked line by line on the `[Request N] ...` payload).

- generator: `exec/vnnik-20260914/gen_compare.py` (mirrored at `artifacts/intel-amx/exec/vnnik-20260914/gen_compare.py`)
- input: `exec/results/vnnik-20260914/mirror-vs-vnni-rows.json` (hand-edited after build)
- input built by: `exec/vnnik-20260914/pull-mirror-vs-vnni-data-wf_9b0f456d-293.js` (Claude Workflow script; origin: `~/.claude/projects/-home-jhan-workspace-intel-AMX-VNNIed-K-in-place/80bfb407-086b-42a0-a4b7-cb11b85eb459/workflows/scripts/`)
- regenerate: `run on claude-agentsrv: python3 /home/jhan/workspace/intel-AMX/exec/vnnik-20260914/gen_compare.py /home/jhan/workspace/intel-AMX/exec/results/vnnik-20260914/mirror-vs-vnni-rows.json <OUT>` (one line differs: the "Pulled from ... on <timestamp>" sentence)

| Decision | Canonical path (relative) | Repo path or reason | Bytes | Note |
|---|---|---|---|---|
| preserved | `PR3879/more-testing/round-1/status.md` | `artifacts/intel-amx/pr3879/more-testing/round-1/status.md` | 42248 |  |
| preserved | `exec/results/ctxfill-20260901/cell.log` | `artifacts/intel-amx/exec/results/ctxfill-20260901/cell.log` | 23351 | 2 measured lines; compact texts: ['ss-window.txt', 'journal-window.txt'] |
| preserved | `exec/results/ctxfill2-20260901/cell.log` | `artifacts/intel-amx/exec/results/ctxfill2-20260901/cell.log` | 22995 | 2 measured lines; compact texts: [] |
| preserved | `exec/results/fence3-20260901/cell.log` | `artifacts/intel-amx/exec/results/fence3-20260901/cell.log` | 23627 | 2 measured lines; compact texts: [] |
| preserved | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__canon2__u8/meta.json` | `artifacts/intel-amx/exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__canon2__u8/meta.json` | 701 |  |
| preserved | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__canon2__u8/perf.json` | `artifacts/intel-amx/exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__canon2__u8/perf.json` | 3093 |  |
| preserved | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__canon2__u8/proof.txt` | `artifacts/intel-amx/exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__canon2__u8/proof.txt` | 585 | adjacency |
| preserved | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__canon__u1/meta.json` | `artifacts/intel-amx/exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__canon__u1/meta.json` | 699 |  |
| preserved | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__canon__u1/perf.json` | `artifacts/intel-amx/exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__canon__u1/perf.json` | 937 |  |
| preserved | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__canon__u1/proof.txt` | `artifacts/intel-amx/exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__canon__u1/proof.txt` | 579 |  |
| preserved | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__canon__u2/meta.json` | `artifacts/intel-amx/exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__canon__u2/meta.json` | 701 |  |
| preserved | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__canon__u2/perf.json` | `artifacts/intel-amx/exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__canon__u2/perf.json` | 1246 |  |
| preserved | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__canon__u2/proof.txt` | `artifacts/intel-amx/exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__canon__u2/proof.txt` | 583 | adjacency |
| preserved | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__canon__u4/meta.json` | `artifacts/intel-amx/exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__canon__u4/meta.json` | 699 |  |
| preserved | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__canon__u4/perf.json` | `artifacts/intel-amx/exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__canon__u4/perf.json` | 1869 |  |
| preserved | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__canon__u4/proof.txt` | `artifacts/intel-amx/exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__canon__u4/proof.txt` | 573 | adjacency |
| preserved | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__canon__u8/meta.json` | `artifacts/intel-amx/exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__canon__u8/meta.json` | 700 |  |
| preserved | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__canon__u8/perf.json` | `artifacts/intel-amx/exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__canon__u8/perf.json` | 3087 |  |
| preserved | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__canon__u8/proof.txt` | `artifacts/intel-amx/exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__canon__u8/proof.txt` | 577 |  |
| preserved | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__g1mirror__u8/meta.json` | `artifacts/intel-amx/exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__g1mirror__u8/meta.json` | 719 |  |
| preserved | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__g1mirror__u8/perf.json` | `artifacts/intel-amx/exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__g1mirror__u8/perf.json` | 3101 |  |
| preserved | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__g1mirror__u8/proof.txt` | `artifacts/intel-amx/exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__g1mirror__u8/proof.txt` | 606 |  |
| preserved | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__inplace__u1/meta.json` | `artifacts/intel-amx/exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__inplace__u1/meta.json` | 717 |  |
| preserved | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__inplace__u1/perf.json` | `artifacts/intel-amx/exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__inplace__u1/perf.json` | 935 |  |
| preserved | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__inplace__u1/proof.txt` | `artifacts/intel-amx/exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__inplace__u1/proof.txt` | 601 | adjacency |
| preserved | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__inplace__u2/meta.json` | `artifacts/intel-amx/exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__inplace__u2/meta.json` | 718 |  |
| preserved | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__inplace__u2/perf.json` | `artifacts/intel-amx/exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__inplace__u2/perf.json` | 1247 |  |
| preserved | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__inplace__u2/proof.txt` | `artifacts/intel-amx/exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__inplace__u2/proof.txt` | 597 | adjacency |
| preserved | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__inplace__u4/meta.json` | `artifacts/intel-amx/exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__inplace__u4/meta.json` | 720 |  |
| preserved | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__inplace__u4/perf.json` | `artifacts/intel-amx/exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__inplace__u4/perf.json` | 1889 |  |
| preserved | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__inplace__u4/proof.txt` | `artifacts/intel-amx/exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__inplace__u4/proof.txt` | 603 | adjacency |
| preserved | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__inplace__u8/meta.json` | `artifacts/intel-amx/exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__inplace__u8/meta.json` | 720 |  |
| preserved | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__inplace__u8/perf.json` | `artifacts/intel-amx/exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__inplace__u8/perf.json` | 3089 |  |
| preserved | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__inplace__u8/proof.txt` | `artifacts/intel-amx/exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__inplace__u8/proof.txt` | 600 |  |
| preserved | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__mirror__u1/meta.json` | `artifacts/intel-amx/exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__mirror__u1/meta.json` | 700 |  |
| preserved | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__mirror__u1/perf.json` | `artifacts/intel-amx/exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__mirror__u1/perf.json` | 937 |  |
| preserved | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__mirror__u1/proof.txt` | `artifacts/intel-amx/exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__mirror__u1/proof.txt` | 579 | adjacency |
| preserved | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__mirror__u2/meta.json` | `artifacts/intel-amx/exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__mirror__u2/meta.json` | 699 |  |
| preserved | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__mirror__u2/perf.json` | `artifacts/intel-amx/exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__mirror__u2/perf.json` | 1243 |  |
| preserved | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__mirror__u2/proof.txt` | `artifacts/intel-amx/exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__mirror__u2/proof.txt` | 575 | adjacency |
| preserved | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__mirror__u4/meta.json` | `artifacts/intel-amx/exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__mirror__u4/meta.json` | 701 |  |
| preserved | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__mirror__u4/perf.json` | `artifacts/intel-amx/exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__mirror__u4/perf.json` | 1893 |  |
| preserved | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__mirror__u4/proof.txt` | `artifacts/intel-amx/exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__mirror__u4/proof.txt` | 581 | adjacency |
| preserved | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__mirror__u8/meta.json` | `artifacts/intel-amx/exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__mirror__u8/meta.json` | 702 |  |
| preserved | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__mirror__u8/perf.json` | `artifacts/intel-amx/exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__mirror__u8/perf.json` | 3096 |  |
| preserved | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__mirror__u8/proof.txt` | `artifacts/intel-amx/exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__mirror__u8/proof.txt` | 578 |  |
| preserved | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__off__u8/meta.json` | `artifacts/intel-amx/exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__off__u8/meta.json` | 697 |  |
| preserved | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__off__u8/perf.json` | `artifacts/intel-amx/exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__off__u8/perf.json` | 3092 |  |
| preserved | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__off__u8/proof.txt` | `artifacts/intel-amx/exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__off__u8/proof.txt` | 577 | adjacency |
| preserved | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__sonly__u1/meta.json` | `artifacts/intel-amx/exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__sonly__u1/meta.json` | 710 |  |
| preserved | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__sonly__u1/perf.json` | `artifacts/intel-amx/exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__sonly__u1/perf.json` | 934 |  |
| preserved | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__sonly__u1/proof.txt` | `artifacts/intel-amx/exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__sonly__u1/proof.txt` | 591 | adjacency |
| preserved | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__sonly__u2/meta.json` | `artifacts/intel-amx/exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__sonly__u2/meta.json` | 713 |  |
| preserved | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__sonly__u2/perf.json` | `artifacts/intel-amx/exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__sonly__u2/perf.json` | 1245 |  |
| preserved | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__sonly__u2/proof.txt` | `artifacts/intel-amx/exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__sonly__u2/proof.txt` | 595 | adjacency |
| preserved | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__sonly__u4/meta.json` | `artifacts/intel-amx/exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__sonly__u4/meta.json` | 715 |  |
| preserved | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__sonly__u4/perf.json` | `artifacts/intel-amx/exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__sonly__u4/perf.json` | 1890 |  |
| preserved | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__sonly__u4/proof.txt` | `artifacts/intel-amx/exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__sonly__u4/proof.txt` | 593 | adjacency |
| preserved | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__sonly__u8/meta.json` | `artifacts/intel-amx/exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__sonly__u8/meta.json` | 717 |  |
| preserved | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__sonly__u8/perf.json` | `artifacts/intel-amx/exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__sonly__u8/perf.json` | 3100 |  |
| preserved | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__sonly__u8/proof.txt` | `artifacts/intel-amx/exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__sonly__u8/proof.txt` | 606 | adjacency |
| preserved | `exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__canon2__u8/meta.json` | `artifacts/intel-amx/exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__canon2__u8/meta.json` | 696 |  |
| preserved | `exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__canon2__u8/perf.json` | `artifacts/intel-amx/exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__canon2__u8/perf.json` | 3095 |  |
| preserved | `exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__canon2__u8/proof.txt` | `artifacts/intel-amx/exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__canon2__u8/proof.txt` | 531 | adjacency |
| preserved | `exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__canon__u1/meta.json` | `artifacts/intel-amx/exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__canon__u1/meta.json` | 690 |  |
| preserved | `exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__canon__u1/perf.json` | `artifacts/intel-amx/exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__canon__u1/perf.json` | 931 |  |
| preserved | `exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__canon__u1/proof.txt` | `artifacts/intel-amx/exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__canon__u1/proof.txt` | 529 |  |
| preserved | `exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__canon__u2/meta.json` | `artifacts/intel-amx/exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__canon__u2/meta.json` | 696 |  |
| preserved | `exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__canon__u2/perf.json` | `artifacts/intel-amx/exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__canon__u2/perf.json` | 1242 |  |
| preserved | `exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__canon__u2/proof.txt` | `artifacts/intel-amx/exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__canon__u2/proof.txt` | 537 | adjacency |
| preserved | `exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__canon__u4/meta.json` | `artifacts/intel-amx/exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__canon__u4/meta.json` | 694 |  |
| preserved | `exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__canon__u4/perf.json` | `artifacts/intel-amx/exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__canon__u4/perf.json` | 1891 |  |
| preserved | `exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__canon__u4/proof.txt` | `artifacts/intel-amx/exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__canon__u4/proof.txt` | 531 | adjacency |
| preserved | `exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__canon__u8/meta.json` | `artifacts/intel-amx/exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__canon__u8/meta.json` | 693 |  |
| preserved | `exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__canon__u8/perf.json` | `artifacts/intel-amx/exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__canon__u8/perf.json` | 3092 |  |
| preserved | `exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__canon__u8/proof.txt` | `artifacts/intel-amx/exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__canon__u8/proof.txt` | 531 | adjacency |
| preserved | `exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__inplace__u1/meta.json` | `artifacts/intel-amx/exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__inplace__u1/meta.json` | 655 |  |
| preserved | `exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__inplace__u1/perf.log` | `artifacts/intel-amx/exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__inplace__u1/perf.log` | 3318 | 0 perf*.json beside |
| preserved | `exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__inplace__u2/meta.json` | `artifacts/intel-amx/exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__inplace__u2/meta.json` | 538 |  |
| preserved | `exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__inplace__u4/meta.json` | `artifacts/intel-amx/exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__inplace__u4/meta.json` | 656 |  |
| preserved | `exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__inplace__u8/meta.json` | `artifacts/intel-amx/exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__inplace__u8/meta.json` | 658 |  |
| preserved | `exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__mirror__u1/meta.json` | `artifacts/intel-amx/exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__mirror__u1/meta.json` | 695 |  |
| preserved | `exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__mirror__u1/perf.json` | `artifacts/intel-amx/exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__mirror__u1/perf.json` | 931 |  |
| preserved | `exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__mirror__u1/proof.txt` | `artifacts/intel-amx/exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__mirror__u1/proof.txt` | 537 | adjacency |
| preserved | `exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__mirror__u2/meta.json` | `artifacts/intel-amx/exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__mirror__u2/meta.json` | 696 |  |
| preserved | `exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__mirror__u2/perf.json` | `artifacts/intel-amx/exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__mirror__u2/perf.json` | 1239 |  |
| preserved | `exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__mirror__u2/proof.txt` | `artifacts/intel-amx/exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__mirror__u2/proof.txt` | 529 | adjacency |
| preserved | `exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__mirror__u4/meta.json` | `artifacts/intel-amx/exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__mirror__u4/meta.json` | 696 |  |
| preserved | `exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__mirror__u4/perf.json` | `artifacts/intel-amx/exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__mirror__u4/perf.json` | 1892 |  |
| preserved | `exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__mirror__u4/proof.txt` | `artifacts/intel-amx/exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__mirror__u4/proof.txt` | 531 | adjacency |
| preserved | `exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__mirror__u8/meta.json` | `artifacts/intel-amx/exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__mirror__u8/meta.json` | 697 |  |
| preserved | `exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__mirror__u8/perf.json` | `artifacts/intel-amx/exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__mirror__u8/perf.json` | 3098 |  |
| preserved | `exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__mirror__u8/proof.txt` | `artifacts/intel-amx/exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__mirror__u8/proof.txt` | 532 |  |
| preserved | `exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__off__u8/meta.json` | `artifacts/intel-amx/exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__off__u8/meta.json` | 691 |  |
| preserved | `exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__off__u8/perf.json` | `artifacts/intel-amx/exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__off__u8/perf.json` | 3084 |  |
| preserved | `exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__off__u8/proof.txt` | `artifacts/intel-amx/exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__off__u8/proof.txt` | 531 | adjacency |
| preserved | `exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__sonly__u1/meta.json` | `artifacts/intel-amx/exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__sonly__u1/meta.json` | 534 |  |
| preserved | `exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__sonly__u1/perf.log` | `artifacts/intel-amx/exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__sonly__u1/perf.log` | 3317 | 0 perf*.json beside |
| preserved | `exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__sonly__u2/meta.json` | `artifacts/intel-amx/exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__sonly__u2/meta.json` | 534 |  |
| preserved | `exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__sonly__u4/meta.json` | `artifacts/intel-amx/exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__sonly__u4/meta.json` | 534 |  |
| preserved | `exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__sonly__u8/meta.json` | `artifacts/intel-amx/exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__sonly__u8/meta.json` | 533 |  |
| preserved | `exec/results/g1-20260908/runtron-8u8k.txt` | `artifacts/intel-amx/exec/results/g1-20260908/runtron-8u8k.txt` | 44736 | header, sha256 lines |
| preserved | `exec/results/g1-20260908/runtron-g1kill-rep2-t0.log` | `artifacts/intel-amx/exec/results/g1-20260908/runtron-g1kill-rep2-t0.log` | 19633 | 0 measured lines; compact texts: ['probe-build.txt', 'runtron-8u8k.txt'] |
| preserved | `exec/results/g1-20260908/runtron-inplace-rep2-t0.log` | `artifacts/intel-amx/exec/results/g1-20260908/runtron-inplace-rep2-t0.log` | 21195 | 8 measured lines; compact texts: ['probe-build.txt', 'runtron-8u8k.txt'] |
| preserved | `exec/results/g1-20260908/summary.json` | `artifacts/intel-amx/exec/results/g1-20260908/summary.json` | 37004 | runtron_8u8k.g1canon |
| preserved | `exec/results/g1-20260908/summary.md` | `artifacts/intel-amx/exec/results/g1-20260908/summary.md` | 52365 |  |
| preserved | `exec/results/g1-20260908/summary.txt` | `artifacts/intel-amx/exec/results/g1-20260908/summary.txt` | 5925 |  |
| preserved | `exec/results/gptoss120b-pr1-half-20260909T1706.txt` | `artifacts/intel-amx/exec/results/gptoss120b-pr1-half-20260909T1706.txt` | 35505 | header, placement, shape-gate note, binary sha256 |
| preserved | `exec/results/more-testing-r1/cells/ingested-gpt-oss-120b-tp4__canon/meta.json` | `artifacts/intel-amx/exec/results/more-testing-r1/cells/ingested-gpt-oss-120b-tp4__canon/meta.json` | 578 |  |
| preserved | `exec/results/more-testing-r1/cells/ingested-gpt-oss-120b-tp4__canon/perf.json` | `artifacts/intel-amx/exec/results/more-testing-r1/cells/ingested-gpt-oss-120b-tp4__canon/perf.json` | 3109 |  |
| preserved | `exec/results/more-testing-r1/cells/ingested-gpt-oss-120b-tp4__mirror/meta.json` | `artifacts/intel-amx/exec/results/more-testing-r1/cells/ingested-gpt-oss-120b-tp4__mirror/meta.json` | 627 |  |
| preserved | `exec/results/more-testing-r1/cells/ingested-gpt-oss-120b-tp4__mirror/mmlu.log` | `artifacts/intel-amx/exec/results/more-testing-r1/cells/ingested-gpt-oss-120b-tp4__mirror/mmlu.log` | 1651 | 0 measured lines; compact texts: [] |
| preserved | `exec/results/more-testing-r1/cells/ingested-gpt-oss-120b-tp4__mirror/perf.json` | `artifacts/intel-amx/exec/results/more-testing-r1/cells/ingested-gpt-oss-120b-tp4__mirror/perf.json` | 3108 |  |
| preserved | `exec/results/more-testing-r1/cells/ingested-gpt-oss-120b-tp4__off/meta.json` | `artifacts/intel-amx/exec/results/more-testing-r1/cells/ingested-gpt-oss-120b-tp4__off/meta.json` | 617 |  |
| preserved | `exec/results/more-testing-r1/cells/ingested-gpt-oss-120b-tp4__off/mmlu.log` | `artifacts/intel-amx/exec/results/more-testing-r1/cells/ingested-gpt-oss-120b-tp4__off/mmlu.log` | 1033 | 0 measured lines; compact texts: [] |
| preserved | `exec/results/more-testing-r1/cells/ingested-gpt-oss-120b-tp4__off/perf.json` | `artifacts/intel-amx/exec/results/more-testing-r1/cells/ingested-gpt-oss-120b-tp4__off/perf.json` | 3112 |  |
| preserved | `exec/results/more-testing-r1/cells/ingested-qwen-3-4b-instruct-2507-tp4__canon/meta.json` | `artifacts/intel-amx/exec/results/more-testing-r1/cells/ingested-qwen-3-4b-instruct-2507-tp4__canon/meta.json` | 635 |  |
| preserved | `exec/results/more-testing-r1/cells/ingested-qwen-3-4b-instruct-2507-tp4__canon/mmlu.log` | `artifacts/intel-amx/exec/results/more-testing-r1/cells/ingested-qwen-3-4b-instruct-2507-tp4__canon/mmlu.log` | 1282 | 0 measured lines; compact texts: [] |
| preserved | `exec/results/more-testing-r1/cells/ingested-qwen-3-4b-instruct-2507-tp4__canon/perf.json` | `artifacts/intel-amx/exec/results/more-testing-r1/cells/ingested-qwen-3-4b-instruct-2507-tp4__canon/perf.json` | 3087 |  |
| preserved | `exec/results/more-testing-r1/cells/ingested-qwen-3-4b-instruct-2507-tp4__mirror/meta.json` | `artifacts/intel-amx/exec/results/more-testing-r1/cells/ingested-qwen-3-4b-instruct-2507-tp4__mirror/meta.json` | 806 |  |
| preserved | `exec/results/more-testing-r1/cells/ingested-qwen-3-4b-instruct-2507-tp4__mirror/mmlu.log` | `artifacts/intel-amx/exec/results/more-testing-r1/cells/ingested-qwen-3-4b-instruct-2507-tp4__mirror/mmlu.log` | 975 | 0 measured lines; compact texts: [] |
| preserved | `exec/results/more-testing-r1/cells/ingested-qwen-3-4b-instruct-2507-tp4__mirror/perf.json` | `artifacts/intel-amx/exec/results/more-testing-r1/cells/ingested-qwen-3-4b-instruct-2507-tp4__mirror/perf.json` | 3098 |  |
| preserved | `exec/results/more-testing-r1/cells/ingested-qwen-3-4b-instruct-2507-tp4__off/meta.json` | `artifacts/intel-amx/exec/results/more-testing-r1/cells/ingested-qwen-3-4b-instruct-2507-tp4__off/meta.json` | 627 |  |
| preserved | `exec/results/more-testing-r1/cells/ingested-qwen-3-4b-instruct-2507-tp4__off/mmlu.log` | `artifacts/intel-amx/exec/results/more-testing-r1/cells/ingested-qwen-3-4b-instruct-2507-tp4__off/mmlu.log` | 1079 | 0 measured lines; compact texts: [] |
| preserved | `exec/results/more-testing-r1/cells/ingested-qwen-3-4b-instruct-2507-tp4__off/perf.json` | `artifacts/intel-amx/exec/results/more-testing-r1/cells/ingested-qwen-3-4b-instruct-2507-tp4__off/perf.json` | 3085 |  |
| preserved | `exec/results/more-testing-r1/cells/ingested-qwen-3-4b-instruct-2507-tp4__off__rep2/meta.json` | `artifacts/intel-amx/exec/results/more-testing-r1/cells/ingested-qwen-3-4b-instruct-2507-tp4__off__rep2/meta.json` | 627 |  |
| preserved | `exec/results/more-testing-r1/cells/ingested-qwen-3-4b-instruct-2507-tp4__off__rep2/mmlu.log` | `artifacts/intel-amx/exec/results/more-testing-r1/cells/ingested-qwen-3-4b-instruct-2507-tp4__off__rep2/mmlu.log` | 1072 | 0 measured lines; compact texts: [] |
| preserved | `exec/results/more-testing-r1/cells/ingested-qwen-3-4b-instruct-2507-tp4__off__rep2/perf.json` | `artifacts/intel-amx/exec/results/more-testing-r1/cells/ingested-qwen-3-4b-instruct-2507-tp4__off__rep2/perf.json` | 3088 |  |
| preserved | `exec/results/more-testing-r1/cells/llama-3.1-8b-instruct-good-tp2__canon/meta.json` | `artifacts/intel-amx/exec/results/more-testing-r1/cells/llama-3.1-8b-instruct-good-tp2__canon/meta.json` | 582 |  |
| preserved | `exec/results/more-testing-r1/cells/llama-3.1-8b-instruct-good-tp2__canon/perf.json` | `artifacts/intel-amx/exec/results/more-testing-r1/cells/llama-3.1-8b-instruct-good-tp2__canon/perf.json` | 3092 |  |
| preserved | `exec/results/more-testing-r1/cells/llama-3.1-8b-instruct-good-tp2__mirror/meta.json` | `artifacts/intel-amx/exec/results/more-testing-r1/cells/llama-3.1-8b-instruct-good-tp2__mirror/meta.json` | 631 |  |
| preserved | `exec/results/more-testing-r1/cells/llama-3.1-8b-instruct-good-tp2__mirror/mmlu.log` | `artifacts/intel-amx/exec/results/more-testing-r1/cells/llama-3.1-8b-instruct-good-tp2__mirror/mmlu.log` | 1911 | 0 measured lines; compact texts: [] |
| preserved | `exec/results/more-testing-r1/cells/llama-3.1-8b-instruct-good-tp2__mirror/perf.json` | `artifacts/intel-amx/exec/results/more-testing-r1/cells/llama-3.1-8b-instruct-good-tp2__mirror/perf.json` | 3093 |  |
| preserved | `exec/results/more-testing-r1/cells/llama-3.1-8b-instruct-good-tp2__off/meta.json` | `artifacts/intel-amx/exec/results/more-testing-r1/cells/llama-3.1-8b-instruct-good-tp2__off/meta.json` | 621 |  |
| preserved | `exec/results/more-testing-r1/cells/llama-3.1-8b-instruct-good-tp2__off/mmlu.log` | `artifacts/intel-amx/exec/results/more-testing-r1/cells/llama-3.1-8b-instruct-good-tp2__off/mmlu.log` | 2119 | 0 measured lines; compact texts: [] |
| preserved | `exec/results/more-testing-r1/cells/llama-3.1-8b-instruct-good-tp2__off/perf.json` | `artifacts/intel-amx/exec/results/more-testing-r1/cells/llama-3.1-8b-instruct-good-tp2__off/perf.json` | 3087 |  |
| preserved | `exec/results/more-testing-r1/cells/mixtral-8x7b-instruct-v0.1-tp2__canon/meta.json` | `artifacts/intel-amx/exec/results/more-testing-r1/cells/mixtral-8x7b-instruct-v0.1-tp2__canon/meta.json` | 583 |  |
| preserved | `exec/results/more-testing-r1/cells/mixtral-8x7b-instruct-v0.1-tp2__canon/perf.json` | `artifacts/intel-amx/exec/results/more-testing-r1/cells/mixtral-8x7b-instruct-v0.1-tp2__canon/perf.json` | 3117 |  |
| preserved | `exec/results/more-testing-r1/cells/mixtral-8x7b-instruct-v0.1-tp2__mirror/meta.json` | `artifacts/intel-amx/exec/results/more-testing-r1/cells/mixtral-8x7b-instruct-v0.1-tp2__mirror/meta.json` | 632 |  |
| preserved | `exec/results/more-testing-r1/cells/mixtral-8x7b-instruct-v0.1-tp2__mirror/mmlu.log` | `artifacts/intel-amx/exec/results/more-testing-r1/cells/mixtral-8x7b-instruct-v0.1-tp2__mirror/mmlu.log` | 1892 | 0 measured lines; compact texts: [] |
| preserved | `exec/results/more-testing-r1/cells/mixtral-8x7b-instruct-v0.1-tp2__mirror/perf.json` | `artifacts/intel-amx/exec/results/more-testing-r1/cells/mixtral-8x7b-instruct-v0.1-tp2__mirror/perf.json` | 3127 |  |
| preserved | `exec/results/more-testing-r1/cells/mixtral-8x7b-instruct-v0.1-tp2__off/meta.json` | `artifacts/intel-amx/exec/results/more-testing-r1/cells/mixtral-8x7b-instruct-v0.1-tp2__off/meta.json` | 622 |  |
| preserved | `exec/results/more-testing-r1/cells/mixtral-8x7b-instruct-v0.1-tp2__off/mmlu.log` | `artifacts/intel-amx/exec/results/more-testing-r1/cells/mixtral-8x7b-instruct-v0.1-tp2__off/mmlu.log` | 1728 | 0 measured lines; compact texts: [] |
| preserved | `exec/results/more-testing-r1/cells/mixtral-8x7b-instruct-v0.1-tp2__off/perf.json` | `artifacts/intel-amx/exec/results/more-testing-r1/cells/mixtral-8x7b-instruct-v0.1-tp2__off/perf.json` | 3128 |  |
| preserved | `exec/results/more-testing-r1/notes.md` | `artifacts/intel-amx/exec/results/more-testing-r1/notes.md` | 14693 |  |
| preserved | `exec/results/p0perf-20260911/build.txt` | `artifacts/intel-amx/exec/results/p0perf-20260911/build.txt` | 518 |  |
| preserved | `exec/results/p0perf-20260911/cells/ingested-qwen-3-4b-instruct-2507-tp2__off__rep1/meta.json` | `artifacts/intel-amx/exec/results/p0perf-20260911/cells/ingested-qwen-3-4b-instruct-2507-tp2__off__rep1/meta.json` | 1022 | and __rep2 |
| preserved | `exec/results/p0perf-20260911/cells/ingested-qwen-3-4b-instruct-2507-tp2__off__rep1/perf.json` | `artifacts/intel-amx/exec/results/p0perf-20260911/cells/ingested-qwen-3-4b-instruct-2507-tp2__off__rep1/perf.json` | 3131 | and __rep2 |
| preserved | `exec/results/p0perf-20260911/cells/ingested-qwen-3-4b-instruct-2507-tp2__off__rep1/proof.txt` | `artifacts/intel-amx/exec/results/p0perf-20260911/cells/ingested-qwen-3-4b-instruct-2507-tp2__off__rep1/proof.txt` | 772 | and __rep2 |
| preserved | `exec/results/p0perf-20260911/cells/ingested-qwen-3-4b-instruct-2507-tp2__off__rep2/meta.json` | `artifacts/intel-amx/exec/results/p0perf-20260911/cells/ingested-qwen-3-4b-instruct-2507-tp2__off__rep2/meta.json` | 1022 | and __rep2 |
| preserved | `exec/results/p0perf-20260911/cells/ingested-qwen-3-4b-instruct-2507-tp2__off__rep2/perf.json` | `artifacts/intel-amx/exec/results/p0perf-20260911/cells/ingested-qwen-3-4b-instruct-2507-tp2__off__rep2/perf.json` | 3135 | and __rep2 |
| preserved | `exec/results/p0perf-20260911/cells/ingested-qwen-3-4b-instruct-2507-tp2__off__rep2/proof.txt` | `artifacts/intel-amx/exec/results/p0perf-20260911/cells/ingested-qwen-3-4b-instruct-2507-tp2__off__rep2/proof.txt` | 766 | and __rep2 |
| preserved | `exec/results/p0perf-20260911/cells/ingested-qwen-3-4b-instruct-2507-tp2__on__rep1/meta.json` | `artifacts/intel-amx/exec/results/p0perf-20260911/cells/ingested-qwen-3-4b-instruct-2507-tp2__on__rep1/meta.json` | 1027 | and __rep2 |
| preserved | `exec/results/p0perf-20260911/cells/ingested-qwen-3-4b-instruct-2507-tp2__on__rep1/perf.json` | `artifacts/intel-amx/exec/results/p0perf-20260911/cells/ingested-qwen-3-4b-instruct-2507-tp2__on__rep1/perf.json` | 3124 | and __rep2 |
| preserved | `exec/results/p0perf-20260911/cells/ingested-qwen-3-4b-instruct-2507-tp2__on__rep1/proof.txt` | `artifacts/intel-amx/exec/results/p0perf-20260911/cells/ingested-qwen-3-4b-instruct-2507-tp2__on__rep1/proof.txt` | 778 | adjacency |
| preserved | `exec/results/p0perf-20260911/cells/ingested-qwen-3-4b-instruct-2507-tp2__on__rep2/meta.json` | `artifacts/intel-amx/exec/results/p0perf-20260911/cells/ingested-qwen-3-4b-instruct-2507-tp2__on__rep2/meta.json` | 1027 | and __rep2 |
| preserved | `exec/results/p0perf-20260911/cells/ingested-qwen-3-4b-instruct-2507-tp2__on__rep2/perf.json` | `artifacts/intel-amx/exec/results/p0perf-20260911/cells/ingested-qwen-3-4b-instruct-2507-tp2__on__rep2/perf.json` | 3129 | and __rep2 |
| preserved | `exec/results/p0perf-20260911/cells/ingested-qwen-3-4b-instruct-2507-tp2__on__rep2/proof.txt` | `artifacts/intel-amx/exec/results/p0perf-20260911/cells/ingested-qwen-3-4b-instruct-2507-tp2__on__rep2/proof.txt` | 766 | adjacency |
| preserved | `exec/results/p0perf-20260911/cells/ingested-qwen-3-4b-instruct-2507-tp4__off__rep1/meta.json` | `artifacts/intel-amx/exec/results/p0perf-20260911/cells/ingested-qwen-3-4b-instruct-2507-tp4__off__rep1/meta.json` | 1092 | and __rep2 |
| preserved | `exec/results/p0perf-20260911/cells/ingested-qwen-3-4b-instruct-2507-tp4__off__rep1/perf.json` | `artifacts/intel-amx/exec/results/p0perf-20260911/cells/ingested-qwen-3-4b-instruct-2507-tp4__off__rep1/perf.json` | 3089 | and __rep2 |
| preserved | `exec/results/p0perf-20260911/cells/ingested-qwen-3-4b-instruct-2507-tp4__off__rep1/proof.txt` | `artifacts/intel-amx/exec/results/p0perf-20260911/cells/ingested-qwen-3-4b-instruct-2507-tp4__off__rep1/proof.txt` | 874 | adjacency |
| preserved | `exec/results/p0perf-20260911/cells/ingested-qwen-3-4b-instruct-2507-tp4__off__rep2/meta.json` | `artifacts/intel-amx/exec/results/p0perf-20260911/cells/ingested-qwen-3-4b-instruct-2507-tp4__off__rep2/meta.json` | 1092 | and __rep2 |
| preserved | `exec/results/p0perf-20260911/cells/ingested-qwen-3-4b-instruct-2507-tp4__off__rep2/perf.json` | `artifacts/intel-amx/exec/results/p0perf-20260911/cells/ingested-qwen-3-4b-instruct-2507-tp4__off__rep2/perf.json` | 3096 | and __rep2 |
| preserved | `exec/results/p0perf-20260911/cells/ingested-qwen-3-4b-instruct-2507-tp4__off__rep2/proof.txt` | `artifacts/intel-amx/exec/results/p0perf-20260911/cells/ingested-qwen-3-4b-instruct-2507-tp4__off__rep2/proof.txt` | 868 | adjacency |
| preserved | `exec/results/p0perf-20260911/cells/ingested-qwen-3-4b-instruct-2507-tp4__on__rep1/meta.json` | `artifacts/intel-amx/exec/results/p0perf-20260911/cells/ingested-qwen-3-4b-instruct-2507-tp4__on__rep1/meta.json` | 1097 | and __rep2 |
| preserved | `exec/results/p0perf-20260911/cells/ingested-qwen-3-4b-instruct-2507-tp4__on__rep1/perf.json` | `artifacts/intel-amx/exec/results/p0perf-20260911/cells/ingested-qwen-3-4b-instruct-2507-tp4__on__rep1/perf.json` | 3090 | and __rep2 |
| preserved | `exec/results/p0perf-20260911/cells/ingested-qwen-3-4b-instruct-2507-tp4__on__rep1/proof.txt` | `artifacts/intel-amx/exec/results/p0perf-20260911/cells/ingested-qwen-3-4b-instruct-2507-tp4__on__rep1/proof.txt` | 862 | adjacency |
| preserved | `exec/results/p0perf-20260911/cells/ingested-qwen-3-4b-instruct-2507-tp4__on__rep2/meta.json` | `artifacts/intel-amx/exec/results/p0perf-20260911/cells/ingested-qwen-3-4b-instruct-2507-tp4__on__rep2/meta.json` | 1097 | and __rep2 |
| preserved | `exec/results/p0perf-20260911/cells/ingested-qwen-3-4b-instruct-2507-tp4__on__rep2/perf.json` | `artifacts/intel-amx/exec/results/p0perf-20260911/cells/ingested-qwen-3-4b-instruct-2507-tp4__on__rep2/perf.json` | 3081 | and __rep2 |
| preserved | `exec/results/p0perf-20260911/cells/ingested-qwen-3-4b-instruct-2507-tp4__on__rep2/proof.txt` | `artifacts/intel-amx/exec/results/p0perf-20260911/cells/ingested-qwen-3-4b-instruct-2507-tp4__on__rep2/proof.txt` | 863 | adjacency |
| preserved | `exec/results/p0perf-20260911/ci-reference-20260911.json` | `artifacts/intel-amx/exec/results/p0perf-20260911/ci-reference-20260911.json` | 7450 | perf.ingested-qwen-3-4b-instruct-2507-tp2 |
| preserved | `exec/results/p0perf-20260911/rt-results.txt` | `artifacts/intel-amx/exec/results/p0perf-20260911/rt-results.txt` | 80886 |  |
| preserved | `exec/results/p0perf-20260911/summary.json` | `artifacts/intel-amx/exec/results/p0perf-20260911/summary.json` | 18327 |  |
| preserved | `exec/results/p0perf-20260911/summary.md` | `artifacts/intel-amx/exec/results/p0perf-20260911/summary.md` | 8565 |  |
| preserved | `exec/results/p0perf-20260913/build.txt` | `artifacts/intel-amx/exec/results/p0perf-20260913/build.txt` | 485 |  |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__fpga__rep1/meta.json` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__fpga__rep1/meta.json` | 1740 | and __rep2, __rep3 |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__fpga__rep1/perf-e0.json` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__fpga__rep1/perf-e0.json` | 1242 | and __rep2, __rep3 |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__fpga__rep1/perf-e1.json` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__fpga__rep1/perf-e1.json` | 1243 | and __rep2, __rep3 |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__fpga__rep1/perf.json` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__fpga__rep1/perf.json` | 2397 | and __rep2, __rep3 |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__fpga__rep1/proof.txt` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__fpga__rep1/proof.txt` | 1936 | and __rep2, __rep3 |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__fpga__rep2/meta.json` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__fpga__rep2/meta.json` | 1740 | and __rep2, __rep3 |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__fpga__rep2/perf-e0.json` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__fpga__rep2/perf-e0.json` | 1241 | and __rep2, __rep3 |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__fpga__rep2/perf-e1.json` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__fpga__rep2/perf-e1.json` | 1246 | and __rep2, __rep3 |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__fpga__rep2/perf.json` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__fpga__rep2/perf.json` | 2400 | and __rep2, __rep3 |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__fpga__rep2/proof.txt` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__fpga__rep2/proof.txt` | 1936 | and __rep2, __rep3 |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__fpga__rep3/meta.json` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__fpga__rep3/meta.json` | 1740 | and __rep2, __rep3 |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__fpga__rep3/perf-e0.json` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__fpga__rep3/perf-e0.json` | 1243 | and __rep2, __rep3 |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__fpga__rep3/perf-e1.json` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__fpga__rep3/perf-e1.json` | 1246 | and __rep2, __rep3 |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__fpga__rep3/perf.json` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__fpga__rep3/perf.json` | 2402 | and __rep2, __rep3 |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__fpga__rep3/proof.txt` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__fpga__rep3/proof.txt` | 1912 | and __rep2, __rep3 |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__off__rep1/meta.json` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__off__rep1/meta.json` | 1733 | and __rep2, __rep3 |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__off__rep1/perf-e0.json` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__off__rep1/perf-e0.json` | 1246 | and __rep2, __rep3 |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__off__rep1/perf-e1.json` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__off__rep1/perf-e1.json` | 1245 | and __rep2, __rep3 |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__off__rep1/perf.json` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__off__rep1/perf.json` | 2405 | and __rep2, __rep3 |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__off__rep1/proof.txt` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__off__rep1/proof.txt` | 1610 | and __rep2, __rep3 |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__off__rep2/meta.json` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__off__rep2/meta.json` | 1733 | and __rep2, __rep3 |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__off__rep2/perf-e0.json` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__off__rep2/perf-e0.json` | 1245 | and __rep2, __rep3 |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__off__rep2/perf-e1.json` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__off__rep2/perf-e1.json` | 1242 | and __rep2, __rep3 |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__off__rep2/perf.json` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__off__rep2/perf.json` | 2401 | and __rep2, __rep3 |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__off__rep2/proof.txt` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__off__rep2/proof.txt` | 1610 | and __rep2, __rep3 |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__off__rep3/meta.json` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__off__rep3/meta.json` | 1733 | and __rep2, __rep3 |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__off__rep3/perf-e0.json` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__off__rep3/perf-e0.json` | 1244 | and __rep2, __rep3 |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__off__rep3/perf-e1.json` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__off__rep3/perf-e1.json` | 1246 | and __rep2, __rep3 |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__off__rep3/perf.json` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__off__rep3/perf.json` | 2405 | and __rep2, __rep3 |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__off__rep3/proof.txt` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__off__rep3/proof.txt` | 1592 | and __rep2, __rep3 |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__on__rep1/meta.json` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__on__rep1/meta.json` | 1738 | and __rep2, __rep3 |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__on__rep1/perf-e0.json` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__on__rep1/perf-e0.json` | 1248 | and __rep2, __rep3 |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__on__rep1/perf-e1.json` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__on__rep1/perf-e1.json` | 1247 | and __rep2, __rep3 |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__on__rep1/perf.json` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__on__rep1/perf.json` | 2411 | and __rep2, __rep3 |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__on__rep1/proof.txt` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__on__rep1/proof.txt` | 1604 | adjacency |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__on__rep2/meta.json` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__on__rep2/meta.json` | 1738 | and __rep2, __rep3 |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__on__rep2/perf-e0.json` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__on__rep2/perf-e0.json` | 1244 | and __rep2, __rep3 |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__on__rep2/perf-e1.json` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__on__rep2/perf-e1.json` | 1240 | and __rep2, __rep3 |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__on__rep2/perf.json` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__on__rep2/perf.json` | 2396 | and __rep2, __rep3 |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__on__rep2/proof.txt` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__on__rep2/proof.txt` | 1616 | adjacency |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__on__rep3/meta.json` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__on__rep3/meta.json` | 1738 | and __rep2, __rep3 |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__on__rep3/perf-e0.json` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__on__rep3/perf-e0.json` | 1246 | and __rep2, __rep3 |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__on__rep3/perf-e1.json` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__on__rep3/perf-e1.json` | 1245 | and __rep2, __rep3 |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__on__rep3/perf.json` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__on__rep3/perf.json` | 2405 | and __rep2, __rep3 |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__on__rep3/proof.txt` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__on__rep3/proof.txt` | 1604 | adjacency |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__fpga__rep1/meta.json` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__fpga__rep1/meta.json` | 1547 | and __rep2, __rep3 |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__fpga__rep1/perf-e0.json` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__fpga__rep1/perf-e0.json` | 1865 | and __rep2, __rep3 |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__fpga__rep1/perf.json` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__fpga__rep1/perf.json` | 2169 | and __rep2, __rep3 |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__fpga__rep1/proof.txt` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__fpga__rep1/proof.txt` | 1064 | adjacency |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__fpga__rep2/meta.json` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__fpga__rep2/meta.json` | 1547 | and __rep2, __rep3 |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__fpga__rep2/perf-e0.json` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__fpga__rep2/perf-e0.json` | 1849 | and __rep2, __rep3 |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__fpga__rep2/perf.json` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__fpga__rep2/perf.json` | 2150 | and __rep2, __rep3 |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__fpga__rep2/proof.txt` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__fpga__rep2/proof.txt` | 1058 | adjacency |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__fpga__rep3/meta.json` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__fpga__rep3/meta.json` | 1547 | and __rep2, __rep3 |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__fpga__rep3/perf-e0.json` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__fpga__rep3/perf-e0.json` | 1853 | and __rep2, __rep3 |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__fpga__rep3/perf.json` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__fpga__rep3/perf.json` | 2156 | and __rep2, __rep3 |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__fpga__rep3/proof.txt` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__fpga__rep3/proof.txt` | 1052 | adjacency |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__off__rep1/meta.json` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__off__rep1/meta.json` | 1540 | and __rep2, __rep3 |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__off__rep1/perf-e0.json` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__off__rep1/perf-e0.json` | 1878 | and __rep2, __rep3 |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__off__rep1/perf.json` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__off__rep1/perf.json` | 2182 | and __rep2, __rep3 |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__off__rep1/proof.txt` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__off__rep1/proof.txt` | 898 | adjacency |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__off__rep2/meta.json` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__off__rep2/meta.json` | 1540 | and __rep2, __rep3 |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__off__rep2/perf-e0.json` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__off__rep2/perf-e0.json` | 1885 | and __rep2, __rep3 |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__off__rep2/perf.json` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__off__rep2/perf.json` | 2188 | and __rep2, __rep3 |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__off__rep2/proof.txt` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__off__rep2/proof.txt` | 898 | adjacency |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__off__rep3/meta.json` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__off__rep3/meta.json` | 1540 | and __rep2, __rep3 |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__off__rep3/perf-e0.json` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__off__rep3/perf-e0.json` | 1882 | and __rep2, __rep3 |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__off__rep3/perf.json` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__off__rep3/perf.json` | 2187 | and __rep2, __rep3 |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__off__rep3/proof.txt` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__off__rep3/proof.txt` | 898 | adjacency |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__on__rep1/meta.json` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__on__rep1/meta.json` | 1545 | and __rep2, __rep3 |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__on__rep1/perf-e0.json` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__on__rep1/perf-e0.json` | 1861 | and __rep2, __rep3 |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__on__rep1/perf.json` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__on__rep1/perf.json` | 2165 | and __rep2, __rep3 |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__on__rep1/proof.txt` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__on__rep1/proof.txt` | 898 | and __rep2, __rep3 |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__on__rep2/meta.json` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__on__rep2/meta.json` | 1545 | and __rep2, __rep3 |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__on__rep2/perf-e0.json` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__on__rep2/perf-e0.json` | 1860 | and __rep2, __rep3 |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__on__rep2/perf.json` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__on__rep2/perf.json` | 2162 | and __rep2, __rep3 |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__on__rep2/proof.txt` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__on__rep2/proof.txt` | 886 | and __rep2, __rep3 |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__on__rep3/meta.json` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__on__rep3/meta.json` | 1545 | and __rep2, __rep3 |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__on__rep3/perf-e0.json` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__on__rep3/perf-e0.json` | 1863 | and __rep2, __rep3 |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__on__rep3/perf.json` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__on__rep3/perf.json` | 2166 | and __rep2, __rep3 |
| preserved | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__on__rep3/proof.txt` | `artifacts/intel-amx/exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__on__rep3/proof.txt` | 892 | and __rep2, __rep3 |
| preserved | `exec/results/p0perf-20260913/rt-results.txt` | `artifacts/intel-amx/exec/results/p0perf-20260913/rt-results.txt` | 80108 |  |
| preserved | `exec/results/p0perf-20260913/summary.json` | `artifacts/intel-amx/exec/results/p0perf-20260913/summary.json` | 32975 |  |
| preserved | `exec/results/qwen8u8k-pr1-20260907T1904.txt` | `artifacts/intel-amx/exec/results/qwen8u8k-pr1-20260907T1904.txt` | 17943 | header, placement, binary sha256 |
| preserved | `exec/results/qwen8u8k-pr1-half-20260907T1904.txt` | `artifacts/intel-amx/exec/results/qwen8u8k-pr1-half-20260907T1904.txt` | 18212 | header, placement, binary sha256 |
| preserved | `exec/results/qwen8u8k-pr1-half-20260909T1704.txt` | `artifacts/intel-amx/exec/results/qwen8u8k-pr1-half-20260909T1704.txt` | 18077 | header, placement, binary sha256 |
| preserved | `exec/results/t4/cap-canonical-amx-u16.log` | `artifacts/intel-amx/exec/results/t4/cap-canonical-amx-u16.log` | 34458 | 32 measured lines; compact texts: ['t1-ext.txt', 't4-reps.txt', 't4-shapes.txt', 'cap-sweep.txt', 'cap-over.txt', 't4-suite.txt', 'p2-inc3-arena.txt'] |
| preserved | `exec/results/t4/cap-canonical-amx-u24.log` | `artifacts/intel-amx/exec/results/t4/cap-canonical-amx-u24.log` | 170283 | 48 measured lines; compact texts: ['t1-ext.txt', 't4-reps.txt', 't4-shapes.txt', 'cap-sweep.txt', 'cap-over.txt', 't4-suite.txt', 'p2-inc3-arena.txt'] |
| preserved | `exec/results/t4/cap-mirror-amx-u16.log` | `artifacts/intel-amx/exec/results/t4/cap-mirror-amx-u16.log` | 290229 | 32 measured lines; compact texts: ['t1-ext.txt', 't4-reps.txt', 't4-shapes.txt', 'cap-sweep.txt', 'cap-over.txt', 't4-suite.txt', 'p2-inc3-arena.txt'] |
| preserved | `exec/results/t4/cap-mirror-amx-u24.log` | `artifacts/intel-amx/exec/results/t4/cap-mirror-amx-u24.log` | 172095 | 48 measured lines; compact texts: ['t1-ext.txt', 't4-reps.txt', 't4-shapes.txt', 'cap-sweep.txt', 'cap-over.txt', 't4-suite.txt', 'p2-inc3-arena.txt'] |
| preserved | `exec/results/t4/cap-over.txt` | `artifacts/intel-amx/exec/results/t4/cap-over.txt` | 2354 |  |
| preserved | `exec/results/t4/cap-sweep.txt` | `artifacts/intel-amx/exec/results/t4/cap-sweep.txt` | 1108 |  |
| preserved | `exec/results/t4/capover-arena-mirror.log` | `artifacts/intel-amx/exec/results/t4/capover-arena-mirror.log` | 373612 | 112 measured lines; compact texts: ['t1-ext.txt', 't4-reps.txt', 't4-shapes.txt', 'cap-sweep.txt', 'cap-over.txt', 't4-suite.txt', 'p2-inc3-arena.txt'] |
| preserved | `exec/results/t4/capover-canonical.log` | `artifacts/intel-amx/exec/results/t4/capover-canonical.log` | 373670 | 112 measured lines; compact texts: ['t1-ext.txt', 't4-reps.txt', 't4-shapes.txt', 'cap-sweep.txt', 'cap-over.txt', 't4-suite.txt', 'p2-inc3-arena.txt'] |
| preserved | `exec/results/t4/capover64-arena-mirror.log` | `artifacts/intel-amx/exec/results/t4/capover64-arena-mirror.log` | 383807 | 128 measured lines; compact texts: ['t1-ext.txt', 't4-reps.txt', 't4-shapes.txt', 'cap-sweep.txt', 'cap-over.txt', 't4-suite.txt', 'p2-inc3-arena.txt'] |
| preserved | `exec/results/t4/capover64-canonical.log` | `artifacts/intel-amx/exec/results/t4/capover64-canonical.log` | 383839 | 128 measured lines; compact texts: ['t1-ext.txt', 't4-reps.txt', 't4-shapes.txt', 'cap-sweep.txt', 'cap-over.txt', 't4-suite.txt', 'p2-inc3-arena.txt'] |
| preserved | `exec/results/t4/capsweep-arena-mirror-u32.log` | `artifacts/intel-amx/exec/results/t4/capsweep-arena-mirror-u32.log` | 321840 | 64 measured lines; compact texts: ['t1-ext.txt', 't4-reps.txt', 't4-shapes.txt', 'cap-sweep.txt', 'cap-over.txt', 't4-suite.txt', 'p2-inc3-arena.txt'] |
| preserved | `exec/results/t4/capsweep-arena-mirror-u48.log` | `artifacts/intel-amx/exec/results/t4/capsweep-arena-mirror-u48.log` | 371040 | 96 measured lines; compact texts: ['t1-ext.txt', 't4-reps.txt', 't4-shapes.txt', 'cap-sweep.txt', 'cap-over.txt', 't4-suite.txt', 'p2-inc3-arena.txt'] |
| preserved | `exec/results/t4/capsweep-canonical-u32.log` | `artifacts/intel-amx/exec/results/t4/capsweep-canonical-u32.log` | 238838 | 64 measured lines; compact texts: ['t1-ext.txt', 't4-reps.txt', 't4-shapes.txt', 'cap-sweep.txt', 'cap-over.txt', 't4-suite.txt', 'p2-inc3-arena.txt'] |
| preserved | `exec/results/t4/capsweep-canonical-u48.log` | `artifacts/intel-amx/exec/results/t4/capsweep-canonical-u48.log` | 362779 | 96 measured lines; compact texts: ['t1-ext.txt', 't4-reps.txt', 't4-shapes.txt', 'cap-sweep.txt', 'cap-over.txt', 't4-suite.txt', 'p2-inc3-arena.txt'] |
| preserved | `exec/results/t4/p2-inc3-arena.txt` | `artifacts/intel-amx/exec/results/t4/p2-inc3-arena.txt` | 34597 | header, sha256 |
| preserved | `exec/results/t4/power-canonical-amx.log` | `artifacts/intel-amx/exec/results/t4/power-canonical-amx.log` | 24695 | 16 measured lines; compact texts: ['t1-ext.txt', 't4-reps.txt', 't4-shapes.txt', 'cap-sweep.txt', 'cap-over.txt', 't4-suite.txt', 'p2-inc3-arena.txt'] |
| preserved | `exec/results/t4/power-clean.log` | `artifacts/intel-amx/exec/results/t4/power-clean.log` | 25089 | 16 measured lines; compact texts: ['t1-ext.txt', 't4-reps.txt', 't4-shapes.txt', 'cap-sweep.txt', 'cap-over.txt', 't4-suite.txt', 'p2-inc3-arena.txt'] |
| preserved | `exec/results/t4/power-mirror-amx.log` | `artifacts/intel-amx/exec/results/t4/power-mirror-amx.log` | 25629 | 16 measured lines; compact texts: ['t1-ext.txt', 't4-reps.txt', 't4-shapes.txt', 'cap-sweep.txt', 'cap-over.txt', 't4-suite.txt', 'p2-inc3-arena.txt'] |
| preserved | `exec/results/t4/power2-canonical-amx.log` | `artifacts/intel-amx/exec/results/t4/power2-canonical-amx.log` | 25083 | 16 measured lines; compact texts: ['t1-ext.txt', 't4-reps.txt', 't4-shapes.txt', 'cap-sweep.txt', 'cap-over.txt', 't4-suite.txt', 'p2-inc3-arena.txt'] |
| preserved | `exec/results/t4/power2-clean.log` | `artifacts/intel-amx/exec/results/t4/power2-clean.log` | 25093 | 16 measured lines; compact texts: ['t1-ext.txt', 't4-reps.txt', 't4-shapes.txt', 'cap-sweep.txt', 'cap-over.txt', 't4-suite.txt', 'p2-inc3-arena.txt'] |
| preserved | `exec/results/t4/power2-mirror-amx.log` | `artifacts/intel-amx/exec/results/t4/power2-mirror-amx.log` | 25631 | 16 measured lines; compact texts: ['t1-ext.txt', 't4-reps.txt', 't4-shapes.txt', 'cap-sweep.txt', 'cap-over.txt', 't4-suite.txt', 'p2-inc3-arena.txt'] |
| preserved | `exec/results/t4/t4-power.txt` | `artifacts/intel-amx/exec/results/t4/t4-power.txt` | 1294 |  |
| preserved | `exec/results/t4/t4-reps.txt` | `artifacts/intel-amx/exec/results/t4/t4-reps.txt` | 24897 | header, sha256s |
| preserved | `exec/results/t4/t4-shapes.txt` | `artifacts/intel-amx/exec/results/t4/t4-shapes.txt` | 23355 | header, sha256 |
| preserved | `exec/results/t4/t4-suite.txt` | `artifacts/intel-amx/exec/results/t4/t4-suite.txt` | 52580 | header, binary sha256s |
| preserved | `exec/results/vnnik-20260914/build.txt` | `artifacts/intel-amx/exec/results/vnnik-20260914/build.txt` | 748 |  |
| preserved | `exec/results/vnnik-20260914/mirror-vs-vnni-rows.json` | `artifacts/intel-amx/exec/results/vnnik-20260914/mirror-vs-vnni-rows.json` | 545679 |  |
| preserved | `exec/results/vnnik-20260914/rt-results.txt` | `artifacts/intel-amx/exec/results/vnnik-20260914/rt-results.txt` | 204559 | campaign header |
| preserved | `exec/results/vnnik-20260914/summary.json` | `artifacts/intel-amx/exec/results/vnnik-20260914/summary.json` | 64655 | n/tps_mean/tps_sd/ttft_mean_s/ttft_sd_s at lines 95-99 |
| preserved | `exec/results/vnnik-20260914/summary.md` | `artifacts/intel-amx/exec/results/vnnik-20260914/summary.md` | 3097 |  |
| preserved | `exec/results/vnnik-20260914/tests.txt` | `artifacts/intel-amx/exec/results/vnnik-20260914/tests.txt` | 476 | adjacency |
| left behind | `../ai-runs/systems_test/testlib/tps.py` | left behind (in git) | 22639 |  |
| left behind | `exec/ctxfill-20260901/run-ctxfill.sh` | already at `artifacts/intel-amx/exec/ctxfill-20260901/run-ctxfill.sh` | 7490 | pinned commit, cmake flags, runtron flags, prompt grid, arm  |
| left behind | `exec/ctxfill-20260901/run-ctxfill2.sh` | already at `artifacts/intel-amx/exec/ctxfill-20260901/run-ctxfill2.sh` | 7596 | reuses the ctxfill-20260901 binaries when present; same runt |
| left behind | `exec/fence-20260831/run-fence3.sh` | already at `artifacts/intel-amx/exec/fence-20260831/run-fence3.sh` | 3790 | arm-to-binary and env mapping, placement flags, grid 256/204 |
| left behind | `exec/g1-20260908/g1-campaign.sh` | already at `artifacts/intel-amx/exec/g1-20260908/g1-campaign.sh` | 30888 |  |
| left behind | `exec/g1-20260908/rz.sh` | already at `artifacts/intel-amx/exec/g1-20260908/rz.sh` | 7542 |  |
| left behind | `exec/logs/more-testing-r1.log` | left behind (provenance) | 14659 |  |
| left behind | `exec/more-testing-r1/run_cell.sh` | already at `artifacts/intel-amx/exec/more-testing-r1/run_cell.sh` | 4629 |  |
| left behind | `exec/more-testing-r1/rz.sh` | already at `artifacts/intel-amx/exec/more-testing-r1/rz.sh` | 4853 |  |
| left behind | `exec/more-testing-r1/st_perf.py` | already at `artifacts/intel-amx/exec/more-testing-r1/st_perf.py` | 3917 |  |
| left behind | `exec/p0perf-20260911/campaign.sh` | already at `artifacts/intel-amx/exec/p0perf-20260911/campaign.sh` | 24246 |  |
| left behind | `exec/p0perf-20260911/rz.sh` | already at `artifacts/intel-amx/exec/p0perf-20260911/rz.sh` | 7687 |  |
| left behind | `exec/p0perf-20260911/summarize.py` | already at `artifacts/intel-amx/exec/p0perf-20260911/summarize.py` | 10803 | TPS = mean of 'average tok/s', TTFT = max of 'Parsing the pr |
| left behind | `exec/p0perf-20260913/campaign.sh` | already at `artifacts/intel-amx/exec/p0perf-20260913/campaign.sh` | 30536 |  |
| left behind | `exec/p0perf-20260913/rz.sh` | already at `artifacts/intel-amx/exec/p0perf-20260913/rz.sh` | 10399 |  |
| left behind | `exec/p0perf-20260913/summarize.py` | already at `artifacts/intel-amx/exec/p0perf-20260913/summarize.py` | 14419 |  |
| left behind | `exec/p2-cap-over.sh` | already at `artifacts/intel-amx/exec/p2-cap-over.sh` | 1368 |  |
| left behind | `exec/p2-cap-sweep.sh` | already at `artifacts/intel-amx/exec/p2-cap-sweep.sh` | 1925 |  |
| left behind | `exec/p2-inc3-arena.sh` | already at `artifacts/intel-amx/exec/p2-inc3-arena.sh` | 2326 |  |
| left behind | `exec/p2-t4-morning.sh` | already at `artifacts/intel-amx/exec/p2-t4-morning.sh` | 5477 | model, placement, flags |
| left behind | `exec/p2-t4-power.sh` | already at `artifacts/intel-amx/exec/p2-t4-power.sh` | 1939 |  |
| left behind | `exec/p2-t4-reps.sh` | already at `artifacts/intel-amx/exec/p2-t4-reps.sh` | 2296 |  |
| left behind | `exec/p2-t4-shapes.sh` | already at `artifacts/intel-amx/exec/p2-t4-shapes.sh` | 1827 |  |
| left behind | `exec/perfstat-20260831/run-perfstat3.sh` | already at `artifacts/intel-amx/exec/perfstat-20260831/run-perfstat3.sh` | 8873 | fcanon build flags DISPATCH=ON K_MIRROR=OFF; RUNPATH note |
| left behind | `exec/results/ctxfill-20260901/ctxfill.txt` | already at `artifacts/intel-amx/amx-decode-boost-202608/ctxfill-20260901/ctxfill.txt` | 38146 | 8 cells, rep order; header line, Parsing line, Generating li |
| left behind | `exec/results/ctxfill-20260901/curve.json` | already at `artifacts/intel-amx/amx-decode-boost-202608/ctxfill-20260901/curve.json` | 372 |  |
| left behind | `exec/results/ctxfill2-20260901/ctxfill.txt` | already at `artifacts/intel-amx/amx-decode-boost-202608/ctxfill2-20260901/ctxfill.txt` | 21109 | 8 cells, rep order |
| left behind | `exec/results/ctxfill2-20260901/curve2.json` | already at `artifacts/intel-amx/amx-decode-boost-202608/ctxfill2-20260901/curve2.json` | 209 |  |
| left behind | `exec/results/fence3-20260901/fence.txt` | already at `artifacts/intel-amx/amx-decode-boost-202608/fence3-20260901/fence.txt` | 8368 | 2 cells, rep order |
| left behind | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__canon2__u8/perf.log` | left behind (provenance) | 11208 | 1 perf*.json beside |
| left behind | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__canon__u1/perf.log` | left behind (provenance) | 4400 | 1 perf*.json beside |
| left behind | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__canon__u2/perf.log` | left behind (provenance) | 5349 | 1 perf*.json beside |
| left behind | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__canon__u4/perf.log` | left behind (provenance) | 7329 | 1 perf*.json beside |
| left behind | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__canon__u8/perf.log` | left behind (provenance) | 11208 | 1 perf*.json beside |
| left behind | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__g1mirror__u8/perf.log` | left behind (provenance) | 11209 | 1 perf*.json beside |
| left behind | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__inplace__u1/perf.log` | left behind (provenance) | 4399 | 1 perf*.json beside |
| left behind | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__inplace__u2/perf.log` | left behind (provenance) | 5350 | 1 perf*.json beside |
| left behind | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__inplace__u4/perf.log` | left behind (provenance) | 7265 | 1 perf*.json beside |
| left behind | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__inplace__u8/perf.log` | left behind (provenance) | 11209 | 1 perf*.json beside |
| left behind | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__mirror__u1/perf.log` | left behind (provenance) | 4399 | 1 perf*.json beside |
| left behind | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__mirror__u2/perf.log` | left behind (provenance) | 5350 | 1 perf*.json beside |
| left behind | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__mirror__u4/perf.log` | left behind (provenance) | 7343 | 1 perf*.json beside |
| left behind | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__mirror__u8/perf.log` | left behind (provenance) | 11207 | 1 perf*.json beside |
| left behind | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__off__u8/perf.log` | left behind (provenance) | 11208 | 1 perf*.json beside |
| left behind | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__sonly__u1/perf.log` | left behind (provenance) | 4399 | 1 perf*.json beside |
| left behind | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__sonly__u2/perf.log` | left behind (provenance) | 5349 | 1 perf*.json beside |
| left behind | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__sonly__u4/perf.log` | left behind (provenance) | 7259 | 1 perf*.json beside |
| left behind | `exec/results/g1-20260908/cells/ingested-qwen-3-4b-instruct-2507-tp4__sonly__u8/perf.log` | left behind (provenance) | 11208 | 1 perf*.json beside |
| left behind | `exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__canon2__u8/perf.log` | left behind (provenance) | 11251 | 1 perf*.json beside |
| left behind | `exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__canon__u1/perf.log` | left behind (provenance) | 4441 | 1 perf*.json beside |
| left behind | `exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__canon__u2/perf.log` | left behind (provenance) | 5387 | 1 perf*.json beside |
| left behind | `exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__canon__u4/perf.log` | left behind (provenance) | 7383 | 1 perf*.json beside |
| left behind | `exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__canon__u8/perf.log` | left behind (provenance) | 11251 | 1 perf*.json beside |
| left behind | `exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__inplace__u1/rinzler.log` | left behind (provenance) | 20395 |  |
| left behind | `exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__inplace__u2/perf.log` | left behind (provenance) | 3132 | 0 perf*.json beside |
| left behind | `exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__inplace__u2/rinzler.log` | left behind (provenance) | 20534 |  |
| left behind | `exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__inplace__u4/perf.log` | left behind (provenance) | 3302 | 0 perf*.json beside |
| left behind | `exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__inplace__u4/rinzler.log` | left behind (provenance) | 20402 |  |
| left behind | `exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__inplace__u8/perf.log` | left behind (provenance) | 3642 | 0 perf*.json beside |
| left behind | `exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__inplace__u8/rinzler.log` | left behind (provenance) | 20778 |  |
| left behind | `exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__mirror__u1/perf.log` | left behind (provenance) | 4441 | 1 perf*.json beside |
| left behind | `exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__mirror__u2/perf.log` | left behind (provenance) | 5392 | 1 perf*.json beside |
| left behind | `exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__mirror__u4/perf.log` | left behind (provenance) | 7381 | 1 perf*.json beside |
| left behind | `exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__mirror__u8/perf.log` | left behind (provenance) | 11250 | 1 perf*.json beside |
| left behind | `exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__off__u8/perf.log` | left behind (provenance) | 11249 | 1 perf*.json beside |
| left behind | `exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__sonly__u1/rinzler.log` | left behind (provenance) | 20695 |  |
| left behind | `exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__sonly__u2/perf.log` | left behind (provenance) | 3132 | 0 perf*.json beside |
| left behind | `exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__sonly__u2/rinzler.log` | left behind (provenance) | 21360 |  |
| left behind | `exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__sonly__u4/perf.log` | left behind (provenance) | 3830 | 0 perf*.json beside |
| left behind | `exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__sonly__u4/rinzler.log` | left behind (provenance) | 21629 |  |
| left behind | `exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__sonly__u8/perf.log` | left behind (provenance) | 5226 | 0 perf*.json beside |
| left behind | `exec/results/g1-20260908/cells/llama-3.1-8b-instruct-good-tp2__sonly__u8/rinzler.log` | left behind (provenance) | 21626 |  |
| left behind | `exec/results/g1-20260908/runtron-g1canon-rep1-t0.log` | duplicate (held by exec/results/g1-20260908/runtron-8u8k.txt) | 25571 | 16 measured lines checked |
| left behind | `exec/results/g1-20260908/runtron-g1canon-rep2-t0.log` | duplicate (held by exec/results/g1-20260908/runtron-8u8k.txt) | 25450 | 16 measured lines checked |
| left behind | `exec/results/g1-20260908/runtron-g1kill-rep1-t0.log` | duplicate (held by exec/results/g1-20260908/runtron-8u8k.txt) | 25565 | 16 measured lines checked |
| left behind | `exec/results/g1-20260908/runtron-g1kill-rep2-t1.log` | duplicate (held by exec/results/g1-20260908/runtron-8u8k.txt) | 25424 | 16 measured lines checked |
| left behind | `exec/results/g1-20260908/runtron-g1mirror-rep1-t0.log` | duplicate (held by exec/results/g1-20260908/runtron-8u8k.txt) | 271632 | 16 measured lines checked |
| left behind | `exec/results/g1-20260908/runtron-g1mirror-rep2-t0.log` | duplicate (held by exec/results/g1-20260908/runtron-8u8k.txt) | 271629 | 16 measured lines checked |
| left behind | `exec/results/g1-20260908/runtron-inplace-rep1-t0.log` | duplicate (held by exec/results/g1-20260908/runtron-8u8k.txt) | 26137 | 16 measured lines checked |
| left behind | `exec/results/g1-20260908/runtron-inplace-rep2-t1.log` | duplicate (held by exec/results/g1-20260908/runtron-8u8k.txt) | 25749 | 16 measured lines checked |
| left behind | `exec/results/g1-20260908/runtron-sonly-rep1-t0.log` | duplicate (held by exec/results/g1-20260908/runtron-8u8k.txt) | 271634 | 16 measured lines checked |
| left behind | `exec/results/g1-20260908/runtron-sonly-rep2-t0.log` | duplicate (held by exec/results/g1-20260908/runtron-8u8k.txt) | 271625 | 16 measured lines checked |
| left behind | `exec/results/more-testing-r1/cells/ingested-gpt-oss-120b-tp4__canon/functional.xml` | left behind (provenance) | 4566 |  |
| left behind | `exec/results/more-testing-r1/cells/ingested-gpt-oss-120b-tp4__canon/rinzler.log` | left behind (provenance) | 30381 |  |
| left behind | `exec/results/more-testing-r1/cells/ingested-gpt-oss-120b-tp4__mirror/functional.xml` | left behind (provenance) | 4566 |  |
| left behind | `exec/results/more-testing-r1/cells/ingested-gpt-oss-120b-tp4__mirror/rinzler.log` | left behind (provenance) | 930923 |  |
| left behind | `exec/results/more-testing-r1/cells/ingested-gpt-oss-120b-tp4__off/functional.xml` | left behind (provenance) | 4567 |  |
| left behind | `exec/results/more-testing-r1/cells/ingested-gpt-oss-120b-tp4__off/rinzler.log` | left behind (provenance) | 1136704 |  |
| left behind | `exec/results/more-testing-r1/cells/ingested-qwen-3-4b-instruct-2507-tp4__canon/functional.xml` | left behind (provenance) | 4382 |  |
| left behind | `exec/results/more-testing-r1/cells/ingested-qwen-3-4b-instruct-2507-tp4__canon/rinzler.log` | left behind (provenance) | 2516206 |  |
| left behind | `exec/results/more-testing-r1/cells/ingested-qwen-3-4b-instruct-2507-tp4__mirror/functional.xml` | left behind (provenance) | 4382 |  |
| left behind | `exec/results/more-testing-r1/cells/ingested-qwen-3-4b-instruct-2507-tp4__mirror/rinzler.log` | left behind (provenance) | 2408077 |  |
| left behind | `exec/results/more-testing-r1/cells/ingested-qwen-3-4b-instruct-2507-tp4__off/functional.xml` | left behind (provenance) | 4383 |  |
| left behind | `exec/results/more-testing-r1/cells/ingested-qwen-3-4b-instruct-2507-tp4__off/rinzler-amx-lines.txt` | left behind (provenance) | 2569 |  |
| left behind | `exec/results/more-testing-r1/cells/ingested-qwen-3-4b-instruct-2507-tp4__off/rinzler.log` | left behind (provenance) | 1428230 |  |
| left behind | `exec/results/more-testing-r1/cells/ingested-qwen-3-4b-instruct-2507-tp4__off__rep2/functional.xml` | left behind (provenance) | 4383 |  |
| left behind | `exec/results/more-testing-r1/cells/ingested-qwen-3-4b-instruct-2507-tp4__off__rep2/rinzler.log` | left behind (provenance) | 739827 |  |
| left behind | `exec/results/more-testing-r1/cells/llama-3.1-8b-instruct-good-tp2__canon/functional.xml` | left behind (provenance) | 4232 |  |
| left behind | `exec/results/more-testing-r1/cells/llama-3.1-8b-instruct-good-tp2__canon/rinzler.log` | left behind (provenance) | 24599 |  |
| left behind | `exec/results/more-testing-r1/cells/llama-3.1-8b-instruct-good-tp2__mirror/functional.xml` | left behind (provenance) | 4232 |  |
| left behind | `exec/results/more-testing-r1/cells/llama-3.1-8b-instruct-good-tp2__mirror/rinzler.log` | left behind (provenance) | 62737 |  |
| left behind | `exec/results/more-testing-r1/cells/llama-3.1-8b-instruct-good-tp2__off/functional.xml` | left behind (provenance) | 4232 |  |
| left behind | `exec/results/more-testing-r1/cells/llama-3.1-8b-instruct-good-tp2__off/rinzler.log` | left behind (provenance) | 49580 |  |
| left behind | `exec/results/more-testing-r1/cells/mixtral-8x7b-instruct-v0.1-tp2__canon/functional.xml` | left behind (provenance) | 4235 |  |
| left behind | `exec/results/more-testing-r1/cells/mixtral-8x7b-instruct-v0.1-tp2__canon/rinzler.log` | left behind (provenance) | 25712 |  |
| left behind | `exec/results/more-testing-r1/cells/mixtral-8x7b-instruct-v0.1-tp2__mirror/functional.xml` | left behind (provenance) | 4234 |  |
| left behind | `exec/results/more-testing-r1/cells/mixtral-8x7b-instruct-v0.1-tp2__mirror/rinzler.log` | left behind (provenance) | 49599 |  |
| left behind | `exec/results/more-testing-r1/cells/mixtral-8x7b-instruct-v0.1-tp2__off/functional.xml` | left behind (provenance) | 4235 |  |
| left behind | `exec/results/more-testing-r1/cells/mixtral-8x7b-instruct-v0.1-tp2__off/rinzler.log` | left behind (provenance) | 520453 |  |
| left behind | `exec/results/p0perf-20260911/cells/ingested-qwen-3-4b-instruct-2507-tp2__off__rep1/perf.log` | left behind (provenance) | 11208 | 1 perf*.json beside |
| left behind | `exec/results/p0perf-20260911/cells/ingested-qwen-3-4b-instruct-2507-tp2__off__rep2/perf.log` | left behind (provenance) | 11211 | 1 perf*.json beside |
| left behind | `exec/results/p0perf-20260911/cells/ingested-qwen-3-4b-instruct-2507-tp2__on__rep1/perf.log` | left behind (provenance) | 11208 | 1 perf*.json beside |
| left behind | `exec/results/p0perf-20260911/cells/ingested-qwen-3-4b-instruct-2507-tp2__on__rep2/perf.log` | left behind (provenance) | 11207 | 1 perf*.json beside |
| left behind | `exec/results/p0perf-20260911/cells/ingested-qwen-3-4b-instruct-2507-tp4__off__rep1/perf.log` | left behind (provenance) | 11207 | 1 perf*.json beside |
| left behind | `exec/results/p0perf-20260911/cells/ingested-qwen-3-4b-instruct-2507-tp4__off__rep2/perf.log` | left behind (provenance) | 11210 | 1 perf*.json beside |
| left behind | `exec/results/p0perf-20260911/cells/ingested-qwen-3-4b-instruct-2507-tp4__on__rep1/perf.log` | left behind (provenance) | 11208 | 1 perf*.json beside |
| left behind | `exec/results/p0perf-20260911/cells/ingested-qwen-3-4b-instruct-2507-tp4__on__rep2/perf.log` | left behind (provenance) | 11208 | 1 perf*.json beside |
| left behind | `exec/results/p0perf-20260911/ci-run-34559196745.log` | left behind (size) | 5738515 |  |
| left behind | `exec/results/p0perf-20260911/rt/tp2__off__rep1.log` | duplicate (held by exec/results/p0perf-20260911/rt-results.txt) | 21099 | 16 measured lines checked |
| left behind | `exec/results/p0perf-20260911/rt/tp2__off__rep2.log` | duplicate (held by exec/results/p0perf-20260911/rt-results.txt) | 20983 | 15 measured lines checked |
| left behind | `exec/results/p0perf-20260911/rt/tp2__off__rep3.log` | duplicate (held by exec/results/p0perf-20260911/rt-results.txt) | 20856 | 15 measured lines checked |
| left behind | `exec/results/p0perf-20260911/rt/tp2__off__rep4.log` | duplicate (held by exec/results/p0perf-20260911/rt-results.txt) | 20992 | 15 measured lines checked |
| left behind | `exec/results/p0perf-20260911/rt/tp2__off__rep5.log` | duplicate (held by exec/results/p0perf-20260911/rt-results.txt) | 20839 | 15 measured lines checked |
| left behind | `exec/results/p0perf-20260911/rt/tp2__off__rep6.log` | duplicate (held by exec/results/p0perf-20260911/rt-results.txt) | 20991 | 15 measured lines checked |
| left behind | `exec/results/p0perf-20260911/rt/tp2__on__rep1.log` | duplicate (held by exec/results/p0perf-20260911/rt-results.txt) | 20993 | 16 measured lines checked |
| left behind | `exec/results/p0perf-20260911/rt/tp2__on__rep2.log` | duplicate (held by exec/results/p0perf-20260911/rt-results.txt) | 20990 | 16 measured lines checked |
| left behind | `exec/results/p0perf-20260911/rt/tp2__on__rep3.log` | duplicate (held by exec/results/p0perf-20260911/rt-results.txt) | 20998 | 16 measured lines checked |
| left behind | `exec/results/p0perf-20260911/rt/tp2__on__rep4.log` | duplicate (held by exec/results/p0perf-20260911/rt-results.txt) | 20855 | 16 measured lines checked |
| left behind | `exec/results/p0perf-20260911/rt/tp2__on__rep5.log` | duplicate (held by exec/results/p0perf-20260911/rt-results.txt) | 20991 | 16 measured lines checked |
| left behind | `exec/results/p0perf-20260911/rt/tp2__on__rep6.log` | duplicate (held by exec/results/p0perf-20260911/rt-results.txt) | 20853 | 16 measured lines checked |
| left behind | `exec/results/p0perf-20260911/rt/tp4__off__rep1.log` | duplicate (held by exec/results/p0perf-20260911/rt-results.txt) | 30020 | 16 measured lines checked |
| left behind | `exec/results/p0perf-20260911/rt/tp4__off__rep2.log` | duplicate (held by exec/results/p0perf-20260911/rt-results.txt) | 29905 | 16 measured lines checked |
| left behind | `exec/results/p0perf-20260911/rt/tp4__off__rep3.log` | duplicate (held by exec/results/p0perf-20260911/rt-results.txt) | 29899 | 16 measured lines checked |
| left behind | `exec/results/p0perf-20260911/rt/tp4__off__rep4.log` | duplicate (held by exec/results/p0perf-20260911/rt-results.txt) | 29717 | 16 measured lines checked |
| left behind | `exec/results/p0perf-20260911/rt/tp4__off__rep5.log` | duplicate (held by exec/results/p0perf-20260911/rt-results.txt) | 29910 | 16 measured lines checked |
| left behind | `exec/results/p0perf-20260911/rt/tp4__off__rep6.log` | duplicate (held by exec/results/p0perf-20260911/rt-results.txt) | 29906 | 16 measured lines checked |
| left behind | `exec/results/p0perf-20260911/rt/tp4__on__rep1.log` | duplicate (held by exec/results/p0perf-20260911/rt-results.txt) | 29909 | 16 measured lines checked |
| left behind | `exec/results/p0perf-20260911/rt/tp4__on__rep2.log` | duplicate (held by exec/results/p0perf-20260911/rt-results.txt) | 29896 | 16 measured lines checked |
| left behind | `exec/results/p0perf-20260911/rt/tp4__on__rep3.log` | duplicate (held by exec/results/p0perf-20260911/rt-results.txt) | 29901 | 16 measured lines checked |
| left behind | `exec/results/p0perf-20260911/rt/tp4__on__rep4.log` | duplicate (held by exec/results/p0perf-20260911/rt-results.txt) | 29903 | 16 measured lines checked |
| left behind | `exec/results/p0perf-20260911/rt/tp4__on__rep5.log` | duplicate (held by exec/results/p0perf-20260911/rt-results.txt) | 29735 | 16 measured lines checked |
| left behind | `exec/results/p0perf-20260911/rt/tp4__on__rep6.log` | duplicate (held by exec/results/p0perf-20260911/rt-results.txt) | 29713 | 16 measured lines checked |
| left behind | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__fpga__rep1/perf-e0.log` | left behind (provenance) | 5649 | 3 perf*.json beside |
| left behind | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__fpga__rep1/perf-e1.log` | left behind (provenance) | 5352 | 3 perf*.json beside |
| left behind | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__fpga__rep2/perf-e0.log` | left behind (provenance) | 5349 | 3 perf*.json beside |
| left behind | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__fpga__rep2/perf-e1.log` | left behind (provenance) | 5349 | 3 perf*.json beside |
| left behind | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__fpga__rep3/perf-e0.log` | left behind (provenance) | 5349 | 3 perf*.json beside |
| left behind | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__fpga__rep3/perf-e1.log` | left behind (provenance) | 5347 | 3 perf*.json beside |
| left behind | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__off__rep1/perf-e0.log` | left behind (provenance) | 5389 | 3 perf*.json beside |
| left behind | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__off__rep1/perf-e1.log` | left behind (provenance) | 5390 | 3 perf*.json beside |
| left behind | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__off__rep2/perf-e0.log` | left behind (provenance) | 5389 | 3 perf*.json beside |
| left behind | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__off__rep2/perf-e1.log` | left behind (provenance) | 5694 | 3 perf*.json beside |
| left behind | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__off__rep3/perf-e0.log` | left behind (provenance) | 5391 | 3 perf*.json beside |
| left behind | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__off__rep3/perf-e1.log` | left behind (provenance) | 5388 | 3 perf*.json beside |
| left behind | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__on__rep1/perf-e0.log` | left behind (provenance) | 5392 | 3 perf*.json beside |
| left behind | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__on__rep1/perf-e1.log` | left behind (provenance) | 5389 | 3 perf*.json beside |
| left behind | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__on__rep2/perf-e0.log` | left behind (provenance) | 5689 | 3 perf*.json beside |
| left behind | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__on__rep2/perf-e1.log` | left behind (provenance) | 5390 | 3 perf*.json beside |
| left behind | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__on__rep3/perf-e0.log` | left behind (provenance) | 5389 | 3 perf*.json beside |
| left behind | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp2__on__rep3/perf-e1.log` | left behind (provenance) | 5387 | 3 perf*.json beside |
| left behind | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__fpga__rep1/perf-e0.log` | left behind (provenance) | 7249 | 2 perf*.json beside |
| left behind | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__fpga__rep2/perf-e0.log` | left behind (provenance) | 7248 | 2 perf*.json beside |
| left behind | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__fpga__rep3/perf-e0.log` | left behind (provenance) | 7555 | 2 perf*.json beside |
| left behind | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__off__rep1/perf-e0.log` | left behind (provenance) | 7330 | 2 perf*.json beside |
| left behind | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__off__rep2/perf-e0.log` | left behind (provenance) | 7331 | 2 perf*.json beside |
| left behind | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__off__rep3/perf-e0.log` | left behind (provenance) | 7329 | 2 perf*.json beside |
| left behind | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__on__rep1/perf-e0.log` | left behind (provenance) | 7574 | 2 perf*.json beside |
| left behind | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__on__rep2/perf-e0.log` | left behind (provenance) | 7299 | 2 perf*.json beside |
| left behind | `exec/results/p0perf-20260913/cells/ingested-qwen-3-4b-instruct-2507-tp4__on__rep3/perf-e0.log` | left behind (provenance) | 7334 | 2 perf*.json beside |
| left behind | `exec/results/p0perf-20260913/platformd-instance-1.env.txt` | already at `artifacts/intel-amx/exec/results/p0perf-20260913/platformd-instance-1.env.txt` | 1622 |  |
| left behind | `exec/results/p0perf-20260913/rt/tp2__off__rep1.log` | duplicate (held by exec/results/p0perf-20260913/rt-results.txt) | 21126 | 16 measured lines checked |
| left behind | `exec/results/p0perf-20260913/rt/tp2__off__rep2.log` | duplicate (held by exec/results/p0perf-20260913/rt-results.txt) | 21003 | 16 measured lines checked |
| left behind | `exec/results/p0perf-20260913/rt/tp2__off__rep3.log` | duplicate (held by exec/results/p0perf-20260913/rt-results.txt) | 20996 | 16 measured lines checked |
| left behind | `exec/results/p0perf-20260913/rt/tp2__off__rep4.log` | duplicate (held by exec/results/p0perf-20260913/rt-results.txt) | 21008 | 16 measured lines checked |
| left behind | `exec/results/p0perf-20260913/rt/tp2__off__rep5.log` | duplicate (held by exec/results/p0perf-20260913/rt-results.txt) | 20998 | 16 measured lines checked |
| left behind | `exec/results/p0perf-20260913/rt/tp2__off__rep6.log` | duplicate (held by exec/results/p0perf-20260913/rt-results.txt) | 20999 | 16 measured lines checked |
| left behind | `exec/results/p0perf-20260913/rt/tp2__on__rep1.log` | duplicate (held by exec/results/p0perf-20260913/rt-results.txt) | 21006 | 16 measured lines checked |
| left behind | `exec/results/p0perf-20260913/rt/tp2__on__rep2.log` | duplicate (held by exec/results/p0perf-20260913/rt-results.txt) | 21001 | 16 measured lines checked |
| left behind | `exec/results/p0perf-20260913/rt/tp2__on__rep3.log` | duplicate (held by exec/results/p0perf-20260913/rt-results.txt) | 20862 | 16 measured lines checked |
| left behind | `exec/results/p0perf-20260913/rt/tp2__on__rep4.log` | duplicate (held by exec/results/p0perf-20260913/rt-results.txt) | 20997 | 16 measured lines checked |
| left behind | `exec/results/p0perf-20260913/rt/tp2__on__rep5.log` | duplicate (held by exec/results/p0perf-20260913/rt-results.txt) | 21003 | 16 measured lines checked |
| left behind | `exec/results/p0perf-20260913/rt/tp2__on__rep6.log` | duplicate (held by exec/results/p0perf-20260913/rt-results.txt) | 21005 | 16 measured lines checked |
| left behind | `exec/results/p0perf-20260913/rt/tp4__off__rep1.log` | duplicate (held by exec/results/p0perf-20260913/rt-results.txt) | 30032 | 16 measured lines checked |
| left behind | `exec/results/p0perf-20260913/rt/tp4__off__rep2.log` | duplicate (held by exec/results/p0perf-20260913/rt-results.txt) | 29735 | 16 measured lines checked |
| left behind | `exec/results/p0perf-20260913/rt/tp4__off__rep3.log` | duplicate (held by exec/results/p0perf-20260913/rt-results.txt) | 29567 | 16 measured lines checked |
| left behind | `exec/results/p0perf-20260913/rt/tp4__off__rep4.log` | duplicate (held by exec/results/p0perf-20260913/rt-results.txt) | 29736 | 16 measured lines checked |
| left behind | `exec/results/p0perf-20260913/rt/tp4__off__rep5.log` | duplicate (held by exec/results/p0perf-20260913/rt-results.txt) | 29921 | 16 measured lines checked |
| left behind | `exec/results/p0perf-20260913/rt/tp4__off__rep6.log` | duplicate (held by exec/results/p0perf-20260913/rt-results.txt) | 29738 | 16 measured lines checked |
| left behind | `exec/results/p0perf-20260913/rt/tp4__on__rep1.log` | duplicate (held by exec/results/p0perf-20260913/rt-results.txt) | 29905 | 16 measured lines checked |
| left behind | `exec/results/p0perf-20260913/rt/tp4__on__rep2.log` | duplicate (held by exec/results/p0perf-20260913/rt-results.txt) | 29727 | 16 measured lines checked |
| left behind | `exec/results/p0perf-20260913/rt/tp4__on__rep3.log` | duplicate (held by exec/results/p0perf-20260913/rt-results.txt) | 29910 | 16 measured lines checked |
| left behind | `exec/results/p0perf-20260913/rt/tp4__on__rep4.log` | duplicate (held by exec/results/p0perf-20260913/rt-results.txt) | 29915 | 16 measured lines checked |
| left behind | `exec/results/p0perf-20260913/rt/tp4__on__rep5.log` | duplicate (held by exec/results/p0perf-20260913/rt-results.txt) | 29914 | 16 measured lines checked |
| left behind | `exec/results/p0perf-20260913/rt/tp4__on__rep6.log` | duplicate (held by exec/results/p0perf-20260913/rt-results.txt) | 29913 | 16 measured lines checked |
| left behind | `exec/results/p0perf-20260913/summary.md` | already at `artifacts/intel-amx/exec/results/p0perf-20260913/summary.md` | 12522 |  |
| left behind | `exec/results/perf-round-20260825/perf-round.txt` | already at `artifacts/intel-amx/exec/results/perf-round-20260825/perf-round.txt` | 82837 |  |
| left behind | `exec/results/perf-round-20260830/perf-round-ext.txt` | already at `artifacts/intel-amx/exec/results/perf-round-20260830/perf-round-ext.txt` | 89641 |  |
| left behind | `exec/results/perf-round-20260830/perf-round.txt` | already at `artifacts/intel-amx/exec/results/perf-round-20260830/perf-round.txt` | 134951 |  |
| left behind | `exec/results/perfstat3-20260901/run-disable-core-r1.log` | left behind (provenance) | 62430 | Version lines of the same-sha256 binaries; K mirror footprin |
| left behind | `exec/results/perfstat3-20260901/run-fcanon-core-r1.log` | left behind (provenance) | 65744 | Version lines of the same-sha256 binaries; K mirror footprin |
| left behind | `exec/results/perfstat3-20260901/run-fmirror-core-r1.log` | left behind (provenance) | 66343 | Version lines of the same-sha256 binaries; K mirror footprin |
| left behind | `exec/results/vnnik-20260914/rt/tp2__p1024__base__rep1.log` | duplicate (held by exec/results/vnnik-20260914/rt-results.txt) | 20850 | 16 measured lines checked |
| left behind | `exec/results/vnnik-20260914/rt/tp2__p1024__base__rep2.log` | duplicate (held by exec/results/vnnik-20260914/rt-results.txt) | 20998 | 16 measured lines checked |
| left behind | `exec/results/vnnik-20260914/rt/tp2__p1024__base__rep3.log` | duplicate (held by exec/results/vnnik-20260914/rt-results.txt) | 20989 | 16 measured lines checked |
| left behind | `exec/results/vnnik-20260914/rt/tp2__p1024__off__rep1.log` | duplicate (held by exec/results/vnnik-20260914/rt-results.txt) | 20867 | 16 measured lines checked |
| left behind | `exec/results/vnnik-20260914/rt/tp2__p1024__off__rep2.log` | duplicate (held by exec/results/vnnik-20260914/rt-results.txt) | 21001 | 16 measured lines checked |
| left behind | `exec/results/vnnik-20260914/rt/tp2__p1024__off__rep3.log` | duplicate (held by exec/results/vnnik-20260914/rt-results.txt) | 20997 | 16 measured lines checked |
| left behind | `exec/results/vnnik-20260914/rt/tp2__p1024__vnni__rep1.log` | duplicate (held by exec/results/vnnik-20260914/rt-results.txt) | 20845 | 16 measured lines checked |
| left behind | `exec/results/vnnik-20260914/rt/tp2__p1024__vnni__rep2.log` | duplicate (held by exec/results/vnnik-20260914/rt-results.txt) | 20836 | 16 measured lines checked |
| left behind | `exec/results/vnnik-20260914/rt/tp2__p1024__vnni__rep3.log` | duplicate (held by exec/results/vnnik-20260914/rt-results.txt) | 20981 | 16 measured lines checked |
| left behind | `exec/results/vnnik-20260914/rt/tp2__p1024__vnnioff__rep1.log` | duplicate (held by exec/results/vnnik-20260914/rt-results.txt) | 20835 | 16 measured lines checked |
| left behind | `exec/results/vnnik-20260914/rt/tp2__p1024__vnnioff__rep2.log` | duplicate (held by exec/results/vnnik-20260914/rt-results.txt) | 20983 | 16 measured lines checked |
| left behind | `exec/results/vnnik-20260914/rt/tp2__p1024__vnnioff__rep3.log` | duplicate (held by exec/results/vnnik-20260914/rt-results.txt) | 20979 | 16 measured lines checked |
| left behind | `exec/results/vnnik-20260914/rt/tp2__p2048__base__rep1.log` | duplicate (held by exec/results/vnnik-20260914/rt-results.txt) | 21667 | 16 measured lines checked |
| left behind | `exec/results/vnnik-20260914/rt/tp2__p2048__base__rep2.log` | duplicate (held by exec/results/vnnik-20260914/rt-results.txt) | 21814 | 16 measured lines checked |
| left behind | `exec/results/vnnik-20260914/rt/tp2__p2048__base__rep3.log` | duplicate (held by exec/results/vnnik-20260914/rt-results.txt) | 21816 | 16 measured lines checked |
| left behind | `exec/results/vnnik-20260914/rt/tp2__p2048__off__rep1.log` | duplicate (held by exec/results/vnnik-20260914/rt-results.txt) | 21686 | 16 measured lines checked |
| left behind | `exec/results/vnnik-20260914/rt/tp2__p2048__off__rep2.log` | duplicate (held by exec/results/vnnik-20260914/rt-results.txt) | 21832 | 16 measured lines checked |
| left behind | `exec/results/vnnik-20260914/rt/tp2__p2048__off__rep3.log` | duplicate (held by exec/results/vnnik-20260914/rt-results.txt) | 21814 | 16 measured lines checked |
| left behind | `exec/results/vnnik-20260914/rt/tp2__p2048__vnni__rep1.log` | duplicate (held by exec/results/vnnik-20260914/rt-results.txt) | 21642 | 16 measured lines checked |
| left behind | `exec/results/vnnik-20260914/rt/tp2__p2048__vnni__rep2.log` | duplicate (held by exec/results/vnnik-20260914/rt-results.txt) | 21506 | 16 measured lines checked |
| left behind | `exec/results/vnnik-20260914/rt/tp2__p2048__vnni__rep3.log` | duplicate (held by exec/results/vnnik-20260914/rt-results.txt) | 21800 | 16 measured lines checked |
| left behind | `exec/results/vnnik-20260914/rt/tp2__p2048__vnnioff__rep1.log` | duplicate (held by exec/results/vnnik-20260914/rt-results.txt) | 21523 | 16 measured lines checked |
| left behind | `exec/results/vnnik-20260914/rt/tp2__p2048__vnnioff__rep2.log` | duplicate (held by exec/results/vnnik-20260914/rt-results.txt) | 21821 | 16 measured lines checked |
| left behind | `exec/results/vnnik-20260914/rt/tp2__p2048__vnnioff__rep3.log` | duplicate (held by exec/results/vnnik-20260914/rt-results.txt) | 267315 | 16 measured lines checked |
| left behind | `exec/results/vnnik-20260914/rt/tp2__p8192__base__rep1.log` | duplicate (held by exec/results/vnnik-20260914/rt-results.txt) | 25390 | 16 measured lines checked |
| left behind | `exec/results/vnnik-20260914/rt/tp2__p8192__base__rep2.log` | duplicate (held by exec/results/vnnik-20260914/rt-results.txt) | 25585 | 16 measured lines checked |
| left behind | `exec/results/vnnik-20260914/rt/tp2__p8192__base__rep3.log` | duplicate (held by exec/results/vnnik-20260914/rt-results.txt) | 25580 | 16 measured lines checked |
| left behind | `exec/results/vnnik-20260914/rt/tp2__p8192__off__rep1.log` | duplicate (held by exec/results/vnnik-20260914/rt-results.txt) | 25400 | 16 measured lines checked |
| left behind | `exec/results/vnnik-20260914/rt/tp2__p8192__off__rep2.log` | duplicate (held by exec/results/vnnik-20260914/rt-results.txt) | 25604 | 16 measured lines checked |
| left behind | `exec/results/vnnik-20260914/rt/tp2__p8192__off__rep3.log` | duplicate (held by exec/results/vnnik-20260914/rt-results.txt) | 25603 | 16 measured lines checked |
| left behind | `exec/results/vnnik-20260914/rt/tp2__p8192__vnni__rep1.log` | duplicate (held by exec/results/vnnik-20260914/rt-results.txt) | 25191 | 16 measured lines checked |
| left behind | `exec/results/vnnik-20260914/rt/tp2__p8192__vnni__rep2.log` | duplicate (held by exec/results/vnnik-20260914/rt-results.txt) | 25562 | 16 measured lines checked |
| left behind | `exec/results/vnnik-20260914/rt/tp2__p8192__vnni__rep3.log` | duplicate (held by exec/results/vnnik-20260914/rt-results.txt) | 25564 | 16 measured lines checked |
| left behind | `exec/results/vnnik-20260914/rt/tp2__p8192__vnnioff__rep1.log` | duplicate (held by exec/results/vnnik-20260914/rt-results.txt) | 25391 | 16 measured lines checked |
| left behind | `exec/results/vnnik-20260914/rt/tp2__p8192__vnnioff__rep2.log` | duplicate (held by exec/results/vnnik-20260914/rt-results.txt) | 25564 | 16 measured lines checked |
| left behind | `exec/results/vnnik-20260914/rt/tp2__p8192__vnnioff__rep3.log` | duplicate (held by exec/results/vnnik-20260914/rt-results.txt) | 25580 | 16 measured lines checked |
| left behind | `exec/results/vnnik-20260914/rt/tp4__p1024__base__rep1.log` | duplicate (held by exec/results/vnnik-20260914/rt-results.txt) | 29923 | 16 measured lines checked |
| left behind | `exec/results/vnnik-20260914/rt/tp4__p1024__base__rep2.log` | duplicate (held by exec/results/vnnik-20260914/rt-results.txt) | 29913 | 16 measured lines checked |
| left behind | `exec/results/vnnik-20260914/rt/tp4__p1024__off__rep1.log` | duplicate (held by exec/results/vnnik-20260914/rt-results.txt) | 29839 | 16 measured lines checked |
| left behind | `exec/results/vnnik-20260914/rt/tp4__p1024__off__rep2.log` | duplicate (held by exec/results/vnnik-20260914/rt-results.txt) | 29915 | 16 measured lines checked |
| left behind | `exec/results/vnnik-20260914/rt/tp4__p1024__vnni__rep1.log` | duplicate (held by exec/results/vnnik-20260914/rt-results.txt) | 30024 | 16 measured lines checked |
| left behind | `exec/results/vnnik-20260914/rt/tp4__p1024__vnni__rep2.log` | duplicate (held by exec/results/vnnik-20260914/rt-results.txt) | 29882 | 16 measured lines checked |
| left behind | `exec/results/vnnik-20260914/rt/tp4__p1024__vnnioff__rep1.log` | duplicate (held by exec/results/vnnik-20260914/rt-results.txt) | 29895 | 16 measured lines checked |
| left behind | `exec/results/vnnik-20260914/rt/tp4__p1024__vnnioff__rep2.log` | duplicate (held by exec/results/vnnik-20260914/rt-results.txt) | 29894 | 16 measured lines checked |
| left behind | `exec/results/vnnik-20260914/rt/tp4__p2048__base__rep1.log` | duplicate (held by exec/results/vnnik-20260914/rt-results.txt) | 30722 | 16 measured lines checked |
| left behind | `exec/results/vnnik-20260914/rt/tp4__p2048__base__rep2.log` | duplicate (held by exec/results/vnnik-20260914/rt-results.txt) | 30720 | 16 measured lines checked |
| left behind | `exec/results/vnnik-20260914/rt/tp4__p2048__off__rep1.log` | duplicate (held by exec/results/vnnik-20260914/rt-results.txt) | 30728 | 16 measured lines checked |
| left behind | `exec/results/vnnik-20260914/rt/tp4__p2048__off__rep2.log` | duplicate (held by exec/results/vnnik-20260914/rt-results.txt) | 30345 | 16 measured lines checked |
| left behind | `exec/results/vnnik-20260914/rt/tp4__p2048__vnni__rep1.log` | duplicate (held by exec/results/vnnik-20260914/rt-results.txt) | 30513 | 16 measured lines checked |
| left behind | `exec/results/vnnik-20260914/rt/tp4__p2048__vnni__rep2.log` | duplicate (held by exec/results/vnnik-20260914/rt-results.txt) | 30687 | 16 measured lines checked |
| left behind | `exec/results/vnnik-20260914/rt/tp4__p2048__vnnioff__rep1.log` | duplicate (held by exec/results/vnnik-20260914/rt-results.txt) | 30702 | 16 measured lines checked |
| left behind | `exec/results/vnnik-20260914/rt/tp4__p2048__vnnioff__rep2.log` | duplicate (held by exec/results/vnnik-20260914/rt-results.txt) | 30702 | 16 measured lines checked |
| left behind | `exec/results/vnnik-20260914/rt/tp4__p8192__base__rep1.log` | duplicate (held by exec/results/vnnik-20260914/rt-results.txt) | 34492 | 16 measured lines checked |
| left behind | `exec/results/vnnik-20260914/rt/tp4__p8192__base__rep2.log` | duplicate (held by exec/results/vnnik-20260914/rt-results.txt) | 34248 | 16 measured lines checked |
| left behind | `exec/results/vnnik-20260914/rt/tp4__p8192__off__rep1.log` | duplicate (held by exec/results/vnnik-20260914/rt-results.txt) | 34264 | 16 measured lines checked |
| left behind | `exec/results/vnnik-20260914/rt/tp4__p8192__off__rep2.log` | duplicate (held by exec/results/vnnik-20260914/rt-results.txt) | 34495 | 16 measured lines checked |
| left behind | `exec/results/vnnik-20260914/rt/tp4__p8192__vnni__rep1.log` | duplicate (held by exec/results/vnnik-20260914/rt-results.txt) | 34005 | 16 measured lines checked |
| left behind | `exec/results/vnnik-20260914/rt/tp4__p8192__vnni__rep2.log` | duplicate (held by exec/results/vnnik-20260914/rt-results.txt) | 34243 | 16 measured lines checked |
| left behind | `exec/results/vnnik-20260914/rt/tp4__p8192__vnnioff__rep1.log` | duplicate (held by exec/results/vnnik-20260914/rt-results.txt) | 34470 | 16 measured lines checked |
| left behind | `exec/results/vnnik-20260914/rt/tp4__p8192__vnnioff__rep2.log` | duplicate (held by exec/results/vnnik-20260914/rt-results.txt) | 279958 | 16 measured lines checked |
