# Patch the LIVE PR 5015 body (re-fetched at run time): three edits for the round-3 head.
# Usage: python3 -I body_patch.py <head-sha> [--apply]
import json, subprocess, sys, pathlib
sha = sys.argv[1]; short = sha[:10]
apply = '--apply' in sys.argv
body = subprocess.run(['gh', 'pr', 'view', '5015', '--repo', 'positron-ai/tron', '--json', 'body', '--jq', '.body'],
                      check=True, capture_output=True, text=True).stdout
if body.endswith('\n'): body = body[:-1]
edits = [
# (1a) scope + define "our half" at its first use
("Every result below comes from head 5061623a34 (branch `jhan-amx-kvmul16`, base main 6198824246) on delphi-3bda, our half, on 2026-10-16 and 2026-10-17,",
 "Every result below except the test rows comes from head 5061623a34 (branch `jhan-amx-kvmul16`, base main 6198824246) on delphi-3bda, our half (one socket of the machine with 4 of its 8 FPGA cards), on 2026-10-16 and 2026-10-17,"),
# (1b) where the raw results live; the current head's kernels; where the test rows come from
("Raw results: rt-results.txt, attn-stats-compare.md, tests.txt and local-obj-compare/ (result set glimmer-20261016).",
 f"Raw results: rt-results.txt, attn-stats-compare.md, tests.txt and local-obj-compare/ (result set glimmer-20261016). The result sets named in this description are the author's files on delphi-3bda, not files in this repository. The current head {short} compiles the six kernel instantiations to the same instructions as 5061623a34 (clang 19.1.7 at -O3; the 16-head QK kernel has two adjacent address increments in the other order). Those results therefore hold for the current head. The test rows come from the current head, built on 2026-10-18 in the plain-shell tree of the token-identity section (clang 19.1.7, preset `native`, `-DTRON_AMX_DISPATCH=ON`)."),
# (2) AMX-on test row
("| AMX on | runtron, t_amx_numerics, t_amx_dispatch_dtype, t_llama_unit | t_amx_numerics 17,424 / 4 pass, t_amx_dispatch_dtype 5,756 / 1 pass, t_llama_unit 265,452 / 67 pass |",
 "| AMX on | runtron, t_amx_numerics, t_amx_dispatch_dtype, t_llama_unit | t_amx_numerics 17,425 / 4 pass, t_amx_dispatch_dtype 3,694 / 1 pass, t_llama_unit 265,452 / 67 pass |"),
# (3) kill-switch row: test cases, not sections; skipped, not passed
("| AMX off (kill switch) | same binaries | t_amx_numerics 4,110 / 4 pass, 2 sections skipped with \"AMX unavailable on this host\" (the precision checks need the kernel) |",
 "| AMX off (kill switch) | same binaries | t_amx_numerics 4,111 assertions pass, 2 of 4 test cases pass and 2 are skipped (the QK and PV precision checks are skipped with \"AMX unavailable on this host\", they need the kernel), exit code 0, t_amx_dispatch_dtype 3,694 / 1 pass (its fakes ignore the switch) |"),
# (4) the nightly comparator: repository, workflow, job, source line
("The nightly CI perf phase runs Glimmer tp4 with 8 users per machine on 2 engines of 4 cards, prompt 1024, 1,536 generated tokens.",
 "The nightly CI perf phase (repository positron-ai/systems_test, workflow \"System CI (Rinzler 72-core Intel system OCI version)\", job system_ci) runs Glimmer tp4 with 8 users per machine on 2 engines of 4 cards, prompt 1024, 1,536 generated tokens."),
("| nightly GitHub Actions run 38999609242 (2026-10-17) | 1 | 78.69 | - | 3697 | 277.0 |",
 "| nightly positron-ai/systems_test [run 38999609242](https://github.com/positron-ai/systems_test/actions/runs/38999609242) (2026-10-17), TPS and TTFT from the final `Running averages` line of its job log | 1 | 78.69 | - | 3696 | 277.0 |"),
]
new = body
for old, rep in edits:
    n = new.count(old)
    if n != 1:
        print(f'ANCHOR {n}x: {old[:70]}'); sys.exit(1)
    new = new.replace(old, rep)
out = pathlib.Path(__file__).with_name('pr-body-new.md'); out.write_text(new + '\n')
print('edits ok; words', len(new.split()), '->', out)
if apply:
    subprocess.run(['gh', 'pr', 'edit', '5015', '--repo', 'positron-ai/tron', '--body-file', str(out)], check=True)
    print('body updated')
