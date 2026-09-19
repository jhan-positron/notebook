#!/usr/bin/env python3
"""Recompute this campaign from full accepted logs without changing its summaries."""
from collections import defaultdict
import datetime
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import statistics

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT.parent / 'exec/results/vnnik-20260914'
ARMS = ['off', 'base', 'vnni', 'vnnioff']
NAME = re.compile(r'tp(\d+)__p(\d+)__(\w+)__rep(\d+)\.log(?:\.attempt(\d+))?$')
HEADER = re.compile(r'### runtron tp=(\d+) prompt=(\d+) arm=(\w+) rep=(\d+) attempt=(\d+) (.*)')
PARSE = re.compile(r'\[Request (\d+)\] Parsing the prompt took ([\d.]+) s at ([\d.]+) tokens/s')
DECODE = re.compile(r'\[Request (\d+)\] Generating (\d+) response tokens with (\d+) context took ([\d.]+) s at ([\d.]+) average tok/s')
FINAL = re.compile(r'\[Request (\d+)\] Request with (\d+) tokens in and (\d+) out \(([^)]+)\) saw ([\d.]+) s TTFT and ([\d.]+) s TTLT')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def mean(values):
    return statistics.mean(values)


headers = []
for number, line in enumerate((RESULTS / 'rt-results.txt').read_text().splitlines(), 1):
    match = HEADER.match(line)
    if match:
        tp, prompt, arm, rep, attempt, tail = match.groups()
        headers.append({'tp': int(tp), 'prompt': int(prompt), 'arm': arm, 'rep': int(rep),
                        'attempt': int(attempt), 'line': number, 'text': line,
                        'utc_start': re.search(r'\d{4}-\d\d-\d\dT[^ ]+Z', tail).group(),
                        'status': 'ok'})
    elif line.startswith('RUN-'):
        headers[-1]['status'] = line
header_by_key = {(h['tp'], h['prompt'], h['arm'], h['rep']): h for h in headers}

runs = []
attempts = []
for path in sorted((RESULTS / 'rt').iterdir()):
    match = NAME.fullmatch(path.name)
    if not match:
        continue
    tp, prompt, arm, rep, attempt = match.groups()
    if attempt:
        attempts.append({'path': str(path), 'sha256': digest(path), 'attempt': int(attempt)})
        continue
    tp, prompt, rep = int(tp), int(prompt), int(rep)
    lines = path.read_text().splitlines()
    parsed, decoded, final = [], [], []
    for line_number, line in enumerate(lines, 1):
        if match := PARSE.search(line):
            request, seconds, rate = match.groups()
            parsed.append({'request': int(request), 'seconds': float(seconds),
                           'tokens_per_second': float(rate), 'line': line_number})
        if match := DECODE.search(line):
            request, tokens, context, seconds, rate = match.groups()
            decoded.append({'request': int(request), 'timed_tokens': int(tokens),
                            'context': int(context), 'seconds': float(seconds),
                            'tokens_per_second': float(rate), 'line': line_number})
        if match := FINAL.search(line):
            request, in_tokens, out_tokens, reason, ttft, ttlt = match.groups()
            final.append({'request': int(request), 'input_tokens': int(in_tokens),
                          'output_tokens': int(out_tokens), 'reason': reason,
                          'ttft_seconds': float(ttft), 'ttlt_seconds': float(ttlt), 'line': line_number})
    assert len(parsed) == len(decoded) == len(final) == 8, path
    assert all(sorted(x['request'] for x in values) == list(range(1, 9))
               for values in (parsed, decoded, final)), path
    assert all(x['timed_tokens'] == 253 and x['context'] == prompt + 1 for x in decoded), path
    assert all(x['input_tokens'] == prompt and x['output_tokens'] == 256
               and x['reason'] == 'sequence limit' for x in final), path
    header = header_by_key[tp, prompt, arm, rep]
    assert header['status'] == 'ok', header
    attempt_path = Path(str(path) + f'.attempt{header["attempt"]}')
    assert digest(path) == digest(attempt_path), path
    text = '\n'.join(lines)
    version = re.findall(r'Version: (\S+) hash: (\w+)', text)
    expected_hash = re.search(r'\btip=(\w+)', header['text']).group(1)
    assert len(version) == 1 and version[0][1] == expected_hash, path
    observed = {}
    for key, pattern in {
        'app_cpu_lists': r'App CPU list: (.*)',
        'instances': r'Configured instance ([\d,]+) using resource map',
        'device_cpu_lists': r'Pinning device driver cores to ([\d,-]+)\.',
        'numa_nodes': r'INIT: NUMA set to (\d+)\.',
        'devices': r'Device \{ idx: \d+ addr: ([^ ]+)',
        'bitfiles': r'Bitfile Release Code (\S+) Release Date (\S+)',
        'random_seeds': r'Seed not supplied, using random seed: (\S+)',
        'model_paths': r'Creating tokenizer for path: (\S+)',
        'hardware_attention': r"HW attention disabled for model '[^']+': (.*)",
    }.items():
        observed[key] = sorted(set(re.findall(pattern, text)))
    assert observed['instances'] == ['2,4' if tp == 2 else '1,2'], path
    assert observed['numa_nodes'] == ['1'], path
    assert observed['hardware_attention'] == ['USE_HW_ATTN=0'], path
    runs.append({'tp': tp, 'prompt': prompt, 'arm': arm, 'rep': rep,
                 'path': str(path), 'sha256': digest(path), 'header': header,
                 'version': version[0], 'observed': observed,
                 'parses': parsed, 'decodes': decoded, 'request_completions': final,
                 'tps_per_user': mean([x['tokens_per_second'] for x in decoded]),
                 'sum_individual_tps': sum(x['tokens_per_second'] for x in decoded),
                 'max_ttft_seconds': max(x['seconds'] for x in parsed),
                 'ttft_request_spread_seconds': max(x['seconds'] for x in parsed) - min(x['seconds'] for x in parsed),
                 'error_lines': [{'line': i, 'text': line} for i, line in enumerate(lines, 1)
                                 if re.search(r'\[error\]|\[error \]|\[critical\]', line)]})

groups = defaultdict(list)
for run in runs:
    groups[run['tp'], run['prompt'], run['arm']].append(run)
cells = []
for (tp, prompt, arm), values in sorted(groups.items()):
    tps = [v['tps_per_user'] for v in values]
    ttft = [v['max_ttft_seconds'] for v in values]
    cells.append({'tp': tp, 'prompt': prompt, 'arm': arm, 'n': len(values),
                  'tps_mean': mean(tps), 'tps_sd': statistics.stdev(tps),
                  'ttft_mean_s': mean(ttft), 'ttft_sd_s': statistics.stdev(ttft)})
cell_by_key = {(c['tp'], c['prompt'], c['arm']): c for c in cells}
run_by_key = {(r['tp'], r['prompt'], r['arm'], r['rep']): r for r in runs}
main = []
pairs = []
for tp in (2, 4):
    for prompt in (1024, 2048, 8192):
        base, vnni = [cell_by_key[tp, prompt, arm] for arm in ('base', 'vnni')]
        main.append({'tp': tp, 'prompt': prompt, 'n': base['n'],
                     'base_tps': base['tps_mean'], 'vnni_tps': vnni['tps_mean'],
                     'tps_change_percent': 100 * (vnni['tps_mean'] / base['tps_mean'] - 1),
                     'base_ttft_seconds': base['ttft_mean_s'], 'vnni_ttft_seconds': vnni['ttft_mean_s'],
                     'ttft_change_ms': 1000 * (vnni['ttft_mean_s'] - base['ttft_mean_s']),
                     'ttft_change_percent': 100 * (vnni['ttft_mean_s'] / base['ttft_mean_s'] - 1)})
        for rep in range(1, base['n'] + 1):
            b, v = [run_by_key[tp, prompt, arm, rep] for arm in ('base', 'vnni')]
            pairs.append({'tp': tp, 'prompt': prompt, 'rep': rep,
                          'base_tps': b['tps_per_user'], 'vnni_tps': v['tps_per_user'],
                          'tps_change_percent': 100 * (v['tps_per_user'] / b['tps_per_user'] - 1),
                          'base_ttft_seconds': b['max_ttft_seconds'], 'vnni_ttft_seconds': v['max_ttft_seconds'],
                          'ttft_change_ms': 1000 * (v['max_ttft_seconds'] - b['max_ttft_seconds']),
                          'ttft_change_percent': 100 * (v['max_ttft_seconds'] / b['max_ttft_seconds'] - 1),
                          'base_source': b['path'], 'vnni_source': v['path']})
summary = json.loads((RESULTS / 'summary.json').read_text())
mismatches = []
for c in cells:
    label = f'tp{c["tp"]} p{c["prompt"]} {c["arm"]}'
    for key in ('n', 'tps_mean', 'tps_sd', 'ttft_mean_s', 'ttft_sd_s'):
        if abs(c[key] - summary['cells'][label][key]) > 1e-12:
            mismatches.append({'cell': label, 'metric': key, 'raw': c[key], 'summary': summary['cells'][label][key]})


class Tables(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tables, self.table, self.row, self.cell = [], None, None, None

    def handle_starttag(self, tag, attrs):
        if tag == 'table':
            self.table = []
        elif tag == 'tr' and self.table is not None:
            self.row = []
        elif tag in ('td', 'th') and self.row is not None:
            self.cell = []

    def handle_data(self, text):
        if self.cell is not None:
            self.cell.append(text)

    def handle_endtag(self, tag):
        if tag in ('td', 'th') and self.cell is not None:
            self.row.append(''.join(self.cell).strip())
            self.cell = None
        elif tag == 'tr' and self.row is not None:
            self.table.append(self.row)
            self.row = None
        elif tag == 'table' and self.table is not None:
            self.tables.append(self.table)
            self.table = None


tables = Tables()
tables.feed((ROOT / 'status/codex-review-evidence/Monday-morning-report.html').read_text())
report_mismatches = []
report_cell_rows, report_delta_rows = 0, 0
for tp, cell_table, delta_table in ((2, tables.tables[1], tables.tables[2]),
                                    (4, tables.tables[3], tables.tables[4])):
    for row in cell_table[1:]:
        prompt, arm = int(row[0]), row[1]
        c = cell_by_key[tp, prompt, arm]
        expected = [str(prompt), arm, str(c['n']), f'{c["tps_mean"]:.2f}', f'{c["tps_sd"]:.2f}',
                    f'{c["ttft_mean_s"]:.3f}', f'{c["ttft_sd_s"]:.3f}', '0',
                    run_by_key[tp, prompt, arm, 1]['version'][1][:10]]
        if row != expected:
            report_mismatches.append({'tp': tp, 'actual': row, 'expected': expected})
        report_cell_rows += 1
    for row in delta_table[1:]:
        prompt = int(row[0])
        a, b = row[1].split(' vs ')
        ca, cb = cell_by_key[tp, prompt, a], cell_by_key[tp, prompt, b]
        expected = [f'{100 * (ca[key] / cb[key] - 1):+.1f}%'
                    for key in ('tps_mean', 'ttft_mean_s')]
        if row[2:4] != expected:
            report_mismatches.append({'tp': tp, 'actual': row, 'expected_deltas': expected})
        report_delta_rows += 1

orders = defaultdict(list)
for header in headers:
    orders[f'tp{header["tp"]} prompt{header["prompt"]} rep{header["rep"]}'].append(header['arm'])
test_results = []
for path in sorted(RESULTS.glob('tests-*.out')):
    text = path.read_text()
    result = re.search(r'All tests passed \((\d+) assertions in (\d+) test cases?\)', text)
    test_results.append({'path': str(path), 'sha256': digest(path),
                         'assertions': int(result[1]), 'test_cases': int(result[2]),
                         'test_skip_lines': [{'line': i, 'text': line} for i, line in enumerate(text.splitlines(), 1)
                                             if re.search(r'AMX unavailable|tests? skipped|nothing to test|\bSKIP\b', line)]})
audit = {
    'created_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'),
    'source': 'Independent parser of all full accepted rt/*.log files; rt-results.txt supplies metadata only.',
    'metric_definitions': {'tps': 'Arithmetic mean of 8 logged decode rates per run, then arithmetic mean across repetitions. Raw rates have 3 decimal places.',
                           'ttft': 'Maximum of 8 enqueue-to-on_start elapsed times per run, then arithmetic mean across repetitions. Excludes process startup and model loading.',
                           'change': '100 * (vnni/base - 1). TTFT positive means slower.',
                           'paired': 'Runs matched by tensor parallelism, prompt length and repetition, not randomized pairs.'},
    'counts': {'accepted_logs': len(runs), 'attempt_logs': len(attempts),
               'attempt_headers': len(headers), 'retried_attempts': sum(h['attempt'] > 1 for h in headers),
               'excluded_attempts': sum(h['status'] != 'ok' for h in headers),
               'request_completions': sum(len(r['request_completions']) for r in runs),
               'early_stop_requests': sum(x['reason'] != 'sequence limit' for r in runs for x in r['request_completions']),
               'run_error_lines': sum(len(r['error_lines']) for r in runs)},
    'summary_mismatches': mismatches,
    'report_table_checks': {'cell_rows': report_cell_rows, 'delta_rows': report_delta_rows,
                            'mismatches': report_mismatches},
    'main_results': main, 'cells': cells,
    'paired_repetitions': pairs, 'arm_orders': dict(orders),
    'max_within_run_ttft_spread_seconds': max(r['ttft_request_spread_seconds'] for r in runs),
    'tests': test_results, 'runs': runs, 'attempts': attempts,
    'input_fingerprints': {str(p): digest(p) for p in [RESULTS / 'rt-results.txt', RESULTS / 'build.txt',
                           RESULTS / 'tests.txt', RESULTS / 'summary.json',
                           ROOT / 'status/codex-review-evidence/Monday-morning-report.html']},
}
destination = ROOT / 'status/codex-perf-audit.json'
destination.write_text(json.dumps(audit, indent=2) + '\n')
print(json.dumps({key: audit[key] for key in ('counts', 'summary_mismatches', 'main_results', 'paired_repetitions', 'tests')}, indent=2))
