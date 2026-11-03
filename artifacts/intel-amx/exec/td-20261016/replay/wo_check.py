#!/usr/bin/env python3
"""wo_check.py: validate replay.py against the binary through the logged o_proj output
('WO layer L of token T', the first logged value downstream of attention).

  WO_pred = replay_attention_output_bf16 (4096, head-major) @ Wo_dequant (4096 x 2560)
  compared with the logged WO (bf16) of the same arm. Wo comes from the GPTQ int4 checkpoint
  the run loaded (/opt/positron/weights_cache/.../model.safetensors, group 64, sym): the FPGA's
  own matmul numerics (int4 x bf16, tp2 halves) are NOT reproduced, so agreement is expected at
  the bf16 level (about 1e-2 relative per element, better in L2), not at the ulp level.
  Controls: the exact fp64 attention output through the same Wo, and a deliberately wrong head
  mapping (query heads reversed inside each KV group) to show the check discriminates.
"""
import argparse
import json
import os
import struct
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import replay as R  # noqa: E402

f32, f64 = np.float32, np.float64
ST = "/opt/positron/weights_cache/cached/positron-ai/Qwen--Qwen3-4B-Instruct-2507-ingest-best-gptq/model.safetensors"


def read_safetensors(path, names):
    with open(path, "rb") as f:
        n = struct.unpack("<Q", f.read(8))[0]
        hdr = json.loads(f.read(n))
        out = {}
        for nm in names:
            e = hdr[nm]
            a, b = e["data_offsets"]
            f.seek(8 + n + a)
            raw = f.read(b - a)
            if e["dtype"] == "I32":
                arr = np.frombuffer(raw, dtype="<i4")
            elif e["dtype"] == "BF16":
                arr = (np.frombuffer(raw, dtype="<u2").astype(np.uint32) << 16).view(f32)
            else:
                raise ValueError(e["dtype"])
            out[nm] = arr.reshape(e["shape"])
    return out


def unpack4(q):
    """int32-packed 4-bit values along axis 0: (n/8, m) -> (n, m), low nibble first."""
    u = q.astype(np.uint32)
    parts = [((u >> (4 * k)) & 0xF) for k in range(8)]
    return np.stack(parts, axis=1).reshape(q.shape[0] * 8, q.shape[1])


def dequant_o_proj(layer):
    p = f"model.layers.{layer}.self_attn.o_proj."
    t = read_safetensors(ST, [p + "qweight", p + "qzeros", p + "scales", p + "g_idx"])
    q = unpack4(t[p + "qweight"])                       # (4096 in, 2560 out)
    zc = t[p + "qzeros"].astype(np.uint32)               # (64 groups, 320) packed along out
    z = np.stack([((zc >> (4 * k)) & 0xF) for k in range(8)], axis=2).reshape(zc.shape[0], zc.shape[1] * 8)
    g = t[p + "g_idx"]
    info = {"zeros_unique": sorted(set(np.unique(z).tolist())), "g_idx_is_i_div_64": bool(np.array_equal(g, np.arange(4096) // 64))}
    # checkpoint_format 'gptq' (v1): stored zero = true zero - 1; sym -> true zero 8
    ztrue = z.astype(np.int64) + 1
    s = t[p + "scales"].astype(f64)                      # (64, 2560)
    W = s[g] * (q.astype(np.int64) - ztrue[g])           # (4096, 2560) float64
    return W, info


def attention_outputs(arrs, model, T, order, amx_model, perm_wrong=False):
    Q, K, V = arrs["Q"], arrs["K"], arrs["V"]
    N = T + 1
    o16 = []
    o64 = []
    for g in range(R.N_KV_HEADS):
        q = Q[T, g * R.KV_MUL * R.HEAD:(g + 1) * R.KV_MUL * R.HEAD].reshape(R.KV_MUL, R.HEAD)
        Kg = K[:N, g * R.HEAD:(g + 1) * R.HEAD]
        Vg = V[:N, g * R.HEAD:(g + 1) * R.HEAD]
        prod = (q[:, None, :] * Kg[None, :, :]).astype(f32)
        sD = R.score_D(prod, order); sR = R.score_R(prod, order); sA = R.score_A(prod, amx_model, order)
        _, ob, _, _ = R.run_model(model, T, sD, sR, sA, Vg, order, amx_model)
        ex, _ = R.exact_reference(q, Kg, Vg, T)
        if perm_wrong:
            ob = ob[::-1]; ex = ex[::-1]
        o16.append(ob); o64.append(ex)
    return np.concatenate(o16).ravel().astype(f64), np.concatenate(o64).ravel()


def cmp(pred, logged):
    d = pred - logged
    rel_l2 = float(np.sqrt((d ** 2).sum() / (logged ** 2).sum()))
    rms = np.sqrt((logged ** 2).mean())
    big = np.abs(logged) >= 0.1 * rms
    rel_big = np.abs(d[big]) / np.abs(logged[big])
    # bf16 agreement: elements where bf16(pred) == logged
    same = R.bf16_rne(pred.astype(f32)) == logged.astype(f32)
    return {"rel_l2": rel_l2, "median_rel_big": float(np.median(rel_big)), "max_rel_big": float(rel_big.max()),
            "frac_bf16_equal": float(same.mean())}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--extract", required=True, help="arm extract file (Q,K,V,O)")
    ap.add_argument("--model", required=True, help="replay model for this arm (clean/newoff/base/new/trunc)")
    ap.add_argument("--layer", type=int, default=0)
    ap.add_argument("--tokens", default="0,1,2,5,17,64,100,127,128,150,191,1024,1090,1278")
    ap.add_argument("--other", default=None, help="another arm's extract: logged WO difference for scale")
    ap.add_argument("--out", default="wo_check.json")
    args = ap.parse_args()
    toks = [int(x) for x in args.tokens.split(",")]
    W, info = dequant_o_proj(args.layer)
    print(f"# o_proj layer {args.layer} dequantized: W {W.shape} {info}")
    arrs, _, _ = R.load_extract(args.extract, args.layer)
    other = R.load_extract(args.other, args.layer, want=("O",))[0] if args.other else None
    res = {"info": info, "model": args.model, "layer": args.layer, "tokens": {}}
    for T in toks:
        logged = arrs["O"][T].astype(f64)
        o16, o64 = attention_outputs(arrs, args.model, T, R.WITHIN_PAIR_ORDER, R.AMX_MODEL)
        ow, _ = attention_outputs(arrs, args.model, T, R.WITHIN_PAIR_ORDER, R.AMX_MODEL, perm_wrong=True)
        r = {"replay_bf16": cmp(o16 @ W, logged), "exact_fp64": cmp(o64 @ W, logged),
             "wrong_head_order": cmp(ow @ W, logged)}
        if other is not None and T < other["O"].shape[0]:
            r["logged_WO_other_arm_vs_this"] = cmp(other["O"][T].astype(f64), logged)
        res["tokens"][T] = r
        print(f"token {T:5d}: replay rel_l2={r['replay_bf16']['rel_l2']:.2e} median_rel={r['replay_bf16']['median_rel_big']:.2e} "
              f"bf16_equal={r['replay_bf16']['frac_bf16_equal']:.3f} | exact64 rel_l2={r['exact_fp64']['rel_l2']:.2e} "
              f"| wrong-order rel_l2={r['wrong_head_order']['rel_l2']:.2e}"
              + (f" | other arm's logged WO rel_l2={r['logged_WO_other_arm_vs_this']['rel_l2']:.2e}" if "logged_WO_other_arm_vs_this" in r else ""))
    with open(args.out, "w") as fh:
        json.dump(res, fh, indent=1)


if __name__ == "__main__":
    main()
