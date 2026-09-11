"""Compare the two pinned K encodings and their scalar HBM mappings.

This validates address algebra, not production shuffle code or performance.
"""
from pathlib import Path
import json

P, D = 64, 128


def bill_offset(p, d):
  return (p // 16) * D * 16 + (d // 2) * 32 + (p % 16) * 2 + d % 2


def pr3879_offset(p, d):
  return ((((d // 32 * 4 + p // 16) * 16 + (d % 32) // 2)
    * 16 + p % 16) * 2 + d % 2)


def hw_offset(d):
  return (d % 4) * 32 + d // 4


bill = [bill_offset(p, d) for p in range(P) for d in range(D)]
current = [pr3879_offset(p, d) for p in range(P) for d in range(D)]
assert sorted(bill) == sorted(current) == list(range(P * D))
assert bill_offset(0, 32) == 512
assert pr3879_offset(0, 32) == 2048
assert sum(a != b for a, b in zip(bill, current)) == 6144

canonical = list(range(P * D))  # distinct 16-bit payloads, no floating arithmetic
planes = []
for indices in (bill, current):
  packed = [None] * (P * D)
  for logical, offset in enumerate(indices):
    packed[offset] = canonical[logical]
  planes.append(packed)

for p in range(P):
  reference = [None] * D
  for d in range(D):
    reference[hw_offset(d)] = canonical[p * D + d]
  for offset, packed in zip((bill_offset, pr3879_offset), planes):
    fused = [None] * D
    for d in range(D):
      fused[hw_offset(d)] = packed[offset(p, d)]
    assert fused == reference

result = {
  'status': 'PASS',
  'scope': 'Scalar address algebra; no production GOF/kernel execution',
  'each_layout_bijection_elements': P * D,
  'different_physical_offsets': 6144,
  'example_p0_d32_bf16_offsets': {'bill': 512, 'pr3879': 2048},
  'hbm_row_comparisons': P * 2,
  'new_performance_measurements': False,
}
path = Path(__file__).with_name('bill-layout-check.json')
path.write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
