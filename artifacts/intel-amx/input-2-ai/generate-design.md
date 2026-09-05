This design markdown file will be part of PR3879, and it will be referenced by subsequent PR which leverage Intel AMX.

Generate the md file and add to PR3879.

# git location
tron/doc/intel-amx.md
- suggest some names, intel-amx-leveraged-features-design.md is better to capture the meaning, but is it too long?

# content

## AMX introduction
The content structure can be similar to `What AMX is` of tron-amx-distilled.html:
- Introduction
- Instruction set
- Throughput
- VNNI B-operand layout
- Precison
-- `What tron's two attention paths actually compute` is not needed
- What AMX requires from the system

tron-amx-distilled.html is quite verbose because its main purpose was rampup. Please be brief at design doc given that
the reviewers are all experts.

## AMX software attention, AKA PR3879
### target
The target is software attention. Forced software attention(USE_HW_ATTN=0) is the main target. FPGA attention flow will
benefit also.

### model
Primary model is qwen-3-4b-instruct-2507-tp2.

### mirror layout
Describe the mirror layout.

Explain Why keep two copies of K instead of just storing K transposed? This is Bill's question. Do not say his name.

### geometry 
Describe the geometry PR3879 supports. It can be a brief version of tron-amx-distilled.html's Supported geometry and model coverage
with the following changes:
- remove this part, "Is tensor-parallel (tp1/tp2/tp4) part of the geometry? No"
- remove "4.1.1 Why the kv_mul 3 / 5 / 8 models are not served — and what would break if the gate were simply forced open"




