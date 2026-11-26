#!/usr/bin/env python3
"""Regenerate every corpus number of the inspection report.

Input:  data/chat_all.jsonl   (assistant chat text since 2026-10-20, from scripts/extract_chat.py)
        the 12 report files written after the skill's last edit (2026-11-15 14:51 PST)
Output: printed tables, and data/corpus_stats.json
"""
import collections, datetime, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT + '/proposed/scripts')
import check_lengths as C

UTC = datetime.timezone.utc
OLD_LAST = datetime.datetime(2026, 11, 10, 4, 25, 41, tzinfo=UTC)    # last context with the old rule order (short sentences = Rule 8, bullets = Rule 7)
NEW_FIRST = datetime.datetime(2026, 11, 10, 15, 54, 31, tzinfo=UTC)  # first context with the current rule order (Rule 3, Rule 4)
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
out = {}


def when(r):
    return datetime.datetime.fromisoformat(r['when'].replace('Z', '+00:00'))


def fmt(s):
    return (f"sentences={s['sentences']:6d} mean={s['mean']:4.1f} median={s['median']:2d} p90={s['p90']:2d} max={s['max']:3d} "
            f">20w={s['over20']:4.1f}% >25w={s['over25']:4.1f}% >30w={s['over30']:4.1f}% | paras={s['paras']:5d} "
            f">=3s={s['para_ge3']:4.1f}% >3s={s['para_over3']:4.1f}% | bullets={s['bullets']:5d} >=3s={s['bullet_ge3']:4.1f}% "
            f">3s={s['bullet_over3']:4.1f}% | bullet word share={s['bullet_word_share']:4.1f}%")


rows = [json.loads(l) for l in open(ROOT + '/data/chat_all.jsonl')]
for r in rows:
    r['blocks'] = C.analyse(r['text'], 'md')
before = [r for r in rows if when(r) <= OLD_LAST]
after = [r for r in rows if when(r) >= NEW_FIRST]
print('== chat replies, before and after the skill edit of 2026-11-10 (the model changed on the same day) ==')
for name, rs in (('before', before), ('after', after)):
    s = C.stats([b for r in rs for b in r['blocks']])
    s['replies'] = len(rs)
    s['models'] = dict(collections.Counter(r['model'] for r in rs))
    s['first'], s['last'] = min(r['when'] for r in rs)[:16], max(r['when'] for r in rs)[:16]
    out['chat_' + name] = s
    print(f"{name:7s} {s['first']} .. {s['last']} replies={len(rs)} {s['models']}\n        {fmt(s)}")

print('\n== the 12 report files written after 2026-11-15 14:51 PST ==')
file_blocks = []
out['files'] = {}
for f in FILES:
    text = open(W + f, errors='replace').read()
    bl = C.analyse(text, 'html' if f.endswith('.html') else 'md')
    file_blocks.append((f, bl))
    s = C.stats(bl)
    out['files'][f] = s
    print(f"{os.path.basename(f)[:40]:40s} words={s['words']:6d} {fmt(s)}")
allf = [b for _, bl in file_blocks for b in bl]
s = C.stats(allf)
out['files_all'] = s
print(f"{'ALL 12 FILES':40s} words={s['words']:6d} {fmt(s)}")

# ---- features of the long sentences that remain (after period: chat + files) ----
sents = [s for r in after for b in r['blocks'] if b['kind'] in ('para', 'bullet') for s in b['sents']]
sents += [s for b in allf if b['kind'] in ('para', 'bullet') for s in b['sents']]
print(f"\n== features of long sentences, after period, chat + 12 files (n={len(sents)} sentences) ==")
trig = re.compile(r'\b(because|since|which means|so that)\b|;', re.I)
out['features'] = {'n_sentences': len(sents)}
for thr in (20, 25, 30):
    L = [s for s in sents if s['words'] > thr]
    n = len(L)
    f = dict(
        n=n, share_of_all=C.pct(n, len(sents)),
        join=C.pct(sum(s['join'] >= 1 for s in L), n),
        colon=C.pct(sum(s['colon'] for s in L), n),
        paren=C.pct(sum(s['paren'] >= 1 for s in L), n),
        commas3=C.pct(sum(s['commas'] >= 3 for s in L), n),
        sub1=C.pct(sum(s['sub'] >= 1 for s in L), n),
        sub2=C.pct(sum(s['sub'] >= 2 for s in L), n),
        semicolon=C.pct(sum(s['semicolon'] for s in L), n),
        rule2_trigger=C.pct(sum(bool(trig.search(s['text'])) for s in L), n),
        within_limit_without_paren=C.pct(sum(s['words'] - s['paren_words'] <= thr for s in L), n),
        none=C.pct(sum(not (s['join'] or s['colon'] or s['paren'] or s['semicolon'] or s['sub']) for s in L), n),
    )
    out['features'][f'over{thr}'] = f
    print(f"> {thr} words: n={n} ({f['share_of_all']:.1f}% of all) | ', and/or/but/so' join {f['join']:.1f}% | colon {f['colon']:.1f}% | "
          f"parenthesis {f['paren']:.1f}% | 3+ commas {f['commas3']:.1f}% | 1+ subordinator {f['sub1']:.1f}% | "
          f"2+ subordinators {f['sub2']:.1f}% | semicolon {f['semicolon']:.1f}% | Rule 2 trigger word {f['rule2_trigger']:.1f}% | "
          f"within limit once parentheses are removed {f['within_limit_without_paren']:.1f}% | none of these {f['none']:.1f}%")

# ---- Short version sentences against all other sentences (after period) ----
sv, rest = [], []
for bl in [r['blocks'] for r in after] + [b for _, b in file_blocks]:
    for i, b in enumerate(bl):
        if b['kind'] not in ('para', 'bullet'):
            continue
        is_sv = b['text'].lower().startswith('short version') or (
            i > 0 and bl[i - 1]['kind'] == 'heading' and bl[i - 1]['text'].strip().lower().startswith('short version'))
        (sv if is_sv else rest).extend(s['words'] for s in b['sents'] if s['words'])
out['short_version'] = dict(n=len(sv), mean=sum(sv) / len(sv), over20=C.pct(sum(x > 20 for x in sv), len(sv)),
                            over25=C.pct(sum(x > 25 for x in sv), len(sv)),
                            rest_n=len(rest), rest_mean=sum(rest) / len(rest),
                            rest_over20=C.pct(sum(x > 20 for x in rest), len(rest)),
                            rest_over25=C.pct(sum(x > 25 for x in rest), len(rest)))
v = out['short_version']
print(f"\n== 'Short version' blocks against all other prose (after period) ==\n"
      f"Short version: n={v['n']} sentences mean={v['mean']:.1f} >20w={v['over20']:.1f}% >25w={v['over25']:.1f}%\n"
      f"other prose:   n={v['rest_n']} sentences mean={v['rest_mean']:.1f} >20w={v['rest_over20']:.1f}% >25w={v['rest_over25']:.1f}%")

# ---- daily trend of chat replies ----
print('\n== chat replies by day (days with 80+ sentences) ==')
days = collections.defaultdict(list)
for r in rows:
    days[when(r).strftime('%Y-%m-%d')].append(r)
out['daily'] = {}
for d in sorted(days):
    s = C.stats([b for r in days[d] for b in r['blocks']])
    if s['sentences'] < 80:
        continue
    m = '+'.join(sorted(set(r['model'][-3:] for r in days[d])))
    out['daily'][d] = dict(sentences=s['sentences'], over20=s['over20'], para_ge3=s['para_ge3'], model=m)
    print(f"{d} model={m:8s} sentences={s['sentences']:5d} >20w={s['over20']:5.1f}% paragraphs>=3s={s['para_ge3']:5.1f}%")

json.dump(out, open(ROOT + '/data/corpus_stats.json', 'w'), indent=1)
