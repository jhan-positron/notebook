# Extract the tp2 apply_page_range from a disassembly and summarise the K scoring loop.
# usage: python3 -I compare.py <dis file> <label>
import re, sys
SYM = "_ZN4tron14self_attentionINS_5modelINS_3llmIXtlNS_17llm_configurationELNS_10model_typeE0ELm4096ELm14336ELm32ELm32ELm8ELm128256ELm128ELf3db504f3ELm1ELm1ELm0ELNS_12rope_scalingE1EEENS_17make_llm_executorILb0ENS_8hardware16tp2_min1k_tensorENS7_7btensorENS7_7dtensorEEEEEEEE5stateINSD_5stateELm32EE16apply_page_rangeIXtlNS_18attention_geometryELm32EtlNS_11kv_geometryELm8ELm128EEEENS_14indexed_vectorINS_12token_job_idENS7_9dmatensorINS_4bf16ELm4096EJEEEEESt6vectorINS_7page_idESaISS_EEEEvRKSR_ISM_SaISM_EERKNS_30attention_operation_descriptorERT0_mmmRKT1_NS_15work_estimate_tERKNS_6mask_tILm4096EEEbbmm"
path, label = sys.argv[1], sys.argv[2]
lines = open(path, errors="replace").read().split("\n")
start = None
for i, l in enumerate(lines):
    if l.startswith("0") and l.rstrip().endswith("<" + SYM + ">:"):
        start = i; break
if start is None:
    print(label, "symbol not found"); sys.exit(1)
body = []
for l in lines[start+1:]:
    if l.strip() == "" : break
    body.append(l)
ins = [l for l in body if re.match(r"^\s*[0-9a-f]+:\s", l)]
base_addr = int(lines[start].split()[0], 16)
def off(l): return int(l.split(":")[0], 16) - base_addr
mn = [l.split(":",1)[1].strip() for l in ins]
n_vdp = sum(1 for m in mn if m.startswith("vdpbf16ps"))
n_call = sum(1 for m in mn if m.startswith("call"))
n_tz = sum(1 for m in mn if m.startswith("tzcnt"))
n_bts = sum(1 for m in mn if m.startswith("bts"))
print(f"{label}: apply_page_range {len(ins)} instructions, vdpbf16ps={n_vdp}, call={n_call}, tzcnt={n_tz}, bts={n_bts}")
# find the K scoring loop: the block containing the first 16 vdpbf16ps; print from 40 insns before to 10 after
idx = [i for i, m in enumerate(mn) if m.startswith("vdpbf16ps")]
first16 = idx[:16]
lo, hi = max(0, first16[0]-12), min(len(ins), first16[-1]+22)
print(f"--- {label} scoring block [{off(ins[lo]):#x} .. {off(ins[hi-1]):#x}] ({hi-lo} instructions)")
for l in ins[lo:hi]:
    print(f"{off(l):6x}: {l.split(':',1)[1].strip()}")
# memory-operand vdpbf16ps count (K re-read from memory) vs register form
mem = sum(1 for i in first16 if "(" in mn[i])
print(f"{label}: of the first 16 vdpbf16ps, {mem} take a memory operand, {16-mem} are register-only")
