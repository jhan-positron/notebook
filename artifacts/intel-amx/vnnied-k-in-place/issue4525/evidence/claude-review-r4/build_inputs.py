#!/usr/bin/env python3
"""Build the round-4 review inputs from the round-3 findings.json:
  $S/r3-findings.md            compact record of round 3 (52 findings, 27 residual items, rejected, judges, edits)
  $S/batches/B01.md..B17.md    one checker batch per topic group (79 open items), + batches.json
Usage: python3 build_inputs.py <scratchpad dir>
"""
import json, sys, re
from pathlib import Path

S = Path(sys.argv[1])
EV = Path('/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/issue4525/evidence')
R3 = json.loads((EV / 'claude-review-r3' / 'findings.json').read_text())
R2 = json.loads((EV / 'claude-review-r2' / 'findings.json').read_text())
R1 = json.loads((EV / 'claude-review' / 'findings.json').read_text())

BATCHES = {
 'B01': ['G01', 'G13', 'G21', 'G12', 'F35'],
 'B02': ['G02', 'G15', 'G35', 'G36', 'F23', 'N44'],
 'B03': ['G03', 'G32', 'G50', 'G51'],
 'B04': ['G04', 'G08', 'G09', 'G10', 'G40', 'N20'],
 'B05': ['G05', 'G06', 'G07', 'N42'],
 'B06': ['F19', 'F20', 'F21', 'M06'],
 'B07': ['G14', 'G47', 'M01', 'G27'],
 'B08': ['G16', 'G17', 'G48', 'H03', 'N59'],
 'B09': ['G18', 'G20', 'N28', 'C06'],
 'B10': ['H01', 'F57', 'F58', 'G33'],
 'B11': ['G19', 'G42', 'M04', 'C01'],
 'B12': ['G22', 'G30', 'M03', 'N50'],
 'B13': ['G23', 'H02', 'G34', 'N33', 'F29', 'N30'],
 'B14': ['G24', 'G26', 'G25', 'G28', 'G29', 'F16'],
 'B15': ['G49', 'G31', 'F38'],
 'B16': ['G37', 'G45', 'N56', 'G44', 'G46'],
 'B17': ['G38', 'G39', 'G41', 'F54', 'N11'],
}
all_ids = [i for b in BATCHES.values() for i in b]
assert len(all_ids) == 79 and len(set(all_ids)) == 79, len(all_ids)

r3_new = {f['id']: f for f in R3['confirmed']}
r3_disp = {d['id']: d for d in R3['dispositions']}
r2_new = {f['id']: f for f in R2['confirmed']}
r2_disp = {d['id']: d for d in R2['dispositions']}
r1_new = {f['id']: f for f in R1['confirmed']}
open_r3 = [d for d in R3['dispositions'] if d['final_status'] != 'resolved']
assert set(d['id'] for d in open_r3) == set(i for i in all_ids if i not in r3_new), set(d['id'] for d in open_r3) ^ set(i for i in all_ids if i not in r3_new)
assert set(r3_new) == set(i for i in all_ids if i in r3_new)


def corrections(votes, label='VERIFIER CORRECTION'):
    out = []
    for v in votes or []:
        if v.get('correction'):
            out.append('- %s (%s lens): %s' % (label, v.get('lens', '?'), v['correction']))
    return out


def new_finding_block(f, heading_round='round-3'):
    lines = ['### %s [%s NEW finding, severity %s] %s' % (f['id'], heading_round, f['severity'].upper(), f['title'])]
    lines.append('- Where in the %s design: %s' % (heading_round, f.get('section', '')))
    if f.get('relates_to'):
        lines.append('- Relates to earlier id(s): %s' % f['relates_to'])
    lines.append('- Kind: %s | found by lenses: %s' % (f.get('kind', ''), ', '.join(f.get('lenses', []))))
    lines.append('- Claim: %s' % f.get('claim', ''))
    q = f.get('design_quote', '')
    if q and q.lower() not in ('omission', 'see evidence'):
        lines.append('- The %s design text said: "%s"' % (heading_round, q))
    elif q:
        lines.append('- The %s design text: %s' % (heading_round, q))
    lines.append('- Evidence given in %s: %s' % (heading_round, f.get('evidence', '')))
    lines.append('- RECOMMENDATION (what the design was asked to change): %s' % f.get('recommendation', ''))
    if f.get('lead_note'):
        lines.append('- LEAD NOTE (final grade %s): %s' % (f['severity'], f['lead_note']))
    lines += corrections(f.get('votes'))
    return '\n'.join(lines)


def origin_of(i):
    if i in r3_new: return 'round 3'
    if i in r2_new: return 'round 2'
    return 'round 1'


def residual_block(d):
    i = d['id']
    origin = origin_of(i)
    sev = d.get('prior_severity', '')
    title = d.get('prior_title', '')
    lines = ['### %s [%s finding, severity %s; graded %s in round 3] %s' % (i, origin, str(sev).upper(), d['final_status'].upper(), title)]
    # original recommendation
    if i in r2_new:
        f = r2_new[i]
        lines.append('- Original round-2 claim: %s' % f.get('claim', '')[:1800])
        lines.append('- Original round-2 RECOMMENDATION: %s' % f.get('recommendation', '')[:2000])
        if f.get('lead_note'): lines.append('- Round-2 LEAD NOTE: %s' % f['lead_note'][:1200])
        lines += [c[:900] for c in corrections(f.get('votes'), 'Round-2 VERIFIER CORRECTION')]
    elif i in r1_new:
        f = r1_new[i]
        lines.append('- Original round-1 claim: %s' % f.get('claim', '')[:1500])
        lines.append('- Original round-1 RECOMMENDATION: %s' % f.get('recommendation', '')[:1800])
        if i in r2_disp:
            d2 = r2_disp[i]
            lines.append('- Round-2 status: %s. Round-2 remark: %s' % (d2.get('final_status'), (d2.get('remark') or '')[:800]))
            if d2.get('residual'): lines.append('- STILL NEEDED after round 2: %s' % d2['residual'][:1800])
    lines.append('- Round-3 checker remark: %s' % (d.get('remark') or d.get('assessment', ''))[:1600])
    if d.get('residual'):
        lines.append('- STILL NEEDED after round 3 (grade this against THIS text): %s' % d['residual'])
    else:
        lines.append('- STILL NEEDED after round 3: (deferred item; see the remark for what is acceptable)')
    lines += corrections(d.get('votes'), 'Round-3 RE-GRADER CORRECTION')
    return '\n'.join(lines)


# ------------------------------------------------------------------ compact record
out = ['# Round-3 review (2026-09-22 ~09:30 UTC) of the SECOND codex revision (121,774 bytes, sha 5dea1702): compact record',
       '',
       'This file is the round-3 review page (status/claude-review-design-new-tensor-type.html at round 3, archived as -r3.html) reduced to its findings and recommendations.',
       '', '## Short version of the round-3 page']
out += ['- ' + p for p in R3['short_version']]
out += ['', '## Round-3 verdict (three judges)']
for j in R3['judges']:
    out.append('- %s: %s; %s. Reasons: %s' % (j['label'], j['verdict'], 'implementable now' if j['implementable_now'] else 'NOT yet implementable', j['reasons']))
    out.append('  Top three edits: ' + ' | '.join(j.get('top_three_edits', [])))
    out.append('  Must fix before implementation: ' + ' | '.join(j.get('must_fix', [])))
out += ['', '## Round-3 section 7: recommended edits, in order']
out += ['%d. %s' % (n + 1, e) for n, e in enumerate(R3['edits'])]
out += ['', '## Round-3 section 5: the decision record (question | covers | assessment)']
out += ['- %s | %s | %s' % tuple(r) for r in R3['questions_rows']]
out += ['', '## Round-3 section 6: what the second revision gets right']
out += ['- ' + s for s in R3['strengths']]
out += ['', '## Round-3 section 4: the 52 NEW findings (G.. finders, H.. completeness critic), with verifier corrections and lead notes', '']
sev_order = {'blocker': 0, 'major': 1, 'minor': 2, 'note': 3}
for f in sorted(R3['confirmed'], key=lambda f: (sev_order[f['severity']], f['id'])):
    out.append(new_finding_block(f)); out.append('')
out += ['## Round-3 section 3: the 27 known items NOT resolved by the second revision (25 partly, 2 deferred), with STILL NEEDED text', '']
for d in open_r3:
    out.append(residual_block(d)); out.append('')
out += ['## Round-3 section 3: the 60 known items the second revision RESOLVED (do not re-raise)', '']
out.append(', '.join(sorted(d['id'] for d in R3['dispositions'] if d['final_status'] == 'resolved')))
out += ['', '## Round-3 section 9: candidates that did not survive verification or were dropped by the lead', '']
for f in R3['rejected']:
    reasons = '; '.join('%s: %s' % (v['lens'], (v.get('correction') or v.get('reason', ''))[:500]) for v in f.get('votes', []) if v.get('refuted'))
    tag = 'DROPPED BY THE LEAD: ' + f.get('lead_drop_reason', '') if f.get('lead_dropped') else 'REJECTED (refuted by at least two verifiers)'
    out.append('### %s %s\n- Candidate claim: %s\n- %s\n- Refuting verifiers: %s\n' % (f['id'], f['title'], f.get('claim', '')[:900], tag, reasons))
out += ['## Earlier rejected candidates (still rejected)', '',
        'Round 1: F06 F07 F09 F18 F22 F33 F36 F44 F53 F55. Round 2: N10 N19 N21 N26 N47 N54. Reasons in r1-findings.md and r2-findings.md.']
(S / 'r3-findings.md').write_text('\n'.join(out) + '\n')
print('wrote r3-findings.md', (S / 'r3-findings.md').stat().st_size, 'bytes')

# ------------------------------------------------------------------ batches
(S / 'batches').mkdir(exist_ok=True)
for b, ids in BATCHES.items():
    lines = ['# Batch %s: %d items to check against the ROUND-4 design text ($S/design-r4.txt)' % (b, len(ids)), '',
             'Each item is either a round-3 NEW finding (G../H..) with its recommendation, lead note and verifier corrections, or an item that round 3 graded PARTLY or DEFERRED with a "STILL NEEDED after round 3" residual. Grade the round-4 design text against the RECOMMENDATION as corrected by the verifiers (for new findings) or against the STILL NEEDED text (for residual items).', '']
    for i in ids:
        if i in r3_new:
            lines.append(new_finding_block(r3_new[i]))
        else:
            lines.append(residual_block(r3_disp[i]))
        lines.append('')
    (S / 'batches' / ('%s.md' % b)).write_text('\n'.join(lines))
(S / 'batches' / 'batches.json').write_text(json.dumps(BATCHES, indent=1))
print('wrote', len(BATCHES), 'batches;', sum(len(v) for v in BATCHES.values()), 'items')
for b, ids in BATCHES.items():
    print(b, len(ids), (S / 'batches' / ('%s.md' % b)).stat().st_size, 'bytes', ids)
