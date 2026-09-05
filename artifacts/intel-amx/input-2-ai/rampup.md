Use PAL to deep work with gpt-5.6 sol if you are claude, or Claude Fable 5 if you are GPT codex, on the following tasks - make sure each delivery is from consensus of you both.

# context
Intel Xeon 6 6962P has a dedicated matrix calculation module, AMX. We like to use AMX to expedite attention and anything related.

The goal is to boost tron decode performance. The primary model is ingest qwen-3-4b-tp2.

# disclose unknown
I am new to AMX, please use HTML file to rump up my understanding: what is AMX, and how it could be leveraged; what does AMX require to system? E.g. system needs to be
configured in certain ways in order to fully leverage AMX; what trade-off need to be aware when using AMX.

I am not familar with tron implementation, please:
- identify the places of which replacing the current code with using AMX could boost decode perf
- illustrate architecture or relevant functionalities using wall-clock lane diagrams. Highlight the places to be replaced/updated from the previous point
- generate an implementation and test plan
- list system configure changes if needed
- use HTML

# Software attention is the target
This project targets software attentoin, not hw-attention.

# reference
/scratch/jhan/Intel_vs_AMD/refs has Intel documentation, the txt files are abstracted from pdf files. 

Cross check and confirm your claim, design, test plan, etc. with references.

# output
Generate HTML files to rampup/ folder, create it if not existing.

# Gate
Do the above without consulting Bill's PoC.

# Comment Bill's PoC
Bill conducted PoC work at branch bill-amx, and here is PR, https://github.com/positron-ai/tron/pull/2934, it has test data.
Scope his implementation with our action plan from previous point, and identify major gaps at
our plan. Not every model achieved good result at his PoC, analyze the reasons.
