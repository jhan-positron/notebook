from html import escape
from html.parser import HTMLParser
import json
from pathlib import Path
import subprocess

report_dir = Path('/tmp/jeremy-tasks-20261021')
latest = """To use Phoenix for the SDK's latency runs, one thing would help whenever you have a moment: a few isolated cores for the runtime's pass thread, for example isolcpus, nohz_full and rcu_nocbs on cores 120-127, and the performance cpufreq governor so the clock stays fixed. Both need root and a reboot. Today the governor is schedutil and no cores are isolated."""
deadline = """Thanks, Jibin. Jeremy's Claude again, with one update since this morning: we now have a date. The per-user latency runs for the Nov 5 demo need a quiet host, because the shared LSF workers are too noisy for them. Could the positron-perf account and one isolated core be ready by Fri 10-23, so counted runs can start Mon 10-26? The rest of the list can follow later. If any step is a problem, for example the reboot that isolcpus needs, tell me and we'll work around it.

Sent using @Claude"""
original = """Jibin, Jeremy's Claude here. No rush on this.

We'd like to run some SDK tests on the Phoenix CRB. They use the host CPU only, so the Asimov cards needn't be attached.

What we'd run, one job at a time:
• A timing test: our runtime drives a simulated device, and we measure what the host software adds to each step, to the gaps between tokens, to time to first token, and to waking a waiting reader..
• Our sampling unit tests, natively on Arm..
• A timed compile of a small model..

What the host would need:
• At least one core (two would be better) isolated with isolcpus and nohz_full, ideally rcu_nocbs too, with IRQs kept off it. The other cores stay with the OS and our worker threads..
• A fixed CPU clock (performance governor, no boost), if the board allows it..
• Nothing else running during a timed run. A nightly window is fine..
• clang 18, CMake 3.25 or newer, Ninja, and Python 3.11+ with dev headers (Ubuntu 24.04's packages cover these)..
• About 100 GB of disk. No sudo and no outbound network; we copy everything in..

Two asks:
1. Could the SDK get a local account (positron-perf) with SSH key login, reachable from Jeremy's laptop directly or through sw-dev-01?.
2. If you'd rather not hand out an account, would you run a script we send you instead?.

Sent using @Claude"""
observed = json.loads((report_dir / 'snapshot.json').read_text())
replacements = {
    '{{LATEST_REQUEST}}': latest,
    '{{DEADLINE_REQUEST}}': deadline,
    '{{ORIGINAL_REQUEST}}': original,
    '{{DETAIL_JSON}}': json.dumps(observed['detail'], indent=2, ensure_ascii=False),
    '{{SNAPSHOT_JSON}}': json.dumps(observed['snapshot'], indent=2, ensure_ascii=False),
}
report = (report_dir / 'jeremy-tasks.template.html').read_text()
for token, value in replacements.items():
    assert report.count(token) == 1, token
    report = report.replace(token, escape(value))
assert '{{' not in report


class CheckHTML(HTMLParser):
    void_tags = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input',
                 'link', 'meta', 'param', 'source', 'track', 'wbr'}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.ids = {}
        self.links = []
        self.fragments = {}
        self.capture = None
        self.scripts = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag not in self.void_tags:
            self.stack.append(tag)
        if 'id' in attrs:
            assert attrs['id'] not in self.ids, attrs['id']
            self.ids[attrs['id']] = tag
            if attrs['id'].startswith('quote-') or attrs['id'] == 'governor-command':
                self.capture = attrs['id']
                self.fragments[self.capture] = ''
        if tag == 'a':
            self.links.append(attrs['href'])
        if tag == 'script':
            self.scripts += 1

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.void_tags:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        assert self.stack and self.stack[-1] == tag, (tag, self.stack)
        self.stack.pop()
        if self.capture and tag in ('pre', 'code'):
            self.capture = None

    def handle_data(self, data):
        if self.capture:
            self.fragments[self.capture] += data


check = CheckHTML()
check.feed(report)
assert not check.stack, check.stack
assert not check.scripts
assert check.fragments['quote-latest'] == latest
assert check.fragments['quote-deadline'] == deadline
assert check.fragments['quote-original'] == original
for href in check.links:
    if href.startswith('#'):
        assert href[1:] in check.ids, href
    else:
        assert href.startswith('https://docs.kernel.org/'), href
command = check.fragments['governor-command']
subprocess.run(['sh', '-n'], input=command, text=True, check=True)
snapshot = observed['snapshot']
assert snapshot['topology']['logical_cpus_inspected'] == 128
assert len(snapshot['topology']['requested_cpus']) == 8
assert 8 / 128 * 100 == 6.25
assert 825 / 880 == 120 / 128
assert 55 / 880 == 8 / 128
target = report_dir / 'jeremy-tasks.html'
target.write_text(report)
print(json.dumps({
    'output': str(target),
    'bytes': target.stat().st_size,
    'exact_quotes_verified': 3,
    'internal_links_verified': sum(h.startswith('#') for h in check.links),
    'html_nesting': 'passed',
    'governor_command_syntax': 'passed; not executed',
    'cpu_chart_proportions': 'passed',
}, indent=2))
