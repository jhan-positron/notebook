import os
import faulthandler
faulthandler.dump_traceback_later(45, exit=True)
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright


root = Path('/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/issue4525')
artifact = root / 'status/design-new-tensor-type.html'
evidence = root / 'evidence'
result = {
    'checked_at_utc': datetime.now(timezone.utc).isoformat(),
    'artifact': str(artifact),
    'report_sha256': hashlib.sha256(artifact.read_bytes()).hexdigest(),
    'scope': 'Local Chromium rendering at three widths under emulated dark preference; document overflow, internal anchors, light theme, clipping, console and script errors; no C++ execution',
    'viewports': [],
}
with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True, args=['--no-sandbox'], timeout=15000, env={**os.environ, 'LD_LIBRARY_PATH': '/tmp/amx-browser-libs/usr/lib/x86_64-linux-gnu'})
    result['browser_version'] = browser.version
    for width, height in [(1440, 1000), (390, 844), (320, 844)]:
        page = browser.new_page(viewport={'width': width, 'height': height}, device_scale_factor=1, color_scheme='dark')
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('console', lambda message: errors.append(message.text) if message.type == 'error' else None)
        page.route('http://**/*', lambda route: route.abort())
        page.route('https://**/*', lambda route: route.abort())
        page.goto(artifact.as_uri(), wait_until='load')
        metrics = page.evaluate('''() => ({
            viewport: innerWidth,
            documentWidth: document.documentElement.scrollWidth,
            bodyWidth: document.body.scrollWidth,
            documentHeight: document.documentElement.scrollHeight,
            colorScheme: getComputedStyle(document.documentElement).colorScheme,
            htmlBackground: getComputedStyle(document.documentElement).backgroundColor,
            bodyBackground: getComputedStyle(document.body).backgroundColor,
            duplicateIds: [...document.querySelectorAll('[id]')].map(e => e.id).filter((id, i, ids) => ids.indexOf(id) !== i),
            missingAnchors: [...document.querySelectorAll('a[href^="#"]')]
                .map(a => a.getAttribute('href'))
                .filter(h => h.length > 1 && !document.getElementById(decodeURIComponent(h.slice(1)))),
            scrollContainers: [...document.querySelectorAll('body *')]
                .filter(e => e.scrollWidth > e.clientWidth + 1 && ['auto', 'scroll'].includes(getComputedStyle(e).overflowX))
                .map(e => ({tag: e.tagName, class: e.className.baseVal ?? e.className,
                    clientWidth: e.clientWidth, scrollWidth: e.scrollWidth})),
            clippedText: [...document.querySelectorAll('p,li,td,th,h1,h2,h3,pre,.pair-stage,.pair-stage span,.flow,.node,.maprow')]
                .filter(e => e.clientWidth > 0 && e.scrollWidth > e.clientWidth + 1 && !['auto', 'scroll'].includes(getComputedStyle(e).overflowX))
                .map(e => ({tag: e.tagName, text: e.innerText.slice(0, 100), clientWidth: e.clientWidth, scrollWidth: e.scrollWidth})),
            headings: [...document.querySelectorAll('h1,h2')].map(e => e.innerText)
        })''')
        top_file = evidence / f'design-round3-{width}-top.png'
        page.screenshot(path=str(top_file))
        screenshots = [top_file.name]
        figures = page.locator('.pairfigure')
        if figures.count():
            figure_file = evidence / f'design-round3-{width}-figure.png'
            figures.first.screenshot(path=str(figure_file))
            screenshots.append(figure_file.name)
        result['viewports'].append({'width': width, 'height': height, 'metrics': metrics, 'errors': errors, 'screenshots': screenshots})
        page.close()
    browser.close()
result['checks_passed'] = all(
    item['metrics']['documentWidth'] <= item['width']
    and not item['metrics']['missingAnchors']
    and not item['metrics']['duplicateIds']
    and not item['metrics']['clippedText']
    and not item['errors']
    and item['metrics']['colorScheme'] == 'light'
    for item in result['viewports']
)
(evidence / 'design-round3-render-checks.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'browser_version': result['browser_version'], 'checks_passed': result['checks_passed'], 'report_sha256': result['report_sha256'], 'viewports': [{'width': v['width'], 'documentWidth': v['metrics']['documentWidth'], 'clippedText': v['metrics']['clippedText'], 'errors': v['errors'], 'missingAnchors': v['metrics']['missingAnchors'], 'duplicateIds': v['metrics']['duplicateIds'], 'screenshots': v['screenshots']} for v in result['viewports']]}, indent=2))
