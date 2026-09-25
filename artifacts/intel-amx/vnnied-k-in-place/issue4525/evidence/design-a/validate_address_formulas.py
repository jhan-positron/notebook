"""Compare byte addresses before and after the scalar-storage change.

This reproduces the independent source-arithmetic review. It does not compile
or execute the C++ implementation. The formulas come from scaled_v_expr and
book's slot/page addressing in h/tron/models/kv_cache.hpp.

Shapes:
  * Head widths: 64, 128, 256, and 512 bf16 elements.
  * Page width: 64 tokens; each bf16 element occupies 2 bytes.
  * Packed vector path: 16-element chunks, two tokens per 64-byte vector.
  * Row-major vector path: 8-element chunks, eight vector loads per part.
  * Slot addressing: 1, 2, 5, or 17 pages; 1, 2, or 8 heads;
    and slot prefixes of 0, 1, or 3 same-geometry slots.

Run from any directory with Python 3:
  python3 validate_address_formulas.py
"""

from itertools import product

checks = {
    "packed_vector_addresses": 0,
    "row_major_vector_addresses": 0,
    "slot_byte_to_scalar_offsets": 0,
}
scalar_bytes = 2
for head_size in (64, 128, 256, 512):
    chunk_size = 16
    starts = (0, 16) if head_size == 512 else (0,)
    loads = 16 if head_size >= 256 else head_size // chunk_size
    for row, start, load in product(range(0, 64, 2), starts, range(loads)):
        old = (
            row * (head_size // chunk_size) * (chunk_size * scalar_bytes)
            + (start + load) * 64
        )
        new = (row * head_size + (start + load) * 2 * chunk_size) * scalar_bytes
        assert old == new
        assert new + 64 <= 64 * head_size * scalar_bytes
        checks["packed_vector_addresses"] += 1
    chunk_size = 8
    for row, part, load in product(
        range(64), range(head_size // chunk_size // 8), range(8)
    ):
        old = (
            (row * (head_size // chunk_size) + part * 8 + load)
            * chunk_size
            * scalar_bytes
        )
        new = (row * head_size + (part * 8 + load) * chunk_size) * scalar_bytes
        assert old == new
        checks["row_major_vector_addresses"] += 1
    block_bytes = 2 * 64 * head_size * scalar_bytes
    for pages, heads, slot_prefix in product((1, 2, 5, 17), (1, 2, 8), (0, 1, 3)):
        offset = slot_prefix * heads * block_bytes
        for head, page in product(range(heads), range(pages)):
            old = pages * offset + (head * pages + page) * block_bytes
            new = (
                pages * (offset // scalar_bytes)
                + (head * pages + page) * (block_bytes // scalar_bytes)
            ) * scalar_bytes
            assert old == new
            checks["slot_byte_to_scalar_offsets"] += 1
print(checks)
