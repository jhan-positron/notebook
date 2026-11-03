import sys
p='/home/jhan/workspace/random/from-claude/TRON-multiuser-attention-claude.html'
t=open(p,encoding='utf-8').read()
R=[
 ('because the V write packs the pair into one SIMD value [h/tron/models/model.hpp:232-237]',
  'because the V write packs the pair into one SIMD (single instruction, multiple data) register value [h/tron/models/model.hpp:232-237]'),
 ('In a prefill pass one prompt chunk shares one label.',
  'In a prefill pass (the pass that processes a new prompt) one prompt chunk shares one label.'),
 ('''is used in ML" [h/tron/models/common.hpp:938-939].</p>''',
  '''is used in ML" [h/tron/models/common.hpp:938-939]. ML means machine learning.</p>'''),
 ('''<dt>TP4</dt><dd>Four FPGA cards serving one model, with the weight matrices split among them.</dd>''',
  '''<dt>TP4</dt><dd>Four FPGA cards serving one model, with the weight matrices split among them.</dd>
<dt>matmul</dt><dd>Matrix multiplication. The projections and the FFN of each layer are matmuls, and TRON runs them on the FPGA.</dd>
<dt>FFN</dt><dd>Feed-forward network: the matmuls of a layer that follow attention.</dd>
<dt>prefill pass, decode pass</dt><dd>A prefill pass processes a new prompt, many tokens of one request at once. A decode pass adds one token per request.</dd>
<dt>Perfetto</dt><dd>The trace format and viewer that TRON's trace events go to [README.perfetto.md].</dd>
<dt>runtron</dt><dd>The TRON command-line runner, <code>src/runtron.cpp</code>.</dd>'''),
]
for o,n in R:
    c=t.count(o)
    if c!=1: print('FAIL count',c,o[:80]); sys.exit(1)
    t=t.replace(o,n)
open(p,'w',encoding='utf-8').write(t); print('terms ok')
