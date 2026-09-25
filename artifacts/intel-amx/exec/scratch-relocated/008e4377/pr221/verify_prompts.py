"""Compare base vs head PromptGenerator output for every nightly config's seeds, with the real tokenizers."""
import ast, importlib.util, json, re, sys, time, copy, hashlib
from pathlib import Path
import transformers
transformers.logging.set_verbosity_error()
from transformers import AutoTokenizer
S = Path(sys.argv[1]); REPO = Path(sys.argv[2])

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
base = load('prompt_base', S / 'prompt_base.py')
head = load('prompt_head', REPO / 'testlib/prompt.py')
base_convos = json.load(open(S / 'sharegpt_base.json'))
head_convos = json.load(open(REPO / 'testlib/sharegpt_1000.json'))
hf = load('hf_models_stub', REPO / 'testlib/hf_models.py') if False else None
# hf_map without importing testlib (its import chain needs config): parse literal
src = open(REPO / 'testlib/hf_models.py').read()
tree = ast.parse(src)
hf_map = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign) and getattr(n.targets[0], 'id', '') == 'hf_map')
src = open(REPO / 'scripts/perf.py').read()
tree = ast.parse(src)
configs = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign) and getattr(n.targets[0], 'id', '') == 'configs')

TS = re.compile(r'\[TIME: [0-9:]+\] ')
def strip_ts(prompt):
    return json.dumps([{**p, 'content': TS.sub('', p['content'])} for p in prompt], sort_keys=True)

toks = {}
def tok(model):
    key = hf_map['-'.join(model.split('-')[:-1])]['hf']
    if key not in toks:
        toks[key] = AutoTokenizer.from_pretrained(key)
    return key, toks[key]

print(f"{'config':45s} {'tokenizer':55s} users prompt seeds same_as_base distinct(no ts) prepare_s")
for c in configs:
    key, t = tok(c['model'])
    n = c['nominal_users'] * 10
    L = c['prompt_length']
    b = base.PromptGenerator(copy.deepcopy(base_convos), t)
    h = head.PromptGenerator(copy.deepcopy(head_convos), t)
    t0 = time.time(); elig = h.prepare(L); prep = time.time() - t0
    same = 0; fails_b = 0; distinct = set(); hp = []
    for seed in range(n):
        try:
            pb = b.generate(prompt_length=L, seed=seed)
        except ValueError:
            pb = None; fails_b += 1
        ph = h.generate(prompt_length=L, seed=seed)
        hp.append(ph)
        distinct.add(strip_ts(ph))
        if pb == ph: same += 1
    print(f"{c['name'][:45]:45s} {key[:55]:55s} {c['nominal_users']:5d} {L:6d} {n:5d} {same:4d}/{n:<4d} base_fail={fails_b:<4d} {len(distinct):4d}/{n:<4d} eligible={len(elig):4d} {prep:6.1f}")
    if L == 4096:
        # token count check of the generated prompt content for the 4096 row, and NUL check
        nul = sum('\0' in p['content'] for ph in hp for p in ph)
        lens = []
        for ph in hp[:32]:
            total = 0
            for p in ph:
                prefix = f"<|start_header_id|>{p['role']}<|end_header_id|>\n"
                total += len(t.encode(prefix + p['content'])[1:])
            lens.append(total)
        print(f"   4096 row: prompts with NUL={nul}; re-encoded token totals of first 32 prompts min/max={min(lens)}/{max(lens)}; records used by seeds 0..319 distinct={len(set(elig[s % len(elig)] for s in range(n)))}")
