#!/usr/bin/env python3
"""Build the draft of the PR 5022 description for the head that holds the two commits of PR 5606.

Reads the saved live description, applies each replacement once, prints the word count after each step
(`wc -w` rule: words are split at white space), and writes the draft. Placeholders in capitals are filled
after the CI runs of the new head. Usage: apply_body.py LIVE.md OUT.md
"""
import sys

live, out = sys.argv[1:3]
s = open(live, encoding='utf-8').read()
REPL = [
 ('first Verification sentence',
  'Tests run at the head `ddf843ad97` on delphi-3b35, a Xeon 6962P host with AMX, on 2026-11-20 (`pr5022-final-20261119`).',
  'Tests run at the head `90a9110be5` on delphi-3b35, a Xeon 6962P host with AMX, on 2026-11-24 (`pr5606-check-20261123`).'),
 ('row of the default CI build',
  '| Both jobs pass. The AMX checks are compiled out. The transpose case runs. |',
  '| Both jobs pass. `t_amx_dispatch_dtype` and the transpose case run. Four `t_amx_numerics` cases are compiled out. |'),
 ('run link of the default CI build',
  'CI run [44777709823](https://github.com/positron-ai/tron/actions/runs/44777709823), jobs Build Tron and Test host',
  'CI run [RUN_ID_NIX](https://github.com/positron-ai/tron/actions/runs/RUN_ID_NIX), jobs Build Tron and Test host'),
 ('row of the CMake workflow',
  '| Run [44777748892](https://github.com/positron-ai/tron/actions/runs/44777748892), test-host on runner delphi-3bd6-0 (Xeon 6962P, attempt 2) | The build and both test jobs pass. test-host: 106 of 106 tests pass. |',
  '| Run [RUN_ID_CMAKE](https://github.com/positron-ai/tron/actions/runs/RUN_ID_CMAKE), test-host on runner RUNNER_NAME (Xeon CPU_MODEL, attempt ATTEMPT_N) | The build and both test jobs pass. test-host: N_PASS of N_TOTAL tests pass. |'),
 ('bullet about fake kernels',
  '- The dispatch tests use fake kernels. They and the transpose case do not require a CPU with AMX support.',
  '- The dispatch test uses fake kernels and passes `TRON_AMX_DISPATCH` itself. It and the transpose case need no AMX CPU.'),
 ('lint sentence (trim of one word)',
  'Clang-format 19.1.7 and `git diff --check` pass at the current head.',
  'Clang-format 19.1.7 and `git diff --check` pass at the head.'),
 ('Open items (only if the rows of config/test-benchmarks.json stay unchanged)',
  'Throughput at the head is not measured [Verification]. No other measurement is pending.',
  'Not measured at the head: throughput [Verification]. Not refreshed: the `config/test-benchmarks.json` rows of `t_amx_dispatch_dtype`.'),
]
n = len(s.split())
print(f'live description: {n} words')
for name, old, new in REPL:
    assert s.count(old) == 1, f'{name}: old text found {s.count(old)} times'
    s = s.replace(old, new)
    m = len(s.split())
    print(f'{name}: {m - n:+d} words, total {m}')
    n = m
assert n < 2000, n
open(out, 'w', encoding='utf-8').write(s)
print(f'draft written: {out}, {n} words')
