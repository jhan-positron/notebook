#!/usr/bin/env python3
"""Verifier: two cross checks.

1. My engine (vm_engine.py, written from F6 and the specification) against the
   lead's emulation (lead_numerics_rerun.py + proto_copy.py), bit for bit, on
   the prototype's 'normal' inputs. Same order of P1 (pieces outer) and no
   DAZ/FTZ, which is what the lead's script models.
2. Claim M06: a tile product with 16 real Q columns gives, in columns 0..3,
   the bits of the product with 4 real columns and 12 zero columns.
"""
import numpy as np

import lead_numerics_rerun as L
import proto_copy as P
import vm_engine as E

u32, f32 = np.uint32, np.float32

S0, K, Q, V, D, Bt = P.make_inputs(P.SCENARIOS["normal"], 2, 64)
O_p, S_p, _ = P.token_form_f32(S0, K, Q, V, D, Bt)
O_m, S_m, _ = E.token_f32(S0, K, Q, V, D, Bt)
print("1a token loop, my engine against the prototype engine: output bits equal",
      bool((O_p.view(u32) == O_m.view(u32)).all()), "| state bits equal", bool((S_p.view(u32) == S_m.view(u32)).all()))
O_l, S_l, _ = L.block_spec(S0, K, Q, V, D, Bt, 32, "Y")
O_b, S_b, _ = E.block_spec(S0, K, Q, V, D, Bt, p1_order="piece_outer", ftz=False)
print("1b block form (pieces outer, no DAZ/FTZ), my engine against the lead's: output bits equal",
      bool((O_l.view(u32) == O_b.view(u32)).all()), "| state bits equal", bool((S_l.view(u32) == S_b.view(u32)).all()))
O_k, S_k, _ = E.block_spec(S0, K, Q, V, D, Bt, p1_order="kb_outer", ftz=True)
print("1c block form with the loop of tile_mapping (key block outer) against the lead's emulation: FP32 output values that differ",
      int((O_l.view(u32) != O_k.view(u32)).sum()), "of", O_k.size, "| state values that differ",
      int((S_l.view(u32) != S_k.view(u32)).sum()), "of", S_k.size)

rng = np.random.default_rng(12)
Kt = E.rbf16(rng.standard_normal((8, 16, 32)).astype(f32))  # 8 dim steps of one K tile (16 tokens x 32 dims)
Q16 = E.rbf16(rng.standard_normal((8, 16, 32)).astype(f32))  # packed Q, 16 real columns (4 tokens x 4 heads)
Q4 = Q16.copy()
Q4[:, :, 8:] = 0  # columns 4..15 zero (pairs: column n uses elements 2n, 2n+1)
C16 = np.zeros((16, 16), f32)
C4 = np.zeros((16, 16), f32)
for s in range(8):
    C16 = E.tdpbf16ps_literal(C16, Kt[s], Q16[s])
    C4 = E.tdpbf16ps_literal(C4, Kt[s], Q4[s])
print("2  M06: columns 0..3 of the 16-column product equal the 4-column product bit for bit:",
      bool((C16[:, :4].view(u32) == C4[:, :4].view(u32)).all()), "| columns 4..15 of the 4-column product all zero:",
      bool((C4[:, 4:] == 0).all()))
