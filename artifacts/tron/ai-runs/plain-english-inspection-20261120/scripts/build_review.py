#!/usr/bin/env python3
"""Arrange test replies in the layout that the skill-creator review page reads.

with_skill    = the installed plain-english-experiment skill, invoked by name in the normal mode
                of the command line (the current plain-english skill is also in context)
without_skill = the current plain-english skill alone (emulated context, safe mode)
Each configuration has 3 runs per case. Every assertion is graded by script.
"""
import json, os, re, shutil, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT + '/proposed/scripts')
sys.path.insert(0, ROOT + '/scripts')
import check_lengths as C

WS = ROOT + '/skill-review/iteration-1'
OUT = ROOT + '/experiment/out'
PROMPTS = ROOT + '/experiment/prompts'
CASES = [('status-report', 'T2_report', 'T2_report.txt'),
         ('explain-tlb', 'T3_explain', 'T3_explain.txt'),
         ('boundary-passages', 'T4_boundary', 'T4_boundary.txt')]
FACTS_T2 = ['412', '409', '118', '119', '2140', '870', '9800', '3100', '61.2', '66.9', '31', '40', '5.7', '9.3',
            '4f1c2aa', 'logrotate', 'ycsb-a', 'NUMA', 'staging', 'capacity']
MARK = re.compile(r'(?mi)^[ \t>*#\-]*passage[ \t]+(\d+)\b[^\n]*$')
LABEL = re.compile(r'^\s*(?:[-*+]|\d+[.)])\s+(?:\*\*[^*]{1,40}\*\*\s*[:.]|\*\*[^*]{1,40}[:.]\*\*|[A-Z][A-Za-z ]{1,24}:\s)')


def unwrap(t):
    return re.sub(r'(?m)^[ \t]*(```|~~~)[^\n]*\n?', '', t)


def segments(text):
    text = unwrap(text)
    ms = list(MARK.finditer(text))
    seg = {}
    for i, m in enumerate(ms):
        n = int(m.group(1))
        end = ms[i + 1].start() if i + 1 < len(ms) else len(text)
        if 1 <= n <= 10 and n not in seg:
            body = text[m.end():end]
            seg[n] = re.split(r'(?m)^(?:#{1,6} |\*\*(?:Notes?|Words used|Terms|Changes|What I changed)[^\n]*$)', body)[0].strip()
    return seg


def shape(body):
    bl = [b for b in C.analyse(body, 'md') if b['kind'] in ('para', 'bullet')]
    sents = [s for b in bl for s in b['sents'] if s['words']]
    items = [b for b in bl if b['kind'] == 'bullet']
    labels = sum(1 for line in body.split('\n') if LABEL.match(line))
    return len(sents), len(items), labels


def grade(task, text):
    measured = unwrap(text) if task.startswith('T4') else text
    bl = [b for b in C.analyse(measured, 'md') if b['kind'] in ('para', 'bullet')]
    sents = [s for b in bl for s in b['sents'] if s['words']]
    longest = max(sents, key=lambda s: s['words'])
    over25 = [s for s in sents if s['words'] > 25]
    over20 = [s for s in sents if s['words'] > 20]
    big = [b for b in bl if len(b['sents']) > 3]
    ex = []

    def add(text_, ok, ev):
        ex.append(dict(text=text_, passed=bool(ok), evidence=ev))

    add('No sentence has more than 25 words.', not over25,
        f"{len(over25)} of {len(sents)} sentences exceed 25 words. Longest: {longest['words']} words.")
    add('No sentence has more than 20 words.', not over20,
        f"{len(over20)} of {len(sents)} sentences exceed 20 words."
        + (f" First: \"{' '.join(over20[0]['text'].split()[:10])} ...\"" if over20 else ''))
    add('No paragraph or bullet has more than three sentences.', not big,
        f"{len(big)} of {len(bl)} paragraphs and bullets exceed three sentences.")
    if task.startswith('T2'):
        missing = [f for f in FACTS_T2 if f.lower() not in text.lower()]
        add('All 20 numbers and names of the notes appear in the reply.', not missing,
            'All 20 found.' if not missing else 'Missing: ' + ', '.join(missing))
    if task.startswith('T4'):
        seg = segments(text)
        sh = {n: shape(seg.get(n, '')) for n in range(1, 11)}
        add('Passage 1, the cache sentence, stays one sentence.', sh[1][0] == 1 and sh[1][1] == 0,
            f"{sh[1][0]} sentences, {sh[1][1]} list items.")
        add('Passage 3, the short sequence, stays one sentence.', sh[3][0] == 1 and sh[3][1] == 0,
            f"{sh[3][0]} sentences, {sh[3][1]} list items.")
        add('Passage 9, the short ", so" sentence, stays one sentence.', sh[9][0] == 1 and sh[9][1] == 0,
            f"{sh[9][0]} sentences, {sh[9][1]} list items.")
        add('Passage 4, a clause inside a clause, becomes two or more sentences without a list.',
            sh[4][0] >= 2 and sh[4][1] == 0, f"{sh[4][0]} sentences, {sh[4][1]} list items.")
        add('Passage 5, three values in 45 words, becomes a list.', sh[5][1] >= 3, f"{sh[5][1]} list items.")
        add('Passage 6, five steps in 35 words, becomes a list.', sh[6][1] >= 4, f"{sh[6][1]} list items.")
        labels = sum(v[2] for v in sh.values())
        add('No list item starts with an added label such as "Benefit:".', labels == 0, f"{labels} labelled list items.")
    n_ok = sum(e['passed'] for e in ex)
    return dict(expectations=ex, summary=dict(passed=n_ok, failed=len(ex) - n_ok, total=len(ex),
                                              pass_rate=round(n_ok / len(ex), 2)))


shutil.rmtree(WS, ignore_errors=True)
for case, task, pfile in CASES:
    prompt = open(f'{PROMPTS}/{pfile}').read()
    cdir = f'{WS}/{case}'
    os.makedirs(cdir, exist_ok=True)
    assertions = None
    for config, arm in (('with_skill', 'SKILL'), ('without_skill', 'CUR')):
        for rep in range(3):
            d = json.load(open(f'{OUT}/{task}_{arm}_{rep}.json'))
            rdir = f'{cdir}/{config}/run-{rep + 1}'
            os.makedirs(rdir + '/outputs', exist_ok=True)
            open(rdir + '/outputs/reply.md', 'w').write(d['result'])
            g = grade(task, d['result'])
            json.dump(g, open(rdir + '/grading.json', 'w'), indent=1)
            assertions = [e['text'] for e in g['expectations']]
            ms = d.get('duration_ms') or 0
            json.dump(dict(total_tokens=(d.get('usage') or {}).get('output_tokens') or 0, duration_ms=ms,
                           total_duration_seconds=round(ms / 1000, 1)), open(rdir + '/timing.json', 'w'))
    note = ('' if task.startswith('T4') else '')
    json.dump(dict(eval_name=case, prompt=prompt, assertions=assertions), open(cdir + '/eval_metadata.json', 'w'), indent=1)
print('workspace written:', WS)
