from pathlib import Path
import base64
import html
import json
import re

DEST = Path('/home/jhan/workspace/intel-AMX/PR3879/new-PRs/new-counters/tron-intuition-codex.html')
BASE = Path('/home/jhan/workspace/intel-AMX/exec/results/attnstats-20261002')
RUN = 'gptoss-8u-p1024-fpga__fpga__amxon__rep1'
LOG = BASE / 'rt' / (RUN + '.log')
LEAVES = BASE / 'leaves' / RUN
SHA = 'dd0f942c75257a0288978a54a0a36b8ef1e6d85d'
raw = LOG.read_text()

def record(prefix):
    return json.loads(next(line for line in raw.splitlines() if line.startswith(prefix)).split(': ', 1)[1])

meta = record('[attn-stats] model ')
totals = record('[attn-stats] decode_like/all_jobs_with_listener totals:')
forwards = record('[attn-stats] decode_like/all_jobs_with_listener forwards:')
prompt = record('[attn-stats] prompt_or_mixed/some_jobs_without_listener forwards:')
layer_line = next(line for line in raw.splitlines() if line.startswith('[attn-stats] decode_like/all_jobs_with_listener k_tokens per layer'))
layer_counts = [tuple(map(int, m)) for m in re.findall(r'(\d+)=(\d+)/(\d+)/(\d+)', layer_line)]
snapshot_hz = json.loads((LEAVES / 'summary').read_text())['tsc_hz']
window_rows = [json.loads((LEAVES / f'decode_like_layer_{i}').read_text()) for i in range(0, 36, 2)]
busy = sum(row['busy_cycles'] / row['attn_jobs'] / snapshot_hz * 1000 for row in window_rows)
join = sum(row['join_wait_cycles'] / row['attn_jobs'] / snapshot_hz * 1000 for row in window_rows)
window_keys = sum(avx for layer, amx, avx, fpga in layer_counts if layer % 2 == 0)
tail_keys = sum(avx for layer, amx, avx, fpga in layer_counts if layer % 2 == 1)
fpga_keys = totals['fpga_k_tokens_x_kv_heads']
dense_keys = 64 * (totals['ready_avx_full_page_visits'] + totals['pending_avx_full_page_visits'])
all_keys = window_keys + tail_keys + fpga_keys
facts = dict(
    forwardMs=forwards['wall_cycles'] / forwards['forwards'] / meta['tsc_hz'] * 1000,
    busyMs=busy, joinMs=join, nonjoinMs=busy-join,
    windowKeys=window_keys, tailKeys=tail_keys, fpgaKeys=fpga_keys,
    allKeys=all_keys, denseKeys=dense_keys, denseFraction=dense_keys/window_keys,
    forwards=forwards['forwards'], tscHz=meta['tsc_hz'], snapshotHz=snapshot_hz,
    promptMs=prompt['wall_cycles']/prompt['forwards']/meta['tsc_hz']*1000,
    log=str(LOG), leaves=str(LEAVES), sha=SHA,
)
assert all_keys == 377634816
assert dense_keys == 19169280
assert all(amx == 0 for layer, amx, avx, fpga in layer_counts)

MODELS = [
    dict(id='llama8', name='Llama 3.1 8B', layers=32, d=4096, q=32, kv=8, h=128, m=14336, vocab=128256, full=32, window=0, experts=0, active=1, source='https://github.com/meta-llama/llama-models/blob/main/models/sku_list.py'),
    dict(id='llama70', name='Llama 3.1 70B', layers=80, d=8192, q=64, kv=8, h=128, m=28672, vocab=128256, full=80, window=0, experts=0, active=1, source='https://github.com/meta-llama/llama-models/blob/main/models/sku_list.py'),
    dict(id='qwen7', name='Qwen 2.5 7B', layers=28, d=3584, q=28, kv=4, h=128, m=18944, vocab=152064, full=28, window=0, experts=0, active=1, source='https://huggingface.co/Qwen/Qwen2.5-7B-Instruct/raw/main/config.json'),
    dict(id='qwen32', name='Qwen 2.5 32B', layers=64, d=5120, q=40, kv=8, h=128, m=27648, vocab=152064, full=64, window=0, experts=0, active=1, source='https://huggingface.co/Qwen/Qwen2.5-32B-Instruct/raw/main/config.json'),
    dict(id='qwen72', name='Qwen 2.5 72B', layers=80, d=8192, q=64, kv=8, h=128, m=29568, vocab=152064, full=80, window=0, experts=0, active=1, source='https://huggingface.co/Qwen/Qwen2.5-72B-Instruct/raw/main/config.json'),
    dict(id='gpt20', name='GPT-OSS 20B', layers=24, d=2880, q=64, kv=8, h=64, m=2880, vocab=201088, full=12, window=12, experts=32, active=4, source='https://huggingface.co/openai/gpt-oss-20b/raw/main/config.json'),
    dict(id='gpt120', name='GPT-OSS 120B', layers=36, d=2880, q=64, kv=8, h=64, m=2880, vocab=201088, full=18, window=18, experts=128, active=4, source='https://huggingface.co/openai/gpt-oss-120b/raw/main/config.json'),
]

PAGE = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light">
<meta name="description" content="A source-grounded guide to estimating Tron timing by hand, with model shapes, execution paths, measured GPT-OSS counters, and interactive dependency diagrams.">
<title>Tron timing by hand</title>
<style>
:root{color-scheme:light;--paper:#faf9f5;--white:#fff;--ink:#172e3b;--muted:#526774;--line:#d5dfe3;--blue:#0072b2;--bluebg:#eaf4fb;--orange:#b94c00;--orangebg:#fff2e5;--teal:#007c67;--tealbg:#eaf5ef;--red:#b32f3f;--redbg:#fff0f1;--soft:#f1f4f5}
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:22px}body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.65 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}a{color:#005f96;text-underline-offset:3px}a:hover{color:#003c61}a:focus-visible,button:focus-visible,input:focus-visible,select:focus-visible,summary:focus-visible{outline:3px solid var(--blue);outline-offset:3px}h1,h2,h3,p,ul,ol,dl,figure{margin-top:0}h1{font-size:clamp(2.2rem,5vw,3.75rem);line-height:1.08;letter-spacing:-.035em;max-width:800px;margin-bottom:24px}h2{font-size:1.8rem;line-height:1.25;letter-spacing:-.02em;margin-bottom:20px}h3{font-size:1.1rem;line-height:1.4;margin-bottom:10px}p{margin-bottom:15px}li{margin-bottom:8px}ul,ol{padding-left:23px}code,.mono{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-size:.88em}code{background:var(--soft);padding:2px 5px;border-radius:4px;overflow-wrap:anywhere}small,.small{font-size:.83rem;line-height:1.55}.muted{color:var(--muted)}.eyebrow{font-size:.76rem;letter-spacing:.13em;text-transform:uppercase;font-weight:700;color:var(--muted);margin-bottom:12px}.wrap{max-width:1290px;margin:auto;padding:48px 34px 70px}.layout{display:grid;grid-template-columns:180px minmax(0,1fr);gap:46px}.sidebar{position:sticky;top:25px;align-self:start;font-size:.85rem;line-height:1.5}.sidebar a{display:block;padding:9px 0;color:var(--muted);text-decoration:none;border-bottom:1px solid var(--line)}.sidebar a:hover{color:var(--blue)}.sidebar .nav-title{font-weight:750;color:var(--ink);font-size:.95rem;padding:0 0 12px}main{min-width:0}.hero{padding-bottom:28px}.summary{border-left:4px solid var(--blue);padding:18px 22px;background:var(--bluebg);border-radius:0 10px 10px 0}.summary .label{font-size:.8rem;font-weight:750;margin-bottom:7px}.summary p:last-child{margin-bottom:0}.meta{margin-top:15px;font-size:.78rem;color:var(--muted)}section{margin-top:45px;padding-top:28px;border-top:1px solid var(--line)}.number{display:block;font-size:.74rem;letter-spacing:.1em;color:var(--blue);font-weight:750;text-transform:uppercase;margin-bottom:8px}.two{display:grid;grid-template-columns:1fr 1fr;gap:20px}.card,.lab{border:1px solid var(--line);background:var(--white);padding:23px;border-radius:12px}.card ul:last-child,.card p:last-child{margin-bottom:0}.learn{border-top:4px solid var(--blue)}.lookup{border-top:4px solid var(--teal)}.card h3{margin-bottom:15px}.terms{display:grid;grid-template-columns:1fr 1fr;gap:12px 30px;font-size:.88rem;margin:20px 0 0}.terms dt{font-weight:700}.terms dd{margin:2px 0 0;color:var(--muted)}details{background:var(--white);border:1px solid var(--line);padding:15px 20px;border-radius:9px;margin:18px 0}summary{cursor:pointer;font-weight:650}details[open] summary{margin-bottom:17px}details p:last-child{margin-bottom:0}.cite{font-size:.78rem;white-space:nowrap;text-decoration:none}.note{padding:14px 18px;background:var(--soft);border-radius:8px;font-size:.9rem;margin:18px 0}.warning{background:var(--orangebg);border-left:3px solid var(--orange)}.good{background:var(--tealbg)}.note p:last-child{margin-bottom:0}.process{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:9px;margin:23px 0}.step{padding:14px 11px;border:1px solid var(--line);background:white;border-radius:8px;font-size:.85rem;line-height:1.5}.step b{display:block;font-size:.77rem;color:var(--blue);margin-bottom:5px}.step span{display:block;color:var(--muted);font-size:.78rem;margin-top:5px}.step:not(:last-child)::after{content:'→';display:block;text-align:right;color:var(--blue);font-size:1.2rem}.diagram{background:var(--white);border:1px solid var(--line);padding:20px;border-radius:10px;margin:22px 0}.diagram svg,.chart svg{display:block;width:100%;height:auto}.scroll{overflow-x:auto;max-width:100%;margin:20px 0;border:1px solid var(--line);border-radius:9px;background:white}.scroll table{margin:0}.diagram-scroll{overflow-x:auto}.diagram-scroll svg{min-width:690px}.caption,figcaption{color:var(--muted);font-size:.83rem;margin-top:12px}.legend{display:flex;gap:18px;flex-wrap:wrap;font-size:.8rem;margin:10px 0}.legend span{display:flex;gap:7px;align-items:center}.swatch{display:inline-block;width:14px;height:12px;background:var(--blue);border-radius:2px}.swatch.orange{background:var(--orange)}.swatch.teal{background:var(--teal)}.swatch.red{background:var(--red)}.swatch.wait{background:white;border:1.5px dashed var(--muted)}table{width:100%;border-collapse:collapse;font-size:.86rem;line-height:1.5}th,td{text-align:left;vertical-align:top;padding:12px 13px;border-bottom:1px solid var(--line)}th{font-size:.76rem;background:var(--soft);font-weight:750}tr:last-child td{border-bottom:0}table .num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}.models{min-width:805px}.models td:first-child{min-width:150px}.badge{display:inline-block;padding:3px 8px;border-radius:5px;font-size:.73rem;line-height:1.5;font-weight:650;background:var(--soft);color:var(--muted)}.badge.blue{background:var(--bluebg);color:#00567f}.badge.orange{background:var(--orangebg);color:#904000}.equation{display:block;white-space:normal;background:#eef3f6;border-radius:8px;padding:16px 19px;margin:16px 0;font:500 .96rem/1.8 ui-monospace,SFMono-Regular,Consolas,monospace;overflow-wrap:anywhere}.equation span{display:block}.symbol{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-weight:650}.controls{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;margin:18px 0}.controls.four{grid-template-columns:repeat(4,minmax(0,1fr))}label{display:block;font-size:.8rem;line-height:1.5;font-weight:650}input,select,button{font:inherit}input[type=number],select{margin-top:6px;padding:9px 10px;border:1px solid #aebfc8;background:white;color:var(--ink);border-radius:6px;width:100%;height:43px}input[type=range]{width:100%;accent-color:var(--blue);margin:14px 0}button{border:1px solid #a9bcc8;background:white;border-radius:6px;color:#005b8e;font-size:.83rem;padding:9px 13px;cursor:pointer}button:hover{background:var(--bluebg)}.buttons{display:flex;flex-wrap:wrap;gap:8px;margin:14px 0}.outputs{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin:18px 0}.output{background:var(--bluebg);padding:14px 16px;border-radius:7px}.output .value{display:block;font-size:1.5rem;font-weight:750;line-height:1.2;font-variant-numeric:tabular-nums;overflow-wrap:anywhere}.output .unit{display:block;color:var(--muted);font-size:.76rem;margin-top:7px}.outputs .output.orange{background:var(--orangebg)}.status{font-size:.9rem;margin:16px 0 0;background:var(--soft);padding:13px 15px;border-radius:7px}.status:empty{display:none}.source-list{padding-left:20px;font-size:.85rem}.source-list li{margin-bottom:18px;overflow-wrap:anywhere}.source-list code{font-size:.9em}.formula-list dt{font-weight:700;margin-top:15px}.formula-list dd{margin:5px 0 16px}.worksheet{counter-reset:worksheet}.worksheet li{padding-left:6px;margin-bottom:17px}.line{display:block;border-bottom:1px dotted #81929b;height:25px}.screenshot{display:block;width:100%;height:auto;border:1px solid var(--line)}.footer{font-size:.76rem;color:var(--muted);margin-top:25px}.print-button{margin-top:19px}.no-js{background:var(--orangebg);padding:12px;margin:16px 0}
@media(max-width:1000px){.wrap{padding:30px 24px}.layout{grid-template-columns:145px minmax(0,1fr);gap:28px}.process{grid-template-columns:1fr 1fr}.step:last-child{grid-column:1/-1}.controls.four{grid-template-columns:1fr 1fr}}
@media(max-width:760px){.wrap{padding:25px 18px 50px}.layout{display:block}.sidebar{position:static;display:flex;flex-wrap:wrap;gap:2px 17px;margin-bottom:30px}.sidebar .nav-title,.sidebar .print-button{display:none}.sidebar a{font-size:.77rem;padding:4px 0;border:0}.two,.terms{grid-template-columns:1fr}.controls,.outputs{grid-template-columns:1fr}.controls.four{grid-template-columns:1fr 1fr}.output .value{font-size:1.35rem}section{margin-top:30px;padding-top:25px}.card,.lab,.diagram{padding:17px}.summary{padding:16px 17px}h2{font-size:1.55rem}.diagram-scroll{margin:0 -5px}.equation{font-size:.84rem}.models{font-size:.8rem}}
@media print{body{background:white;font-size:10pt}.wrap{padding:0}.layout{display:block}.sidebar,.buttons,.print-button{display:none}.hero{padding-bottom:10px}section{margin-top:20px;padding-top:16px}h1{font-size:28pt}h2{font-size:18pt}h2,h3{break-after:avoid}.card,.lab,figure,table{break-inside:avoid}.scroll{overflow:visible}.models{min-width:0;font-size:7pt}.diagram-scroll{overflow:visible}.diagram-scroll svg{min-width:0}.controls,.outputs{grid-template-columns:repeat(3,1fr)}.two{grid-template-columns:1fr 1fr}a{color:inherit}.screenshot{max-height:400px;object-fit:contain}details:not([open]){display:none}}
</style>
</head>
<body>
<div class="wrap layout">
<nav class="sidebar" aria-label="Guide sections">
  <div class="nav-title">Tron timing by hand</div>
  <a href="#learn">What to internalize</a><a href="#execution">Execution map</a><a href="#routes">AoF, AMX, AVX</a><a href="#shapes">Model reference</a><a href="#work">Count the work</a><a href="#elapsed">Estimate elapsed time</a><a href="#case">Your GPT-OSS example</a><a href="#gain">Estimate a speedup</a><a href="#handy">Keep these handy</a><a href="#sources">Sources and arithmetic</a>
  <button class="print-button" type="button" onclick="window.print()">Print the guide</button>
</nav>
<main>
<header class="hero">
<div class="eyebrow">A manual method · rebuilt from image.png</div>
<h1>Tron timing by hand</h1>
<div class="summary"><div class="label">Short version</div><p>Learn the order of the work and the conditions that choose its execution path. Keep model dimensions and measured operation costs beside your drawing. In the GPT-OSS run from your image, the CPU handled 10.19% of scored keys, but a speedup estimate also needs their cost and their position in the execution schedule. <a class="cite" href="#r1">[R1]</a></p></div>
<p class="meta">Rebuilt 7 October 2026 · implementation checked at Tron <code>dd0f942c7525</code> · measurements from 2 October 2026 · accelerator-backed execution</p>
<dl class="terms">
<div><dt>Tron, CPU, and FPGA</dt><dd>Tron is the inference program under test. The CPU is the host processor. The FPGA is the programmable accelerator card.</dd></div>
<div><dt>AoF, AMX, and AVX</dt><dd>AoF means attention on FPGA. AMX and AVX are CPU instruction sets. Here they select how CPU attention runs.</dd></div>
<div><dt>Token, forward, prefill, and decode</dt><dd>A token is a piece of text. A forward is one model invocation. Prefill processes prompt tokens. Decode produces subsequent tokens.</dd></div>
<div><dt>Attention, heads, and KV</dt><dd>Attention scores stored keys against a query and combines their values. Heads are separate groups of these vectors. KV means cached keys and values.</dd></div>
<div><dt>KV page, GQA, and bf16</dt><dd>A software KV page is a 64-token block. GQA is grouped-query attention: several query heads share one KV head. bf16 is a 2-byte number format.</dd></div>
<div><dt>Elapsed time and critical path</dt><dd>Elapsed time is time on the clock. The critical path is the chain of dependencies that determines when the result can finish.</dd></div>
</dl>
<noscript><p class="no-js">The reference and measured tables work without JavaScript. Enable JavaScript to use the calculators and adjustable diagrams.</p></noscript>
</header>

<section id="learn">
<span class="number">01 · Learn the relationships</span><h2>What should you internalize?</h2>
<div class="two">
<div class="card learn"><h3>Learn these until you can draw them</h3><ul>
<li>A token passes through every layer. The next layer needs the previous layer’s result.</li>
<li>Inside a layer, some CPU work can overlap device work. The last required result controls the next step.</li>
<li>Full attention grows with visible history. A sliding window caps the history used by that layer.</li>
<li>AoF chooses device attention where it is eligible. AMX chooses an implementation for eligible CPU pages.</li>
<li>A count becomes a time only after you apply a matching measured cost.</li>
<li>Faster work shortens elapsed time only where it advances a required result.</li>
</ul></div>
<div class="card lookup"><h3>Keep these in a reference card</h3><ul>
<li>Exact model dimensions, attention windows, and active experts.</li>
<li>The build, hardware, worker count, and actual path counters.</li>
<li>Measured costs for complete pages, partial pages, joins, transfers, and device operations.</li>
<li>The boundaries and units of every timer you use.</li>
<li>A matching baseline for prompt processing and for decode.</li>
</ul><p class="small muted">Memorizing a particular microsecond value is less useful than recording the conditions under which it was measured.</p></div>
</div>
<div class="process" aria-label="Five steps for a timing estimate">
<div class="step"><b>1 · Shape</b>Which vectors and layers?<span>Read the model card.</span></div>
<div class="step"><b>2 · Route</b>Which processor does each part?<span>Check actual eligibility.</span></div>
<div class="step"><b>3 · Amount</b>How many queries and visible keys?<span>Count work in one unit.</span></div>
<div class="step"><b>4 · Cost</b>How long does that work take?<span>Use matching measurements.</span></div>
<div class="step"><b>5 · Dependency</b>Which result arrives last?<span>Count the time it exposes.</span></div>
</div>
<p class="small muted">The routing and overlap rules follow the checked implementation. The five-step method is a way to use those rules in an estimate. <a class="cite" href="#c1">[C1]</a> <a class="cite" href="#c2">[C2]</a> <a class="cite" href="#c3">[C3]</a></p>
</section>

<section id="execution">
<span class="number">02 · Draw one layer first</span><h2>Where does the time go?</h2>
<p>For Llama and Qwen, draw the dense layer below. “Dense” means each token uses the same feed-forward matrices. GPT-OSS replaces that feed-forward block with selected experts, which are separate learned feed-forward networks.</p>
<figure class="diagram">
<div class="diagram-scroll"><svg viewBox="0 0 900 302" role="img" aria-labelledby="execution-title execution-desc">
<title id="execution-title">One model layer, with CPU and FPGA work</title><desc id="execution-desc">CPU normalization leads to device Q K V projections. CPU prepares position information and the KV cache. Attention may split between CPU and FPGA. The merged result goes through the device output projection and feed-forward block, then the next layer. The diagram shows dependency order, not durations.</desc>
<defs><marker id="arrow" markerWidth="7" markerHeight="7" refX="6" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6" fill="none" stroke="#526774" stroke-width="1.4"/></marker></defs>
<g font-family="system-ui,sans-serif" font-size="13" fill="#172e3b">
<rect x="6" y="32" width="132" height="65" rx="8" fill="#eaf4fb" stroke="#8cb7cf"/><text x="72" y="56" text-anchor="middle" font-weight="700">CPU</text><text x="72" y="78" text-anchor="middle">Normalize input</text>
<path d="M138 64 H164" stroke="#526774" fill="none" marker-end="url(#arrow)"/>
<rect x="170" y="32" width="136" height="65" rx="8" fill="#eaf5ef" stroke="#80b9ab"/><text x="238" y="56" text-anchor="middle" font-weight="700">FPGA</text><text x="238" y="78" text-anchor="middle">Q, K, V projections</text>
<path d="M306 64 H332" stroke="#526774" fill="none" marker-end="url(#arrow)"/>
<rect x="338" y="32" width="150" height="65" rx="8" fill="#eaf4fb" stroke="#8cb7cf"/><text x="413" y="56" text-anchor="middle" font-weight="700">CPU</text><text x="413" y="78" text-anchor="middle">Position + KV save</text>
<path d="M488 64 H514" stroke="#526774" fill="none" marker-end="url(#arrow)"/>
<rect x="520" y="14" width="180" height="103" rx="8" fill="#fff2e5" stroke="#c7936c"/><text x="610" y="39" text-anchor="middle" font-weight="700">Attention</text><text x="610" y="61" text-anchor="middle">CPU pages + AoF ranges</text><text x="610" y="82" text-anchor="middle">where eligible</text><text x="610" y="102" text-anchor="middle">Merge partial results</text>
<path d="M700 64 H726" stroke="#526774" fill="none" marker-end="url(#arrow)"/>
<rect x="732" y="32" width="158" height="65" rx="8" fill="#eaf5ef" stroke="#80b9ab"/><text x="811" y="56" text-anchor="middle" font-weight="700">FPGA</text><text x="811" y="78" text-anchor="middle">Output projection</text>
<path d="M72 130 H811" stroke="#d5dfe3" stroke-dasharray="4 4"/><text x="450" y="150" text-anchor="middle" fill="#526774" font-size="12">Then feed-forward work, shown left to right below</text>
<rect x="6" y="178" width="175" height="66" rx="8" fill="#eaf4fb" stroke="#8cb7cf"/><text x="93" y="204" text-anchor="middle" font-weight="700">CPU</text><text x="93" y="226" text-anchor="middle">Add input + normalize</text>
<path d="M181 212 H207" stroke="#526774" fill="none" marker-end="url(#arrow)"/>
<rect x="213" y="178" width="175" height="66" rx="8" fill="#eaf5ef" stroke="#80b9ab"/><text x="300" y="204" text-anchor="middle" font-weight="700">FPGA</text><text x="300" y="226" text-anchor="middle">Two input matrices</text>
<path d="M388 212 H414" stroke="#526774" fill="none" marker-end="url(#arrow)"/>
<rect x="420" y="178" width="143" height="66" rx="8" fill="#eaf4fb" stroke="#8cb7cf"/><text x="491" y="204" text-anchor="middle" font-weight="700">CPU</text><text x="491" y="226" text-anchor="middle">Activation + gate</text>
<path d="M563 212 H589" stroke="#526774" fill="none" marker-end="url(#arrow)"/>
<rect x="595" y="178" width="142" height="66" rx="8" fill="#eaf5ef" stroke="#80b9ab"/><text x="666" y="204" text-anchor="middle" font-weight="700">FPGA</text><text x="666" y="226" text-anchor="middle">Output matrix</text>
<path d="M737 212 H763" stroke="#526774" fill="none" marker-end="url(#arrow)"/>
<rect x="769" y="178" width="121" height="66" rx="8" fill="#eaf4fb" stroke="#8cb7cf"/><text x="829" y="204" text-anchor="middle" font-weight="700">CPU</text><text x="829" y="226" text-anchor="middle">Add input</text>
<text x="6" y="282" fill="#526774">Repeat for each layer. After the last layer: final normalization → vocabulary scores → token selection.</text>
</g></svg></div>
<figcaption>This diagram shows dependency order. Query work can start before all new K and V values arrive. Dense matrix placement follows the design document. Attention routing follows the checked code. <a class="cite" href="#c3">[C3]</a> <a class="cite" href="#c5">[C5]</a></figcaption>
</figure>
<ul>
<li>Q, K, and V are the query, key, and value vectors. Their projections are matrix multiplications that create those vectors.</li>
<li>Normalization rescales the input vector. Position transforms add token-position information. The activation and gate transform and combine the feed-forward vectors.</li>
<li>The CPU can score already cached KV after Q becomes ready. It handles pending KV after their producer finishes. <a class="cite" href="#c3">[C3]</a></li>
<li>A join combines partial attention results. Some join time is useful merge work. Some is waiting for a device or another worker. <a class="cite" href="#c1">[C1]</a></li>
<li>Weights are loaded into the accelerator’s memory for execution. Per-token host transfers carry intermediate vectors and relevant KV data. Estimate transfers from actual buffers and placement. <a class="cite" href="#c5">[C5]</a></li>
</ul>
<div class="note"><p>The dense layer is the part to memorize. For GPT-OSS, add expert selection, the selected expert matrices, and their weighted combination. GPT-OSS 120B’s total parameter count includes all experts. Each token selects 4 of 128 experts per layer. <a class="cite" href="#m-gpt120">[M7]</a></p></div>
</section>

<section id="routes">
<span class="number">03 · Separate the two decisions</span><h2>AoF and AMX can be enabled together</h2>
<p>AoF controls eligible attention ranges on the accelerator. The remaining CPU attention chooses AMX or AVX page by page. Switching AoF off leaves the other accelerator matrix operations in place. <a class="cite" href="#c2">[C2]</a> <a class="cite" href="#c4">[C4]</a> <a class="cite" href="#c5">[C5]</a></p>
<div class="scroll"><table><thead><tr><th>Configuration</th><th>Eligible full-attention ranges</th><th>CPU remainder and window layers</th></tr></thead><tbody>
<tr><td>AoF off · AMX off</td><td>CPU AVX</td><td>CPU AVX</td></tr>
<tr><td>AoF off · AMX on</td><td>CPU AMX on eligible pages; AVX elsewhere</td><td>Same per-page test</td></tr>
<tr><td>AoF on · AMX off</td><td>FPGA where the hardware plan assigns work</td><td>CPU AVX</td></tr>
<tr><td>AoF on · AMX on</td><td>FPGA where the hardware plan assigns work</td><td>CPU AMX on eligible pages; AVX elsewhere</td></tr>
</tbody></table></div>
<div class="two">
<div class="card"><h3>AMX needs every condition</h3><ul>
<li>The build includes <code>TRON_AMX_DISPATCH</code>.</li>
<li>The CPU and operating system allow AMX.</li>
<li><code>TRON_AMX_DISABLE</code> is not exactly <code>1</code>.</li>
<li>Queries use bf16, with a head width of 128 elements and 4 query heads per KV head.</li>
<li>The full 64-token page is visible and inside the query’s window.</li>
</ul><p class="small muted">These are the rules in the measured build. A later kernel can change them. <a class="cite" href="#c2">[C2]</a></p></div>
<div class="card"><h3>AoF needs an eligible operation</h3><ul>
<li>Model geometry, the device, and runtime policy must allow it.</li>
<li>The layer must have a hardware candidate operation and a supported attention scale.</li>
<li>Windowed attention remains on the CPU in this build.</li>
<li>The hardware plan can leave partial or newly written ranges on the CPU.</li>
</ul><p class="small muted"><code>USE_HW_ATTN=0</code> disables AoF. A positive value enables policy and sets a rounded engagement threshold. It does not bypass the model checks. <a class="cite" href="#c4">[C4]</a></p></div>
</div>
<p class="note warning">Use the path counters to confirm execution. An “AMX on” run can record zero AMX keys. That is exactly what happened for GPT-OSS in this example. <a class="cite" href="#r1">[R1]</a></p>
</section>

<section id="shapes">
<span class="number">04 · Keep a model card</span><h2>The model family is not enough</h2>
<p>The table uses representative sizes from your three families. <span class="symbol">Hq</span> is the query-head count. <span class="symbol">Hkv</span> is the KV-head count. <span class="symbol">h</span> is the number of elements in one head. <span class="symbol">g = Hq / Hkv</span> is the number of query heads sharing each KV head.</p>
<div class="scroll"><table class="models"><thead><tr><th>Model</th><th class="num">Layers</th><th class="num">Hq / Hkv</th><th class="num">h</th><th class="num">g</th><th>Attention layout</th><th>Matches this AMX shape?</th></tr></thead><tbody>@@MODEL_ROWS@@</tbody></table></div>
<ul>
<li>Llama 3.1 8B matches the current AMX geometry. The other runtime and per-page conditions still apply.</li>
<li>These Qwen 2.5 configurations have sliding windows disabled. Their <code>sliding_window</code> field alone would give the wrong conclusion. <a class="cite" href="#m-qwen7">[M3–M5]</a></li>
<li>GPT-OSS alternates a 128-token window with full attention. Its 8-query-head × 64-element group needs a different AMX kernel and query packing. <a class="cite" href="#m-gpt120">[M6–M7]</a> <a class="cite" href="#c2">[C2]</a></li>
</ul>
<details><summary>Dimensions for the matrix-multiplication estimate</summary>
<p class="small"><span class="symbol">d</span> is the hidden-vector width. <span class="symbol">m</span> is the feed-forward intermediate width, per expert where applicable. <span class="symbol">V</span> is the vocabulary size. All widths count elements. Expert counts are per layer.</p>
<div class="scroll"><table><thead><tr><th>Model</th><th class="num">d</th><th class="num">m</th><th class="num">V tokens</th><th>Expert selection</th></tr></thead><tbody>@@DIM_ROWS@@</tbody></table></div>
<p class="small muted">Llama’s intermediate widths are derived using Meta’s feed-forward rounding rule. <a class="cite" href="https://github.com/meta-llama/llama-models/blob/main/models/llama3/model.py#L188-L204">[Meta implementation]</a> GPT-OSS has query width <code>64 × 64 = 4,096</code> elements, although its hidden width is 2,880 elements. Use explicit head dimensions in the projection formulas.</p>
</details>
</section>

<section id="work">
<span class="number">05 · Count before assigning time</span><h2>Three calculations cover most of the work</h2>
<h3>Attention work in a decode forward</h3>
<p>Let <span class="symbol">B</span> be query tokens in this forward, and <span class="symbol">S</span> be visible keys per query, including the current token. Ordinary decode usually has one query per active user. Let <span class="symbol">Lfull</span> and <span class="symbol">Lwindow</span> count the two layer types.</p>
<div class="equation"><span>R = Lfull × S + Lwindow × min(S, 128)</span><span>key/head pairs = B × Hkv × R</span><span>QK + PV arithmetic ≈ 4 × B × Hq × h × R operations</span><span>logical KV scan = 2 × B × Hkv × h × R × 2 bytes</span></div>
<p class="small">QK is query–key scoring. PV multiplies attention weights by values. The arithmetic counts multiplication and addition separately. It omits normalization of the scores, position transforms, and merge work. The KV scan assumes bf16 and one read of K and V per query and KV head. Cache reuse, layout padding, and actual memory traffic need their own measurements.</p>
<div class="lab" id="work-lab">
<h3>Change the model or sequence length</h3>
<div class="controls"><label>Model<select id="model-select">@@MODEL_OPTIONS@@</select></label><label>Query tokens B<input id="query-count" type="number" min="1" max="65536" step="1" value="8"></label><label>Visible keys S per query<input id="visible-keys" type="number" min="1" max="1000000" step="1" value="1152"></label></div>
<div class="outputs" aria-live="polite"><div class="output"><span class="value" id="work-pairs">—</span><span class="unit">key/head pairs across all layers</span></div><div class="output"><span class="value" id="work-ops">—</span><span class="unit">billion QK + PV operations, approx.</span></div><div class="output"><span class="value" id="work-bytes">—</span><span class="unit">MiB logical KV scan; 1 MiB = 2²⁰ bytes</span></div></div>
<div id="work-split" class="chart" aria-label="Full and window layer work"></div>
<p id="work-status" class="status" aria-live="polite"></p>
<p class="small muted">All values here are calculated work amounts. They are not timing measurements. Default S = 1,152 tokens is a round example near the measured run’s average history. The exact run includes a different S at each step.</p>
</div>
<h3 style="margin-top:28px">Prefill counts every query’s history</h3>
<p>For a fresh causal prompt of <span class="symbol">P</span> tokens, full attention has <span class="symbol">P(P + 1) / 2</span> query–key pairs per head and layer. For a window of <span class="symbol">W</span> tokens, use <span class="symbol">Σ min(i, W)</span> for <span class="symbol">i = 1…P</span>. For <span class="symbol">P &gt; W</span>, this is <span class="symbol">W(W + 1)/2 + (P − W)W</span> pairs.</p>
<p>Prompt chunks with cached history use each new query’s actual visible keys. Prefix reuse can remove work. Reuse also changes memory traffic. Keep prefill and decode cost measurements separate.</p>
<details><summary>Matrix arithmetic, memory traffic, and the limit of peak-rate estimates</summary>
<p>One matrix with <span class="symbol">a × b</span> weights applied to <span class="symbol">B</span> vectors costs approximately <span class="symbol">2Bab</span> arithmetic operations. For the layer’s attention projections, sum Q, K, V, and the output projection:</p>
<div class="equation"><span>projection weights = 2 × d × h × (Hq + Hkv)</span><span>dense feed-forward weights = 3 × d × m</span><span>selected expert weights per token = 3 × k × d × m</span><span>final vocabulary projection weights = d × V</span></div>
<p class="small"><span class="symbol">k</span> is selected experts per token. These formulas count matrix elements used, excluding biases and the expert router. Multiply by 2 operations per multiply-add and the appropriate token count. The vocabulary projection runs for tokens requiring output scores. Across a batch, selected experts can differ, so distinct expert weights read are the union of those selections.</p>
<p>For one stage with overlapping compute and memory access, a first lower estimate is:</p>
<div class="equation">stage time est. ≳ max(operations / measured operation rate, bytes moved / measured bandwidth) + exposed fixed overhead</div>
<p class="small">Use rates for the same matrix shape, batch, data format, and hardware placement. If compute and transfer happen in sequence, add their times. Peak specifications do not supply the missing utilization, queueing, or synchronization cost. <strong>Insufficient data</strong> for an absolute latency prediction here: matching device-operation and transfer measurements are needed.</p>
</details>

<h3 style="margin-top:28px">Full pages inside a sliding window</h3>
<p>A 128-token window can overlap three 64-token pages. The two end pages are partial unless the window starts at a page boundary. Only complete visible pages qualify for this AMX implementation’s dense-page rule. <a class="cite" href="#c2">[C2]</a></p>
<div class="lab">
<label for="page-offset">Window start within its first page: <output id="offset-value">1 token</output></label><input id="page-offset" type="range" min="0" max="63" step="1" value="1">
<div id="page-chart" class="chart"></div>
<div class="legend"><span><i class="swatch teal"></i>Full-page candidate</span><span><i class="swatch orange"></i>Visible part of a partial page</span><span><i class="swatch wait"></i>Outside the window</span></div>
<p id="page-summary" class="status" aria-live="polite"></p>
<p class="small muted">One contiguous window with no prefix split is shown. Averaged equally over all 64 start offsets: <code>(128 + 63 × 64) / 64 = 65</code> candidate keys per query. That is <code>65 / 128 = 50.78125%</code> of window keys. This matches the completed run’s candidate count. GPT-OSS still fails the current AMX shape check.</p>
</div>
</section>

<section id="elapsed">
<span class="number">06 · Put work on the clock</span><h2>Time the dependency that finishes last</h2>
<p>Use a common start time for all branches. For the simplified attention schedule below, all durations and arrival times are in microseconds:</p>
<div class="equation"><span>CPU done = max(Q ready + ready-page work, KV ready) + pending-page work</span><span>attention done = max(CPU done, FPGA done, other workers done) + merge work</span></div>
<p>“Ready” pages already hold their KV. “Pending” pages are updated in this forward. The formula follows Tron’s ready pass, KV wait, pending pass, and join. Streamed joins can merge earlier partials before the final result arrives. Use a trace for their exact overlap. <a class="cite" href="#c3">[C3]</a></p>
<div class="lab">
<h3>Wall-clock lanes: why less CPU work may save no time</h3>
<p class="small">This is an assumed schedule for teaching the dependency rule. It is not a reconstruction of the GPT-OSS trace. Both producers start at 0 µs. “Merge” means useful merge work after both results arrive.</p>
<div class="controls four"><label>CPU work, assumed µs<input id="lane-cpu" type="number" min="1" max="10000" step="1" value="30"></label><label>FPGA work, assumed µs<input id="lane-fpga" type="number" min="1" max="10000" step="1" value="90"></label><label>Merge, assumed µs<input id="lane-merge" type="number" min="0" max="1000" step="1" value="6"></label><label>CPU work speedup, assumed ×<input id="lane-speed" type="number" min="1" max="100" step="0.1" value="2"></label></div>
<div class="buttons"><button id="device-last" type="button">Example: FPGA finishes last</button><button id="cpu-last" type="button">Example: CPU finishes last</button></div>
<div class="diagram-scroll" id="lane-chart"></div>
<div class="legend"><span><i class="swatch"></i>CPU work</span><span><i class="swatch teal"></i>FPGA work</span><span><i class="swatch wait"></i>Wait or idle</span><span><i class="swatch red"></i>Critical branch and final merge</span></div>
<p id="lane-status" class="status" aria-live="polite"></p>
<p class="small muted">Durations are to scale on one shared axis. Dashed rectangles include spin-wait if a real worker polls during that interval. The simple merge shown here waits for both complete results.</p>
</div>
<p class="note">Build the full forward from these dependencies, then add the final vocabulary projection and token-delivery work. Add sequential stages. Use the latest finish time for concurrent prerequisites. Count each interval once.</p>
<h3>Keep throughput and user latency separate</h3>
<ul>
<li>For ordinary steady decode with <span class="symbol">B</span> users, aggregate throughput is approximately <span class="symbol">B / Tforward</span> tokens per second. Per-user output spacing is approximately <span class="symbol">Tforward</span>.</li>
<li>TTFT means time to first token. It includes the prompt forwards on the request’s path and any request-level overhead.</li>
<li>Mixed batches and speculative decoding change tokens produced per forward. Read the output count before converting a forward time to tokens per second.</li>
</ul>
</section>

<section id="case">
<span class="number">07 · Rework the conversation from evidence</span><h2>What the GPT-OSS example actually establishes</h2>
<p>The completed run used GPT-OSS 120B, 8 users, prompt length 1,024 tokens before the added start token, AoF enabled, and AMX enabled. It used 4 accelerator devices and 40 attention workers. All CPU attention still took the AVX path. <a class="cite" href="#r1">[R1]</a></p>
<div class="outputs"><div class="output"><span class="value">@@T_MS@@ ms</span><span class="unit">measured mean forward time</span></div><div class="output"><span class="value">10.19%</span><span class="unit">scored key/head pairs on CPU</span></div><div class="output orange"><span class="value">0 keys</span><span class="unit">executed with AMX in this run</span></div></div>
<figure class="diagram"><div id="case-chart" class="diagram-scroll">@@CASE_CHART@@</div><figcaption>These bars count scored keys, once per KV head. They do not divide elapsed time. The 18 window layers contribute about 10.00% of all keys, despite being half the layers. <a class="cite" href="#r1">[R1]</a></figcaption></figure>
<div class="scroll"><table><thead><tr><th>Completed-run count</th><th class="num">Key/head pairs</th><th class="num">Share of all pairs</th></tr></thead><tbody>
<tr><td>18 window layers, CPU AVX</td><td class="num">37,748,736</td><td class="num">9.9961%</td></tr><tr><td>18 full layers, CPU remainder</td><td class="num">737,280</td><td class="num">0.1952%</td></tr><tr><td>18 full layers, FPGA</td><td class="num">339,148,800</td><td class="num">89.8087%</td></tr><tr><td>All paths</td><td class="num">377,634,816</td><td class="num">100.0000%</td></tr><tr><td>Full-page candidates within CPU window work</td><td class="num">19,169,280</td><td class="num">5.0761%</td></tr>
</tbody></table></div>
<p class="small">The final row is a subset of the first row. CPU counters already count each KV head. To compare FPGA work in the same unit, use <code>fpga_k_tokens_x_kv_heads</code>. The raw <code>fpga_k_tokens</code> count is smaller by 8 KV heads here. <a class="cite" href="#c1">[C1]</a> <a class="cite" href="#r1">[R1]</a></p>
<h3>Worker time is a second kind of evidence</h3>
<p>The copied layer counters give the following averages across the 18 window layers. Each layer is normalized by its own attention-job count before summing. The copies were taken at different progress points. These values describe average worker service, not one synchronized forward. <a class="cite" href="#r2">[R2]</a></p>
<div class="scroll"><table><thead><tr><th>Snapshot-derived quantity</th><th class="num">Time per average worker</th><th>What it contains</th></tr></thead><tbody>
<tr><td>Attention busy time, T2</td><td class="num">@@BUSY_MS@@ ms</td><td>Both CPU passes, merge work, and join waiting</td></tr>
<tr><td>Join waiting, T5</td><td class="num">@@JOIN_MS@@ ms</td><td>Failed join polls; already inside T2</td></tr>
<tr><td>T2 − T5</td><td class="num">@@NONJOIN_MS@@ ms</td><td>Compute and merge work; not a pure QK/PV kernel timer</td></tr>
</tbody></table></div>
<ul>
<li>The image’s roughly 0.649 ms busy budget is reproducible. The layer-by-layer normalization here gives about 0.118 ms join wait, close to the image’s 0.119 ms value.</li>
<li>The completed counters give 50.78125% full-page coverage of window keys. The copied counters give about 50.9%. Use the completed counters for the work fraction.</li>
<li>The mean worker’s 0.530 ms outside join waiting is about 5.17% of mean forward time. Calling it a removable elapsed-time ceiling requires an unproven assumption about worker balance and overlap.</li>
<li>The image’s roughly 55 µs “KV wait” subtracts average worker busy time from one worker’s elapsed time. That subtraction cannot isolate one worker’s KV wait. Query readiness and other excluded work also need separate boundaries. <a class="cite" href="#c1">[C1]</a> <a class="cite" href="#c3">[C3]</a></li>
</ul>
<p class="note warning"><strong>Insufficient data for the new kernel’s decode gain.</strong> The missing evidence is an 8-query-head × 64-element kernel measurement on these page shapes, plus a matched trace or end-to-end comparison showing how much of its saved service time reaches the forward boundary.</p>
<details><summary>Why the prefill estimate needs a separate calculation</summary>
<p>The run has 8 prompt-or-mixed forwards averaging <strong>335.064 ms per forward</strong>. The requests report about <strong>2.730 seconds TTFT</strong>. These are different measurement boundaries. The prompt is processed across multiple forwards. <a class="cite" href="#r1">[R1]</a></p>
<p>The conversation’s 3–4% TTFT estimate transfers a kernel factor from other shapes and assumes it reaches request completion. Treat it as an est. scenario. Measure eligible service time during prefill, expert/device work, and overlap for those prompt chunks before turning it into a prediction.</p>
<p>The window’s logical K and V data total <code>2 × 128 × 64 × 2 = 32,768 bytes</code> per KV head, or 32 KiB. A full layer with 1,152 visible keys has 288 KiB per KV head under the same calculation. Those different sizes can change cache behavior. Measure the new kernel with the relevant working set.</p>
</details>
</section>

<section id="gain">
<span class="number">08 · Make the assumptions explicit</span><h2>Convert saved work into a timing estimate</h2>
<p>Start with a measured service budget for the code being replaced. Let <span class="symbol">c</span> be the fraction of that time eligible for replacement. Let <span class="symbol">r</span> be the fractional reduction of that eligible time. Let <span class="symbol">e</span> be the fraction of saved service time that advances the forward’s completion. Let <span class="symbol">H</span> be added exposed overhead.</p>
<div class="equation"><span>forward time saved est. = C × c × r × e − H</span><span>time reduction est. = saved / original time</span><span>throughput increase est. = original time / (original time − saved) − 1</span></div>
<p>A kernel speedup of <span class="symbol">s</span> gives <span class="symbol">r = 1 − 1/s</span>. A 2× kernel gives a 50% service-time reduction. For a schedule with several dependencies, calculate the before-and-after finish times directly when possible.</p>
<div class="lab">
<h3>A conditional estimate for the GPT-OSS window layers</h3>
<p class="small">The 0.530459 ms budget is a snapshot-derived proxy. Using it assumes that the average worker represents the worker controlling completion. The starting 50.78125% coverage assumes that key share equals service-time share. Kernel gain and exposed share are deliberately blank until supplied. All outputs are estimates.</p>
<div class="controls four">
<label>Service budget C, ms<input id="gain-budget" type="number" min="0" max="1000" step="any" value="@@NONJOIN_EXACT@@"></label>
<label>Eligible service share c, assumed %<input id="gain-coverage" type="number" min="0" max="100" step="any" value="50.78125"></label>
<label>Eligible service reduction r, %<input id="gain-reduction" type="number" min="0" max="100" step="any" placeholder="Insufficient data"></label>
<label>Exposed saved share e, %<input id="gain-exposure" type="number" min="0" max="100" step="any" placeholder="Insufficient data"></label>
<label>Added exposed overhead H, µs<input id="gain-overhead" type="number" min="0" max="1000000" step="any" value="0"></label>
<label>Baseline forward time, ms<input id="gain-baseline" type="number" min="0.000001" max="100000" step="any" value="@@T_EXACT@@"></label>
</div>
<div class="buttons"><button type="button" id="gain-twofold">Assume 2× eligible service; all savings exposed</button><button type="button" id="gain-proxy">Assume 12–16% eligible service reduction</button><button type="button" id="gain-reset">Restore missing measurements</button></div>
<div class="outputs" aria-live="polite"><div class="output"><span class="value" id="gain-saved">Insufficient data</span><span class="unit">forward time saved, ms est.</span></div><div class="output"><span class="value" id="gain-percent">—</span><span class="unit">forward time reduction, % est.</span></div><div class="output"><span class="value" id="gain-throughput">—</span><span class="unit">throughput increase, % est.</span></div></div>
<p id="gain-status" class="status" aria-live="polite"></p>
</div>
<h3 style="margin-top:27px">How to read “under 1%” in the conversation</h3>
<p>The image applies a 12–16% service reduction from other model runs to roughly half of the 0.649 ms busy budget. That arithmetic gives about 0.040–0.053 ms saved, or 0.39–0.51% of the 10.261 ms forward. These are est. values. The transfer of that reduction to GPT-OSS and its exposure on the critical path remain assumptions. <a class="cite" href="#r3">[R3]</a></p>
<p>The calculator instead starts with the measured proxy after removing join waiting. It still includes merge work. A useful next measurement isolates the actual eligible kernel service time. This avoids assigning a kernel’s speedup to time spent elsewhere.</p>
</section>

<section id="handy">
<span class="number">09 · Your working reference</span><h2>Keep one measured cost sheet per configuration</h2>
<p>A useful sheet records what a cost means and where it applies. Fill it from the same build and execution mode you intend to estimate.</p>
<div class="scroll"><table><thead><tr><th>Keep</th><th>Record with it</th><th>Use it for</th></tr></thead><tbody>
<tr><td>Model and run identity</td><td>Exact model, build commit, device count, format, AoF policy, AMX availability, worker split</td><td>Prevent comparisons across different execution paths</td></tr>
<tr><td>Work shape</td><td>Query count, per-query visible keys, layer/window type, full-page fraction, prefix reuse</td><td>Choose a matching cost measurement</td></tr>
<tr><td>CPU service costs</td><td>µs per complete page and partial page, Q packing, merge work, effective parallelism</td><td>Estimate CPU completion and partial-page overhead</td></tr>
<tr><td>Device operation costs</td><td>µs for each projection/expert shape and AoF range, with batch and placement</td><td>Estimate device result arrival times</td></tr>
<tr><td>Transfer and readiness</td><td>Bytes moved, start/finish times, Q/KV ready times, queue delays</td><td>Identify gaps and overlap</td></tr>
<tr><td>End-to-end baseline</td><td>Prompt and decode forwards separately, TTFT, token spacing, output count, run variation</td><td>Check whether component estimates explain user-visible time</td></tr>
</tbody></table></div>
<h3>The timer card</h3>
<div class="scroll"><table><thead><tr><th>Counter</th><th>Meaning</th><th>How to use it</th></tr></thead><tbody>
<tr><td>T1: forward wall</td><td>Elapsed time inside one model forward, through output delivery and cleanup</td><td><code>wall_cycles / forwards / tsc_hz</code> gives seconds</td></tr>
<tr><td>T2: attention busy</td><td>One worker’s ready/pending passes and join; excludes upstream KV wait</td><td>Service budget; T5 is already included</td></tr>
<tr><td>T3: worker-0 attention wall</td><td>One attention worker’s job entry to return</td><td>Compare only with matched work on that worker</td></tr>
<tr><td>T4: worker-0 period</td><td>First attention job of one operation to first job of the next</td><td>Use <code>period_count</code>; the last operation lacks a following period</td></tr>
<tr><td>T5: join wait</td><td>Failed join polls inside T2</td><td>Subtract once to get compute plus merge service</td></tr>
</tbody></table></div>
<p class="small">TSC is the time-stamp counter. <code>tsc_hz</code> is its ticks per second. It is not the CPU’s changing core clock. For aggregate worker counters, divide by the matching job count before treating the result as an average. Never add the workers’ times to obtain elapsed time. <a class="cite" href="#c1">[C1]</a></p>
<div class="two">
<div class="card"><h3>A manual estimate on one sheet</h3><ol class="worksheet">
<li>Write the target: TTFT, forward time, or output-token spacing.<span class="line"></span></li>
<li>Write the model shape, query count, and visible history.<span class="line"></span></li>
<li>Mark CPU and FPGA work for each layer type.<span class="line"></span></li>
<li>Multiply work counts by matching service costs.<span class="line"></span></li>
<li>Draw ready times and take the latest required finish.<span class="line"></span></li>
<li>Sum sequential layers and final output work. Compare with T1.<span class="line"></span></li>
</ol></div>
<div class="card"><h3>How to build intuition from existing runs</h3><ul>
<li>First predict which counters can change when one option changes. Check that prediction against the recorded path counts.</li>
<li>Keep paired AoF-on/off measurements at the same model shape. Keep paired AMX-on/off measurements only where AMX actually executes.</li>
<li>Compare different sequence lengths at the same batch. Full-layer attention work should grow with visible history. Window-layer work stops growing after its window fills.</li>
<li>Compare small and large batches separately. More queries can change reuse, worker balance, and hardware launch timing.</li>
<li>Use repeated runs to judge a small predicted gain. The example used one repetition per configuration.</li>
</ul><p class="small muted">The checked build chooses early hardware launch at 4 or more query jobs by default. Smaller batches launch after current KV saves. This is a scheduling threshold, separate from AoF eligibility. <a class="cite" href="#c3">[C3]</a></p></div>
</div>
</section>

<section id="sources">
<span class="number">10 · Evidence you can audit</span><h2>Sources and exact arithmetic</h2>
<p class="small">All implementation claims refer to the measured build’s commit. Model dimensions come from the publishers’ configurations. The user-supplied image sets the question; the raw logs supply the measured numbers.</p>
<ol class="source-list">
<li id="r1"><strong>R1 · Completed GPT-OSS run.</strong> <a href="@@LOG_PATH@@">Raw log: gptoss-8u-p1024-fpga__fpga__amxon__rep1.log</a>. Run dated 2 October 2026. Final <code>attn-stats</code> records contain 256 decode-like forwards and the path counts used above. The run log also contains request TTFT and the hardware configuration. The <a href="@@BUILD_PATH@@">build record</a> supplies the exact commit and confirms AMX dispatch was compiled.</li>
<li id="r2"><strong>R2 · Copied layer counters.</strong> <a href="@@LEAVES_PATH@@/summary">Snapshot metadata</a> and <a href="@@LEAVES_PATH@@/decode_like_layer_0">example layer-0 counter</a>. Even-numbered layers 0 through 34 are the 18 window layers. These live counter files were copied separately, so their progress differs.</li>
<li id="r3"><strong>R3 · Your conversation image.</strong> <a href="image.png">image.png</a>. This is the source for the discussion of the proposed 8 × 64 AMX kernel and the earlier conditional speedup estimates. The Notion link was not used as measurement evidence.</li>
<li id="c1"><strong>C1 · Counter definitions.</strong> <a href="@@GH@@/h/tron/models/attn_stats.hpp#L18-L84">attn_stats.hpp</a>. Units, timer boundaries, forward classification, and live-read behavior.</li>
<li id="c2"><strong>C2 · AMX rules.</strong> <a href="@@GH@@/h/tron/kernels/amx_attn_iface.hpp#L7-L52">amx_attn_iface.hpp</a> and <a href="@@GH@@/h/tron/models/self_attention.hpp#L1710-L1721">dense-page predicate</a>. The measured implementation supports the 128-element, 4-query-head group.</li>
<li id="c3"><strong>C3 · Scheduling.</strong> <a href="@@GH@@/h/tron/models/model.hpp#L91-L129">early/late launch</a>, <a href="@@GH@@/h/tron/models/model.hpp#L1920-L1940">ready versus pending pages</a>, and <a href="@@GH@@/h/tron/models/self_attention.hpp#L774-L860">worker attention execution</a>.</li>
<li id="c4"><strong>C4 · AoF rules.</strong> <a href="@@GH@@/h/tron/models/model.hpp#L681-L762">model eligibility</a>, <a href="@@GH@@/h/tron/models/self_attention.hpp#L506-L514">operation and window eligibility</a>, and <a href="@@GH@@/src/tron/models/hw_attn_config.cpp">USE_HW_ATTN policy</a>.</li>
<li id="c5"><strong>C5 · Architecture.</strong> <a href="@@GH@@/doc/tron_design_document.md">Tron design document</a>. Used for the dense layer and device-worker map. The newer routing code above supplies the attention details.</li>
@@MODEL_SOURCES@@
</ol>
<details><summary>Reproduce the measured numbers</summary>
<div class="equation"><span>T1 = 7,092,208,900 ticks ÷ 256 forwards ÷ 2,699,992,417 ticks/s</span><span>   = 10.260747712 ms/forward</span><span>window keys = 18 layers × 2,097,152 = 37,748,736 key/head pairs</span><span>CPU full-layer remainder = 18 × 40,960 = 737,280 key/head pairs</span><span>FPGA keys = 42,393,600 × 8 KV heads = 339,148,800 key/head pairs</span><span>CPU share = (37,748,736 + 737,280) ÷ 377,634,816 = 10.1913315%</span><span>candidate keys = (294,912 + 4,608) visits × 64 keys = 19,169,280</span><span>candidate/window share = 19,169,280 ÷ 37,748,736 = 50.78125%</span></div>
<p class="small">For snapshot worker service, compute <code>Σlayer busy_cycles / attn_jobs / snapshot_tsc_hz</code> over the 18 window layers. Use the same expression for join waiting. Here <code>snapshot_tsc_hz = 2,699,992,391</code> ticks/s. The sum is 0.648675677 ms busy and 0.118216777 ms waiting. Their difference is 0.530458900 ms.</p>
<p class="small">In this run, one final prompt step also satisfies <code>decode_like</code>, the class where every token job has an output listener. The remaining 255 forwards are ordinary decode. Tokenization added a beginning token, producing 1,025 input tokens per request. Seven shared beginning tokens were reused. Preserve those definitions when reproducing the totals.</p>
<p class="small">A worker’s service time divided by T1 is a diagnostic ratio. It is not a measured fraction of the critical path. A new kernel must be measured before turning the conditional gain into a claim about this run.</p>
</details>
<details><summary>View the supplied conversation image</summary><img class="screenshot" src="@@IMAGE_DATA@@" width="2050" height="972" alt="Supplied Claude conversation about GPT-OSS CPU attention, full-page AMX coverage, and conditional decode and prefill speedup estimates."></details>
<p class="footer">Local source links require the original workspace. The article, diagrams, data, and calculators are contained in this HTML file. No external scripts, fonts, or network requests are required.</p>
</section>
</main></div>
<script id="evidence-data" type="application/json">@@FACTS@@</script>
<script id="model-data" type="application/json">@@MODELS@@</script>
<script>
@@SCRIPT@@
</script>
</body></html>
'''

# The interactive code is kept separate while the single-file artifact is built.
SCRIPT_PATH = Path('/tmp/tron_intuition_fresh.js')

def model_rows():
    rows = []
    for model in MODELS:
        g = model['q'] // model['kv']
        layout = f"{model['full']} full + {model['window']} window" if model['window'] else f"{model['full']} full"
        amx = '<span class="badge blue">Yes, if other gates pass</span>' if model['h'] == 128 and g == 4 else '<span class="badge">No</span>'
        rows.append(f'<tr><td>{model["name"]} <a class="cite" href="#m-{model["id"]}">[config]</a></td><td class="num">{model["layers"]}</td><td class="num">{model["q"]} / {model["kv"]}</td><td class="num">{model["h"]}</td><td class="num">{g}</td><td>{layout}</td><td>{amx}</td></tr>')
    return ''.join(rows)

def case_chart():
    rows = [('FPGA · full layers', fpga_keys, '#007c67'), ('CPU · window layers', window_keys, '#0072b2'), ('CPU · full-layer remainder', tail_keys, '#b94c00')]
    svg = ['<svg viewBox="0 0 860 220" role="img" aria-label="Share of scored keys: FPGA 89.81 percent, CPU window layers 10.00 percent, CPU full-layer remainder 0.20 percent. These are work shares, not time shares."><g font-family="system-ui,sans-serif" fill="#172e3b">']
    for i, (label, count, color) in enumerate(rows):
        y = 30 + 58*i
        width = count/all_keys*540
        svg.append(f'<text x="0" y="{y+16}" font-size="13">{label}</text><rect x="222" y="{y}" width="540" height="24" rx="3" fill="#eef2f3"/><rect x="222" y="{y}" width="{width:.5f}" height="24" fill="{color}"/><text x="842" y="{y+17}" text-anchor="end" font-size="14" font-weight="700">{count/all_keys*100:.2f}%</text>')
    svg.append('<text x="222" y="199" font-size="12" fill="#526774">0%</text><text x="762" y="199" text-anchor="end" font-size="12" fill="#526774">100% of scored keys</text></g></svg>')
    return ''.join(svg)

def build():
    replacements = {
        'MODEL_ROWS': model_rows(),
        'DIM_ROWS': ''.join(f'<tr><td>{m["name"]}</td><td class="num">{m["d"]:,}</td><td class="num">{m["m"]:,}</td><td class="num">{m["vocab"]:,}</td><td>{str(m["active"]) + " of " + str(m["experts"]) + " experts" if m["experts"] else "Dense"}</td></tr>' for m in MODELS),
        'MODEL_OPTIONS': ''.join(f'<option value="{m["id"]}"{" selected" if m["id"] == "gpt120" else ""}>{m["name"]}</option>' for m in MODELS),
        'MODEL_SOURCES': ''.join(f'<li id="m-{m["id"]}"><strong>M{i+1} · {m["name"]}.</strong> <a href="{m["source"]}">Publisher configuration</a>. The Qwen entries use the Instruct configurations.</li>' for i, m in enumerate(MODELS)),
        'T_MS': f'{facts["forwardMs"]:.3f}', 'BUSY_MS': f'{busy:.6f}', 'JOIN_MS': f'{join:.6f}', 'NONJOIN_MS': f'{busy-join:.6f}',
        'T_EXACT': f'{facts["forwardMs"]:.12f}', 'NONJOIN_EXACT': f'{busy-join:.12f}',
        'CASE_CHART': case_chart(), 'LOG_PATH': html.escape(str(LOG)), 'LEAVES_PATH': html.escape(str(LEAVES)), 'BUILD_PATH': html.escape(str(BASE/'build-main1002.txt')),
        'GH': f'https://github.com/positron-ai/tron/blob/{SHA}',
        'FACTS': json.dumps(facts), 'MODELS': json.dumps(MODELS),
        'IMAGE_DATA': 'data:image/png;base64,' + base64.b64encode((DEST.parent/'image.png').read_bytes()).decode(),
        'SCRIPT': SCRIPT_PATH.read_text(),
    }
    result = PAGE
    for key, value in replacements.items():
        result = result.replace('@@' + key + '@@', value)
    assert not re.search(r'@@[A-Z_]+@@', result)
    DEST.write_text(result)
    print(json.dumps({'file': str(DEST), 'bytes': DEST.stat().st_size, 'facts': facts}, indent=2))

if __name__ == '__main__':
    build()
