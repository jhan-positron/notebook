# Offline prune probe: how many of the 8-user config's 80 ShareGPT seeds (0-79) survive
# testlib/prompt.py prune_convo at prompt_length 1024 / 2048 / 4096 / 8192 with the
# llama-3.1-8b good tokenizer. Same code path as the harness (PromptGenerator.generate).
import os, sys, json, copy
sys.path.insert(0, "/home/jhan/workspace/ai-runs/systems_test")
os.environ["HF_HUB_OFFLINE"] = "1"; os.environ["TOKENIZERS_PARALLELISM"] = "false"
from testlib.prompt import PromptGenerator
pg = PromptGenerator.for_model("neuralmagic/Meta-Llama-3.1-8B-Instruct-quantized.w4a16")
convos0 = copy.deepcopy(pg.convos)
for L in (1024, 2048, 4096, 8192):
    pg.convos = copy.deepcopy(convos0)   # generate() inserts a system prompt in place
    ok = fail = 0; lens = []
    for seed in range(80):
        try:
            pg.generate(prompt_length=L, seed=seed); ok += 1
        except ValueError as e:
            fail += 1
    print(f"prompt_length {L}: ok {ok} fail {fail} of 80 seeds")
