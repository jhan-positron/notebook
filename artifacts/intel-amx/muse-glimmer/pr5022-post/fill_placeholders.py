#!/usr/bin/env python3
"""Fill the placeholders of the review-round-2 texts of tron PR 5022.
Usage: fill_placeholders.py <values.json> [--write]
  values.json: {"HEAD": "...", "ISSUE": "...", "NIXRUN": "...", "CMAKERUN": "...", "RUNNER": "...", "CMAKERESULT": "..."}
  A key that is missing stays a placeholder. "<KEY>_BODY" gives the PR description its own value for <KEY>. Without --write the script only reports what it would change.
Targets:
  1. respond-2-Isaac.html: only inside the reply blocks (<div class="reply">). A run id becomes a link in prose and
     the markdown form of that link inside <pre> (a quoted row of the PR description).
  2. pr5022-body-round2.draft.md -> pr5022-body-round2.final.md (the draft keeps its placeholders).
"""
import html, json, re, sys
vals = json.load(open(sys.argv[1])); write = '--write' in sys.argv
PAGE = '/home/jhan/workspace/intel-AMX/muse-glimmer/respond-2-Isaac.html'
DRAFT = '/home/jhan/workspace/intel-AMX/muse-glimmer/pr5022-body-round2.draft.md'
FINAL = '/home/jhan/workspace/intel-AMX/muse-glimmer/pr5022-body-round2.final.md'
RUN_URL = 'https://github.com/positron-ai/tron/actions/runs/'
def md_value(key):
    v = vals[key]
    return f'[{v}]({RUN_URL}{v})' if key in ('NIXRUN', 'CMAKERUN') else v
def html_value(key, in_pre):
    v = vals[key]
    if key in ('NIXRUN', 'CMAKERUN'):
        return html.escape(md_value(key), quote=False) if in_pre else f'<a href="{RUN_URL}{v}">{v}</a>'
    return html.escape(v, quote=False)
def block_end(h, start):
    depth = 0
    for m in re.finditer(r'<div\b|</div>', h[start:]):
        depth += 1 if m.group(0) != '</div>' else -1
        if depth == 0: return start + m.end()
    raise SystemExit('unbalanced div')
# 1. the page
h = open(PAGE, encoding='utf-8').read(); out = []; pos = 0; n_page = 0
for m in re.finditer(r'<div class="reply"[^>]*>', h):
    s, e = m.start(), block_end(h, m.start())
    out.append(h[pos:s]); block = h[s:e]; pos = e
    parts = re.split(r'(<pre>.*?</pre>)', block, flags=re.S)
    for i, part in enumerate(parts):
        in_pre = part.startswith('<pre>')
        def sub(mm):
            global n_page
            k = mm.group(1)
            if k not in vals: return mm.group(0)
            n_page += 1; return html_value(k, in_pre)
        parts[i] = re.sub(r'⟦([A-Z]+)⟧', sub, part)
    out.append(''.join(parts))
out.append(h[pos:]); h2 = ''.join(out)
left_page = sorted(set(re.findall(r'⟦[A-Z]+⟧', ''.join(re.findall(r'<div class="reply".*?</div>\s*</div>', h2, re.S)))))
# 2. the PR description
d = open(DRAFT, encoding='utf-8').read(); n_body = 0
def subb(mm):
    global n_body
    k = mm.group(1)
    if k + '_BODY' in vals:              # a shorter form for the PR description
        n_body += 1; return vals[k + '_BODY']
    if k not in vals: return mm.group(0)
    n_body += 1; return md_value(k)
d2 = re.sub(r'⟦([A-Z]+)⟧', subb, d)
print(f'page: {n_page} placeholder(s) filled inside reply blocks; body: {n_body} filled; left in the body: {sorted(set(re.findall(r"⟦[A-Z]+⟧", d2)))}')
if write:
    if h2 != h: open(PAGE, 'w', encoding='utf-8').write(h2)
    open(FINAL, 'w', encoding='utf-8').write(d2)
    print('written:', PAGE, 'and', FINAL)
