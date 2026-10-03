#!/usr/bin/env python3
"""Fill the <<COUNTS>> and <<COUNTS_INLINE>> placeholders in the final-*.md
texts from the 3bda log of the faf8ee42ca build+test run, and split
final-replies.md into one file per reply (final-reply-b2.md .. b6.md).

Usage: python3 fill-counts.py <path to tron-issue4525-final.log copy>
Without the log (or with an incomplete one) it only splits the replies and
leaves the placeholders in place, and says so.
"""
import re, sys, pathlib
E = pathlib.Path(__file__).resolve().parent
TESTS = ['t_llama_unit', 't_amx_numerics', 't_amx_dispatch_dtype', 't_heterogeneous_scheduler']

def parse(log):
    # Blocks look like: "== run t_llama_unit (gen/t_llama_unit) ..." then
    # "== t_llama_unit gen rc=0 ..." then "test cases: N | ..." / "assertions: M | ...".
    counts = {}
    cur = None
    for line in log.splitlines():
        m = re.match(r'^== run (\S+) \((\S+)/\S+\)', line)
        if m: cur = (m.group(2), m.group(1)); continue
        m = re.match(r'^== (\S+) (\S+) rc=(\d+)', line)
        if m: counts.setdefault((m.group(2), m.group(1)), {})['rc'] = int(m.group(3)); continue
        m = re.match(r'^== run t_llama_unit case1', line)
        if m: cur = ('gen', 'packed-bits'); continue
        m = re.match(r'^== run t_llama_unit case2', line)
        if m: cur = ('gen', 'sliding-chunk'); continue
        m = re.match(r'^== case([12]) rc=(\d+)', line)
        if m: counts.setdefault(cur, {})['rc'] = int(m.group(2)); continue
        m = re.match(r'^test cases:\s*(\d+)', line)
        if m and cur: counts.setdefault(cur, {})['cases'] = int(m.group(1)); continue
        m = re.match(r'^assertions:\s*(\d+)', line)
        if m and cur: counts.setdefault(cur, {})['assertions'] = int(m.group(1)); continue
        m = re.match(r'^All tests passed \((\d+) assertions? in (\d+) test cases?\)', line)
        if m and cur:
            counts.setdefault(cur, {}).update(assertions=int(m.group(1)), cases=int(m.group(2)))
    return counts

def complete(c):
    return all((t, x) in c and 'assertions' in c[(t, x)] and c[(t, x)].get('rc') == 0
               for t in ('gen', 'gen-amxoff') for x in TESTS)

def table(c):
    rows = ['| Tree | Test | Result |', '|---|---|---|']
    for t in ('gen', 'gen-amxoff'):
        for x in TESTS:
            r = c[(t, x)]
            rows.append(f'| {t} | {x} | pass, {r["assertions"]} assertions / {r["cases"]} test cases |')
    if ('gen', 'packed-bits') in c and 'assertions' in c[('gen', 'packed-bits')]:
        rows.append(f'| gen | t_llama_unit, packed-bits case alone | pass, {c[("gen","packed-bits")]["assertions"]} assertions |')
    return '\n'.join(rows)

def inline(c):
    g, o = (lambda x: c[('gen', x)]), (lambda x: c[('gen-amxoff', x)])
    return (f'AMX-on tree t_llama_unit {g("t_llama_unit")["assertions"]} assertions / {g("t_llama_unit")["cases"]} cases, '
            f't_amx_numerics {g("t_amx_numerics")["assertions"]} assertions (real AMX), '
            f't_amx_dispatch_dtype {g("t_amx_dispatch_dtype")["assertions"]}, '
            f't_heterogeneous_scheduler {g("t_heterogeneous_scheduler")["assertions"]}, '
            f'and AMX-off tree t_llama_unit {o("t_llama_unit")["assertions"]} assertions / {o("t_llama_unit")["cases"]} cases, '
            f't_heterogeneous_scheduler {o("t_heterogeneous_scheduler")["assertions"]} '
            f'(the AMX cases of the other two tests are compiled out there: {o("t_amx_numerics")["assertions"]} and {o("t_amx_dispatch_dtype")["assertions"]} assertions)')

def split_replies():
    txt = (E / 'final-replies.md').read_text()
    parts = re.split(r'^## (B[2-6]), reply under (\d+)\n', txt, flags=re.M)
    for i in range(1, len(parts), 3):
        b, cid, body = parts[i], parts[i + 1], parts[i + 2].strip() + '\n'
        (E / f'final-reply-{b.lower()}.md').write_text(body)
        print(f'wrote final-reply-{b.lower()}.md (in_reply_to={cid}, {len(body.split())} words)')

c = {}
if len(sys.argv) > 1 and pathlib.Path(sys.argv[1]).exists():
    c = parse(pathlib.Path(sys.argv[1]).read_text())
if complete(c):
    for f in ('final-pr-body.md', 'final-replies.md', 'final-issue-4588-comment.md'):
        p = E / f
        s = p.read_text().replace('<<COUNTS>>', table(c)).replace('<<COUNTS_INLINE>>', inline(c))
        p.write_text(s)
    print('counts filled:', inline(c))
else:
    print('LOG INCOMPLETE OR MISSING: placeholders <<COUNTS>> / <<COUNTS_INLINE>> left in place')
split_replies()

