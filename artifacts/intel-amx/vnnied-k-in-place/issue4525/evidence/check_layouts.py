#!/usr/bin/env python3
"""Check the design's index formulas against physical-order enumeration."""

import json
from pathlib import Path


def check_v(rows, cols):
    physical_order = [(p + lane, d) for p in range(0, rows, 2)
                      for d in range(cols) for lane in range(2)]
    for offset, (token, dim) in enumerate(physical_order):
        assert (token // 2) * (2 * cols) + 2 * dim + token % 2 == offset
    assert len(set(physical_order)) == rows * cols
    return {"rows_tokens": rows, "columns_dimensions": cols,
            "elements_checked": len(physical_order), "plane_bytes": 2 * rows * cols}


def check_k():
    physical_order = [(block * 16 + token, step * 32 + pair * 2 + lane)
                      for step in range(4) for block in range(4)
                      for pair in range(16) for token in range(16) for lane in range(2)]
    def offset(token, dim):
        return ((((dim // 32) * 4 + token // 16) * 16 + (dim % 32) // 2)
                * 16 + token % 16) * 2 + dim % 2
    for expected, (token, dim) in enumerate(physical_order):
        assert offset(token, dim) == expected
    assert len(set(physical_order)) == 64 * 128
    anchors = {(0, 0): 0, (0, 1): 1, (1, 0): 2, (0, 2): 32,
               (16, 0): 512, (0, 32): 2048, (63, 127): 8191}
    for coordinate, expected in anchors.items():
        assert offset(*coordinate) == expected
    return {"rows_tokens": 64, "columns_dimensions": 128,
            "elements_checked": len(physical_order), "anchors_checked": len(anchors),
            "plane_bytes": 64 * 128 * 2}


if __name__ == "__main__":
    result = {"kind": "design arithmetic check, not a C++ implementation test",
              "packed_v": [check_v(64, d) for d in (64, 128, 256, 512)],
              "blocked_packed_k": check_k()}
    Path(__file__).with_name("layout-checks.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
