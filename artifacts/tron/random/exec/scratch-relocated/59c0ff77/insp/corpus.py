#!/usr/bin/env python3
"""Run measure.py over the real outputs written after the skill's last edit."""
import json, os, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import measure as M

W = '/home/jhan/workspace/'
FILES = [
    'titan/cache-perf/crb/new-test-kernel/old-read-cache-explanation.html',
    'titan/cache-perf/crb/new-test-kernel/ASCT-cross-check.html',
    'titan/cache-perf/crb/new-test-kernel/whole-chip-read-drop-easy-read.html',
    'machines/arm-crb/arm-support-case-20261117/email-to-arm-support.html',
    'titan/cache-perf/crb/new-test-kernel/whole-chip-rerun-7200.html',
    'intel-AMX/muse-glimmer/respond-2-Isaac.html',
    'machines/arm-crb/DIMM-flaky-report.md',
    'intel-AMX/muse-glimmer/review-checks-from-isaac-pr5022.draft.md',
    'intel-AMX/muse-glimmer/pr5022-body-round2.draft.md',
    'intel-AMX/exec/pr5022-final-20261119/README.md',
    'intel-AMX/exec/objcmp5022-20261119/README.md',
    'intel-AMX/muse-glimmer/pr5022-followup-issue.md',
]
HERE = os.path.dirname(os.path.abspath(__file__))


def load():
    corpus = []  # (name, group, blocks)
    for f in FILES:
        text = open(W + f, errors='replace').read()
        fmt = 'html' if f.endswith('.html') else 'md'
        corpus.append((os.path.basename(f), fmt, M.analyse(text, fmt)))
    chat = []
    for line in open(HERE + '/docs.jsonl'):
        d = json.loads(line)
        if d['kind'] == 'chat':
            bl = M.analyse(d['text'], 'md')
            for b in bl:
                b['src'] = d['proj'] + ' ' + d['when'][:16]
            chat.append((d, bl))
    return corpus, chat


def row(name, blocks):
    paras = [b for b in blocks if b['kind'] == 'para']
    bullets = [b for b in blocks if b['kind'] == 'bullet']
    s = M.summary(blocks)
    if not s.get('sentences'):
        return None
    pw = sum(b['words'] for b in paras)
    bw = sum(b['words'] for b in bullets)
    ps = [len(b['sents']) for b in paras]
    bs = [len(b['sents']) for b in bullets]
    return dict(
        name=name, words=s['words'], sents=s['sentences'], mean=s['mean'], median=s['median'], p90=s['p90'],
        max=s['max'], o20=s['over20'], o25=s['over25'], o30=s['over30'],
        n_para=len(paras), para_ge3=M.pct(sum(x >= 3 for x in ps), len(ps)),
        para_ge4=M.pct(sum(x >= 4 for x in ps), len(ps)), para_max_s=max(ps) if ps else 0,
        para_max_w=max([b['words'] for b in paras]) if paras else 0,
        para_over60=M.pct(sum(b['words'] > 60 for b in paras), len(paras)),
        n_bul=len(bullets), bul_ge3=M.pct(sum(x >= 3 for x in bs), len(bs)),
        bul_max_w=max([b['words'] for b in bullets]) if bullets else 0,
        bul_over40=M.pct(sum(b['words'] > 40 for b in bullets), len(bullets)),
        bullet_share=M.pct(bw, pw + bw),
    )


def show(rows):
    hdr = ('name', 'words', 'sents', 'mean', 'median', 'p90', 'max', 'o20', 'o25', 'o30', 'n_para', 'para_ge3',
           'para_ge4', 'para_max_s', 'para_max_w', 'para_over60', 'n_bul', 'bul_ge3', 'bul_max_w', 'bul_over40',
           'bullet_share')
    print('\t'.join(hdr))
    for r in rows:
        if r:
            print('\t'.join(('%.1f' % r[h]) if isinstance(r[h], float) else str(r[h]) for h in hdr))


if __name__ == '__main__':
    corpus, chat = load()
    rows = [row(n[:40], b) for n, fmt, b in corpus]
    allb = [x for n, fmt, b in corpus for x in b]
    rows.append(row('ALL 12 FILES', allb))
    chatb = [x for d, bl in chat for x in bl]
    rows.append(row('CHAT all (%d replies)' % len(chat), chatb))
    long_chat = [x for d, bl in chat if sum(b['words'] for b in bl) >= 60 for x in bl]
    rows.append(row('CHAT replies >= 60 words', long_chat))
    show(rows)
    json.dump(dict(files=[(n, fmt, b) for n, fmt, b in corpus], chat=[(d['proj'], d['when'], bl) for d, bl in chat]),
              open(HERE + '/analysed.json', 'w'))
