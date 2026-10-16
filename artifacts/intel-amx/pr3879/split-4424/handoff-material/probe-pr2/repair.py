import re, sys
W = "/home/jhan/workspace/ai-runs/tron-split-probe"

# 1. kv_cache.hpp: keep "ours" item 1 (PR-1 wording), take "theirs" items 2 and 3 (A wording).
p = f"{W}/h/tron/models/kv_cache.hpp"
s = open(p).read()
m = re.search(r"<<<<<<< ours\n(.*?)=======\n(.*?)>>>>>>> theirs\n", s, re.S)
assert m, "no conflict block"
ours, theirs = m.group(1), m.group(2)
ours_item1 = ours[: ours.index("//   2. ")]
theirs_from2 = theirs[theirs.index("//   2. ") :]
assert "set_k_block" not in ours_item1 and "set_k_block" not in theirs_from2
s = s[: m.start()] + ours_item1 + theirs_from2 + s[m.end() :]
open(p, "w").write(s)
print("kv_cache.hpp resolved")

# 2. amx_attn_iface.hpp: the S sentences of Note [QK orientation] -> one PR-2 sentence.
p = f"{W}/h/tron/kernels/amx_attn_iface.hpp"
s = open(p).read()
old = (
"// transpose is needed. The cost moves to two places. The K store scatters 64\n"
"// dimension pairs per token when the token's run has one token (save_k,\n"
"// page::set_k_row). A run of two or more consecutive tokens of one block uses\n"
"// the block save (page::set_k_block). The software reader for partial pages\n"
"// runs k_vnni::qk_group instead of the row-major dotter.\n")
new = (
"// transpose is needed. The price moves to the K store (a scatter of 64\n"
"// dimension pairs per token, in save_k) and to the software reader\n"
"// k_vnni::qk_group for partial pages.\n")
assert s.count(old) == 1, s.count(old)
s = s.replace(old, new)
open(p, "w").write(s)
print("amx_attn_iface.hpp rewritten")
