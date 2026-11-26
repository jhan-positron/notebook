#!/usr/bin/env python3
"""Verifier: growth of the error with chain length when the decay is near 1.

Question 1: does the difference between block form and token loop stay flat
over a long chain (claim N04)?
Question 2: does the existing token loop meet the proposed test band of
16 FP32 spacings against a float64 oracle?
"""
import numpy as np

import vm_engine as E
from vm_checks import decay_longmem, u, normal

f64 = np.float64
H, T = 4, 1024
MARKS = (32, 64, 128, 256, 512, 1024)


def run(tag, seed, **kw):
    S0, K, Q, V, D, Bt = E.make(seed, H, T, **kw)
    keep = set(MARKS)
    O_t, _, sn_t = E.token_f32(S0, K, Q, V, D, Bt, keep)
    O_o, _, sn_o = E.token_f64(S0, K, Q, V, D, Bt, keep)
    O_b, _, sn_b = E.block_spec(S0, K, Q, V, D, Bt, keep=keep)
    print(f"{tag}")
    print("  tokens | state error in FP32 spacings of the largest |S|: token loop vs oracle, block vs oracle, "
          "block vs token loop | outputs of the last 32 tokens, same three")
    for m in MARKS:
        sp = E.spacing(float(np.abs(sn_o[m]).max()))
        e = lambda a, b: float(np.abs(a.astype(f64) - b.astype(f64)).max())
        osl = slice(m - 32, m)
        spo = E.spacing(float(np.abs(O_o[:, osl]).max()))
        print(f"  {m:6d} | {e(sn_t[m], sn_o[m]) / sp:6.1f} {e(sn_b[m], sn_o[m]) / sp:6.1f} "
              f"{e(sn_b[m], sn_t[m]) / sp:6.1f} | {e(O_t[:, osl], O_o[:, osl]) / spo:6.1f} "
              f"{e(O_b[:, osl], O_o[:, osl]) / spo:6.1f} {e(O_b[:, osl], O_t[:, osl]) / spo:6.1f}")


run("A. decay 0.998-1.0 (25 % exactly 1.0), beta 0-0.2, v sigma 0.3, start state sigma 0.3", 9034,
    decay=decay_longmem, beta=u(0, 0.2), v=normal(0.3), s0=normal(0.3))
run("B. decay 0.9-1.0, beta 0-1 (the prototype's 'normal' ranges), my seed", 9001,
    decay=u(0.9, 1.0), beta=u(0, 1), v=normal(0.3), s0=normal(0.01))
run("C. decay 0.99-1.0, beta 0-1, v sigma 0.3, start state sigma 0.3", 9077,
    decay=u(0.99, 1.0), beta=u(0, 1), v=normal(0.3), s0=normal(0.3))
