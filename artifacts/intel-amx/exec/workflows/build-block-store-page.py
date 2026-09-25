from pathlib import Path
import json
import re

root = Path('/home/jhan/workspace/intel-AMX/VNNIed-K-in-place')
reference = (root / 'status/shared-save-explained-codex.html').read_text()
style = re.search(r'<style>(.*?)</style>', reference, re.S).group(1)
style += '''
.glossary-title{font-size:17px;margin-bottom:0}.words{margin-bottom:42px}.line-example{display:grid;grid-template-columns:repeat(16,1fr);gap:3px;margin:22px 0 16px}.line-example span{font-size:10px;text-align:center;border:1px solid #7baccc;background:#eaf4fa;padding:9px 0}.line-example.joined{gap:0;border:2px solid #007b63;border-radius:4px;overflow:hidden}.line-example.joined span{border:0;border-right:1px solid #b1d2c4;background:#e5f3ed}.matrices{display:block;width:100%;min-width:880px}.key.stored{background:#d7eee4;border:1px solid #007b63}.key.selected{background:#f9d88e;border:2px solid #a95a00}.value-detail{padding:13px 16px;border:1px solid #d7dee7;border-radius:8px;background:#f8fafc;font-size:14px;min-height:76px}.pair.untouched{background:#fff;border:1px dashed #b3bfca;color:#536174}.pair.written{background:#e5f3ed;border-color:#a4cebb}.pair.selected-pair{outline:2px solid #a95a00;outline-offset:2px}.page-map{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}.panel{padding:13px 15px;border:1px solid #d7dee7;background:#f6f8fa;border-radius:7px}.panel strong,.panel span,.panel small{display:block}.panel strong{font-size:14px}.panel span{font:700 18px/1.8 ui-monospace,monospace}.panel small{font-size:12px;color:#536174}.panel.chosen{border-color:#84b6d3;background:#eaf4fa}.panel.current{outline:3px solid #0072b2;outline-offset:1px}.formula{font:14px/1.9 ui-monospace,monospace;padding:16px;background:#edf6fb;border-radius:7px;margin:16px 0}.flow.vertical{flex-direction:column;gap:7px}.flow.vertical .arrow{transform:rotate(90deg);line-height:1.1}.counter b{font-size:22px}.controls input[type=range]{accent-color:#0072b2;min-width:100px}#state{min-height:101px}#pair-detail{min-height:82px}
@media(max-width:760px){.page-map{gap:6px}.panel{padding:8px 6px}.panel span{font-size:14px}.panel small{font-size:10px}.line-example{gap:2px}.line-example span{font-size:9px}.formula{font-size:12px}.controls label{max-width:100%}.controls select{max-width:100%;margin-left:0}.controls{align-items:flex-start}.counter b{font-size:19px}.scrub output{min-width:68px}#state{min-height:155px}}
@media print{.matrices{min-width:0}.page-map{grid-template-columns:repeat(4,1fr)}.scroll{overflow:visible}}
'''
records = json.loads((root.parent / 'exec/results/vnnik2-trace-20260915/analysis.json').read_text())
means = {r['trace'].removesuffix('.perfetto-trace'): r['kinds']['prefill']['save_k_us_per_layer'] for r in records}
rows = [(f'TP{tp}', means[f'vnni0-tp{tp}'], means[f'a-tp{tp}']) for tp in (2, 4)]
svg = ['<svg class="chart" viewBox="0 0 1060 330" role="img" aria-label="Block-only Save K duration falls from 857.723 to 346.218 microseconds at TP2 and from 862.917 to 352.903 microseconds at TP4">']
def text(x, y, value, **attrs):
    attr = ' '.join(f'{k.replace("_", "-")}="{v}"' for k, v in attrs.items())
    svg.append(f'<text x="{x}" y="{y}" fill="#536174" font-size="13" {attr}>{value}</text>')
def xpos(value):
    return 100 + value / 1000 * 910
for value in range(0,1001,200):
    x = xpos(value)
    svg.append(f'<line x1="{x}" x2="{x}" y1="45" y2="270" stroke="#e2e7ed"/>')
    text(x,295,f'{value}',text_anchor='middle')
text(1010,319,'µs per layer · zero-based scale',text_anchor='end')
text(100,23,'● Scatter · sharing off',font_weight='700')
svg.append('<text x="365" y="23" fill="#0072b2" font-size="13" font-weight="700">◆ Block store · sharing off</text>')
for i, (name, before, after) in enumerate(rows):
    y = 110 + i * 125
    x1,x2 = xpos(after),xpos(before)
    text(24,y+5,name,font_weight='750')
    svg.append(f'<line x1="{x1}" x2="{x2}" y1="{y}" y2="{y}" stroke="#b3c3cf" stroke-width="4"/>')
    svg.append(f'<circle cx="{x2}" cy="{y}" r="7" fill="#536174"/>')
    svg.append(f'<path d="M {x1} {y-9} l 9 9 l -9 9 l -9 -9 Z" fill="#0072b2"/>')
    text(x2,y-22,f'{before:.1f} µs',text_anchor='middle',font_weight='700')
    svg.append(f'<text x="{x1}" y="{y-22}" fill="#0072b2" font-size="15" text-anchor="middle" font-weight="700">{after:.1f} µs</text>')
    text((x1+x2)/2,y+31,f'−{before-after:.1f} µs · {(before-after)/before*100:.1f}% shorter',text_anchor='middle',font_weight='700')
svg.append('</svg>')
table = ['<table><thead><tr><th>Configuration</th><th class="num">Scatter (µs)</th><th class="num">Block (µs)</th><th class="num">Reduction (µs)</th><th class="num">Reduction (%)</th></tr></thead><tbody>']
for name,before,after in rows:
    table.append(f'<tr><th scope="row">{name}</th><td class="num">{before:.3f}</td><td class="num">{after:.3f}</td><td class="num">{before-after:.3f}</td><td class="num">{(before-after)/before*100:.3f}%</td></tr>')
table.append('</tbody></table>')
body=Path('/tmp/block-store-body.html').read_text()
body=body.replace('@@CHART@@',''.join(svg)).replace('@@TABLE@@',''.join(table))
body=body.replace('@@BASE@@','https://github.com/positron-ai/tron/blob/30c4ac82cbb6959f7e4f66b29efb36f5e0749b48')
body=body.replace('kv_cache.hpp#L10-L110','kv_cache.hpp#L648-L716')
head='<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n<meta name="color-scheme" content="light">\n<title>PR 4424 · How block store works</title>\n'
(root/'status/block-store-explained-codex.html').write_text(head+'<style>'+style+'</style>\n</head>\n<body>\n<main>\n'+body+'\n</main>\n</body>\n</html>\n')
print('Wrote',root/'status/block-store-explained-codex.html')
