# usage: python3 -I aprbody.py <dis> : print the tp2 apply_page_range body with offsets, symbols shortened
import re, sys
SYM = "_ZN4tron14self_attentionINS_5modelINS_3llmIXtlNS_17llm_configurationELNS_10model_typeE0ELm4096ELm14336ELm32ELm32ELm8ELm128256ELm128ELf3db504f3ELm1ELm1ELm0ELNS_12rope_scalingE1EEENS_17make_llm_executorILb0ENS_8hardware16tp2_min1k_tensorENS7_7btensorENS7_7dtensorEEEEEEEE5stateINSD_5stateELm32EE16apply_page_rangeIXtlNS_18attention_geometryELm32EtlNS_11kv_geometryELm8ELm128EEEENS_14indexed_vectorINS_12token_job_idENS7_9dmatensorINS_4bf16ELm4096EJEEEEESt6vectorINS_7page_idESaISS_EEEEvRKSR_ISM_SaISM_EERKNS_30attention_operation_descriptorERT0_mmmRKT1_NS_15work_estimate_tERKNS_6mask_tILm4096EEEbbmm"
lines = open(sys.argv[1], errors="replace").read().split("\n")
start = next(i for i, l in enumerate(lines) if l.startswith("0") and l.rstrip().endswith("<" + SYM + ">:"))
base = int(lines[start].split()[0], 16)
for l in lines[start+1:]:
    if l.strip() == "": break
    m = re.match(r"^\s*([0-9a-f]+):\s(.*)", l)
    if not m: continue
    off = int(m.group(1), 16) - base
    txt = re.sub(r"<" + re.escape(SYM) + r"\+0x([0-9a-f]+)>", lambda mm: "<+%x>" % int(mm.group(1), 16), m.group(2))
    print("%6x: %s" % (off, txt))
