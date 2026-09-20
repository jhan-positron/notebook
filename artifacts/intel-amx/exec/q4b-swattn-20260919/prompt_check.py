#!/usr/bin/env python3
"""Offline check of PromptGenerator.generate after the concatenation change (qwen3-4b Saturday plan, section 3;
copied from exec/l8b-levers-20260919/prompt_check.py with the Qwen/Qwen3-4B-Instruct-2507 tokenizer and the 9 prompt lengths).

Runs in the systems_test .venv with HF_HUB_OFFLINE=1 and the qwen3-4b tokenizer (no BOS token: the re-encoded length
column drops one real token per part and is informational only). For prompt lengths
1024 to 8192 (9 lengths) and seeds 0-319 it records: exceptions (must be 0), the re-encoded token
length of the pruned prompt (informational: prune_convo's own count is exactly prompt_length whenever it does
not raise, by construction), the number of conversations concatenated, and a sha256 of every prompt so two
runs can be compared for determinism. At prompt 1024 it also checks that the new generate() returns exactly
what the previous code (systems_test fc27f07) returned. The stored conversation lists are hashed before and
after all calls: they must not change (the previous code mutated them in place).

qwen-specific: prune_convo encodes "<|start_header_id|>role<|end_header_id|>\n" + text, drops token [0] (the BOS
token for llama) and decodes; the qwen tokenizer adds no BOS, so a real token is dropped and every part's content
loses its first few characters (the system line "[TIME: hh:mm:ss] You are a helpful assistant." comes back as
"IME: ..." or similar). The nightly runs the same code for this model, so the campaign keeps it (plan section 3,
"fidelity-neutral"). The check therefore requires the first part to be a system part whose content is a suffix of
the intended system line, and records the number of dropped characters per prompt (dropped_chars_hist).

usage: prompt_check.py run OUT.json | prompt_check.py compare RUN1.json RUN2.json
"""
import hashlib
import json
import os
import sys
import time

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
ST = "/home/jhan/workspace/ai-runs/systems_test"
sys.path.insert(0, ST)
from testlib.prompt import PromptGenerator  # noqa: E402

TOKENIZER = "Qwen/Qwen3-4B-Instruct-2507"
LENGTHS = [1024, 1536, 2048, 3000, 4096, 5120, 6144, 7168, 8192]
SEEDS = range(0, 320)


def system_prompt_for(seed):
    ix = str(seed)
    ps = ix.rjust(max(6, int((len(ix) + 1) / 2 * 2)), '0')
    fake_time = ':'.join([ps[i:i + 2] for i in range(0, len(ps), 2)])
    return {'from': 'system', 'value': f'[TIME: {fake_time}] You are a helpful assistant.'}


def original_generate(gen, prompt_length, seed):
    """generate() of systems_test fc27f07, on a copy of the stored list (the original mutated it)."""
    convo = list(gen.convos[seed % len(gen.convos)]['conversations'])
    convo.insert(0, system_prompt_for(seed))
    return gen.prune_convo(convo, prompt_length)


def conversations_needed(gen, prompt_length, seed):
    """The k of the new loop, recomputed here (generate() does not return it)."""
    base = list(gen.convos[seed % len(gen.convos)]['conversations'])
    k = 1
    while gen._token_count([system_prompt_for(seed)] + base) < prompt_length:
        base = base + list(gen.convos[(seed + k) % len(gen.convos)]['conversations'])
        k += 1
    return k


def reencoded_len(gen, prompt):
    n = 0
    for part in prompt:
        prefix = f"<|start_header_id|>{part['role']}<|end_header_id|>\n"
        n += len(gen.tokenizer.encode(prefix + part['content'])[1:])
    return n


def sha(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def run(out):
    gen = PromptGenerator.for_model(TOKENIZER)
    rec = {"tokenizer": TOKENIZER, "lengths": LENGTHS, "seeds": [SEEDS.start, SEEDS.stop - 1],
           "systems_test_head": open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "systems_test.head")).read().strip(),
           "convos_sha256_before": sha(gen.convos), "cells": {}, "exceptions": [], "identity_1024_mismatches": []}
    for L in LENGTHS:
        t0 = time.time()
        hashes, reenc, nparts, ks, dropped = [], [], [], [], []
        for seed in SEEDS:
            try:
                p = gen.generate(prompt_length=L, seed=seed)
            except Exception as exc:  # the check records every failure; nothing is skipped silently
                rec["exceptions"].append({"prompt_length": L, "seed": seed, "error": repr(exc)[:300]})
                continue
            hashes.append(sha(p))
            reenc.append(reencoded_len(gen, p))
            nparts.append(len(p))
            ks.append(conversations_needed(gen, L, seed))
            exp_sys = system_prompt_for(seed)['value']
            if p[0]['role'] != 'system' or not exp_sys.endswith(p[0]['content']) or len(p[0]['content']) < len('] You are a helpful assistant.'):
                rec["exceptions"].append({"prompt_length": L, "seed": seed, "error": f"first part is not (a suffix of) the system line: {p[0]!r}"[:300]})
            else:
                dropped.append(len(exp_sys) - len(p[0]['content']))
            if L == 1024 and p != original_generate(gen, L, seed):
                rec["identity_1024_mismatches"].append(seed)
        rec["cells"][str(L)] = {
            "n_ok": len(hashes), "n_exceptions": sum(1 for e in rec["exceptions"] if e["prompt_length"] == L),
            "seconds": round(time.time() - t0, 1), "prompt_sha256": hashes,
            "reencoded_len_min": min(reenc) if reenc else None, "reencoded_len_max": max(reenc) if reenc else None,
            "reencoded_len_mean": round(sum(reenc) / len(reenc), 2) if reenc else None,
            "parts_min": min(nparts) if nparts else None, "parts_max": max(nparts) if nparts else None,
            "conversations_concatenated_min": min(ks) if ks else None, "conversations_concatenated_max": max(ks) if ks else None,
            "conversations_concatenated_hist": {str(k): ks.count(k) for k in sorted(set(ks))},
            "dropped_chars_hist": {str(d): dropped.count(d) for d in sorted(set(dropped))},
        }
        c = rec["cells"][str(L)]
        print(f"prompt {L}: ok {c['n_ok']} exceptions {c['n_exceptions']} re-encoded {c['reencoded_len_min']}-{c['reencoded_len_max']} "
              f"(mean {c['reencoded_len_mean']}) conversations {c['conversations_concatenated_hist']} "
              f"system-line chars dropped {c['dropped_chars_hist']} {c['seconds']} s", flush=True)
    rec["convos_sha256_after"] = sha(gen.convos)
    rec["stored_lists_unchanged"] = rec["convos_sha256_after"] == rec["convos_sha256_before"]
    rec["total_exceptions"] = len(rec["exceptions"])
    rec["identity_1024_ok"] = not rec["identity_1024_mismatches"]
    with open(out, "w") as f:
        json.dump(rec, f, indent=1)
    print(f"exceptions total {rec['total_exceptions']}; stored lists unchanged {rec['stored_lists_unchanged']}; "
          f"prompt-1024 identical to the previous code {rec['identity_1024_ok']} ({len(rec['identity_1024_mismatches'])} mismatches)")
    return 0 if rec["total_exceptions"] == 0 and rec["stored_lists_unchanged"] and rec["identity_1024_ok"] else 1


def compare(a, b):
    ra, rb = json.load(open(a)), json.load(open(b))
    bad = 0
    for L in ra["lengths"]:
        ha, hb = ra["cells"][str(L)]["prompt_sha256"], rb["cells"][str(L)]["prompt_sha256"]
        same = ha == hb
        bad += not same
        print(f"prompt {L}: {len(ha)} vs {len(hb)} prompts, identical across runs: {same}")
    print("DETERMINISTIC" if bad == 0 else f"NOT deterministic in {bad} length(s)")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    if sys.argv[1] == "run":
        sys.exit(run(sys.argv[2]))
    sys.exit(compare(sys.argv[2], sys.argv[3]))
