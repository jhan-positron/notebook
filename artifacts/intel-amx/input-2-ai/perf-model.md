# Context

Notion page, https://app.notion.com/p/positron-ai/Estimate-the-AMX-decode-boost-from-pre-AMX-data-in-plain-English-3cfd132d3cfd81fe8b79d71a428e7695?source=copy_link,  discussed why AVX measurement plus Intel AMX spec fell short of estimating AMX boost. Primary causes are waiting for data from DRAM at long prompt case, 8192 prompt tokens. This project takes those factors into account, add data wait time to perf modeling, measure AMX’s perf metrics using delphi-3bda - use the machine just as it is a cloud PC with AMX equipped Intel 6962P processor, but it does not have FPGA cards - and estimate AMX decode boost. The goal is to achieve parity with real measurement of AMX boost.

# Setup

Same as described in the Notion page, 1 user, qwen-3-4b-tp2, 8192 prompt length, 256 generate tokens.

# Perf model

Build the new perf model from the starting point as described at “The model in one picture”. For example, that model does not include data waits, the new model needs to add that. 

Again, this project focuses on defining the perf model and use the model to estimate AMX decode boost, so this project should not run AMX tron solution. It is ok to measure processor’s AMX metrics using non-tron software.

# Exit condition

The estimate is on par, or close enough, to the measure AMX decode boost.

# Data, script, tooling

It is ok to use existing data, need to double check and confirm 100% applicability of those data. If there are any doubt, please measure the data afresh.

Similar requirement to tooling. E.g. rerun perf capture if have doubt.

delphi-3bda just did some hardware change, some components changed to newer revision. HW's perf spec should stay same.

## Clock frequency

Clock frequency is not a major factor, skip the testing, just assume a sensible data.

# Output

Perf model

- break down of each layer
- proportion of each component of each layer
- arithmetic calculations leading to the final estimate

Use plain English. 

Generate HTML report to perf-model/ folder.

First, generate action plan HTML without using delphi-3bda; after CI finishes, do on machine testing. 

# Permission

No need to request permission, I grant you all.
