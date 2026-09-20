import sys, json, copy
sys.path.insert(0, sys.argv[1])
from testlib.prompt import PromptGenerator
tok = sys.argv[2]
pg = PromptGenerator.for_model(tok)
def ok(seed, L):
    # generate() mutates the convo (insert system prompt); work on a copy each time
    convo = copy.deepcopy(pg.convos[seed % len(pg.convos)]['conversations'])
    convo.insert(0, {'from': 'system', 'value': '[TIME: 00:00:00] You are a helpful assistant.'})
    try:
        pg.prune_convo(convo, L); return True
    except ValueError as e:
        return False
def length(seed):
    convo = copy.deepcopy(pg.convos[seed % len(pg.convos)]['conversations'])
    convo.insert(0, {'from': 'system', 'value': '[TIME: 00:00:00] You are a helpful assistant.'})
    n = 0
    for part in convo:
        from testlib.prompt import ROLES
        role = ROLES[part['from']]
        prefix = f"<|start_header_id|>{role}<|end_header_id|>\n"
        n += len(pg.tokenizer.encode(prefix + part['value'])[1:])
    return n
for L, seeds in [(1024, range(320)), (4096, range(80)), (8192, range(80))]:
    fails = [s for s in seeds if not ok(s, L)]
    print(f"prompt_length {L}: {len(fails)} of {len(seeds)} seeds fail", fails[:10])
lens = [(length(s), s) for s in range(320)]
print("shortest of 320:", min(lens))
